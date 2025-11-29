"""
Unit tests for ReliabilityScanner - Pure logic tests only.

These tests verify scanner logic WITHOUT mocking AWS services.
AWS interaction tests are in tests/integration/ using LocalStack.

Testing Strategy:
- Unit tests: Test internal logic (finding creation, severity calculation)
- Integration tests: Test actual AWS API interactions via LocalStack
"""

import pytest

from cloud_optimizer.integrations.aws.reliability import ReliabilityScanner


class TestReliabilityScannerInitialization:
    """Tests for ReliabilityScanner initialization and configuration."""

    def test_scanner_name(self):
        """Test scanner returns correct name."""
        scanner = ReliabilityScanner()
        assert scanner.get_scanner_name() == "ReliabilityScanner"

    def test_scanner_default_region(self):
        """Test scanner uses default region."""
        scanner = ReliabilityScanner()
        assert scanner.region == "us-east-1"

    def test_scanner_custom_region(self):
        """Test scanner accepts custom region."""
        scanner = ReliabilityScanner(region="eu-west-1")
        assert scanner.region == "eu-west-1"

    def test_thresholds_defined(self):
        """Test thresholds are properly defined."""
        assert ReliabilityScanner.MIN_BACKUP_RETENTION_DAYS == 7
        assert ReliabilityScanner.MIN_HEALTHY_INSTANCES == 2


