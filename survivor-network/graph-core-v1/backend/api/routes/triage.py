from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from models.schemas import TriageAssessRequest, TriageAssessResponse
from services.escalation_resolver_service import EscalationResolverService
from services.escalation_service import EscalationService
from services.intake_service import IntakeService
from services.recommendation_service import RecommendationService
from services.triage_service import TriageService

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("/assess", response_model=TriageAssessResponse)
def assess_triage(payload: TriageAssessRequest, db: Session = Depends(get_db)):
    parsed = IntakeService.parse_message(
        db=db,
        message=payload.message,
        explicit_location=payload.location,
    )

    triage = TriageService.assess_triage(
        message=payload.message,
        parsed=parsed,
    )

    escalation = EscalationService.assess_escalation(
        triage=triage,
        parsed=parsed,
    )

    escalation_destinations = EscalationResolverService.resolve_destinations(
        db=db,
        triage=triage,
        escalation=escalation,
        parsed=parsed,
    )

    intake = RecommendationService.assess_intake(
        db=db,
        parsed=parsed,
        top_k=payload.top_k,
    )

    return {
        "message": payload.message,
        "triage": triage,
        "escalation": escalation,
        "escalation_destinations": escalation_destinations,
        "intake": intake,
    }