from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.incident import IncidentReport, Case, CaseTimelineEntry, CaseAssignment
from app.safety_rules import normalize_case_safety, URGENCY_ORDER, SAFETY_ORDER, _SAFETY_RULES
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

    # --- Deterministic safety normalization ---
    message_lower = payload.message.lower()
    urgency, safety_risk, needs, incident_type = normalize_case_safety(
        message_lower=message_lower,
        incoming_urgency=payload.urgency,
        incoming_safety_risk=payload.safety_risk,
        incoming_needs=([payload.primary_need] if payload.primary_need else []) + payload.secondary_needs,
        incoming_incident_type=payload.incident_type,
        immediate_danger=payload.immediate_danger,
    )

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
    if payload.immediate_danger or urgency == "critical":
        case.status = "triaging"
        _add_timeline(db, str(case.id), "escalation", f"Auto-triaging: urgency={urgency}, safety_risk={safety_risk}")
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

@router.get("/cases/{case_id}/timeline")
def get_case_timeline(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    entries = (
        db.query(CaseTimelineEntry)
        .filter(CaseTimelineEntry.case_id == case_id)
        .order_by(CaseTimelineEntry.created_at.asc())
        .all()
    )
    return {
        "case_id": case_id,
        "timeline": [
            {
                "id": str(e.id),
                "case_id": e.case_id,
                "event_type": e.event_type,
                "description": e.description,
                "actor": e.actor,
                "metadata": e.metadata_json,
                "created_at": e.created_at,
            }
            for e in entries
        ],
    }

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
# Deterministic safety normalization (no LLM required)
# ---------------------------------------------------------------------------
# Urgency: standard, medium, urgent, critical
# Safety risk: low, medium, high, immediate

# Pattern rules: (phrases, urgency, safety_risk, incident_type, needs)
_SAFETY_RULES: list[dict] = [
    # --- CRITICAL / IMMEDIATE ---
    # DV active attack (must be above generic attack rules for specificity)
    {"phrases": ["husband is beating", "partner is hitting", "husband is hitting", "wife is hitting",
                 "boyfriend is beating", "partner is beating", "beating me right now", "locked myself in"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Domestic Violence",
     "needs": ["Emergency Shelter", "Protection Order Support"]},
    {"phrases": ["stabbed", "stabbing", "bleeding heavily", "bleeding badly"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Assault",
     "needs": ["Emergency Medical"]},
    {"phrases": ["unconscious", "not breathing", "no pulse"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Medical Emergency",
     "needs": ["Emergency Medical"]},
    {"phrases": ["building collapse", "trapped under", "people are trapped", "flood", "fire and"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Disaster / Emergency",
     "needs": ["Emergency Medical"]},
    {"phrases": ["overdose", "took too many pills", "swallowed pills", "poisoned"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Mental Health Crisis",
     "needs": ["Emergency Medical", "Mental Health Support"]},
    {"phrases": ["kill myself", "want to die", "end my life", "suicidal", "self-harm"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Mental Health Crisis",
     "needs": ["Emergency Medical", "Mental Health Support"]},
    {"phrases": ["being attacked", "attacking me", "hitting me right now"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Assault",
     "needs": ["Emergency Medical", "Emergency Shelter"]},
    # --- URGENT / HIGH ---
    {"phrases": ["raped", "i was raped", "sexual assault", "sexually assaulted"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Sexual Assault",
     "needs": ["Emergency Medical", "Mental Health Support"]},
    {"phrases": ["domestic violence", "partner hit me", "husband hit me", "abusive partner",
                 "wife hit me", "boyfriend hit me"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Domestic Violence",
     "needs": ["Emergency Shelter", "Protection Order Support"]},
    {"phrases": ["knife", "gun", "weapon", "armed"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Assault",
     "needs": ["Emergency Shelter"]},
    {"phrases": ["kidnap", "abducted", "locked in", "trapped", "won't let me leave"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Child Endangerment",
     "needs": ["Emergency Shelter"]},
    {"phrases": ["hijack", "carjack"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Hijacking",
     "needs": ["Emergency Medical", "Transport Support"]},
    # --- URGENT / MEDIUM ---
    {"phrases": ["arv", "hiv medication", "antiretroviral", "ran out of medication", "need my medication", "medication stolen"],
     "urgency": "urgent", "safety_risk": "medium", "incident_type": "Medication Access",
     "needs": ["Medication Access"]},
    {"phrases": ["need shelter", "nowhere to stay", "kicked me out", "homeless"],
     "urgency": "urgent", "safety_risk": "medium", "incident_type": "Domestic Violence",
     "needs": ["Emergency Shelter"]},
    # --- MEDIUM ---
    {"phrases": ["mugged", "robbed", "robbery", "stolen my"],
     "urgency": "medium", "safety_risk": "medium", "incident_type": "Robbery",
     "needs": ["Transport Support"]},
    {"phrases": ["counselling", "counseling", "trauma", "panic attack", "can't cope", "can't sleep"],
     "urgency": "medium", "safety_risk": "low", "incident_type": "Mental Health Crisis",
     "needs": ["Mental Health Support"]},
    {"phrases": ["protection order", "restraining order", "legal help"],
     "urgency": "medium", "safety_risk": "medium", "incident_type": "Protection Order",
     "needs": ["Protection Order Support"]},
    {"phrases": ["break-in", "broke into", "burglary"],
     "urgency": "medium", "safety_risk": "medium", "incident_type": "Break-in",
     "needs": ["Protection Order Support"]},
    {"phrases": ["stranded", "no transport", "need a ride", "can't get home"],
     "urgency": "medium", "safety_risk": "low", "incident_type": "Transport Support",
     "needs": ["Transport Support"]},
]

URGENCY_ORDER = ["standard", "medium", "urgent", "critical"]
SAFETY_ORDER = ["low", "medium", "high", "immediate"]


def _infer_incident_type(message_lower: str) -> str | None:
    """Legacy helper — kept for non-intake routes."""
    for rule in _SAFETY_RULES:
        for phrase in rule["phrases"]:
            if phrase in message_lower:
                return rule["incident_type"]
    return None


def _infer_needs(message_lower: str) -> list[str]:
    """Legacy helper — kept for non-intake routes."""
    found: set[str] = set()
    for rule in _SAFETY_RULES:
        for phrase in rule["phrases"]:
            if phrase in message_lower:
                found.update(rule["needs"])
                break
    return sorted(found) if found else []


# ---------------------------------------------------------------------------
# Dev-only: reset test data
# ---------------------------------------------------------------------------

@router.delete("/dev/reset-cases")
def reset_cases(db: Session = Depends(get_db)):
    """Delete all cases, timeline entries, and assignments. DEV/LOCAL ONLY."""
    import os
    env = os.environ.get("ENVIRONMENT", "")
    if env not in ("dev", "local", "test"):
        raise HTTPException(status_code=403, detail=f"Reset forbidden: ENVIRONMENT={env!r}. Must be dev/local/test.")

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
