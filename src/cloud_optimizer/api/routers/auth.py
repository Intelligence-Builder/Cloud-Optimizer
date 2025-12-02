"""
Authentication API endpoints for Cloud Optimizer.

Implements user registration, login, token refresh, and profile management.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from cloud_optimizer.api.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from cloud_optimizer.database import AsyncSessionDep
from cloud_optimizer.middleware.auth import get_current_user
from cloud_optimizer.services.auth import (
    AuthService,
    InvalidCredentialsError,
    InvalidTokenError,
    PasswordPolicyError,
    UserExistsError,
)

router = APIRouter()


def get_auth_service(db: AsyncSessionDep) -> AuthService:
    """Dependency to get auth service with database session."""
    return AuthService(db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentUser = Annotated[UUID, Depends(get_current_user)]


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        400: {"description": "Password policy violation"},
        409: {"description": "User already exists"},
    },
)
async def register(
    request: RegisterRequest,
    auth_service: AuthServiceDep,
) -> AuthResponse:
    """
    Register a new user account.

    Creates a new user with the provided email and password.
    Returns user information and authentication tokens.
    """
    try:
        user, token_pair = await auth_service.register(
            email=request.email,
            password=request.password,
            name=request.name,
        )

        return AuthResponse(
            user=UserResponse.model_validate(user),
            tokens=TokenResponse(
                access_token=token_pair.access_token,
                refresh_token=token_pair.refresh_token,
                token_type=token_pair.token_type,
                expires_in=token_pair.expires_in,
            ),
        )
    except PasswordPolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet requirements",
        ) from e
    except UserExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with email and password",
    responses={
        401: {"description": "Invalid credentials"},
    },
)
async def login(
    request: LoginRequest,
    auth_service: AuthServiceDep,
) -> AuthResponse:
    """
    Authenticate user with email and password.

    Returns user information and authentication tokens.
    """
    try:
        user, token_pair = await auth_service.login(
            email=request.email,
            password=request.password,
        )

        return AuthResponse(
            user=UserResponse.model_validate(user),
            tokens=TokenResponse(
                access_token=token_pair.access_token,
                refresh_token=token_pair.refresh_token,
                token_type=token_pair.token_type,
                expires_in=token_pair.expires_in,
            ),
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    responses={
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh(
    request: RefreshRequest,
    auth_service: AuthServiceDep,
) -> TokenResponse:
    """
    Refresh access token using a valid refresh token.

    Returns new access and refresh tokens.
    """
    try:
        token_pair = await auth_service.refresh(request.refresh_token)

        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and revoke session",
)
async def logout(
    request: LogoutRequest,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    """
    Logout by revoking the refresh token session.

    Always returns success even if token is invalid.
    """
    await auth_service.logout(request.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def get_me(
    user_id: CurrentUser,
    auth_service: AuthServiceDep,
) -> UserResponse:
    """
    Get the current authenticated user's profile.

    Requires a valid access token.
    """
    user = await auth_service.get_current_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    responses={
        401: {"description": "Not authenticated"},
        409: {"description": "Email already taken"},
    },
)
async def update_me(
    request: UpdateProfileRequest,
    user_id: CurrentUser,
    auth_service: AuthServiceDep,
) -> UserResponse:
    """
    Update the current authenticated user's profile.

    Requires a valid access token.
    """
    try:
        user = await auth_service.update_profile(
            user_id=user_id,
            name=request.name,
            email=request.email,
        )

        return UserResponse.model_validate(user)
    except UserExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e


@router.put(
    "/password",
    response_model=MessageResponse,
    summary="Change password",
    responses={
        400: {"description": "Password policy violation"},
        401: {"description": "Not authenticated or wrong password"},
    },
)
async def change_password(
    request: ChangePasswordRequest,
    user_id: CurrentUser,
    auth_service: AuthServiceDep,
) -> MessageResponse:
    """
    Change the current user's password.

    Requires the current password for verification.
    All existing sessions will be revoked.
    """
    try:
        await auth_service.change_password(
            user_id=user_id,
            old_password=request.old_password,
            new_password=request.new_password,
        )

        return MessageResponse(
            message="Password changed successfully. Please login again."
        )
    except PasswordPolicyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password does not meet requirements",
        ) from e
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e
