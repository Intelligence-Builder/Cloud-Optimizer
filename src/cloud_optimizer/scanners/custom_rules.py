"""Custom Rule Engine for User-Defined Checks.

Issue #150: 9.3.1 Custom rule engine for user-defined checks
Issue #151: 9.3.2 Rule import/export functionality

Implements a flexible rule engine allowing users to define custom security checks
using a declarative syntax and provides import/export functionality for rule sharing.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

import yaml

from cloud_optimizer.scanners.base import ScannerRule, ScanResult

logger = logging.getLogger(__name__)


class RuleOperator(str, Enum):
    """Supported operators for rule conditions."""

    # Comparison operators
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    MATCHES = "matches"  # Regex match

    # Existence operators
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    IS_EMPTY = "is_empty"
    NOT_EMPTY = "not_empty"

    # Collection operators
    IN = "in"
    NOT_IN = "not_in"
    ALL = "all"
    ANY = "any"

    # Logical operators
    AND = "and"
    OR = "or"
    NOT = "not"


class RuleType(str, Enum):
    """Types of custom rules."""

    CONFIGURATION = "configuration"  # Check resource attributes
    TAG = "tag"  # Enforce tagging standards
    NAMING = "naming"  # Enforce naming conventions
    RELATIONSHIP = "relationship"  # Check resource relationships
    COST = "cost"  # Enforce cost thresholds


@dataclass
class RuleCondition:
    """A single condition in a rule.

    Attributes:
        field: JSONPath-like field to check (e.g., "Tags.Environment")
        operator: Comparison operator
        value: Expected value (optional for existence checks)
        key: Key for map lookups (e.g., tag key)
    """

    field: str
    operator: RuleOperator
    value: Any = None
    key: Optional[str] = None


@dataclass
class CustomRule:
    """Custom security rule definition.

    Attributes:
        rule_id: Unique rule identifier
        name: Human-readable rule name
        description: Detailed description
        severity: Rule severity (critical, high, medium, low)
        enabled: Whether rule is active
        resource_types: List of AWS resource types this rule applies to
        rule_type: Type of rule
        conditions: Rule conditions (nested for AND/OR)
        remediation: Remediation guidance
        compliance_frameworks: Related compliance frameworks
        metadata: Additional metadata
        version: Rule version
        author: Rule author
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    rule_id: str
    name: str
    description: str
    severity: str = "medium"
    enabled: bool = True
    resource_types: List[str] = field(default_factory=list)
    rule_type: RuleType = RuleType.CONFIGURATION
    conditions: Dict[str, Any] = field(default_factory=dict)
    remediation: str = ""
    compliance_frameworks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    author: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Initialize timestamps if not set."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_scanner_rule(self) -> ScannerRule:
        """Convert to ScannerRule for consistency.

        Returns:
            ScannerRule representation
        """
        return ScannerRule(
            rule_id=self.rule_id,
            title=self.name,
            description=self.description,
            severity=self.severity,
            service="Custom",
            resource_type=self.resource_types[0] if self.resource_types else "AWS::*",
            recommendation=self.remediation,
            compliance_frameworks=self.compliance_frameworks,
        )


