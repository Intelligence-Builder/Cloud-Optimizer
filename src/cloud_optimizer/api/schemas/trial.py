"""
Trial schemas for Cloud Optimizer API.

Pydantic models for trial request/response validation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# Request schemas


class ExtendTrialRequest(BaseModel):
    """Request to extend trial period."""

    pass  # No parameters needed


# Response schemas


class UsageDimensionResponse(BaseModel):
    """Usage information for a single dimension."""

    current: int = Field(..., description="Current usage count")
    limit: int = Field(..., description="Maximum allowed usage")
    remaining: int = Field(..., description="Remaining usage")


class TrialStatusResponse(BaseModel):
    """Comprehensive trial status response."""

    trial_id: str = Field(..., description="Trial UUID")
    status: str = Field(..., description="Trial status (active, expired, converted)")
    is_active: bool = Field(..., description="Whether trial is currently active")
    started_at: str = Field(..., description="Trial start timestamp (ISO format)")
    expires_at: str = Field(..., description="Trial expiration timestamp (ISO format)")
    days_remaining: int = Field(..., description="Days remaining in trial")
    extended: bool = Field(..., description="Whether trial has been extended")
    can_extend: bool = Field(..., description="Whether trial can be extended")
    converted: bool = Field(..., description="Whether trial has been converted to paid")
    usage: dict[str, UsageDimensionResponse] = Field(
        ..., description="Usage by dimension"
    )


class ExtendTrialResponse(BaseModel):
    """Response for trial extension."""

    trial_id: str = Field(..., description="Trial UUID")
    expires_at: str = Field(..., description="New expiration timestamp (ISO format)")
    extended_at: str = Field(..., description="Extension timestamp (ISO format)")
    message: str = Field(..., description="Success message")


class TrialErrorResponse(BaseModel):
    """Error response for trial operations."""

    detail: str = Field(..., description="Error detail message")
    error_type: str = Field(..., description="Type of error")


# Analytics schemas (TRL-006)


class TrialAnalyticsResponse(BaseModel):
    """Analytics response for trial metrics (admin only)."""

    total_trials: int = Field(..., description="Total number of trials")
    active_trials: int = Field(..., description="Currently active trials")
    expired_trials: int = Field(..., description="Expired trials")
    converted_trials: int = Field(..., description="Converted to paid")
    conversion_rate: float = Field(..., description="Conversion rate percentage")
    average_days_to_conversion: float | None = Field(
        None, description="Average days from trial start to conversion"
    )
    extension_rate: float = Field(..., description="Percentage of trials extended")


class UsageAnalyticsResponse(BaseModel):
    """Usage analytics by dimension."""

    dimension: str = Field(..., description="Usage dimension name")
    total_usage: int = Field(..., description="Total usage across all trials")
    average_usage: float = Field(..., description="Average usage per trial")
    limit_reached_count: int = Field(..., description="Number of trials reaching limit")
    utilization_rate: float = Field(..., description="Average utilization percentage")


class TrialUsageBreakdownResponse(BaseModel):
    """Complete usage analytics breakdown."""

    dimensions: list[UsageAnalyticsResponse] = Field(
        ..., description="Analytics by dimension"
    )
    most_used_dimension: str | None = Field(
        None, description="Most frequently used dimension"
    )
    least_used_dimension: str | None = Field(
        None, description="Least frequently used dimension"
    )
