from services.intake_service import IntakeParseResult


class EscalationService:
    @staticmethod
    def assess_escalation(triage: dict, parsed: IntakeParseResult) -> dict:
        actions: list[dict] = []
        escalate = False
        level = "none"
        queue = None
        handoff_required = False

        urgency = triage.get("urgency", "standard")
        safety_risk = triage.get("safety_risk", "low")
        incident_types = triage.get("incident_types", [])

        if urgency == "critical" or safety_risk == "immediate":
            escalate = True
            level = "critical"
            queue = "emergency_response"
            handoff_required = True
            actions.append(
                {
                    "action": "Immediate escalation to emergency response",
                    "target": "emergency_response",
                    "priority": "critical",
                    "reason": "Critical urgency or immediate safety risk detected",
                }
            )

        elif safety_risk == "high":
            escalate = True
            level = "high"
            queue = "human_case_worker"
            handoff_required = True
            actions.append(
                {
                    "action": "Escalate to human case worker",
                    "target": "human_case_worker",
                    "priority": "high",
                    "reason": "High safety risk detected",
                }
            )

        elif urgency == "urgent":
            escalate = True
            level = "urgent"
            queue = "priority_support_queue"
            actions.append(
                {
                    "action": "Route to priority support queue",
                    "target": "priority_support_queue",
                    "priority": "urgent",
                    "reason": "Urgent support need detected",
                }
            )

        if "Domestic Violence" in incident_types or "Assault" in incident_types:
            actions.append(
                {
                    "action": "Prioritize safety planning and legal support review",
                    "target": "safety_review",
                    "priority": "high",
                    "reason": "Violence-related incident inferred",
                }
            )

        if "No Transport" in parsed.normalized_barriers:
            actions.append(
                {
                    "action": "Flag transport barrier for mitigation",
                    "target": "transport_support",
                    "priority": "medium",
                    "reason": "Transport barrier may block access to primary support",
                }
            )

        if "Emergency Shelter" in parsed.primary_needs:
            actions.append(
                {
                    "action": "Check shelter availability immediately",
                    "target": "shelter_coordination",
                    "priority": "urgent",
                    "reason": "Emergency shelter need detected",
                }
            )

        if "Protection Order Support" in parsed.primary_needs:
            actions.append(
                {
                    "action": "Route to legal protection support",
                    "target": "legal_support",
                    "priority": "urgent",
                    "reason": "Protection order support needed",
                }
            )

        return {
            "escalate": escalate,
            "level": level,
            "queue": queue,
            "handoff_required": handoff_required,
            "actions": actions,
        }