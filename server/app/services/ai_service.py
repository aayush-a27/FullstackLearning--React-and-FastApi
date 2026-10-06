"""
AI Service — Multi-model LLM integration with automatic fallback and streaming.
"""
import logging
from collections.abc import AsyncIterator
import httpx
from litellm import acompletion
from redis.exceptions import RedisError
from app.config import get_settings
from app.core.redis import cache_get, cache_set
from app.services.model_router import (
    FREE_MODELS,
    MODEL_PROVIDERS,
    MODEL_MAX_CONTEXT_CHARS,
    DEFAULT_MODEL,
    DEFAULT_FALLBACK_CHAIN,
    normalize_model_id,
    get_provider_credentials,
)

settings = get_settings()
logger = logging.getLogger(__name__)

# Per-model request timeout (seconds) — a slow model falls through to the next one
MODEL_TIMEOUT_SECONDS = 45
# Summaries run in the background over large inputs, so they get longer
SUMMARY_TIMEOUT_SECONDS = 180

# How long a runtime failure marks a provider as "degraded" in the health dots
DEGRADED_TTL_SECONDS = 300
# How long a successful/failed API-key check is cached
HEALTH_CHECK_TTL_SECONDS = 300

# Cheap "is the key valid and the API reachable" endpoints per provider
PROVIDER_HEALTH_URLS = {
    "groq": "https://api.groq.com/openai/v1/models",
    "google": "https://generativelanguage.googleapis.com/v1beta/models",
    "nvidia": f"{settings.NVIDIA_BASE_URL}/models",
}

# Shown to end users — never include provider error details here
FRIENDLY_BUSY_MESSAGE = (
    "Our AI models are busy right now and couldn't answer. "
    "Please try again in a moment."
)
FRIENDLY_NOT_CONFIGURED_MESSAGE = "The AI service isn't available right now. Please try again later."

# Formatting rules — responses are rendered as GitHub-flavored Markdown in the chat UI
SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions about the user's PDF documents.

Format every answer as clean, easy-to-scan Markdown:
- Start with a one or two sentence direct answer, then add detail only if it helps.
- Use short `##` or `###` headings to separate sections in longer answers.
- Use bullet points or numbered lists for multiple items; keep each bullet to one idea.
- Bold only the key terms, not whole sentences.
- Leave a blank line between paragraphs, headings and lists.
- Use a table only for genuinely tabular data (e.g. comparing items across the same attributes), keep cells short, and never put lists or line breaks inside table cells.
- Never use HTML tags such as <br>; use Markdown only.
- Keep answers concise; don't repeat the question or pad with filler."""

SUMMARY_SYSTEM_PROMPT = """You summarize long documents accurately and concisely.

- Capture the key facts, events, arguments and conclusions in the text you are given.
- Stay faithful to the source; never invent details that are not present.
- Write in clean Markdown prose with short paragraphs; use bullet points only for genuine lists.
- Do not add a preamble such as "Here is a summary"; start directly with the content."""


class AIServiceError(Exception):
    """Raised when no model could answer. The message is safe to show to end users."""


def _candidate_models(model_id: str, context_len: int) -> list[str]:
    """
    Order of models to try: the selected one first, then the fallback chain.
    Models whose context limit is too small for the context are skipped; if none
    fit, use the one with the largest limit (the context gets truncated for it).
    """
    order = [model_id] + [m for m in DEFAULT_FALLBACK_CHAIN if m != model_id]
    fits = [m for m in order if MODEL_MAX_CONTEXT_CHARS[m] >= context_len]
    return fits or [max(order, key=lambda m: MODEL_MAX_CONTEXT_CHARS[m])]


def build_system_message(context: str, max_chars: int) -> str:
    """System prompt plus the retrieved document context, truncated if needed."""
    system_message = SYSTEM_PROMPT
    if context:
        truncated = len(context) > max_chars
        system_message += (
            "\n\nUse the document excerpts below to answer. Each excerpt is labelled "
            "with its file name and page numbers. Cite the page numbers you relied on, "
            "inline and in brackets, like (page 42). If the excerpts don't contain the "
            "answer, say so instead of guessing."
        )
        if truncated:
            system_message += " Note: some excerpts were cut off for length."
        system_message += f"\n\n<excerpts>\n{context[:max_chars]}\n</excerpts>"
    return system_message


async def _record_provider_status(provider: str, status: str):
    """Remember the last real request's outcome so the health dots reflect it. Best-effort."""
    try:
        await cache_set(f"model_health:runtime:{provider}", status, DEGRADED_TTL_SECONDS)
    except (RuntimeError, RedisError):
        pass


