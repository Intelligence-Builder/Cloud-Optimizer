"""Unit tests for X-Ray Tracing CloudFormation template.

Issue #167: Distributed tracing with X-Ray.
Tests for xray-tracing.yaml template structure and configuration.
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


class TestXRayTracingTemplate:
    """Test X-Ray tracing CloudFormation template structure."""

    @pytest.fixture
    def template_path(self) -> Path:
        """Get path to X-Ray tracing template."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "xray-tracing.yaml"
        )

    @pytest.fixture
    def template(self, template_path: Path) -> Dict[str, Any]:
        """Load and parse the CloudFormation template."""
        return load_cfn_template(template_path)

    def test_template_file_exists(self, template_path: Path) -> None:
        """Test that X-Ray tracing template file exists."""
        assert template_path.exists(), "X-Ray tracing template should exist"

    def test_template_version(self, template: Dict[str, Any]) -> None:
        """Test template has valid AWSTemplateFormatVersion."""
        assert template["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_template_has_description(self, template: Dict[str, Any]) -> None:
        """Test template has description."""
        assert "Description" in template
        assert "X-Ray" in template["Description"]

    def test_required_parameters_exist(self, template: Dict[str, Any]) -> None:
        """Test all required parameters are defined."""
        params = template.get("Parameters", {})
        required_params = [
            "Environment",
            "ServiceName",
            "AlertTopicArn",
            "DefaultSamplingRate",
            "APISamplingRate",
        ]
        for param in required_params:
            assert param in params, f"Missing required parameter: {param}"

    def test_environment_parameter(self, template: Dict[str, Any]) -> None:
        """Test Environment parameter configuration."""
        env_param = template["Parameters"]["Environment"]
        assert env_param["Type"] == "String"
        assert "AllowedValues" in env_param
        allowed = env_param["AllowedValues"]
        assert "development" in allowed
        assert "staging" in allowed
        assert "production" in allowed

    def test_sampling_rate_parameters(self, template: Dict[str, Any]) -> None:
        """Test sampling rate parameters have valid ranges."""
        params = template["Parameters"]

        for rate_param in ["DefaultSamplingRate", "APISamplingRate", "ErrorSamplingRate"]:
            param = params[rate_param]
            assert param["Type"] == "Number"
            assert param["MinValue"] <= param["Default"] <= param["MaxValue"]


class TestXRaySamplingRules:
    """Test X-Ray sampling rule resources."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load X-Ray tracing template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "xray-tracing.yaml"
        )
        return load_cfn_template(path)

    def test_xray_group_exists(self, template: Dict[str, Any]) -> None:
        """Test X-Ray group resource is defined."""
        resources = template.get("Resources", {})
        assert "XRayGroup" in resources
        group = resources["XRayGroup"]
        assert group["Type"] == "AWS::XRay::Group"

    def test_xray_group_has_insights(self, template: Dict[str, Any]) -> None:
        """Test X-Ray group has insights configuration."""
        group = template["Resources"]["XRayGroup"]
        props = group["Properties"]
        assert "InsightsConfiguration" in props

    def test_default_sampling_rule_exists(self, template: Dict[str, Any]) -> None:
        """Test default sampling rule is defined."""
        resources = template.get("Resources", {})
        assert "DefaultSamplingRule" in resources
        rule = resources["DefaultSamplingRule"]
        assert rule["Type"] == "AWS::XRay::SamplingRule"

    def test_api_sampling_rule_exists(self, template: Dict[str, Any]) -> None:
        """Test API sampling rule is defined."""
        resources = template.get("Resources", {})
        assert "APISamplingRule" in resources
        rule = resources["APISamplingRule"]
        assert rule["Type"] == "AWS::XRay::SamplingRule"

    def test_error_sampling_rule_exists(self, template: Dict[str, Any]) -> None:
        """Test error sampling rule is defined."""
        resources = template.get("Resources", {})
        assert "ErrorSamplingRule" in resources

    def test_health_check_sampling_rule_exists(self, template: Dict[str, Any]) -> None:
        """Test health check sampling rule is defined."""
        resources = template.get("Resources", {})
        assert "HealthCheckSamplingRule" in resources

    def test_scanner_sampling_rule_exists(self, template: Dict[str, Any]) -> None:
        """Test scanner sampling rule is defined."""
        resources = template.get("Resources", {})
        assert "ScannerSamplingRule" in resources

    def test_sampling_rule_count(self, template: Dict[str, Any]) -> None:
        """Test expected number of sampling rules."""
        resources = template.get("Resources", {})
        sampling_rules = [
            r for r in resources
            if resources[r]["Type"] == "AWS::XRay::SamplingRule"
        ]
        assert len(sampling_rules) == 5, "Should have 5 sampling rules"


class TestXRayAlarms:
    """Test X-Ray CloudWatch alarm resources."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load X-Ray tracing template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "xray-tracing.yaml"
        )
        return load_cfn_template(path)

    def test_high_latency_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test high latency alarm is defined."""
        resources = template.get("Resources", {})
        assert "HighLatencyAlarm" in resources
        alarm = resources["HighLatencyAlarm"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"

    def test_error_rate_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test error rate alarm is defined."""
        resources = template.get("Resources", {})
        assert "ErrorRateAlarm" in resources

    def test_fault_rate_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test fault rate alarm is defined."""
        resources = template.get("Resources", {})
        assert "FaultRateAlarm" in resources

    def test_throttle_rate_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test throttle rate alarm is defined."""
        resources = template.get("Resources", {})
        assert "ThrottleRateAlarm" in resources

    def test_alarm_count(self, template: Dict[str, Any]) -> None:
        """Test expected number of alarms."""
        resources = template.get("Resources", {})
        alarms = [
            r for r in resources
            if resources[r]["Type"] == "AWS::CloudWatch::Alarm"
        ]
        assert len(alarms) == 4, "Should have 4 CloudWatch alarms"


class TestXRayDashboard:
    """Test X-Ray CloudWatch dashboard."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load X-Ray tracing template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "xray-tracing.yaml"
        )
        return load_cfn_template(path)

    def test_dashboard_exists(self, template: Dict[str, Any]) -> None:
        """Test CloudWatch dashboard is defined."""
        resources = template.get("Resources", {})
        assert "XRayDashboard" in resources
        dashboard = resources["XRayDashboard"]
        assert dashboard["Type"] == "AWS::CloudWatch::Dashboard"

    def test_dashboard_conditional(self, template: Dict[str, Any]) -> None:
        """Test dashboard is only created in production."""
        dashboard = template["Resources"]["XRayDashboard"]
        assert dashboard.get("Condition") == "IsProduction"


class TestXRayOutputs:
    """Test X-Ray template outputs."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load X-Ray tracing template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "xray-tracing.yaml"
        )
        return load_cfn_template(path)

    def test_outputs_defined(self, template: Dict[str, Any]) -> None:
        """Test template has required outputs."""
        outputs = template.get("Outputs", {})
        required_outputs = [
            "XRayGroupName",
            "XRayGroupARN",
            "DefaultSamplingRuleARN",
            "APISamplingRuleARN",
            "SamplingRates",
        ]
        for output in required_outputs:
            assert output in outputs, f"Missing output: {output}"

    def test_outputs_exported(self, template: Dict[str, Any]) -> None:
        """Test key outputs are exported."""
        outputs = template["Outputs"]
        for key in ["XRayGroupName", "XRayGroupARN"]:
            assert "Export" in outputs[key], f"{key} should be exported"
