class ResponseAssemblyService:
    """Kept for backward compatibility. Response generation is now handled by the LLM."""

    @staticmethod
    def opening_message() -> str:
        return "I'm here to help. You're safe to share what's happening, and I'll do my best to connect you with the right support."

    @staticmethod
    def emergency_message(queue: str | None) -> str:
        if queue:
            return f"This sounds urgent. I'm escalating this now to {queue}. While that happens, I need a few more details."
        return "This sounds urgent. I'm escalating this now and I need a few more details."

    @staticmethod
    def standard_message(question: str) -> str:
        return question
