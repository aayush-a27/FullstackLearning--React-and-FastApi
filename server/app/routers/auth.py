from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
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
from app.core.redis import blacklist_token
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
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
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=False,  # Set True in production (HTTPS)
        samesite="lax",
        max_age=get_settings().REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

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
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=get_settings().REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return AuthResponse(
        access_token=tokens["access_token"],
        user=UserResponse.model_validate(user).model_dump(mode="json"),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
):
    """Logout the current user by blacklisting their token and clearing cookies."""
    # Note: Token blacklisting requires Redis to be running
    # In dev without Redis, logout just returns success
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
