"""
Unit tests for CostExplorerScanner - Pure logic tests only.

These tests verify scanner logic WITHOUT mocking AWS services.
AWS interaction tests are in tests/integration/ using LocalStack.

Testing Strategy:
- Unit tests: Test internal logic (finding creation, severity calculation)
- Integration tests: Test actual AWS API interactions via LocalStack
"""

import pytest

from cloud_optimizer.integrations.aws.cost import CostExplorerScanner


class TestCostExplorerScannerInitialization:
    """Tests for CostExplorerScanner initialization and configuration."""

    def test_scanner_name(self):
        """Test scanner returns correct name."""
        scanner = CostExplorerScanner()
        assert scanner.get_scanner_name() == "CostExplorerScanner"

    def test_scanner_default_region(self):
        """Test scanner uses default region."""
        scanner = CostExplorerScanner()
        assert scanner.region == "us-east-1"

    def test_scanner_custom_region(self):
        """Test scanner accepts custom region."""
        scanner = CostExplorerScanner(region="eu-west-1")
        assert scanner.region == "eu-west-1"

    def test_thresholds_defined(self):
        """Test thresholds are properly defined."""
        assert CostExplorerScanner.ANOMALY_PERCENTAGE_THRESHOLD == 20
        assert CostExplorerScanner.IDLE_DAYS_THRESHOLD == 14


