"""
JWT token handling for Cloud Optimizer.

Implements JWT token creation, validation, and refresh token management.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from cloud_optimizer.config import get_settings


@dataclass
class TokenPair:
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0  # Access token expiry in seconds


@dataclass
class TokenPayload:
    """Decoded token payload."""

    sub: str  # User ID
    exp: datetime
    iat: datetime
    token_type: str  # "access" or "refresh"
    jti: str | None = None  # JWT ID for refresh tokens


class TokenError(Exception):
    """Token validation or generation error."""

    pass


class TokenService:
    """
    JWT token service for authentication.

    Handles:
    - Access token generation (15 min expiry)
    - Refresh token generation (7 day expiry)
    - Token validation and decoding
    """

    TOKEN_TYPE_ACCESS = "access"
    TOKEN_TYPE_REFRESH = "refresh"

    def __init__(self) -> None:
        """Initialize token service with settings."""
        settings = get_settings()
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_expire_days = settings.jwt_refresh_token_expire_days

    def create_access_token(
        self,
        user_id: UUID,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create an access token for a user.

        Args:
            user_id: User's UUID.
            extra_claims: Optional additional claims to include.

        Returns:
            Encoded JWT access token.
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=self.access_expire_minutes)

        payload = {
            "sub": str(user_id),
            "exp": expires,
            "iat": now,
            "token_type": self.TOKEN_TYPE_ACCESS,
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> str:
        """
        Create a refresh token for a user session.

        Args:
            user_id: User's UUID.
            session_id: Session UUID for tracking.

        Returns:
            Encoded JWT refresh token.
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=self.refresh_expire_days)

        payload = {
            "sub": str(user_id),
            "exp": expires,
            "iat": now,
            "token_type": self.TOKEN_TYPE_REFRESH,
            "jti": str(session_id),  # Use session ID as JWT ID
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_token_pair(
        self,
        user_id: UUID,
        session_id: UUID,
        extra_claims: dict[str, Any] | None = None,
    ) -> TokenPair:
        """
        Create both access and refresh tokens.

        Args:
            user_id: User's UUID.
            session_id: Session UUID for refresh token tracking.
            extra_claims: Optional additional claims for access token.

        Returns:
            TokenPair with both tokens.
        """
        access_token = self.create_access_token(user_id, extra_claims)
        refresh_token = self.create_refresh_token(user_id, session_id)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.access_expire_minutes * 60,
        )

    def decode_token(self, token: str) -> TokenPayload:
        """
        Decode and validate a JWT token.

        Args:
            token: Encoded JWT token.

        Returns:
            Decoded TokenPayload.

        Raises:
            TokenError: If token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            return TokenPayload(
                sub=payload["sub"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                token_type=payload.get("token_type", self.TOKEN_TYPE_ACCESS),
                jti=payload.get("jti"),
            )
        except JWTError as e:
            raise TokenError(f"Invalid token: {e}") from e

    def validate_access_token(self, token: str) -> TokenPayload:
        """
        Validate an access token.

        Args:
            token: Encoded JWT access token.

        Returns:
            Decoded TokenPayload.

        Raises:
            TokenError: If token is invalid, expired, or not an access token.
        """
        payload = self.decode_token(token)

        if payload.token_type != self.TOKEN_TYPE_ACCESS:
            raise TokenError("Token is not an access token")

        return payload

    def validate_refresh_token(self, token: str) -> TokenPayload:
        """
        Validate a refresh token.

        Args:
            token: Encoded JWT refresh token.

        Returns:
            Decoded TokenPayload with session ID in jti.

        Raises:
            TokenError: If token is invalid, expired, or not a refresh token.
        """
        payload = self.decode_token(token)

        if payload.token_type != self.TOKEN_TYPE_REFRESH:
            raise TokenError("Token is not a refresh token")

        if not payload.jti:
            raise TokenError("Refresh token missing session ID")

        return payload

    def get_user_id_from_token(self, token: str) -> UUID:
        """
        Extract user ID from any valid token.

        Args:
            token: Encoded JWT token.

        Returns:
            User's UUID.

        Raises:
            TokenError: If token is invalid.
        """
        payload = self.decode_token(token)
        return UUID(payload.sub)


# Singleton instance
_token_service: TokenService | None = None


def get_token_service() -> TokenService:
    """Get or create token service instance."""
    global _token_service
    if _token_service is None:
        _token_service = TokenService()
    return _token_service
