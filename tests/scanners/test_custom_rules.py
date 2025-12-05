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
    RuleValidator,
    get_example_rules,
)
from cloud_optimizer.scanners.base import ScanResult


class TestRuleCondition:
    """Test RuleCondition dataclass."""

    def test_equals_operator(self) -> None:
        """Test equals operator."""
        condition = RuleCondition(
            field="Status",
            operator=RuleOperator.EQUALS,
            value="Active"
        )
        assert condition.evaluate({"Status": "Active"})
        assert not condition.evaluate({"Status": "Inactive"})

    def test_not_equals_operator(self) -> None:
        """Test not equals operator."""
        condition = RuleCondition(
            field="Status",
            operator=RuleOperator.NOT_EQUALS,
            value="Disabled"
        )
        assert condition.evaluate({"Status": "Active"})
        assert not condition.evaluate({"Status": "Disabled"})

    def test_contains_operator(self) -> None:
        """Test contains operator."""
        condition = RuleCondition(
            field="Tags",
            operator=RuleOperator.CONTAINS,
            value="production"
        )
        assert condition.evaluate({"Tags": ["production", "web"]})
        assert not condition.evaluate({"Tags": ["staging", "web"]})

    def test_not_contains_operator(self) -> None:
        """Test not contains operator."""
        condition = RuleCondition(
            field="Tags",
            operator=RuleOperator.NOT_CONTAINS,
            value="deprecated"
        )
        assert condition.evaluate({"Tags": ["production", "web"]})
        assert not condition.evaluate({"Tags": ["deprecated", "web"]})

    def test_matches_operator(self) -> None:
        """Test regex matches operator."""
        condition = RuleCondition(
            field="Name",
            operator=RuleOperator.MATCHES,
            value=r"^prod-.*"
        )
        assert condition.evaluate({"Name": "prod-api-1"})
        assert not condition.evaluate({"Name": "dev-api-1"})

    def test_exists_operator(self) -> None:
        """Test exists operator."""
        condition = RuleCondition(
            field="Encryption",
            operator=RuleOperator.EXISTS,
            value=True
        )
        assert condition.evaluate({"Encryption": {"Enabled": True}})
        assert not condition.evaluate({})

    def test_greater_than_operator(self) -> None:
        """Test greater than operator."""
        condition = RuleCondition(
            field="Size",
            operator=RuleOperator.GREATER_THAN,
            value=100
        )
        assert condition.evaluate({"Size": 150})
        assert not condition.evaluate({"Size": 50})

    def test_less_than_operator(self) -> None:
        """Test less than operator."""
        condition = RuleCondition(
            field="Age",
            operator=RuleOperator.LESS_THAN,
            value=30
        )
        assert condition.evaluate({"Age": 25})
        assert not condition.evaluate({"Age": 35})

    def test_in_operator(self) -> None:
        """Test in operator."""
        condition = RuleCondition(
            field="Region",
            operator=RuleOperator.IN,
            value=["us-east-1", "us-west-2"]
        )
        assert condition.evaluate({"Region": "us-east-1"})
        assert not condition.evaluate({"Region": "eu-west-1"})

    def test_not_in_operator(self) -> None:
        """Test not in operator."""
        condition = RuleCondition(
            field="Environment",
            operator=RuleOperator.NOT_IN,
            value=["dev", "test"]
        )
        assert condition.evaluate({"Environment": "prod"})
        assert not condition.evaluate({"Environment": "dev"})

    def test_nested_field_access(self) -> None:
        """Test accessing nested fields."""
        condition = RuleCondition(
            field="Config.Encryption.Enabled",
            operator=RuleOperator.EQUALS,
            value=True
        )
        assert condition.evaluate({"Config": {"Encryption": {"Enabled": True}}})
        assert not condition.evaluate({"Config": {"Encryption": {"Enabled": False}}})


