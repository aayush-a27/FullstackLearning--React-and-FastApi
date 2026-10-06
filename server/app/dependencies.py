from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import decode_token
from app.core.redis import is_token_blacklisted
from app.services.auth_service import get_user_by_id
from uuid import UUID

# Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Dependency to extract and validate the current user from JWT token.
    Raises 401 if token is invalid, expired, or blacklisted.
    """
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token type is access
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Check if token is blacklisted (logged out)
    jti = payload.get("jti")
    if jti:
        try:
            if await is_token_blacklisted(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                )
        except (RuntimeError, RedisError):
            # Redis not initialized or went down — skip blacklist check
            pass

    # Fetch user from DB
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await get_user_by_id(db, UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user
