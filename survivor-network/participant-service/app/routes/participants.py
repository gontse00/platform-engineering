from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.participant import Participant
from app.schemas.participant import (
    ParticipantCreate, ParticipantResponse,
    AvailabilityUpdate, VerificationUpdate, SearchAvailable,
)

router = APIRouter(tags=["participants"])

SAFETY_VERIFICATION_REQUIRED = {"admin_verified", "organization_verified", "background_checked"}

@router.post("/participants", response_model=ParticipantResponse)
def create_participant(payload: ParticipantCreate, db: Session = Depends(get_db)):
    p = Participant(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _resp(p)

@router.get("/participants/{pid}", response_model=ParticipantResponse)
def get_participant(pid: str, db: Session = Depends(get_db)):
    p = db.query(Participant).filter(Participant.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    return _resp(p)

@router.get("/participants")
def list_participants(role: str | None = None, status: str | None = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(Participant)
    if status:
        q = q.filter(Participant.availability_status == status)
    total = q.count()
    participants = q.limit(limit).all()
    return {"participants": [_resp(p) for p in participants], "total": total}

@router.patch("/participants/{pid}/availability")
def update_availability(pid: str, payload: AvailabilityUpdate, db: Session = Depends(get_db)):
    p = db.query(Participant).filter(Participant.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    p.availability_status = payload.availability_status
    db.commit()
    return {"id": str(p.id), "availability_status": p.availability_status}

@router.patch("/participants/{pid}/verification")
def update_verification(pid: str, payload: VerificationUpdate, db: Session = Depends(get_db)):
    p = db.query(Participant).filter(Participant.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    p.verification_status = payload.verification_status
    if payload.verification_status in SAFETY_VERIFICATION_REQUIRED:
        p.trust_level = "high"
    elif payload.verification_status == "phone_verified":
        p.trust_level = "medium"
    db.commit()
    return {"id": str(p.id), "verification_status": p.verification_status, "trust_level": p.trust_level}

@router.post("/participants/search-available")
def search_available(payload: SearchAvailable, db: Session = Depends(get_db)):
    """Search for available participants eligible for assignment.
    Safety rules:
    - high/critical safety_risk requires admin_verified or higher
    - suspended/offline participants excluded
    """
    q = db.query(Participant).filter(Participant.availability_status.in_(["available", "on_call"]))

    # Safety: high-risk cases require verified helpers
    if payload.safety_risk in ("high", "critical"):
        q = q.filter(Participant.verification_status.in_(list(SAFETY_VERIFICATION_REQUIRED)))

    results = q.limit(20).all()
    return {"available": [_resp(p) for p in results], "total": len(results), "safety_filter_applied": payload.safety_risk in ("high", "critical")}

def _resp(p):
    return {"id": str(p.id), "display_name": p.display_name, "phone": p.phone, "email": p.email, "roles": p.roles or [], "skills": p.skills or [], "availability_status": p.availability_status, "verification_status": p.verification_status, "trust_level": p.trust_level, "home_location_text": p.home_location_text, "latitude": p.latitude, "longitude": p.longitude, "service_radius_km": p.service_radius_km, "can_transport_people": p.can_transport_people, "can_offer_shelter": p.can_offer_shelter, "can_offer_counselling": p.can_offer_counselling, "can_offer_legal_help": p.can_offer_legal_help, "can_handle_medical": p.can_handle_medical, "can_handle_crime_report": p.can_handle_crime_report, "created_at": p.created_at}
