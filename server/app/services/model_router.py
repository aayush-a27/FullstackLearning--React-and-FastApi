"""
Smart Model Router — Auto-selects AI model based on question complexity
and falls back to alternative models if a provider is down.
"""

from app.core.redis import cache_get, cache_set


# Fallback chain: ordered from most capable to least
DEFAULT_FALLBACK_CHAIN = [
    "gpt-4o",
    "gemini-pro",
    "claude-sonnet",
    "gpt-4o-mini",
    "llama-local",
]

# Simple heuristics for complexity detection
COMPLEX_KEYWORDS = [
    "analyze", "compare", "contrast", "evaluate", "synthesize",
    "explain in detail", "deep dive", "critically", "implications",
    "pros and cons", "trade-offs", "architecture", "design",
]

SIMPLE_KEYWORDS = [
    "what is", "define", "list", "who", "when", "where",
    "how many", "name", "true or false",
]


def classify_complexity(question: str) -> str:
    """
    Classify the complexity of a question.

    Returns: 'simple' | 'moderate' | 'complex'
    """
    question_lower = question.lower()
    word_count = len(question.split())

    # Complex: long questions with analytical keywords
    if any(kw in question_lower for kw in COMPLEX_KEYWORDS) or word_count > 50:
        return "complex"

    # Simple: short factual questions
    if any(kw in question_lower for kw in SIMPLE_KEYWORDS) and word_count < 20:
        return "simple"

    return "moderate"


# Mapping from complexity to preferred model tier
COMPLEXITY_TO_MODEL = {
    "simple": "gpt-4o-mini",      # Fast and cheap for simple questions
    "moderate": "gemini-pro",      # Balanced for moderate questions
    "complex": "gpt-4o",           # Most capable for complex analysis
}


async def select_model(
    question: str,
    user_selected_model: str | None = None,
    smart_switch_enabled: bool = True,
    fallback_chain: list[str] | None = None,
) -> str:
    """
    Select the best model for a question.

    If smart switch is disabled, returns the user's selected model.
    If smart switch is enabled, selects based on complexity and availability.
    """
    chain = fallback_chain or DEFAULT_FALLBACK_CHAIN

    if not smart_switch_enabled and user_selected_model:
        # Check if user's model is healthy
        status = await cache_get(f"model_status:{user_selected_model}")
        if status != "down":
            return user_selected_model
        # If down, fall through to fallback

    if smart_switch_enabled:
        complexity = classify_complexity(question)
        preferred = COMPLEXITY_TO_MODEL.get(complexity, "gpt-4o")

        # Check if preferred model is healthy
        status = await cache_get(f"model_status:{preferred}")
        if status != "down":
            return preferred

    # Fallback: find first healthy model
    for model_id in chain:
        status = await cache_get(f"model_status:{model_id}")
        if status != "down":
            return model_id

    # Last resort
    return chain[-1] if chain else "gpt-4o-mini"
