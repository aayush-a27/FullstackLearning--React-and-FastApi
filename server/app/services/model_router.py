"""
Smart Model Router — Auto-selects AI model based on question complexity
using Groq, and falls back to alternative models.
"""
import json
import logging
from litellm import acompletion
from app.config import get_settings
from app.core.redis import cache_get, cache_set

logger = logging.getLogger(__name__)
settings = get_settings()

# Free models via litellm mapping
FREE_MODELS = {
    "groq-llama3": "groq/llama-3.1-8b-instant",
    "gemini-flash": "gemini/gemini-2.5-flash",
    "gemini-pro": "gemini/gemini-2.5-pro",
}

# Mapping from complexity to preferred model tier
COMPLEXITY_TO_MODEL = {
    "simple": "groq-llama3",     # Groq is fastest and free
    "moderate": "gemini-flash",  # Fast, free, larger context
    "complex": "gemini-pro",     # Best reasoning, free tier available
}

DEFAULT_FALLBACK_CHAIN = [
    "gemini-pro",
    "gemini-flash",
    "groq-llama3"
]

async def classify_complexity(question: str, pdf_context: str = "") -> str:
    """
    Classify the complexity of a question using Groq Llama3.
    Returns: 'simple' | 'moderate' | 'complex'
    """
    system_prompt = (
        "You are an efficient routing AI. Classify the user's question complexity.\n"
        "Return ONLY a JSON object: {\"complexity\": \"simple\"} OR {\"complexity\": \"moderate\"} OR {\"complexity\": \"complex\"}\n"
        "simple: Basic facts, greetings, short questions.\n"
        "moderate: Summaries, basic analysis.\n"
        "complex: Deep reasoning, coding, long document synthesis."
    )
    
    try:
        if not settings.GROQ_API_KEY:
            return "moderate" # Fallback if no key

        response = await acompletion(
            model=FREE_MODELS["groq-llama3"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question: {question}\nContext Length: {len(pdf_context)}"}
            ],
            api_key=settings.GROQ_API_KEY,
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        data = json.loads(result)
        return data.get("complexity", "moderate").lower()
    except Exception as e:
        logger.error(f"Router AI failed: {e}")
        return "moderate" # Fallback


async def select_model(
    question: str,
    user_selected_model: str | None = None,
    smart_switch_enabled: bool = True,
    fallback_chain: list[str] | None = None,
) -> str:
    """
    Select the best model ID for a question.
    Returns the internal model key (e.g. 'groq-llama3')
    """
    chain = fallback_chain or DEFAULT_FALLBACK_CHAIN

    # Map frontend hardcoded IDs to our free models if they pass them directly
    frontend_map = {
        "gpt-4o": "gemini-pro",
        "gpt-4o-mini": "groq-llama3",
        "gemini-pro": "gemini-pro",
        "claude-sonnet": "gemini-pro",
        "llama-local": "groq-llama3",
    }
    
    if user_selected_model in frontend_map:
        user_selected_model = frontend_map[user_selected_model]

    if not smart_switch_enabled and user_selected_model:
        return user_selected_model

    if smart_switch_enabled:
        complexity = await classify_complexity(question)
        preferred = COMPLEXITY_TO_MODEL.get(complexity, "gemini-flash")
        return preferred

    # Last resort
    return chain[-1] if chain else "groq-llama3"
