"""
Finding model for Cloud Optimizer security and cost findings.

Implements finding storage with deduplication and status tracking.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cloud_optimizer.database import Base

if TYPE_CHECKING:
    from cloud_optimizer.models.aws_account import AWSAccount
    from cloud_optimizer.models.scan_job import ScanJob


class FindingType(str, Enum):
    """Type of finding."""

    SECURITY = "security"
    COST = "cost"


class FindingSeverity(str, Enum):
    """Severity level of finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(str, Enum):
    """Status of finding."""

    OPEN = "open"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    FALSE_POSITIVE = "false_positive"


class Finding(Base):
    """Security or cost finding model."""

    __tablename__ = "findings"

    finding_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    scan_job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scan_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    aws_account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("aws_accounts.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    finding_type: Mapped[FindingType] = mapped_column(
        SQLEnum(FindingType, name="finding_type"),
        nullable=False,
        index=True,
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        SQLEnum(FindingSeverity, name="finding_severity"),
        nullable=False,
        index=True,
    )
    status: Mapped[FindingStatus] = mapped_column(
        SQLEnum(FindingStatus, name="finding_status"),
        nullable=False,
        default=FindingStatus.OPEN,
        index=True,
    )
    service: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    resource_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    resource_arn: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    region: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    recommendation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    compliance_frameworks: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
    )
    potential_savings: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Composite index for deduplication
    __table_args__ = (
        Index(
            "idx_finding_dedup",
            "aws_account_id",
            "rule_id",
            "resource_id",
            "status",
        ),
    )

    # Relationships
    scan_job: Mapped["ScanJob"] = relationship(
        "ScanJob",
        back_populates="findings",
    )
    aws_account: Mapped["AWSAccount"] = relationship("AWSAccount")

    def __repr__(self) -> str:
        """String representation of finding."""
        return f"<Finding {self.rule_id} - {self.severity.value} - {self.resource_id}>"
