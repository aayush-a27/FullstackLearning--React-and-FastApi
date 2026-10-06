"""
Small JSON cache on top of Redis.

Every helper fails open: if Redis is down, reads miss and writes are dropped so
the request simply hits Postgres instead of failing.
"""
import json
import logging
from uuid import UUID
from redis.exceptions import RedisError
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

CHAT_LIST_TTL_SECONDS = 300
MESSAGES_TTL_SECONDS = 300


def chat_list_key(user_id: UUID) -> str:
    return f"cache:chats:{user_id}"


def messages_key(chat_id: UUID) -> str:
    return f"cache:messages:{chat_id}"


async def get_json(key: str):
    """Return the cached value, or None on a miss or any Redis problem."""
    try:
        raw = await get_redis().get(key)
    except (RuntimeError, RedisError):
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Discarding malformed cache entry at %s", key)
        return None


async def set_json(key: str, value, ttl_seconds: int):
    """Cache a JSON-serializable value. Silently skipped if Redis is unavailable."""
    try:
        await get_redis().setex(key, ttl_seconds, json.dumps(value, default=str))
    except (RuntimeError, RedisError):
        pass


async def invalidate(*keys: str):
    """Drop cache entries after a write. Silently skipped if Redis is unavailable."""
    if not keys:
        return
    try:
        await get_redis().delete(*keys)
    except (RuntimeError, RedisError):
        pass
