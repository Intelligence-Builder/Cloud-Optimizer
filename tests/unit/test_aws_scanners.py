"""
Unit tests for AWS scanners - Pure logic tests only.

These tests verify scanner logic WITHOUT mocking AWS services.
AWS interaction tests are in tests/integration/test_epic3_app.py using LocalStack.

Testing Strategy:
- Unit tests: Test internal logic (severity calculation, port descriptions, etc.)
- Integration tests: Test actual AWS API interactions via LocalStack
"""

import pytest

from cloud_optimizer.integrations.aws.base import BaseAWSScanner
from cloud_optimizer.integrations.aws.encryption import EncryptionScanner
from cloud_optimizer.integrations.aws.iam import IAMScanner
from cloud_optimizer.integrations.aws.security_groups import SecurityGroupScanner


class TestBaseAWSScanner:
    """Tests for BaseAWSScanner initialization and configuration."""

    def test_scanner_initialization_default_region(self):
        """Test scanner initializes with default region."""

        class TestScanner(BaseAWSScanner):
            async def scan(self, account_id: str):
                return []

            def get_scanner_name(self) -> str:
                return "TestScanner"

        scanner = TestScanner()
        assert scanner.region == "us-east-1"

    def test_scanner_initialization_custom_region(self):
        """Test scanner initializes with custom region."""

        class TestScanner(BaseAWSScanner):
            async def scan(self, account_id: str):
                return []

            def get_scanner_name(self) -> str:
                return "TestScanner"

        scanner = TestScanner(region="us-west-2")
        assert scanner.region == "us-west-2"

    def test_scanner_name_abstract(self):
        """Test get_scanner_name must be implemented."""

        with pytest.raises(TypeError):
            # Cannot instantiate abstract class
            BaseAWSScanner()


class TestSecurityGroupScanner:
    """Tests for SecurityGroupScanner internal logic."""

    def test_scanner_name(self):
        """Test scanner returns correct name."""
        scanner = SecurityGroupScanner()
        assert scanner.get_scanner_name() == "SecurityGroupScanner"

    def test_risky_ports_defined(self):
        """Test risky ports are properly defined."""
        assert 22 in SecurityGroupScanner.RISKY_PORTS  # SSH
        assert 3389 in SecurityGroupScanner.RISKY_PORTS  # RDP
        assert 3306 in SecurityGroupScanner.RISKY_PORTS  # MySQL
        assert 5432 in SecurityGroupScanner.RISKY_PORTS  # PostgreSQL
        assert 27017 in SecurityGroupScanner.RISKY_PORTS  # MongoDB

    def test_unrestricted_cidr_defined(self):
        """Test unrestricted CIDR is defined."""
        assert SecurityGroupScanner.UNRESTRICTED_CIDR == "0.0.0.0/0"

    def test_calculate_severity_for_ssh(self):
        """Test severity is critical for SSH port."""
        scanner = SecurityGroupScanner()
        severity = scanner._calculate_severity(22, 22)
        assert severity == "critical"

    def test_calculate_severity_for_rdp(self):
        """Test severity is critical for RDP port."""
        scanner = SecurityGroupScanner()
        severity = scanner._calculate_severity(3389, 3389)
        assert severity == "critical"

    def test_calculate_severity_for_database_ports(self):
        """Test severity is critical for database ports."""
        scanner = SecurityGroupScanner()

        # MySQL
        assert scanner._calculate_severity(3306, 3306) == "critical"
        # PostgreSQL
        assert scanner._calculate_severity(5432, 5432) == "critical"
        # MongoDB
        assert scanner._calculate_severity(27017, 27017) == "critical"

    def test_calculate_severity_for_wide_range(self):
        """Test severity is high for wide port ranges."""
        scanner = SecurityGroupScanner()
        # Wide range not including risky ports
        severity = scanner._calculate_severity(8000, 8200)
        assert severity == "high"

    def test_calculate_severity_for_range_including_risky_port(self):
        """Test severity is critical for range including risky port."""
        scanner = SecurityGroupScanner()
        # Range including SSH port
        severity = scanner._calculate_severity(20, 25)
        assert severity == "critical"

    def test_calculate_severity_for_narrow_safe_range(self):
        """Test severity is medium for narrow safe port range."""
        scanner = SecurityGroupScanner()
        # Narrow range without risky ports
        severity = scanner._calculate_severity(8080, 8080)
        assert severity == "medium"

    def test_get_port_description_ssh(self):
        """Test port description for SSH."""
        scanner = SecurityGroupScanner()
        desc = scanner._get_port_description(22, 22)
        assert desc == "SSH (22)"

    def test_get_port_description_rdp(self):
        """Test port description for RDP."""
        scanner = SecurityGroupScanner()
        desc = scanner._get_port_description(3389, 3389)
        assert desc == "RDP (3389)"

    def test_get_port_description_mysql(self):
        """Test port description for MySQL."""
        scanner = SecurityGroupScanner()
        desc = scanner._get_port_description(3306, 3306)
        assert desc == "MySQL (3306)"

    def test_get_port_description_postgres(self):
        """Test port description for PostgreSQL."""
        scanner = SecurityGroupScanner()
        desc = scanner._get_port_description(5432, 5432)
        assert desc == "PostgreSQL (5432)"

    def test_get_port_description_range(self):
        """Test port description for port range."""
        scanner = SecurityGroupScanner()
        desc = scanner._get_port_description(80, 443)
        assert desc == "ports 80-443"

    def test_get_port_description_unknown_port(self):
        """Test port description for unknown port."""
        scanner = SecurityGroupScanner()
        desc = scanner._get_port_description(9999, 9999)
        assert desc == "port 9999"

    def test_create_finding_structure(self):
        """Test finding has correct structure."""
        scanner = SecurityGroupScanner()
        finding = scanner._create_finding(
            sg_id="sg-123456",
            sg_name="test-sg",
            from_port=22,
            to_port=22,
            protocol="tcp",
            cidr="0.0.0.0/0",
            account_id="123456789012",
        )

        assert finding["finding_type"] == "overly_permissive_security_group"
        assert finding["severity"] == "critical"
        assert "SSH" in finding["title"]
        assert finding["resource_id"] == "sg-123456"
        assert finding["resource_name"] == "test-sg"
        assert finding["resource_type"] == "security_group"
        assert finding["aws_account_id"] == "123456789012"
        assert "remediation" in finding
        assert finding["metadata"]["from_port"] == 22
        assert finding["metadata"]["to_port"] == 22
        assert finding["metadata"]["protocol"] == "tcp"
        assert finding["metadata"]["cidr"] == "0.0.0.0/0"


