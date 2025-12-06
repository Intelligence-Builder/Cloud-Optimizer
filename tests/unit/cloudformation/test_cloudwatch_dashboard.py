"""Unit tests for CloudWatch Dashboard CloudFormation template.

Issue #166: Application metrics with CloudWatch Metrics.
Tests for cloudwatch-dashboard.yaml template structure and configuration.
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


class TestCloudWatchDashboardTemplate:
    """Test CloudWatch Dashboard CloudFormation template structure."""

    @pytest.fixture
    def template_path(self) -> Path:
        """Get path to CloudWatch dashboard template."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "cloudwatch-dashboard.yaml"
        )

    @pytest.fixture
    def template(self, template_path: Path) -> Dict[str, Any]:
        """Load and parse the CloudFormation template."""
        return load_cfn_template(template_path)

    def test_template_file_exists(self, template_path: Path) -> None:
        """Test that CloudWatch dashboard template file exists."""
        assert template_path.exists(), "CloudWatch dashboard template should exist"

    def test_template_version(self, template: Dict[str, Any]) -> None:
        """Test template has valid AWSTemplateFormatVersion."""
        assert template["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_template_has_description(self, template: Dict[str, Any]) -> None:
        """Test template has description."""
        assert "Description" in template
        assert "CloudWatch" in template["Description"]

    def test_required_parameters_exist(self, template: Dict[str, Any]) -> None:
        """Test all required parameters are defined."""
        params = template.get("Parameters", {})
        required_params = [
            "EnvironmentName",
            "MetricNamespace",
            "DashboardName",
        ]
        for param in required_params:
            assert param in params, f"Missing required parameter: {param}"

    def test_environment_parameter(self, template: Dict[str, Any]) -> None:
        """Test Environment parameter configuration."""
        env_param = template["Parameters"]["EnvironmentName"]
        assert env_param["Type"] == "String"
        assert "AllowedValues" in env_param
        allowed = env_param["AllowedValues"]
        assert "production" in allowed
        assert "staging" in allowed
        assert "development" in allowed


class TestDashboardResources:
    """Test CloudWatch Dashboard resources."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load CloudWatch dashboard template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "cloudwatch-dashboard.yaml"
        )
        return load_cfn_template(path)

    def test_dashboard_resource_exists(self, template: Dict[str, Any]) -> None:
        """Test CloudWatch dashboard resource is defined."""
        resources = template.get("Resources", {})
        assert "ApplicationDashboard" in resources
        dashboard = resources["ApplicationDashboard"]
        assert dashboard["Type"] == "AWS::CloudWatch::Dashboard"

    def test_sns_topic_exists(self, template: Dict[str, Any]) -> None:
        """Test SNS topic for alarms is defined."""
        resources = template.get("Resources", {})
        assert "AlarmNotificationTopic" in resources
        topic = resources["AlarmNotificationTopic"]
        assert topic["Type"] == "AWS::SNS::Topic"


class TestDashboardAlarms:
    """Test CloudWatch alarm resources."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load CloudWatch dashboard template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "cloudwatch-dashboard.yaml"
        )
        return load_cfn_template(path)

    def test_high_error_rate_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test high error rate alarm is defined."""
        resources = template.get("Resources", {})
        assert "HighErrorRateAlarm" in resources
        alarm = resources["HighErrorRateAlarm"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"

    def test_high_latency_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test high latency alarm is defined."""
        resources = template.get("Resources", {})
        assert "HighLatencyAlarm" in resources
        alarm = resources["HighLatencyAlarm"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"

    def test_critical_findings_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test critical findings alarm is defined."""
        resources = template.get("Resources", {})
        assert "CriticalFindingsAlarm" in resources

    def test_scan_failure_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test scan failure alarm is defined."""
        resources = template.get("Resources", {})
        assert "ScanFailureAlarm" in resources

    def test_database_latency_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test database latency alarm is defined."""
        resources = template.get("Resources", {})
        assert "DatabaseLatencyAlarm" in resources

    def test_alarm_count(self, template: Dict[str, Any]) -> None:
        """Test expected number of alarms."""
        resources = template.get("Resources", {})
        alarms = [
            r for r in resources
            if resources[r]["Type"] == "AWS::CloudWatch::Alarm"
        ]
        assert len(alarms) == 5, "Should have 5 CloudWatch alarms"


class TestDashboardOutputs:
    """Test CloudWatch dashboard template outputs."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load CloudWatch dashboard template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "cloudwatch-dashboard.yaml"
        )
        return load_cfn_template(path)

    def test_outputs_defined(self, template: Dict[str, Any]) -> None:
        """Test template has required outputs."""
        outputs = template.get("Outputs", {})
        required_outputs = [
            "DashboardURL",
            "MetricNamespace",
        ]
        for output in required_outputs:
            assert output in outputs, f"Missing output: {output}"

    def test_dashboard_url_exported(self, template: Dict[str, Any]) -> None:
        """Test dashboard URL is exported."""
        outputs = template["Outputs"]
        assert "Export" in outputs["DashboardURL"]


class TestDashboardConditions:
    """Test CloudWatch dashboard conditional resources."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load CloudWatch dashboard template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "cloudwatch-dashboard.yaml"
        )
        return load_cfn_template(path)

    def test_conditions_defined(self, template: Dict[str, Any]) -> None:
        """Test conditions are defined for optional resources."""
        conditions = template.get("Conditions", {})
        assert "CreateAlarms" in conditions
        assert "HasAlarmEmail" in conditions

    def test_alarm_topic_conditional(self, template: Dict[str, Any]) -> None:
        """Test SNS topic is conditional on CreateAlarms."""
        topic = template["Resources"]["AlarmNotificationTopic"]
        assert topic.get("Condition") == "CreateAlarms"

    def test_alarms_conditional(self, template: Dict[str, Any]) -> None:
        """Test alarms are conditional on CreateAlarms."""
        resources = template["Resources"]
        alarms = [
            r for r in resources
            if resources[r]["Type"] == "AWS::CloudWatch::Alarm"
        ]
        for alarm_name in alarms:
            alarm = resources[alarm_name]
            assert alarm.get("Condition") == "CreateAlarms", \
                f"{alarm_name} should be conditional"
