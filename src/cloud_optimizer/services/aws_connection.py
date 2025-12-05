"""
AWS Account connection service.

Provides secure onboarding for customer AWS accounts using IAM roles or access keys.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Optional
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cloud_optimizer.config import Settings, get_settings
from cloud_optimizer.models.aws_account import AWSAccount, ConnectionStatus, ConnectionType

logger = logging.getLogger(__name__)

ROLE_ARN_PATTERN = re.compile(r"^arn:aws:iam::(\d{12}):role/.+$")
PERMISSION_DENIED_CODES = {
    "AccessDenied",
    "AccessDeniedException",
    "UnauthorizedOperation",
}


@dataclass(frozen=True)
class PermissionCheck:
    """Represents a lightweight permission probe."""

    service: str
    operation: str
    params: Dict[str, Any]


PERMISSION_CHECKS: tuple[PermissionCheck, ...] = (
    PermissionCheck("iam", "list_users", {"MaxItems": 1}),
    PermissionCheck("s3", "list_buckets", {}),
    PermissionCheck("ec2", "describe_regions", {}),
)


class AWSConnectionService:
    """Service for managing AWS account connections."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        settings: Settings | None = None,
        boto3_client_factory: Callable[[str], Any] | None = None,
        boto3_session_factory: Callable[..., Any] | None = None,
    ) -> None:
        """
        Initialize AWS connection service.

        Args:
            db: Database session
            settings: Optional settings override (primarily for testing)
            boto3_client_factory: Optional factory for creating boto3 clients
            boto3_session_factory: Optional factory for creating boto3 sessions
        """
        self.db = db
        self._settings = settings
        self._fernet: Fernet | None = None
        self._client_factory = boto3_client_factory or boto3.client
        self._session_factory = boto3_session_factory or boto3.Session

    @property
    def settings(self) -> Settings:
        """Return cached settings instance."""
        return self._settings or get_settings()

    @property
    def fernet(self) -> Fernet:
        """Get Fernet encryption instance."""
        if self._fernet is None:
            encryption_key = (self.settings.encryption_key or "").strip()
            if not encryption_key:
                raise ValueError(
                    "encryption_key not configured; set ENCRYPTION_KEY environment variable"
                )
            self._fernet = Fernet(encryption_key.encode())
        return self._fernet

    async def connect_with_role(
        self,
        user_id: UUID,
        role_arn: str,
        *,
        aws_account_id: Optional[str] = None,
        external_id: Optional[str] = None,
        friendly_name: Optional[str] = None,
        region: str = "us-east-1",
    ) -> AWSAccount:
        """
        Connect an AWS account using IAM role assumption.

        Args:
            user_id: User ID who owns this account
            role_arn: ARN of the IAM role to assume
            aws_account_id: Optional AWS account ID (auto-derived if not supplied)
            external_id: Optional external ID for role assumption
            friendly_name: Optional friendly name for the account
            region: Default AWS region

        Returns:
            Created AWSAccount instance
        """
        self._validate_role_arn(role_arn)
        derived_account_id = self._extract_account_id(role_arn)
        if derived_account_id:
            self._validate_account_id(derived_account_id)

        if aws_account_id:
            self._validate_account_id(aws_account_id)
            if derived_account_id and aws_account_id != derived_account_id:
                raise ValueError("Provided AWS account ID does not match role ARN")
        else:
            aws_account_id = derived_account_id

        await self._check_account_limit(user_id)

        session = await self._assume_role(role_arn, external_id)
        if session is None:
            raise ValueError("Unable to assume IAM role; verify trust policy and ARN")

        identity = await self._verify_permissions(session)
        identity_account_id = identity.get("Account")

        if identity_account_id and aws_account_id and identity_account_id != aws_account_id:
            raise ValueError(
                "AWS credentials resolved to a different account than the provided ID"
            )

        if not aws_account_id:
            aws_account_id = identity_account_id

        if not aws_account_id:
            raise ValueError("Unable to determine AWS account ID from role")

        account = AWSAccount(
            user_id=user_id,
            aws_account_id=aws_account_id,
            friendly_name=friendly_name,
            connection_type=ConnectionType.IAM_ROLE,
            role_arn=role_arn,
            external_id=external_id or self._generate_external_id(user_id),
            status=ConnectionStatus.ACTIVE,
            default_region=region,
            last_validated_at=self._now(),
        )
        return await self._persist_account(account)

    async def connect_with_keys(
        self,
        user_id: UUID,
        *,
        access_key_id: str,
        secret_access_key: str,
        aws_account_id: Optional[str] = None,
        friendly_name: Optional[str] = None,
        region: str = "us-east-1",
    ) -> AWSAccount:
        """
        Connect an AWS account using access keys.

        Args:
            user_id: User ID who owns this account
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key
            aws_account_id: Optional AWS account ID to validate against
            friendly_name: Optional friendly name for the account
            region: Default AWS region

        Returns:
            Created AWSAccount instance
        """
        if aws_account_id:
            self._validate_account_id(aws_account_id)

        await self._check_account_limit(user_id)

        session = self._session_factory(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
        identity = await self._verify_permissions(session)
        identity_account_id = identity.get("Account")

        if identity_account_id and aws_account_id and identity_account_id != aws_account_id:
            raise ValueError(
                "AWS credentials resolved to a different account than the provided ID"
            )

        if not aws_account_id:
            aws_account_id = identity_account_id

        if not aws_account_id:
            raise ValueError("Unable to determine AWS account ID from credentials")

        encrypted_access_key = self.fernet.encrypt(access_key_id.encode())
        encrypted_secret_key = self.fernet.encrypt(secret_access_key.encode())

        account = AWSAccount(
            user_id=user_id,
            aws_account_id=aws_account_id,
            friendly_name=friendly_name,
            connection_type=ConnectionType.ACCESS_KEYS,
            access_key_encrypted=encrypted_access_key,
            secret_key_encrypted=encrypted_secret_key,
            status=ConnectionStatus.ACTIVE,
            default_region=region,
            last_validated_at=self._now(),
        )
        return await self._persist_account(account)

    async def disconnect_account(self, account_id: UUID, user_id: UUID) -> AWSAccount:
        """
        Disconnect an AWS account for a user.

        Args:
            account_id: AWS account identifier
            user_id: Owner user ID

        Returns:
            Updated AWSAccount instance
        """
        account = await self.get_account_for_user(account_id, user_id)
        self._clear_credentials(account)
        account.status = ConnectionStatus.DISCONNECTED
        account.last_error = None
        account.last_validated_at = None
        await self.db.commit()
        await self.db.refresh(account)
        logger.info("Disconnected AWS account %s for user %s", account.aws_account_id, user_id)
        return account

    async def validate_account(self, account_id: UUID, user_id: UUID) -> AWSAccount:
        """
        Re-validate an existing AWS account connection.

        Args:
            account_id: AWS account identifier
            user_id: Owner user ID

        Returns:
            Updated AWSAccount instance
        """
        account = await self.get_account_for_user(account_id, user_id)

        try:
            session = await self.get_session(account.account_id, allow_inactive=True)
            await self._verify_permissions(session)
            account.status = ConnectionStatus.ACTIVE
            account.last_error = None
            account.last_validated_at = self._now()
        except ValueError as exc:
            account.status = ConnectionStatus.ERROR
            account.last_error = str(exc)
            logger.warning(
                "AWS account %s validation failed: %s", account.aws_account_id, exc
            )
            await self.db.commit()
            await self.db.refresh(account)
            raise

        await self.db.commit()
        await self.db.refresh(account)
        logger.info("Revalidated AWS account %s", account.aws_account_id)
        return account

    async def get_user_accounts(self, user_id: UUID) -> list[AWSAccount]:
        """Get all AWS accounts for a user."""
        result = await self.db.execute(
            select(AWSAccount).where(AWSAccount.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_account_for_user(self, account_id: UUID, user_id: UUID) -> AWSAccount:
        """
        Retrieve an AWS account owned by a user.

        Raises:
            ValueError: If account is not found or not owned by the user
        """
        result = await self.db.execute(
            select(AWSAccount).where(
                AWSAccount.account_id == account_id, AWSAccount.user_id == user_id
            )
        )
        account = result.scalars().first()
        if not account:
            raise ValueError("AWS account not found")
        return account

    async def get_session(
        self,
        account_id: UUID,
        *,
        allow_inactive: bool = False,
    ) -> boto3.Session:
        """
        Get a boto3 session for the given account.

        Args:
            account_id: AWS account ID
            allow_inactive: Whether to allow validation for inactive accounts
        """
        account = await self.db.get(AWSAccount, account_id)
        if not account:
            raise ValueError(f"AWS account {account_id} not found")

        if not allow_inactive and account.status != ConnectionStatus.ACTIVE:
            raise ValueError(f"AWS account {account.aws_account_id} is not active")

        if account.connection_type == ConnectionType.IAM_ROLE:
            session = await self._assume_role(account.role_arn, account.external_id)
            if not session:
                raise ValueError("Unable to assume IAM role, please reconfigure")
            return session

        if not account.access_key_encrypted or not account.secret_key_encrypted:
            raise ValueError("Encrypted access keys are missing for this account")

        access_key = self.fernet.decrypt(account.access_key_encrypted).decode()
        secret_key = self.fernet.decrypt(account.secret_key_encrypted).decode()
        return self._session_factory(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=account.default_region,
        )

    async def _persist_account(self, account: AWSAccount) -> AWSAccount:
        """Persist account and handle uniqueness violations."""
        self.db.add(account)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            logger.warning(
                "Duplicate AWS account %s for user %s",
                account.aws_account_id,
                account.user_id,
            )
            raise ValueError("AWS account already connected") from exc

        await self.db.refresh(account)
        logger.info(
            "Connected AWS account %s for user %s via %s",
            account.aws_account_id,
            account.user_id,
            account.connection_type.value,
        )
        return account

    async def _assume_role(
        self, role_arn: str, external_id: Optional[str] = None
    ) -> Optional[boto3.Session]:
        """Assume an IAM role and return a session."""
        try:
            sts = self._client_factory("sts")
            params: Dict[str, Any] = {
                "RoleArn": role_arn,
                "RoleSessionName": "CloudOptimizer",
                "DurationSeconds": 3600,
            }
            if external_id:
                params["ExternalId"] = external_id

            response = sts.assume_role(**params)
            credentials = response["Credentials"]
            return self._session_factory(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )
        except ClientError as exc:
            logger.error("Failed to assume role %s: %s", role_arn, exc)
            return None

    async def _verify_permissions(self, session: boto3.Session) -> Dict[str, Any]:
        """
        Verify the session has required permissions.

        Args:
            session: boto3 session to verify

        Returns:
            Caller identity payload

        Raises:
            ValueError: If session lacks required permissions
        """
        try:
            sts_client = session.client("sts")
            identity = sts_client.get_caller_identity()
        except ClientError as exc:
            logger.error("Failed to verify AWS credentials: %s", exc)
            raise ValueError("Unable to validate AWS credentials") from exc

        failures: list[str] = []
        for check in PERMISSION_CHECKS:
            client = session.client(check.service)
            operation = getattr(client, check.operation)
            try:
                operation(**check.params)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code")
                if code in PERMISSION_DENIED_CODES:
                    failures.append(f"{check.service}.{check.operation}")
                else:
                    logger.error(
                        "Error while verifying permission %s.%s: %s",
                        check.service,
                        check.operation,
                        exc,
                    )
                    raise ValueError("Failed to validate AWS permissions") from exc

        if failures:
            raise ValueError(
                "AWS credentials are missing required permissions: "
                + ", ".join(failures)
            )

        return identity

    async def _check_account_limit(self, user_id: UUID) -> None:
        """Enforce the one-account trial limit when enabled."""
        if not self.settings.trial_mode:
            return

        result = await self.db.execute(
            select(func.count()).where(
                AWSAccount.user_id == user_id,
                AWSAccount.status != ConnectionStatus.DISCONNECTED,
            )
        )
        (count,) = result.one()
        if count >= 1:
            raise ValueError("Trial plan allows only one connected AWS account")

    def _validate_account_id(self, aws_account_id: str) -> None:
        if not aws_account_id.isdigit() or len(aws_account_id) != 12:
            raise ValueError("AWS account ID must be a 12-digit string")

    def _validate_role_arn(self, role_arn: str) -> None:
        if not ROLE_ARN_PATTERN.match(role_arn):
            raise ValueError("Invalid IAM role ARN format")

    def _extract_account_id(self, role_arn: str) -> Optional[str]:
        match = ROLE_ARN_PATTERN.match(role_arn)
        return match.group(1) if match else None

    def _generate_external_id(self, user_id: UUID) -> str:
        """Generate a deterministic external ID per user."""
        return f"co-{user_id}"

    def _clear_credentials(self, account: AWSAccount) -> None:
        account.access_key_encrypted = None
        account.secret_key_encrypted = None

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
