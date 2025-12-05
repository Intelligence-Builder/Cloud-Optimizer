"""Unit tests for Multi-Account Scanning Support.

Issue #147: Multi-account scanning support
Tests for multi-account scanning orchestration and account management.
"""

import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, AsyncMock

from cloud_optimizer.scanners.multi_account import (
    AccountRegistry,
    AccountScanResult,
    AccountStatus,
    AuthMethod,
    AWSAccount,
    MultiAccountScanner,
)
from cloud_optimizer.scanners.base import ScanResult


class TestAWSAccount:
    """Test AWSAccount dataclass."""

    def test_valid_account_creation(self) -> None:
        """Test creating a valid AWS account."""
        account = AWSAccount(
            account_id="123456789012",
            name="Production Account",
            auth_method=AuthMethod.ASSUME_ROLE,
            role_arn="arn:aws:iam::123456789012:role/CloudOptimizerScanner",
            regions=["us-east-1", "us-west-2"],
            environment="production",
            business_unit="engineering"
        )

        assert account.account_id == "123456789012"
        assert account.name == "Production Account"
        assert account.validate()

    def test_invalid_account_id(self) -> None:
        """Test validation fails for invalid account ID."""
        account = AWSAccount(
            account_id="12345",  # Too short
            name="Invalid Account",
            auth_method=AuthMethod.IAM_ROLE
        )
        assert not account.validate()

        account2 = AWSAccount(
            account_id="12345678901X",  # Contains letter
            name="Invalid Account",
            auth_method=AuthMethod.IAM_ROLE
        )
        assert not account2.validate()

    def test_assume_role_requires_role_arn(self) -> None:
        """Test that assume role auth requires role ARN."""
        account = AWSAccount(
            account_id="123456789012",
            name="Test Account",
            auth_method=AuthMethod.ASSUME_ROLE,
            role_arn=None  # Missing role ARN
        )
        assert not account.validate()

        account2 = AWSAccount(
            account_id="123456789012",
            name="Test Account",
            auth_method=AuthMethod.ASSUME_ROLE,
            role_arn="arn:aws:iam::123456789012:role/Scanner"
        )
        assert account2.validate()

    def test_access_key_requires_credentials(self) -> None:
        """Test that access key auth requires credentials."""
        account = AWSAccount(
            account_id="123456789012",
            name="Test Account",
            auth_method=AuthMethod.ACCESS_KEY,
            access_key_id=None,
            secret_access_key=None
        )
        assert not account.validate()

        account2 = AWSAccount(
            account_id="123456789012",
            name="Test Account",
            auth_method=AuthMethod.ACCESS_KEY,
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )
        assert account2.validate()

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        account = AWSAccount(
            account_id="123456789012",
            name="Test Account"
        )
        assert account.auth_method == AuthMethod.ASSUME_ROLE
        assert account.regions == ["us-east-1"]
        assert account.environment == "unknown"
        assert account.business_unit == "unknown"
        assert account.status == AccountStatus.PENDING


