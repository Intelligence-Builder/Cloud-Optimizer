"""Unit tests for Custom Rule Engine and Import/Export.

Issue #150: Custom rule engine for user-defined checks
Issue #151: Rule import/export functionality
Tests for custom rule definition, evaluation, validation, and import/export.
"""

import json
import pytest
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from cloud_optimizer.scanners.custom_rules import (
    CustomRule,
    RuleCondition,
    RuleEngine,
    RuleImportExporter,
    RuleOperator,
    RulePackage,
    RuleType,
)


class TestRuleOperator:
    """Test RuleOperator enum."""

    def test_equals_operator_exists(self) -> None:
        """Test EQUALS operator exists."""
        assert RuleOperator.EQUALS == "equals"

    def test_not_equals_operator_exists(self) -> None:
        """Test NOT_EQUALS operator exists."""
        assert RuleOperator.NOT_EQUALS == "not_equals"

    def test_contains_operator_exists(self) -> None:
        """Test CONTAINS operator exists."""
        assert RuleOperator.CONTAINS == "contains"

    def test_not_contains_operator_exists(self) -> None:
        """Test NOT_CONTAINS operator exists."""
        assert RuleOperator.NOT_CONTAINS == "not_contains"

    def test_matches_operator_exists(self) -> None:
        """Test MATCHES operator exists."""
        assert RuleOperator.MATCHES == "matches"

    def test_exists_operator_exists(self) -> None:
        """Test EXISTS operator exists."""
        assert RuleOperator.EXISTS == "exists"

    def test_greater_than_operator_exists(self) -> None:
        """Test GREATER_THAN operator exists."""
        assert RuleOperator.GREATER_THAN == "greater_than"

    def test_less_than_operator_exists(self) -> None:
        """Test LESS_THAN operator exists."""
        assert RuleOperator.LESS_THAN == "less_than"

    def test_in_operator_exists(self) -> None:
        """Test IN operator exists."""
        assert RuleOperator.IN == "in"

    def test_not_in_operator_exists(self) -> None:
        """Test NOT_IN operator exists."""
        assert RuleOperator.NOT_IN == "not_in"


class TestRuleCondition:
    """Test RuleCondition dataclass."""

    def test_condition_creation(self) -> None:
        """Test creating a rule condition."""
        condition = RuleCondition(
            field="Status",
            operator=RuleOperator.EQUALS,
            value="Active"
        )
        assert condition.field == "Status"
        assert condition.operator == RuleOperator.EQUALS
        assert condition.value == "Active"

    def test_condition_with_key(self) -> None:
        """Test condition with key field."""
        condition = RuleCondition(
            field="Tags",
            operator=RuleOperator.EXISTS,
            key="Environment"
        )
        assert condition.key == "Environment"


class TestRuleType:
    """Test RuleType enum."""

    def test_configuration_type_exists(self) -> None:
        """Test CONFIGURATION type exists."""
        assert RuleType.CONFIGURATION == "configuration"

    def test_tag_type_exists(self) -> None:
        """Test TAG type exists."""
        assert RuleType.TAG == "tag"

    def test_naming_type_exists(self) -> None:
        """Test NAMING type exists."""
        assert RuleType.NAMING == "naming"

    def test_relationship_type_exists(self) -> None:
        """Test RELATIONSHIP type exists."""
        assert RuleType.RELATIONSHIP == "relationship"

    def test_cost_type_exists(self) -> None:
        """Test COST type exists."""
        assert RuleType.COST == "cost"


class TestCustomRule:
    """Test CustomRule dataclass."""

    def test_rule_creation(self) -> None:
        """Test creating a custom rule."""
        rule = CustomRule(
            rule_id="CUSTOM_001",
            name="Test Rule",
            description="A test rule",
            severity="high",
            rule_type=RuleType.CONFIGURATION,
            resource_types=["AWS::EC2::Instance"]
        )
        assert rule.rule_id == "CUSTOM_001"
        assert rule.name == "Test Rule"
        assert rule.severity == "high"
        assert rule.rule_type == RuleType.CONFIGURATION

    def test_rule_default_values(self) -> None:
        """Test rule default values."""
        rule = CustomRule(
            rule_id="CUSTOM_002",
            name="Default Test",
            description="Test defaults"
        )
        assert rule.severity == "medium"
        assert rule.enabled is True
        assert rule.version == "1.0"
        assert rule.created_at is not None

    def test_rule_to_scanner_rule(self) -> None:
        """Test converting to ScannerRule."""
        rule = CustomRule(
            rule_id="CUSTOM_003",
            name="Conversion Test",
            description="Test conversion",
            severity="critical",
            resource_types=["AWS::S3::Bucket"],
            remediation="Fix the issue"
        )
        scanner_rule = rule.to_scanner_rule()
        assert scanner_rule.rule_id == "CUSTOM_003"
        assert scanner_rule.title == "Conversion Test"
        assert scanner_rule.severity == "critical"


