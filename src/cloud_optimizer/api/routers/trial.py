"""
Trial API endpoints for Cloud Optimizer.

Implements trial status and extension endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from cloud_optimizer.api.schemas.trial import (
    ExtendTrialRequest,
    ExtendTrialResponse,
    TrialStatusResponse,
    UsageDimensionResponse,
)
from cloud_optimizer.database import AsyncSessionDep
from cloud_optimizer.middleware.auth import CurrentUser
from cloud_optimizer.services.trial import TrialError, TrialExtensionError, TrialService

router = APIRouter()


def get_trial_service(db: AsyncSessionDep) -> TrialService:
    """Dependency to get trial service with database session."""
    return TrialService(db)


TrialServiceDep = Annotated[TrialService, Depends(get_trial_service)]


@router.get(
    "/status",
    response_model=TrialStatusResponse,
    summary="Get trial status",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def get_trial_status(
    user_id: CurrentUser,
    trial_service: TrialServiceDep,
) -> TrialStatusResponse:
    """
    Get current trial status for authenticated user.

    Returns comprehensive trial information including:
    - Trial period dates and status
    - Usage by dimension (scans, questions, documents)
    - Extension eligibility
    - Conversion status
    """
    status_data = await trial_service.get_trial_status(user_id)

    # Convert usage dict to proper response models
    usage_response = {
        dimension: UsageDimensionResponse(**data)
        for dimension, data in status_data["usage"].items()
    }

    return TrialStatusResponse(
        trial_id=status_data["trial_id"],
        status=status_data["status"],
        is_active=status_data["is_active"],
        started_at=status_data["started_at"],
        expires_at=status_data["expires_at"],
        days_remaining=status_data["days_remaining"],
        extended=status_data["extended"],
        can_extend=status_data["can_extend"],
        converted=status_data["converted"],
        usage=usage_response,
    )


@router.post(
    "/extend",
    response_model=ExtendTrialResponse,
    summary="Extend trial period",
    responses={
        400: {"description": "Trial cannot be extended"},
        401: {"description": "Not authenticated"},
    },
)
async def extend_trial(
    user_id: CurrentUser,
    trial_service: TrialServiceDep,
) -> ExtendTrialResponse:
    """
    Request one-time trial extension.

    Extends the trial period by 7 days. Can only be used once per trial.

    Returns:
        Updated trial information with new expiration date.

    Raises:
        400: If trial has already been extended or has been converted.
    """
    try:
        trial = await trial_service.extend_trial(user_id)

        return ExtendTrialResponse(
            trial_id=str(trial.trial_id),
            expires_at=trial.expires_at.isoformat(),
            extended_at=trial.extended_at.isoformat() if trial.extended_at else "",
            message="Trial extended by 7 days",
        )
    except TrialExtensionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except TrialError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
