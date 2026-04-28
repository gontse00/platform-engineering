"""Generates empathetic replies based on triage and extracted fields."""

import random

from app.models import ExtractedFields, TriageResult, SafetyFlags

_CRITICAL_REPLIES = [
    "I'm sorry this happened. Your safety is the priority. I'm identifying urgent support options near you now.",
    "Help is being prioritized for you right now. Stay as safe as you can — we're connecting you with emergency support.",
    "I hear you. This is being treated as urgent. Support is being arranged immediately.",
]

_HIGH_REPLIES = [
    "Thank you for reaching out. What you've been through is serious and we're here to help. Let me find the right support for you.",
    "I'm here to help. We're treating this as a priority and will connect you with the right people.",
]

_URGENT_REPLIES = [
    "I understand you need help soon. Let me find the best options available to you.",
    "Thank you for sharing this. We're working on connecting you with support as quickly as possible.",
]

_STANDARD_REPLIES = [
    "Thank you for reaching out. I'd like to understand your situation better so I can connect you with the right support.",
    "I'm here to help. Can you tell me more about what you need and where you are?",
]


def generate_reply(
    extracted: ExtractedFields,
    triage: TriageResult,
    safety_flags: SafetyFlags,
) -> str:
    """Pick an appropriate empathetic reply based on triage urgency."""
    urgency = triage.suggested_urgency

    if urgency == "critical":
        return random.choice(_CRITICAL_REPLIES)
    elif urgency == "high":
        return random.choice(_HIGH_REPLIES)
    elif urgency == "urgent":
        return random.choice(_URGENT_REPLIES)
    else:
        return random.choice(_STANDARD_REPLIES)