class TestCustomRule:
    """Test CustomRule dataclass."""

    def test_rule_creation(self) -> None:
        """Test creating a custom rule."""
        rule = CustomRule(
            rule_id="CUSTOM_001",
            name="Test Rule",
            description="A test custom rule",
            severity="high",
            service="s3",
            resource_type="bucket",
            rule_type=RuleType.SECURITY,
            conditions=[
                RuleCondition(
                    field="PublicAccessBlockConfiguration",
                    operator=RuleOperator.EXISTS,
                    value=True
                )
            ],
            recommendation="Enable public access block"
        )

        assert rule.rule_id == "CUSTOM_001"
        assert rule.severity == "high"
        assert len(rule.conditions) == 1

    def test_rule_evaluation_all_conditions(self) -> None:
        """Test rule evaluation with all conditions (AND logic)."""
        rule = CustomRule(
            rule_id="CUSTOM_001",
            name="Test Rule",
            description="Test",
            severity="high",
            service="s3",
            resource_type="bucket",
            rule_type=RuleType.SECURITY,
            conditions=[
                RuleCondition(
                    field="Encrypted",
                    operator=RuleOperator.EQUALS,
                    value=True
                ),
                RuleCondition(
                    field="Versioning",
                    operator=RuleOperator.EQUALS,
                    value="Enabled"
                )
            ],
            match_any=False  # All conditions must match
        )

        # Both conditions pass
        assert rule.evaluate({"Encrypted": True, "Versioning": "Enabled"})
        # One condition fails
        assert not rule.evaluate({"Encrypted": True, "Versioning": "Disabled"})

    def test_rule_evaluation_any_condition(self) -> None:
        """Test rule evaluation with any condition (OR logic)."""
        rule = CustomRule(
            rule_id="CUSTOM_001",
            name="Test Rule",
            description="Test",
            severity="high",
            service="s3",
            resource_type="bucket",
            rule_type=RuleType.SECURITY,
            conditions=[
                RuleCondition(
                    field="Public",
                    operator=RuleOperator.EQUALS,
                    value=True
                ),
                RuleCondition(
                    field="ACL",
                    operator=RuleOperator.EQUALS,
                    value="public-read"
                )
            ],
            match_any=True  # Any condition matching is a failure
        )

        # One condition matches - should flag
        assert rule.evaluate({"Public": True, "ACL": "private"})
        # Neither matches - should pass
        assert not rule.evaluate({"Public": False, "ACL": "private"})


class TestRuleEngine:
    """Test RuleEngine class."""

    @pytest.fixture
    def engine(self) -> RuleEngine:
        """Create rule engine."""
        return RuleEngine()

    @pytest.fixture
    def sample_rule(self) -> CustomRule:
        """Create sample custom rule."""
        return CustomRule(
            rule_id="CUSTOM_001",
            name="S3 Encryption Check",
            description="Ensure S3 buckets are encrypted",
            severity="high",
            service="s3",
            resource_type="bucket",
            rule_type=RuleType.SECURITY,
            conditions=[
                RuleCondition(
                    field="ServerSideEncryptionConfiguration",
                    operator=RuleOperator.EXISTS,
                    value=True
                )
            ],
            recommendation="Enable S3 bucket encryption"
        )

    def test_register_rule(
        self, engine: RuleEngine, sample_rule: CustomRule
    ) -> None:
        """Test registering a rule."""
        engine.register_rule(sample_rule)
        assert sample_rule.rule_id in engine.list_rules()

    def test_unregister_rule(
        self, engine: RuleEngine, sample_rule: CustomRule
    ) -> None:
        """Test unregistering a rule."""
        engine.register_rule(sample_rule)
        engine.unregister_rule(sample_rule.rule_id)
        assert sample_rule.rule_id not in engine.list_rules()

    def test_get_rule(
        self, engine: RuleEngine, sample_rule: CustomRule
    ) -> None:
        """Test getting a rule by ID."""
        engine.register_rule(sample_rule)
        retrieved = engine.get_rule(sample_rule.rule_id)
        assert retrieved == sample_rule

    def test_evaluate_rule(
        self, engine: RuleEngine, sample_rule: CustomRule
    ) -> None:
        """Test evaluating a rule against a resource."""
        engine.register_rule(sample_rule)

        # Resource without encryption - should fail
        resource_no_encryption: Dict[str, Any] = {
            "BucketName": "my-bucket",
            "Arn": "arn:aws:s3:::my-bucket"
        }
        result = engine.evaluate_rule(sample_rule, resource_no_encryption)
        assert result is not None
        assert not result.passed

        # Resource with encryption - should pass
        resource_encrypted: Dict[str, Any] = {
            "BucketName": "my-bucket",
            "Arn": "arn:aws:s3:::my-bucket",
            "ServerSideEncryptionConfiguration": {
                "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
            }
        }
        result = engine.evaluate_rule(sample_rule, resource_encrypted)
        assert result is None or result.passed

    def test_evaluate_all_rules(
        self, engine: RuleEngine, sample_rule: CustomRule
    ) -> None:
        """Test evaluating all rules against resources."""
        engine.register_rule(sample_rule)

        resources: List[Dict[str, Any]] = [
            {"BucketName": "bucket1", "Arn": "arn:aws:s3:::bucket1"},
            {
                "BucketName": "bucket2",
                "Arn": "arn:aws:s3:::bucket2",
                "ServerSideEncryptionConfiguration": {}
            }
        ]

        results = engine.evaluate_all(resources, service="s3")
        assert len(results) >= 1  # At least one failure

    def test_list_rules_by_service(
        self, engine: RuleEngine
    ) -> None:
        """Test listing rules filtered by service."""
        s3_rule = CustomRule(
            rule_id="S3_CUSTOM_001",
            name="S3 Rule",
            description="Test",
            severity="high",
            service="s3",
            resource_type="bucket",
            rule_type=RuleType.SECURITY,
            conditions=[]
        )
        ec2_rule = CustomRule(
            rule_id="EC2_CUSTOM_001",
            name="EC2 Rule",
            description="Test",
            severity="high",
            service="ec2",
            resource_type="instance",
            rule_type=RuleType.SECURITY,
            conditions=[]
        )

        engine.register_rule(s3_rule)
        engine.register_rule(ec2_rule)

        s3_rules = engine.list_rules(service="s3")
        assert "S3_CUSTOM_001" in s3_rules
        assert "EC2_CUSTOM_001" not in s3_rules


