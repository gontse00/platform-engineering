from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from models.schemas import (
    CaseIntakeRequest,
    CaseIntakeResponse,
    CaseContextUpdateRequest,
    CaseContextUpdateResponse,
)
from services.case_orchestration_service import CaseOrchestrationService
from services.case_update_service import CaseUpdateService

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/intake", response_model=CaseIntakeResponse)
def intake_case(payload: CaseIntakeRequest, db: Session = Depends(get_db)):
    return CaseOrchestrationService.intake_case(
        db=db,
        message=payload.message,
        location=payload.location,
        top_k=payload.top_k,
        create_referrals=payload.create_referrals,
    )


@router.patch("/{case_id}/context", response_model=CaseContextUpdateResponse)
def update_case_context(case_id: str, payload: CaseContextUpdateRequest, db: Session = Depends(get_db)):
    result = CaseUpdateService.update_case_context(
        db=db,
        case_id=case_id,
        payload=payload.model_dump(),
    )
    if not result["updated"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result