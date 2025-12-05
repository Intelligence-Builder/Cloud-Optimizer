"""Unit tests for CloudFront Scanner.

Issue #140: CloudFront distribution scanner
Tests for CloudFront security scanning rules CF_001-009.
"""

import pytest

from cloud_optimizer.scanners.base import ScannerRule
from cloud_optimizer.scanners.cloudfront_scanner import CloudFrontScanner


@pytest.fixture
def scanner(boto_session) -> CloudFrontScanner:
    """Create CloudFront scanner using real boto3 session (LocalStack or AWS)."""
    return CloudFrontScanner(session=boto_session, regions=["us-east-1"])


class TestCloudFrontScannerRules:
    """Test CloudFront scanner security rules."""

    def test_scanner_initialization(self, scanner: CloudFrontScanner) -> None:
        """Test scanner initializes with correct rules."""
        assert scanner.SERVICE == "CloudFront"
        assert len(scanner.rules) >= 9

        rule_ids = list(scanner.rules.keys())
        expected_rules = [
            "CF_001",
            "CF_002",
            "CF_003",
            "CF_004",
            "CF_005",
            "CF_006",
            "CF_007",
            "CF_008",
            "CF_009",
        ]
        for expected in expected_rules:
            assert expected in rule_ids, f"Missing rule {expected}"

    def test_rule_cf_001_definition(self, scanner: CloudFrontScanner) -> None:
        """Test CF_001 rule definition."""
        rule = scanner.rules.get("CF_001")
        assert rule is not None
        assert rule.rule_id == "CF_001"
        assert rule.severity in ["critical", "high", "medium", "low"]
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_cf_002_definition(self, scanner: CloudFrontScanner) -> None:
        """Test CF_002 rule definition."""
        rule = scanner.rules.get("CF_002")
        assert rule is not None
        assert rule.rule_id == "CF_002"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_cf_003_definition(self, scanner: CloudFrontScanner) -> None:
        """Test CF_003 rule definition."""
        rule = scanner.rules.get("CF_003")
        assert rule is not None
        assert rule.rule_id == "CF_003"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_cf_004_definition(self, scanner: CloudFrontScanner) -> None:
        """Test CF_004 rule definition."""
        rule = scanner.rules.get("CF_004")
        assert rule is not None
        assert rule.rule_id == "CF_004"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_cf_005_definition(self, scanner: CloudFrontScanner) -> None:
        """Test CF_005 rule definition."""
        rule = scanner.rules.get("CF_005")
        assert rule is not None
        assert rule.rule_id == "CF_005"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_cf_006_definition(self, scanner: CloudFrontScanner) -> None:
        """Test CF_006 rule definition."""
        rule = scanner.rules.get("CF_006")
        assert rule is not None
        assert rule.rule_id == "CF_006"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_cf_007_definition(self, scanner: CloudFrontScanner) -> None:
        """Test CF_007 rule definition."""
        rule = scanner.rules.get("CF_007")
        assert rule is not None
        assert rule.rule_id == "CF_007"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_cf_008_definition(self, scanner: CloudFrontScanner) -> None:
        """Test CF_008 rule definition."""
        rule = scanner.rules.get("CF_008")
        assert rule is not None
        assert rule.rule_id == "CF_008"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_cf_009_definition(self, scanner: CloudFrontScanner) -> None:
        """Test CF_009 rule definition."""
        rule = scanner.rules.get("CF_009")
        assert rule is not None
        assert rule.rule_id == "CF_009"
        assert isinstance(rule.compliance_frameworks, list)

    def test_all_rules_have_required_fields(self, scanner: CloudFrontScanner) -> None:
        """Test all rules have required fields."""
        for rule_id, rule in scanner.rules.items():
            assert rule.rule_id == rule_id
            assert rule.title, f"Rule {rule_id} missing title"
            assert rule.description, f"Rule {rule_id} missing description"
            assert rule.severity in ["critical", "high", "medium", "low"]
            assert rule.service == "CloudFront"
            assert rule.resource_type, f"Rule {rule_id} missing resource_type"
            assert rule.recommendation, f"Rule {rule_id} missing recommendation"


class TestCloudFrontScannerMetadata:
    """Metadata validation for CloudFront scanner."""

    def test_scanner_has_correct_service(self, scanner: CloudFrontScanner) -> None:
        """Test scanner has correct service."""
        assert scanner.SERVICE == "CloudFront"

    def test_scanner_registers_rules_on_init(self, scanner: CloudFrontScanner) -> None:
        """Test scanner registers rules on initialization."""
        assert len(scanner.rules) > 0
        for rule_id, rule in scanner.rules.items():
            assert isinstance(rule, ScannerRule)