class TestRuleValidator:
    """Test RuleValidator class."""

    def test_valid_rule(self) -> None:
        """Test validation of valid rule."""
        rule = CustomRule(
            rule_id="CUSTOM_001",
            name="Valid Rule",
            description="A valid custom rule",
            severity="high",
            service="s3",
            resource_type="bucket",
            rule_type=RuleType.SECURITY,
            conditions=[
                RuleCondition(
                    field="Encrypted",
                    operator=RuleOperator.EQUALS,
                    value=True
                )
            ]
        )

        errors = RuleValidator.validate(rule)
        assert len(errors) == 0

    def test_invalid_rule_id(self) -> None:
        """Test validation catches invalid rule ID."""
        rule = CustomRule(
            rule_id="",  # Empty ID
            name="Invalid Rule",
            description="Test",
            severity="high",
            service="s3",
            resource_type="bucket",
            rule_type=RuleType.SECURITY,
            conditions=[]
        )

        errors = RuleValidator.validate(rule)
        assert any("rule_id" in e.lower() for e in errors)

    def test_invalid_severity(self) -> None:
        """Test validation catches invalid severity."""
        rule = CustomRule(
            rule_id="CUSTOM_001",
            name="Test",
            description="Test",
            severity="invalid",  # Invalid severity
            service="s3",
            resource_type="bucket",
            rule_type=RuleType.SECURITY,
            conditions=[]
        )

        errors = RuleValidator.validate(rule)
        assert any("severity" in e.lower() for e in errors)

    def test_no_conditions(self) -> None:
        """Test validation catches empty conditions."""
        rule = CustomRule(
            rule_id="CUSTOM_001",
            name="Test",
            description="Test",
            severity="high",
            service="s3",
            resource_type="bucket",
            rule_type=RuleType.SECURITY,
            conditions=[]  # No conditions
        )

        errors = RuleValidator.validate(rule)
        assert any("condition" in e.lower() for e in errors)


