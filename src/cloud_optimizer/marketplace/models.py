"""
AWS Marketplace data models.

Defines Pydantic models for license validation, usage reporting,
and marketplace configuration.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LicenseStatus(str, Enum):
    """License status enumeration."""

    VALID = "valid"
    TRIAL = "trial"
    TRIAL_EXPIRED = "trial_expired"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    INVALID = "invalid"


class LicenseStatusResponse(BaseModel):
    """Response model for license validation."""

    status: str = Field(description="License status")
    customer_id: str | None = Field(
        default=None,
        description="AWS Marketplace customer identifier",
    )
    valid_until: datetime | None = Field(
        default=None,
        description="License expiration timestamp",
    )
    features_enabled: list[str] = Field(
        default_factory=list,
        description="List of enabled features for this license",
    )


class UsageReportResponse(BaseModel):
    """Response model for usage metering reports."""

    dimension: str = Field(description="Usage dimension being reported")
    quantity: int = Field(description="Usage quantity")
    reported_at: datetime = Field(description="Timestamp of usage report")
    metering_record_id: str | None = Field(
        default=None,
        description="AWS Marketplace metering record identifier",
    )


class MarketplaceConfig(BaseModel):
    """Configuration for AWS Marketplace integration."""

    enabled: bool = Field(
        default=True,
        description="Whether marketplace integration is enabled",
    )
    product_code: str = Field(
        default="",
        description="AWS Marketplace product code",
    )
    trial_duration_days: int = Field(
        default=14,
        description="Trial period duration in days",
    )
    trial_limits: dict[str, int] = Field(
        default_factory=lambda: {
            "scans": 10,
            "chat_questions": 50,
            "documents": 5,
        },
        description="Usage limits for trial mode",
    )
