"""CloudWatch Metrics Service for Cloud Optimizer.

Issue #166: Application metrics with CloudWatch Metrics.
Provides direct CloudWatch API integration with batching and async support.
"""

import asyncio
import atexit
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from cloud_optimizer.config import get_settings
from cloud_optimizer.logging.config import get_logger
from cloud_optimizer.metrics.types import (
    DimensionName,
    MetricDataPoint,
    MetricDimension,
    MetricUnit,
)

logger = get_logger(__name__)


@dataclass
class MetricsConfig:
    """Configuration for CloudWatch metrics service."""

    enabled: bool = True
    namespace: str = "CloudOptimizer"
    environment: str = "development"
    batch_size: int = 20  # CloudWatch limit is 1000 per request
    flush_interval_seconds: float = 60.0  # Flush every 60 seconds
    max_queue_size: int = 10000  # Max metrics to buffer
    async_mode: bool = True  # Publish metrics asynchronously
    default_dimensions: list[MetricDimension] = field(default_factory=list)
    high_resolution: bool = False  # 1-second resolution (costs more)

    def __post_init__(self) -> None:
        """Add default dimensions after init."""
        if not self.default_dimensions:
            self.default_dimensions = [
                MetricDimension(DimensionName.ENVIRONMENT, self.environment),
                MetricDimension(DimensionName.SERVICE, "cloud-optimizer"),
            ]


