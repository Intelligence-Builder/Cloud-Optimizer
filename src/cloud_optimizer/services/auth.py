"""
Authentication service for Cloud Optimizer.

Implements user registration, login, refresh, and logout.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cloud_optimizer.auth.jwt import TokenPair, TokenService, get_token_service
from cloud_optimizer.auth.password import PasswordPolicy, get_password_policy
from cloud_optimizer.config import get_settings
from cloud_optimizer.models.session import Session
from cloud_optimizer.models.user import User


class AuthError(Exception):
    """Authentication error."""

    pass


class UserExistsError(AuthError):
    """User already exists."""

    pass


class InvalidCredentialsError(AuthError):
    """Invalid login credentials."""

    pass


class InvalidTokenError(AuthError):
    """Invalid or expired token."""

    pass


class PasswordPolicyError(AuthError):
    """Password does not meet policy requirements."""

    def __init__(self, errors: list[str]) -> None:
        """Initialize with validation errors."""
        self.errors = errors
        super().__init__("; ".join(errors))


class AuthService:
    """
    Authentication service.

    Handles:
    - User registration
    - Login with email/password
    - Token refresh
    - Logout (session revocation)
    - Profile updates
    - Password changes
    """

    def __init__(
        self,
        db: AsyncSession,
        password_policy: PasswordPolicy | None = None,
        token_service: TokenService | None = None,
    ) -> None:
        """
        Initialize auth service.

        Args:
            db: Async database session.
            password_policy: Optional password policy (uses default if not provided).
            token_service: Optional token service (uses default if not provided).
        """
        self.db = db
        self.password_policy = password_policy or get_password_policy()
        self.token_service = token_service or get_token_service()
        self.settings = get_settings()

    async def register(
        self,
        email: str,
        password: str,
        name: str | None = None,
    ) -> tuple[User, TokenPair]:
        """
        Register a new user.

        Args:
            email: User's email address.
            password: Plain text password.
            name: Optional display name.

        Returns:
            Tuple of (User, TokenPair).

        Raises:
            UserExistsError: If email is already registered.
            PasswordPolicyError: If password doesn't meet requirements.
        """
        # Validate password
        validation = self.password_policy.validate(password)
        if not validation.is_valid:
            raise PasswordPolicyError(validation.errors)

        # Check for existing user
        existing = await self._get_user_by_email(email)
        if existing:
            raise UserExistsError(f"User with email {email} already exists")

        # Create user
        password_hash = self.password_policy.hash(password)
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash,
            name=name,
        )
        self.db.add(user)
        await self.db.flush()

        # Create session and tokens
        token_pair = await self._create_session(user)

        return user, token_pair

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        """
        Authenticate user with email and password.

        Args:
            email: User's email address.
            password: Plain text password.

        Returns:
            Tuple of (User, TokenPair).

        Raises:
            InvalidCredentialsError: If email or password is invalid.
        """
        # Get user
        user = await self._get_user_by_email(email)
        if not user:
            raise InvalidCredentialsError("Invalid email or password")

        # Verify password
        if not self.password_policy.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()

        # Create session and tokens
        token_pair = await self._create_session(user)

        return user, token_pair

    async def refresh(self, refresh_token: str) -> TokenPair:
        """
        Refresh tokens using a valid refresh token.

        Args:
            refresh_token: JWT refresh token.

        Returns:
            New TokenPair with fresh tokens.

        Raises:
            InvalidTokenError: If refresh token is invalid or revoked.
        """
        # Validate refresh token
        try:
            payload = self.token_service.validate_refresh_token(refresh_token)
        except Exception as e:
            raise InvalidTokenError(str(e)) from e

        # Get session
        session_id = UUID(payload.jti) if payload.jti else None
        if not session_id:
            raise InvalidTokenError("Invalid refresh token")

        session = await self._get_session(session_id)
        if not session or not session.is_valid:
            raise InvalidTokenError("Session not found or revoked")

        # Verify token hash matches
        token_hash = self._hash_token(refresh_token)
        if session.token_hash != token_hash:
            raise InvalidTokenError("Token mismatch")

        # Get user
        user = await self._get_user_by_id(session.user_id)
        if not user:
            raise InvalidTokenError("User not found")

        # Create new token pair (reuse session)
        token_pair = self.token_service.create_token_pair(
            user_id=user.user_id,
            session_id=session.session_id,
        )

        # Update session with new token hash
        session.token_hash = self._hash_token(token_pair.refresh_token)
        session.expires_at = datetime.now(timezone.utc) + timedelta(
            days=self.settings.jwt_refresh_token_expire_days
        )
        await self.db.flush()

        return token_pair

    async def logout(self, refresh_token: str) -> None:
        """
        Logout by revoking the session.

        Args:
            refresh_token: JWT refresh token to revoke.
        """
        try:
            payload = self.token_service.validate_refresh_token(refresh_token)
            session_id = UUID(payload.jti) if payload.jti else None

            if session_id:
                session = await self._get_session(session_id)
                if session:
                    session.revoked_at = datetime.now(timezone.utc)
                    await self.db.flush()
        except Exception:
            # Silently ignore invalid tokens on logout
            pass

    async def get_current_user(self, user_id: UUID) -> User | None:
        """
        Get user by ID.

        Args:
            user_id: User's UUID.

        Returns:
            User if found, None otherwise.
        """
        return await self._get_user_by_id(user_id)

    async def update_profile(
        self,
        user_id: UUID,
        name: str | None = None,
        email: str | None = None,
    ) -> User:
        """
        Update user profile.

        Args:
            user_id: User's UUID.
            name: New display name (optional).
            email: New email (optional).

        Returns:
            Updated User.

        Raises:
            InvalidCredentialsError: If user not found.
            UserExistsError: If new email is already taken.
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise InvalidCredentialsError("User not found")

        if email and email.lower().strip() != user.email:
            existing = await self._get_user_by_email(email)
            if existing:
                raise UserExistsError(f"Email {email} is already taken")
            user.email = email.lower().strip()

        if name is not None:
            user.name = name

        user.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        return user

    async def change_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str,
    ) -> None:
        """
        Change user password.

        Args:
            user_id: User's UUID.
            old_password: Current password for verification.
            new_password: New password.

        Raises:
            InvalidCredentialsError: If user not found or old password wrong.
            PasswordPolicyError: If new password doesn't meet requirements.
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise InvalidCredentialsError("User not found")

        # Verify old password
        if not self.password_policy.verify(old_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")

        # Validate new password
        validation = self.password_policy.validate(new_password)
        if not validation.is_valid:
            raise PasswordPolicyError(validation.errors)

        # Update password
        user.password_hash = self.password_policy.hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        # Revoke all sessions (force re-login)
        await self._revoke_all_sessions(user_id)

    async def _get_user_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def _get_session(self, session_id: UUID) -> Session | None:
        """Get session by ID."""
        result = await self.db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def _create_session(self, user: User) -> TokenPair:
        """Create a new session and return token pair."""
        # Create session record first to get ID
        session = Session(
            user_id=user.user_id,
            token_hash="",  # Will be updated
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=self.settings.jwt_refresh_token_expire_days),
        )
        self.db.add(session)
        await self.db.flush()

        # Create tokens with session ID
        token_pair = self.token_service.create_token_pair(
            user_id=user.user_id,
            session_id=session.session_id,
        )

        # Update session with token hash
        session.token_hash = self._hash_token(token_pair.refresh_token)
        await self.db.flush()

        return token_pair

    async def _revoke_all_sessions(self, user_id: UUID) -> None:
        """Revoke all sessions for a user."""
        result = await self.db.execute(
            select(Session).where(
                Session.user_id == user_id,
                Session.revoked_at.is_(None),
            )
        )
        sessions = result.scalars().all()

        now = datetime.now(timezone.utc)
        for session in sessions:
            session.revoked_at = now

        await self.db.flush()

    def _hash_token(self, token: str) -> str:
        """Create a hash of a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()
