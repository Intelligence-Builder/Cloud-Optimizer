"""
Scan job tracking model.

Implements scan job orchestration and progress tracking for security and cost scans.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cloud_optimizer.database import Base

if TYPE_CHECKING:
    from cloud_optimizer.models.aws_account import AWSAccount
    from cloud_optimizer.models.finding import Finding
    from cloud_optimizer.models.user import User


class ScanStatus(str, Enum):
    """Status of a scan job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanType(str, Enum):
    """Type of scan to perform."""

    SECURITY = "security"
    COST = "cost"
    FULL = "full"


class ScanJob(Base):
    """Scan job tracking model."""

    __tablename__ = "scan_jobs"

    job_id: Mapped[UUID] = mapped_column(
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
    aws_account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("aws_accounts.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_type: Mapped[ScanType] = mapped_column(
        SQLEnum(ScanType, name="scan_type"),
        nullable=False,
    )
    status: Mapped[ScanStatus] = mapped_column(
        SQLEnum(ScanStatus, name="scan_status"),
        nullable=False,
        default=ScanStatus.PENDING,
    )
    services_to_scan: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_findings: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error_message: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    aws_account: Mapped["AWSAccount"] = relationship(
        "AWSAccount",
        back_populates="scan_jobs",
    )
    findings: Mapped[list["Finding"]] = relationship(
        "Finding",
        back_populates="scan_job",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation of scan job."""
        return f"<ScanJob {self.job_id} ({self.scan_type.value}, {self.status.value})>"
