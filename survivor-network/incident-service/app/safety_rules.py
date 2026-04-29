"""Deterministic safety normalization rules.

No LLM dependency. No FastAPI dependency. Pure logic.
Used by /cases/from-intake to classify and boost case urgency/risk.

Urgency levels: standard, medium, urgent, critical
Safety risk levels: low, medium, high, immediate
"""

# Pattern rules ordered by specificity — first match per rule wins
_SAFETY_RULES: list[dict] = [
    # --- CRITICAL / IMMEDIATE ---
    # DV active attack (above generic attack for specificity)
    {"phrases": ["husband is beating", "partner is hitting", "husband is hitting", "wife is hitting",
                 "boyfriend is beating", "partner is beating", "beating me right now", "locked myself in"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Domestic Violence",
     "needs": ["Emergency Shelter", "Protection Order Support"]},
    {"phrases": ["stabbed", "stabbing", "bleeding heavily", "bleeding badly"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Assault",
     "needs": ["Emergency Medical"]},
    {"phrases": ["unconscious", "not breathing", "no pulse"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Medical Emergency",
     "needs": ["Emergency Medical"]},
    {"phrases": ["building collapse", "trapped under", "people are trapped", "flood", "fire and"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Disaster / Emergency",
     "needs": ["Emergency Medical"]},
    {"phrases": ["overdose", "took too many pills", "swallowed pills", "poisoned"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Mental Health Crisis",
     "needs": ["Emergency Medical", "Mental Health Support"]},
    {"phrases": ["kill myself", "want to die", "end my life", "suicidal", "self-harm"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Mental Health Crisis",
     "needs": ["Emergency Medical", "Mental Health Support"]},
    {"phrases": ["being attacked", "attacking me", "hitting me right now"],
     "urgency": "critical", "safety_risk": "immediate", "incident_type": "Assault",
     "needs": ["Emergency Medical", "Emergency Shelter"]},
    # --- URGENT / HIGH ---
    {"phrases": ["raped", "i was raped", "sexual assault", "sexually assaulted"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Sexual Assault",
     "needs": ["Emergency Medical", "Mental Health Support"]},
    {"phrases": ["domestic violence", "partner hit me", "husband hit me", "abusive partner",
                 "wife hit me", "boyfriend hit me"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Domestic Violence",
     "needs": ["Emergency Shelter", "Protection Order Support"]},
    {"phrases": ["knife", "gun", "weapon", "armed"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Assault",
     "needs": ["Emergency Shelter"]},
    {"phrases": ["kidnap", "abducted", "locked in", "trapped", "won't let me leave"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Child Endangerment",
     "needs": ["Emergency Shelter"]},
    {"phrases": ["hijack", "carjack"],
     "urgency": "urgent", "safety_risk": "high", "incident_type": "Hijacking",
     "needs": ["Emergency Medical", "Transport Support"]},
    # --- URGENT / MEDIUM ---
    {"phrases": ["arv", "hiv medication", "antiretroviral", "ran out of medication", "need my medication", "medication stolen"],
     "urgency": "urgent", "safety_risk": "medium", "incident_type": "Medication Access",
     "needs": ["Medication Access"]},
    {"phrases": ["need shelter", "nowhere to stay", "kicked me out", "homeless"],
     "urgency": "urgent", "safety_risk": "medium", "incident_type": "Domestic Violence",
     "needs": ["Emergency Shelter"]},
    # --- MEDIUM ---
    {"phrases": ["mugged", "robbed", "robbery", "stolen my"],
     "urgency": "medium", "safety_risk": "medium", "incident_type": "Robbery",
     "needs": ["Transport Support"]},
    {"phrases": ["counselling", "counseling", "trauma", "panic attack", "can't cope", "can't sleep"],
     "urgency": "medium", "safety_risk": "low", "incident_type": "Mental Health Crisis",
     "needs": ["Mental Health Support"]},
    {"phrases": ["protection order", "restraining order", "legal help"],
     "urgency": "medium", "safety_risk": "medium", "incident_type": "Protection Order",
     "needs": ["Protection Order Support"]},
    {"phrases": ["break-in", "broke into", "burglary"],
     "urgency": "medium", "safety_risk": "medium", "incident_type": "Break-in",
     "needs": ["Protection Order Support"]},
    {"phrases": ["stranded", "no transport", "need a ride", "can't get home"],
     "urgency": "medium", "safety_risk": "low", "incident_type": "Transport Support",
     "needs": ["Transport Support"]},
]

URGENCY_ORDER = ["standard", "medium", "urgent", "critical"]
SAFETY_ORDER = ["low", "medium", "high", "immediate"]


def normalize_case_safety(
    message_lower: str,
    incoming_urgency: str,
    incoming_safety_risk: str,
    incoming_needs: list[str],
    incoming_incident_type: str | None,
    immediate_danger: bool,
) -> tuple[str, str, list[str], str | None]:
    """Apply deterministic safety rules. Returns (urgency, safety_risk, needs, incident_type)."""

    urgency = incoming_urgency if incoming_urgency in URGENCY_ORDER else "medium"
    safety_risk = incoming_safety_risk if incoming_safety_risk in SAFETY_ORDER else "low"
    needs: set[str] = set(n for n in incoming_needs if n)
    incident_type = incoming_incident_type

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
                break

    if immediate_danger:
        if URGENCY_ORDER.index(urgency) < URGENCY_ORDER.index("critical"):
            urgency = "critical"
        if SAFETY_ORDER.index(safety_risk) < SAFETY_ORDER.index("immediate"):
            safety_risk = "immediate"

    if URGENCY_ORDER.index(urgency) >= URGENCY_ORDER.index("urgent") and not needs:
        needs.add("Emergency Support")

    return urgency, safety_risk, sorted(needs), incident_type
