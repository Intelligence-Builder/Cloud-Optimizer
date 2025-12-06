"""CloudWatch Metrics module for Cloud Optimizer.

Issue #166: Application metrics with CloudWatch Metrics.
Provides direct CloudWatch API integration for custom metrics emission.
"""

from cloud_optimizer.metrics.service import (
    MetricsConfig,
    MetricsService,
    get_metrics_service,
)
from cloud_optimizer.metrics.decorators import (
    track_latency,
    track_errors,
    count_invocations,
)
from cloud_optimizer.metrics.types import (
    MetricUnit,
    MetricDimension,
    MetricDataPoint,
)

__all__ = [
    "MetricsConfig",
    "MetricsService",
    "get_metrics_service",
    "track_latency",
    "track_errors",
    "count_invocations",
    "MetricUnit",
    "MetricDimension",
    "MetricDataPoint",
]
