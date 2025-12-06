"""Unit tests for X-Ray Tracing Service.

Issue #167: Distributed tracing with X-Ray.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from cloud_optimizer.tracing.config import TracingConfig, SamplingRule
from cloud_optimizer.tracing.service import (
    TracingService,
    get_tracing_service,
    reset_tracing_service,
    XRAY_SDK_AVAILABLE,
)


class TestTracingConfig:
    """Test TracingConfig class."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = TracingConfig()
        assert config.enabled is True
        assert config.service_name == "cloud-optimizer"
        assert config.daemon_address == "127.0.0.1:2000"
        assert config.context_missing == "LOG_ERROR"

    def test_default_sampling_rules(self) -> None:
        """Test default sampling rules are created."""
        config = TracingConfig()
        assert len(config.sampling_rules) == 4
        rule_names = [r.name for r in config.sampling_rules]
        assert "error-traces" in rule_names
        assert "api-traces" in rule_names
        assert "health-traces" in rule_names
        assert "default" in rule_names

    def test_excluded_paths(self) -> None:
        """Test excluded paths are set."""
        config = TracingConfig()
        assert "/health" in config.excluded_paths
        assert "/healthz" in config.excluded_paths
        assert "/metrics" in config.excluded_paths

    def test_custom_sampling_rules(self) -> None:
        """Test custom sampling rules override defaults."""
        custom_rule = SamplingRule(
            name="custom",
            priority=1,
            fixed_rate=0.5,
        )
        config = TracingConfig(sampling_rules=[custom_rule])
        assert len(config.sampling_rules) == 1
        assert config.sampling_rules[0].name == "custom"


class TestSamplingRule:
    """Test SamplingRule class."""

    def test_default_values(self) -> None:
        """Test default sampling rule values."""
        rule = SamplingRule(name="test")
        assert rule.name == "test"
        assert rule.priority == 1000
        assert rule.fixed_rate == 0.05
        assert rule.reservoir_size == 1

    def test_custom_values(self) -> None:
        """Test custom sampling rule values."""
        rule = SamplingRule(
            name="high-priority",
            priority=1,
            fixed_rate=1.0,
            reservoir_size=10,
            url_path="/api/*",
        )
        assert rule.priority == 1
        assert rule.fixed_rate == 1.0
        assert rule.url_path == "/api/*"


class TestTracingServiceWithoutSDK:
    """Test TracingService behavior when X-Ray SDK is not available."""

    def test_service_disabled_without_sdk(self) -> None:
        """Test service is disabled when SDK not installed."""
        with patch("cloud_optimizer.tracing.service.XRAY_SDK_AVAILABLE", False):
            config = TracingConfig(enabled=True)
            service = TracingService(config)
            assert service.enabled is False

    def test_operations_no_op_without_sdk(self) -> None:
        """Test operations are no-op when SDK not available."""
        with patch("cloud_optimizer.tracing.service.XRAY_SDK_AVAILABLE", False):
            service = TracingService(TracingConfig(enabled=True))

            # All operations should succeed but do nothing
            assert service.begin_segment("test") is None
            service.end_segment()  # Should not raise

            assert service.begin_subsegment("test") is None
            service.end_subsegment()  # Should not raise

            service.add_annotation("key", "value")  # Should not raise
            service.add_metadata("key", "value")  # Should not raise
            service.add_exception(ValueError("test"))  # Should not raise

            assert service.get_trace_header() is None
            assert service.is_sampled() is False


class TestTracingServiceContextManagers:
    """Test context manager functionality."""

    def test_segment_context_manager_no_sdk(self) -> None:
        """Test segment context manager without SDK."""
        with patch("cloud_optimizer.tracing.service.XRAY_SDK_AVAILABLE", False):
            service = TracingService(TracingConfig(enabled=True))

            with service.segment("test") as seg:
                assert seg is None

    def test_subsegment_context_manager_no_sdk(self) -> None:
        """Test subsegment context manager without SDK."""
        with patch("cloud_optimizer.tracing.service.XRAY_SDK_AVAILABLE", False):
            service = TracingService(TracingConfig(enabled=True))

            with service.subsegment("test") as subseg:
                assert subseg is None

    def test_segment_context_manager_exception_handling(self) -> None:
        """Test segment context manager handles exceptions."""
        with patch("cloud_optimizer.tracing.service.XRAY_SDK_AVAILABLE", False):
            service = TracingService(TracingConfig(enabled=True))

            with pytest.raises(ValueError):
                with service.segment("test"):
                    raise ValueError("Test error")


class TestTracingServiceSingleton:
    """Test singleton behavior of get_tracing_service."""

    def test_singleton_returns_same_instance(self) -> None:
        """Test that get_tracing_service returns the same instance."""
        reset_tracing_service()

        with patch("cloud_optimizer.tracing.service.XRAY_SDK_AVAILABLE", False):
            service1 = get_tracing_service()
            service2 = get_tracing_service()
            assert service1 is service2

        reset_tracing_service()

    def test_reset_creates_new_instance(self) -> None:
        """Test that reset_tracing_service creates new instance."""
        with patch("cloud_optimizer.tracing.service.XRAY_SDK_AVAILABLE", False):
            service1 = get_tracing_service()
            reset_tracing_service()
            service2 = get_tracing_service()
            assert service1 is not service2

        reset_tracing_service()


class TestTracingServiceDisabled:
    """Test TracingService when disabled."""

    def test_disabled_service(self) -> None:
        """Test service behavior when disabled."""
        config = TracingConfig(enabled=False)
        service = TracingService(config)

        assert service.enabled is False
        assert service.begin_segment("test") is None
        assert service.begin_subsegment("test") is None


class TestTracingServiceWithMockedSDK:
    """Test TracingService with mocked X-Ray SDK."""

    @pytest.fixture
    def mock_xray_recorder(self) -> MagicMock:
        """Create mock X-Ray recorder."""
        recorder = MagicMock()
        recorder.begin_segment = MagicMock(return_value=MagicMock())
        recorder.end_segment = MagicMock()
        recorder.begin_subsegment = MagicMock(return_value=MagicMock())
        recorder.end_subsegment = MagicMock()
        recorder.current_segment = MagicMock(return_value=MagicMock(
            trace_id="1-12345-abcdef",
            id="segment-id",
            sampled=True,
        ))
        recorder.current_subsegment = MagicMock(return_value=MagicMock())
        return recorder

    def test_service_with_mocked_sdk(self, mock_xray_recorder: MagicMock) -> None:
        """Test service operations with mocked SDK."""
        with patch("cloud_optimizer.tracing.service.XRAY_SDK_AVAILABLE", True):
            with patch("cloud_optimizer.tracing.service.xray_recorder", mock_xray_recorder):
                config = TracingConfig(enabled=True)
                service = TracingService(config)
                service._initialized = True  # Force initialization

                # Test begin_segment
                segment = service.begin_segment("test-segment")
                mock_xray_recorder.begin_segment.assert_called_once()

                # Test end_segment
                service.end_segment()
                mock_xray_recorder.end_segment.assert_called_once()

    def test_get_trace_header(self, mock_xray_recorder: MagicMock) -> None:
        """Test get_trace_header returns correct format."""
        with patch("cloud_optimizer.tracing.service.XRAY_SDK_AVAILABLE", True):
            with patch("cloud_optimizer.tracing.service.xray_recorder", mock_xray_recorder):
                config = TracingConfig(enabled=True)
                service = TracingService(config)
                service._initialized = True

                header = service.get_trace_header()
                assert header is not None
                assert "Root=" in header
                assert "Parent=" in header
                assert "Sampled=" in header
