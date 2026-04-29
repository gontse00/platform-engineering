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

    # --- Deterministic safety normalization ---
    message_lower = payload.message.lower()
    urgency, safety_risk, needs, incident_type = _normalize_case_safety(
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
    {"phrases": ["stabbed", "stabbing", "bleeding heavily", "bleeding badly"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Assault",
     "needs": ["Emergency Medical"]},
    {"phrases": ["unconscious", "not breathing", "no pulse", "collapsed and"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Medical Emergency",
     "needs": ["Emergency Medical"]},
    {"phrases": ["building collapse", "trapped under", "people are trapped"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Disaster",
     "needs": ["Emergency Medical"]},
    {"phrases": ["overdose", "took too many pills", "swallowed pills", "poisoned"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Overdose",
     "needs": ["Emergency Medical", "Mental Health Support"]},
    {"phrases": ["kill myself", "want to die", "end my life", "suicidal"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Mental Health Crisis",
     "needs": ["Emergency Medical", "Mental Health Support"]},
    {"phrases": ["being attacked", "attacking me", "beating me right now", "hitting me right now"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Assault",
     "needs": ["Emergency Medical", "Emergency Shelter"]},
    {"phrases": ["husband is beating", "partner is hitting", "beating me right now"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Domestic Violence",
     "needs": ["Emergency Shelter", "Protection Order Support"]},
    # --- URGENT / HIGH ---
    {"phrases": ["raped", "i was raped", "sexual assault", "sexually assaulted"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Sexual Assault",
     "needs": ["Emergency Medical", "Mental Health Support"]},
    {"phrases": ["domestic violence", "partner hit me", "husband hit me", "abusive partner"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Domestic Violence",
     "needs": ["Emergency Shelter", "Protection Order Support"]},
    {"phrases": ["knife", "gun", "weapon", "armed"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Armed Threat",
     "needs": ["Emergency Shelter"]},
    {"phrases": ["kidnap", "abducted", "locked in", "trapped", "won't let me leave"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Kidnapping",
     "needs": ["Emergency Shelter"]},
    # --- URGENT / MEDIUM ---
    {"phrases": ["arv", "hiv medication", "antiretroviral", "ran out of medication", "need my medication"],
     "urgency": "urgent", "safety_risk": "medium", "incident_type": "Medication Access",
     "needs": ["Medication Access"]},
    {"phrases": ["need shelter", "nowhere to stay", "kicked me out", "homeless"],
     "urgency": "urgent", "safety_risk": "medium", "incident_type": "Displacement",
     "needs": ["Emergency Shelter"]},
    {"phrases": ["mugged", "robbed", "robbery", "stolen"],
     "urgency": "medium", "safety_risk": "medium", "incident_type": "Robbery",
     "needs": ["Transport"]},
    {"phrases": ["hijack", "carjack"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Hijacking",
     "needs": ["Emergency Medical", "Transport"]},
    # --- MEDIUM ---
    {"phrases": ["counselling", "counseling", "trauma", "panic attack", "can't cope"],
     "urgency": "medium", "safety_risk": "low", "incident_type": "Mental Health",
     "needs": ["Mental Health Support"]},
    {"phrases": ["protection order", "restraining order", "legal help"],
     "urgency": "medium", "safety_risk": "medium", "incident_type": "Legal Support",
     "needs": ["Protection Order Support"]},
    {"phrases": ["break-in", "broke into", "burglary"],
     "urgency": "medium", "safety_risk": "medium", "incident_type": "Break-in",
     "needs": ["Protection Order Support"]},
    {"phrases": ["stranded", "no transport", "need a ride", "can't get home"],
     "urgency": "medium", "safety_risk": "low", "incident_type": "Transport Need",
     "needs": ["Transport"]},
]

URGENCY_ORDER = ["standard", "medium", "urgent", "critical"]
SAFETY_ORDER = ["low", "medium", "high", "immediate"]


def _normalize_case_safety(
    message_lower: str,
    incoming_urgency: str,
    incoming_safety_risk: str,
    incoming_needs: list[str],
    incoming_incident_type: str | None,
    immediate_danger: bool,
) -> tuple[str, str, list[str], str | None]:
    """Apply deterministic safety rules. Returns (urgency, safety_risk, needs, incident_type)."""

    # Normalize incoming values to valid set
    urgency = incoming_urgency if incoming_urgency in URGENCY_ORDER else "medium"
    safety_risk = incoming_safety_risk if incoming_safety_risk in SAFETY_ORDER else "low"
    needs: set[str] = set(n for n in incoming_needs if n)
    incident_type = incoming_incident_type

    # Apply pattern rules — take the highest matching urgency/safety
    for rule in _SAFETY_RULES:
        for phrase in rule["phrases"]:
            if phrase in message_lower:
                rule_urg_idx = URGENCY_ORDER.index(rule["urgency"])
                rule_saf_idx = SAFETY_ORDER.index(rule["safety_risk"])
                if rule_urg_idx > URGENCY_ORDER.index(urgency):
                    urgency = rule["urgency"]
                if rule_saf_idx > SAFETY_ORDER.index(safety_risk):
                    safety_risk = rule["safety_risk"]
                if not incident_type:
                    incident_type = rule["incident_type"]
                for need in rule["needs"]:
                    needs.add(need)
                break  # first phrase match per rule

    # Immediate danger flag always forces critical/immediate
    if immediate_danger:
        if URGENCY_ORDER.index(urgency) < URGENCY_ORDER.index("critical"):
            urgency = "critical"
        if SAFETY_ORDER.index(safety_risk) < SAFETY_ORDER.index("immediate"):
            safety_risk = "immediate"

    # Safety net: urgent+ cases must have at least one need
    if URGENCY_ORDER.index(urgency) >= URGENCY_ORDER.index("urgent") and not needs:
        needs.add("Emergency Support")

    return urgency, safety_risk, sorted(needs), incident_type


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
