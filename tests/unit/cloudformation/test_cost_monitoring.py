"""Unit tests for Cost Monitoring CloudFormation template.

Issue #169: Cost monitoring and budgets.
Tests for cost-monitoring.yaml template structure and configuration.
"""

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


def get_cfn_loader() -> type:
    """Create a YAML loader that handles CloudFormation intrinsic functions."""

    class CloudFormationLoader(yaml.SafeLoader):
        pass

    cfn_tags = [
        "!Ref", "!Sub", "!GetAtt", "!If", "!Not", "!Equals",
        "!And", "!Or", "!Condition", "!Select", "!Split",
        "!Join", "!FindInMap", "!ImportValue", "!GetAZs",
        "!Cidr", "!Base64",
    ]

    def generic_constructor(
        loader: yaml.Loader, tag_suffix: str, node: yaml.Node
    ) -> Dict[str, Any]:
        if isinstance(node, yaml.ScalarNode):
            return {f"Fn::{tag_suffix}": loader.construct_scalar(node)}
        elif isinstance(node, yaml.SequenceNode):
            return {f"Fn::{tag_suffix}": loader.construct_sequence(node)}
        elif isinstance(node, yaml.MappingNode):
            return {f"Fn::{tag_suffix}": loader.construct_mapping(node)}
        return {}

    for tag in cfn_tags:
        tag_name = tag[1:]
        CloudFormationLoader.add_constructor(
            tag,
            lambda loader, node, name=tag_name: generic_constructor(loader, name, node),
        )

    return CloudFormationLoader


def load_cfn_template(path: Path) -> Dict[str, Any]:
    """Load a CloudFormation template with intrinsic function support."""
    with open(path, "r") as f:
        return yaml.load(f, Loader=get_cfn_loader())


