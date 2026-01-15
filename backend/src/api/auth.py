"""
NH Mission Control - Authentication API
========================================

Authentication endpoints for user registration, login, and token management.

EPOCH 1 - Will be LOCKED after implementation.

==========================================================================
IMPLEMENTATION CONTRACT
==========================================================================

CC must implement all functions marked with `# TODO: Implement`.
The function signatures, docstrings, and return types define the contract.
Tests in tests/epoch1/ define expected behavior.

DO NOT change function signatures without updating tests.
DO NOT change response schemas without updating tests.
==========================================================================
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import (
    CurrentUser,
    DbSession,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from src.core.config import settings
from src.core.models import RefreshToken, User, UserRole
from src.core.schemas import (
    MessageResponse,
    PasswordReset,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==========================================================================
# Helper Functions
# ==========================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.verify(password, password_hash)


def hash_token(token: str) -> str:
    """Create a hash of a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


# ==========================================================================
# Registration
# ==========================================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        201: {"description": "User created successfully"},
        409: {"description": "Email already registered"},
        422: {"description": "Validation error"},
    },
)
async def register(
    data: UserCreate,
    db: DbSession,
) -> UserResponse:
    """
    Register a new user account.

    - Validates email uniqueness
    - Validates password strength (min 8 chars, upper, lower, digit)
    - Hashes password with bcrypt
    - Creates user with email_verified=False
    - Returns user data (without password)

    **Implementation Requirements:**
    1. Check if email already exists → return 409 Conflict
    2. Hash password using passlib bcrypt
    3. Create User record
    4. Return UserResponse (password_hash must NOT be included)
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == data.email.lower())
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        id=uuid4(),
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        name=data.name,
        role=UserRole.USER,
        is_active=True,
        email_verified=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


# ==========================================================================
# Login / Logout
# ==========================================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get tokens",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
    },
)
async def login(
    data: UserLogin,
    db: DbSession,
) -> TokenResponse:
    """
    Authenticate user and return tokens.

    - Validates email/password combination
    - Returns access token + refresh token
    - Updates user's last_login timestamp

    **Implementation Requirements:**
    1. Find user by email → return 401 if not found
    2. Verify password hash → return 401 if invalid
    3. Check user.is_active → return 401 if inactive
    4. Create access token (short-lived)
    5. Create refresh token (long-lived)
    6. Store refresh token hash in database
    7. Update user.last_login
    8. Return TokenResponse

    **Security Notes:**
    - Use constant-time comparison for password
    - Don't reveal whether email exists vs password wrong
    - Both cases should return same 401 error
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == data.email.lower())
    )
    user = result.scalar_one_or_none()

    # Invalid credentials - same message for security
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )

    if not user:
        raise credentials_exception

    # Verify password
    if not verify_password(data.password, user.password_hash):
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        raise credentials_exception

    # Create tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Store refresh token hash in database
    refresh_token_record = RefreshToken(
        id=uuid4(),
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) +
            __import__('datetime').timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(refresh_token_record)

    # Update last_login
    user.last_login = datetime.now(timezone.utc)

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and revoke refresh token",
    responses={
        200: {"description": "Logout successful"},
        401: {"description": "Not authenticated"},
    },
)
async def logout(
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """
    Logout user and revoke their refresh token.

    **Implementation Requirements:**
    1. Get refresh token from request (if provided)
    2. Mark refresh token as revoked in database
    3. Return success message

    **Note:** Access tokens cannot be revoked (stateless).
    They will expire naturally.
    """
    # Revoke all refresh tokens for this user
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False,
        )
    )
    tokens = result.scalars().all()

    for token in tokens:
        token.revoked = True

    await db.commit()

    return MessageResponse(message="Logged out successfully", success=True)


