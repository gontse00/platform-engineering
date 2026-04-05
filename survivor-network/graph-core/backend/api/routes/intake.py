from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from models.schemas import IntakeAssessRequest, IntakeAssessResponse
from services.intake_service import IntakeService
from services.recommendation_service import RecommendationService

router = APIRouter(prefix="/intake", tags=["intake"])


@router.post("/assess", response_model=IntakeAssessResponse)
def assess_intake(payload: IntakeAssessRequest, db: Session = Depends(get_db)):
    parsed = IntakeService.parse_message(
        db=db,
        message=payload.message,
        explicit_location=payload.location,
    )

    result = RecommendationService.assess_intake(
        db=db,
        parsed=parsed,
        top_k=payload.top_k,
    )

    return result