class TestRuleImportExporter:
    """Test RuleImportExporter class."""

    @pytest.fixture
    def sample_rules(self) -> List[CustomRule]:
        """Create sample rules for export."""
        return [
            CustomRule(
                rule_id="CUSTOM_001",
                name="S3 Encryption",
                description="Check S3 encryption",
                severity="high",
                service="s3",
                resource_type="bucket",
                rule_type=RuleType.SECURITY,
                conditions=[
                    RuleCondition(
                        field="Encrypted",
                        operator=RuleOperator.EQUALS,
                        value=True
                    )
                ]
            ),
            CustomRule(
                rule_id="CUSTOM_002",
                name="EC2 Public IP",
                description="Check for public IPs",
                severity="medium",
                service="ec2",
                resource_type="instance",
                rule_type=RuleType.SECURITY,
                conditions=[
                    RuleCondition(
                        field="PublicIpAddress",
                        operator=RuleOperator.EXISTS,
                        value=False
                    )
                ]
            )
        ]

    def test_export_to_json(self, sample_rules: List[CustomRule]) -> None:
        """Test exporting rules to JSON."""
        json_str = RuleImportExporter.export_to_json(sample_rules)
        data = json.loads(json_str)

        assert "rules" in data
        assert len(data["rules"]) == 2
        assert data["rules"][0]["rule_id"] == "CUSTOM_001"

    def test_import_from_json(self, sample_rules: List[CustomRule]) -> None:
        """Test importing rules from JSON."""
        json_str = RuleImportExporter.export_to_json(sample_rules)
        imported = RuleImportExporter.import_from_json(json_str)

        assert len(imported) == 2
        assert imported[0].rule_id == "CUSTOM_001"
        assert imported[1].rule_id == "CUSTOM_002"

    def test_export_to_yaml(self, sample_rules: List[CustomRule]) -> None:
        """Test exporting rules to YAML."""
        yaml_str = RuleImportExporter.export_to_yaml(sample_rules)

        assert "rules:" in yaml_str
        assert "CUSTOM_001" in yaml_str
        assert "CUSTOM_002" in yaml_str

    def test_import_from_yaml(self, sample_rules: List[CustomRule]) -> None:
        """Test importing rules from YAML."""
        yaml_str = RuleImportExporter.export_to_yaml(sample_rules)
        imported = RuleImportExporter.import_from_yaml(yaml_str)

        assert len(imported) == 2
        assert imported[0].rule_id == "CUSTOM_001"

    def test_export_to_file(self, sample_rules: List[CustomRule]) -> None:
        """Test exporting rules to file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            RuleImportExporter.export_to_file(sample_rules, f.name)
            f.flush()

            with open(f.name, "r") as rf:
                content = rf.read()
                assert "CUSTOM_001" in content

    def test_import_from_file(self, sample_rules: List[CustomRule]) -> None:
        """Test importing rules from file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json_str = RuleImportExporter.export_to_json(sample_rules)
            f.write(json_str)
            f.flush()

            imported = RuleImportExporter.import_from_file(f.name)
            assert len(imported) == 2

    def test_roundtrip_json(self, sample_rules: List[CustomRule]) -> None:
        """Test JSON export/import roundtrip preserves data."""
        exported = RuleImportExporter.export_to_json(sample_rules)
        imported = RuleImportExporter.import_from_json(exported)

        assert len(imported) == len(sample_rules)
        for orig, imp in zip(sample_rules, imported):
            assert orig.rule_id == imp.rule_id
            assert orig.name == imp.name
            assert orig.severity == imp.severity
            assert len(orig.conditions) == len(imp.conditions)


class TestRulePackage:
    """Test RulePackage dataclass."""

    def test_package_creation(self) -> None:
        """Test creating a rule package."""
        rules = [
            CustomRule(
                rule_id="PKG_001",
                name="Package Rule",
                description="Test",
                severity="high",
                service="s3",
                resource_type="bucket",
                rule_type=RuleType.SECURITY,
                conditions=[]
            )
        ]

        package = RulePackage(
            name="Security Pack",
            version="1.0.0",
            description="Security rules package",
            author="Cloud Optimizer",
            rules=rules
        )

        assert package.name == "Security Pack"
        assert package.version == "1.0.0"
        assert len(package.rules) == 1

    def test_package_to_dict(self) -> None:
        """Test converting package to dictionary."""
        rules = [
            CustomRule(
                rule_id="PKG_001",
                name="Test",
                description="Test",
                severity="high",
                service="s3",
                resource_type="bucket",
                rule_type=RuleType.SECURITY,
                conditions=[]
            )
        ]

        package = RulePackage(
            name="Test Pack",
            version="1.0.0",
            description="Test",
            author="Test",
            rules=rules
        )

        data = package.to_dict()
        assert data["name"] == "Test Pack"
        assert data["version"] == "1.0.0"
        assert "rules" in data


class TestExampleRules:
    """Test example rules function."""

    def test_example_rules_returned(self) -> None:
        """Test that example rules are returned."""
        rules = get_example_rules()
        assert len(rules) > 0

    def test_example_rules_valid(self) -> None:
        """Test that example rules pass validation."""
        rules = get_example_rules()
        for rule in rules:
            errors = RuleValidator.validate(rule)
            assert len(errors) == 0, f"Rule {rule.rule_id} has errors: {errors}"

    def test_example_rules_have_required_fields(self) -> None:
        """Test that example rules have all required fields."""
        rules = get_example_rules()
        for rule in rules:
            assert rule.rule_id
            assert rule.name
            assert rule.description
            assert rule.severity in ["critical", "high", "medium", "low"]
            assert rule.service
            assert rule.resource_type
