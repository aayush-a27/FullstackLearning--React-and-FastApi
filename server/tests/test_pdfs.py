"""PDF upload, background indexing, retrieval-backed answers and limits."""
import asyncio
import uuid

from tests.conftest import sample_pdf


async def _upload(client, pages=1, text="Hello from the test document.", name="doc.pdf"):
    return await client.post(
        "/pdfs/upload",
        files={"file": (name, sample_pdf(pages, text), "application/pdf")},
    )


async def _wait_until_ready(client, pdf_id, timeout=30.0):
    """Background indexing runs as a task; poll until it finishes."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        body = (await client.get(f"/pdfs/{pdf_id}")).json()
        if body["status"] in ("ready", "failed"):
            return body
        await asyncio.sleep(0.2)
    raise AssertionError("PDF did not finish indexing in time")


async def test_upload_returns_immediately_as_pending(auth_client):
    response = await _upload(auth_client)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["page_count"] == 1


async def test_upload_rejects_non_pdf(auth_client):
    response = await auth_client.post(
        "/pdfs/upload", files={"file": ("notes.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 400


async def test_upload_rejects_a_renamed_file(auth_client):
    response = await auth_client.post(
        "/pdfs/upload", files={"file": ("fake.pdf", b"not a pdf at all", "application/pdf")}
    )
    assert response.status_code == 400


async def test_pdf_is_indexed_in_the_background(auth_client):
    pdf_id = (await _upload(auth_client)).json()["id"]
    body = await _wait_until_ready(auth_client, pdf_id)
    assert body["status"] == "ready"
    assert body["chunk_count"] > 0
    assert body["progress"] == 100


async def test_answer_uses_retrieved_chunks_and_cites_sources(auth_client):
    pdf_id = (
        await _upload(auth_client, text="The treasury balance was 4200 gold dragons.")
    ).json()["id"]
    await _wait_until_ready(auth_client, pdf_id)

    chat_id = (
        await auth_client.post("/chats", json={"title": "Doc", "pdf_ids": [pdf_id]})
    ).json()["id"]
    response = await auth_client.post(
        f"/chats/{chat_id}/messages", json={"content": "What was the treasury balance?"}
    )
    assert response.status_code == 201
    metadata = response.json()["metadata"]
    assert metadata["mode"] in ("rag", "raw")
    assert metadata["sources"]


async def test_asking_before_indexing_finishes_is_explained(auth_client):
    pdf_id = (await _upload(auth_client)).json()["id"]
    chat_id = (
        await auth_client.post("/chats", json={"title": "Doc", "pdf_ids": [pdf_id]})
    ).json()["id"]

    response = await auth_client.post(
        f"/chats/{chat_id}/messages", json={"content": "What is this?"}
    )
    # Either indexing finished first (201) or we get the clear "still preparing" message
    assert response.status_code in (201, 409)
    if response.status_code == 409:
        assert "still being prepared" in response.json()["detail"].lower()


async def test_view_endpoint_returns_the_file(auth_client):
    pdf_id = (await _upload(auth_client)).json()["id"]
    response = await auth_client.get(f"/pdfs/{pdf_id}/view")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


async def test_view_requires_authentication(auth_client):
    pdf_id = (await _upload(auth_client)).json()["id"]
    response = await auth_client.get(f"/pdfs/{pdf_id}/view", headers={"Authorization": ""})
    assert response.status_code in (401, 403)


async def test_users_cannot_read_each_others_pdfs(auth_client):
    pdf_id = (await _upload(auth_client)).json()["id"]
    suffix = uuid.uuid4().hex[:10]
    other = await auth_client.post(
        "/auth/register",
        json={
            "username": f"p_{suffix}",
            "email": f"p_{suffix}@example.com",
            "password": "Passw0rd!",
        },
    )
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    assert (await auth_client.get(f"/pdfs/{pdf_id}", headers=headers)).status_code == 404
    assert (await auth_client.get(f"/pdfs/{pdf_id}/view", headers=headers)).status_code == 404


async def test_delete_pdf_removes_it(auth_client):
    pdf_id = (await _upload(auth_client)).json()["id"]
    await _wait_until_ready(auth_client, pdf_id)
    assert (await auth_client.delete(f"/pdfs/{pdf_id}")).status_code == 204
    assert (await auth_client.get(f"/pdfs/{pdf_id}")).status_code == 404


async def test_too_many_small_pdfs_in_one_chat_is_refused(auth_client):
    ids = [(await _upload(auth_client, name=f"d{i}.pdf")).json()["id"] for i in range(6)]
    response = await auth_client.post("/chats", json={"title": "Many", "pdf_ids": ids})
    assert response.status_code == 400
    assert "at most" in response.json()["detail"].lower()


async def test_five_small_pdfs_are_allowed(auth_client):
    ids = [(await _upload(auth_client, name=f"ok{i}.pdf")).json()["id"] for i in range(5)]
    response = await auth_client.post("/chats", json={"title": "Five", "pdf_ids": ids})
    assert response.status_code == 201


async def test_chat_without_a_pdf_still_answers(auth_client):
    chat_id = (await auth_client.post("/chats", json={"title": "No PDF"})).json()["id"]
    response = await auth_client.post(
        f"/chats/{chat_id}/messages", json={"content": "Hello"}
    )
    assert response.status_code == 201
    assert response.json()["metadata"]["mode"] == "none"
