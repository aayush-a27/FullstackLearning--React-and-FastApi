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


async def _stream_events(client, chat_id, body) -> dict:
    """POST to the stream endpoint and return {event name: last payload}."""
    events, name = {}, None
    async with client.stream("POST", f"/chats/{chat_id}/messages/stream", json=body) as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if line.startswith("event: "):
                name = line[7:].strip()
            elif line.startswith("data: "):
                events[name] = json.loads(line[6:])
    return events


async def test_editing_a_message_replaces_it_and_everything_after(auth_client, monkeypatch):
    from app.services import ai_service as ai_module

    chat_id = (await auth_client.post("/chats", json={"title": "Edit"})).json()["id"]
    await auth_client.post(f"/chats/{chat_id}/messages", json={"content": "First"})
    await auth_client.post(f"/chats/{chat_id}/messages", json={"content": "Second"})
    first = (await auth_client.get(f"/chats/{chat_id}/messages")).json()[0]

    seen = []

    async def recording_get_response(self, model_id, messages, pdf_context=""):
        seen.append(messages)
        return f"Stub answer for: {messages[-1]['content']}", model_id

    monkeypatch.setattr(ai_module.AIService, "get_response", recording_get_response)

    response = await auth_client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "First, edited", "replace_from_id": first["id"]},
    )
    assert response.status_code == 201

    # The model saw only the edited question, not the turns being replaced
    assert seen[-1] == [{"role": "user", "content": "First, edited"}]
    history = (await auth_client.get(f"/chats/{chat_id}/messages")).json()
    assert [m["content"] for m in history] == ["First, edited", "Stub answer for: First, edited"]


async def test_streaming_returns_the_saved_question_and_supports_try_again(auth_client):
    chat_id = (await auth_client.post("/chats", json={"title": "Retry"})).json()["id"]

    events = await _stream_events(auth_client, chat_id, {"content": "Question"})
    saved_question = events["user"]
    assert saved_question["role"] == "user" and saved_question["content"] == "Question"

    # Try again = resend the same question, replacing the saved one by its real id
    await _stream_events(
        auth_client, chat_id, {"content": "Question", "replace_from_id": saved_question["id"]}
    )
    history = (await auth_client.get(f"/chats/{chat_id}/messages")).json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["id"] != saved_question["id"]


async def test_replace_from_must_be_a_user_message_in_the_same_chat(auth_client):
    chat_a = (await auth_client.post("/chats", json={"title": "A"})).json()["id"]
    chat_b = (await auth_client.post("/chats", json={"title": "B"})).json()["id"]
    await auth_client.post(f"/chats/{chat_a}/messages", json={"content": "In A"})
    question, answer = (await auth_client.get(f"/chats/{chat_a}/messages")).json()

    other_chat = await auth_client.post(
        f"/chats/{chat_b}/messages", json={"content": "x", "replace_from_id": question["id"]}
    )
    assert other_chat.status_code == 404

    not_a_question = await auth_client.post(
        f"/chats/{chat_a}/messages", json={"content": "x", "replace_from_id": answer["id"]}
    )
    assert not_a_question.status_code == 404

    # Nothing was deleted by the rejected requests
    assert len((await auth_client.get(f"/chats/{chat_a}/messages")).json()) == 2


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
