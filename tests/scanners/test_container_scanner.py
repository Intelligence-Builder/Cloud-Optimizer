"""Unit tests for Container Scanner (EKS/ECS).

Issue #142: EKS/ECS container security scanner
Tests for container security scanning rules EKS_001-004 and ECS_001-008.
"""

import pytest

from cloud_optimizer.scanners.container_scanner import ContainerScanner
from cloud_optimizer.scanners.base import ScannerRule


@pytest.fixture
def scanner(boto_session) -> ContainerScanner:
    """Create Container scanner using real boto3 session (LocalStack or AWS)."""
    return ContainerScanner(session=boto_session, regions=["us-east-1"])


class TestContainerScannerRules:
    """Test Container scanner security rules."""

    def test_scanner_initialization(self, scanner: ContainerScanner) -> None:
        """Test scanner initializes with correct rules."""
        assert scanner.SERVICE == "Container"
        assert len(scanner.rules) >= 12

        rule_ids = list(scanner.rules.keys())
        expected_rules = [
            "EKS_001", "EKS_002", "EKS_003", "EKS_004",
            "ECS_001", "ECS_002", "ECS_003", "ECS_004",
            "ECS_005", "ECS_006", "ECS_007", "ECS_008"
        ]
        for expected in expected_rules:
            assert expected in rule_ids, f"Missing rule {expected}"


class TestEKSRules:
    """Test EKS-specific security rules."""

    def test_rule_eks_001_definition(self, scanner: ContainerScanner) -> None:
        """Test EKS_001 rule definition."""
        rule = scanner.rules.get("EKS_001")
        assert rule is not None
        assert rule.rule_id == "EKS_001"
        assert rule.severity in ["critical", "high", "medium", "low"]

    def test_rule_eks_002_definition(self, scanner: ContainerScanner) -> None:
        """Test EKS_002 rule definition."""
        rule = scanner.rules.get("EKS_002")
        assert rule is not None
        assert rule.rule_id == "EKS_002"

    def test_rule_eks_003_definition(self, scanner: ContainerScanner) -> None:
        """Test EKS_003 rule definition."""
        rule = scanner.rules.get("EKS_003")
        assert rule is not None
        assert rule.rule_id == "EKS_003"

    def test_rule_eks_004_definition(self, scanner: ContainerScanner) -> None:
        """Test EKS_004 rule definition."""
        rule = scanner.rules.get("EKS_004")
        assert rule is not None
        assert rule.rule_id == "EKS_004"


class TestECSRules:
    """Test ECS-specific security rules."""

    def test_rule_ecs_001_definition(self, scanner: ContainerScanner) -> None:
        """Test ECS_001 rule definition."""
        rule = scanner.rules.get("ECS_001")
        assert rule is not None
        assert rule.rule_id == "ECS_001"
        assert rule.severity in ["critical", "high", "medium", "low"]

    def test_rule_ecs_002_definition(self, scanner: ContainerScanner) -> None:
        """Test ECS_002 rule definition."""
        rule = scanner.rules.get("ECS_002")
        assert rule is not None
        assert rule.rule_id == "ECS_002"

    def test_rule_ecs_003_definition(self, scanner: ContainerScanner) -> None:
        """Test ECS_003 rule definition."""
        rule = scanner.rules.get("ECS_003")
        assert rule is not None
        assert rule.rule_id == "ECS_003"

    def test_rule_ecs_004_definition(self, scanner: ContainerScanner) -> None:
        """Test ECS_004 rule definition."""
        rule = scanner.rules.get("ECS_004")
        assert rule is not None
        assert rule.rule_id == "ECS_004"

    def test_rule_ecs_005_definition(self, scanner: ContainerScanner) -> None:
        """Test ECS_005 rule definition."""
        rule = scanner.rules.get("ECS_005")
        assert rule is not None
        assert rule.rule_id == "ECS_005"

    def test_rule_ecs_006_definition(self, scanner: ContainerScanner) -> None:
        """Test ECS_006 rule definition."""
        rule = scanner.rules.get("ECS_006")
        assert rule is not None
        assert rule.rule_id == "ECS_006"

    def test_rule_ecs_007_definition(self, scanner: ContainerScanner) -> None:
        """Test ECS_007 rule definition."""
        rule = scanner.rules.get("ECS_007")
        assert rule is not None
        assert rule.rule_id == "ECS_007"

    def test_rule_ecs_008_definition(self, scanner: ContainerScanner) -> None:
        """Test ECS_008 rule definition."""
        rule = scanner.rules.get("ECS_008")
        assert rule is not None
        assert rule.rule_id == "ECS_008"


class TestContainerScannerMetadata:
    """Verify scanner metadata and rule registration."""

    def test_scanner_has_correct_service(self, scanner: ContainerScanner) -> None:
        """Test scanner has correct service."""
        assert scanner.SERVICE == "Container"

    def test_scanner_registers_rules_on_init(self, scanner: ContainerScanner) -> None:
        """Test scanner registers rules on initialization."""
        assert len(scanner.rules) > 0
        for rule_id, rule in scanner.rules.items():
            assert isinstance(rule, ScannerRule)

    def test_all_rules_have_required_fields(self, scanner: ContainerScanner) -> None:
        """Test all rules have required fields."""
        for rule_id, rule in scanner.rules.items():
            assert rule.rule_id == rule_id
            assert rule.title, f"Rule {rule_id} missing title"
            assert rule.description, f"Rule {rule_id} missing description"
            assert rule.severity in ["critical", "high", "medium", "low"]
            assert rule.resource_type, f"Rule {rule_id} missing resource_type"
            assert rule.recommendation, f"Rule {rule_id} missing recommendation"
