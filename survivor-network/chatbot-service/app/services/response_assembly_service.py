class ResponseAssemblyService:
    @staticmethod
    def opening_message() -> str:
        return "I’m here to help. Tell me what happened, and I’ll guide you step by step."

    @staticmethod
    def emergency_message(queue: str | None) -> str:
        if queue:
            return f"This sounds urgent. I’m escalating this now to {queue}. While that happens, I need a few more details."
        return "This sounds urgent. I’m escalating this now and I need a few more details."

    @staticmethod
    def standard_message(question: str) -> str:
        return question