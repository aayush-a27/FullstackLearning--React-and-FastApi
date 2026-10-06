"""Sending messages, streaming, history trimming and model routing."""
import json
import uuid

from app.routers.messages import _trim_history, MAX_HISTORY_MESSAGES, MAX_HISTORY_CHARS
from app.models.message import Message


async def test_send_message_saves_both_turns(auth_client):
    chat_id = (await auth_client.post("/chats", json={"title": "Chat"})).json()["id"]

    response = await auth_client.post(
        f"/chats/{chat_id}/messages", json={"content": "Hello there", "smart_switch": True}
    )
    assert response.status_code == 201
    assert response.json()["role"] == "assistant"
    assert response.json()["model_used"]

    history = (await auth_client.get(f"/chats/{chat_id}/messages")).json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"] == "Hello there"


async def test_message_history_is_cached_and_invalidated(auth_client):
    chat_id = (await auth_client.post("/chats", json={"title": "Chat"})).json()["id"]
    await auth_client.post(f"/chats/{chat_id}/messages", json={"content": "First"})

    assert len((await auth_client.get(f"/chats/{chat_id}/messages")).json()) == 2
    await auth_client.post(f"/chats/{chat_id}/messages", json={"content": "Second"})
    # A stale cache would still show 2
    assert len((await auth_client.get(f"/chats/{chat_id}/messages")).json()) == 4


async def test_cannot_post_to_someone_elses_chat(auth_client):
    chat_id = (await auth_client.post("/chats", json={"title": "Private"})).json()["id"]
    suffix = uuid.uuid4().hex[:10]
    other = await auth_client.post(
        "/auth/register",
        json={
            "username": f"m_{suffix}",
            "email": f"m_{suffix}@example.com",
            "password": "Passw0rd!",
        },
    )
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    response = await auth_client.post(
        f"/chats/{chat_id}/messages", json={"content": "Sneaky"}, headers=headers
    )
    assert response.status_code == 404


async def test_streaming_sends_events_and_saves_the_answer(auth_client):
    chat_id = (await auth_client.post("/chats", json={"title": "Stream"})).json()["id"]

    events, deltas = [], []
    async with auth_client.stream(
        "POST", f"/chats/{chat_id}/messages/stream", json={"content": "Stream please"}
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        name = None
        async for line in response.aiter_lines():
            if line.startswith("event: "):
                name = line[7:].strip()
                events.append(name)
            elif line.startswith("data: ") and name == "delta":
                deltas.append(json.loads(line[6:])["text"])

    assert {"start", "model", "done"} <= set(events)
    assert deltas, "expected at least one delta event"

    history = (await auth_client.get(f"/chats/{chat_id}/messages")).json()
    assert history[-1]["content"] == "".join(deltas)


def test_trim_history_respects_the_message_limit():
    messages = [
        Message(chat_id=uuid.uuid4(), role="user", content=f"message {i}")
        for i in range(MAX_HISTORY_MESSAGES + 10)
    ]
    trimmed = _trim_history(messages)
    assert len(trimmed) <= MAX_HISTORY_MESSAGES
    # Keeps the most recent turns
    assert trimmed[-1]["content"] == messages[-1].content


def test_trim_history_respects_the_character_budget():
    messages = [
        Message(chat_id=uuid.uuid4(), role="user", content="x" * 5000) for _ in range(5)
    ]
    trimmed = _trim_history(messages)
    assert sum(len(m["content"]) for m in trimmed) <= MAX_HISTORY_CHARS + 5000
    assert len(trimmed) < len(messages)
