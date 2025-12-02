"""
Trial models for Cloud Optimizer.

Implements trial period management and usage tracking.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cloud_optimizer.database import Base

if TYPE_CHECKING:
    from cloud_optimizer.models.user import User


class Trial(Base):
    """Trial period model."""

    __tablename__ = "trials"

    trial_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    extended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="trial",
    )
    usage: Mapped[list["TrialUsage"]] = relationship(
        "TrialUsage",
        back_populates="trial",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation of trial."""
        return f"<Trial {self.trial_id} for user {self.user_id}>"


class TrialUsage(Base):
    """Trial usage tracking model."""

    __tablename__ = "trial_usage"

    usage_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    trial_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("trials.trial_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dimension: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    trial: Mapped["Trial"] = relationship(
        "Trial",
        back_populates="usage",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("trial_id", "dimension", name="uq_trial_usage_dimension"),
    )

    def __repr__(self) -> str:
        """String representation of trial usage."""
        return f"<TrialUsage {self.dimension}={self.count} for trial {self.trial_id}>"