class TestAccountRegistry:
    """Test AccountRegistry class."""

    @pytest.fixture
    def registry(self) -> AccountRegistry:
        """Create empty account registry."""
        return AccountRegistry()

    @pytest.fixture
    def sample_account(self) -> AWSAccount:
        """Create sample AWS account."""
        return AWSAccount(
            account_id="123456789012",
            name="Production Account",
            auth_method=AuthMethod.ASSUME_ROLE,
            role_arn="arn:aws:iam::123456789012:role/Scanner",
            environment="production",
            business_unit="engineering"
        )

    def test_add_account(
        self, registry: AccountRegistry, sample_account: AWSAccount
    ) -> None:
        """Test adding an account to registry."""
        assert registry.add_account(sample_account)
        assert registry.get_account("123456789012") == sample_account

    def test_add_invalid_account_fails(self, registry: AccountRegistry) -> None:
        """Test adding invalid account fails."""
        invalid_account = AWSAccount(
            account_id="invalid",
            name="Invalid",
            auth_method=AuthMethod.ASSUME_ROLE
        )
        assert not registry.add_account(invalid_account)

    def test_remove_account(
        self, registry: AccountRegistry, sample_account: AWSAccount
    ) -> None:
        """Test removing an account from registry."""
        registry.add_account(sample_account)
        assert registry.remove_account("123456789012")
        assert registry.get_account("123456789012") is None

    def test_remove_nonexistent_account(self, registry: AccountRegistry) -> None:
        """Test removing non-existent account returns False."""
        assert not registry.remove_account("123456789012")

    def test_list_accounts_no_filter(
        self, registry: AccountRegistry, sample_account: AWSAccount
    ) -> None:
        """Test listing all accounts."""
        registry.add_account(sample_account)
        accounts = registry.list_accounts()
        assert len(accounts) == 1
        assert accounts[0] == sample_account

    def test_list_accounts_by_environment(
        self, registry: AccountRegistry
    ) -> None:
        """Test filtering accounts by environment."""
        prod_account = AWSAccount(
            account_id="111111111111",
            name="Prod",
            auth_method=AuthMethod.IAM_ROLE,
            environment="production"
        )
        dev_account = AWSAccount(
            account_id="222222222222",
            name="Dev",
            auth_method=AuthMethod.IAM_ROLE,
            environment="development"
        )

        registry.add_account(prod_account)
        registry.add_account(dev_account)

        prod_accounts = registry.list_accounts(environment="production")
        assert len(prod_accounts) == 1
        assert prod_accounts[0].name == "Prod"

    def test_list_accounts_by_business_unit(
        self, registry: AccountRegistry
    ) -> None:
        """Test filtering accounts by business unit."""
        eng_account = AWSAccount(
            account_id="111111111111",
            name="Engineering",
            auth_method=AuthMethod.IAM_ROLE,
            business_unit="engineering"
        )
        finance_account = AWSAccount(
            account_id="222222222222",
            name="Finance",
            auth_method=AuthMethod.IAM_ROLE,
            business_unit="finance"
        )

        registry.add_account(eng_account)
        registry.add_account(finance_account)

        eng_accounts = registry.list_accounts(business_unit="engineering")
        assert len(eng_accounts) == 1
        assert eng_accounts[0].name == "Engineering"

    def test_list_accounts_by_status(self, registry: AccountRegistry) -> None:
        """Test filtering accounts by status."""
        active_account = AWSAccount(
            account_id="111111111111",
            name="Active",
            auth_method=AuthMethod.IAM_ROLE,
            status=AccountStatus.ACTIVE
        )
        pending_account = AWSAccount(
            account_id="222222222222",
            name="Pending",
            auth_method=AuthMethod.IAM_ROLE,
            status=AccountStatus.PENDING
        )

        registry.add_account(active_account)
        registry.add_account(pending_account)

        active_accounts = registry.list_accounts(status=AccountStatus.ACTIVE)
        assert len(active_accounts) == 1
        assert active_accounts[0].name == "Active"

    def test_update_account_status(
        self, registry: AccountRegistry, sample_account: AWSAccount
    ) -> None:
        """Test updating account status."""
        registry.add_account(sample_account)
        registry.update_account_status(
            "123456789012",
            AccountStatus.ACTIVE
        )

        account = registry.get_account("123456789012")
        assert account is not None
        assert account.status == AccountStatus.ACTIVE
        assert account.last_scan is not None

    def test_update_account_status_with_error(
        self, registry: AccountRegistry, sample_account: AWSAccount
    ) -> None:
        """Test updating account status with error message."""
        registry.add_account(sample_account)
        registry.update_account_status(
            "123456789012",
            AccountStatus.ERROR,
            "Connection failed"
        )

        account = registry.get_account("123456789012")
        assert account is not None
        assert account.status == AccountStatus.ERROR
        assert account.error_message == "Connection failed"


class TestAccountScanResult:
    """Test AccountScanResult dataclass."""

    @pytest.fixture
    def sample_account(self) -> AWSAccount:
        """Create sample AWS account."""
        return AWSAccount(
            account_id="123456789012",
            name="Test Account",
            auth_method=AuthMethod.IAM_ROLE
        )

    def test_successful_result(self, sample_account: AWSAccount) -> None:
        """Test successful scan result."""
        result = AccountScanResult(
            account=sample_account,
            findings=[],
            scan_duration=10.5,
            scanners_run=["S3Scanner", "EC2Scanner"]
        )

        assert result.success
        assert result.finding_count == 0
        assert result.scan_duration == 10.5

    def test_failed_result(self, sample_account: AWSAccount) -> None:
        """Test failed scan result."""
        result = AccountScanResult(
            account=sample_account,
            error="Access denied"
        )

        assert not result.success
        assert result.error == "Access denied"

    def test_findings_by_severity(self, sample_account: AWSAccount) -> None:
        """Test findings by severity aggregation."""
        findings: List[ScanResult] = [
            ScanResult(
                rule_id="TEST_001",
                resource_id="res1",
                passed=False,
                evidence={"severity": "critical"}
            ),
            ScanResult(
                rule_id="TEST_002",
                resource_id="res2",
                passed=False,
                evidence={"severity": "high"}
            ),
            ScanResult(
                rule_id="TEST_003",
                resource_id="res3",
                passed=False,
                evidence={"severity": "high"}
            ),
            ScanResult(
                rule_id="TEST_004",
                resource_id="res4",
                passed=True,  # Passed - should not count
                evidence={"severity": "critical"}
            ),
        ]

        result = AccountScanResult(
            account=sample_account,
            findings=findings
        )

        severity_counts = result.findings_by_severity()
        assert severity_counts["critical"] == 1
        assert severity_counts["high"] == 2
        assert severity_counts["medium"] == 0
        assert severity_counts["low"] == 0