class TestSingleAZRDSFinding:
    """Tests for single-AZ RDS finding creation."""

    def test_create_single_az_rds_finding(self):
        """Test single-AZ RDS finding has correct structure."""
        scanner = ReliabilityScanner()

        finding = scanner._create_single_az_rds_finding(
            db_identifier="prod-database",
            engine="postgres",
            account_id="123456789012",
        )

        assert finding["finding_type"] == "single_point_of_failure"
        assert finding["severity"] == "high"
        assert "prod-database" in finding["title"]
        assert "Single-AZ" in finding["title"]
        assert "Multi-AZ" in finding["description"]
        assert finding["resource_type"] == "rds_instance"
        assert finding["metadata"]["db_identifier"] == "prod-database"
        assert finding["metadata"]["engine"] == "postgres"
        assert finding["metadata"]["multi_az"] is False

    def test_single_az_includes_remediation(self):
        """Test single-AZ finding includes remediation steps."""
        scanner = ReliabilityScanner()

        finding = scanner._create_single_az_rds_finding(
            db_identifier="test-db",
            engine="mysql",
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "Multi-AZ" in finding["remediation"]
        assert "test-db" in finding["remediation"]


class TestBackupConfigurationFinding:
    """Tests for backup configuration finding creation."""

    def test_create_backup_disabled_finding(self):
        """Test backup disabled finding has critical severity."""
        scanner = ReliabilityScanner()

        finding = scanner._create_backup_configuration_finding(
            db_identifier="no-backup-db",
            current_retention=0,
            engine="postgres",
            account_id="123456789012",
        )

        assert finding["finding_type"] == "backup_configuration"
        assert finding["severity"] == "critical"
        assert "disabled" in finding["title"]
        assert "no-backup-db" in finding["title"]
        assert finding["metadata"]["current_retention_days"] == 0
        assert finding["metadata"]["recommended_retention_days"] == 7

    def test_create_insufficient_retention_finding(self):
        """Test insufficient retention finding has correct structure."""
        scanner = ReliabilityScanner()

        finding = scanner._create_backup_configuration_finding(
            db_identifier="short-retention-db",
            current_retention=3,
            engine="mysql",
            account_id="123456789012",
        )

        assert finding["finding_type"] == "backup_configuration"
        assert finding["severity"] == "medium"
        assert "Insufficient" in finding["title"]
        assert "3 days" in finding["title"]
        assert finding["metadata"]["current_retention_days"] == 3
        assert finding["metadata"]["recommended_retention_days"] == 7

    def test_backup_finding_includes_remediation(self):
        """Test backup finding includes remediation steps."""
        scanner = ReliabilityScanner()

        finding = scanner._create_backup_configuration_finding(
            db_identifier="test-db",
            current_retention=1,
            engine="postgres",
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "automated backups" in finding["remediation"]
        assert "7" in finding["remediation"]


class TestHealthCheckFinding:
    """Tests for health check finding creation."""

    def test_create_missing_health_check_finding(self):
        """Test missing health check finding has high severity."""
        scanner = ReliabilityScanner()

        finding = scanner._create_missing_health_check_finding(
            lb_name="prod-lb",
            lb_type="application",
            account_id="123456789012",
        )

        assert finding["finding_type"] == "health_check"
        assert finding["severity"] == "high"
        assert "Missing health check" in finding["title"]
        assert "prod-lb" in finding["title"]
        assert "health checks configured" in finding["description"]
        assert finding["metadata"]["lb_name"] == "prod-lb"
        assert finding["metadata"]["lb_type"] == "application"

    def test_create_misconfigured_health_check_finding(self):
        """Test misconfigured health check finding has medium severity."""
        scanner = ReliabilityScanner()

        finding = scanner._create_misconfigured_health_check_finding(
            lb_name="test-lb",
            lb_type="network",
            interval=30,
            timeout=30,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "health_check"
        assert finding["severity"] == "medium"
        assert "Misconfigured health check" in finding["title"]
        assert "test-lb" in finding["title"]
        assert "timeout" in finding["description"]
        assert finding["metadata"]["interval_seconds"] == 30
        assert finding["metadata"]["timeout_seconds"] == 30

    def test_health_check_finding_includes_remediation(self):
        """Test health check finding includes remediation steps."""
        scanner = ReliabilityScanner()

        finding = scanner._create_missing_health_check_finding(
            lb_name="my-lb",
            lb_type="classic",
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "Configure health checks" in finding["remediation"]
        assert "my-lb" in finding["remediation"]


class TestEBSSnapshotFinding:
    """Tests for EBS snapshot finding creation."""

    def test_create_no_snapshot_finding(self):
        """Test no snapshot finding has medium severity."""
        scanner = ReliabilityScanner()

        finding = scanner._create_no_snapshot_finding(
            volume_id="vol-0123456789abcdef0",
            size_gb=100,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "backup_configuration"
        assert finding["severity"] == "medium"
        assert "without snapshots" in finding["title"]
        assert "vol-0123456789abcdef0" in finding["title"]
        assert "100 GB" in finding["description"]
        assert finding["resource_type"] == "ebs_volume"
        assert finding["metadata"]["volume_id"] == "vol-0123456789abcdef0"
        assert finding["metadata"]["size_gb"] == 100

    def test_snapshot_finding_includes_remediation(self):
        """Test snapshot finding includes remediation steps."""
        scanner = ReliabilityScanner()

        finding = scanner._create_no_snapshot_finding(
            volume_id="vol-test123",
            size_gb=50,
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "Create snapshots" in finding["remediation"]
        assert "vol-test123" in finding["remediation"]
        assert "Data Lifecycle Manager" in finding["remediation"]


class TestAutoScalingFinding:
    """Tests for Auto Scaling finding creation."""

    def test_create_no_auto_scaling_finding(self):
        """Test no Auto Scaling finding has medium severity."""
        scanner = ReliabilityScanner()

        finding = scanner._create_no_auto_scaling_finding(
            instance_id="i-0123456789abcdef0",
            instance_type="t3.large",
            instance_name="prod-web-server",
            account_id="123456789012",
        )

        assert finding["finding_type"] == "single_point_of_failure"
        assert finding["severity"] == "medium"
        assert "without Auto Scaling" in finding["title"]
        assert "prod-web-server" in finding["title"]
        assert "Auto Scaling Group" in finding["description"]
        assert finding["resource_type"] == "ec2_instance"
        assert finding["metadata"]["instance_id"] == "i-0123456789abcdef0"
        assert finding["metadata"]["instance_type"] == "t3.large"
        assert finding["metadata"]["instance_name"] == "prod-web-server"

    def test_auto_scaling_finding_without_name(self):
        """Test Auto Scaling finding works without instance name."""
        scanner = ReliabilityScanner()

        finding = scanner._create_no_auto_scaling_finding(
            instance_id="i-test123",
            instance_type="m5.xlarge",
            instance_name="",
            account_id="123456789012",
        )

        assert "i-test123" in finding["title"]
        assert finding["resource_name"] == "i-test123"

    def test_auto_scaling_finding_includes_remediation(self):
        """Test Auto Scaling finding includes remediation steps."""
        scanner = ReliabilityScanner()

        finding = scanner._create_no_auto_scaling_finding(
            instance_id="i-prod456",
            instance_type="c5.2xlarge",
            instance_name="api-server",
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "Auto Scaling Group" in finding["remediation"]
        assert "AMI" in finding["remediation"]
        assert "launch template" in finding["remediation"]


class TestSeverityCalculation:
    """Tests for severity calculation logic."""

    def test_severity_critical_no_multi_az_no_backups(self):
        """Test critical severity for no Multi-AZ and no backups."""
        scanner = ReliabilityScanner()

        severity = scanner._calculate_severity(
            has_multi_az=False,
            has_backups=False,
            resource_type="rds",
        )

        assert severity == "critical"

    def test_severity_high_no_multi_az_has_backups(self):
        """Test high severity for no Multi-AZ but has backups."""
        scanner = ReliabilityScanner()

        severity = scanner._calculate_severity(
            has_multi_az=False,
            has_backups=True,
            resource_type="rds",
        )

        assert severity == "high"

    def test_severity_medium_has_multi_az_no_backups(self):
        """Test medium severity for Multi-AZ but no backups."""
        scanner = ReliabilityScanner()

        severity = scanner._calculate_severity(
            has_multi_az=True,
            has_backups=False,
            resource_type="rds",
        )

        assert severity == "medium"

    def test_severity_low_has_both(self):
        """Test low severity for both Multi-AZ and backups."""
        scanner = ReliabilityScanner()

        severity = scanner._calculate_severity(
            has_multi_az=True,
            has_backups=True,
            resource_type="rds",
        )

        assert severity == "low"

    def test_severity_calculation_different_resource_types(self):
        """Test severity calculation works for different resource types."""
        scanner = ReliabilityScanner()

        # Test with EC2
        severity_ec2 = scanner._calculate_severity(
            has_multi_az=False,
            has_backups=False,
            resource_type="ec2",
        )
        assert severity_ec2 == "critical"

        # Test with EBS
        severity_ebs = scanner._calculate_severity(
            has_multi_az=True,
            has_backups=True,
            resource_type="ebs",
        )
        assert severity_ebs == "low"


class TestFindingStructure:
    """Tests for common finding structure requirements."""

    def test_all_findings_have_required_fields(self):
        """Test all finding types have required fields."""
        scanner = ReliabilityScanner()

        # Test each finding type
        findings = [
            scanner._create_single_az_rds_finding("db1", "postgres", "123456789012"),
            scanner._create_backup_configuration_finding(
                "db2", 0, "mysql", "123456789012"
            ),
            scanner._create_missing_health_check_finding(
                "lb1", "application", "123456789012"
            ),
            scanner._create_no_snapshot_finding("vol-123", 100, "123456789012"),
            scanner._create_no_auto_scaling_finding(
                "i-123", "t3.large", "web-server", "123456789012"
            ),
        ]

        required_fields = [
            "finding_type",
            "severity",
            "title",
            "description",
            "resource_arn",
            "resource_id",
            "resource_name",
            "resource_type",
            "aws_account_id",
            "region",
            "remediation",
            "metadata",
        ]

        for finding in findings:
            for field in required_fields:
                assert (
                    field in finding
                ), f"Missing field: {field} in {finding['finding_type']}"

    def test_all_severities_are_valid(self):
        """Test all findings use valid severity levels."""
        scanner = ReliabilityScanner()

        valid_severities = ["low", "medium", "high", "critical"]

        findings = [
            scanner._create_single_az_rds_finding("db1", "postgres", "123456789012"),
            scanner._create_backup_configuration_finding(
                "db2", 0, "mysql", "123456789012"
            ),
            scanner._create_missing_health_check_finding(
                "lb1", "application", "123456789012"
            ),
            scanner._create_no_snapshot_finding("vol-123", 100, "123456789012"),
            scanner._create_no_auto_scaling_finding(
                "i-123", "t3.large", "web-server", "123456789012"
            ),
        ]

        for finding in findings:
            assert finding["severity"] in valid_severities

    def test_all_finding_types_are_valid(self):
        """Test all findings use valid finding types."""
        scanner = ReliabilityScanner()

        valid_finding_types = [
            "single_point_of_failure",
            "backup_configuration",
            "health_check",
        ]

        findings = [
            scanner._create_single_az_rds_finding("db1", "postgres", "123456789012"),
            scanner._create_backup_configuration_finding(
                "db2", 0, "mysql", "123456789012"
            ),
            scanner._create_missing_health_check_finding(
                "lb1", "application", "123456789012"
            ),
            scanner._create_no_snapshot_finding("vol-123", 100, "123456789012"),
            scanner._create_no_auto_scaling_finding(
                "i-123", "t3.large", "web-server", "123456789012"
            ),
        ]

        for finding in findings:
            assert finding["finding_type"] in valid_finding_types