class MetricsService:
    """CloudWatch metrics service with batching and async support.

    Features:
    - Direct CloudWatch PutMetricData API calls
    - Automatic batching for efficiency
    - Async metric publishing (non-blocking)
    - Thread-safe metric queue
    - Automatic flush on shutdown
    - Graceful degradation when CloudWatch unavailable
    """

    def __init__(self, config: Optional[MetricsConfig] = None) -> None:
        """Initialize metrics service.

        Args:
            config: Optional MetricsConfig. Uses defaults if not provided.
        """
        self.config = config or MetricsConfig()
        self._queue: deque[MetricDataPoint] = deque(maxlen=self.config.max_queue_size)
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._client: Optional[boto3.client] = None
        self._initialized = False

        if self.config.enabled:
            self._initialize()

    def _initialize(self) -> None:
        """Initialize CloudWatch client and background flush thread."""
        try:
            self._client = boto3.client("cloudwatch")
            self._initialized = True

            if self.config.async_mode:
                self._start_flush_thread()

            # Register shutdown handler
            atexit.register(self._shutdown)

            logger.info(
                "metrics_service_initialized",
                namespace=self.config.namespace,
                async_mode=self.config.async_mode,
                batch_size=self.config.batch_size,
            )
        except Exception as e:
            logger.warning(
                "metrics_service_init_failed",
                error=str(e),
                message="Metrics will be logged only",
            )
            self._initialized = False

    def _start_flush_thread(self) -> None:
        """Start background thread for periodic metric flushing."""
        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            daemon=True,
            name="metrics-flush",
        )
        self._flush_thread.start()

    def _flush_loop(self) -> None:
        """Background loop that periodically flushes metrics."""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self.config.flush_interval_seconds)
            if not self._stop_event.is_set():
                self._flush()

    def _shutdown(self) -> None:
        """Graceful shutdown - flush remaining metrics."""
        logger.info("metrics_service_shutting_down")
        self._stop_event.set()
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5.0)
        self._flush()  # Final flush

    @property
    def enabled(self) -> bool:
        """Check if metrics service is enabled and initialized."""
        return self.config.enabled and self._initialized

    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: MetricUnit = MetricUnit.COUNT,
        dimensions: Optional[list[MetricDimension]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record a single metric.

        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: CloudWatch metric unit
            dimensions: Optional additional dimensions
            timestamp: Optional timestamp (defaults to now)
        """
        if not self.config.enabled:
            return

        # Combine default and custom dimensions
        all_dimensions = list(self.config.default_dimensions)
        if dimensions:
            all_dimensions.extend(dimensions)

        data_point = MetricDataPoint(
            metric_name=metric_name,
            value=value,
            unit=unit,
            dimensions=all_dimensions,
            timestamp=timestamp or datetime.utcnow(),
            storage_resolution=1 if self.config.high_resolution else 60,
        )

        # Log metric for CloudWatch Logs metric filters (backup)
        logger.debug(
            "metric_recorded",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit.value,
        )

        if self.config.async_mode:
            self._enqueue(data_point)
        else:
            self._publish([data_point])

    def put_metrics(self, metrics: list[MetricDataPoint]) -> None:
        """Record multiple metrics at once.

        Args:
            metrics: List of MetricDataPoint objects
        """
        if not self.config.enabled or not metrics:
            return

        # Add default dimensions to each metric
        for metric in metrics:
            metric.dimensions = list(self.config.default_dimensions) + metric.dimensions

        if self.config.async_mode:
            for metric in metrics:
                self._enqueue(metric)
        else:
            self._publish(metrics)

    def _enqueue(self, data_point: MetricDataPoint) -> None:
        """Add metric to queue for async publishing."""
        with self._lock:
            self._queue.append(data_point)

            # Auto-flush if batch size reached
            if len(self._queue) >= self.config.batch_size:
                self._flush()

    def _flush(self) -> None:
        """Flush queued metrics to CloudWatch."""
        if not self._initialized or not self._client:
            return

        metrics_to_publish: list[MetricDataPoint] = []

        with self._lock:
            while self._queue and len(metrics_to_publish) < self.config.batch_size:
                metrics_to_publish.append(self._queue.popleft())

        if metrics_to_publish:
            self._publish(metrics_to_publish)

    def _publish(self, metrics: list[MetricDataPoint]) -> None:
        """Publish metrics to CloudWatch.

        Args:
            metrics: List of metrics to publish
        """
        if not self._client or not metrics:
            return

        try:
            # Convert to CloudWatch format
            metric_data = [
                m.to_cloudwatch_format(self.config.namespace) for m in metrics
            ]

            # CloudWatch allows max 1000 metrics per request
            for i in range(0, len(metric_data), 1000):
                batch = metric_data[i : i + 1000]
                self._client.put_metric_data(
                    Namespace=self.config.namespace,
                    MetricData=batch,
                )

            logger.debug(
                "metrics_published",
                count=len(metrics),
                namespace=self.config.namespace,
            )

        except ClientError as e:
            logger.error(
                "metrics_publish_failed",
                error=str(e),
                count=len(metrics),
            )
        except Exception as e:
            logger.error(
                "metrics_publish_error",
                error=str(e),
                count=len(metrics),
            )

    # Convenience methods for common metrics
    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        """Record API request metrics.

        Args:
            endpoint: API endpoint path
            method: HTTP method
            status_code: Response status code
            latency_ms: Request latency in milliseconds
        """
        dimensions = [
            MetricDimension(DimensionName.ENDPOINT, endpoint),
            MetricDimension(DimensionName.METHOD, method),
            MetricDimension(DimensionName.STATUS_CODE, str(status_code)),
        ]

        # Record request count
        self.put_metric("RequestCount", 1, MetricUnit.COUNT, dimensions)

        # Record latency
        self.put_metric("RequestLatency", latency_ms, MetricUnit.MILLISECONDS, dimensions)

        # Record error if 5xx
        if status_code >= 500:
            self.put_metric("RequestErrors", 1, MetricUnit.COUNT, dimensions)

    def record_scan(
        self,
        scanner_type: str,
        duration_ms: float,
        resources_scanned: int,
        findings_count: int,
        error: Optional[str] = None,
    ) -> None:
        """Record scanner execution metrics.

        Args:
            scanner_type: Type of scanner (e.g., "iam", "s3", "lambda")
            duration_ms: Scan duration in milliseconds
            resources_scanned: Number of resources scanned
            findings_count: Number of findings generated
            error: Optional error message if scan failed
        """
        dimensions = [
            MetricDimension(DimensionName.SCANNER_TYPE, scanner_type),
        ]

        self.put_metric("ScanDuration", duration_ms, MetricUnit.MILLISECONDS, dimensions)
        self.put_metric("ScanCount", 1, MetricUnit.COUNT, dimensions)
        self.put_metric("ResourcesScanned", resources_scanned, MetricUnit.COUNT, dimensions)
        self.put_metric("FindingsCount", findings_count, MetricUnit.COUNT, dimensions)

        if error:
            self.put_metric("ScanErrors", 1, MetricUnit.COUNT, dimensions)

    def record_finding(
        self,
        finding_type: str,
        severity: str,
        resource_type: str,
        account_id: Optional[str] = None,
    ) -> None:
        """Record security finding metrics.

        Args:
            finding_type: Type of finding (e.g., "public_bucket", "weak_password")
            severity: Severity level (critical, high, medium, low)
            resource_type: AWS resource type
            account_id: Optional AWS account ID
        """
        dimensions = [
            MetricDimension(DimensionName.FINDING_TYPE, finding_type),
            MetricDimension(DimensionName.SEVERITY, severity),
            MetricDimension(DimensionName.RESOURCE_TYPE, resource_type),
        ]

        if account_id:
            dimensions.append(MetricDimension(DimensionName.ACCOUNT_ID, account_id))

        self.put_metric("FindingsCount", 1, MetricUnit.COUNT, dimensions)

        # Also record by severity for dashboards
        severity_metric = f"{severity.capitalize()}Findings"
        self.put_metric(severity_metric, 1, MetricUnit.COUNT, dimensions[:1])

    def record_database_operation(
        self,
        operation: str,
        latency_ms: float,
        success: bool,
    ) -> None:
        """Record database operation metrics.

        Args:
            operation: Database operation type (query, insert, update, delete)
            latency_ms: Operation latency in milliseconds
            success: Whether operation succeeded
        """
        dimensions = [
            MetricDimension(DimensionName.OPERATION, operation),
        ]

        self.put_metric("DatabaseLatency", latency_ms, MetricUnit.MILLISECONDS, dimensions)
        self.put_metric("DatabaseOperations", 1, MetricUnit.COUNT, dimensions)

        if not success:
            self.put_metric("DatabaseErrors", 1, MetricUnit.COUNT, dimensions)

    def record_business_event(
        self,
        event_name: str,
        value: float = 1.0,
        unit: MetricUnit = MetricUnit.COUNT,
        extra_dimensions: Optional[list[MetricDimension]] = None,
    ) -> None:
        """Record custom business metrics.

        Args:
            event_name: Name of the business event
            value: Metric value
            unit: Metric unit
            extra_dimensions: Additional dimensions
        """
        self.put_metric(event_name, value, unit, extra_dimensions)


# Singleton instance management
_metrics_service: Optional[MetricsService] = None
_service_lock = threading.Lock()


def get_metrics_service() -> MetricsService:
    """Get or create the global metrics service instance.

    Returns:
        Configured MetricsService instance
    """
    global _metrics_service

    if _metrics_service is None:
        with _service_lock:
            if _metrics_service is None:
                settings = get_settings()
                config = MetricsConfig(
                    enabled=True,
                    namespace="CloudOptimizer",
                    environment="development" if settings.debug else "production",
                )
                _metrics_service = MetricsService(config)

    return _metrics_service


def reset_metrics_service() -> None:
    """Reset the global metrics service (for testing)."""
    global _metrics_service
    with _service_lock:
        if _metrics_service:
            _metrics_service._shutdown()
        _metrics_service = None
