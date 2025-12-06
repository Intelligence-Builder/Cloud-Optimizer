"""Type definitions for CloudWatch metrics.

Issue #166: Application metrics with CloudWatch Metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MetricUnit(str, Enum):
    """CloudWatch metric units."""

    # Count units
    COUNT = "Count"
    COUNT_PER_SECOND = "Count/Second"

    # Time units
    SECONDS = "Seconds"
    MILLISECONDS = "Milliseconds"
    MICROSECONDS = "Microseconds"

    # Size units
    BYTES = "Bytes"
    KILOBYTES = "Kilobytes"
    MEGABYTES = "Megabytes"
    GIGABYTES = "Gigabytes"
    TERABYTES = "Terabytes"

    # Data rate units
    BYTES_PER_SECOND = "Bytes/Second"
    KILOBYTES_PER_SECOND = "Kilobytes/Second"
    MEGABYTES_PER_SECOND = "Megabytes/Second"

    # Percentage
    PERCENT = "Percent"

    # Dimensionless
    NONE = "None"


@dataclass
class MetricDimension:
    """A CloudWatch metric dimension."""

    name: str
    value: str

    def to_dict(self) -> dict[str, str]:
        """Convert to CloudWatch API format."""
        return {"Name": self.name, "Value": self.value}


@dataclass
class MetricDataPoint:
    """A single metric data point for CloudWatch."""

    metric_name: str
    value: float
    unit: MetricUnit = MetricUnit.COUNT
    dimensions: list[MetricDimension] = field(default_factory=list)
    timestamp: Optional[datetime] = None
    storage_resolution: int = 60  # Standard resolution (1 minute)

    def to_cloudwatch_format(self, namespace: str) -> dict:
        """Convert to CloudWatch PutMetricData format."""
        data: dict = {
            "MetricName": self.metric_name,
            "Value": self.value,
            "Unit": self.unit.value,
            "StorageResolution": self.storage_resolution,
        }

        if self.dimensions:
            data["Dimensions"] = [d.to_dict() for d in self.dimensions]

        if self.timestamp:
            data["Timestamp"] = self.timestamp

        return data


# Pre-defined dimension names for consistency
class DimensionName:
    """Standard dimension names for Cloud Optimizer metrics."""

    ENVIRONMENT = "Environment"
    SERVICE = "Service"
    ENDPOINT = "Endpoint"
    METHOD = "Method"
    STATUS_CODE = "StatusCode"
    SCANNER_TYPE = "ScannerType"
    SEVERITY = "Severity"
    FINDING_TYPE = "FindingType"
    ACCOUNT_ID = "AccountId"
    REGION = "Region"
    RESOURCE_TYPE = "ResourceType"
    ERROR_TYPE = "ErrorType"
    OPERATION = "Operation"


# Pre-defined metric names for consistency
class MetricName:
    """Standard metric names for Cloud Optimizer."""

    # API Metrics
    REQUEST_COUNT = "RequestCount"
    REQUEST_LATENCY = "RequestLatency"
    REQUEST_ERRORS = "RequestErrors"
    REQUEST_SUCCESS = "RequestSuccess"

    # Scanner Metrics
    SCAN_DURATION = "ScanDuration"
    SCAN_COUNT = "ScanCount"
    SCAN_ERRORS = "ScanErrors"
    RESOURCES_SCANNED = "ResourcesScanned"

    # Finding Metrics
    FINDINGS_COUNT = "FindingsCount"
    FINDINGS_BY_SEVERITY = "FindingsBySeverity"
    CRITICAL_FINDINGS = "CriticalFindings"
    HIGH_FINDINGS = "HighFindings"

    # Business Metrics
    ACTIVE_USERS = "ActiveUsers"
    TRIAL_REGISTRATIONS = "TrialRegistrations"
    RECOMMENDATIONS_GENERATED = "RecommendationsGenerated"
    POTENTIAL_SAVINGS = "PotentialSavings"

    # Performance Metrics
    DATABASE_LATENCY = "DatabaseLatency"
    CACHE_HIT_RATE = "CacheHitRate"
    QUEUE_DEPTH = "QueueDepth"
    MEMORY_USAGE = "MemoryUsage"
    CPU_USAGE = "CPUUsage"

    # SLI Metrics
    AVAILABILITY = "Availability"
    ERROR_RATE = "ErrorRate"
    P99_LATENCY = "P99Latency"
    P95_LATENCY = "P95Latency"
