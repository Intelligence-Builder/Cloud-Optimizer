"""
Logging configuration for Cloud Optimizer.

Provides structured logging with JSON format, proper log levels,
and CloudWatch Logs integration support.
"""

import logging
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Optional

import structlog
from structlog.types import Processor

from cloud_optimizer.logging.context import add_correlation_id
from cloud_optimizer.logging.pii_filter import PIIRedactionProcessor


@dataclass
class LogConfig:
    """Logging configuration settings."""

    level: str = "INFO"
    format: str = "json"  # json or console
    service_name: str = "cloud-optimizer"
    environment: str = "development"
    version: str = "2.0.0"
    cloudwatch_enabled: bool = False
    cloudwatch_log_group: str = "/cloud-optimizer/application"
    cloudwatch_retention_days: int = 30
    pii_redaction_enabled: bool = True
    include_stack_info: bool = True

    # CloudWatch metric filters
    metric_namespace: str = "CloudOptimizer"
    error_metric_name: str = "ErrorCount"
    request_metric_name: str = "RequestCount"

    # Additional context fields to always include
    extra_context: dict[str, Any] = field(default_factory=dict)


def create_processors(config: LogConfig) -> list[Processor]:
    """Create the chain of structlog processors."""
    processors: list[Processor] = [
        # Add correlation ID from context
        add_correlation_id,
        # Add standard library log level filtering
        structlog.stdlib.filter_by_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add log level
        structlog.stdlib.add_log_level,
        # Add timestamp in ISO format
        structlog.processors.TimeStamper(fmt="iso"),
        # Add service context
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    # Add PII redaction if enabled
    if config.pii_redaction_enabled:
        processors.append(PIIRedactionProcessor())

    # Add stack info if enabled
    if config.include_stack_info:
        processors.append(structlog.processors.StackInfoRenderer())

    # Add exception formatting
    processors.append(structlog.processors.format_exc_info)

    # Add final renderer based on format
    if config.format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    return processors


def configure_logging(config: Optional[LogConfig] = None) -> None:
    """
    Configure structured logging for the application.

    Args:
        config: Optional LogConfig instance. Uses defaults if not provided.
    """
    if config is None:
        config = LogConfig()

    # Set root logger level
    log_level = getattr(logging, config.level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Get processors
    processors = create_processors(config)

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Store config for later access
    _set_config(config)


@lru_cache(maxsize=1)
def _get_config_cache() -> dict[str, LogConfig]:
    """Internal cache for config storage."""
    return {}


def _set_config(config: LogConfig) -> None:
    """Store the current logging config."""
    cache = _get_config_cache()
    cache["current"] = config


def get_config() -> LogConfig:
    """Get the current logging configuration."""
    cache = _get_config_cache()
    return cache.get("current", LogConfig())


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance with context.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger with service context
    """
    config = get_config()
    logger = structlog.get_logger(name)

    # Bind service context
    return logger.bind(
        service=config.service_name,
        environment=config.environment,
        version=config.version,
        **config.extra_context,
    )


def log_metric(
    logger: structlog.stdlib.BoundLogger,
    metric_name: str,
    value: float,
    unit: str = "Count",
    dimensions: Optional[dict[str, str]] = None,
) -> None:
    """
    Log a metric event for CloudWatch Logs metric filters.

    The log format is designed to be parsed by CloudWatch metric filters:
    {
        "metric_name": "RequestLatency",
        "metric_value": 123.45,
        "metric_unit": "Milliseconds",
        "metric_dimensions": {"endpoint": "/api/v1/security"}
    }

    Args:
        logger: Structlog logger instance
        metric_name: Name of the metric
        value: Metric value
        unit: CloudWatch unit (Count, Milliseconds, Bytes, etc.)
        dimensions: Optional dimension key-value pairs
    """
    logger.info(
        "metric",
        metric_name=metric_name,
        metric_value=value,
        metric_unit=unit,
        metric_dimensions=dimensions or {},
    )