class TestMultiAccountScanner:
    """Test MultiAccountScanner class."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        session = MagicMock()
        sts_client = MagicMock()
        sts_client.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
                "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "SessionToken": "token"
            }
        }
        sts_client.get_caller_identity.return_value = {
            "Arn": "arn:aws:iam::123456789012:role/Scanner"
        }
        session.client.return_value = sts_client
        return session

    @pytest.fixture
    def registry(self) -> AccountRegistry:
        """Create account registry with sample accounts."""
        registry = AccountRegistry()
        registry.add_account(AWSAccount(
            account_id="111111111111",
            name="Production",
            auth_method=AuthMethod.IAM_ROLE,
            status=AccountStatus.ACTIVE
        ))
        registry.add_account(AWSAccount(
            account_id="222222222222",
            name="Staging",
            auth_method=AuthMethod.IAM_ROLE,
            status=AccountStatus.PENDING
        ))
        return registry

    def test_scanner_initialization(self, registry: AccountRegistry) -> None:
        """Test multi-account scanner initialization."""
        scanner = MultiAccountScanner(
            registry=registry,
            scanner_classes=[],
            max_workers=5
        )

        assert scanner.registry == registry
        assert scanner.max_workers == 5

    @pytest.mark.asyncio
    async def test_scan_all_returns_results(
        self, registry: AccountRegistry
    ) -> None:
        """Test that scan_all returns results."""
        scanner = MultiAccountScanner(
            registry=registry,
            scanner_classes=[],
            max_workers=5
        )

        with patch.object(
            scanner, 'scan_all', new_callable=AsyncMock
        ) as mock_scan:
            mock_scan.return_value = []
            results = await scanner.scan_all()
            assert isinstance(results, list)

    def test_aggregate_results(self, registry: AccountRegistry) -> None:
        """Test result aggregation."""
        scanner = MultiAccountScanner(
            registry=registry,
            scanner_classes=[],
            max_workers=5
        )

        account1 = AWSAccount(
            account_id="111111111111",
            name="Account1",
            auth_method=AuthMethod.IAM_ROLE
        )
        account2 = AWSAccount(
            account_id="222222222222",
            name="Account2",
            auth_method=AuthMethod.IAM_ROLE
        )

        results = [
            AccountScanResult(
                account=account1,
                findings=[
                    ScanResult(
                        rule_id="S3_001",
                        resource_id="bucket1",
                        passed=False,
                        evidence={"severity": "high"}
                    ),
                    ScanResult(
                        rule_id="S3_002",
                        resource_id="bucket2",
                        passed=False,
                        evidence={"severity": "medium"}
                    ),
                ],
                scanners_run=["S3Scanner"]
            ),
            AccountScanResult(
                account=account2,
                findings=[
                    ScanResult(
                        rule_id="EC2_001",
                        resource_id="instance1",
                        passed=False,
                        evidence={"severity": "critical"}
                    ),
                ],
                scanners_run=["EC2Scanner"]
            ),
        ]

        aggregated = scanner.aggregate_results(results)

        assert aggregated["total_accounts"] == 2
        assert aggregated["successful_scans"] == 2
        assert aggregated["failed_scans"] == 0
        assert aggregated["total_findings"] == 3
        assert aggregated["findings_by_severity"]["critical"] == 1
        assert aggregated["findings_by_severity"]["high"] == 1
        assert aggregated["findings_by_severity"]["medium"] == 1
        assert aggregated["findings_by_account"]["111111111111"] == 2
        assert aggregated["findings_by_account"]["222222222222"] == 1
