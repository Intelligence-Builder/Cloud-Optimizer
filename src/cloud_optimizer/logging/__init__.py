"""
Structured logging module for Cloud Optimizer.

Provides:
- JSON-formatted structured logging
- Correlation ID tracking for request tracing
- PII redaction for sensitive data
- CloudWatch Logs integration
- Log-based metrics support
"""

from cloud_optimizer.logging.config import (
    LogConfig,
    configure_logging,
    get_logger,
)
from cloud_optimizer.logging.context import (
    CorrelationContext,
    get_correlation_id,
    set_correlation_id,
)
from cloud_optimizer.logging.pii_filter import (
    PIIFilter,
    redact_pii,
)

__all__ = [
    "LogConfig",
    "configure_logging",
    "get_logger",
    "CorrelationContext",
    "get_correlation_id",
    "set_correlation_id",
    "PIIFilter",
    "redact_pii",
]
