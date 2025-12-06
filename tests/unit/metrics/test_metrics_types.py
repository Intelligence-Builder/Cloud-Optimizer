"""Tests for CloudWatch metrics types.

Issue #166: Application metrics with CloudWatch Metrics.
"""

from datetime import datetime

import pytest

from cloud_optimizer.metrics.types import (
    DimensionName,
    MetricDataPoint,
    MetricDimension,
    MetricName,
    MetricUnit,
)


class TestMetricUnit:
    """Tests for MetricUnit enum."""

    def test_count_units(self) -> None:
        """Test count-related units."""
        assert MetricUnit.COUNT.value == "Count"
        assert MetricUnit.COUNT_PER_SECOND.value == "Count/Second"

    def test_time_units(self) -> None:
        """Test time-related units."""
        assert MetricUnit.SECONDS.value == "Seconds"
        assert MetricUnit.MILLISECONDS.value == "Milliseconds"
        assert MetricUnit.MICROSECONDS.value == "Microseconds"

    def test_size_units(self) -> None:
        """Test size-related units."""
        assert MetricUnit.BYTES.value == "Bytes"
        assert MetricUnit.KILOBYTES.value == "Kilobytes"
        assert MetricUnit.MEGABYTES.value == "Megabytes"
        assert MetricUnit.GIGABYTES.value == "Gigabytes"

    def test_percentage_unit(self) -> None:
        """Test percentage unit."""
        assert MetricUnit.PERCENT.value == "Percent"

    def test_none_unit(self) -> None:
        """Test dimensionless unit."""
        assert MetricUnit.NONE.value == "None"


class TestMetricDimension:
    """Tests for MetricDimension dataclass."""

    def test_creation(self) -> None:
        """Test dimension creation."""
        dim = MetricDimension("Environment", "production")
        assert dim.name == "Environment"
        assert dim.value == "production"

    def test_to_dict(self) -> None:
        """Test conversion to CloudWatch format."""
        dim = MetricDimension("Service", "cloud-optimizer")
        result = dim.to_dict()
        assert result == {"Name": "Service", "Value": "cloud-optimizer"}


class TestMetricDataPoint:
    """Tests for MetricDataPoint dataclass."""

    def test_creation_with_defaults(self) -> None:
        """Test data point creation with defaults."""
        point = MetricDataPoint(
            metric_name="TestMetric",
            value=42.0,
        )
        assert point.metric_name == "TestMetric"
        assert point.value == 42.0
        assert point.unit == MetricUnit.COUNT
        assert point.dimensions == []
        assert point.timestamp is None
        assert point.storage_resolution == 60

    def test_creation_with_all_fields(self) -> None:
        """Test data point creation with all fields."""
        timestamp = datetime.utcnow()
        dims = [MetricDimension("Env", "test")]
        point = MetricDataPoint(
            metric_name="CustomMetric",
            value=100.5,
            unit=MetricUnit.MILLISECONDS,
            dimensions=dims,
            timestamp=timestamp,
            storage_resolution=1,
        )
        assert point.metric_name == "CustomMetric"
        assert point.value == 100.5
        assert point.unit == MetricUnit.MILLISECONDS
        assert len(point.dimensions) == 1
        assert point.timestamp == timestamp
        assert point.storage_resolution == 1

    def test_to_cloudwatch_format_minimal(self) -> None:
        """Test conversion to CloudWatch format with minimal fields."""
        point = MetricDataPoint(
            metric_name="TestMetric",
            value=10.0,
        )
        result = point.to_cloudwatch_format("CloudOptimizer")

        assert result["MetricName"] == "TestMetric"
        assert result["Value"] == 10.0
        assert result["Unit"] == "Count"
        assert result["StorageResolution"] == 60
        assert "Dimensions" not in result

    def test_to_cloudwatch_format_with_dimensions(self) -> None:
        """Test conversion includes dimensions."""
        dims = [
            MetricDimension("Environment", "prod"),
            MetricDimension("Service", "api"),
        ]
        point = MetricDataPoint(
            metric_name="RequestCount",
            value=1.0,
            dimensions=dims,
        )
        result = point.to_cloudwatch_format("CloudOptimizer")

        assert "Dimensions" in result
        assert len(result["Dimensions"]) == 2
        assert result["Dimensions"][0] == {"Name": "Environment", "Value": "prod"}

    def test_to_cloudwatch_format_with_timestamp(self) -> None:
        """Test conversion includes timestamp."""
        timestamp = datetime(2024, 1, 15, 12, 0, 0)
        point = MetricDataPoint(
            metric_name="TestMetric",
            value=1.0,
            timestamp=timestamp,
        )
        result = point.to_cloudwatch_format("CloudOptimizer")

        assert result["Timestamp"] == timestamp


class TestDimensionName:
    """Tests for DimensionName constants."""

    def test_standard_dimensions(self) -> None:
        """Test standard dimension names are defined."""
        assert DimensionName.ENVIRONMENT == "Environment"
        assert DimensionName.SERVICE == "Service"
        assert DimensionName.ENDPOINT == "Endpoint"
        assert DimensionName.METHOD == "Method"
        assert DimensionName.STATUS_CODE == "StatusCode"
        assert DimensionName.SCANNER_TYPE == "ScannerType"
        assert DimensionName.SEVERITY == "Severity"
        assert DimensionName.FINDING_TYPE == "FindingType"
        assert DimensionName.ACCOUNT_ID == "AccountId"
        assert DimensionName.REGION == "Region"
        assert DimensionName.RESOURCE_TYPE == "ResourceType"
        assert DimensionName.ERROR_TYPE == "ErrorType"
        assert DimensionName.OPERATION == "Operation"


class TestMetricName:
    """Tests for MetricName constants."""

    def test_api_metrics(self) -> None:
        """Test API metric names."""
        assert MetricName.REQUEST_COUNT == "RequestCount"
        assert MetricName.REQUEST_LATENCY == "RequestLatency"
        assert MetricName.REQUEST_ERRORS == "RequestErrors"
        assert MetricName.REQUEST_SUCCESS == "RequestSuccess"

    def test_scanner_metrics(self) -> None:
        """Test scanner metric names."""
        assert MetricName.SCAN_DURATION == "ScanDuration"
        assert MetricName.SCAN_COUNT == "ScanCount"
        assert MetricName.SCAN_ERRORS == "ScanErrors"
        assert MetricName.RESOURCES_SCANNED == "ResourcesScanned"

    def test_finding_metrics(self) -> None:
        """Test finding metric names."""
        assert MetricName.FINDINGS_COUNT == "FindingsCount"
        assert MetricName.CRITICAL_FINDINGS == "CriticalFindings"
        assert MetricName.HIGH_FINDINGS == "HighFindings"

    def test_business_metrics(self) -> None:
        """Test business metric names."""
        assert MetricName.ACTIVE_USERS == "ActiveUsers"
        assert MetricName.TRIAL_REGISTRATIONS == "TrialRegistrations"
        assert MetricName.RECOMMENDATIONS_GENERATED == "RecommendationsGenerated"
        assert MetricName.POTENTIAL_SAVINGS == "PotentialSavings"

    def test_sli_metrics(self) -> None:
        """Test SLI metric names."""
        assert MetricName.AVAILABILITY == "Availability"
        assert MetricName.ERROR_RATE == "ErrorRate"
        assert MetricName.P99_LATENCY == "P99Latency"
        assert MetricName.P95_LATENCY == "P95Latency"
