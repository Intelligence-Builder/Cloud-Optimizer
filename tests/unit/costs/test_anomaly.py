"""Unit tests for cost anomaly detection.

Issue #169: Cost monitoring and budgets.
"""

from datetime import datetime, timezone

import pytest

from cloud_optimizer.costs.anomaly import AnomalySeverity, CostAnomaly


class TestAnomalySeverity:
    """Test AnomalySeverity enum."""

    def test_low_severity(self) -> None:
        """Test LOW severity value."""
        assert AnomalySeverity.LOW.value == "low"

    def test_medium_severity(self) -> None:
        """Test MEDIUM severity value."""
        assert AnomalySeverity.MEDIUM.value == "medium"

    def test_high_severity(self) -> None:
        """Test HIGH severity value."""
        assert AnomalySeverity.HIGH.value == "high"

    def test_critical_severity(self) -> None:
        """Test CRITICAL severity value."""
        assert AnomalySeverity.CRITICAL.value == "critical"


class TestCostAnomaly:
    """Test CostAnomaly dataclass."""

    def test_default_values(self) -> None:
        """Test default anomaly values."""
        anomaly = CostAnomaly(anomaly_id="test-123", service="EC2")
        assert anomaly.anomaly_id == "test-123"
        assert anomaly.service == "EC2"
        assert anomaly.region is None
        assert anomaly.start_date is None
        assert anomaly.end_date is None
        assert anomaly.expected_cost == 0.0
        assert anomaly.actual_cost == 0.0
        assert anomaly.impact == 0.0
        assert anomaly.impact_percentage == 0.0
        assert anomaly.severity == AnomalySeverity.LOW
        assert anomaly.root_causes == []
        assert anomaly.is_resolved is False

    def test_anomaly_with_costs(self) -> None:
        """Test anomaly with cost data."""
        anomaly = CostAnomaly(
            anomaly_id="cost-anomaly-1",
            service="Lambda",
            expected_cost=100.0,
            actual_cost=250.0,
            impact=150.0,
            impact_percentage=150.0,
        )
        assert anomaly.expected_cost == 100.0
        assert anomaly.actual_cost == 250.0
        assert anomaly.impact == 150.0
        assert anomaly.impact_percentage == 150.0

    def test_anomaly_with_region(self) -> None:
        """Test anomaly with region specified."""
        anomaly = CostAnomaly(
            anomaly_id="regional-1",
            service="RDS",
            region="us-east-1",
        )
        assert anomaly.region == "us-east-1"

    def test_anomaly_with_dates(self) -> None:
        """Test anomaly with start and end dates."""
        now = datetime.now(timezone.utc)
        anomaly = CostAnomaly(
            anomaly_id="dated-1",
            service="S3",
            start_date=now,
            end_date=now,
        )
        assert anomaly.start_date == now
        assert anomaly.end_date == now

    def test_critical_severity_anomaly(self) -> None:
        """Test anomaly with critical severity."""
        anomaly = CostAnomaly(
            anomaly_id="critical-1",
            service="EC2",
            impact=1500.0,
            impact_percentage=200.0,
            severity=AnomalySeverity.CRITICAL,
        )
        assert anomaly.severity == AnomalySeverity.CRITICAL

    def test_resolved_anomaly(self) -> None:
        """Test resolved anomaly."""
        anomaly = CostAnomaly(
            anomaly_id="resolved-1",
            service="CloudWatch",
            is_resolved=True,
        )
        assert anomaly.is_resolved is True

    def test_anomaly_with_root_causes(self) -> None:
        """Test anomaly with root causes."""
        root_causes = [
            {"service": "EC2", "region": "us-east-1", "usage_type": "BoxUsage"},
            {"service": "EC2", "region": "us-west-2", "usage_type": "BoxUsage"},
        ]
        anomaly = CostAnomaly(
            anomaly_id="multi-cause-1",
            service="EC2",
            root_causes=root_causes,
        )
        assert len(anomaly.root_causes) == 2
        assert anomaly.root_causes[0]["region"] == "us-east-1"

    def test_high_impact_anomaly(self) -> None:
        """Test high impact anomaly."""
        anomaly = CostAnomaly(
            anomaly_id="high-impact-1",
            service="SageMaker",
            expected_cost=500.0,
            actual_cost=1000.0,
            impact=500.0,
            impact_percentage=100.0,
            severity=AnomalySeverity.HIGH,
        )
        assert anomaly.impact == 500.0
        assert anomaly.severity == AnomalySeverity.HIGH

    def test_medium_severity_anomaly(self) -> None:
        """Test medium severity anomaly."""
        anomaly = CostAnomaly(
            anomaly_id="medium-1",
            service="DynamoDB",
            impact=150.0,
            impact_percentage=30.0,
            severity=AnomalySeverity.MEDIUM,
        )
        assert anomaly.severity == AnomalySeverity.MEDIUM

    def test_anomaly_string_representation(self) -> None:
        """Test anomaly can be represented as string."""
        anomaly = CostAnomaly(
            anomaly_id="str-test-1",
            service="ElastiCache",
        )
        # Should not raise any exceptions
        str_repr = str(anomaly)
        assert "str-test-1" in str_repr
        assert "ElastiCache" in str_repr
