"""Tests for RDS PostgreSQL CloudFormation template.

Issue #141: 13.2.2 RDS PostgreSQL production setup with encryption
"""

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml


# Path to the CloudFormation template
TEMPLATE_PATH = Path(__file__).parent.parent.parent.parent / "cloudformation" / "rds" / "rds-postgresql.yaml"


# Custom YAML loader that handles CloudFormation intrinsic functions
class CloudFormationLoader(yaml.SafeLoader):
    """YAML loader that handles CloudFormation intrinsic functions."""

    pass


def _multi_constructor(loader: yaml.Loader, tag_suffix: str, node: yaml.Node) -> dict[str, Any]:
    """Handle CloudFormation intrinsic functions."""
    if isinstance(node, yaml.ScalarNode):
        return {tag_suffix: loader.construct_scalar(node)}
    elif isinstance(node, yaml.SequenceNode):
        return {tag_suffix: loader.construct_sequence(node)}
    elif isinstance(node, yaml.MappingNode):
        return {tag_suffix: loader.construct_mapping(node)}
    return {tag_suffix: None}


# Register all CloudFormation intrinsic functions
for fn in ['Ref', 'Sub', 'If', 'Equals', 'Not', 'And', 'Or', 'Condition',
           'GetAtt', 'GetAZs', 'ImportValue', 'Join', 'Select', 'Split',
           'FindInMap', 'Base64', 'Cidr', 'Transform']:
    CloudFormationLoader.add_multi_constructor(f'!{fn}', _multi_constructor)


@pytest.fixture
def template() -> dict[str, Any]:
    """Load the CloudFormation template."""
    with open(TEMPLATE_PATH) as f:
        return yaml.load(f, Loader=CloudFormationLoader)


class TestTemplateStructure:
    """Tests for template structure."""

    def test_template_has_description(self, template: dict[str, Any]) -> None:
        """Test template has a description."""
        assert "Description" in template
        assert "RDS PostgreSQL" in template["Description"]

    def test_template_has_parameters(self, template: dict[str, Any]) -> None:
        """Test template has required parameters."""
        assert "Parameters" in template
        params = template["Parameters"]

        required_params = [
            "Environment",
            "VpcId",
            "PrivateSubnetIds",
            "ApplicationSecurityGroupId",
            "DBInstanceClass",
            "DBAllocatedStorage",
            "DBName",
            "DBMasterUsername",
        ]

        for param in required_params:
            assert param in params, f"Missing required parameter: {param}"

    def test_template_has_resources(self, template: dict[str, Any]) -> None:
        """Test template has required resources."""
        assert "Resources" in template
        resources = template["Resources"]

        required_resources = [
            "RDSEncryptionKey",
            "DBMasterSecret",
            "RDSSecurityGroup",
            "DBSubnetGroup",
            "DBParameterGroup",
            "RDSMonitoringRole",
            "RDSInstance",
        ]

        for resource in required_resources:
            assert resource in resources, f"Missing required resource: {resource}"

    def test_template_has_outputs(self, template: dict[str, Any]) -> None:
        """Test template has required outputs."""
        assert "Outputs" in template
        outputs = template["Outputs"]

        required_outputs = [
            "RDSInstanceId",
            "RDSInstanceEndpoint",
            "RDSInstancePort",
            "DBSecretArn",
            "KMSKeyArn",
            "RDSSecurityGroupId",
            "ConnectionString",
        ]

        for output in required_outputs:
            assert output in outputs, f"Missing required output: {output}"


class TestKMSKey:
    """Tests for KMS key configuration."""

    def test_kms_key_has_rotation(self, template: dict[str, Any]) -> None:
        """Test KMS key has key rotation enabled."""
        kms_key = template["Resources"]["RDSEncryptionKey"]
        assert kms_key["Properties"]["EnableKeyRotation"] is True

    def test_kms_key_has_policy(self, template: dict[str, Any]) -> None:
        """Test KMS key has proper key policy."""
        kms_key = template["Resources"]["RDSEncryptionKey"]
        assert "KeyPolicy" in kms_key["Properties"]

        policy = kms_key["Properties"]["KeyPolicy"]
        assert policy["Version"] == "2012-10-17"

        # Check that RDS service is allowed
        statements = policy["Statement"]
        rds_statement = next(
            (s for s in statements if s.get("Sid") == "Allow RDS to use the key"),
            None
        )
        assert rds_statement is not None
        assert rds_statement["Principal"]["Service"] == "rds.amazonaws.com"


