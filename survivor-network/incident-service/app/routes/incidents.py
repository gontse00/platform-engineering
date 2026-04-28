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
    needs = [payload.primary_need] if payload.primary_need else []
    needs.extend(payload.secondary_needs)
    case = Case(
        source="chatbot",
        summary=payload.message[:500],
        incident_type=payload.incident_type,
        location_text=payload.location_text,
        latitude=payload.latitude,
        longitude=payload.longitude,
        urgency=payload.urgency,
        safety_risk=payload.safety_risk,
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

def _to_response(report):
    return {"id": str(report.id), "reporter_participant_id": report.reporter_participant_id, "source": report.source, "incident_type": report.incident_type, "summary": report.summary, "description": report.description, "location_text": report.location_text, "latitude": report.latitude, "longitude": report.longitude, "urgency": report.urgency, "safety_risk": report.safety_risk, "status": report.status, "needs": report.needs or [], "created_at": report.created_at}

def _case_response(case):
    return {"id": str(case.id), "incident_report_id": case.incident_report_id, "source": case.source, "summary": case.summary, "incident_type": case.incident_type, "location_text": case.location_text, "latitude": case.latitude, "longitude": case.longitude, "urgency": case.urgency, "safety_risk": case.safety_risk, "status": case.status, "needs": case.needs or [], "assigned_participant_id": case.assigned_participant_id, "created_at": case.created_at, "updated_at": case.updated_at}
