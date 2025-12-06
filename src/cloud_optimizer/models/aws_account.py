"""
AWS Account connection model.

Implements AWS account connection management with support for IAM role and access key authentication.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cloud_optimizer.database import Base

if TYPE_CHECKING:
    from cloud_optimizer.models.scan_job import ScanJob
    from cloud_optimizer.models.user import User


class ConnectionType(str, Enum):
    """Type of AWS account connection."""

    IAM_ROLE = "iam_role"
    ACCESS_KEYS = "access_keys"


class ConnectionStatus(str, Enum):
    """Status of AWS account connection."""

    PENDING = "pending"
    ACTIVE = "active"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class AWSAccount(Base):
    """AWS Account connection model."""

    __tablename__ = "aws_accounts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "aws_account_id",
            name="uq_aws_account_user_account",
        ),
        Index("ix_aws_accounts_status", "status"),
    )

    account_id: Mapped[UUID] = mapped_column(
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
    aws_account_id: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
    )
    friendly_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    connection_type: Mapped[ConnectionType] = mapped_column(
        SQLEnum(ConnectionType, name="connection_type"),
        nullable=False,
    )
    role_arn: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    access_key_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )
    secret_key_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )
    status: Mapped[ConnectionStatus] = mapped_column(
        SQLEnum(ConnectionStatus, name="connection_status"),
        nullable=False,
        default=ConnectionStatus.PENDING,
    )
    last_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    default_region: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="us-east-1",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="aws_accounts",
    )
    scan_jobs: Mapped[list["ScanJob"]] = relationship(
        "ScanJob",
        back_populates="aws_account",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation of AWS account."""
        return f"<AWSAccount {self.aws_account_id} ({self.friendly_name or 'unnamed'})>"
