import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, AsyncSessionLocal
from app.schemas.message import MessageCreate, MessageResponse
from app.services.chat_service import get_chat_by_id
from app.services.ai_service import ai_service, AIServiceError
from app.services.model_router import select_model, is_summary_question
from app.services.retrieval import retrieve_chunks, build_context, sources_from_chunks
from app.core.cache import chat_list_key, messages_key, get_json, set_json, invalidate, MESSAGES_TTL_SECONDS
from app.core.rate_limit import rate_limited, MESSAGE_LIMIT
from app.dependencies import get_current_user
from app.models.chat import Chat
from app.models.user import User
from app.models.message import Message
from app.models.pdf_document import PdfDocument

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["Messages"])

# How much earlier conversation to replay to the model. Sending the whole
# history made every message in a long chat slower and more expensive.
MAX_HISTORY_MESSAGES = 12
MAX_HISTORY_CHARS = 8_000

# Caps on document context per request
MAX_RAG_CONTEXT_CHARS = 12_000
MAX_SUMMARY_CONTEXT_CHARS = 30_000
# Used only when a PDF has no embeddings (no key, or embedding failed)
MAX_RAW_TEXT_CHARS = 20_000

STILL_INDEXING_MESSAGE = (
    "Your PDF is still being prepared. This takes a moment for long documents — "
    "please try again shortly."
)


@dataclass
class PreparedContext:
    """Document context for one question, plus where it came from."""

    context: str = ""
    sources: list[dict] = field(default_factory=list)
    mode: str = "none"  # none | rag | summary | raw


def _trim_history(messages: list[Message]) -> list[dict]:
    """Keep the most recent turns within both a message count and a character budget."""
    selected: list[Message] = []
    used = 0
    for message in reversed(messages[-MAX_HISTORY_MESSAGES:]):
        length = len(message.content)
        if selected and used + length > MAX_HISTORY_CHARS:
            break
        selected.append(message)
        used += length
    selected.reverse()
    return [{"role": m.role, "content": m.content} for m in selected]


async def _summary_context(db: AsyncSession, pdf_ids: list[UUID]) -> PreparedContext:
    """Whole-document summaries, for questions about the document as a whole."""
    rows = (
        await db.execute(
            select(PdfDocument.id, PdfDocument.filename, PdfDocument.summary).where(
                PdfDocument.id.in_(pdf_ids), PdfDocument.summary_status == "ready"
            )
        )
    ).all()
    if not rows:
        return PreparedContext()

    parts = [f"[{row.filename} — full document summary]\n{row.summary}" for row in rows]
    return PreparedContext(
        context="\n\n---\n\n".join(parts)[:MAX_SUMMARY_CONTEXT_CHARS],
        sources=[{"pdf_id": str(row.id), "filename": row.filename} for row in rows],
        mode="summary",
    )


async def _raw_text_context(db: AsyncSession, pdf_ids: list[UUID]) -> PreparedContext:
    """Fallback when a PDF has no embeddings: send the start of its text."""
    rows = (
        await db.execute(
            select(PdfDocument.id, PdfDocument.filename, PdfDocument.extracted_text)
            .where(PdfDocument.id.in_(pdf_ids))
        )
    ).all()
    parts, sources = [], []
    budget = MAX_RAW_TEXT_CHARS
    for row in rows:
        if not row.extracted_text:
            continue
        excerpt = row.extracted_text[:budget]
        budget -= len(excerpt)
        parts.append(f"[{row.filename}]\n{excerpt}")
        sources.append({"pdf_id": str(row.id), "filename": row.filename})
        if budget <= 0:
            break
    if not parts:
        return PreparedContext()
    return PreparedContext(context="\n\n---\n\n".join(parts), sources=sources, mode="raw")


async def prepare_context(db: AsyncSession, chat: Chat, question: str) -> PreparedContext:
    """
    Build the document context for a question.

    Only the passages that matter are sent, instead of the whole PDF: summaries
    for whole-document questions, vector search otherwise.
    """
    pdfs = list(chat.pdf_documents)
    if not pdfs:
        return PreparedContext()

    ready = [p for p in pdfs if p.status == "ready"]
    if not ready:
        if any(p.status in ("pending", "processing") for p in pdfs):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=STILL_INDEXING_MESSAGE
            )
        return PreparedContext()

    ready_ids = [p.id for p in ready]

    if is_summary_question(question):
        prepared = await _summary_context(db, ready_ids)
        if prepared.context:
            return prepared
        writing = [p for p in ready if p.summary_status in ("pending", "processing")]
        if writing:
            # A "summary" stitched from 8 search hits would misrepresent a long
            # document, so say it's coming rather than answer badly.
            pdf = writing[0]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"The full summary of {pdf.filename} is still being written "
                    f"({pdf.summary_progress}% done). You can ask specific questions "
                    "about it in the meantime."
                ),
            )
        # Summary failed — fall through to retrieval as a best effort

    if any(p.chunk_count for p in ready):
        chunks = await retrieve_chunks(db, ready_ids, question)
        if chunks:
            return PreparedContext(
                context=build_context(chunks, MAX_RAG_CONTEXT_CHARS),
                sources=sources_from_chunks(chunks),
                mode="rag",
            )

    return await _raw_text_context(db, ready_ids)


