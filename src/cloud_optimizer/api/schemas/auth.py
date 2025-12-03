"""
Authentication schemas for Cloud Optimizer API.

Pydantic models for auth request/response validation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# Request schemas


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    name: str | None = Field(None, max_length=255, description="Display name")


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Logout request."""

    refresh_token: str = Field(..., description="Refresh token to revoke")


class UpdateProfileRequest(BaseModel):
    """Update profile request."""

    name: str | None = Field(None, max_length=255, description="New display name")
    email: EmailStr | None = Field(None, description="New email address")


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""

    email: EmailStr = Field(..., description="Email address for password reset")


class ResetPasswordRequest(BaseModel):
    """Reset password request."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")


# Response schemas


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")


class UserResponse(BaseModel):
    """User information response."""

    user_id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: str | None = Field(None, description="Display name")
    is_admin: bool = Field(..., description="Admin status")
    email_verified: bool = Field(..., description="Email verification status")
    created_at: datetime = Field(..., description="Account creation time")
    last_login_at: datetime | None = Field(None, description="Last login time")

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Authentication response with user and tokens."""

    user: UserResponse = Field(..., description="User information")
    tokens: TokenResponse = Field(..., description="Authentication tokens")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str = Field(..., description="Response message")


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str = Field(..., description="Error detail message")
    errors: list[str] | None = Field(None, description="Validation errors")
