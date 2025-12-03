"""AWS Account connection API endpoints."""
import json
from pathlib import Path
from typing import Annotated, Any
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


IAM_TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "data" / "iam"


class ConnectWithRoleRequest(BaseModel):
    """Request schema for connecting with IAM role."""

    aws_account_id: str | None = Field(
        default=None,
        min_length=12,
        max_length=12,
    )
    role_arn: str = Field(..., pattern=r"^arn:aws:iam::\d{12}:role/.+$")
    external_id: str | None = None
    friendly_name: str | None = None
    region: str = "us-east-1"


class ConnectWithKeysRequest(BaseModel):
    """Request schema for connecting with access keys."""

    aws_account_id: str | None = Field(
        default=None, min_length=12, max_length=12
    )
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
    updated_at: str

    class Config:
        """Pydantic config."""

        from_attributes = True


class SetupInstructionsResponse(BaseModel):
    """Response schema for IAM policy/trust policy templates."""

    iam_policy: dict[str, Any]
    trust_policy: dict[str, Any]


def _to_response(account: AWSAccount) -> AWSAccountResponse:
    return AWSAccountResponse.model_validate(account)


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
    """Connect an AWS account using IAM role assumption."""
    try:
        account = await service.connect_with_role(
            user_id=user_id,
            role_arn=request.role_arn,
            aws_account_id=request.aws_account_id,
            external_id=request.external_id,
            friendly_name=request.friendly_name,
            region=request.region,
        )
        return _to_response(account)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/connect/keys",
    response_model=AWSAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect AWS account with access keys",
    responses={
        400: {"description": "Invalid credentials or permissions"},
        401: {"description": "Not authenticated"},
    },
)
async def connect_with_keys(
    request: ConnectWithKeysRequest,
    user_id: CurrentUser,
    service: AWSConnectionServiceDep,
) -> AWSAccountResponse:
    """Connect an AWS account using IAM access keys."""
    try:
        account = await service.connect_with_keys(
            user_id=user_id,
            access_key_id=request.access_key_id,
            secret_access_key=request.secret_access_key,
            aws_account_id=request.aws_account_id,
            friendly_name=request.friendly_name,
            region=request.region,
        )
        return _to_response(account)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


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
    accounts = await service.get_user_accounts(user_id)
    return [_to_response(a) for a in accounts]


@router.get(
    "/{account_id}",
    response_model=AWSAccountResponse,
    summary="Get AWS account details",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Account not found"},
    },
)
async def get_account(
    account_id: UUID,
    user_id: CurrentUser,
    service: AWSConnectionServiceDep,
) -> AWSAccountResponse:
    """Get details for a specific AWS account."""
    try:
        account = await service.get_account_for_user(account_id, user_id)
        return _to_response(account)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AWS account not found"
        )


@router.post(
    "/{account_id}/validate",
    response_model=AWSAccountResponse,
    summary="Revalidate AWS account connection",
    responses={
        400: {"description": "Validation failed"},
        401: {"description": "Not authenticated"},
        404: {"description": "Account not found"},
    },
)
async def validate_account(
    account_id: UUID,
    user_id: CurrentUser,
    service: AWSConnectionServiceDep,
) -> AWSAccountResponse:
    """Force a re-validation of the AWS connection."""
    try:
        account = await service.validate_account(account_id, user_id)
        return _to_response(account)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect AWS account",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Account not found"},
    },
)
async def disconnect_account_endpoint(
    account_id: UUID,
    user_id: CurrentUser,
    service: AWSConnectionServiceDep,
) -> None:
    """Disconnect an AWS account."""
    try:
        await service.disconnect_account(account_id, user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AWS account not found"
        )


@router.get(
    "/setup-instructions",
    response_model=SetupInstructionsResponse,
    summary="Get IAM policy and trust policy templates",
)
async def get_setup_instructions() -> SetupInstructionsResponse:
    """Return IAM policy/trust policy templates required for onboarding."""
    return SetupInstructionsResponse(
        iam_policy=_load_template("policy.json"),
        trust_policy=_load_template("trust-policy.json"),
    )


def _load_template(filename: str) -> dict[str, Any]:
    template_path = IAM_TEMPLATE_DIR / filename
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Template {filename} not found",
        )
    return json.loads(template_path.read_text(encoding="utf-8"))
