"""
Per-user rate limiting backed by Redis.

Limits are deliberately generous — they exist to stop runaway loops and abuse of
the free-tier AI quota, not to get in a real user's way. If Redis is unavailable
requests are allowed through: losing the cache shouldn't take the app down.
"""
import logging
from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from redis.exceptions import RedisError
from app.core.redis import get_redis
from app.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimit:
    name: str
    max_requests: int
    window_seconds: int

    @property
    def description(self) -> str:
        unit = "minute" if self.window_seconds == 60 else f"{self.window_seconds} seconds"
        return f"{self.max_requests} per {unit}"


# AI calls cost real quota, so they're the tightest limit
MESSAGE_LIMIT = RateLimit("messages", max_requests=20, window_seconds=60)
# Uploads kick off embedding work in the background
UPLOAD_LIMIT = RateLimit("uploads", max_requests=10, window_seconds=60)
# Account creation, to slow down automated signups
REGISTER_LIMIT = RateLimit("register", max_requests=5, window_seconds=300)


async def check_rate_limit(limit: RateLimit, identifier: str) -> tuple[bool, int]:
    """
    Count one request against `limit`. Returns (allowed, seconds_until_reset).
    Fails open when Redis is down.
    """
    key = f"rate_limit:{limit.name}:{identifier}"
    try:
        redis = get_redis()
        # INCR then EXPIRE on first hit: atomic enough for a fixed window
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, limit.window_seconds)
            return True, limit.window_seconds
        if count > limit.max_requests:
            ttl = await redis.ttl(key)
            return False, max(ttl, 1)
        return True, limit.window_seconds
    except (RuntimeError, RedisError) as e:
        logger.debug("Rate limiting unavailable (%s) — allowing request", type(e).__name__)
        return True, 0


def rate_limited(limit: RateLimit):
    """
    FastAPI dependency enforcing `limit` per authenticated user.

    Usage: `dependencies=[Depends(rate_limited(MESSAGE_LIMIT))]`
    """

    async def dependency(current_user: User = Depends(get_current_user)):
        allowed, retry_after = await check_rate_limit(limit, str(current_user.id))
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"You're going a bit fast — the limit is {limit.description}. "
                    f"Try again in {retry_after} second{'s' if retry_after != 1 else ''}."
                ),
                headers={"Retry-After": str(retry_after)},
            )

    return dependency


def rate_limited_by_ip(limit: RateLimit):
    """Same, but keyed on client IP — for endpoints with no authenticated user."""
    from fastapi import Request

    async def dependency(request: Request):
        client = request.client.host if request.client else "unknown"
        allowed, retry_after = await check_rate_limit(limit, client)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
