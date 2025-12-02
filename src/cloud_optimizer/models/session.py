"""
Session model for Cloud Optimizer authentication.

Implements session storage for refresh token management.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cloud_optimizer.database import Base

if TYPE_CHECKING:
    from cloud_optimizer.models.user import User


class Session(Base):
    """User session model for refresh token tracking."""

    __tablename__ = "sessions"

    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
    )

    @property
    def is_valid(self) -> bool:
        """Check if session is still valid."""
        if self.revoked_at is not None:
            return False
        return datetime.now(self.expires_at.tzinfo) < self.expires_at

    def __repr__(self) -> str:
        """String representation of session."""
        return f"<Session {self.session_id} for user {self.user_id}>"
