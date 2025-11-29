"""
Unit tests for CloudWatchScanner - Pure logic tests only.

These tests verify scanner logic WITHOUT mocking AWS services.
AWS interaction tests are in tests/integration/ using LocalStack.

Testing Strategy:
- Unit tests: Test internal logic (finding creation, severity calculation)
- Integration tests: Test actual AWS API interactions via LocalStack
"""

from cloud_optimizer.integrations.aws.performance import CloudWatchScanner


class TestCloudWatchScannerInitialization:
    """Tests for CloudWatchScanner initialization and configuration."""

    def test_scanner_name(self):
        """Test scanner returns correct name."""
        scanner = CloudWatchScanner()
        assert scanner.get_scanner_name() == "CloudWatchScanner"

    def test_scanner_default_region(self):
        """Test scanner uses default region."""
        scanner = CloudWatchScanner()
        assert scanner.region == "us-east-1"

    def test_scanner_custom_region(self):
        """Test scanner accepts custom region."""
        scanner = CloudWatchScanner(region="eu-west-1")
        assert scanner.region == "eu-west-1"

    def test_thresholds_defined(self):
        """Test performance thresholds are properly defined."""
        assert CloudWatchScanner.CPU_HIGH_THRESHOLD == 80.0
        assert CloudWatchScanner.CPU_CRITICAL_THRESHOLD == 95.0
        assert CloudWatchScanner.MEMORY_HIGH_THRESHOLD == 85.0
        assert CloudWatchScanner.MEMORY_CRITICAL_THRESHOLD == 95.0
        assert CloudWatchScanner.DISK_QUEUE_THRESHOLD == 10.0
        assert CloudWatchScanner.NETWORK_ERROR_THRESHOLD == 100
        assert CloudWatchScanner.LAMBDA_ERROR_RATE_THRESHOLD == 5.0
        assert CloudWatchScanner.LAMBDA_THROTTLE_THRESHOLD == 1
        assert CloudWatchScanner.RDS_CPU_THRESHOLD == 80.0
        assert CloudWatchScanner.RDS_CONNECTIONS_THRESHOLD == 0.9