class TestSecretsManager:
    """Tests for Secrets Manager configuration."""

    def test_secret_has_generated_password(self, template: dict[str, Any]) -> None:
        """Test secret generates a random password."""
        secret = template["Resources"]["DBMasterSecret"]
        assert "GenerateSecretString" in secret["Properties"]

        gen_config = secret["Properties"]["GenerateSecretString"]
        assert gen_config["PasswordLength"] == 32
        assert "ExcludeCharacters" in gen_config

    def test_secret_uses_kms_key(self, template: dict[str, Any]) -> None:
        """Test secret is encrypted with KMS key."""
        secret = template["Resources"]["DBMasterSecret"]
        assert "KmsKeyId" in secret["Properties"]


class TestSecurityGroup:
    """Tests for security group configuration."""

    def test_security_group_restricts_access(self, template: dict[str, Any]) -> None:
        """Test security group only allows access from application tier."""
        sg = template["Resources"]["RDSSecurityGroup"]
        ingress = sg["Properties"]["SecurityGroupIngress"]

        assert len(ingress) == 1
        assert ingress[0]["FromPort"] == 5432
        assert ingress[0]["ToPort"] == 5432
        assert "SourceSecurityGroupId" in ingress[0]


class TestRDSInstance:
    """Tests for RDS instance configuration."""

    def test_instance_uses_postgresql_15(self, template: dict[str, Any]) -> None:
        """Test instance uses PostgreSQL 15."""
        instance = template["Resources"]["RDSInstance"]
        assert instance["Properties"]["Engine"] == "postgres"
        assert instance["Properties"]["EngineVersion"] == "15.4"

    def test_instance_has_encryption(self, template: dict[str, Any]) -> None:
        """Test instance has encryption at rest enabled."""
        instance = template["Resources"]["RDSInstance"]
        assert instance["Properties"]["StorageEncrypted"] is True
        assert "KmsKeyId" in instance["Properties"]

    def test_instance_has_backup_configured(self, template: dict[str, Any]) -> None:
        """Test instance has backup configuration."""
        instance = template["Resources"]["RDSInstance"]
        assert "BackupRetentionPeriod" in instance["Properties"]
        assert "PreferredBackupWindow" in instance["Properties"]
        assert instance["Properties"]["CopyTagsToSnapshot"] is True

    def test_instance_has_monitoring(self, template: dict[str, Any]) -> None:
        """Test instance has enhanced monitoring enabled."""
        instance = template["Resources"]["RDSInstance"]
        assert instance["Properties"]["MonitoringInterval"] == 60
        assert "MonitoringRoleArn" in instance["Properties"]
        assert instance["Properties"]["EnablePerformanceInsights"] is True

    def test_instance_has_iam_auth(self, template: dict[str, Any]) -> None:
        """Test instance has IAM authentication enabled."""
        instance = template["Resources"]["RDSInstance"]
        assert instance["Properties"]["EnableIAMDatabaseAuthentication"] is True

    def test_instance_not_publicly_accessible(self, template: dict[str, Any]) -> None:
        """Test instance is not publicly accessible."""
        instance = template["Resources"]["RDSInstance"]
        assert instance["Properties"]["PubliclyAccessible"] is False

    def test_instance_has_deletion_protection(self, template: dict[str, Any]) -> None:
        """Test instance has deletion protection (conditional)."""
        instance = template["Resources"]["RDSInstance"]
        assert "DeletionProtection" in instance["Properties"]

    def test_instance_has_cloudwatch_logs(self, template: dict[str, Any]) -> None:
        """Test instance exports CloudWatch logs."""
        instance = template["Resources"]["RDSInstance"]
        exports = instance["Properties"]["EnableCloudwatchLogsExports"]
        assert "postgresql" in exports
        assert "upgrade" in exports


class TestParameterGroup:
    """Tests for DB parameter group configuration."""

    def test_parameter_group_family(self, template: dict[str, Any]) -> None:
        """Test parameter group uses correct family."""
        param_group = template["Resources"]["DBParameterGroup"]
        assert param_group["Properties"]["Family"] == "postgres15"

    def test_parameter_group_forces_ssl(self, template: dict[str, Any]) -> None:
        """Test parameter group forces SSL connections."""
        param_group = template["Resources"]["DBParameterGroup"]
        params = param_group["Properties"]["Parameters"]
        assert params["rds.force_ssl"] == "1"

    def test_parameter_group_has_memory_settings(self, template: dict[str, Any]) -> None:
        """Test parameter group has memory optimization settings."""
        param_group = template["Resources"]["DBParameterGroup"]
        params = param_group["Properties"]["Parameters"]

        memory_params = [
            "shared_buffers",
            "effective_cache_size",
            "work_mem",
            "maintenance_work_mem",
        ]

        for param in memory_params:
            assert param in params, f"Missing memory parameter: {param}"