class TestIAMScanner:
    """Tests for IAMScanner internal logic."""

    def test_scanner_name(self):
        """Test scanner returns correct name."""
        scanner = IAMScanner()
        assert scanner.get_scanner_name() == "IAMScanner"

    def test_inactive_days_threshold(self):
        """Test inactive days threshold is defined."""
        assert IAMScanner.INACTIVE_DAYS_THRESHOLD == 90

    def test_has_wildcard_permissions_with_action_wildcard(self):
        """Test detection of wildcard action."""
        scanner = IAMScanner()

        policy_doc = {
            "Statement": [
                {"Effect": "Allow", "Action": "*", "Resource": "arn:aws:s3:::bucket"}
            ]
        }

        assert scanner._has_wildcard_permissions(policy_doc) is True

    def test_has_wildcard_permissions_with_resource_wildcard(self):
        """Test detection of wildcard resource."""
        scanner = IAMScanner()

        policy_doc = {
            "Statement": [
                {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "*"}
            ]
        }

        assert scanner._has_wildcard_permissions(policy_doc) is True

    def test_has_wildcard_permissions_with_both_wildcards(self):
        """Test detection of both wildcards."""
        scanner = IAMScanner()

        policy_doc = {
            "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]
        }

        assert scanner._has_wildcard_permissions(policy_doc) is True

    def test_has_wildcard_permissions_no_wildcard(self):
        """Test no false positive for specific permissions."""
        scanner = IAMScanner()

        policy_doc = {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:GetObject", "s3:ListBucket"],
                    "Resource": [
                        "arn:aws:s3:::specific-bucket",
                        "arn:aws:s3:::specific-bucket/*",
                    ],
                }
            ]
        }

        assert scanner._has_wildcard_permissions(policy_doc) is False

    def test_has_wildcard_permissions_deny_statement(self):
        """Test Deny statements are not flagged."""
        scanner = IAMScanner()

        policy_doc = {"Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]}

        assert scanner._has_wildcard_permissions(policy_doc) is False

    def test_has_wildcard_permissions_single_statement_dict(self):
        """Test handling of single statement as dict (not list)."""
        scanner = IAMScanner()

        policy_doc = {"Statement": {"Effect": "Allow", "Action": "*", "Resource": "*"}}

        assert scanner._has_wildcard_permissions(policy_doc) is True

    def test_has_wildcard_permissions_string_action(self):
        """Test handling of single action as string."""
        scanner = IAMScanner()

        policy_doc = {
            "Statement": [
                {"Effect": "Allow", "Action": "*", "Resource": "arn:aws:s3:::bucket"}
            ]
        }

        assert scanner._has_wildcard_permissions(policy_doc) is True

    def test_create_no_mfa_finding_structure(self):
        """Test MFA finding has correct structure."""
        scanner = IAMScanner()
        finding = scanner._create_no_mfa_finding(
            user_name="test-user",
            account_id="123456789012",
        )

        assert finding["finding_type"] == "iam_user_no_mfa"
        assert finding["severity"] == "medium"
        assert "MFA" in finding["title"]
        assert finding["resource_name"] == "test-user"
        assert finding["resource_type"] == "iam_user"
        assert finding["aws_account_id"] == "123456789012"
        assert "remediation" in finding

    def test_create_wildcard_policy_finding_structure(self):
        """Test wildcard policy finding has correct structure."""
        scanner = IAMScanner()
        finding = scanner._create_wildcard_policy_finding(
            policy_arn="arn:aws:iam::123456789012:policy/test-policy",
            policy_name="test-policy",
            account_id="123456789012",
        )

        assert finding["finding_type"] == "wildcard_iam_permissions"
        assert finding["severity"] == "high"
        assert "wildcard" in finding["title"].lower()
        assert finding["resource_name"] == "test-policy"
        assert finding["resource_type"] == "iam_policy"
        assert "remediation" in finding


class TestEncryptionScanner:
    """Tests for EncryptionScanner internal logic."""

    def test_scanner_name(self):
        """Test scanner returns correct name."""
        scanner = EncryptionScanner()
        assert scanner.get_scanner_name() == "EncryptionScanner"

    def test_scanner_region(self):
        """Test scanner region configuration."""
        scanner = EncryptionScanner(region="eu-west-1")
        assert scanner.region == "eu-west-1"
