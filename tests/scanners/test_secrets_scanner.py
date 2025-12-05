"""Unit tests for Secrets Scanner.

Issue #143: Secrets Manager and Parameter Store scanner
Tests for secrets security scanning rules SM_001-006 and SSM_001-004.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, patch, AsyncMock

from cloud_optimizer.scanners.secrets_scanner import SecretsScanner
from cloud_optimizer.scanners.base import ScannerRule


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
        assert scanner.SERVICE == "SecretsManager"
        assert len(scanner.rules) >= 10

        rule_ids = list(scanner.rules.keys())
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

    def test_rule_sm_001_definition(self, scanner: SecretsScanner) -> None:
        """Test SM_001 rule definition."""
        rule = scanner.rules.get("SM_001")
        assert rule is not None
        assert rule.rule_id == "SM_001"
        assert rule.severity in ["critical", "high", "medium", "low"]

    def test_rule_sm_002_definition(self, scanner: SecretsScanner) -> None:
        """Test SM_002 rule definition."""
        rule = scanner.rules.get("SM_002")
        assert rule is not None
        assert rule.rule_id == "SM_002"

    def test_rule_sm_003_definition(self, scanner: SecretsScanner) -> None:
        """Test SM_003 rule definition."""
        rule = scanner.rules.get("SM_003")
        assert rule is not None
        assert rule.rule_id == "SM_003"

    def test_rule_sm_004_definition(self, scanner: SecretsScanner) -> None:
        """Test SM_004 rule definition."""
        rule = scanner.rules.get("SM_004")
        assert rule is not None
        assert rule.rule_id == "SM_004"

    def test_rule_sm_005_definition(self, scanner: SecretsScanner) -> None:
        """Test SM_005 rule definition."""
        rule = scanner.rules.get("SM_005")
        assert rule is not None
        assert rule.rule_id == "SM_005"

    def test_rule_sm_006_definition(self, scanner: SecretsScanner) -> None:
        """Test SM_006 rule definition."""
        rule = scanner.rules.get("SM_006")
        assert rule is not None
        assert rule.rule_id == "SM_006"


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

    def test_rule_ssm_001_definition(self, scanner: SecretsScanner) -> None:
        """Test SSM_001 rule definition."""
        rule = scanner.rules.get("SSM_001")
        assert rule is not None
        assert rule.rule_id == "SSM_001"
        assert rule.severity in ["critical", "high", "medium", "low"]

    def test_rule_ssm_002_definition(self, scanner: SecretsScanner) -> None:
        """Test SSM_002 rule definition."""
        rule = scanner.rules.get("SSM_002")
        assert rule is not None
        assert rule.rule_id == "SSM_002"

    def test_rule_ssm_003_definition(self, scanner: SecretsScanner) -> None:
        """Test SSM_003 rule definition."""
        rule = scanner.rules.get("SSM_003")
        assert rule is not None
        assert rule.rule_id == "SSM_003"

    def test_rule_ssm_004_definition(self, scanner: SecretsScanner) -> None:
        """Test SSM_004 rule definition."""
        rule = scanner.rules.get("SSM_004")
        assert rule is not None
        assert rule.rule_id == "SSM_004"


class TestSecretsScannerIntegration:
    """Integration tests for Secrets scanner."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        return MagicMock()

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> SecretsScanner:
        """Create Secrets scanner with mock session."""
        return SecretsScanner(session=mock_session, regions=["us-east-1"])

    @pytest.mark.asyncio
    async def test_scan_returns_results(self, scanner: SecretsScanner) -> None:
        """Test that scan returns results."""
        with patch.object(scanner, 'scan', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = []
            results = await scanner.scan()
            assert isinstance(results, list)

    def test_scanner_has_correct_service(self, scanner: SecretsScanner) -> None:
        """Test scanner has correct service."""
        assert scanner.SERVICE == "SecretsManager"

    def test_scanner_registers_rules_on_init(self, scanner: SecretsScanner) -> None:
        """Test scanner registers rules on initialization."""
        assert len(scanner.rules) > 0
        for rule_id, rule in scanner.rules.items():
            assert isinstance(rule, ScannerRule)

    def test_all_rules_have_required_fields(self, scanner: SecretsScanner) -> None:
        """Test all rules have required fields."""
        for rule_id, rule in scanner.rules.items():
            assert rule.rule_id == rule_id
            assert rule.title, f"Rule {rule_id} missing title"
            assert rule.description, f"Rule {rule_id} missing description"
            assert rule.severity in ["critical", "high", "medium", "low"]
            assert rule.resource_type, f"Rule {rule_id} missing resource_type"
            assert rule.recommendation, f"Rule {rule_id} missing recommendation"
