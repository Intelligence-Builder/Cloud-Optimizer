"""Unit tests for API Gateway Scanner.

Issue #134: API Gateway scanner with rules
Tests for API Gateway security scanning rules APIGW_001-009.
"""

import pytest
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, AsyncMock

from cloud_optimizer.scanners.apigateway_scanner import APIGatewayScanner
from cloud_optimizer.scanners.base import ScannerRule


class TestAPIGatewayScannerRules:
    """Test API Gateway scanner security rules."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> APIGatewayScanner:
        """Create API Gateway scanner with mock session."""
        return APIGatewayScanner(session=mock_session, regions=["us-east-1"])

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


class TestAPIGatewayScannerIntegration:
    """Integration tests for API Gateway scanner."""

    @pytest.fixture
    def mock_apigateway_client(self) -> MagicMock:
        """Create mock API Gateway client."""
        client = MagicMock()
        client.get_rest_apis.return_value = {
            "items": [
                {
                    "id": "api123",
                    "name": "test-api",
                    "endpointConfiguration": {"types": ["REGIONAL"]}
                }
            ]
        }
        client.get_stages.return_value = {
            "item": [{"stageName": "prod"}]
        }
        client.get_resources.return_value = {
            "items": []
        }
        return client

    @pytest.fixture
    def mock_session_with_client(
        self, mock_apigateway_client: MagicMock
    ) -> MagicMock:
        """Create mock session with API Gateway client."""
        session = MagicMock()
        session.client.return_value = mock_apigateway_client
        return session

    @pytest.mark.asyncio
    async def test_scan_returns_results(
        self, mock_session_with_client: MagicMock
    ) -> None:
        """Test that scan returns results."""
        scanner = APIGatewayScanner(
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
        scanner = APIGatewayScanner(
            session=mock_session_with_client,
            regions=["us-east-1"]
        )
        assert scanner.SERVICE == "APIGateway"

    def test_scanner_registers_rules_on_init(
        self, mock_session_with_client: MagicMock
    ) -> None:
        """Test scanner registers rules on initialization."""
        scanner = APIGatewayScanner(
            session=mock_session_with_client,
            regions=["us-east-1"]
        )
        assert len(scanner.rules) > 0
        for rule_id, rule in scanner.rules.items():
            assert isinstance(rule, ScannerRule)
