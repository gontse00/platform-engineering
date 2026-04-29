from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.incident import IncidentReport, Case, CaseTimelineEntry, CaseAssignment
from app.schemas.incident import (
    IncidentReportCreate, IncidentReportResponse,
    CaseCreate, CaseFromIntake, CaseResponse,
    StatusUpdate, TimelineEntryCreate, TimelineEntryResponse,
    AssignmentCreate,
)

router = APIRouter(tags=["incidents"])

@router.post("/incident-reports", response_model=IncidentReportResponse)
def create_incident_report(payload: IncidentReportCreate, db: Session = Depends(get_db)):
    report = IncidentReport(**payload.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return _to_response(report)

@router.get("/incident-reports/{report_id}", response_model=IncidentReportResponse)
def get_incident_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(IncidentReport).filter(IncidentReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_response(report)

@router.post("/cases", response_model=CaseResponse)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    case = Case(**payload.model_dump())
    db.add(case)
    db.flush()
    _add_timeline(db, str(case.id), "created", f"Case created from {payload.source}")
    db.commit()
    db.refresh(case)
    return _case_response(case)

@router.post("/cases/from-intake", response_model=CaseResponse)
def create_case_from_intake(payload: CaseFromIntake, db: Session = Depends(get_db)):
    # --- Idempotency: one case per session ---
    if payload.session_id:
        existing = db.query(Case).filter(Case.source_session_id == payload.session_id).first()
        if existing:
            return _case_response(existing)

    # --- Safety inference: boost urgency/risk from keywords when LLM is off ---
    urgency = payload.urgency
    safety_risk = payload.safety_risk
    needs = [payload.primary_need] if payload.primary_need else []
    needs.extend(payload.secondary_needs)
    incident_type = payload.incident_type

    message_lower = payload.message.lower()

    # Infer incident_type from message if null
    if not incident_type:
        incident_type = _infer_incident_type(message_lower)

    # Safety boost: if immediate_danger or critical keywords, enforce minimum urgency
    if payload.immediate_danger:
        if urgency in ("low", "medium", "standard"):
            urgency = "critical"
        if safety_risk in ("low", "medium"):
            safety_risk = "critical"

    # Infer needs from message if empty
    if not needs:
        needs = _infer_needs(message_lower)

    case = Case(
        source="chatbot",
        source_session_id=payload.session_id,
        summary=payload.message[:500],
        incident_type=incident_type,
        location_text=payload.location_text,
        latitude=payload.latitude,
        longitude=payload.longitude,
        urgency=urgency,
        safety_risk=safety_risk,
        needs=needs,
    )
    db.add(case)
    db.flush()
    _add_timeline(db, str(case.id), "created", f"Case created from chatbot intake (session={payload.session_id})")
    if payload.immediate_danger:
        case.status = "triaging"
        _add_timeline(db, str(case.id), "escalation", "Immediate danger flagged — auto-triaging")
    db.commit()
    db.refresh(case)
    return _case_response(case)

@router.get("/cases/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return _case_response(case)

@router.get("/cases")
def list_cases(status: str | None = None, urgency: str | None = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    q = db.query(Case).order_by(Case.created_at.desc())
    if status:
        q = q.filter(Case.status == status)
    if urgency:
        q = q.filter(Case.urgency == urgency)
    total = q.count()
    cases = q.offset(offset).limit(limit).all()
    return {"cases": [_case_response(c) for c in cases], "total": total}

@router.patch("/cases/{case_id}/status")
def update_case_status(case_id: str, payload: StatusUpdate, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    old_status = case.status
    case.status = payload.status
    _add_timeline(db, case_id, "status_change", f"Status changed from {old_status} to {payload.status}", metadata={"reason": payload.reason})
    db.commit()
    return {"case_id": case_id, "old_status": old_status, "new_status": payload.status}

@router.post("/cases/{case_id}/timeline", response_model=TimelineEntryResponse)
def add_timeline_entry(case_id: str, payload: TimelineEntryCreate, db: Session = Depends(get_db)):
    entry = CaseTimelineEntry(case_id=case_id, event_type=payload.event_type, description=payload.description, actor=payload.actor)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": str(entry.id), "case_id": case_id, "event_type": entry.event_type, "description": entry.description, "actor": entry.actor, "created_at": entry.created_at}

@router.post("/cases/{case_id}/assignments")
def assign_case(case_id: str, payload: AssignmentCreate, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    assignment = CaseAssignment(case_id=case_id, participant_id=payload.participant_id, role=payload.role)
    db.add(assignment)
    case.assigned_participant_id = payload.participant_id
    if case.status == "new" or case.status == "triaging":
        case.status = "assigned"
    _add_timeline(db, case_id, "assignment", f"Assigned to participant {payload.participant_id} as {payload.role}")
    db.commit()
    return {"case_id": case_id, "participant_id": payload.participant_id, "role": payload.role}

def _add_timeline(db, case_id, event_type, description, actor=None, metadata=None):
    entry = CaseTimelineEntry(case_id=case_id, event_type=event_type, description=description, actor=actor, metadata_json=metadata or {})
    db.add(entry)


# ---------------------------------------------------------------------------
# Safety inference helpers (deterministic, no LLM)
# ---------------------------------------------------------------------------

_INCIDENT_TYPE_KEYWORDS: dict[str, str] = {
    "mugged": "Robbery", "robbed": "Robbery", "robbery": "Robbery", "stolen": "Robbery",
    "assaulted": "Assault", "attacked": "Assault", "beaten": "Assault", "hit me": "Assault",
    "stabbed": "Assault", "punched": "Assault",
    "domestic": "Domestic Violence", "partner": "Domestic Violence", "husband": "Domestic Violence",
    "wife": "Domestic Violence", "boyfriend": "Domestic Violence",
    "raped": "Sexual Violence", "sexual assault": "Sexual Violence", "sexually": "Sexual Violence",
    "hijack": "Hijacking", "carjack": "Hijacking",
    "break-in": "Break-in", "broke into": "Break-in", "burglary": "Break-in",
    "kidnap": "Kidnapping", "abducted": "Kidnapping", "grabbed": "Child Endangerment",
    "child": "Child Endangerment",
    "threat": "Threats", "threatened": "Threats",
    "stalking": "Stalking", "following me": "Stalking",
}

_NEED_KEYWORDS: dict[str, str] = {
    "shelter": "Emergency Shelter", "nowhere to stay": "Emergency Shelter",
    "homeless": "Emergency Shelter", "kicked out": "Emergency Shelter",
    "medical": "Emergency Medical", "hospital": "Emergency Medical",
    "bleeding": "Emergency Medical", "injured": "Emergency Medical", "ambulance": "Emergency Medical",
    "medication": "Medication Access", "pills": "Medication Access", "arv": "Medication Access",
    "counsell": "Mental Health Support", "trauma": "Mental Health Support",
    "mental": "Mental Health Support", "panic": "Mental Health Support",
    "transport": "Transport", "stranded": "Transport", "ride": "Transport",
    "legal": "Protection Order Support", "protection order": "Protection Order Support",
}


def _infer_incident_type(message_lower: str) -> str | None:
    for keyword, itype in _INCIDENT_TYPE_KEYWORDS.items():
        if keyword in message_lower:
            return itype
    return None


def _infer_needs(message_lower: str) -> list[str]:
    found: set[str] = set()
    for keyword, need in _NEED_KEYWORDS.items():
        if keyword in message_lower:
            found.add(need)
    return sorted(found) if found else []


# ---------------------------------------------------------------------------
# Dev-only: reset test data
# ---------------------------------------------------------------------------

@router.delete("/dev/reset-cases")
def reset_cases(db: Session = Depends(get_db)):
    """Delete all cases, timeline entries, and assignments. DEV ONLY."""
    db.query(CaseAssignment).delete()
    db.query(CaseTimelineEntry).delete()
    db.query(Case).delete()
    db.query(IncidentReport).delete()
    db.commit()
    return {"reset": True, "message": "All cases, reports, timeline, and assignments deleted."}

def _to_response(report):
    return {"id": str(report.id), "reporter_participant_id": report.reporter_participant_id, "source": report.source, "incident_type": report.incident_type, "summary": report.summary, "description": report.description, "location_text": report.location_text, "latitude": report.latitude, "longitude": report.longitude, "urgency": report.urgency, "safety_risk": report.safety_risk, "status": report.status, "needs": report.needs or [], "created_at": report.created_at}

def _case_response(case):
    return {"id": str(case.id), "source_session_id": case.source_session_id, "incident_report_id": case.incident_report_id, "source": case.source, "summary": case.summary, "incident_type": case.incident_type, "location_text": case.location_text, "latitude": case.latitude, "longitude": case.longitude, "urgency": case.urgency, "safety_risk": case.safety_risk, "status": case.status, "needs": case.needs or [], "assigned_participant_id": case.assigned_participant_id, "created_at": case.created_at, "updated_at": case.updated_at}
