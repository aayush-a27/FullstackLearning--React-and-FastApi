"""Chat CRUD, renaming, ownership isolation and caching."""
import uuid


async def _second_user(client):
    """Register another account and return a client header for it."""
    suffix = uuid.uuid4().hex[:10]
    response = await client.post(
        "/auth/register",
        json={
            "username": f"second_{suffix}",
            "email": f"second_{suffix}@example.com",
            "password": "Passw0rd!",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_create_and_list_chat(auth_client):
    created = await auth_client.post("/chats", json={"title": "First chat"})
    assert created.status_code == 201
    assert created.json()["title"] == "First chat"

    listed = await auth_client.get("/chats")
    assert listed.status_code == 200
    assert any(c["id"] == created.json()["id"] for c in listed.json())


async def test_rename_chat(auth_client):
    chat_id = (await auth_client.post("/chats", json={"title": "Old name"})).json()["id"]

    renamed = await auth_client.patch(f"/chats/{chat_id}", json={"title": "New name"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "New name"

    # The cached chat list must reflect the rename, not a stale copy
    listed = await auth_client.get("/chats")
    assert next(c for c in listed.json() if c["id"] == chat_id)["title"] == "New name"


async def test_delete_chat(auth_client):
    chat_id = (await auth_client.post("/chats", json={"title": "Temp"})).json()["id"]
    assert (await auth_client.delete(f"/chats/{chat_id}")).status_code == 204
    assert (await auth_client.get(f"/chats/{chat_id}")).status_code == 404
    assert all(c["id"] != chat_id for c in (await auth_client.get("/chats")).json())


async def test_unknown_chat_returns_404(auth_client):
    assert (await auth_client.get(f"/chats/{uuid.uuid4()}")).status_code == 404


async def test_malformed_chat_id_is_rejected(auth_client):
    assert (await auth_client.get("/chats/not-a-uuid")).status_code == 422


async def test_users_cannot_see_each_others_chats(auth_client):
    chat_id = (await auth_client.post("/chats", json={"title": "Private"})).json()["id"]
    other_headers = await _second_user(auth_client)

    response = await auth_client.get(f"/chats/{chat_id}", headers=other_headers)
    assert response.status_code == 404

    listed = await auth_client.get("/chats", headers=other_headers)
    assert all(c["id"] != chat_id for c in listed.json())


async def test_other_user_cannot_delete_chat(auth_client):
    chat_id = (await auth_client.post("/chats", json={"title": "Private"})).json()["id"]
    other_headers = await _second_user(auth_client)

    assert (
        await auth_client.delete(f"/chats/{chat_id}", headers=other_headers)
    ).status_code == 404
    # Still there for the owner
    assert (await auth_client.get(f"/chats/{chat_id}")).status_code == 200


async def test_chat_list_cache_updates_when_a_chat_is_added(auth_client):
    first = await auth_client.get("/chats")
    count = len(first.json())

    await auth_client.post("/chats", json={"title": "Another"})
    second = await auth_client.get("/chats")
    assert len(second.json()) == count + 1
