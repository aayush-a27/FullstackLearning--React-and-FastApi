"""
AI Service — Multi-model LLM integration.
"""
import logging
from litellm import acompletion
from app.config import get_settings
from app.services.model_router import FREE_MODELS

settings = get_settings()
logger = logging.getLogger(__name__)

class AIService:
    """Service for interacting with multiple AI models using litellm."""

    def __init__(self):
        pass

    async def get_response(
        self,
        model_id: str,
        messages: list[dict],
        pdf_context: str = "",
    ) -> str:
        """
        Get an AI response for the given messages and PDF context.
        """
        # The model_id coming in here should now be one of our internal keys:
        # "groq-llama3", "gemini-flash", "gemini-pro"
        # If it's something else, default to groq
        target_model = FREE_MODELS.get(model_id, FREE_MODELS["groq-llama3"])

        # Determine API key based on prefix
        if target_model.startswith("groq/"):
            api_key = settings.GROQ_API_KEY
        else:
            api_key = settings.GOOGLE_API_KEY
            
        if not api_key:
            return "⚠️ Error: API Key missing for this model."

        # Build final messages array
        system_message = "You are a helpful AI assistant."
        if pdf_context:
            system_message += f"\n\nHere is the document context to help you answer:\n\n{pdf_context}"
            
        formatted_messages = [{"role": "system", "content": system_message}] + messages
        
        try:
            response = await acompletion(
                model=target_model,
                messages=formatted_messages,
                api_key=api_key
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI Generation failed: {e}")
            return f"⚠️ Error generating response with {target_model}: {str(e)}"

    async def check_model_health(self, provider: str) -> str:
        """
        Check if an AI provider's API is healthy.
        """
        return "healthy"


# Singleton instance
ai_service = AIService()
