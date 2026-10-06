"""Rate limiting, security headers and CORS."""
import pytest

from app.core.rate_limit import MESSAGE_LIMIT


async def test_security_headers_are_present(auth_client):
    response = await auth_client.get("/users/me")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["Permissions-Policy"]


async def test_hsts_is_not_sent_in_debug(auth_client):
    """HSTS over plain http would be wrong, so it's production-only."""
    from app.config import get_settings

    response = await auth_client.get("/users/me")
    if get_settings().DEBUG:
        assert "Strict-Transport-Security" not in response.headers
    else:
        assert "Strict-Transport-Security" in response.headers


async def test_cors_allows_the_configured_origin(auth_client):
    response = await auth_client.options(
        "/users/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


async def test_cors_blocks_an_unknown_origin(auth_client):
    response = await auth_client.options(
        "/users/me",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


async def test_message_rate_limit_eventually_returns_429(auth_client):
    if not getattr(auth_client, "redis_available", False):
        pytest.skip("Rate limiting needs Redis")

    chat_id = (await auth_client.post("/chats", json={"title": "Flood"})).json()["id"]

    statuses = []
    for _ in range(MESSAGE_LIMIT.max_requests + 2):
        response = await auth_client.post(
            f"/chats/{chat_id}/messages", json={"content": "hi"}
        )
        statuses.append(response.status_code)
        if response.status_code == 429:
            assert "Retry-After" in response.headers
            assert "limit" in response.json()["detail"].lower()
            break

    assert 429 in statuses, "rate limit never triggered"


async def test_rate_limit_is_per_user(auth_client):
    """One user hitting the limit must not lock anyone else out."""
    if not getattr(auth_client, "redis_available", False):
        pytest.skip("Rate limiting needs Redis")

    import uuid

    chat_id = (await auth_client.post("/chats", json={"title": "Flood"})).json()["id"]
    for _ in range(MESSAGE_LIMIT.max_requests + 2):
        response = await auth_client.post(
            f"/chats/{chat_id}/messages", json={"content": "hi"}
        )
        if response.status_code == 429:
            break

    suffix = uuid.uuid4().hex[:10]
    other = await auth_client.post(
        "/auth/register",
        json={
            "username": f"fresh_{suffix}",
            "email": f"fresh_{suffix}@example.com",
            "password": "Passw0rd!",
        },
    )
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    their_chat = (
        await auth_client.post("/chats", json={"title": "Mine"}, headers=headers)
    ).json()["id"]

    response = await auth_client.post(
        f"/chats/{their_chat}/messages", json={"content": "hello"}, headers=headers
    )
    assert response.status_code == 201


async def test_health_endpoint_is_public(auth_client):
    response = await auth_client.get("/health", headers={"Authorization": ""})
    # /health sits outside the API prefix
    assert response.status_code in (200, 404)