async def _load_turn(db: AsyncSession, chat_id: UUID, user_id: UUID, data: MessageCreate):
    """Shared setup for both the streaming and non-streaming endpoints."""
    chat = await get_chat_by_id(db, chat_id, user_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    prepared = await prepare_context(db, chat, data.content)

    history_rows = (
        await db.execute(
            select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc())
        )
    ).scalars().all()
    history = _trim_history(list(history_rows))
    history.append({"role": "user", "content": data.content})

    smart_switch = (
        data.smart_switch if data.smart_switch is not None else chat.smart_switch_enabled
    )
    model_id = select_model(
        question=data.content,
        user_selected_model=data.model_id or chat.active_model,
        smart_switch_enabled=smart_switch,
        context_len=len(prepared.context),
    )
    return prepared, history, model_id


async def _save_turn(
    chat_id: UUID,
    user_id: UUID,
    question: str,
    answer: str,
    model_used: str,
    prepared: PreparedContext,
) -> Message:
    """Persist the user message and the assistant reply together."""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        db.add(
            Message(
                chat_id=chat_id,
                role="user",
                content=question,
                created_at=now - timedelta(milliseconds=1),
            )
        )
        ai_message = Message(
            chat_id=chat_id,
            role="assistant",
            content=answer,
            model_used=model_used,
            metadata_={"mode": prepared.mode, "sources": prepared.sources},
            created_at=now,
        )
        db.add(ai_message)
        # Keep the chat list ordered by real activity
        chat = await db.get(Chat, chat_id)
        if chat:
            chat.updated_at = now
        await db.commit()
        await db.refresh(ai_message)

    # New messages change both the history and the chat list's ordering
    await invalidate(messages_key(chat_id), chat_list_key(user_id))
    return ai_message


@router.get("", response_model=list[MessageResponse])
async def list_messages(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a chat, ordered chronologically."""
    chat = await get_chat_by_id(db, chat_id, current_user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    key = messages_key(chat_id)
    cached = await get_json(key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
    )
    payload = [
        MessageResponse.model_validate(m).model_dump(mode="json")
        for m in result.scalars().all()
    ]
    await set_json(key, payload, MESSAGES_TTL_SECONDS)
    return payload


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limited(MESSAGE_LIMIT))],
)
async def send_message(
    chat_id: UUID,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a user message and get an AI response.
    The AI model is selected based on smart switch or user preference.
    """
    prepared, history, model_id = await _load_turn(db, chat_id, current_user.id, data)

    try:
        answer, model_used = await ai_service.get_response(
            model_id=model_id, messages=history, pdf_context=prepared.context
        )
    except AIServiceError as e:
        # Nothing is saved, so the user can simply retry
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return await _save_turn(
        chat_id, current_user.id, data.content, answer, model_used, prepared
    )


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@router.post("/stream", dependencies=[Depends(rate_limited(MESSAGE_LIMIT))])
async def stream_message(
    chat_id: UUID,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Same as POST /messages, but streams the answer as Server-Sent Events so the
    user sees it being written instead of waiting for the whole response.

    Events: `start`, `model`, `delta`, `done`, `error`.
    """
    prepared, history, model_id = await _load_turn(db, chat_id, current_user.id, data)
    user_id = current_user.id

    async def event_stream():
        yield _sse("start", {"mode": prepared.mode, "sources": prepared.sources})
        pieces: list[str] = []
        model_used = model_id
        try:
            async for kind, value in ai_service.stream_response(
                model_id=model_id, messages=history, pdf_context=prepared.context
            ):
                if kind == "model":
                    model_used = value
                    yield _sse("model", {"model_used": value})
                else:
                    pieces.append(value)
                    yield _sse("delta", {"text": value})
        except AIServiceError as e:
            if pieces:
                # Partial answer — keep what the user already saw
                saved = await _save_turn(
                    chat_id, user_id, data.content, "".join(pieces), model_used, prepared
                )
                yield _sse("done", json.loads(MessageResponse.model_validate(saved).model_dump_json()))
            else:
                yield _sse("error", {"detail": str(e)})
            return
        except Exception:
            logger.exception("Streaming failed for chat %s", chat_id)
            yield _sse("error", {"detail": "Something went wrong. Please try again."})
            return

        saved = await _save_turn(
            chat_id, user_id, data.content, "".join(pieces), model_used, prepared
        )
        yield _sse("done", json.loads(MessageResponse.model_validate(saved).model_dump_json()))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
