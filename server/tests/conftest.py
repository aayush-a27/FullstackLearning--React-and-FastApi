"""
Shared test fixtures.

Tests run against a throwaway database (`<your db>_test`) that is created and
dropped per session, so the development data is never touched. The AI providers
and the embedding API are stubbed — tests must not spend real API quota or
depend on a provider being up.
"""
import asyncio
import os
import uuid
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio

from tests.factories import sample_pdf  # noqa: F401 — re-exported for tests

os.environ.setdefault("DEBUG", "False")

from app.config import get_settings  # noqa: E402

# ---------------------------------------------------------------------------
# Redirect the app to the test database AT IMPORT TIME.
#
# conftest is imported before test modules are collected, and those modules
# import app code (routers, services) which in turn imports app.database — and
# app.database builds its engine from the settings at import time. Redirecting
# any later than this leaves the engine pointed at the development database.
# ---------------------------------------------------------------------------
_REAL_DATABASE_URL = get_settings().DATABASE_URL
_BASE_URL, _DEV_DB_NAME = _REAL_DATABASE_URL.rsplit("/", 1)
TEST_DB_NAME = f"{_DEV_DB_NAME}_test"
TEST_DB_URL = f"{_BASE_URL}/{TEST_DB_NAME}"

os.environ["DATABASE_URL"] = TEST_DB_URL

# Uploaded test files go to a throwaway folder, never the real uploads/ directory
import tempfile  # noqa: E402

TEST_UPLOAD_DIR = tempfile.mkdtemp(prefix="pdfchat_test_uploads_")
os.environ["UPLOAD_DIR"] = TEST_UPLOAD_DIR

get_settings.cache_clear()
assert get_settings().DATABASE_URL == TEST_DB_URL
assert get_settings().UPLOAD_DIR == TEST_UPLOAD_DIR

settings = get_settings()


def _admin_url() -> str:
    url = _BASE_URL.replace("postgresql+asyncpg", "postgresql")
    return url + "/postgres"


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def test_database():
    """Create a fresh test database, build the schema, drop it afterwards."""
    conn = await asyncpg.connect(_admin_url())
    await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')
    await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    await conn.close()

    # Safety net: refuse to run if anything is still pointed at the real database
    from app.database import engine as app_engine

    assert app_engine.url.database == TEST_DB_NAME, (
        f"Tests would write to {app_engine.url.database!r}, not {TEST_DB_NAME!r}. "
        "Something imported app.database before conftest redirected it."
    )

    # Build the schema by running the real migrations, so a broken migration
    # fails the test suite rather than showing up in production.
    from alembic import command
    from alembic.config import Config

    config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    await asyncio.to_thread(command.upgrade, config, "head")

    yield

    import shutil

    shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)
    await app_engine.dispose()
    conn = await asyncpg.connect(_admin_url())
    await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')
    await conn.close()


@pytest_asyncio.fixture
async def client(test_database, monkeypatch):
    """An HTTP client bound to the app, with the AI and embedding calls stubbed."""
    import httpx
    from app.services import ai_service as ai_module
    from app.services import embedding_service as embed_module
    from app.main import app

    async def fake_get_response(self, model_id, messages, pdf_context=""):
        return f"Stub answer for: {messages[-1]['content'][:40]}", model_id

    async def fake_stream_response(self, model_id, messages, pdf_context=""):
        yield "model", model_id
        for word in ["Stub ", "streamed ", "answer."]:
            yield "delta", word

    async def fake_summarize(self, text, instruction):
        return f"Stub summary of {len(text)} characters.", "groq-fast"

    async def fake_health(self, provider):
        return "healthy"

    async def fake_embed_texts(texts, input_type="passage", on_progress=None):
        # Deterministic unit vectors: similarity depends on word overlap
        import numpy as np

        packed = []
        for text in texts:
            vector = np.zeros(embed_module.EMBED_DIM, dtype=np.float32)
            for word in set(text.lower().split()):
                vector[hash(word) % embed_module.EMBED_DIM] += 1.0
            packed.append(embed_module.pack_vector(vector))
        if on_progress:
            await on_progress(len(texts), len(texts))
        return packed

    monkeypatch.setattr(ai_module.AIService, "get_response", fake_get_response)
    monkeypatch.setattr(ai_module.AIService, "stream_response", fake_stream_response)
    monkeypatch.setattr(ai_module.AIService, "summarize_text", fake_summarize)
    monkeypatch.setattr(ai_module.AIService, "check_model_health", fake_health)
    monkeypatch.setattr(embed_module, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(embed_module, "is_configured", lambda: True)

    from app.services import pdf_processing

    monkeypatch.setattr(pdf_processing, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(pdf_processing, "is_configured", lambda: True)

    async def fake_embed_query(question):
        packed = await fake_embed_texts([question], "query")
        import numpy as np

        return np.frombuffer(packed[0], dtype=np.float32)

    from app.services import retrieval

    monkeypatch.setattr(retrieval, "embed_query", fake_embed_query)

    # httpx's ASGI transport doesn't run lifespan events, so Redis is connected
    # here; without it token blacklisting and rate limits would silently no-op.
    from app.core import redis as redis_module

    redis_available = True
    try:
        redis = await redis_module.init_redis()
        # Clear per-IP rate-limit counters so one test can't throttle the next
        async for key in redis.scan_iter("rate_limit:*"):
            await redis.delete(key)
    except Exception:
        redis_available = False

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test" + settings.API_V1_PREFIX
    ) as test_client:
        test_client.redis_available = redis_available
        yield test_client

    if redis_available:
        await redis_module.close_redis()


@pytest_asyncio.fixture
async def auth_client(client):
    """A client already registered and authenticated as a fresh user."""
    suffix = uuid.uuid4().hex[:10]
    response = await client.post(
        "/auth/register",
        json={
            "username": f"user_{suffix}",
            "email": f"user_{suffix}@example.com",
            "password": "Passw0rd!",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    client.headers["Authorization"] = f"Bearer {body['access_token']}"
    client.user = body["user"]
    client.password = "Passw0rd!"
    return client
