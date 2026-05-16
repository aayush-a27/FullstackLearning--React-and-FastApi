"""
AI Service — Multi-model LLM integration.
This is a placeholder that defines the interface.
Actual LLM integration will be implemented when API keys are configured.
"""


class AIService:
    """Service for interacting with multiple AI models."""

    def __init__(self):
        self.providers = {}

    async def get_response(
        self,
        model_id: str,
        messages: list[dict],
        pdf_context: str = "",
    ) -> str:
        """
        Get an AI response for the given messages and PDF context.

        Args:
            model_id: The AI model to use (e.g., 'gpt-4o', 'gemini-pro')
            messages: Conversation history as list of {role, content} dicts
            pdf_context: Extracted text from the PDF for context

        Returns:
            AI response text
        """
        # TODO: Implement actual LLM API calls
        # For now, return a placeholder response
        return (
            "🤖 **AI Response Placeholder**\n\n"
            f"I received your message and I'm using the **{model_id}** model.\n\n"
            f"PDF context length: {len(pdf_context)} characters.\n\n"
            "This is a placeholder — actual AI integration will be configured "
            "once API keys are set in the `.env` file."
        )

    async def check_model_health(self, provider: str) -> str:
        """
        Check if an AI provider's API is healthy.

        Returns: 'healthy' | 'degraded' | 'down'
        """
        # TODO: Implement actual health checks
        return "healthy"


# Singleton instance
ai_service = AIService()