@dataclass
class RulePackage:
    """Collection of related rules.

    Attributes:
        name: Package name
        description: Package description
        author: Package author
        version: Package version
        rules: List of rules in the package
        dependencies: Other package dependencies
        metadata: Additional metadata
    """

    name: str
    description: str
    author: str = ""
    version: str = "1.0"
    rules: List[CustomRule] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RuleValidator:
    """Validates custom rule definitions."""

    VALID_SEVERITIES = {"critical", "high", "medium", "low"}
    VALID_OPERATORS = {op.value for op in RuleOperator}

    @classmethod
    def validate_rule(cls, rule: CustomRule) -> List[str]:
        """Validate a custom rule.

        Args:
            rule: Rule to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors: List[str] = []

        # Validate rule_id
        if not rule.rule_id or not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", rule.rule_id):
            errors.append(
                "rule_id must start with letter and contain only "
                "alphanumeric, underscore, hyphen"
            )

        # Validate name
        if not rule.name or len(rule.name) < 3:
            errors.append("name must be at least 3 characters")

        # Validate severity
        if rule.severity.lower() not in cls.VALID_SEVERITIES:
            errors.append(f"severity must be one of: {cls.VALID_SEVERITIES}")

        # Validate resource_types
        if not rule.resource_types:
            errors.append("at least one resource_type is required")

        # Validate conditions
        if not rule.conditions:
            errors.append("at least one condition is required")
        else:
            condition_errors = cls._validate_conditions(rule.conditions)
            errors.extend(condition_errors)

        return errors

    @classmethod
    def _validate_conditions(
        cls, conditions: Dict[str, Any], depth: int = 0
    ) -> List[str]:
        """Validate rule conditions recursively.

        Args:
            conditions: Conditions to validate
            depth: Current nesting depth

        Returns:
            List of validation errors
        """
        errors: List[str] = []

        if depth > 5:
            errors.append("conditions nested too deeply (max 5 levels)")
            return errors

        operator = conditions.get("operator", "").lower()
        if not operator:
            errors.append("condition must have an operator")
            return errors

        if operator in {"and", "or"}:
            checks = conditions.get("checks", [])
            if not checks:
                errors.append(f"{operator} condition must have checks")
            for i, check in enumerate(checks):
                if isinstance(check, dict):
                    errors.extend(cls._validate_conditions(check, depth + 1))
                else:
                    errors.append(f"check {i} must be a dictionary")
        else:
            # Leaf condition
            if operator not in cls.VALID_OPERATORS:
                errors.append(f"invalid operator: {operator}")

            if "field" not in conditions:
                errors.append("condition must have a field")

        return errors


class RuleEngine:
    """Engine for evaluating custom rules against resources."""

    def __init__(self) -> None:
        """Initialize rule engine."""
        self._rules: Dict[str, CustomRule] = {}
        self._operator_functions: Dict[str, Callable[..., bool]] = {
            RuleOperator.EQUALS.value: lambda a, b: a == b,
            RuleOperator.NOT_EQUALS.value: lambda a, b: a != b,
            RuleOperator.GREATER_THAN.value: lambda a, b: float(a) > float(b),
            RuleOperator.LESS_THAN.value: lambda a, b: float(a) < float(b),
            RuleOperator.GREATER_EQUAL.value: lambda a, b: float(a) >= float(b),
            RuleOperator.LESS_EQUAL.value: lambda a, b: float(a) <= float(b),
            RuleOperator.CONTAINS.value: lambda a, b: b in str(a),
            RuleOperator.NOT_CONTAINS.value: lambda a, b: b not in str(a),
            RuleOperator.MATCHES.value: lambda a, b: bool(re.search(b, str(a))),
            RuleOperator.EXISTS.value: lambda a, _: a is not None,
            RuleOperator.NOT_EXISTS.value: lambda a, _: a is None,
            RuleOperator.IS_EMPTY.value: lambda a, _: not a,
            RuleOperator.NOT_EMPTY.value: lambda a, _: bool(a),
            RuleOperator.IN.value: lambda a, b: a in b,
            RuleOperator.NOT_IN.value: lambda a, b: a not in b,
        }

    def register_rule(self, rule: CustomRule) -> bool:
        """Register a custom rule.

        Args:
            rule: Rule to register

        Returns:
            True if registered successfully
        """
        errors = RuleValidator.validate_rule(rule)
        if errors:
            logger.error(f"Rule validation failed for {rule.rule_id}: {errors}")
            return False

        self._rules[rule.rule_id] = rule
        logger.info(f"Registered custom rule: {rule.rule_id}")
        return True

    def unregister_rule(self, rule_id: str) -> bool:
        """Unregister a rule.

        Args:
            rule_id: ID of rule to remove

        Returns:
            True if removed
        """
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[CustomRule]:
        """Get a rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Rule if found
        """
        return self._rules.get(rule_id)

    def list_rules(
        self,
        enabled_only: bool = True,
        resource_type: Optional[str] = None,
    ) -> List[CustomRule]:
        """List registered rules.

        Args:
            enabled_only: Only return enabled rules
            resource_type: Filter by resource type

        Returns:
            List of matching rules
        """
        rules = list(self._rules.values())

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        if resource_type:
            rules = [r for r in rules if resource_type in r.resource_types]

        return rules

    def evaluate_rule(
        self,
        rule: CustomRule,
        resource: Dict[str, Any],
    ) -> Optional[ScanResult]:
        """Evaluate a rule against a resource.

        Args:
            rule: Rule to evaluate
            resource: Resource data to check

        Returns:
            ScanResult if rule violated, None if passed
        """
        if not rule.enabled:
            return None

        try:
            passed = self._evaluate_conditions(rule.conditions, resource)

            if not passed:
                return ScanResult(
                    rule_id=rule.rule_id,
                    passed=False,
                    resource_id=resource.get("ResourceId", resource.get("Arn", "unknown")),
                    resource_arn=resource.get("Arn"),
                    region=resource.get("Region", "unknown"),
                    evidence={
                        "rule_name": rule.name,
                        "severity": rule.severity,
                        "rule_type": rule.rule_type.value,
                        "remediation": rule.remediation,
                    },
                )

        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")

        return None

    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        resource: Dict[str, Any],
    ) -> bool:
        """Evaluate conditions against resource.

        Args:
            conditions: Conditions to evaluate
            resource: Resource data

        Returns:
            True if conditions pass
        """
        operator = conditions.get("operator", "").lower()

        if operator == "and":
            checks = conditions.get("checks", [])
            return all(self._evaluate_conditions(c, resource) for c in checks)

        elif operator == "or":
            checks = conditions.get("checks", [])
            return any(self._evaluate_conditions(c, resource) for c in checks)

        elif operator == "not":
            inner = conditions.get("condition", conditions.get("checks", [{}])[0])
            return not self._evaluate_conditions(inner, resource)

        else:
            # Leaf condition
            field_path = conditions.get("field", "")
            value = conditions.get("value")
            key = conditions.get("key")

            # Get field value from resource
            actual_value = self._get_field_value(resource, field_path, key)

            # Apply operator
            op_func = self._operator_functions.get(operator)
            if op_func:
                try:
                    return op_func(actual_value, value)
                except (TypeError, ValueError):
                    return False

            return False

    def _get_field_value(
        self,
        data: Dict[str, Any],
        field_path: str,
        key: Optional[str] = None,
    ) -> Any:
        """Get value from nested dictionary using dot notation.

        Args:
            data: Dictionary to search
            field_path: Dot-separated path (e.g., "Tags.Environment")
            key: Optional key for tag-like structures

        Returns:
            Value at path or None if not found
        """
        parts = field_path.split(".")
        current = data

        for part in parts:
            if current is None:
                return None

            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                # Handle list of dicts (like Tags)
                if key:
                    for item in current:
                        if isinstance(item, dict) and item.get("Key") == key:
                            return item.get("Value")
                    return None
                else:
                    try:
                        current = current[int(part)]
                    except (ValueError, IndexError):
                        return None
            else:
                return None

        return current


class RuleImportExporter:
    """Handles import/export of custom rules.

    Issue #151: 9.3.2 Rule import/export functionality
    """

    @staticmethod
    def export_rule_to_yaml(rule: CustomRule) -> str:
        """Export a single rule to YAML.

        Args:
            rule: Rule to export

        Returns:
            YAML string
        """
        rule_dict = {
            "rule": {
                "id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity,
                "enabled": rule.enabled,
                "resource_types": rule.resource_types,
                "rule_type": rule.rule_type.value,
                "conditions": rule.conditions,
                "remediation": rule.remediation,
                "compliance_frameworks": rule.compliance_frameworks,
                "metadata": {
                    "author": rule.author,
                    "version": rule.version,
                    "created_at": rule.created_at.isoformat() if rule.created_at else None,
                    **rule.metadata,
                },
            }
        }
        return yaml.dump(rule_dict, default_flow_style=False, sort_keys=False)

    @staticmethod
    def export_rules_to_yaml(rules: List[CustomRule]) -> str:
        """Export multiple rules to YAML.

        Args:
            rules: Rules to export

        Returns:
            YAML string
        """
        rules_dict = {
            "rules": [
                {
                    "id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "severity": r.severity,
                    "enabled": r.enabled,
                    "resource_types": r.resource_types,
                    "rule_type": r.rule_type.value,
                    "conditions": r.conditions,
                    "remediation": r.remediation,
                    "compliance_frameworks": r.compliance_frameworks,
                    "metadata": {
                        "author": r.author,
                        "version": r.version,
                        **r.metadata,
                    },
                }
                for r in rules
            ]
        }
        return yaml.dump(rules_dict, default_flow_style=False, sort_keys=False)

    @staticmethod
    def export_package_to_yaml(package: RulePackage) -> str:
        """Export a rule package to YAML.

        Args:
            package: Package to export

        Returns:
            YAML string
        """
        package_dict = {
            "rule_package": {
                "name": package.name,
                "description": package.description,
                "author": package.author,
                "version": package.version,
                "dependencies": package.dependencies,
                "metadata": package.metadata,
                "rules": [
                    {
                        "id": r.rule_id,
                        "name": r.name,
                        "description": r.description,
                        "severity": r.severity,
                        "enabled": r.enabled,
                        "resource_types": r.resource_types,
                        "rule_type": r.rule_type.value,
                        "conditions": r.conditions,
                        "remediation": r.remediation,
                        "compliance_frameworks": r.compliance_frameworks,
                    }
                    for r in package.rules
                ],
            }
        }
        return yaml.dump(package_dict, default_flow_style=False, sort_keys=False)

    @staticmethod
    def import_rule_from_yaml(yaml_str: str) -> Optional[CustomRule]:
        """Import a rule from YAML.

        Args:
            yaml_str: YAML string

        Returns:
            CustomRule or None on error
        """
        try:
            data = yaml.safe_load(yaml_str)
            rule_data = data.get("rule", {})

            return CustomRule(
                rule_id=rule_data["id"],
                name=rule_data["name"],
                description=rule_data.get("description", ""),
                severity=rule_data.get("severity", "medium"),
                enabled=rule_data.get("enabled", True),
                resource_types=rule_data.get("resource_types", []),
                rule_type=RuleType(rule_data.get("rule_type", "configuration")),
                conditions=rule_data.get("conditions", {}),
                remediation=rule_data.get("remediation", ""),
                compliance_frameworks=rule_data.get("compliance_frameworks", []),
                metadata=rule_data.get("metadata", {}),
                author=rule_data.get("metadata", {}).get("author", ""),
                version=rule_data.get("metadata", {}).get("version", "1.0"),
            )

        except Exception as e:
            logger.error(f"Failed to import rule from YAML: {e}")
            return None

    @staticmethod
    def import_rules_from_yaml(yaml_str: str) -> List[CustomRule]:
        """Import multiple rules from YAML.

        Args:
            yaml_str: YAML string

        Returns:
            List of CustomRules
        """
        rules: List[CustomRule] = []
        try:
            data = yaml.safe_load(yaml_str)
            rules_data = data.get("rules", [])

            for rule_data in rules_data:
                rule = CustomRule(
                    rule_id=rule_data["id"],
                    name=rule_data["name"],
                    description=rule_data.get("description", ""),
                    severity=rule_data.get("severity", "medium"),
                    enabled=rule_data.get("enabled", True),
                    resource_types=rule_data.get("resource_types", []),
                    rule_type=RuleType(rule_data.get("rule_type", "configuration")),
                    conditions=rule_data.get("conditions", {}),
                    remediation=rule_data.get("remediation", ""),
                    compliance_frameworks=rule_data.get("compliance_frameworks", []),
                    metadata=rule_data.get("metadata", {}),
                    author=rule_data.get("metadata", {}).get("author", ""),
                    version=rule_data.get("metadata", {}).get("version", "1.0"),
                )
                rules.append(rule)

        except Exception as e:
            logger.error(f"Failed to import rules from YAML: {e}")

        return rules

    @staticmethod
    def import_package_from_yaml(yaml_str: str) -> Optional[RulePackage]:
        """Import a rule package from YAML.

        Args:
            yaml_str: YAML string

        Returns:
            RulePackage or None on error
        """
        try:
            data = yaml.safe_load(yaml_str)
            pkg_data = data.get("rule_package", {})

            rules: List[CustomRule] = []
            for rule_data in pkg_data.get("rules", []):
                rule = CustomRule(
                    rule_id=rule_data["id"],
                    name=rule_data["name"],
                    description=rule_data.get("description", ""),
                    severity=rule_data.get("severity", "medium"),
                    enabled=rule_data.get("enabled", True),
                    resource_types=rule_data.get("resource_types", []),
                    rule_type=RuleType(rule_data.get("rule_type", "configuration")),
                    conditions=rule_data.get("conditions", {}),
                    remediation=rule_data.get("remediation", ""),
                    compliance_frameworks=rule_data.get("compliance_frameworks", []),
                )
                rules.append(rule)

            return RulePackage(
                name=pkg_data["name"],
                description=pkg_data.get("description", ""),
                author=pkg_data.get("author", ""),
                version=pkg_data.get("version", "1.0"),
                rules=rules,
                dependencies=pkg_data.get("dependencies", []),
                metadata=pkg_data.get("metadata", {}),
            )

        except Exception as e:
            logger.error(f"Failed to import package from YAML: {e}")
            return None

    @staticmethod
    def export_to_json(rules: List[CustomRule]) -> str:
        """Export rules to JSON format.

        Args:
            rules: Rules to export

        Returns:
            JSON string
        """
        rules_list = [
            {
                "id": r.rule_id,
                "name": r.name,
                "description": r.description,
                "severity": r.severity,
                "enabled": r.enabled,
                "resource_types": r.resource_types,
                "rule_type": r.rule_type.value,
                "conditions": r.conditions,
                "remediation": r.remediation,
                "compliance_frameworks": r.compliance_frameworks,
                "metadata": {
                    "author": r.author,
                    "version": r.version,
                },
            }
            for r in rules
        ]
        return json.dumps({"rules": rules_list}, indent=2)

    @staticmethod
    def import_from_json(json_str: str) -> List[CustomRule]:
        """Import rules from JSON format.

        Args:
            json_str: JSON string

        Returns:
            List of CustomRules
        """
        rules: List[CustomRule] = []
        try:
            data = json.loads(json_str)
            for rule_data in data.get("rules", []):
                rule = CustomRule(
                    rule_id=rule_data["id"],
                    name=rule_data["name"],
                    description=rule_data.get("description", ""),
                    severity=rule_data.get("severity", "medium"),
                    enabled=rule_data.get("enabled", True),
                    resource_types=rule_data.get("resource_types", []),
                    rule_type=RuleType(rule_data.get("rule_type", "configuration")),
                    conditions=rule_data.get("conditions", {}),
                    remediation=rule_data.get("remediation", ""),
                    compliance_frameworks=rule_data.get("compliance_frameworks", []),
                    author=rule_data.get("metadata", {}).get("author", ""),
                    version=rule_data.get("metadata", {}).get("version", "1.0"),
                )
                rules.append(rule)

        except Exception as e:
            logger.error(f"Failed to import rules from JSON: {e}")

        return rules


# Example rules
EXAMPLE_RULES_YAML = """
rules:
  - id: custom-tag-001
    name: "Require CostCenter tag on all EC2 instances"
    description: "All EC2 instances must have a CostCenter tag for cost allocation"
    severity: medium
    enabled: true
    resource_types:
      - AWS::EC2::Instance
    rule_type: tag
    conditions:
      operator: and
      checks:
        - field: Tags
          operator: contains
          key: CostCenter
        - field: Tags.CostCenter
          operator: not_empty
    remediation: "Add CostCenter tag to EC2 instance with appropriate cost center code"
    compliance_frameworks:
      - custom

  - id: custom-naming-001
    name: "EC2 instance naming convention"
    description: "EC2 instances must follow naming convention: env-app-purpose-number"
    severity: low
    enabled: true
    resource_types:
      - AWS::EC2::Instance
    rule_type: naming
    conditions:
      operator: and
      checks:
        - field: Tags.Name
          operator: matches
          value: "^(prod|staging|dev)-[a-z]+-[a-z]+-[0-9]+$"
    remediation: "Rename instance following pattern: env-app-purpose-number (e.g., prod-api-web-001)"
    compliance_frameworks:
      - custom

  - id: custom-config-001
    name: "S3 bucket versioning enabled"
    description: "S3 buckets must have versioning enabled for data protection"
    severity: high
    enabled: true
    resource_types:
      - AWS::S3::Bucket
    rule_type: configuration
    conditions:
      operator: and
      checks:
        - field: Versioning.Status
          operator: equals
          value: "Enabled"
    remediation: "Enable versioning on the S3 bucket"
    compliance_frameworks:
      - SOC2
      - HIPAA
"""


def get_example_rules() -> List[CustomRule]:
    """Get example custom rules.

    Returns:
        List of example CustomRules
    """
    return RuleImportExporter.import_rules_from_yaml(EXAMPLE_RULES_YAML)
