"""agent-service — AI reasoning service for survivor intake and triage."""

import logging

from fastapi import FastAPI

from app.config import settings
from app.llm_provider import get_llm_client
from app.models import (
    AgentReply,
    ReasonRequest,
    ReasonResponse,
    SuggestedAction,
)
from app.agents.intake_agent import run_intake
from app.agents.triage_agent import run_triage
from app.agents.reply_generator import generate_reply

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


@app.post("/reason", response_model=ReasonResponse)
def reason(req: ReasonRequest):
    """Main reasoning endpoint. Runs intake + triage agents."""
    logger.info("Reasoning for session=%s", req.session_id)

    llm_client = get_llm_client()

    # 1. Intake extraction
    extracted = run_intake(
        message=req.message,
        context=req.conversation_context,
        safety_flags=req.safety_flags,
        llm_client=llm_client,
    )

    # 2. Triage assessment
    triage = run_triage(
        message=req.message,
        extracted=extracted,
        safety_flags=req.safety_flags,
        llm_client=llm_client,
    )

    # 3. Suggest actions based on extraction
    actions: list[SuggestedAction] = []
    if extracted.primary_need:
        actions.append(SuggestedAction(
            type="resource_lookup",
            need=extracted.primary_need,
            location=extracted.location,
            reason=f"Primary need: {extracted.primary_need}",
        ))
    if triage.requires_escalation:
        actions.append(SuggestedAction(
            type="escalation",
            reason=f"Urgency={triage.suggested_urgency}, safety={triage.safety_risk}",
        ))

    # 4. Generate reply
    reply_text = generate_reply(extracted, triage, req.safety_flags)

    return ReasonResponse(
        extracted=extracted,
        triage=triage,
        actions=actions,
        reply=AgentReply(message=reply_text),
    )
