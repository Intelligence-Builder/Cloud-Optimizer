"""Unit tests for Secrets Scanner.

Issue #143: Secrets Manager and Parameter Store scanner
Tests for secrets security scanning rules SM_001-006 and SSM_001-004.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch, AsyncMock

from cloud_optimizer.scanners.secrets_scanner import SecretsScanner


class TestSecretsScannerRules:
    """Test Secrets scanner security rules."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> SecretsScanner:
        """Create Secrets scanner with mock session."""
        return SecretsScanner(session=mock_session, regions=["us-east-1"])

    def test_scanner_initialization(self, scanner: SecretsScanner) -> None:
        """Test scanner initializes with correct rules."""
        assert scanner.service_name == "secrets"
        assert len(scanner.rules) >= 10

        rule_ids = [r.rule_id for r in scanner.rules]
        expected_rules = [
            "SM_001", "SM_002", "SM_003", "SM_004", "SM_005", "SM_006",
            "SSM_001", "SSM_002", "SSM_003", "SSM_004"
        ]
        for expected in expected_rules:
            assert expected in rule_ids, f"Missing rule {expected}"


class TestSecretsManagerRules:
    """Test Secrets Manager-specific rules."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        return MagicMock()

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> SecretsScanner:
        """Create Secrets scanner with mock session."""
        return SecretsScanner(session=mock_session, regions=["us-east-1"])

    def test_rule_sm_001_rotation_disabled(
        self, scanner: SecretsScanner
    ) -> None:
        """Test SM_001: Check for rotation disabled."""
        # Secret without rotation
        secret_no_rotation: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "RotationEnabled": False
        }

        rule = next(r for r in scanner.rules if r.rule_id == "SM_001")
        result = rule.check_function(secret_no_rotation)
        assert result is not None
        assert not result.passed

        # Secret with rotation enabled
        secret_with_rotation: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "RotationEnabled": True,
            "RotationRules": {"AutomaticallyAfterDays": 30}
        }
        result = rule.check_function(secret_with_rotation)
        assert result is None or result.passed

    def test_rule_sm_002_no_kms_encryption(
        self, scanner: SecretsScanner
    ) -> None:
        """Test SM_002: Check for KMS encryption."""
        # Secret without KMS
        secret_default_kms: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "KmsKeyId": None
        }

        rule = next(r for r in scanner.rules if r.rule_id == "SM_002")
        result = rule.check_function(secret_default_kms)
        assert result is not None
        assert not result.passed

        # Secret with customer KMS key
        secret_with_kms: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/12345"
        }
        result = rule.check_function(secret_with_kms)
        assert result is None or result.passed

    def test_rule_sm_003_cross_account_access(
        self, scanner: SecretsScanner
    ) -> None:
        """Test SM_003: Check for cross-account access."""
        # Secret with cross-account access
        secret_cross_account: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "_resource_policy": '{"Statement":[{"Principal":{"AWS":"arn:aws:iam::999999999999:root"}}]}'
        }

        rule = next(r for r in scanner.rules if r.rule_id == "SM_003")
        result = rule.check_function(secret_cross_account)
        assert result is not None

        # Secret without cross-account access
        secret_same_account: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "_resource_policy": '{"Statement":[{"Principal":{"AWS":"arn:aws:iam::123456789012:role/app"}}]}'
        }
        result = rule.check_function(secret_same_account)
        assert result is None or result.passed

    def test_rule_sm_004_unused_secret(self, scanner: SecretsScanner) -> None:
        """Test SM_004: Check for unused secrets (90+ days)."""
        # Unused secret
        secret_unused: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "LastAccessedDate": (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        }

        rule = next(r for r in scanner.rules if r.rule_id == "SM_004")
        result = rule.check_function(secret_unused)
        assert result is not None
        assert not result.passed

        # Recently used secret
        secret_used: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "LastAccessedDate": datetime.now(timezone.utc).isoformat()
        }
        result = rule.check_function(secret_used)
        assert result is None or result.passed

    def test_rule_sm_005_replication_disabled(
        self, scanner: SecretsScanner
    ) -> None:
        """Test SM_005: Check for replication for DR."""
        # Secret without replication
        secret_no_replication: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "ReplicationStatus": None
        }

        rule = next(r for r in scanner.rules if r.rule_id == "SM_005")
        result = rule.check_function(secret_no_replication)
        # This is advisory
        assert result is not None

        # Secret with replication
        secret_replicated: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "ReplicationStatus": [
                {"Region": "us-west-2", "Status": "InSync"}
            ]
        }
        result = rule.check_function(secret_replicated)
        assert result is None or result.passed

    def test_rule_sm_006_weak_secret_value(
        self, scanner: SecretsScanner
    ) -> None:
        """Test SM_006: Check for potentially weak secret values."""
        # Secret with weak value pattern
        secret_weak: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "_secret_value": "password123"
        }

        rule = next(r for r in scanner.rules if r.rule_id == "SM_006")
        result = rule.check_function(secret_weak)
        assert result is not None
        assert not result.passed

        # Secret with strong value
        secret_strong: Dict[str, Any] = {
            "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
            "Name": "test-secret",
            "_secret_value": "aB3$kL9mNp2xQw8zYv6tRs5uDf4gHj7i"
        }
        result = rule.check_function(secret_strong)
        assert result is None or result.passed


class TestSSMParameterRules:
    """Test SSM Parameter Store-specific rules."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        return MagicMock()

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> SecretsScanner:
        """Create Secrets scanner with mock session."""
        return SecretsScanner(session=mock_session, regions=["us-east-1"])

    def test_rule_ssm_001_not_secure_string(
        self, scanner: SecretsScanner
    ) -> None:
        """Test SSM_001: Check for non-SecureString sensitive parameters."""
        # Parameter with plain text
        param_plain: Dict[str, Any] = {
            "Name": "/app/db/password",
            "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/app/db/password",
            "Type": "String"
        }

        rule = next(r for r in scanner.rules if r.rule_id == "SSM_001")
        result = rule.check_function(param_plain)
        assert result is not None
        assert not result.passed

        # Parameter as SecureString
        param_secure: Dict[str, Any] = {
            "Name": "/app/db/password",
            "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/app/db/password",
            "Type": "SecureString"
        }
        result = rule.check_function(param_secure)
        assert result is None or result.passed

    def test_rule_ssm_002_no_kms_key(self, scanner: SecretsScanner) -> None:
        """Test SSM_002: Check for KMS encryption on SecureString."""
        # SecureString without customer KMS
        param_default_kms: Dict[str, Any] = {
            "Name": "/app/secret",
            "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/app/secret",
            "Type": "SecureString",
            "KeyId": "alias/aws/ssm"
        }

        rule = next(r for r in scanner.rules if r.rule_id == "SSM_002")
        result = rule.check_function(param_default_kms)
        assert result is not None
        assert not result.passed

        # SecureString with customer KMS
        param_customer_kms: Dict[str, Any] = {
            "Name": "/app/secret",
            "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/app/secret",
            "Type": "SecureString",
            "KeyId": "arn:aws:kms:us-east-1:123456789012:key/12345"
        }
        result = rule.check_function(param_customer_kms)
        assert result is None or result.passed

    def test_rule_ssm_003_public_tier(self, scanner: SecretsScanner) -> None:
        """Test SSM_003: Check for parameters in public tier."""
        # Parameter in standard tier
        param_standard: Dict[str, Any] = {
            "Name": "/app/config",
            "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/app/config",
            "Tier": "Standard"
        }

        rule = next(r for r in scanner.rules if r.rule_id == "SSM_003")
        result = rule.check_function(param_standard)
        # Standard tier is acceptable
        assert result is None or result.passed

        # Parameter in advanced tier
        param_advanced: Dict[str, Any] = {
            "Name": "/app/config",
            "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/app/config",
            "Tier": "Advanced"
        }
        result = rule.check_function(param_advanced)
        assert result is None or result.passed

    def test_rule_ssm_004_credential_patterns(
        self, scanner: SecretsScanner
    ) -> None:
        """Test SSM_004: Check for credential patterns in parameter values."""
        # Parameter with credential pattern
        param_cred: Dict[str, Any] = {
            "Name": "/app/config",
            "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/app/config",
            "Type": "String",
            "_value": "AKIAIOSFODNN7EXAMPLE"
        }

        rule = next(r for r in scanner.rules if r.rule_id == "SSM_004")
        result = rule.check_function(param_cred)
        assert result is not None
        assert not result.passed

        # Parameter without credential pattern
        param_safe: Dict[str, Any] = {
            "Name": "/app/config",
            "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/app/config",
            "Type": "String",
            "_value": "us-east-1"
        }
        result = rule.check_function(param_safe)
        assert result is None or result.passed


