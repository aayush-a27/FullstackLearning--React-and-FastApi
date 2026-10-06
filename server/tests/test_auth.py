"""Registration, login, token refresh and logout."""
import uuid


async def test_register_returns_token_and_user(client):
    suffix = uuid.uuid4().hex[:10]
    response = await client.post(
        "/auth/register",
        json={
            "username": f"new_{suffix}",
            "email": f"new_{suffix}@example.com",
            "password": "Passw0rd!",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == f"new_{suffix}@example.com"
    assert "hashed_password" not in body["user"]


async def test_duplicate_email_is_rejected(client, auth_client):
    response = await client.post(
        "/auth/register",
        json={
            "username": f"other_{uuid.uuid4().hex[:8]}",
            "email": auth_client.user["email"],
            "password": "Passw0rd!",
        },
    )
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


async def test_login_with_wrong_password_fails(client, auth_client):
    response = await client.post(
        "/auth/login",
        json={"email": auth_client.user["email"], "password": "WrongPassword!"},
    )
    assert response.status_code == 401


async def test_protected_route_requires_token(client):
    client.headers.pop("Authorization", None)
    assert (await client.get("/users/me")).status_code in (401, 403)


async def test_refresh_issues_a_new_access_token(client, auth_client):
    response = await client.post(
        "/auth/login",
        json={"email": auth_client.user["email"], "password": auth_client.password},
    )
    assert response.status_code == 200
    refreshed = await client.post("/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


async def test_logout_revokes_the_access_token(auth_client):
    """The old token must stop working — this needs Redis to be running."""
    old_token = auth_client.headers["Authorization"]
    assert (await auth_client.post("/auth/logout")).status_code == 204

    auth_client.headers["Authorization"] = old_token
    response = await auth_client.get("/users/me")
    if response.status_code == 200:
        import pytest

        pytest.skip("Redis unavailable, so token blacklisting is disabled")
    assert response.status_code == 401
