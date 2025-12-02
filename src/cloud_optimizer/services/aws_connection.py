"""
AWS Account connection service.

Manages AWS account connections with support for IAM role and access key authentication.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cloud_optimizer.config import get_settings
from cloud_optimizer.models.aws_account import AWSAccount, ConnectionStatus, ConnectionType

logger = logging.getLogger(__name__)


class AWSConnectionService:
    """Service for managing AWS account connections."""

    def __init__(self, db: AsyncSession):
        """
        Initialize AWS connection service.

        Args:
            db: Database session
        """
        self.db = db
        self._fernet: Optional[Fernet] = None

    @property
    def fernet(self) -> Fernet:
        """Get Fernet encryption instance."""
        if self._fernet is None:
            settings = get_settings()
            if not settings.encryption_key:
                raise ValueError("encryption_key not configured")
            self._fernet = Fernet(settings.encryption_key.encode())
        return self._fernet

    async def connect_with_role(
        self,
        user_id: UUID,
        aws_account_id: str,
        role_arn: str,
        external_id: Optional[str] = None,
        friendly_name: Optional[str] = None,
        region: str = "us-east-1",
    ) -> AWSAccount:
        """
        Connect an AWS account using IAM role assumption.

        Args:
            user_id: User ID who owns this account
            aws_account_id: 12-digit AWS account ID
            role_arn: ARN of the IAM role to assume
            external_id: Optional external ID for role assumption
            friendly_name: Optional friendly name for the account
            region: Default AWS region

        Returns:
            Created AWSAccount instance

        Raises:
            ValueError: If role cannot be assumed or lacks permissions
        """
        # Validate role can be assumed
        session = await self._assume_role(role_arn, external_id)
        if not session:
            raise ValueError("Failed to assume IAM role")

        # Verify permissions
        await self._verify_permissions(session)

        # Create account record
        account = AWSAccount(
            user_id=user_id,
            aws_account_id=aws_account_id,
            friendly_name=friendly_name,
            connection_type=ConnectionType.IAM_ROLE,
            role_arn=role_arn,
            external_id=external_id,
            status=ConnectionStatus.ACTIVE,
            default_region=region,
            last_validated_at=datetime.now(timezone.utc),
        )
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        logger.info(f"Connected AWS account {aws_account_id} via IAM role for user {user_id}")
        return account

    async def connect_with_keys(
        self,
        user_id: UUID,
        aws_account_id: str,
        access_key_id: str,
        secret_access_key: str,
        friendly_name: Optional[str] = None,
        region: str = "us-east-1",
    ) -> AWSAccount:
        """
        Connect an AWS account using access keys.

        Args:
            user_id: User ID who owns this account
            aws_account_id: 12-digit AWS account ID
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key
            friendly_name: Optional friendly name for the account
            region: Default AWS region

        Returns:
            Created AWSAccount instance

        Raises:
            ValueError: If credentials are invalid or lack permissions
        """
        # Validate credentials
        session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
        await self._verify_permissions(session)

        # Encrypt credentials
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
            last_validated_at=datetime.now(timezone.utc),
        )
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        logger.info(f"Connected AWS account {aws_account_id} via access keys for user {user_id}")
        return account

    async def get_session(self, account_id: UUID) -> boto3.Session:
        """
        Get a boto3 session for the given account.

        Args:
            account_id: AWS account ID

        Returns:
            Configured boto3 session

        Raises:
            ValueError: If account not found or credentials invalid
        """
        account = await self.db.get(AWSAccount, account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")

        if account.status != ConnectionStatus.ACTIVE:
            raise ValueError(f"Account {account_id} is not active (status: {account.status})")

        if account.connection_type == ConnectionType.IAM_ROLE:
            session = await self._assume_role(account.role_arn, account.external_id)
            if not session:
                raise ValueError(f"Failed to assume role for account {account_id}")
            return session
        else:
            if not account.access_key_encrypted or not account.secret_key_encrypted:
                raise ValueError(f"Account {account_id} missing encrypted credentials")
            access_key = self.fernet.decrypt(account.access_key_encrypted).decode()
            secret_key = self.fernet.decrypt(account.secret_key_encrypted).decode()
            return boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=account.default_region,
            )

    async def _assume_role(
        self, role_arn: str, external_id: Optional[str] = None
    ) -> Optional[boto3.Session]:
        """
        Assume an IAM role and return a session.

        Args:
            role_arn: ARN of the IAM role to assume
            external_id: Optional external ID for role assumption

        Returns:
            boto3.Session with temporary credentials or None if failed
        """
        try:
            sts = boto3.client("sts")
            params = {
                "RoleArn": role_arn,
                "RoleSessionName": "CloudOptimizer",
                "DurationSeconds": 3600,
            }
            if external_id:
                params["ExternalId"] = external_id

            response = sts.assume_role(**params)
            credentials = response["Credentials"]
            return boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )
        except ClientError as e:
            logger.error(f"Failed to assume role {role_arn}: {e}")
            return None

    async def _verify_permissions(self, session: boto3.Session) -> None:
        """
        Verify the session has required permissions.

        Args:
            session: boto3 session to verify

        Raises:
            ValueError: If session lacks required permissions
        """
        try:
            # Try to call STS GetCallerIdentity to verify credentials work
            sts = session.client("sts")
            sts.get_caller_identity()
        except ClientError as e:
            logger.error(f"Failed to verify AWS credentials: {e}")
            raise ValueError("Invalid AWS credentials or insufficient permissions")

    async def disconnect(self, account_id: UUID) -> None:
        """
        Disconnect an AWS account.

        Args:
            account_id: AWS account ID to disconnect
        """
        account = await self.db.get(AWSAccount, account_id)
        if account:
            account.status = ConnectionStatus.DISCONNECTED
            await self.db.commit()
            logger.info(f"Disconnected AWS account {account.aws_account_id}")

    async def get_user_accounts(self, user_id: UUID) -> list[AWSAccount]:
        """
        Get all AWS accounts for a user.

        Args:
            user_id: User ID

        Returns:
            List of AWS accounts for the user
        """
        result = await self.db.execute(
            select(AWSAccount).where(AWSAccount.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_account(self, account_id: UUID) -> Optional[AWSAccount]:
        """
        Get an AWS account by ID.

        Args:
            account_id: AWS account ID

        Returns:
            AWSAccount or None if not found
        """
        return await self.db.get(AWSAccount, account_id)
