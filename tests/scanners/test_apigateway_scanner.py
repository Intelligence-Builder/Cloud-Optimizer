"""Unit tests for API Gateway Scanner.

Issue #134: API Gateway scanner with rules
Tests for API Gateway security scanning rules APIGW_001-009.
"""

import pytest

from cloud_optimizer.scanners.apigateway_scanner import APIGatewayScanner
from cloud_optimizer.scanners.base import ScannerRule


@pytest.fixture
def scanner(boto_session) -> APIGatewayScanner:
    """Create API Gateway scanner using real boto3 session (LocalStack or AWS)."""
    return APIGatewayScanner(session=boto_session, regions=["us-east-1"])


class TestAPIGatewayScannerRules:
    """Test API Gateway scanner security rules."""

    def test_scanner_initialization(self, scanner: APIGatewayScanner) -> None:
        """Test scanner initializes with correct rules."""
        assert scanner.SERVICE == "APIGateway"
        assert len(scanner.rules) >= 9

        rule_ids = list(scanner.rules.keys())
        expected_rules = [
            "APIGW_001", "APIGW_002", "APIGW_003", "APIGW_004", "APIGW_005",
            "APIGW_006", "APIGW_007", "APIGW_008", "APIGW_009"
        ]
        for expected in expected_rules:
            assert expected in rule_ids, f"Missing rule {expected}"

    def test_rule_apigw_001_definition(self, scanner: APIGatewayScanner) -> None:
        """Test APIGW_001 rule definition."""
        rule = scanner.rules.get("APIGW_001")
        assert rule is not None
        assert rule.rule_id == "APIGW_001"
        assert rule.severity == "critical"
        assert "authentication" in rule.description.lower()
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_apigw_002_definition(self, scanner: APIGatewayScanner) -> None:
        """Test APIGW_002 rule definition."""
        rule = scanner.rules.get("APIGW_002")
        assert rule is not None
        assert rule.rule_id == "APIGW_002"
        assert rule.severity == "critical"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_apigw_003_definition(self, scanner: APIGatewayScanner) -> None:
        """Test APIGW_003 rule definition."""
        rule = scanner.rules.get("APIGW_003")
        assert rule is not None
        assert rule.rule_id == "APIGW_003"
        assert rule.severity in ["critical", "high", "medium", "low"]
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_apigw_004_definition(self, scanner: APIGatewayScanner) -> None:
        """Test APIGW_004 rule definition."""
        rule = scanner.rules.get("APIGW_004")
        assert rule is not None
        assert rule.rule_id == "APIGW_004"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_apigw_005_definition(self, scanner: APIGatewayScanner) -> None:
        """Test APIGW_005 rule definition."""
        rule = scanner.rules.get("APIGW_005")
        assert rule is not None
        assert rule.rule_id == "APIGW_005"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_apigw_006_definition(self, scanner: APIGatewayScanner) -> None:
        """Test APIGW_006 rule definition."""
        rule = scanner.rules.get("APIGW_006")
        assert rule is not None
        assert rule.rule_id == "APIGW_006"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_apigw_007_definition(self, scanner: APIGatewayScanner) -> None:
        """Test APIGW_007 rule definition."""
        rule = scanner.rules.get("APIGW_007")
        assert rule is not None
        assert rule.rule_id == "APIGW_007"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_apigw_008_definition(self, scanner: APIGatewayScanner) -> None:
        """Test APIGW_008 rule definition."""
        rule = scanner.rules.get("APIGW_008")
        assert rule is not None
        assert rule.rule_id == "APIGW_008"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_apigw_009_definition(self, scanner: APIGatewayScanner) -> None:
        """Test APIGW_009 rule definition."""
        rule = scanner.rules.get("APIGW_009")
        assert rule is not None
        assert rule.rule_id == "APIGW_009"
        assert isinstance(rule.compliance_frameworks, list)

    def test_all_rules_have_required_fields(self, scanner: APIGatewayScanner) -> None:
        """Test all rules have required fields."""
        for rule_id, rule in scanner.rules.items():
            assert rule.rule_id == rule_id
            assert rule.title, f"Rule {rule_id} missing title"
            assert rule.description, f"Rule {rule_id} missing description"
            assert rule.severity in ["critical", "high", "medium", "low"]
            assert rule.service == "APIGateway"
            assert rule.resource_type, f"Rule {rule_id} missing resource_type"
            assert rule.recommendation, f"Rule {rule_id} missing recommendation"


class TestAPIGatewayScannerMetadata:
    """Metadata validation for API Gateway scanner."""

    def test_scanner_has_correct_service(self, scanner: APIGatewayScanner) -> None:
        """Test scanner has correct service."""
        assert scanner.SERVICE == "APIGateway"

    def test_scanner_registers_rules_on_init(self, scanner: APIGatewayScanner) -> None:
        """Test scanner registers rules on initialization."""
        assert len(scanner.rules) > 0
        for rule_id, rule in scanner.rules.items():
            assert isinstance(rule, ScannerRule)