class TestCloudWatchAlarms:
    """Tests for CloudWatch alarms."""

    def test_cpu_alarm_exists(self, template: dict[str, Any]) -> None:
        """Test CPU utilization alarm exists."""
        assert "CPUUtilizationAlarm" in template["Resources"]
        alarm = template["Resources"]["CPUUtilizationAlarm"]
        assert alarm["Properties"]["MetricName"] == "CPUUtilization"
        assert alarm["Properties"]["Threshold"] == 80

    def test_storage_alarm_exists(self, template: dict[str, Any]) -> None:
        """Test free storage space alarm exists."""
        assert "FreeStorageSpaceAlarm" in template["Resources"]
        alarm = template["Resources"]["FreeStorageSpaceAlarm"]
        assert alarm["Properties"]["MetricName"] == "FreeStorageSpace"

    def test_connections_alarm_exists(self, template: dict[str, Any]) -> None:
        """Test database connections alarm exists."""
        assert "DatabaseConnectionsAlarm" in template["Resources"]
        alarm = template["Resources"]["DatabaseConnectionsAlarm"]
        assert alarm["Properties"]["MetricName"] == "DatabaseConnections"
        assert alarm["Properties"]["Threshold"] == 180

    def test_latency_alarms_exist(self, template: dict[str, Any]) -> None:
        """Test read/write latency alarms exist."""
        assert "ReadLatencyAlarm" in template["Resources"]
        assert "WriteLatencyAlarm" in template["Resources"]

    def test_memory_alarm_exists(self, template: dict[str, Any]) -> None:
        """Test freeable memory alarm exists."""
        assert "FreeableMemoryAlarm" in template["Resources"]


class TestConditionalResources:
    """Tests for conditional resources."""

    def test_read_replica_is_conditional(self, template: dict[str, Any]) -> None:
        """Test read replica creation is conditional."""
        replica = template["Resources"]["RDSReadReplica"]
        assert replica["Condition"] == "CreateReadReplica"

    def test_rds_proxy_is_conditional(self, template: dict[str, Any]) -> None:
        """Test RDS Proxy creation is conditional."""
        proxy = template["Resources"]["RDSProxy"]
        assert proxy["Condition"] == "CreateRDSProxy"

    def test_replica_lag_alarm_is_conditional(self, template: dict[str, Any]) -> None:
        """Test replica lag alarm is conditional."""
        alarm = template["Resources"]["ReplicaLagAlarm"]
        assert alarm["Condition"] == "CreateReadReplica"


class TestRDSProxy:
    """Tests for RDS Proxy configuration."""

    def test_proxy_requires_tls(self, template: dict[str, Any]) -> None:
        """Test RDS Proxy requires TLS."""
        proxy = template["Resources"]["RDSProxy"]
        assert proxy["Properties"]["RequireTLS"] is True

    def test_proxy_uses_secrets(self, template: dict[str, Any]) -> None:
        """Test RDS Proxy uses Secrets Manager."""
        proxy = template["Resources"]["RDSProxy"]
        auth = proxy["Properties"]["Auth"]
        assert len(auth) > 0
        assert auth[0]["AuthScheme"] == "SECRETS"


class TestTemplateValidation:
    """Tests for template validation."""

    def test_template_is_valid_yaml(self) -> None:
        """Test template is valid YAML."""
        with open(TEMPLATE_PATH) as f:
            template = yaml.load(f, Loader=CloudFormationLoader)
        assert template is not None
        assert isinstance(template, dict)

    def test_template_passes_aws_validation(self) -> None:
        """Test template passes AWS CloudFormation validation."""
        result = subprocess.run(
            [
                "aws", "cloudformation", "validate-template",
                "--template-body", f"file://{TEMPLATE_PATH}"
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Template validation failed: {result.stderr}"


class TestDashboard:
    """Tests for CloudWatch dashboard."""

    def test_dashboard_exists(self, template: dict[str, Any]) -> None:
        """Test CloudWatch dashboard is created."""
        assert "RDSDashboard" in template["Resources"]

    def test_dashboard_has_widgets(self, template: dict[str, Any]) -> None:
        """Test dashboard has monitoring widgets."""
        dashboard = template["Resources"]["RDSDashboard"]
        assert "DashboardBody" in dashboard["Properties"]
