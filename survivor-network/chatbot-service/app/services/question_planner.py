class QuestionPlanner:
    """Kept for backward compatibility. Question generation is now handled by the LLM."""

    @staticmethod
    def next_question(missing_fields: list[str]) -> str:
        if not missing_fields:
            return "Thank you. I have enough information to continue with your case."
        return ""
