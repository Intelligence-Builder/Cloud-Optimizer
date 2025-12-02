"""Findings API endpoints."""
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from cloud_optimizer.api.schemas.findings import (
    FindingListResponse,
    FindingResponse,
    FindingSeverity,
    FindingStatus,
    FindingSummaryResponse,
    UpdateFindingStatusRequest,
)
from cloud_optimizer.database import AsyncSessionDep
from cloud_optimizer.middleware.auth import CurrentUser
from cloud_optimizer.models.finding import FindingSeverity as ModelSeverity
from cloud_optimizer.models.finding import FindingStatus as ModelStatus
from cloud_optimizer.services.findings import FindingsService

router = APIRouter()


def get_findings_service(db: AsyncSessionDep) -> FindingsService:
    """Dependency to get findings service with database session.

    Args:
        db: Database session

    Returns:
        FindingsService instance
    """
    return FindingsService(db)


FindingsServiceDep = Annotated[FindingsService, Depends(get_findings_service)]


@router.get(
    "/accounts/{aws_account_id}",
    response_model=FindingListResponse,
    summary="List findings for an AWS account",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def list_findings(
    aws_account_id: UUID,
    user_id: CurrentUser,
    findings_service: FindingsServiceDep,
    severity: Optional[FindingSeverity] = None,
    status: Optional[FindingStatus] = None,
    service: Optional[str] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FindingListResponse:
    """List findings for an AWS account with optional filters.

    Args:
        aws_account_id: AWS account ID
        user_id: Current authenticated user ID
        findings_service: Findings service instance
        severity: Filter by severity level
        status: Filter by status
        service: Filter by AWS service
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of findings with pagination info
    """
    # TODO: Verify user owns the AWS account
    findings = await findings_service.get_findings_by_account(
        aws_account_id=aws_account_id,
        severity=ModelSeverity(severity.value) if severity else None,
        status=ModelStatus(status.value) if status else None,
        service=service,
        limit=limit,
        offset=offset,
    )

    return FindingListResponse(
        findings=[FindingResponse.model_validate(f) for f in findings],
        total=len(findings),  # Would be from COUNT query in production
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{finding_id}",
    response_model=FindingResponse,
    summary="Get finding by ID",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Finding not found"},
    },
)
async def get_finding(
    finding_id: UUID,
    user_id: CurrentUser,
    findings_service: FindingsServiceDep,
) -> FindingResponse:
    """Get a specific finding by ID.

    Args:
        finding_id: Finding ID
        user_id: Current authenticated user ID
        findings_service: Findings service instance

    Returns:
        Finding details

    Raises:
        HTTPException: If finding not found
    """
    # TODO: Verify user owns the AWS account associated with this finding
    finding = await findings_service.get_finding(finding_id)

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found"
        )

    return FindingResponse.model_validate(finding)


@router.patch(
    "/{finding_id}/status",
    response_model=FindingResponse,
    summary="Update finding status",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Finding not found"},
    },
)
async def update_finding_status(
    finding_id: UUID,
    request: UpdateFindingStatusRequest,
    user_id: CurrentUser,
    findings_service: FindingsServiceDep,
) -> FindingResponse:
    """Update a finding's status.

    Args:
        finding_id: Finding ID
        request: Status update request
        user_id: Current authenticated user ID
        findings_service: Findings service instance

    Returns:
        Updated finding

    Raises:
        HTTPException: If finding not found
    """
    # TODO: Verify user owns the AWS account associated with this finding
    finding = await findings_service.update_status(
        finding_id, ModelStatus(request.status.value)
    )

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found"
        )

    return FindingResponse.model_validate(finding)


@router.get(
    "/accounts/{aws_account_id}/summary",
    response_model=FindingSummaryResponse,
    summary="Get findings summary",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def get_findings_summary(
    aws_account_id: UUID,
    user_id: CurrentUser,
    findings_service: FindingsServiceDep,
) -> FindingSummaryResponse:
    """Get summary of findings for an AWS account.

    Args:
        aws_account_id: AWS account ID
        user_id: Current authenticated user ID
        findings_service: Findings service instance

    Returns:
        Summary with counts by severity and status
    """
    # TODO: Verify user owns the AWS account
    summary = await findings_service.get_summary(aws_account_id)
    return FindingSummaryResponse(**summary)
