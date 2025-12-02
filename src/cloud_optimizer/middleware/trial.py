"""
Trial enforcement middleware for Cloud Optimizer.

Provides dependency for checking trial limits before protected actions.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from cloud_optimizer.database import AsyncSessionDep
from cloud_optimizer.middleware.auth import CurrentUser
from cloud_optimizer.services.trial import (
    TrialExpiredError,
    TrialLimitExceededError,
    TrialService,
)


async def check_trial_limit(
    dimension: str,
    user_id: CurrentUser,
    db: AsyncSessionDep,
) -> bool:
    """
    Check if user can perform action within trial limits.

    Args:
        dimension: Usage dimension to check (scans, questions, documents).
        user_id: Authenticated user ID.
        db: Database session.

    Returns:
        True if action is allowed.

    Raises:
        HTTPException: If trial is expired or limit exceeded.
    """
    trial_service = TrialService(db)

    try:
        return await trial_service.check_limit(user_id, dimension)
    except TrialExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except TrialLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        ) from e


async def record_trial_usage(
    dimension: str,
    user_id: UUID,
    db: AsyncSessionDep,
    count: int = 1,
) -> None:
    """
    Record usage for a dimension.

    Args:
        dimension: Usage dimension (scans, questions, documents).
        user_id: User ID.
        db: Database session.
        count: Amount to increment (default: 1).
    """
    trial_service = TrialService(db)
    await trial_service.record_usage(user_id, dimension, count)


# Dependency factories for different dimensions


async def check_scan_limit(
    user_id: CurrentUser,
    db: AsyncSessionDep,
) -> bool:
    """Check if user can perform a scan."""
    return await check_trial_limit("scans", user_id, db)


async def check_question_limit(
    user_id: CurrentUser,
    db: AsyncSessionDep,
) -> bool:
    """Check if user can ask a question."""
    return await check_trial_limit("questions", user_id, db)


async def check_document_limit(
    user_id: CurrentUser,
    db: AsyncSessionDep,
) -> bool:
    """Check if user can add a document."""
    return await check_trial_limit("documents", user_id, db)


# Type aliases for dependency injection
RequireScanLimit = Annotated[bool, Depends(check_scan_limit)]
RequireQuestionLimit = Annotated[bool, Depends(check_question_limit)]
RequireDocumentLimit = Annotated[bool, Depends(check_document_limit)]