class TestCostAnomalyFinding:
    """Tests for cost anomaly finding creation."""

    def test_create_cost_anomaly_critical_severity(self):
        """Test critical severity for high impact anomalies."""
        scanner = CostExplorerScanner()
        anomaly = {
            "AnomalyId": "test-anomaly-123",
            "Impact": {"TotalImpact": 1500.0},
            "RootCauses": [{"Service": "AmazonEC2", "Region": "us-east-1"}],
        }

        finding = scanner._create_cost_anomaly_finding(
            anomaly_id="test-anomaly-123",
            anomaly=anomaly,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "cost_anomaly"
        assert finding["severity"] == "critical"
        assert "$1500.00" in finding["title"]
        assert "AmazonEC2" in finding["description"]
        assert finding["metadata"]["total_impact"] == 1500.0

    def test_create_cost_anomaly_high_severity(self):
        """Test high severity for medium impact anomalies."""
        scanner = CostExplorerScanner()
        anomaly = {
            "AnomalyId": "test-anomaly-456",
            "Impact": {"TotalImpact": 750.0},
            "RootCauses": [],
        }

        finding = scanner._create_cost_anomaly_finding(
            anomaly_id="test-anomaly-456",
            anomaly=anomaly,
            account_id="123456789012",
        )

        assert finding["severity"] == "high"
        assert "$750.00" in finding["title"]

    def test_create_cost_anomaly_medium_severity(self):
        """Test medium severity for moderate impact anomalies."""
        scanner = CostExplorerScanner()
        anomaly = {
            "AnomalyId": "test-anomaly-789",
            "Impact": {"TotalImpact": 250.0},
            "RootCauses": [],
        }

        finding = scanner._create_cost_anomaly_finding(
            anomaly_id="test-anomaly-789",
            anomaly=anomaly,
            account_id="123456789012",
        )

        assert finding["severity"] == "medium"

    def test_create_cost_anomaly_low_severity(self):
        """Test low severity for small impact anomalies."""
        scanner = CostExplorerScanner()
        anomaly = {
            "AnomalyId": "test-anomaly-abc",
            "Impact": {"TotalImpact": 50.0},
            "RootCauses": [],
        }

        finding = scanner._create_cost_anomaly_finding(
            anomaly_id="test-anomaly-abc",
            anomaly=anomaly,
            account_id="123456789012",
        )

        assert finding["severity"] == "low"


class TestRIRecommendationFinding:
    """Tests for RI recommendation finding creation."""

    def test_create_ri_recommendation_finding(self):
        """Test RI recommendation finding has correct structure."""
        scanner = CostExplorerScanner()
        detail = {
            "EstimatedMonthlySavingsAmount": "150.00",
            "UpfrontCost": "0",
            "RecommendedNumberOfInstancesToPurchase": "3",
        }

        finding = scanner._create_ri_recommendation_finding(
            instance_type="m5.large",
            detail=detail,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "reserved_instance_recommendation"
        assert finding["severity"] == "medium"
        assert "m5.large" in finding["title"]
        assert "$150.00/month" in finding["title"]
        assert finding["metadata"]["instance_type"] == "m5.large"
        assert finding["metadata"]["estimated_monthly_savings"] == 150.0
        assert finding["metadata"]["recommended_count"] == 3

    def test_ri_recommendation_includes_remediation(self):
        """Test RI recommendation includes remediation steps."""
        scanner = CostExplorerScanner()
        detail = {
            "EstimatedMonthlySavingsAmount": "200.00",
            "UpfrontCost": "0",
            "RecommendedNumberOfInstancesToPurchase": "2",
        }

        finding = scanner._create_ri_recommendation_finding(
            instance_type="c5.xlarge",
            detail=detail,
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "c5.xlarge" in finding["remediation"]
        assert "Reserved Instance" in finding["remediation"]


class TestRightsizingFinding:
    """Tests for rightsizing recommendation finding creation."""

    def test_create_rightsizing_finding(self):
        """Test rightsizing finding has correct structure."""
        scanner = CostExplorerScanner()

        finding = scanner._create_rightsizing_finding(
            resource_id="i-0123456789abcdef0",
            current_type="m5.2xlarge",
            target_type="m5.xlarge",
            estimated_savings=75.50,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "rightsizing_recommendation"
        assert finding["severity"] == "medium"
        assert "i-0123456789abcdef0" in finding["title"]
        assert "m5.2xlarge -> m5.xlarge" in finding["title"]
        assert finding["resource_type"] == "ec2_instance"
        assert finding["metadata"]["current_type"] == "m5.2xlarge"
        assert finding["metadata"]["target_type"] == "m5.xlarge"
        assert finding["metadata"]["estimated_monthly_savings"] == 75.50

    def test_rightsizing_includes_remediation(self):
        """Test rightsizing finding includes remediation steps."""
        scanner = CostExplorerScanner()

        finding = scanner._create_rightsizing_finding(
            resource_id="i-test123",
            current_type="t3.large",
            target_type="t3.medium",
            estimated_savings=25.00,
            account_id="123456789012",
        )

        assert "Stop the instance" in finding["remediation"]
        assert "change instance type" in finding["remediation"]


class TestIdleResourceFinding:
    """Tests for idle resource finding creation."""

    def test_create_idle_ebs_volume_finding(self):
        """Test idle EBS volume finding has correct structure."""
        scanner = CostExplorerScanner()

        finding = scanner._create_idle_resource_finding(
            resource_id="vol-0123456789abcdef0",
            resource_type="ebs_volume",
            days_idle=30,
            size_gb=100,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "idle_resource"
        assert finding["severity"] == "low"
        assert "vol-0123456789abcdef0" in finding["title"]
        assert "100 GB" in finding["title"]
        assert "30 days" in finding["title"]
        assert finding["resource_type"] == "ebs_volume"
        assert finding["metadata"]["days_idle"] == 30
        assert finding["metadata"]["size_gb"] == 100
        # Estimated cost: 100 GB * $0.10 = $10.00
        assert finding["metadata"]["estimated_monthly_cost"] == 10.0

    def test_idle_ebs_includes_remediation(self):
        """Test idle EBS finding includes remediation steps."""
        scanner = CostExplorerScanner()

        finding = scanner._create_idle_resource_finding(
            resource_id="vol-test456",
            resource_type="ebs_volume",
            days_idle=45,
            size_gb=50,
            account_id="123456789012",
        )

        assert "snapshot" in finding["remediation"].lower()
        assert "delete" in finding["remediation"].lower()


class TestIdleEIPFinding:
    """Tests for idle Elastic IP finding creation."""

    def test_create_idle_eip_finding(self):
        """Test idle EIP finding has correct structure."""
        scanner = CostExplorerScanner()

        finding = scanner._create_idle_eip_finding(
            allocation_id="eipalloc-0123456789abcdef0",
            public_ip="203.0.113.25",
            account_id="123456789012",
        )

        assert finding["finding_type"] == "idle_resource"
        assert finding["severity"] == "low"
        assert "203.0.113.25" in finding["title"]
        assert finding["resource_type"] == "elastic_ip"
        assert finding["metadata"]["public_ip"] == "203.0.113.25"
        assert finding["metadata"]["estimated_monthly_cost"] == 3.60

    def test_idle_eip_includes_remediation(self):
        """Test idle EIP finding includes remediation steps."""
        scanner = CostExplorerScanner()

        finding = scanner._create_idle_eip_finding(
            allocation_id="eipalloc-test",
            public_ip="198.51.100.10",
            account_id="123456789012",
        )

        assert (
            "attach" in finding["remediation"].lower()
            or "release" in finding["remediation"].lower()
        )
