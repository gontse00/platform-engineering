import re

from services.intake_service import IntakeParseResult


class TriageService:
    CRITICAL_PATTERNS = [
        r"\bbleeding\b",
        r"\bunconscious\b",
        r"\bnot breathing\b",
        r"\bsevere injury\b",
        r"\bdying\b",
        r"\bheart attack\b",
        r"\bstroke\b",
    ]

    HIGH_RISK_PATTERNS = [
        r"\bassault\b",
        r"\bassaulted\b",
        r"\battacked\b",
        r"\bviolence\b",
        r"\bdomestic violence\b",
        r"\bthreatened\b",
        r"\bunsafe\b",
        r"\bnot safe\b",
        r"\btrafficking\b",
        r"\bchild in danger\b",
        r"\bscared to go home\b",
        r"\bpartner threatened me\b",
        r"\babusive partner\b",
        r"\bi am scared\b",
    ]

    URGENT_PATTERNS = [
        r"\bneed shelter tonight\b",
        r"\bnowhere to sleep\b",
        r"\bno medication\b",
        r"\bpanic\b",
        r"\bprotection order\b",
        r"\bneed legal help\b",
        r"\btraumatized\b",
        r"\btraumatised\b",
        r"\bneed someone to talk to\b",
        r"\bneed to talk to someone\b",
        r"\boverwhelmed\b",
        r"\bemotional support\b",
        r"\bcrisis support\b",
    ]

    INCIDENT_PATTERNS: dict[str, list[str]] = {
        "Assault": [
            r"\bassault\b",
            r"\bassaulted\b",
            r"\battacked\b",
            r"\bbeaten\b",
        ],
        "Domestic Violence": [
            r"\bdomestic violence\b",
            r"\babusive partner\b",
            r"\babuse at home\b",
            r"\bpartner threatened me\b",
        ],
        "Displacement": [
            r"\bevicted\b",
            r"\bdisplaced\b",
            r"\bnowhere to stay\b",
        ],
        "Missing Medication": [
            r"\bno medication\b",
            r"\bout of medicine\b",
            r"\bmissed prescription\b",
        ],
        "Child Endangerment": [
            r"\bchild in danger\b",
            r"\bunsafe child\b",
        ],
        "Threats": [
            r"\bthreatened\b",
            r"\bthreatened me\b",
        ],
    }

    @staticmethod
    def _detect_incident_types(message: str) -> list[str]:
        found: list[str] = []
        for incident_type, patterns in TriageService.INCIDENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message, flags=re.IGNORECASE):
                    found.append(incident_type)
                    break
        return sorted(set(found))

    @staticmethod
    def assess_triage(message: str, parsed: IntakeParseResult) -> dict:
        text = message.strip()
        rationale: list[str] = []
        urgency = "standard"
        safety_risk = "low"
        escalation_recommended = False
        escalation_target = None
        requires_human_review = False

        incident_types = TriageService._detect_incident_types(text)

        if any(re.search(p, text, flags=re.IGNORECASE) for p in TriageService.CRITICAL_PATTERNS):
            urgency = "critical"
            safety_risk = "immediate"
            escalation_recommended = True
            escalation_target = "emergency_response"
            requires_human_review = True
            rationale.append("Critical medical risk language detected.")

        elif any(re.search(p, text, flags=re.IGNORECASE) for p in TriageService.HIGH_RISK_PATTERNS):
            urgency = "high"
            safety_risk = "high"
            escalation_recommended = True
            escalation_target = "human_case_worker"
            requires_human_review = True
            rationale.append("High-risk safety language detected.")

        elif any(re.search(p, text, flags=re.IGNORECASE) for p in TriageService.URGENT_PATTERNS):
            urgency = "urgent"
            safety_risk = "medium"
            escalation_recommended = True
            escalation_target = "priority_support_queue"
            rationale.append("Urgent support language detected.")

        if "Emergency Medical" in parsed.primary_needs and urgency == "standard":
            urgency = "urgent"
            rationale.append("Emergency Medical need detected.")

        if "Emergency Shelter" in parsed.primary_needs and urgency == "standard":
            urgency = "urgent"
            rationale.append("Emergency Shelter need detected.")

        if "Mental Health Support" in parsed.primary_needs and urgency == "standard":
            urgency = "urgent"
            safety_risk = "medium"
            escalation_recommended = True
            escalation_target = "priority_support_queue"
            rationale.append("Mental Health Support need detected.")   

        if parsed.normalized_barriers:
            rationale.append(f"Barriers detected: {', '.join(parsed.normalized_barriers)}")

        if parsed.normalized_location:
            rationale.append(f"Location identified: {parsed.normalized_location}")

        if incident_types:
            rationale.append(f"Incident types inferred: {', '.join(incident_types)}")

        return {
            "urgency": urgency,
            "safety_risk": safety_risk,
            "incident_types": incident_types,
            "requires_human_review": requires_human_review,
            "escalation_recommended": escalation_recommended,
            "escalation_target": escalation_target,
            "rationale": rationale,
        }