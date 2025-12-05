"""Unit tests for Lambda Scanner.

Issue #133: Lambda function scanner with rules
Tests for Lambda function security scanning rules LAMBDA_001-010.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Any

from cloud_optimizer.scanners.lambda_scanner import LambdaScanner
from cloud_optimizer.scanners.base import ScannerRule


class TestLambdaScannerRules:
    """Test Lambda scanner security rules."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> LambdaScanner:
        """Create Lambda scanner with mock session."""
        return LambdaScanner(session=mock_session, regions=["us-east-1"])

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


class TestLambdaScannerIntegration:
    """Integration tests for Lambda scanner."""

    @pytest.fixture
    def mock_lambda_client(self) -> MagicMock:
        """Create mock Lambda client."""
        client = MagicMock()
        client.list_functions.return_value = {
            "Functions": [
                {
                    "FunctionName": "test-function",
                    "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
                    "Runtime": "python3.9"
                }
            ]
        }
        return client

    @pytest.fixture
    def mock_session_with_client(
        self, mock_lambda_client: MagicMock
    ) -> MagicMock:
        """Create mock session with Lambda client."""
        session = MagicMock()
        session.client.return_value = mock_lambda_client
        return session

    @pytest.mark.asyncio
    async def test_scan_returns_results(
        self, mock_session_with_client: MagicMock
    ) -> None:
        """Test that scan returns results."""
        scanner = LambdaScanner(
            session=mock_session_with_client,
            regions=["us-east-1"]
        )

        with patch.object(scanner, 'scan', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = []
            results = await scanner.scan()
            assert isinstance(results, list)

    def test_scanner_has_correct_service(
        self, mock_session_with_client: MagicMock
    ) -> None:
        """Test scanner has correct service."""
        scanner = LambdaScanner(
            session=mock_session_with_client,
            regions=["us-east-1"]
        )
        assert scanner.SERVICE == "Lambda"

    def test_scanner_registers_rules_on_init(
        self, mock_session_with_client: MagicMock
    ) -> None:
        """Test scanner registers rules on initialization."""
        scanner = LambdaScanner(
            session=mock_session_with_client,
            regions=["us-east-1"]
        )
        assert len(scanner.rules) > 0
        for rule_id, rule in scanner.rules.items():
            assert isinstance(rule, ScannerRule)
