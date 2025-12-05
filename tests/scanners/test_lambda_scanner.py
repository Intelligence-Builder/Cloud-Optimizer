"""Unit tests for Lambda Scanner.

Issue #133: Lambda function scanner with rules
Tests for Lambda function security scanning rules LAMBDA_001-010.
"""

import pytest
from typing import Any

from cloud_optimizer.scanners.lambda_scanner import LambdaScanner
from cloud_optimizer.scanners.base import ScannerRule


@pytest.fixture
def scanner(boto_session) -> LambdaScanner:
    """Create Lambda scanner using real boto3 session (LocalStack or AWS)."""
    return LambdaScanner(session=boto_session, regions=["us-east-1"])


class TestLambdaScannerRules:
    """Test Lambda scanner security rules."""

    def test_scanner_initialization(self, scanner: LambdaScanner) -> None:
        """Test scanner initializes with correct rules."""
        assert scanner.SERVICE == "Lambda"
        assert len(scanner.rules) >= 10

        rule_ids = list(scanner.rules.keys())
        expected_rules = [
            "LAMBDA_001", "LAMBDA_002", "LAMBDA_003", "LAMBDA_004",
            "LAMBDA_005", "LAMBDA_006", "LAMBDA_007", "LAMBDA_008",
            "LAMBDA_009", "LAMBDA_010"
        ]
        for expected in expected_rules:
            assert expected in rule_ids, f"Missing rule {expected}"

    def test_rule_lambda_001_definition(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_001 rule definition."""
        rule = scanner.rules.get("LAMBDA_001")
        assert rule is not None
        assert rule.rule_id == "LAMBDA_001"
        assert rule.severity in ["critical", "high", "medium", "low"]
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_lambda_002_definition(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_002 rule definition."""
        rule = scanner.rules.get("LAMBDA_002")
        assert rule is not None
        assert rule.rule_id == "LAMBDA_002"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_lambda_003_definition(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_003 rule definition."""
        rule = scanner.rules.get("LAMBDA_003")
        assert rule is not None
        assert rule.rule_id == "LAMBDA_003"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_lambda_004_definition(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_004 rule definition."""
        rule = scanner.rules.get("LAMBDA_004")
        assert rule is not None
        assert rule.rule_id == "LAMBDA_004"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_lambda_005_definition(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_005 rule definition."""
        rule = scanner.rules.get("LAMBDA_005")
        assert rule is not None
        assert rule.rule_id == "LAMBDA_005"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_lambda_006_definition(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_006 rule definition."""
        rule = scanner.rules.get("LAMBDA_006")
        assert rule is not None
        assert rule.rule_id == "LAMBDA_006"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_lambda_007_definition(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_007 rule definition."""
        rule = scanner.rules.get("LAMBDA_007")
        assert rule is not None
        assert rule.rule_id == "LAMBDA_007"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_lambda_008_definition(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_008 rule definition."""
        rule = scanner.rules.get("LAMBDA_008")
        assert rule is not None
        assert rule.rule_id == "LAMBDA_008"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_lambda_009_definition(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_009 rule definition."""
        rule = scanner.rules.get("LAMBDA_009")
        assert rule is not None
        assert rule.rule_id == "LAMBDA_009"
        assert isinstance(rule.compliance_frameworks, list)

    def test_rule_lambda_010_definition(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_010 rule definition."""
        rule = scanner.rules.get("LAMBDA_010")
        assert rule is not None
        assert rule.rule_id == "LAMBDA_010"
        assert isinstance(rule.compliance_frameworks, list)

    def test_all_rules_have_required_fields(self, scanner: LambdaScanner) -> None:
        """Test all rules have required fields."""
        for rule_id, rule in scanner.rules.items():
            assert rule.rule_id == rule_id
            assert rule.title, f"Rule {rule_id} missing title"
            assert rule.description, f"Rule {rule_id} missing description"
            assert rule.severity in ["critical", "high", "medium", "low"]
            assert rule.service == "Lambda"
            assert rule.resource_type, f"Rule {rule_id} missing resource_type"
            assert rule.recommendation, f"Rule {rule_id} missing recommendation"


class TestLambdaScannerMetadata:
    """Metadata validation for Lambda scanner."""

    def test_scanner_has_correct_service(self, scanner: LambdaScanner) -> None:
        """Test scanner has correct service."""
        assert scanner.SERVICE == "Lambda"

    def test_scanner_registers_rules_on_init(self, scanner: LambdaScanner) -> None:
        """Test scanner registers rules on initialization."""
        assert len(scanner.rules) > 0
        for rule_id, rule in scanner.rules.items():
            assert isinstance(rule, ScannerRule)