class TestRuleEngine:
    """Test RuleEngine class."""

    def _create_valid_rule(self, rule_id: str, name: str = "Test Rule") -> CustomRule:
        """Create a valid rule that passes validation."""
        return CustomRule(
            rule_id=rule_id,
            name=name,
            description="Test description",
            resource_types=["AWS::EC2::Instance"],
            conditions={
                "operator": "equals",
                "field": "Status",
                "value": "running"
            }
        )

    def test_engine_creation(self) -> None:
        """Test creating a rule engine."""
        engine = RuleEngine()
        assert engine is not None

    def test_register_rule(self) -> None:
        """Test registering a rule."""
        engine = RuleEngine()
        rule = self._create_valid_rule("TEST_001")
        result = engine.register_rule(rule)
        assert result is True
        assert engine.get_rule("TEST_001") is not None

    def test_get_rule(self) -> None:
        """Test getting a rule."""
        engine = RuleEngine()
        rule = self._create_valid_rule("TEST_002")
        engine.register_rule(rule)
        retrieved = engine.get_rule("TEST_002")
        assert retrieved is not None
        assert retrieved.rule_id == "TEST_002"

    def test_list_rules(self) -> None:
        """Test listing all rules."""
        engine = RuleEngine()
        rule1 = self._create_valid_rule("TEST_003", "Test Rule 1")
        rule2 = self._create_valid_rule("TEST_004", "Test Rule 2")
        engine.register_rule(rule1)
        engine.register_rule(rule2)
        rules = engine.list_rules()
        assert len(rules) >= 2

    def test_unregister_rule(self) -> None:
        """Test unregistering a rule."""
        engine = RuleEngine()
        rule = self._create_valid_rule("TEST_005")
        engine.register_rule(rule)
        result = engine.unregister_rule("TEST_005")
        assert result is True
        assert engine.get_rule("TEST_005") is None


class TestRulePackage:
    """Test RulePackage dataclass."""

    def test_package_creation(self) -> None:
        """Test creating a rule package."""
        rules = [
            CustomRule(
                rule_id="PKG_001",
                name="Package Rule 1",
                description="Test rule 1"
            ),
            CustomRule(
                rule_id="PKG_002",
                name="Package Rule 2",
                description="Test rule 2"
            )
        ]
        package = RulePackage(
            name="Test Package",
            description="A test package",
            version="1.0",
            rules=rules
        )
        assert package.name == "Test Package"
        assert len(package.rules) == 2


class TestRuleImportExporter:
    """Test RuleImportExporter class."""

    def test_exporter_creation(self) -> None:
        """Test creating an exporter."""
        exporter = RuleImportExporter()
        assert exporter is not None

    def test_export_to_json(self) -> None:
        """Test exporting rules to JSON."""
        rules = [
            CustomRule(
                rule_id="JSON_001",
                name="JSON Rule",
                description="JSON test",
                resource_types=["AWS::EC2::Instance"],
                conditions={"operator": "equals", "field": "Status", "value": "running"}
            )
        ]
        json_str = RuleImportExporter.export_to_json(rules)
        assert "JSON_001" in json_str
        data = json.loads(json_str)
        assert len(data["rules"]) == 1
        # Note: export uses "id" not "rule_id"
        assert data["rules"][0]["id"] == "JSON_001"

    def test_import_from_json(self) -> None:
        """Test importing rules from JSON."""
        # Note: import expects "id" not "rule_id"
        json_data = {
            "rules": [
                {
                    "id": "IMPORT_001",
                    "name": "Import Test",
                    "description": "Test import",
                    "severity": "high",
                    "rule_type": "configuration",
                    "resource_types": ["AWS::S3::Bucket"],
                    "conditions": {"operator": "equals", "field": "Status", "value": "active"},
                    "remediation": "",
                    "compliance_frameworks": [],
                    "metadata": {"author": "", "version": "1.0"},
                    "enabled": True
                }
            ]
        }
        rules = RuleImportExporter.import_from_json(json.dumps(json_data))
        assert len(rules) == 1
        assert rules[0].rule_id == "IMPORT_001"

    def test_export_import_roundtrip(self) -> None:
        """Test exporting and reimporting rules."""
        original_rules = [
            CustomRule(
                rule_id="ROUND_001",
                name="Roundtrip Test",
                description="Test roundtrip",
                severity="high",
                resource_types=["AWS::Lambda::Function"],
                conditions={"operator": "exists", "field": "Tags"}
            )
        ]
        json_str = RuleImportExporter.export_to_json(original_rules)
        reimported = RuleImportExporter.import_from_json(json_str)
        assert len(reimported) == 1
        assert reimported[0].rule_id == "ROUND_001"
        assert reimported[0].name == "Roundtrip Test"


class TestRuleValidation:
    """Test rule validation."""

    def test_valid_severity_values(self) -> None:
        """Test valid severity values."""
        for severity in ["critical", "high", "medium", "low"]:
            rule = CustomRule(
                rule_id=f"SEV_{severity.upper()}",
                name="Severity Test",
                description="Test severity",
                severity=severity
            )
            assert rule.severity == severity

    def test_rule_id_required(self) -> None:
        """Test that rule_id is required."""
        with pytest.raises(TypeError):
            CustomRule(  # type: ignore
                name="Missing ID",
                description="No rule ID"
            )

    def test_name_required(self) -> None:
        """Test that name is required."""
        with pytest.raises(TypeError):
            CustomRule(  # type: ignore
                rule_id="TEST",
                description="No name"
            )
