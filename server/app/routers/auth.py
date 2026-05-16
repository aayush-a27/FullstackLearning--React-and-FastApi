from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, AuthResponse
from app.schemas.user import UserResponse
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

    return AuthResponse(
        access_token=tokens["access_token"],
        user=UserResponse.model_validate(user).model_dump(mode="json"),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
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

    return AuthResponse(
        access_token=tokens["access_token"],
        user=UserResponse.model_validate(user).model_dump(mode="json"),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
):
    """Logout the current user by blacklisting their token."""
    # Note: Token blacklisting requires Redis to be running
    # In dev without Redis, logout just returns success
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/refresh", response_model=dict)
async def refresh_token(
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh an access token.
    In production, the refresh token would come from an httpOnly cookie.
    For now, this is a placeholder endpoint.
    """
    # TODO: Implement refresh token logic with httpOnly cookies
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not yet implemented. Use login to get a new token.",
    )
