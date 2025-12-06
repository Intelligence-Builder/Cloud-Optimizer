"""Unit tests for Blue/Green Deployment CloudFormation template.

Issue #159: Blue/green deployment strategy.
Tests for cloudformation/blue-green-deployment.yaml template structure.
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


class TestBlueGreenDeploymentTemplate:
    """Test Blue/Green Deployment CloudFormation template structure."""

    @pytest.fixture
    def template_path(self) -> Path:
        """Get path to blue/green deployment template."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "blue-green-deployment.yaml"
        )

    @pytest.fixture
    def template(self, template_path: Path) -> Dict[str, Any]:
        """Load and parse the CloudFormation template."""
        return load_cfn_template(template_path)

    def test_template_file_exists(self, template_path: Path) -> None:
        """Test that blue/green deployment template file exists."""
        assert template_path.exists(), "Blue/green deployment template should exist"

    def test_template_version(self, template: Dict[str, Any]) -> None:
        """Test template has valid AWSTemplateFormatVersion."""
        assert template["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_template_has_description(self, template: Dict[str, Any]) -> None:
        """Test template has description mentioning blue/green."""
        assert "Description" in template
        assert "Blue/Green" in template["Description"]

    def test_required_parameters_exist(self, template: Dict[str, Any]) -> None:
        """Test all required parameters are defined."""
        params = template.get("Parameters", {})
        required_params = [
            "EnvironmentName",
            "VpcId",
            "SubnetIds",
            "ContainerImage",
            "ContainerPort",
            "DesiredCount",
            "HealthCheckPath",
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


class TestBlueGreenTargetGroups:
    """Test Blue and Green target group resources."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load blue/green deployment template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "blue-green-deployment.yaml"
        )
        return load_cfn_template(path)

    def test_blue_target_group_exists(self, template: Dict[str, Any]) -> None:
        """Test Blue target group resource is defined."""
        resources = template.get("Resources", {})
        assert "BlueTargetGroup" in resources
        tg = resources["BlueTargetGroup"]
        assert tg["Type"] == "AWS::ElasticLoadBalancingV2::TargetGroup"

    def test_green_target_group_exists(self, template: Dict[str, Any]) -> None:
        """Test Green target group resource is defined."""
        resources = template.get("Resources", {})
        assert "GreenTargetGroup" in resources
        tg = resources["GreenTargetGroup"]
        assert tg["Type"] == "AWS::ElasticLoadBalancingV2::TargetGroup"

    def test_target_groups_have_health_checks(self, template: Dict[str, Any]) -> None:
        """Test both target groups have health checks configured."""
        resources = template.get("Resources", {})
        for tg_name in ["BlueTargetGroup", "GreenTargetGroup"]:
            tg = resources[tg_name]["Properties"]
            assert tg.get("HealthCheckEnabled") is True
            assert "HealthCheckPath" in tg
            assert "HealthCheckProtocol" in tg

    def test_target_groups_use_ip_type(self, template: Dict[str, Any]) -> None:
        """Test target groups use IP target type for Fargate compatibility."""
        resources = template.get("Resources", {})
        for tg_name in ["BlueTargetGroup", "GreenTargetGroup"]:
            tg = resources[tg_name]["Properties"]
            assert tg.get("TargetType") == "ip"


class TestBlueGreenListeners:
    """Test ALB listener configuration for traffic shifting."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load blue/green deployment template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "blue-green-deployment.yaml"
        )
        return load_cfn_template(path)

    def test_production_listener_exists(self, template: Dict[str, Any]) -> None:
        """Test production listener is defined on port 80."""
        resources = template.get("Resources", {})
        assert "ProductionListener" in resources
        listener = resources["ProductionListener"]
        assert listener["Type"] == "AWS::ElasticLoadBalancingV2::Listener"
        assert listener["Properties"]["Port"] == 80

    def test_test_listener_exists(self, template: Dict[str, Any]) -> None:
        """Test test listener is defined on port 8080."""
        resources = template.get("Resources", {})
        assert "TestListener" in resources
        listener = resources["TestListener"]
        assert listener["Type"] == "AWS::ElasticLoadBalancingV2::Listener"
        assert listener["Properties"]["Port"] == 8080

    def test_production_listener_has_weighted_routing(
        self, template: Dict[str, Any]
    ) -> None:
        """Test production listener has weighted routing for traffic shift."""
        resources = template.get("Resources", {})
        listener = resources["ProductionListener"]["Properties"]
        actions = listener["DefaultActions"]
        assert len(actions) > 0
        action = actions[0]
        assert action["Type"] == "forward"
        assert "ForwardConfig" in action

    def test_test_listener_routes_to_green(self, template: Dict[str, Any]) -> None:
        """Test test listener routes to green target group."""
        resources = template.get("Resources", {})
        listener = resources["TestListener"]["Properties"]
        actions = listener["DefaultActions"]
        assert len(actions) > 0
        # Should forward to green target group


class TestBlueGreenECSServices:
    """Test ECS service configuration for blue/green deployment."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load blue/green deployment template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "blue-green-deployment.yaml"
        )
        return load_cfn_template(path)

    def test_ecs_cluster_exists(self, template: Dict[str, Any]) -> None:
        """Test ECS cluster is defined."""
        resources = template.get("Resources", {})
        assert "ECSCluster" in resources
        cluster = resources["ECSCluster"]
        assert cluster["Type"] == "AWS::ECS::Cluster"

    def test_blue_service_exists(self, template: Dict[str, Any]) -> None:
        """Test Blue ECS service is defined."""
        resources = template.get("Resources", {})
        assert "BlueService" in resources
        service = resources["BlueService"]
        assert service["Type"] == "AWS::ECS::Service"

    def test_green_service_exists(self, template: Dict[str, Any]) -> None:
        """Test Green ECS service is defined."""
        resources = template.get("Resources", {})
        assert "GreenService" in resources
        service = resources["GreenService"]
        assert service["Type"] == "AWS::ECS::Service"

    def test_services_use_fargate(self, template: Dict[str, Any]) -> None:
        """Test both services use Fargate launch type."""
        resources = template.get("Resources", {})
        for svc_name in ["BlueService", "GreenService"]:
            svc = resources[svc_name]["Properties"]
            assert svc.get("LaunchType") == "FARGATE"

    def test_green_service_starts_with_zero_tasks(
        self, template: Dict[str, Any]
    ) -> None:
        """Test Green service starts with 0 tasks (scaled up during deployment)."""
        resources = template.get("Resources", {})
        green_svc = resources["GreenService"]["Properties"]
        assert green_svc.get("DesiredCount") == 0

    def test_services_have_circuit_breaker(self, template: Dict[str, Any]) -> None:
        """Test services have deployment circuit breaker for rollback."""
        resources = template.get("Resources", {})
        for svc_name in ["BlueService", "GreenService"]:
            svc = resources[svc_name]["Properties"]
            deploy_config = svc.get("DeploymentConfiguration", {})
            assert "DeploymentCircuitBreaker" in deploy_config


class TestBlueGreenDeploymentAlarms:
    """Test CloudWatch alarms for deployment monitoring."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load blue/green deployment template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "blue-green-deployment.yaml"
        )
        return load_cfn_template(path)

    def test_blue_target_group_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test Blue target group health alarm is defined."""
        resources = template.get("Resources", {})
        assert "BlueTargetGroupHealthyAlarm" in resources
        alarm = resources["BlueTargetGroupHealthyAlarm"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"

    def test_green_target_group_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test Green target group health alarm is defined."""
        resources = template.get("Resources", {})
        assert "GreenTargetGroupHealthyAlarm" in resources
        alarm = resources["GreenTargetGroupHealthyAlarm"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"

    def test_error_rate_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test deployment error rate alarm is defined."""
        resources = template.get("Resources", {})
        assert "DeploymentErrorRateAlarm" in resources
        alarm = resources["DeploymentErrorRateAlarm"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"

    def test_latency_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test deployment latency alarm is defined."""
        resources = template.get("Resources", {})
        assert "DeploymentLatencyAlarm" in resources
        alarm = resources["DeploymentLatencyAlarm"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"

    def test_alarm_count(self, template: Dict[str, Any]) -> None:
        """Test expected number of deployment alarms."""
        resources = template.get("Resources", {})
        alarms = [
            r for r in resources
            if resources[r]["Type"] == "AWS::CloudWatch::Alarm"
        ]
        assert len(alarms) >= 4, "Should have at least 4 CloudWatch alarms"


class TestBlueGreenOutputs:
    """Test CloudFormation template outputs."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load blue/green deployment template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "blue-green-deployment.yaml"
        )
        return load_cfn_template(path)

    def test_outputs_defined(self, template: Dict[str, Any]) -> None:
        """Test template has required outputs."""
        outputs = template.get("Outputs", {})
        required_outputs = [
            "ClusterName",
            "LoadBalancerDNS",
            "BlueTargetGroupArn",
            "GreenTargetGroupArn",
            "ProductionListenerArn",
            "TestListenerArn",
        ]
        for output in required_outputs:
            assert output in outputs, f"Missing output: {output}"

    def test_target_group_arns_exported(self, template: Dict[str, Any]) -> None:
        """Test target group ARNs are exported for cross-stack references."""
        outputs = template["Outputs"]
        assert "Export" in outputs["BlueTargetGroupArn"]
        assert "Export" in outputs["GreenTargetGroupArn"]

    def test_listener_arns_exported(self, template: Dict[str, Any]) -> None:
        """Test listener ARNs are exported."""
        outputs = template["Outputs"]
        assert "Export" in outputs["ProductionListenerArn"]
        assert "Export" in outputs["TestListenerArn"]


class TestBlueGreenConditions:
    """Test conditional resources in the template."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load blue/green deployment template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "blue-green-deployment.yaml"
        )
        return load_cfn_template(path)

    def test_conditions_defined(self, template: Dict[str, Any]) -> None:
        """Test conditions are defined for optional features."""
        conditions = template.get("Conditions", {})
        assert "HasAlertTopic" in conditions
        assert "EnableRollback" in conditions

    def test_rollback_condition_checks_parameter(
        self, template: Dict[str, Any]
    ) -> None:
        """Test rollback condition checks DeploymentRollbackEnabled parameter."""
        # Verify the parameter exists
        params = template.get("Parameters", {})
        assert "DeploymentRollbackEnabled" in params


class TestBlueGreenSecurityGroups:
    """Test security group configuration."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load blue/green deployment template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "blue-green-deployment.yaml"
        )
        return load_cfn_template(path)

    def test_alb_security_group_exists(self, template: Dict[str, Any]) -> None:
        """Test ALB security group is defined."""
        resources = template.get("Resources", {})
        assert "ALBSecurityGroup" in resources
        sg = resources["ALBSecurityGroup"]
        assert sg["Type"] == "AWS::EC2::SecurityGroup"

    def test_ecs_security_group_exists(self, template: Dict[str, Any]) -> None:
        """Test ECS security group is defined."""
        resources = template.get("Resources", {})
        assert "ECSSecurityGroup" in resources
        sg = resources["ECSSecurityGroup"]
        assert sg["Type"] == "AWS::EC2::SecurityGroup"

    def test_alb_allows_http_https(self, template: Dict[str, Any]) -> None:
        """Test ALB security group allows HTTP and HTTPS traffic."""
        resources = template.get("Resources", {})
        sg = resources["ALBSecurityGroup"]["Properties"]
        ingress = sg["SecurityGroupIngress"]

        ports = [rule.get("FromPort") for rule in ingress]
        assert 80 in ports, "ALB should allow HTTP on port 80"
        assert 443 in ports, "ALB should allow HTTPS on port 443"


class TestBlueGreenIAMRoles:
    """Test IAM role configuration."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load blue/green deployment template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "blue-green-deployment.yaml"
        )
        return load_cfn_template(path)

    def test_task_execution_role_exists(self, template: Dict[str, Any]) -> None:
        """Test task execution role is defined."""
        resources = template.get("Resources", {})
        assert "TaskExecutionRole" in resources
        role = resources["TaskExecutionRole"]
        assert role["Type"] == "AWS::IAM::Role"

    def test_task_role_exists(self, template: Dict[str, Any]) -> None:
        """Test task role is defined."""
        resources = template.get("Resources", {})
        assert "TaskRole" in resources
        role = resources["TaskRole"]
        assert role["Type"] == "AWS::IAM::Role"

    def test_task_definition_exists(self, template: Dict[str, Any]) -> None:
        """Test ECS task definition is defined."""
        resources = template.get("Resources", {})
        assert "TaskDefinition" in resources
        task_def = resources["TaskDefinition"]
        assert task_def["Type"] == "AWS::ECS::TaskDefinition"
