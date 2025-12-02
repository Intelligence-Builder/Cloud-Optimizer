"""Findings API schemas."""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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


class FindingType(str, Enum):
    """Type of finding."""

    SECURITY = "security"
    COST = "cost"


class FindingResponse(BaseModel):
    """Response schema for a finding."""

    finding_id: UUID
    rule_id: str
    finding_type: FindingType
    severity: FindingSeverity
    status: FindingStatus
    service: str
    resource_type: str
    resource_id: str
    resource_arn: str | None = None
    region: str
    title: str
    description: str
    recommendation: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    compliance_frameworks: list[str] = Field(default_factory=list)
    potential_savings: float | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class FindingListResponse(BaseModel):
    """Response schema for a list of findings."""

    findings: list[FindingResponse]
    total: int
    limit: int
    offset: int


class FindingSummaryResponse(BaseModel):
    """Response schema for findings summary."""

    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]


class UpdateFindingStatusRequest(BaseModel):
    """Request schema for updating finding status."""

    status: FindingStatus
