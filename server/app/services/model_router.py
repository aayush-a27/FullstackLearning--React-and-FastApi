"""
Smart Model Router — picks an AI model from the question itself.

Classification is a local heuristic, not an LLM call: routing used to spend a
whole extra API round-trip (and its latency and rate-limit budget) just to label
the question before answering it.
"""
import logging
import re
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Free models via litellm mapping (internal key -> litellm model name)
FREE_MODELS = {
    "groq-fast": "groq/openai/gpt-oss-20b",
    "gemini-flash": "gemini/gemini-flash-latest",
    "nemotron-super": "openai/nvidia/nemotron-3-super-120b-a12b",  # NVIDIA NIM (OpenAI-compatible)
}

# Which provider each internal key belongs to (used to pick API key / base URL)
MODEL_PROVIDERS = {
    "groq-fast": "groq",
    "gemini-flash": "google",
    "nemotron-super": "nvidia",
}

DEFAULT_MODEL = "groq-fast"

# Rough max context (in characters, ~4 chars/token) each model can take per request.
# Groq's limit is set by the free-tier tokens-per-minute cap, not the model's context window.
MODEL_MAX_CONTEXT_CHARS = {
    "groq-fast": 24_000,           # ~6k tokens (free tier TPM cap)
    "gemini-flash": 2_000_000,     # ~500k tokens of a 1M window
    "nemotron-super": 300_000,     # ~75k tokens of a 128k window
}

# Mapping from complexity to preferred model tier
COMPLEXITY_TO_MODEL = {
    "simple": "groq-fast",         # Groq is fastest and free
    "moderate": "gemini-flash",    # Fast, free, larger context
    "complex": "nemotron-super",   # Best reasoning of the free models
}

DEFAULT_FALLBACK_CHAIN = [
    "nemotron-super",
    "gemini-flash",
    "groq-fast",
]

# Old model IDs that may still be stored on chats or sent by an old client
LEGACY_MODEL_IDS = {
    "groq-llama3": "groq-fast",
    "gemini-pro": "gemini-flash",
    "gpt-4o": "nemotron-super",
    "gpt-4o-mini": "groq-fast",
    "claude-sonnet": "nemotron-super",
    "llama-local": "groq-fast",
}

# --- Heuristic classification ----------------------------------------------

# Deep reasoning, multi-step work, or writing at length
COMPLEX_PATTERNS = re.compile(
    r"\b(analys|analyz|compar|contrast|evaluat|critiq|assess|implic|"
    r"why\s+(?:do|does|did|is|are|was|were)|reason(?:ing)?\b|argue|argument|"
    r"step[-\s]by[-\s]step|in\s+detail|detailed|comprehensive|thorough|"
    r"pros\s+and\s+cons|trade[-\s]?offs?|strengths?\s+and\s+weakness|"
    r"write\s+(?:an?\s+)?(?:essay|report|article)|draft|rewrite|"
    r"code|implement|debug|refactor|algorithm|derive|prove)",
    re.IGNORECASE,
)

# Summarizing / synthesizing a chunk of material
MODERATE_PATTERNS = re.compile(
    r"\b(summar|overview|outline|key\s+points?|main\s+(?:points?|ideas?|themes?)|"
    r"explain|describe|how\s+does|how\s+do|what\s+happens|walk\s+me\s+through|"
    r"list\s+all|timeline)",
    re.IGNORECASE,
)

# Short factual lookups and chit-chat
SIMPLE_PATTERNS = re.compile(
    r"^\s*(hi|hey|hello|thanks|thank\s+you|ok(?:ay)?|yes|no|sure|cool|"
    r"who\s+is|who\s+was|what\s+is\s+the\s+name|when\s+(?:is|was|did)|"
    r"where\s+(?:is|was)|how\s+many|how\s+much|define|spell)\b",
    re.IGNORECASE,
)

# Questions about the document as a whole, which retrieval alone can't answer
SUMMARY_INTENT_PATTERNS = re.compile(
    r"\b(summar(?:y|ise|ize|izing|ising)|tl;?dr|overview\s+of\s+(?:the\s+)?(?:doc|book|pdf|file|paper|report)|"
    r"what(?:'s| is)\s+(?:this|the)\s+(?:doc(?:ument)?|book|pdf|file|paper|report)\s+about|"
    r"what\s+is\s+it\s+about|tell\s+me\s+about\s+(?:this|the)\s+(?:doc(?:ument)?|book|pdf|file|paper|report)|"
    r"main\s+(?:points?|ideas?|themes?|takeaways?)|key\s+takeaways?|"
    r"outline\s+(?:of\s+)?(?:this|the)\b|overall\s+(?:theme|structure|argument))",
    re.IGNORECASE,
)

# Above this much context, a small model can't do the job well
LARGE_CONTEXT_CHARS = 20_000
LONG_QUESTION_WORDS = 40


def normalize_model_id(model_id: str | None) -> str | None:
    """Map legacy/unknown model IDs to a current internal key."""
    if not model_id:
        return None
    model_id = LEGACY_MODEL_IDS.get(model_id, model_id)
    return model_id if model_id in FREE_MODELS else None


def get_provider_credentials(model_id: str) -> tuple[str, str | None]:
    """Return (api_key, api_base) for an internal model key."""
    provider = MODEL_PROVIDERS.get(model_id)
    if provider == "groq":
        return settings.GROQ_API_KEY, None
    if provider == "google":
        return settings.GOOGLE_API_KEY, None
    if provider == "nvidia":
        return settings.NEMOTRON_API_KEY, settings.NVIDIA_BASE_URL
    return "", None


def is_summary_question(question: str) -> bool:
    """True when the user is asking about the document as a whole."""
    return bool(SUMMARY_INTENT_PATTERNS.search(question or ""))


def classify_complexity(question: str, context_len: int = 0) -> str:
    """
    Classify question complexity locally: 'simple' | 'moderate' | 'complex'.
    No API call — this runs in microseconds.
    """
    question = (question or "").strip()
    if not question:
        return "simple"

    word_count = len(question.split())

    if COMPLEX_PATTERNS.search(question) or word_count > LONG_QUESTION_WORDS:
        return "complex"
    if context_len >= LARGE_CONTEXT_CHARS:
        # A lot of material to synthesize, even for a plainly worded question
        return "complex"
    if MODERATE_PATTERNS.search(question):
        return "moderate"
    if SIMPLE_PATTERNS.search(question) or word_count <= 8:
        return "simple"
    return "moderate"


def select_model(
    question: str,
    user_selected_model: str | None = None,
    smart_switch_enabled: bool = True,
    context_len: int = 0,
    fallback_chain: list[str] | None = None,
) -> str:
    """
    Select the best model ID for a question.
    Returns the internal model key (e.g. 'groq-fast').
    """
    chain = fallback_chain or DEFAULT_FALLBACK_CHAIN
    user_selected_model = normalize_model_id(user_selected_model)

    if not smart_switch_enabled and user_selected_model:
        return user_selected_model

    if smart_switch_enabled:
        complexity = classify_complexity(question, context_len)
        return COMPLEXITY_TO_MODEL.get(complexity, "gemini-flash")

    return chain[-1] if chain else DEFAULT_MODEL
