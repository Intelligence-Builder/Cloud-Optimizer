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
