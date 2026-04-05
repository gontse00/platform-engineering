class QuestionPlanner:
    QUESTIONS = {
        "immediate_danger": "Are you in immediate danger right now?",
        "injury_status": "Are you injured or bleeding right now?",
        "location": "What area are you in right now?",
        "primary_need": "What do you need most right now: medical help, shelter, legal help, or someone to talk to?",
        "safe_contact_method": "What is the safest way to contact you: text or phone call?",
        "incident_summary": "Please briefly tell me what happened.",
    }

    @staticmethod
    def next_question(missing_fields: list[str]) -> str:
        if not missing_fields:
            return "Thank you. I have enough information to continue with your case."
        field = missing_fields[0]
        return QuestionPlanner.QUESTIONS.get(field, "Please tell me more.")