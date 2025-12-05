"""Unit tests for Cross-Account Role Assumption.

Issue #148: Cross-account role assumption
Tests for cross-account IAM role assumption and credential management.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import boto3
from botocore.exceptions import ClientError

from cloud_optimizer.scanners.cross_account import (
    AssumedRoleCredentials,
    CredentialCache,
    CrossAccountRoleManager,
    get_cloudformation_template,
    get_terraform_template,
)


class TestAssumedRoleCredentials:
    """Test AssumedRoleCredentials dataclass."""

    def test_valid_credentials(self) -> None:
        """Test creating valid credentials."""
        expiration = datetime.now(timezone.utc) + timedelta(hours=1)
        creds = AssumedRoleCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            session_token="token123",
            expiration=expiration,
            role_arn="arn:aws:iam::123456789012:role/Scanner"
        )

        assert creds.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert not creds.is_expired
        assert not creds.expires_soon
        assert creds.time_remaining > 3000  # More than 50 minutes

    def test_expired_credentials(self) -> None:
        """Test expired credentials detection."""
        expiration = datetime.now(timezone.utc) - timedelta(hours=1)
        creds = AssumedRoleCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            session_token="token",
            expiration=expiration,
            role_arn="arn:aws:iam::123456789012:role/Scanner"
        )

        assert creds.is_expired
        assert creds.time_remaining < 0

    def test_expires_soon(self) -> None:
        """Test credentials expiring soon detection."""
        # Expires in 3 minutes
        expiration = datetime.now(timezone.utc) + timedelta(minutes=3)
        creds = AssumedRoleCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            session_token="token",
            expiration=expiration,
            role_arn="arn:aws:iam::123456789012:role/Scanner"
        )

        assert not creds.is_expired
        assert creds.expires_soon  # Less than 5 minutes

    def test_assumed_at_default(self) -> None:
        """Test that assumed_at defaults to current time."""
        expiration = datetime.now(timezone.utc) + timedelta(hours=1)
        before = datetime.now(timezone.utc)
        creds = AssumedRoleCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            session_token="token",
            expiration=expiration,
            role_arn="arn:aws:iam::123456789012:role/Scanner"
        )
        after = datetime.now(timezone.utc)

        assert before <= creds.assumed_at <= after


class TestCredentialCache:
    """Test CredentialCache class."""

    @pytest.fixture
    def cache(self) -> CredentialCache:
        """Create empty credential cache."""
        return CredentialCache()

    @pytest.fixture
    def valid_credentials(self) -> AssumedRoleCredentials:
        """Create valid credentials."""
        return AssumedRoleCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            session_token="token",
            expiration=datetime.now(timezone.utc) + timedelta(hours=1),
            role_arn="arn:aws:iam::123456789012:role/Scanner"
        )

    def test_put_and_get(
        self, cache: CredentialCache, valid_credentials: AssumedRoleCredentials
    ) -> None:
        """Test putting and getting credentials."""
        cache.put(valid_credentials)
        retrieved = cache.get(valid_credentials.role_arn)

        assert retrieved is not None
        assert retrieved == valid_credentials

    def test_get_returns_none_for_expired(
        self, cache: CredentialCache
    ) -> None:
        """Test get returns None for soon-expiring credentials."""
        expiring_creds = AssumedRoleCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            session_token="token",
            expiration=datetime.now(timezone.utc) + timedelta(minutes=2),
            role_arn="arn:aws:iam::123456789012:role/Scanner"
        )

        cache.put(expiring_creds)
        retrieved = cache.get(expiring_creds.role_arn)

        assert retrieved is None  # Expires soon, not returned

    def test_get_returns_none_for_missing(
        self, cache: CredentialCache
    ) -> None:
        """Test get returns None for missing role."""
        retrieved = cache.get("arn:aws:iam::999999999999:role/NonExistent")
        assert retrieved is None

    def test_invalidate(
        self, cache: CredentialCache, valid_credentials: AssumedRoleCredentials
    ) -> None:
        """Test invalidating cached credentials."""
        cache.put(valid_credentials)
        cache.invalidate(valid_credentials.role_arn)

        retrieved = cache.get(valid_credentials.role_arn)
        assert retrieved is None

    def test_clear(
        self, cache: CredentialCache, valid_credentials: AssumedRoleCredentials
    ) -> None:
        """Test clearing all cached credentials."""
        cache.put(valid_credentials)

        creds2 = AssumedRoleCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE2",
            secret_access_key="secret2",
            session_token="token2",
            expiration=datetime.now(timezone.utc) + timedelta(hours=1),
            role_arn="arn:aws:iam::222222222222:role/Scanner"
        )
        cache.put(creds2)

        cache.clear()

        assert cache.get(valid_credentials.role_arn) is None
        assert cache.get(creds2.role_arn) is None


class TestCrossAccountRoleManager:
    """Test CrossAccountRoleManager class."""

    @pytest.fixture
    def mock_sts_client(self) -> MagicMock:
        """Create mock STS client."""
        client = MagicMock()
        client.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
                "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "SessionToken": "token123",
                "Expiration": datetime.now(timezone.utc) + timedelta(hours=1)
            }
        }
        client.get_caller_identity.return_value = {
            "UserId": "AIDAIOSFODNN7EXAMPLE",
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:user/test"
        }
        return client

    @pytest.fixture
    def mock_session(self, mock_sts_client: MagicMock) -> MagicMock:
        """Create mock boto3 session."""
        session = MagicMock()
        session.client.return_value = mock_sts_client
        return session

    @pytest.fixture
    def manager(self, mock_session: MagicMock) -> CrossAccountRoleManager:
        """Create cross-account role manager with mock session."""
        return CrossAccountRoleManager(source_session=mock_session)

    def test_generate_external_id(self, manager: CrossAccountRoleManager) -> None:
        """Test external ID generation."""
        external_id = manager.generate_external_id()
        assert len(external_id) >= 32  # URL-safe base64 of 32 bytes
        assert external_id != manager.generate_external_id()  # Should be unique

    def test_assume_role(self, manager: CrossAccountRoleManager) -> None:
        """Test assuming a role."""
        creds = manager.assume_role(
            role_arn="arn:aws:iam::123456789012:role/Scanner"
        )

        assert creds.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert creds.role_arn == "arn:aws:iam::123456789012:role/Scanner"

    def test_assume_role_with_external_id(
        self, manager: CrossAccountRoleManager, mock_sts_client: MagicMock
    ) -> None:
        """Test assuming role with external ID."""
        manager.assume_role(
            role_arn="arn:aws:iam::123456789012:role/Scanner",
            external_id="my-external-id-123"
        )

        # Verify external ID was passed
        call_args = mock_sts_client.assume_role.call_args
        assert call_args[1]["ExternalId"] == "my-external-id-123"

    def test_assume_role_uses_cache(
        self, manager: CrossAccountRoleManager, mock_sts_client: MagicMock
    ) -> None:
        """Test that assume_role uses cache."""
        role_arn = "arn:aws:iam::123456789012:role/Scanner"

        # First call
        creds1 = manager.assume_role(role_arn=role_arn)

        # Second call should use cache
        creds2 = manager.assume_role(role_arn=role_arn)

        assert mock_sts_client.assume_role.call_count == 1
        assert creds1 == creds2

    def test_assume_role_bypass_cache(
        self, manager: CrossAccountRoleManager, mock_sts_client: MagicMock
    ) -> None:
        """Test bypassing cache."""
        role_arn = "arn:aws:iam::123456789012:role/Scanner"

        manager.assume_role(role_arn=role_arn, use_cache=False)
        manager.assume_role(role_arn=role_arn, use_cache=False)

        assert mock_sts_client.assume_role.call_count == 2

    def test_assume_role_duration_bounds(
        self, manager: CrossAccountRoleManager, mock_sts_client: MagicMock
    ) -> None:
        """Test duration is bounded correctly."""
        role_arn = "arn:aws:iam::123456789012:role/Scanner"

        # Too short (below 15 min)
        manager.assume_role(
            role_arn=role_arn,
            duration_seconds=100,
            use_cache=False
        )
        call_args = mock_sts_client.assume_role.call_args
        assert call_args[1]["DurationSeconds"] >= 900

        # Too long (above 12 hours)
        manager.assume_role(
            role_arn=role_arn,
            duration_seconds=100000,
            use_cache=False
        )
        call_args = mock_sts_client.assume_role.call_args
        assert call_args[1]["DurationSeconds"] <= 43200

    def test_assume_role_access_denied(
        self, manager: CrossAccountRoleManager, mock_sts_client: MagicMock
    ) -> None:
        """Test handling access denied error."""
        mock_sts_client.assume_role.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
            "AssumeRole"
        )

        with pytest.raises(ClientError):
            manager.assume_role(
                role_arn="arn:aws:iam::123456789012:role/Scanner",
                use_cache=False
            )

    def test_get_session_for_role(
        self, manager: CrossAccountRoleManager
    ) -> None:
        """Test getting boto3 session for assumed role."""
        with patch("cloud_optimizer.scanners.cross_account.boto3.Session") as mock_boto:
            mock_boto.return_value = MagicMock()
            session = manager.get_session_for_role(
                role_arn="arn:aws:iam::123456789012:role/Scanner"
            )

            assert session is not None
            mock_boto.assert_called_once()

    def test_refresh_credentials(
        self, manager: CrossAccountRoleManager, mock_sts_client: MagicMock
    ) -> None:
        """Test refreshing credentials."""
        role_arn = "arn:aws:iam::123456789012:role/Scanner"

        # Initial assumption
        manager.assume_role(role_arn=role_arn)

        # Refresh (should invalidate cache and re-assume)
        manager.refresh_credentials(role_arn)

        assert mock_sts_client.assume_role.call_count == 2


class TestCloudFormationTemplate:
    """Test CloudFormation template generation."""

    def test_template_contains_required_sections(self) -> None:
        """Test template has required sections."""
        template = get_cloudformation_template()

        assert "AWSTemplateFormatVersion" in template
        assert "Parameters" in template
        assert "Resources" in template
        assert "Outputs" in template

    def test_template_has_trusted_account_parameter(self) -> None:
        """Test template has TrustedAccountId parameter."""
        template = get_cloudformation_template()
        assert "TrustedAccountId" in template

    def test_template_has_external_id_parameter(self) -> None:
        """Test template has ExternalId parameter."""
        template = get_cloudformation_template()
        assert "ExternalId" in template

    def test_template_creates_iam_role(self) -> None:
        """Test template creates IAM role."""
        template = get_cloudformation_template()
        assert "AWS::IAM::Role" in template
        assert "CloudOptimizerScanner" in template

    def test_template_has_deny_policy(self) -> None:
        """Test template has deny policy for destructive actions."""
        template = get_cloudformation_template()
        assert "DenyDestructiveActions" in template
        assert "ec2:TerminateInstances" in template
        assert "s3:DeleteBucket" in template


class TestTerraformTemplate:
    """Test Terraform template generation."""

    def test_template_contains_variables(self) -> None:
        """Test template has required variables."""
        template = get_terraform_template()

        assert 'variable "trusted_account_id"' in template
        assert 'variable "external_id"' in template
        assert 'variable "role_name"' in template

    def test_template_creates_iam_role(self) -> None:
        """Test template creates IAM role."""
        template = get_terraform_template()
        assert 'resource "aws_iam_role"' in template
        assert "assume_role_policy" in template

    def test_template_has_policy_attachments(self) -> None:
        """Test template has policy attachments."""
        template = get_terraform_template()
        assert "aws_iam_role_policy_attachment" in template
        assert "SecurityAudit" in template
        assert "ReadOnlyAccess" in template

    def test_template_has_deny_policy(self) -> None:
        """Test template has deny policy."""
        template = get_terraform_template()
        assert "DenyDestructiveActions" in template
        assert "ec2:TerminateInstances" in template

    def test_template_has_outputs(self) -> None:
        """Test template has outputs."""
        template = get_terraform_template()
        assert 'output "role_arn"' in template
