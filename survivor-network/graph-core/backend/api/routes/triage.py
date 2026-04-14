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
    # Pass pre-parsed data from chatbot-service if available.
    # This skips the intake LLM call when chatbot-service already extracted fields.
    # Convert Pydantic models to dicts so all downstream services work with plain dicts
    pre_parsed_dict = payload.pre_parsed.model_dump() if payload.pre_parsed else None
    crisis_dict = payload.crisis_override.model_dump() if payload.crisis_override else None

    # Resolve coordinates: prefer pre_parsed, fall back to top-level
    lat = payload.latitude
    lon = payload.longitude
    if lat is None and pre_parsed_dict:
        lat = pre_parsed_dict.get("latitude")
        lon = pre_parsed_dict.get("longitude")

    parsed = IntakeService.parse_message(
        db=db,
        message=payload.message,
        explicit_location=payload.location,
        pre_parsed=pre_parsed_dict,
        latitude=lat,
        longitude=lon,
    )

    # Triage assessment (1 LLM call) with crisis safeguard boost
    triage = TriageService.assess_triage(
        message=payload.message,
        parsed=parsed,
        crisis_override=crisis_dict,
    )

    # Deterministic escalation (no LLM call)
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
        urgency=triage.get("urgency", "unknown"),
    )

    return {
        "message": payload.message,
        "triage": triage,
        "escalation": escalation,
        "escalation_destinations": escalation_destinations,
        "intake": intake,
    }
