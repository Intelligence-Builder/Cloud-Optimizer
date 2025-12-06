"""AWS X-Ray Distributed Tracing module for Cloud Optimizer.

Issue #167: Distributed tracing with X-Ray.
Provides X-Ray SDK integration for request tracing and service map visualization.
"""

from cloud_optimizer.tracing.config import TracingConfig
from cloud_optimizer.tracing.service import (
    TracingService,
    get_tracing_service,
)
from cloud_optimizer.tracing.decorators import (
    trace_function,
    trace_async_function,
    trace_database,
    trace_http_call,
)
from cloud_optimizer.tracing.middleware import XRayMiddleware

__all__ = [
    "TracingConfig",
    "TracingService",
    "get_tracing_service",
    "trace_function",
    "trace_async_function",
    "trace_database",
    "trace_http_call",
    "XRayMiddleware",
]
