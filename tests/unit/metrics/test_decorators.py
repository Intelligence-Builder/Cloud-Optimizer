"""Unit tests for metrics decorators.

Issue #166: Application metrics with CloudWatch Metrics.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from cloud_optimizer.metrics.decorators import (
    count_invocations,
    track_all,
    track_errors,
    track_latency,
)
from cloud_optimizer.metrics.service import MetricsConfig, MetricsService


@pytest.fixture
def mock_metrics_service() -> MagicMock:
    """Create mock metrics service."""
    service = MagicMock(spec=MetricsService)
    service.put_metric = MagicMock()
    return service


@pytest.fixture(autouse=True)
def patch_metrics_service(mock_metrics_service: MagicMock):
    """Patch get_metrics_service to return mock."""
    with patch(
        "cloud_optimizer.metrics.decorators.get_metrics_service",
        return_value=mock_metrics_service,
    ):
        yield


class TestTrackLatency:
    """Test track_latency decorator."""

    def test_tracks_sync_function_latency(self, mock_metrics_service: MagicMock) -> None:
        """Test latency tracking for sync functions."""

        @track_latency("TestLatency", operation="test_op")
        def slow_function() -> str:
            time.sleep(0.01)
            return "done"

        result = slow_function()

        assert result == "done"
        mock_metrics_service.put_metric.assert_called_once()
        call_args = mock_metrics_service.put_metric.call_args
        assert call_args[0][0] == "TestLatency"
        assert call_args[0][1] >= 10  # At least 10ms

    def test_tracks_async_function_latency(
        self, mock_metrics_service: MagicMock
    ) -> None:
        """Test latency tracking for async functions."""

        @track_latency("AsyncLatency", operation="async_op")
        async def async_slow_function() -> str:
            await asyncio.sleep(0.01)
            return "async done"

        result = asyncio.run(async_slow_function())

        assert result == "async done"
        mock_metrics_service.put_metric.assert_called_once()
        call_args = mock_metrics_service.put_metric.call_args
        assert call_args[0][0] == "AsyncLatency"
        assert call_args[0][1] >= 10

    def test_uses_function_name_as_default_operation(
        self, mock_metrics_service: MagicMock
    ) -> None:
        """Test default operation name from function name."""

        @track_latency("FunctionLatency")
        def my_function_name() -> None:
            pass

        my_function_name()

        call_args = mock_metrics_service.put_metric.call_args
        dimensions = call_args[0][3]  # 4th argument is dimensions
        assert any(d.name == "Operation" and d.value == "my_function_name" for d in dimensions)

    def test_still_records_on_exception(self, mock_metrics_service: MagicMock) -> None:
        """Test latency is recorded even when function raises."""

        @track_latency("ErrorLatency")
        def failing_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        mock_metrics_service.put_metric.assert_called_once()


class TestTrackErrors:
    """Test track_errors decorator."""

    def test_does_not_record_on_success(self, mock_metrics_service: MagicMock) -> None:
        """Test no error metric when function succeeds."""

        @track_errors("TestErrors")
        def successful_function() -> str:
            return "success"

        result = successful_function()

        assert result == "success"
        mock_metrics_service.put_metric.assert_not_called()

    def test_records_error_and_reraises(self, mock_metrics_service: MagicMock) -> None:
        """Test error is recorded and re-raised."""

        @track_errors("TestErrors", operation="failing_op")
        def failing_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

        mock_metrics_service.put_metric.assert_called_once()
        call_args = mock_metrics_service.put_metric.call_args
        assert call_args[0][0] == "TestErrors"
        dimensions = call_args[0][3]
        assert any(d.name == "ErrorType" and d.value == "ValueError" for d in dimensions)

    def test_records_error_without_reraise(
        self, mock_metrics_service: MagicMock
    ) -> None:
        """Test error recording without re-raising."""

        @track_errors("TestErrors", reraise=False)
        def failing_function() -> None:
            raise ValueError("Suppressed error")

        # Should not raise
        failing_function()

        mock_metrics_service.put_metric.assert_called_once()

    def test_tracks_async_errors(self, mock_metrics_service: MagicMock) -> None:
        """Test error tracking for async functions."""

        @track_errors("AsyncErrors")
        async def async_failing() -> None:
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError):
            asyncio.run(async_failing())

        mock_metrics_service.put_metric.assert_called_once()
        call_args = mock_metrics_service.put_metric.call_args
        dimensions = call_args[0][3]
        assert any(d.name == "ErrorType" and d.value == "RuntimeError" for d in dimensions)


class TestCountInvocations:
    """Test count_invocations decorator."""

    def test_counts_sync_invocations(self, mock_metrics_service: MagicMock) -> None:
        """Test invocation counting for sync functions."""

        @count_invocations("TestInvocations", operation="test_count")
        def counted_function() -> str:
            return "counted"

        result = counted_function()

        assert result == "counted"
        mock_metrics_service.put_metric.assert_called_once()
        call_args = mock_metrics_service.put_metric.call_args
        assert call_args[0][0] == "TestInvocations"
        assert call_args[0][1] == 1  # Count is always 1

    def test_counts_multiple_invocations(
        self, mock_metrics_service: MagicMock
    ) -> None:
        """Test counting multiple invocations."""

        @count_invocations("TestInvocations")
        def multi_call() -> None:
            pass

        for _ in range(5):
            multi_call()

        assert mock_metrics_service.put_metric.call_count == 5

    def test_counts_async_invocations(self, mock_metrics_service: MagicMock) -> None:
        """Test invocation counting for async functions."""

        @count_invocations("AsyncInvocations")
        async def async_counted() -> str:
            return "async counted"

        result = asyncio.run(async_counted())

        assert result == "async counted"
        mock_metrics_service.put_metric.assert_called_once()


class TestTrackAll:
    """Test track_all decorator (combined tracking)."""

    def test_tracks_all_metrics_on_success(
        self, mock_metrics_service: MagicMock
    ) -> None:
        """Test all metrics tracked on successful execution."""

        @track_all(operation="full_track")
        def tracked_function() -> str:
            time.sleep(0.01)
            return "tracked"

        result = tracked_function()

        assert result == "tracked"
        # Should have 2 calls: invocations and latency
        assert mock_metrics_service.put_metric.call_count == 2

    def test_tracks_all_metrics_on_error(
        self, mock_metrics_service: MagicMock
    ) -> None:
        """Test all metrics tracked on error."""

        @track_all(operation="error_track")
        def failing_tracked() -> None:
            time.sleep(0.01)
            raise ValueError("Track error")

        with pytest.raises(ValueError):
            failing_tracked()

        # Should have 3 calls: invocations, error, and latency
        assert mock_metrics_service.put_metric.call_count == 3

    def test_custom_metric_names(self, mock_metrics_service: MagicMock) -> None:
        """Test custom metric names."""

        @track_all(
            operation="custom",
            latency_metric="CustomLatency",
            error_metric="CustomErrors",
            invocation_metric="CustomInvocations",
        )
        def custom_tracked() -> None:
            pass

        custom_tracked()

        calls = mock_metrics_service.put_metric.call_args_list
        metric_names = [call[0][0] for call in calls]
        assert "CustomInvocations" in metric_names
        assert "CustomLatency" in metric_names

    def test_tracks_async_functions(self, mock_metrics_service: MagicMock) -> None:
        """Test track_all with async functions."""

        @track_all(operation="async_full")
        async def async_tracked() -> str:
            await asyncio.sleep(0.01)
            return "async tracked"

        result = asyncio.run(async_tracked())

        assert result == "async tracked"
        assert mock_metrics_service.put_metric.call_count == 2


class TestDecoratorPreservation:
    """Test that decorators preserve function metadata."""

    def test_preserves_function_name(self, mock_metrics_service: MagicMock) -> None:
        """Test function name is preserved."""

        @track_latency()
        def original_name() -> None:
            pass

        assert original_name.__name__ == "original_name"

    def test_preserves_docstring(self, mock_metrics_service: MagicMock) -> None:
        """Test docstring is preserved."""

        @track_errors()
        def documented_function() -> None:
            """This is the docstring."""
            pass

        assert documented_function.__doc__ == "This is the docstring."

    def test_preserves_return_type(self, mock_metrics_service: MagicMock) -> None:
        """Test return value is correctly passed through."""

        @count_invocations()
        def returns_dict() -> dict[str, int]:
            return {"key": 42}

        result = returns_dict()
        assert result == {"key": 42}
        assert isinstance(result, dict)