class TestCostMonitoringTemplate:
    """Test Cost Monitoring CloudFormation template structure."""

    @pytest.fixture
    def template_path(self) -> Path:
        """Get path to cost monitoring template."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "cost-monitoring.yaml"
        )

    @pytest.fixture
    def template(self, template_path: Path) -> Dict[str, Any]:
        """Load and parse the CloudFormation template."""
        return load_cfn_template(template_path)

    def test_template_file_exists(self, template_path: Path) -> None:
        """Test that cost monitoring template file exists."""
        assert template_path.exists(), "Cost monitoring template should exist"

    def test_template_version(self, template: Dict[str, Any]) -> None:
        """Test template has valid AWSTemplateFormatVersion."""
        assert template["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_template_has_description(self, template: Dict[str, Any]) -> None:
        """Test template has description."""
        assert "Description" in template
        assert "Cost" in template["Description"]

    def test_required_parameters_exist(self, template: Dict[str, Any]) -> None:
        """Test all required parameters are defined."""
        params = template.get("Parameters", {})
        required_params = [
            "Environment",
            "ProjectName",
            "MonthlyBudgetAmount",
            "AlertEmail",
            "CostAnomalyThreshold",
        ]
        for param in required_params:
            assert param in params, f"Missing required parameter: {param}"

    def test_environment_parameter(self, template: Dict[str, Any]) -> None:
        """Test Environment parameter configuration."""
        env_param = template["Parameters"]["Environment"]
        assert env_param["Type"] == "String"
        assert "AllowedValues" in env_param
        allowed = env_param["AllowedValues"]
        assert "production" in allowed
        assert "staging" in allowed
        assert "development" in allowed

    def test_monthly_budget_amount_parameter(self, template: Dict[str, Any]) -> None:
        """Test MonthlyBudgetAmount parameter configuration."""
        param = template["Parameters"]["MonthlyBudgetAmount"]
        assert param["Type"] == "Number"
        assert param["Default"] == 1000

    def test_alert_email_parameter(self, template: Dict[str, Any]) -> None:
        """Test AlertEmail parameter configuration."""
        param = template["Parameters"]["AlertEmail"]
        assert param["Type"] == "String"
        assert "AllowedPattern" in param


class TestCostMonitoringResources:
    """Test cost monitoring resources are properly defined."""

    @pytest.fixture
    def template_path(self) -> Path:
        """Get path to cost monitoring template."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "cost-monitoring.yaml"
        )

    @pytest.fixture
    def template(self, template_path: Path) -> Dict[str, Any]:
        """Load and parse the CloudFormation template."""
        return load_cfn_template(template_path)

    @pytest.fixture
    def resources(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Get resources from template."""
        return template.get("Resources", {})

    def test_sns_topic_exists(self, resources: Dict[str, Any]) -> None:
        """Test SNS topic for budget alerts is defined."""
        assert "BudgetAlertTopic" in resources
        topic = resources["BudgetAlertTopic"]
        assert topic["Type"] == "AWS::SNS::Topic"

    def test_sns_subscription_exists(self, resources: Dict[str, Any]) -> None:
        """Test SNS email subscription is defined."""
        assert "BudgetAlertEmailSubscription" in resources
        sub = resources["BudgetAlertEmailSubscription"]
        assert sub["Type"] == "AWS::SNS::Subscription"
        assert sub["Properties"]["Protocol"] == "email"

    def test_monthly_budget_exists(self, resources: Dict[str, Any]) -> None:
        """Test monthly budget is defined."""
        assert "MonthlyBudget" in resources
        budget = resources["MonthlyBudget"]
        assert budget["Type"] == "AWS::Budgets::Budget"
        props = budget["Properties"]["Budget"]
        assert props["BudgetType"] == "COST"
        assert props["TimeUnit"] == "MONTHLY"

    def test_monthly_budget_has_notifications(self, resources: Dict[str, Any]) -> None:
        """Test monthly budget has notification thresholds."""
        budget = resources["MonthlyBudget"]
        notifications = budget["Properties"]["NotificationsWithSubscribers"]
        # Should have multiple threshold notifications
        assert len(notifications) >= 4
        thresholds = [n["Notification"]["Threshold"] for n in notifications]
        assert 50 in thresholds  # 50% warning
        assert 80 in thresholds  # 80% warning
        assert 100 in thresholds  # 100% critical

    def test_daily_budget_exists(self, resources: Dict[str, Any]) -> None:
        """Test daily budget with auto-adjustment is defined."""
        assert "DailyBudget" in resources
        budget = resources["DailyBudget"]
        assert budget["Type"] == "AWS::Budgets::Budget"
        props = budget["Properties"]["Budget"]
        assert props["TimeUnit"] == "DAILY"
        # Auto-adjusting budget
        assert "AutoAdjustData" in props
        assert props["AutoAdjustData"]["AutoAdjustType"] == "HISTORICAL"

    def test_cost_anomaly_monitor_exists(self, resources: Dict[str, Any]) -> None:
        """Test cost anomaly monitor is defined."""
        assert "CostAnomalyMonitor" in resources
        monitor = resources["CostAnomalyMonitor"]
        assert monitor["Type"] == "AWS::CE::AnomalyMonitor"
        assert monitor["Properties"]["MonitorType"] == "DIMENSIONAL"

    def test_cost_anomaly_subscription_exists(self, resources: Dict[str, Any]) -> None:
        """Test cost anomaly subscription is defined."""
        assert "CostAnomalySubscription" in resources
        sub = resources["CostAnomalySubscription"]
        assert sub["Type"] == "AWS::CE::AnomalySubscription"
        assert sub["Properties"]["Frequency"] == "DAILY"

    def test_cost_explorer_role_exists(self, resources: Dict[str, Any]) -> None:
        """Test IAM role for Cost Explorer is defined."""
        assert "CostExplorerRole" in resources
        role = resources["CostExplorerRole"]
        assert role["Type"] == "AWS::IAM::Role"
        # Check it has Cost Explorer permissions
        policies = role["Properties"]["Policies"]
        assert len(policies) > 0
        policy_doc = policies[0]["PolicyDocument"]
        statements = policy_doc["Statement"]
        ce_actions = []
        for stmt in statements:
            if isinstance(stmt["Action"], list):
                ce_actions.extend([a for a in stmt["Action"] if a.startswith("ce:")])
        assert len(ce_actions) > 0, "Should have Cost Explorer permissions"

    def test_cost_report_function_exists(self, resources: Dict[str, Any]) -> None:
        """Test Lambda function for cost reporting is defined."""
        assert "CostReportFunction" in resources
        fn = resources["CostReportFunction"]
        assert fn["Type"] == "AWS::Lambda::Function"
        assert fn["Properties"]["Runtime"] == "python3.11"

    def test_weekly_report_rule_exists(self, resources: Dict[str, Any]) -> None:
        """Test EventBridge rule for weekly reports is defined."""
        assert "WeeklyCostReportRule" in resources
        rule = resources["WeeklyCostReportRule"]
        assert rule["Type"] == "AWS::Events::Rule"
        assert "ScheduleExpression" in rule["Properties"]


class TestCostMonitoringOutputs:
    """Test cost monitoring template outputs."""

    @pytest.fixture
    def template_path(self) -> Path:
        """Get path to cost monitoring template."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "cost-monitoring.yaml"
        )

    @pytest.fixture
    def template(self, template_path: Path) -> Dict[str, Any]:
        """Load and parse the CloudFormation template."""
        return load_cfn_template(template_path)

    @pytest.fixture
    def outputs(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Get outputs from template."""
        return template.get("Outputs", {})

    def test_budget_alert_topic_output(self, outputs: Dict[str, Any]) -> None:
        """Test BudgetAlertTopicArn output is defined."""
        assert "BudgetAlertTopicArn" in outputs
        output = outputs["BudgetAlertTopicArn"]
        assert "Description" in output
        assert "Export" in output

    def test_cost_explorer_role_output(self, outputs: Dict[str, Any]) -> None:
        """Test CostExplorerRoleArn output is defined."""
        assert "CostExplorerRoleArn" in outputs
        output = outputs["CostExplorerRoleArn"]
        assert "Export" in output

    def test_anomaly_monitor_output(self, outputs: Dict[str, Any]) -> None:
        """Test CostAnomalyMonitorArn output is defined."""
        assert "CostAnomalyMonitorArn" in outputs
        output = outputs["CostAnomalyMonitorArn"]
        assert "Export" in output

    def test_cost_report_function_output(self, outputs: Dict[str, Any]) -> None:
        """Test CostReportFunctionArn output is defined."""
        assert "CostReportFunctionArn" in outputs


class TestCostMonitoringBestPractices:
    """Test cost monitoring template follows AWS best practices."""

    @pytest.fixture
    def template_path(self) -> Path:
        """Get path to cost monitoring template."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "cost-monitoring.yaml"
        )

    @pytest.fixture
    def template(self, template_path: Path) -> Dict[str, Any]:
        """Load and parse the CloudFormation template."""
        return load_cfn_template(template_path)

    @pytest.fixture
    def resources(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Get resources from template."""
        return template.get("Resources", {})

    def test_sns_topic_has_tags(self, resources: Dict[str, Any]) -> None:
        """Test SNS topic has proper tagging."""
        topic = resources["BudgetAlertTopic"]
        assert "Tags" in topic["Properties"]
        tags = topic["Properties"]["Tags"]
        tag_keys = [t["Key"] for t in tags]
        assert "Project" in tag_keys
        assert "Environment" in tag_keys

    def test_lambda_has_tags(self, resources: Dict[str, Any]) -> None:
        """Test Lambda function has proper tagging."""
        fn = resources["CostReportFunction"]
        assert "Tags" in fn["Properties"]

    def test_iam_role_has_tags(self, resources: Dict[str, Any]) -> None:
        """Test IAM role has proper tagging."""
        role = resources["CostExplorerRole"]
        assert "Tags" in role["Properties"]

    def test_lambda_has_reasonable_timeout(self, resources: Dict[str, Any]) -> None:
        """Test Lambda function has reasonable timeout."""
        fn = resources["CostReportFunction"]
        timeout = fn["Properties"]["Timeout"]
        assert timeout <= 300, "Lambda timeout should be reasonable"

    def test_budget_includes_forecasted_alert(self, resources: Dict[str, Any]) -> None:
        """Test monthly budget includes forecasted alert."""
        budget = resources["MonthlyBudget"]
        notifications = budget["Properties"]["NotificationsWithSubscribers"]
        notification_types = [n["Notification"]["NotificationType"] for n in notifications]
        assert "FORECASTED" in notification_types, "Should have forecasted alert"

    def test_cost_filters_use_tags(self, resources: Dict[str, Any]) -> None:
        """Test budgets use tag-based cost filtering."""
        budget = resources["MonthlyBudget"]
        cost_filters = budget["Properties"]["Budget"].get("CostFilters", {})
        assert "TagKeyValue" in cost_filters, "Should filter costs by tags"