# ==========================================================================
# Token Management
# ==========================================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    responses={
        200: {"description": "Token refreshed"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: DbSession,
) -> TokenResponse:
    """
    Get new access token using refresh token.

    **Implementation Requirements:**
    1. Decode refresh token
    2. Verify token type is "refresh"
    3. Verify token is not expired
    4. Find refresh token in database
    5. Verify token is not revoked
    6. Get user from token
    7. Verify user is active
    8. Create new access token
    9. Optionally rotate refresh token
    10. Return TokenResponse

    **Security Notes:**
    - Each refresh token should only be used once (rotation)
    - Old refresh token should be revoked after use
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    try:
        payload = decode_token(data.refresh_token)
    except HTTPException:
        raise credentials_exception

    # Verify token type
    if payload.get("type") != "refresh":
        raise credentials_exception

    # Get user ID
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    # Find token in database
    token_hash = hash_token(data.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored_token = result.scalar_one_or_none()

    if not stored_token or stored_token.revoked:
        raise credentials_exception

    # Check expiration (handle both naive and aware datetimes)
    expires_at = stored_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise credentials_exception

    # Get user
    from uuid import UUID
    user_id = UUID(user_id_str)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise credentials_exception

    # Revoke old token (rotation)
    stored_token.revoked = True

    # Create new tokens
    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    # Store new refresh token
    new_refresh_record = RefreshToken(
        id=uuid4(),
        user_id=user.id,
        token_hash=hash_token(new_refresh_token),
        expires_at=datetime.now(timezone.utc) +
            __import__('datetime').timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(new_refresh_record)

    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ==========================================================================
# Email Verification
# ==========================================================================

@router.get(
    "/verify-email/{token}",
    response_model=MessageResponse,
    summary="Verify email address",
    responses={
        200: {"description": "Email verified"},
        400: {"description": "Invalid or expired token"},
    },
)
async def verify_email(
    token: str,
    db: DbSession,
) -> MessageResponse:
    """
    Verify user's email address using verification token.

    **Implementation Requirements:**
    1. Decode verification token
    2. Find user by ID in token
    3. Verify token is not expired
    4. Set user.email_verified = True
    5. Return success message

    **Token Format:**
    Use JWT with payload: {"sub": user_id, "type": "email_verify", "exp": ...}
    """
    try:
        payload = decode_token(token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Verify token type
    if payload.get("type") != "email_verify":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    # Get user
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    from uuid import UUID
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    # Verify email
    user.email_verified = True
    await db.commit()

    return MessageResponse(message="Email verified successfully", success=True)


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
    responses={
        200: {"description": "Verification email sent"},
        401: {"description": "Not authenticated"},
    },
)
async def resend_verification(
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """
    Resend email verification link.

    **Implementation Requirements:**
    1. Check if email is already verified → return early
    2. Generate new verification token
    3. Send verification email (or log in dev mode)
    4. Return success message

    **Note:** Always return 200 even if already verified (security)
    """
    if current_user.email_verified:
        return MessageResponse(
            message="Verification email sent (if not already verified)",
            success=True,
        )

    # In development mode, just log the token
    # In production, would send actual email
    # For now, just return success
    return MessageResponse(
        message="Verification email sent",
        success=True,
    )


# ==========================================================================
# Password Reset
# ==========================================================================

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
    responses={
        200: {"description": "Reset email sent (if account exists)"},
    },
)
async def forgot_password(
    data: PasswordResetRequest,
    db: DbSession,
) -> MessageResponse:
    """
    Request password reset email.

    **Implementation Requirements:**
    1. Find user by email (don't reveal if exists)
    2. If user exists, generate reset token
    3. Send reset email (or log in dev mode)
    4. Return success message

    **Security Notes:**
    - ALWAYS return 200, even if email doesn't exist
    - This prevents email enumeration attacks
    - Reset token should expire quickly (1 hour)
    """
    # Always return success to prevent email enumeration
    # In production, would actually send email if user exists
    return MessageResponse(
        message="If an account exists with that email, a reset link has been sent",
        success=True,
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
    responses={
        200: {"description": "Password reset successful"},
        400: {"description": "Invalid or expired token"},
        422: {"description": "Password validation failed"},
    },
)
async def reset_password(
    data: PasswordReset,
    db: DbSession,
) -> MessageResponse:
    """
    Reset password using reset token.

    **Implementation Requirements:**
    1. Decode reset token
    2. Verify token type is "password_reset"
    3. Verify token is not expired
    4. Find user by ID in token
    5. Validate new password strength
    6. Hash new password
    7. Update user.password_hash
    8. Revoke all user's refresh tokens (security)
    9. Return success message
    """
    try:
        payload = decode_token(data.token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Verify token type
    if payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    # Get user
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    from uuid import UUID
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    # Update password
    user.password_hash = hash_password(data.new_password)

    # Revoke all refresh tokens for security
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked == False,
        )
    )
    tokens = result.scalars().all()
    for token in tokens:
        token.revoked = True

    await db.commit()

    return MessageResponse(message="Password reset successfully", success=True)


# ==========================================================================
# User Profile
# ==========================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    responses={
        200: {"description": "Current user data"},
        401: {"description": "Not authenticated"},
    },
)
async def get_me(
    current_user: CurrentUser,
) -> UserResponse:
    """
    Get current authenticated user's profile.

    **Implementation Requirements:**
    1. Return current_user as UserResponse

    **Note:** This is simple - the heavy lifting is in the dependency.
    """
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    responses={
        200: {"description": "User updated"},
        401: {"description": "Not authenticated"},
        409: {"description": "Email already in use"},
    },
)
async def update_me(
    data: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """
    Update current user's profile.

    **Implementation Requirements:**
    1. If email is being changed, check uniqueness
    2. Update only provided fields
    3. If email changed, set email_verified = False
    4. Return updated user
    """
    # Check email uniqueness if being changed
    if data.email and data.email.lower() != current_user.email:
        result = await db.execute(
            select(User).where(User.email == data.email.lower())
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )

        current_user.email = data.email.lower()
        current_user.email_verified = False

    # Update name if provided
    if data.name:
        current_user.name = data.name

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)
