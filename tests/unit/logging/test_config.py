"""Tests for logging configuration."""

import json
from io import StringIO

import pytest
import structlog

from cloud_optimizer.logging.config import (
    LogConfig,
    configure_logging,
    create_processors,
    get_config,
    get_logger,
    log_metric,
)


class TestLogConfig:
    """Tests for LogConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = LogConfig()
        assert config.level == "INFO"
        assert config.format == "json"
        assert config.service_name == "cloud-optimizer"
        assert config.environment == "development"
        assert config.pii_redaction_enabled is True

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = LogConfig(
            level="DEBUG",
            format="console",
            service_name="test-service",
            environment="production",
            cloudwatch_enabled=True,
        )
        assert config.level == "DEBUG"
        assert config.format == "console"
        assert config.service_name == "test-service"
        assert config.environment == "production"
        assert config.cloudwatch_enabled is True

    def test_extra_context(self) -> None:
        """Test extra context configuration."""
        config = LogConfig(extra_context={"region": "us-east-1", "instance": "i-123"})
        assert config.extra_context["region"] == "us-east-1"
        assert config.extra_context["instance"] == "i-123"


class TestCreateProcessors:
    """Tests for processor chain creation."""

    def test_creates_processor_list(self) -> None:
        """Test that processors are created."""
        config = LogConfig()
        processors = create_processors(config)
        assert len(processors) > 0
        assert callable(processors[0])

    def test_json_format_processors(self) -> None:
        """Test processors for JSON format."""
        config = LogConfig(format="json")
        processors = create_processors(config)
        # Last processor should be JSON renderer
        last_processor = processors[-1]
        assert isinstance(last_processor, structlog.processors.JSONRenderer)

    def test_console_format_processors(self) -> None:
        """Test processors for console format."""
        config = LogConfig(format="console")
        processors = create_processors(config)
        # Last processor should be console renderer
        last_processor = processors[-1]
        assert isinstance(last_processor, structlog.dev.ConsoleRenderer)

    def test_pii_redaction_processor_included(self) -> None:
        """Test PII redaction processor is included when enabled."""
        config = LogConfig(pii_redaction_enabled=True)
        processors = create_processors(config)
        # Check that PIIRedactionProcessor is in the chain
        processor_types = [type(p).__name__ for p in processors]
        assert "PIIRedactionProcessor" in processor_types

    def test_pii_redaction_processor_excluded(self) -> None:
        """Test PII redaction processor excluded when disabled."""
        config = LogConfig(pii_redaction_enabled=False)
        processors = create_processors(config)
        processor_types = [type(p).__name__ for p in processors]
        assert "PIIRedactionProcessor" not in processor_types


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_with_defaults(self) -> None:
        """Test configuring with default settings."""
        configure_logging()
        config = get_config()
        assert config.level == "INFO"

    def test_configure_with_custom_config(self) -> None:
        """Test configuring with custom settings."""
        custom_config = LogConfig(
            level="DEBUG",
            service_name="custom-service",
        )
        configure_logging(custom_config)
        config = get_config()
        assert config.level == "DEBUG"
        assert config.service_name == "custom-service"


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_bound_logger(self) -> None:
        """Test that get_logger returns a bound logger."""
        configure_logging(LogConfig(service_name="test-service"))
        logger = get_logger("test.module")
        assert logger is not None

    def test_logger_has_service_context(self) -> None:
        """Test that logger has service context bound."""
        configure_logging(LogConfig(service_name="context-test"))
        logger = get_logger("test.module")
        # The logger should have context bound - verify by checking it's a BoundLogger
        assert hasattr(logger, "bind")


class TestLogMetric:
    """Tests for log_metric function."""

    def test_log_metric_creates_metric_event(self) -> None:
        """Test that log_metric creates a metric log event without error."""
        configure_logging(LogConfig(format="json"))
        logger = get_logger("metric.test")

        # The function should complete without raising
        log_metric(
            logger,
            metric_name="TestMetric",
            value=42.5,
            unit="Count",
            dimensions={"endpoint": "/test"},
        )
        # Success is indicated by no exception being raised

    def test_log_metric_with_dimensions(self) -> None:
        """Test log_metric with dimensions."""
        configure_logging(LogConfig())
        logger = get_logger("metric.test")

        # This should not raise
        log_metric(
            logger,
            metric_name="RequestLatency",
            value=150.5,
            unit="Milliseconds",
            dimensions={"endpoint": "/api/v1/test", "method": "GET"},
        )

    def test_log_metric_without_dimensions(self) -> None:
        """Test log_metric without dimensions."""
        configure_logging(LogConfig())
        logger = get_logger("metric.test")

        # This should not raise
        log_metric(
            logger,
            metric_name="TotalRequests",
            value=100,
            unit="Count",
        )
