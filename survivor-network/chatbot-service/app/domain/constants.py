"""Shared constants, enums, and deterministic crisis safeguards for chatbot-service."""

from __future__ import annotations

from enum import Enum


# ---------------------------------------------------------------------------
# Canonical enum types — used for schema validation & normalization
# ---------------------------------------------------------------------------

class Urgency(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    URGENT = "urgent"
    STANDARD = "standard"


class SafetyRisk(str, Enum):
    IMMEDIATE = "immediate"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PrimaryNeed(str, Enum):
    EMERGENCY_MEDICAL = "Emergency Medical"
    MEDICATION_ACCESS = "Medication Access"
    MENTAL_HEALTH_SUPPORT = "Mental Health Support"
    EMERGENCY_SHELTER = "Emergency Shelter"
    PROTECTION_ORDER_SUPPORT = "Protection Order Support"
    TRANSPORT = "Transport"


class InjuryStatus(str, Enum):
    INJURED = "injured"
    NOT_INJURED = "not_injured"


class ContactMethod(str, Enum):
    TEXT = "text"
    CALL = "call"
    WHATSAPP = "whatsapp"
    EMAIL = "email"


# ---------------------------------------------------------------------------
# Deterministic crisis safeguard — keyword patterns
# ---------------------------------------------------------------------------
# These phrases, if found in a user message, FORCE urgency to at least the
# specified level regardless of what the LLM returns.  This is a safety net:
# LLMs can occasionally under-triage life-threatening situations.

CRISIS_KEYWORD_RULES: list[dict] = [
    # --- CRITICAL (life-threatening RIGHT NOW) ---
    {"phrases": ["i am bleeding", "i'm bleeding", "bleeding heavily", "losing blood"],
     "min_urgency": Urgency.CRITICAL, "min_safety": SafetyRisk.IMMEDIATE,
     "reason": "Active bleeding reported"},
    {"phrases": ["i am being attacked", "i'm being attacked", "attacking me right now",
                 "someone is hurting me", "he is hitting me", "she is hitting me",
                 "being beaten", "beating me"],
     "min_urgency": Urgency.CRITICAL, "min_safety": SafetyRisk.IMMEDIATE,
     "reason": "Active violence reported"},
    {"phrases": ["can't breathe", "cannot breathe", "i can't breath", "difficulty breathing",
                 "struggling to breathe", "choking"],
     "min_urgency": Urgency.CRITICAL, "min_safety": SafetyRisk.IMMEDIATE,
     "reason": "Breathing emergency reported"},
    {"phrases": ["i want to die", "i want to kill myself", "going to kill myself",
                 "suicidal", "end my life", "planning to end it"],
     "min_urgency": Urgency.CRITICAL, "min_safety": SafetyRisk.IMMEDIATE,
     "reason": "Suicidal ideation reported"},
    {"phrases": ["overdose", "took too many pills", "swallowed pills",
                 "poisoned", "drank poison"],
     "min_urgency": Urgency.CRITICAL, "min_safety": SafetyRisk.IMMEDIATE,
     "reason": "Overdose/poisoning reported"},
    {"phrases": ["unconscious", "not breathing", "no pulse", "collapsed",
                 "passed out and won't wake"],
     "min_urgency": Urgency.CRITICAL, "min_safety": SafetyRisk.IMMEDIATE,
     "reason": "Unconscious/unresponsive person reported"},

    # --- HIGH (serious threat, not necessarily happening this second) ---
    {"phrases": ["he threatened to kill me", "she threatened to kill me",
                 "death threat", "going to kill me", "wants to kill me"],
     "min_urgency": Urgency.HIGH, "min_safety": SafetyRisk.HIGH,
     "reason": "Death threat reported"},
    {"phrases": ["i was raped", "i've been raped", "sexual assault", "sexually assaulted",
                 "someone raped me"],
     "min_urgency": Urgency.HIGH, "min_safety": SafetyRisk.HIGH,
     "reason": "Sexual violence reported"},
    {"phrases": ["he has a gun", "she has a gun", "he has a knife", "she has a knife",
                 "weapon", "armed"],
     "min_urgency": Urgency.HIGH, "min_safety": SafetyRisk.HIGH,
     "reason": "Armed threat reported"},
    {"phrases": ["child in danger", "my child is hurt", "hurting my child",
                 "beating my child", "abusing my child"],
     "min_urgency": Urgency.HIGH, "min_safety": SafetyRisk.HIGH,
     "reason": "Child endangerment reported"},
    {"phrases": ["kidnapped", "being held", "locked in", "can't leave",
                 "won't let me leave", "trapped"],
     "min_urgency": Urgency.HIGH, "min_safety": SafetyRisk.HIGH,
     "reason": "Captivity/confinement reported"},
]


def check_crisis_keywords(message: str) -> dict | None:
    """Scan message for crisis keywords. Returns override dict or None.

    Returns:
        {
            "min_urgency": Urgency,
            "min_safety": SafetyRisk,
            "reasons": [str, ...],
            "immediate_danger": True  # if any critical rule fired
        }
        or None if no crisis keywords matched.
    """
    lower = message.lower()
    matched_reasons: list[str] = []
    highest_urgency = Urgency.STANDARD
    highest_safety = SafetyRisk.LOW

    urgency_order = [Urgency.STANDARD, Urgency.URGENT, Urgency.HIGH, Urgency.CRITICAL]
    safety_order = [SafetyRisk.LOW, SafetyRisk.MEDIUM, SafetyRisk.HIGH, SafetyRisk.IMMEDIATE]

    for rule in CRISIS_KEYWORD_RULES:
        for phrase in rule["phrases"]:
            if phrase in lower:
                matched_reasons.append(rule["reason"])
                rule_urg = rule["min_urgency"]
                rule_saf = rule["min_safety"]
                if urgency_order.index(rule_urg) > urgency_order.index(highest_urgency):
                    highest_urgency = rule_urg
                if safety_order.index(rule_saf) > safety_order.index(highest_safety):
                    highest_safety = rule_saf
                break  # only match first phrase per rule

    if not matched_reasons:
        return None

    return {
        "min_urgency": highest_urgency,
        "min_safety": highest_safety,
        "reasons": matched_reasons,
        "immediate_danger": highest_urgency == Urgency.CRITICAL,
    }


def normalize_urgency(value: str | None) -> str:
    """Normalize an urgency string to a valid enum value, defaulting to 'standard'."""
    if not value:
        return Urgency.STANDARD.value
    try:
        return Urgency(value.lower().strip()).value
    except ValueError:
        return Urgency.STANDARD.value


def normalize_safety_risk(value: str | None) -> str:
    """Normalize a safety_risk string to a valid enum value, defaulting to 'low'."""
    if not value:
        return SafetyRisk.LOW.value
    try:
        return SafetyRisk(value.lower().strip()).value
    except ValueError:
        return SafetyRisk.LOW.value


def normalize_primary_need(value: str | None) -> str | None:
    """Normalize a primary_need string to a valid enum value, or None."""
    if not value:
        return None
    # Try exact match first
    for need in PrimaryNeed:
        if value.strip().lower() == need.value.lower():
            return need.value
    # Try substring match for common variations
    lower = value.strip().lower()
    for need in PrimaryNeed:
        if lower in need.value.lower() or need.value.lower() in lower:
            return need.value
    return value  # pass through if no match — LLM may have a valid reason


def normalize_injury_status(value: str | None) -> str | None:
    """Normalize injury_status to a valid enum value, or None."""
    if not value:
        return None
    try:
        return InjuryStatus(value.lower().strip()).value
    except ValueError:
        lower = value.lower().strip()
        if "not" in lower or "no" in lower:
            return InjuryStatus.NOT_INJURED.value
        if "yes" in lower or "injur" in lower or "hurt" in lower:
            return InjuryStatus.INJURED.value
        return None


def normalize_contact_method(value: str | None) -> str | None:
    """Normalize contact_method to a valid enum value, or None."""
    if not value:
        return None
    try:
        return ContactMethod(value.lower().strip()).value
    except ValueError:
        lower = value.lower().strip()
        if "whats" in lower:
            return ContactMethod.WHATSAPP.value
        if "sms" in lower or "text" in lower:
            return ContactMethod.TEXT.value
        if "call" in lower or "phone" in lower:
            return ContactMethod.CALL.value
        if "email" in lower or "mail" in lower:
            return ContactMethod.EMAIL.value
        return value
