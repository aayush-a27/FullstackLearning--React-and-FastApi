"""Profile updates, preferences and account deletion."""
import uuid


async def test_update_profile_name(auth_client):
    response = await auth_client.patch("/users/me", json={"full_name": "Renamed User"})
    assert response.status_code == 200
    assert response.json()["full_name"] == "Renamed User"


async def test_duplicate_username_returns_409(auth_client):
    # A second account whose username we then try to claim
    suffix = uuid.uuid4().hex[:10]
    other = await auth_client.post(
        "/auth/register",
        json={
            "username": f"taken_{suffix}",
            "email": f"taken_{suffix}@example.com",
            "password": "Passw0rd!",
        },
    )
    taken = other.json()["user"]["username"]

    response = await auth_client.patch("/users/me", json={"username": taken})
    assert response.status_code == 409
    assert "already taken" in response.json()["detail"].lower()


async def test_short_username_is_rejected(auth_client):
    assert (await auth_client.patch("/users/me", json={"username": "ab"})).status_code == 422


async def test_email_notifications_preference_persists(auth_client):
    assert (await auth_client.get("/users/me")).json()["email_notifications"] is False

    response = await auth_client.patch("/users/me", json={"email_notifications": True})
    assert response.status_code == 200
    assert response.json()["email_notifications"] is True
    assert (await auth_client.get("/users/me")).json()["email_notifications"] is True


async def test_profile_pictures_are_not_supported(auth_client):
    """Avatar upload was removed: no endpoint, and avatar_url is neither stored nor returned."""
    assert (await auth_client.post("/users/me/avatar")).status_code in (404, 405)

    response = await auth_client.patch("/users/me", json={"avatar_url": "https://x.test/a.png"})
    assert response.status_code == 200
    assert "avatar_url" not in response.json()


async def test_delete_account_requires_correct_password(auth_client):
    response = await auth_client.request(
        "DELETE", "/users/me", json={"password": "WrongPassword!"}
    )
    assert response.status_code == 401
    assert (await auth_client.get("/users/me")).status_code == 200


async def test_delete_account_removes_the_user(auth_client):
    response = await auth_client.request(
        "DELETE", "/users/me", json={"password": auth_client.password}
    )
    assert response.status_code == 204
    # The token is still well-formed, but the user is gone
    assert (await auth_client.get("/users/me")).status_code == 401


async def test_onboarding_sets_flag(auth_client):
    response = await auth_client.patch(
        "/users/me/onboarding",
        json={"language": "English", "purpose": "deep_research", "date_of_birth": "2000-01-01"},
    )
    assert response.status_code == 200
    assert response.json()["is_onboarded"] is True


async def test_onboarding_rejects_bad_date(auth_client):
    response = await auth_client.patch(
        "/users/me/onboarding",
        json={"language": "English", "purpose": "x", "date_of_birth": "01-01-2000"},
    )
    assert response.status_code == 422
