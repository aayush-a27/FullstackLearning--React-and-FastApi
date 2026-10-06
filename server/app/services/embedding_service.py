"""
Text embeddings via NVIDIA NIM (OpenAI-compatible /embeddings endpoint).

Vectors are L2-normalized before storage so cosine similarity is a plain dot
product at query time. They are stored as packed float32 bytes — see
app/models/pdf_chunk.py for why pgvector isn't used.
"""
import asyncio
import logging
import httpx
import numpy as np
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

EMBED_MODEL = "nvidia/nemotron-3-embed-1b"
EMBED_DIM = 2048

# The API accepts large batches; keep requests modest so payloads stay small
EMBED_BATCH_SIZE = 32
EMBED_CONCURRENCY = 4
EMBED_TIMEOUT_SECONDS = 120
EMBED_MAX_ATTEMPTS = 3

# Chunks longer than this are truncated before embedding (model sequence limit)
MAX_EMBED_CHARS = 8_000


class EmbeddingError(Exception):
    """Raised when embeddings could not be generated."""


def pack_vector(vector) -> bytes:
    """Normalize a vector and pack it as float32 bytes for storage."""
    array = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(array))
    if norm > 0:
        array = array / norm
    return array.astype(np.float32).tobytes()


def unpack_matrix(blobs: list[bytes]) -> np.ndarray:
    """Turn stored embedding bytes into an (n, EMBED_DIM) float32 matrix."""
    if not blobs:
        return np.zeros((0, EMBED_DIM), dtype=np.float32)
    return np.frombuffer(b"".join(blobs), dtype=np.float32).reshape(len(blobs), -1)


def is_configured() -> bool:
    return bool(settings.NEMOTRON_API_KEY)


async def _embed_batch(
    client: httpx.AsyncClient, texts: list[str], input_type: str
) -> list[list[float]]:
    """Embed one batch, retrying on rate limits and transient server errors."""
    payload = {
        "input": [t[:MAX_EMBED_CHARS] for t in texts],
        "model": EMBED_MODEL,
        "input_type": input_type,
        "encoding_format": "float",
    }
    headers = {"Authorization": f"Bearer {settings.NEMOTRON_API_KEY}"}

    for attempt in range(1, EMBED_MAX_ATTEMPTS + 1):
        try:
            response = await client.post(
                f"{settings.NVIDIA_BASE_URL}/embeddings", json=payload, headers=headers
            )
            if response.status_code == 200:
                data = sorted(response.json()["data"], key=lambda d: d["index"])
                return [d["embedding"] for d in data]
            if response.status_code in (429, 500, 502, 503, 504) and attempt < EMBED_MAX_ATTEMPTS:
                await asyncio.sleep(2 * attempt)
                continue
            raise EmbeddingError(
                f"Embedding request failed: HTTP {response.status_code} {response.text[:200]}"
            )
        except httpx.HTTPError as e:
            if attempt < EMBED_MAX_ATTEMPTS:
                await asyncio.sleep(2 * attempt)
                continue
            raise EmbeddingError(f"Embedding request failed: {e}") from e

    raise EmbeddingError("Embedding request failed after retries")


async def embed_texts(
    texts: list[str],
    input_type: str = "passage",
    on_progress=None,
) -> list[bytes]:
    """
    Embed many texts and return packed float32 bytes, in the same order.
    `input_type` must be "passage" for documents and "query" for questions —
    this model is asymmetric and retrieval quality drops if they're swapped.
    `on_progress(done, total)` is awaited after each batch, if given.
    """
    if not is_configured():
        raise EmbeddingError("NEMOTRON_API_KEY is not set, so embeddings are unavailable")
    if not texts:
        return []

    batches = [
        texts[i : i + EMBED_BATCH_SIZE] for i in range(0, len(texts), EMBED_BATCH_SIZE)
    ]
    semaphore = asyncio.Semaphore(EMBED_CONCURRENCY)

    async with httpx.AsyncClient(timeout=EMBED_TIMEOUT_SECONDS) as client:

        done = 0

        async def run(batch: list[str]) -> list[list[float]]:
            nonlocal done
            async with semaphore:
                vectors = await _embed_batch(client, batch, input_type)
            done += len(batch)
            if on_progress:
                await on_progress(done, len(texts))
            return vectors

        results = await asyncio.gather(*(run(batch) for batch in batches))

    return [pack_vector(vector) for batch in results for vector in batch]


async def embed_query(question: str) -> np.ndarray:
    """Embed a user question and return it as a normalized float32 vector."""
    packed = await embed_texts([question], input_type="query")
    return np.frombuffer(packed[0], dtype=np.float32)