class AIService:
    """Service for interacting with multiple AI models using litellm."""

    async def _complete(
        self,
        messages: list[dict],
        context: str,
        preferred_model: str,
        system_prompt_builder=build_system_message,
        timeout: int = MODEL_TIMEOUT_SECONDS,
    ) -> tuple[str, str]:
        """Try each candidate model in turn. Returns (content, model_id_used)."""
        candidates = _candidate_models(preferred_model, len(context))
        tried_any = False

        for candidate in candidates:
            api_key, api_base = get_provider_credentials(candidate)
            if not api_key:
                logger.warning("Skipping %s: no API key configured", candidate)
                continue
            tried_any = True
            provider = MODEL_PROVIDERS[candidate]
            system_message = system_prompt_builder(
                context, MODEL_MAX_CONTEXT_CHARS[candidate]
            )

            try:
                response = await acompletion(
                    model=FREE_MODELS[candidate],
                    messages=[{"role": "system", "content": system_message}] + messages,
                    api_key=api_key,
                    api_base=api_base,
                    timeout=timeout,
                    num_retries=0,
                )
                content = (response.choices[0].message.content or "").strip()
                if not content:
                    raise ValueError("Model returned an empty response")
            except Exception as e:
                # Full details go to the server log only — never to the user
                logger.warning("Model %s failed (%s): %s", candidate, type(e).__name__, e)
                await _record_provider_status(provider, "degraded")
                continue

            if candidate != preferred_model:
                logger.info("Fell back from %s to %s", preferred_model, candidate)
            await _record_provider_status(provider, "healthy")
            return content, candidate

        if not tried_any:
            raise AIServiceError(FRIENDLY_NOT_CONFIGURED_MESSAGE)
        raise AIServiceError(FRIENDLY_BUSY_MESSAGE)

    async def get_response(
        self,
        model_id: str,
        messages: list[dict],
        pdf_context: str = "",
    ) -> tuple[str, str]:
        """
        Get an AI response, falling back to other models if the chosen one fails.
        Returns (response_text, model_id_actually_used).
        Raises AIServiceError (with a user-safe message) if every model fails.
        """
        model_id = normalize_model_id(model_id) or DEFAULT_MODEL
        return await self._complete(messages, pdf_context, model_id)

    async def stream_response(
        self,
        model_id: str,
        messages: list[dict],
        pdf_context: str = "",
    ) -> AsyncIterator[tuple[str, str]]:
        """
        Stream an AI response as ("model", model_id) followed by ("delta", text) events.

        Fallback only applies before the first token arrives: once the user has
        seen part of an answer, switching models mid-sentence would be worse than
        surfacing the failure.
        """
        model_id = normalize_model_id(model_id) or DEFAULT_MODEL
        candidates = _candidate_models(model_id, len(pdf_context))
        tried_any = False

        for candidate in candidates:
            api_key, api_base = get_provider_credentials(candidate)
            if not api_key:
                logger.warning("Skipping %s: no API key configured", candidate)
                continue
            tried_any = True
            provider = MODEL_PROVIDERS[candidate]
            system_message = build_system_message(
                pdf_context, MODEL_MAX_CONTEXT_CHARS[candidate]
            )
            started = False

            try:
                stream = await acompletion(
                    model=FREE_MODELS[candidate],
                    messages=[{"role": "system", "content": system_message}] + messages,
                    api_key=api_key,
                    api_base=api_base,
                    timeout=MODEL_TIMEOUT_SECONDS,
                    num_retries=0,
                    stream=True,
                )
                async for part in stream:
                    delta = part.choices[0].delta
                    piece = getattr(delta, "content", None)
                    if not piece:
                        continue
                    if not started:
                        started = True
                        await _record_provider_status(provider, "healthy")
                        yield "model", candidate
                    yield "delta", piece
            except Exception as e:
                logger.warning(
                    "Streaming from %s failed (%s): %s", candidate, type(e).__name__, e
                )
                await _record_provider_status(provider, "degraded")
                if started:
                    # Partial answer already shown — don't restart with another model
                    raise AIServiceError(
                        "The answer was cut off because the AI model stopped responding."
                    ) from e
                continue

            if started:
                return
            # Model finished without producing anything — treat as a failure
            logger.warning("Model %s streamed an empty response", candidate)
            await _record_provider_status(provider, "degraded")

        if not tried_any:
            raise AIServiceError(FRIENDLY_NOT_CONFIGURED_MESSAGE)
        raise AIServiceError(FRIENDLY_BUSY_MESSAGE)

    async def summarize_text(self, text: str, instruction: str) -> tuple[str, str]:
        """Summarize a block of text. Used by background document summarization."""
        return await self._complete(
            messages=[{"role": "user", "content": f"{instruction}\n\n<text>\n{text}\n</text>"}],
            context="",
            preferred_model=_candidate_models(DEFAULT_MODEL, len(text))[0],
            system_prompt_builder=lambda _context, _max: SUMMARY_SYSTEM_PROMPT,
            timeout=SUMMARY_TIMEOUT_SECONDS,
        )

    async def check_model_health(self, provider: str) -> str:
        """
        Check if an AI provider is usable: 'healthy' | 'degraded' | 'down'.
        - 'down': no API key, or the key/API check fails
        - 'degraded': key is fine but a real request failed in the last few minutes
        """
        api_key = {
            "groq": settings.GROQ_API_KEY,
            "google": settings.GOOGLE_API_KEY,
            "nvidia": settings.NEMOTRON_API_KEY,
        }.get(provider, "")
        if not api_key:
            return "down"

        # 1) Is the key valid / API reachable? (cached)
        status = None
        try:
            status = await cache_get(f"model_health:check:{provider}")
        except (RuntimeError, RedisError):
            pass
        if not status:
            status = await self._check_provider_api(provider, api_key)
            try:
                await cache_set(f"model_health:check:{provider}", status, HEALTH_CHECK_TTL_SECONDS)
            except (RuntimeError, RedisError):
                pass
        if status == "down":
            return "down"

        # 2) Key is fine — but did a real request fail recently? (busy / rate limited)
        try:
            if await cache_get(f"model_health:runtime:{provider}") == "degraded":
                return "degraded"
        except (RuntimeError, RedisError):
            pass
        return "healthy"

    async def _check_provider_api(self, provider: str, api_key: str) -> str:
        """Hit the provider's list-models endpoint to confirm the key works."""
        url = PROVIDER_HEALTH_URLS[provider]
        if provider == "google":
            headers, params = {}, {"key": api_key, "pageSize": 1}
        else:
            headers, params = {"Authorization": f"Bearer {api_key}"}, {}
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url, headers=headers, params=params)
            return "healthy" if response.status_code == 200 else "down"
        except httpx.HTTPError as e:
            logger.warning("Health check for %s failed: %s", provider, e)
            return "down"


# Singleton instance
ai_service = AIService()
