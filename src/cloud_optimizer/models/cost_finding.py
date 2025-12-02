"""Cost finding and summary models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum as SQLEnum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from cloud_optimizer.database import Base


class CostCategory(str, Enum):
    """Cost optimization category types."""

    UNUSED = "unused"
    RIGHTSIZING = "rightsizing"
    RESERVED = "reserved"
    SAVINGS_PLAN = "savings_plan"
    SPOT = "spot"


class CostFinding(Base):
    """Cost optimization finding model.

    Represents a cost savings opportunity identified during scanning.
    """

    __tablename__ = "cost_findings"

    finding_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    scan_job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scan_jobs.job_id"), nullable=False
    )
    aws_account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("aws_accounts.account_id"), nullable=False
    )
    category: Mapped[CostCategory] = mapped_column(
        SQLEnum(CostCategory), nullable=False
    )
    service: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(500), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    current_cost: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_savings: Mapped[float] = mapped_column(Float, default=0.0)
    savings_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CostSummary(Base):
    """Cost summary model.

    Aggregates cost findings for reporting and analytics.
    """

    __tablename__ = "cost_summaries"

    summary_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    scan_job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scan_jobs.job_id"), nullable=False
    )
    aws_account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("aws_accounts.account_id"), nullable=False
    )
    total_monthly_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_potential_savings: Mapped[float] = mapped_column(Float, default=0.0)
    savings_by_category: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    cost_by_service: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