class TestCPUBottleneckFinding:
    """Tests for CPU bottleneck finding creation."""

    def test_create_cpu_bottleneck_critical_severity(self):
        """Test critical severity for very high CPU usage."""
        scanner = CloudWatchScanner()

        finding = scanner._create_cpu_bottleneck_finding(
            resource_id="i-0123456789abcdef0",
            resource_name="web-server-1",
            instance_type="t3.medium",
            avg_cpu=96.5,
            max_cpu=99.2,
            severity="critical",
            account_id="123456789012",
        )

        assert finding["finding_type"] == "performance_bottleneck"
        assert finding["severity"] == "critical"
        assert "web-server-1" in finding["title"]
        assert "96.5%" in finding["title"]
        assert finding["resource_type"] == "ec2_instance"
        assert finding["metadata"]["avg_cpu"] == 96.5
        assert finding["metadata"]["max_cpu"] == 99.2
        assert finding["metadata"]["metric_type"] == "cpu_utilization"

    def test_create_cpu_bottleneck_high_severity(self):
        """Test high severity for moderately high CPU usage."""
        scanner = CloudWatchScanner()

        finding = scanner._create_cpu_bottleneck_finding(
            resource_id="i-test123",
            resource_name="app-server-2",
            instance_type="m5.large",
            avg_cpu=85.0,
            max_cpu=92.0,
            severity="high",
            account_id="123456789012",
        )

        assert finding["severity"] == "high"
        assert "85.0%" in finding["title"]
        assert "app-server-2" in finding["title"]

    def test_cpu_bottleneck_includes_remediation(self):
        """Test CPU bottleneck finding includes remediation steps."""
        scanner = CloudWatchScanner()

        finding = scanner._create_cpu_bottleneck_finding(
            resource_id="i-abc123",
            resource_name="test-server",
            instance_type="t3.small",
            avg_cpu=88.0,
            max_cpu=95.0,
            severity="high",
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert (
            "upgrading" in finding["remediation"].lower()
            or "upgrade" in finding["remediation"].lower()
        )
        assert "test-server" in finding["remediation"]


class TestDiskQueueFinding:
    """Tests for disk queue finding creation."""

    def test_create_disk_queue_critical_severity(self):
        """Test critical severity for very high disk queue depth."""
        scanner = CloudWatchScanner()

        finding = scanner._create_disk_queue_finding(
            resource_id="i-disk123",
            resource_name="db-server",
            instance_type="m5.xlarge",
            avg_queue=25.5,
            max_queue=40.0,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "performance_bottleneck"
        assert finding["severity"] == "critical"
        assert "db-server" in finding["title"]
        assert "25.5" in finding["title"]
        assert finding["metadata"]["avg_queue"] == 25.5
        assert finding["metadata"]["max_queue"] == 40.0
        assert finding["metadata"]["metric_type"] == "disk_queue_depth"

    def test_create_disk_queue_high_severity(self):
        """Test high severity for moderately high disk queue depth."""
        scanner = CloudWatchScanner()

        finding = scanner._create_disk_queue_finding(
            resource_id="i-disk456",
            resource_name="app-server",
            instance_type="t3.medium",
            avg_queue=15.0,
            max_queue=20.0,
            account_id="123456789012",
        )

        assert finding["severity"] == "high"
        assert "15.0" in finding["title"]

    def test_disk_queue_includes_remediation(self):
        """Test disk queue finding includes remediation steps."""
        scanner = CloudWatchScanner()

        finding = scanner._create_disk_queue_finding(
            resource_id="i-disk789",
            resource_name="storage-server",
            instance_type="m5.large",
            avg_queue=12.0,
            max_queue=18.0,
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "iops" in finding["remediation"].lower()
        assert "ebs" in finding["remediation"].lower()


class TestNetworkIssueFinding:
    """Tests for network issue finding creation."""

    def test_create_network_issue_high_severity(self):
        """Test high severity for many network errors."""
        scanner = CloudWatchScanner()

        finding = scanner._create_network_issue_finding(
            resource_id="i-net123",
            resource_name="api-server",
            instance_type="c5.large",
            total_errors=1500.0,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "latency_issue"
        assert finding["severity"] == "high"
        assert "api-server" in finding["title"]
        assert "1500" in finding["title"]
        assert finding["metadata"]["total_errors"] == 1500.0
        assert finding["metadata"]["metric_type"] == "network_packets_dropped"

    def test_create_network_issue_medium_severity(self):
        """Test medium severity for moderate network errors."""
        scanner = CloudWatchScanner()

        finding = scanner._create_network_issue_finding(
            resource_id="i-net456",
            resource_name="web-server",
            instance_type="t3.medium",
            total_errors=500.0,
            account_id="123456789012",
        )

        assert finding["severity"] == "medium"
        assert "500" in finding["title"]

    def test_network_issue_includes_remediation(self):
        """Test network issue finding includes remediation steps."""
        scanner = CloudWatchScanner()

        finding = scanner._create_network_issue_finding(
            resource_id="i-net789",
            resource_name="compute-server",
            instance_type="m5.large",
            total_errors=250.0,
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "network" in finding["remediation"].lower()


class TestLambdaErrorFinding:
    """Tests for Lambda error finding creation."""

    def test_create_lambda_error_critical_severity(self):
        """Test critical severity for very high error rate."""
        scanner = CloudWatchScanner()

        finding = scanner._create_lambda_error_finding(
            function_name="data-processor",
            error_rate=15.5,
            total_errors=155.0,
            total_invocations=1000.0,
            memory_size=512,
            timeout=30,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "performance_bottleneck"
        assert finding["severity"] == "critical"
        assert "data-processor" in finding["title"]
        assert "15.5%" in finding["title"]
        assert finding["resource_type"] == "lambda_function"
        assert finding["metadata"]["error_rate"] == 15.5
        assert finding["metadata"]["total_errors"] == 155.0
        assert finding["metadata"]["memory_size"] == 512
        assert finding["metadata"]["timeout"] == 30
        assert finding["metadata"]["metric_type"] == "lambda_errors"

    def test_create_lambda_error_high_severity(self):
        """Test high severity for moderate error rate."""
        scanner = CloudWatchScanner()

        finding = scanner._create_lambda_error_finding(
            function_name="api-handler",
            error_rate=7.5,
            total_errors=75.0,
            total_invocations=1000.0,
            memory_size=256,
            timeout=10,
            account_id="123456789012",
        )

        assert finding["severity"] == "high"
        assert "7.5%" in finding["title"]

    def test_lambda_error_includes_remediation(self):
        """Test Lambda error finding includes remediation steps."""
        scanner = CloudWatchScanner()

        finding = scanner._create_lambda_error_finding(
            function_name="test-function",
            error_rate=8.0,
            total_errors=80.0,
            total_invocations=1000.0,
            memory_size=128,
            timeout=5,
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "cloudwatch logs" in finding["remediation"].lower()
        assert "test-function" in finding["remediation"]


class TestLambdaThrottleFinding:
    """Tests for Lambda throttle finding creation."""

    def test_create_lambda_throttle_critical_severity(self):
        """Test critical severity for high throttle count."""
        scanner = CloudWatchScanner()

        finding = scanner._create_lambda_throttle_finding(
            function_name="high-traffic-api",
            total_throttles=250.0,
            memory_size=512,
            timeout=30,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "scaling_recommendation"
        assert finding["severity"] == "critical"
        assert "high-traffic-api" in finding["title"]
        assert "250" in finding["title"]
        assert finding["metadata"]["total_throttles"] == 250.0
        assert finding["metadata"]["metric_type"] == "lambda_throttles"

    def test_create_lambda_throttle_high_severity(self):
        """Test high severity for moderate throttle count."""
        scanner = CloudWatchScanner()

        finding = scanner._create_lambda_throttle_finding(
            function_name="batch-processor",
            total_throttles=50.0,
            memory_size=256,
            timeout=60,
            account_id="123456789012",
        )

        assert finding["severity"] == "high"
        assert "50" in finding["title"]

    def test_lambda_throttle_includes_remediation(self):
        """Test Lambda throttle finding includes remediation steps."""
        scanner = CloudWatchScanner()

        finding = scanner._create_lambda_throttle_finding(
            function_name="test-function",
            total_throttles=10.0,
            memory_size=128,
            timeout=10,
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "concurrency" in finding["remediation"].lower()
        assert "test-function" in finding["remediation"]


class TestRDSCPUFinding:
    """Tests for RDS CPU finding creation."""

    def test_create_rds_cpu_critical_severity(self):
        """Test critical severity for very high RDS CPU."""
        scanner = CloudWatchScanner()

        finding = scanner._create_rds_cpu_finding(
            db_identifier="production-db",
            db_class="db.m5.large",
            engine="postgres",
            avg_cpu=92.5,
            max_cpu=98.0,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "performance_bottleneck"
        assert finding["severity"] == "critical"
        assert "production-db" in finding["title"]
        assert "92.5%" in finding["title"]
        assert finding["resource_type"] == "rds_instance"
        assert finding["metadata"]["db_class"] == "db.m5.large"
        assert finding["metadata"]["engine"] == "postgres"
        assert finding["metadata"]["avg_cpu"] == 92.5
        assert finding["metadata"]["max_cpu"] == 98.0
        assert finding["metadata"]["metric_type"] == "rds_cpu_utilization"

    def test_create_rds_cpu_high_severity(self):
        """Test high severity for moderately high RDS CPU."""
        scanner = CloudWatchScanner()

        finding = scanner._create_rds_cpu_finding(
            db_identifier="staging-db",
            db_class="db.t3.medium",
            engine="mysql",
            avg_cpu=85.0,
            max_cpu=89.0,
            account_id="123456789012",
        )

        assert finding["severity"] == "high"
        assert "85.0%" in finding["title"]

    def test_rds_cpu_includes_remediation(self):
        """Test RDS CPU finding includes remediation steps."""
        scanner = CloudWatchScanner()

        finding = scanner._create_rds_cpu_finding(
            db_identifier="test-db",
            db_class="db.t3.small",
            engine="postgres",
            avg_cpu=87.0,
            max_cpu=93.0,
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert (
            "optimize" in finding["remediation"].lower()
            or "queries" in finding["remediation"].lower()
        )


class TestRDSConnectionsFinding:
    """Tests for RDS connections finding creation."""

    def test_create_rds_connections_critical_severity(self):
        """Test critical severity for very high connection usage."""
        scanner = CloudWatchScanner()

        finding = scanner._create_rds_connections_finding(
            db_identifier="production-db",
            db_class="db.m5.large",
            engine="postgres",
            avg_connections=950.0,
            max_connections=1000,
            connection_usage=0.95,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "scaling_recommendation"
        assert finding["severity"] == "critical"
        assert "production-db" in finding["title"]
        assert "95%" in finding["title"]
        assert finding["metadata"]["avg_connections"] == 950.0
        assert finding["metadata"]["max_connections"] == 1000
        assert finding["metadata"]["connection_usage"] == 0.95
        assert finding["metadata"]["metric_type"] == "rds_connections"

    def test_create_rds_connections_high_severity(self):
        """Test high severity for moderately high connection usage."""
        scanner = CloudWatchScanner()

        finding = scanner._create_rds_connections_finding(
            db_identifier="staging-db",
            db_class="db.t3.medium",
            engine="mysql",
            avg_connections=450.0,
            max_connections=500,
            connection_usage=0.90,
            account_id="123456789012",
        )

        assert finding["severity"] == "high"
        assert "90%" in finding["title"]

    def test_rds_connections_includes_remediation(self):
        """Test RDS connections finding includes remediation steps."""
        scanner = CloudWatchScanner()

        finding = scanner._create_rds_connections_finding(
            db_identifier="test-db",
            db_class="db.t3.small",
            engine="postgres",
            avg_connections=180.0,
            max_connections=200,
            connection_usage=0.90,
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert (
            "connection pooling" in finding["remediation"].lower()
            or "pooling" in finding["remediation"].lower()
        )


class TestRDSMaxConnectionsEstimate:
    """Tests for RDS max connections estimation."""

    def test_estimate_micro_instance(self):
        """Test max connections estimate for micro instance."""
        scanner = CloudWatchScanner()
        max_connections = scanner._estimate_rds_max_connections("db.t3.micro")
        assert max_connections == 100

    def test_estimate_small_instance(self):
        """Test max connections estimate for small instance."""
        scanner = CloudWatchScanner()
        max_connections = scanner._estimate_rds_max_connections("db.t3.small")
        assert max_connections == 200

    def test_estimate_medium_instance(self):
        """Test max connections estimate for medium instance."""
        scanner = CloudWatchScanner()
        max_connections = scanner._estimate_rds_max_connections("db.m5.medium")
        assert max_connections == 500

    def test_estimate_large_instance(self):
        """Test max connections estimate for large instance."""
        scanner = CloudWatchScanner()
        max_connections = scanner._estimate_rds_max_connections("db.m5.large")
        assert max_connections == 1000

    def test_estimate_xlarge_instance(self):
        """Test max connections estimate for xlarge instance."""
        scanner = CloudWatchScanner()
        max_connections = scanner._estimate_rds_max_connections("db.m5.xlarge")
        assert max_connections == 2000

    def test_estimate_2xlarge_instance(self):
        """Test max connections estimate for 2xlarge instance."""
        scanner = CloudWatchScanner()
        max_connections = scanner._estimate_rds_max_connections("db.m5.2xlarge")
        assert max_connections == 3000

    def test_estimate_4xlarge_instance(self):
        """Test max connections estimate for 4xlarge instance."""
        scanner = CloudWatchScanner()
        max_connections = scanner._estimate_rds_max_connections("db.m5.4xlarge")
        assert max_connections == 5000

    def test_estimate_unknown_instance(self):
        """Test max connections estimate for unknown instance type."""
        scanner = CloudWatchScanner()
        max_connections = scanner._estimate_rds_max_connections("db.custom.unknown")
        assert max_connections == 500  # Default fallback


class TestFindingStructure:
    """Tests for finding structure consistency."""

    def test_all_findings_have_required_fields(self):
        """Test that all finding types include required fields."""
        scanner = CloudWatchScanner()

        # Test CPU bottleneck finding
        cpu_finding = scanner._create_cpu_bottleneck_finding(
            resource_id="i-test",
            resource_name="test",
            instance_type="t3.small",
            avg_cpu=85.0,
            max_cpu=95.0,
            severity="high",
            account_id="123456789012",
        )

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

        for field in required_fields:
            assert field in cpu_finding, f"Missing required field: {field}"

    def test_finding_metadata_structure(self):
        """Test that findings have properly structured metadata."""
        scanner = CloudWatchScanner()

        finding = scanner._create_lambda_error_finding(
            function_name="test-function",
            error_rate=10.0,
            total_errors=100.0,
            total_invocations=1000.0,
            memory_size=256,
            timeout=30,
            account_id="123456789012",
        )

        metadata = finding["metadata"]
        assert "metric_type" in metadata
        assert isinstance(metadata, dict)