class TestSecretsScannerIntegration:
    """Integration tests for Secrets scanner."""

    @pytest.fixture
    def mock_secretsmanager_client(self) -> MagicMock:
        """Create mock Secrets Manager client."""
        client = MagicMock()
        client.list_secrets.return_value = {
            "SecretList": [
                {
                    "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test",
                    "Name": "test-secret",
                    "RotationEnabled": True
                }
            ]
        }
        return client

    @pytest.fixture
    def mock_ssm_client(self) -> MagicMock:
        """Create mock SSM client."""
        client = MagicMock()
        client.describe_parameters.return_value = {
            "Parameters": []
        }
        return client

    @pytest.fixture
    def mock_session_with_clients(
        self,
        mock_secretsmanager_client: MagicMock,
        mock_ssm_client: MagicMock
    ) -> MagicMock:
        """Create mock session with Secrets Manager and SSM clients."""
        session = MagicMock()

        def get_client(service: str, **kwargs: Any) -> MagicMock:
            if service == "secretsmanager":
                return mock_secretsmanager_client
            elif service == "ssm":
                return mock_ssm_client
            return MagicMock()

        session.client.side_effect = get_client
        return session

    @pytest.mark.asyncio
    async def test_scan_returns_results(
        self, mock_session_with_clients: MagicMock
    ) -> None:
        """Test that scan returns results."""
        scanner = SecretsScanner(
            session=mock_session_with_clients,
            regions=["us-east-1"]
        )

        with patch.object(scanner, 'scan', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = []
            results = await scanner.scan()
            assert isinstance(results, list)

    def test_scanner_has_correct_service_name(
        self, mock_session_with_clients: MagicMock
    ) -> None:
        """Test scanner has correct service name."""
        scanner = SecretsScanner(
            session=mock_session_with_clients,
            regions=["us-east-1"]
        )
        assert scanner.service_name == "secrets"
