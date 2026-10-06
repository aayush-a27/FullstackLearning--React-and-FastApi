import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPAuthorizationCredentials
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, AuthResponse
from app.schemas.user import UserResponse
from app.config import get_settings
from app.services.auth_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_username,
    generate_tokens,
)
from app.core.security import decode_token
from app.core.redis import blacklist_token, is_token_blacklisted
from app.core.rate_limit import rate_limited_by_ip, REGISTER_LIMIT
from app.dependencies import get_current_user, security
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


def _set_refresh_cookie(response: Response, refresh_token: str):
    """Store the refresh token in an httpOnly cookie (never readable by JS)."""
    settings = get_settings()
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,  # True once served over HTTPS
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )



@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limited_by_ip(REGISTER_LIMIT))],
)
async def register(
    request: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    # Check if email already exists
    existing = await get_user_by_email(db, request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check if username already exists
    existing = await get_user_by_username(db, request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Create user
    user = await create_user(
        db,
        username=request.username,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
    )

    # Generate tokens
    tokens = generate_tokens(user)

    # Set HTTP-only refresh token cookie
    _set_refresh_cookie(response, tokens["refresh_token"])

    return AuthResponse(
        access_token=tokens["access_token"],
        user=UserResponse.model_validate(user).model_dump(mode="json"),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a user and return tokens."""
    user = await authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    tokens = generate_tokens(user)

    # Set HTTP-only refresh token cookie
    _set_refresh_cookie(response, tokens["refresh_token"])

    return AuthResponse(
        access_token=tokens["access_token"],
        user=UserResponse.model_validate(user).model_dump(mode="json"),
    )


async def _blacklist_until_expiry(payload: dict | None):
    """Blacklist a decoded token's jti for the rest of its lifetime."""
    if not payload or not payload.get("jti") or not payload.get("exp"):
        return
    ttl = int(payload["exp"] - datetime.now(timezone.utc).timestamp())
    if ttl > 0:
        await blacklist_token(payload["jti"], ttl)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
):
    """Logout the current user by blacklisting their tokens and clearing cookies."""
    try:
        await _blacklist_until_expiry(decode_token(credentials.credentials))
        refresh_cookie = request.cookies.get("refresh_token")
        if refresh_cookie:
            await _blacklist_until_expiry(decode_token(refresh_cookie))
    except (RuntimeError, RedisError):
        # Redis not available — tokens stay valid until they expire
        logger.warning("Logout without Redis: tokens were not blacklisted")

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key="refresh_token")
    return response


@router.post("/refresh", response_model=dict)
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh an access token using an httpOnly cookie.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    try:
        if payload.get("jti") and await is_token_blacklisted(payload["jti"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )
    except (RuntimeError, RedisError):
        pass

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    import uuid
    from app.services.auth_service import get_user_by_id
    from app.core.security import create_access_token
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID format")

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Generate a new access token
    new_access_token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": new_access_token}
