"""AWS Account connection API endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from cloud_optimizer.database import AsyncSessionDep
from cloud_optimizer.middleware.auth import CurrentUser
from cloud_optimizer.services.aws_connection import AWSConnectionService

router = APIRouter()


def get_aws_connection_service(db: AsyncSessionDep) -> AWSConnectionService:
    """Dependency to get AWS connection service with database session.

    Args:
        db: Database session

    Returns:
        AWSConnectionService instance
    """
    return AWSConnectionService(db)


AWSConnectionServiceDep = Annotated[
    AWSConnectionService, Depends(get_aws_connection_service)
]


class ConnectWithRoleRequest(BaseModel):
    """Request schema for connecting with IAM role."""

    aws_account_id: str = Field(..., min_length=12, max_length=12)
    role_arn: str = Field(..., pattern=r"^arn:aws:iam::\d{12}:role/.+$")
    external_id: str | None = None
    friendly_name: str | None = None
    region: str = "us-east-1"


class ConnectWithKeysRequest(BaseModel):
    """Request schema for connecting with access keys."""

    aws_account_id: str = Field(..., min_length=12, max_length=12)
    access_key_id: str = Field(..., min_length=16, max_length=128)
    secret_access_key: str = Field(..., min_length=1)
    friendly_name: str | None = None
    region: str = "us-east-1"


class AWSAccountResponse(BaseModel):
    """Response schema for AWS account."""

    account_id: UUID
    aws_account_id: str
    friendly_name: str | None
    connection_type: str
    status: str
    default_region: str
    last_validated_at: str | None = None
    last_error: str | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True


@router.post(
    "/connect/role",
    response_model=AWSAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect AWS account with IAM role",
    responses={
        400: {"description": "Invalid request or role cannot be assumed"},
        401: {"description": "Not authenticated"},
    },
)
async def connect_with_role(
    request: ConnectWithRoleRequest,
    user_id: CurrentUser,
    service: AWSConnectionServiceDep,
) -> AWSAccountResponse:
    """Connect an AWS account using IAM role assumption.

    Args:
        request: Connection request with role details
        user_id: Current authenticated user ID
        service: AWS connection service instance

    Returns:
        Created AWS account connection

    Raises:
        HTTPException: If validation fails or role cannot be assumed
    """
    try:
        account = await service.connect_with_role(
            user_id=user_id,
            aws_account_id=request.aws_account_id,
            role_arn=request.role_arn,
            external_id=request.external_id,
            friendly_name=request.friendly_name,
            region=request.region,
        )
        return AWSAccountResponse.model_validate(account)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/",
    response_model=list[AWSAccountResponse],
    summary="List AWS accounts",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def list_accounts(
    user_id: CurrentUser,
    service: AWSConnectionServiceDep,
) -> list[AWSAccountResponse]:
    """List all AWS accounts for the current user.

    Args:
        user_id: Current authenticated user ID
        service: AWS connection service instance

    Returns:
        List of AWS accounts
    """
    accounts = await service.get_user_accounts(user_id)
    return [AWSAccountResponse.model_validate(a) for a in accounts]


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect AWS account",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Account not found"},
    },
)
async def disconnect_account(
    account_id: UUID,
    user_id: CurrentUser,
    service: AWSConnectionServiceDep,
) -> None:
    """Disconnect an AWS account.

    Args:
        account_id: AWS account ID
        user_id: Current authenticated user ID
        service: AWS connection service instance

    Raises:
        HTTPException: If account not found
    """
    # TODO: Verify user owns the account
    try:
        await service.disconnect(account_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
