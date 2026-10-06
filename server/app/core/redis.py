import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

# Redis connection pool
redis_client: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    """Initialize and return the async Redis client. Raises if Redis is unreachable."""
    global redis_client
    client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        # from_url() is lazy — ping so a dead Redis fails here, not on every request
        await client.ping()
    except Exception:
        await client.aclose()
        raise
    redis_client = client
    return redis_client


async def close_redis():
    """Close the Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None


def get_redis() -> redis.Redis:
    """Get the Redis client instance."""
    if redis_client is None:
        raise RuntimeError("Redis is not initialized. Call init_redis() first.")
    return redis_client


# ===== Redis Helper Functions =====

async def blacklist_token(jti: str, ttl_seconds: int):
    """Add a JWT token ID to the blacklist (for logout)."""
    r = get_redis()
    await r.setex(f"blacklist:{jti}", ttl_seconds, "1")


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a JWT token ID has been blacklisted."""
    r = get_redis()
    result = await r.get(f"blacklist:{jti}")
    return result is not None


async def set_rate_limit(user_id: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
    """Simple rate limiter. Returns True if request is allowed, False if rate limited."""
    r = get_redis()
    key = f"rate_limit:{user_id}"
    current = await r.get(key)

    if current is None:
        await r.setex(key, window_seconds, 1)
        return True

    if int(current) >= max_requests:
        return False

    await r.incr(key)
    return True


async def cache_set(key: str, value: str, ttl_seconds: int = 3600):
    """Set a cached value with TTL."""
    r = get_redis()
    await r.setex(key, ttl_seconds, value)


async def cache_get(key: str) -> str | None:
    """Get a cached value."""
    r = get_redis()
    return await r.get(key)


async def cache_delete(key: str):
    """Delete a cached value."""
    r = get_redis()
    await r.delete(key)
