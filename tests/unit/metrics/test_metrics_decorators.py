"""Tests for CloudWatch metrics decorators.

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
from cloud_optimizer.metrics.types import MetricDimension


class TestTrackLatency:
    """Tests for track_latency decorator."""

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_tracks_sync_function_latency(
        self, mock_get_service: MagicMock
    ) -> None:
        """Test tracking latency of sync function."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_latency("TestLatency", operation="test_op")
        def slow_function() -> str:
            time.sleep(0.01)
            return "done"

        result = slow_function()

        assert result == "done"
        mock_service.put_metric.assert_called_once()
        call_args = mock_service.put_metric.call_args
        assert call_args[0][0] == "TestLatency"
        assert call_args[0][1] >= 10  # At least 10ms

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_tracks_async_function_latency(
        self, mock_get_service: MagicMock
    ) -> None:
        """Test tracking latency of async function."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_latency("AsyncLatency", operation="async_op")
        async def async_function() -> str:
            await asyncio.sleep(0.01)
            return "async_done"

        result = asyncio.run(async_function())

        assert result == "async_done"
        mock_service.put_metric.assert_called_once()

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_uses_function_name_as_default_operation(
        self, mock_get_service: MagicMock
    ) -> None:
        """Test using function name as default operation."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_latency()
        def my_function() -> None:
            pass

        my_function()

        call_args = mock_service.put_metric.call_args
        dims = call_args[0][3]  # dimensions argument
        assert any(d.value == "my_function" for d in dims)

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_preserves_return_value(self, mock_get_service: MagicMock) -> None:
        """Test decorator preserves function return value."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_latency()
        def returns_value() -> dict:
            return {"key": "value"}

        result = returns_value()
        assert result == {"key": "value"}


class TestTrackErrors:
    """Tests for track_errors decorator."""

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_tracks_sync_function_error(
        self, mock_get_service: MagicMock
    ) -> None:
        """Test tracking errors in sync function."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_errors("TestErrors", operation="error_op")
        def failing_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

        mock_service.put_metric.assert_called_once()
        call_args = mock_service.put_metric.call_args
        assert call_args[0][0] == "TestErrors"
        assert call_args[0][1] == 1

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_tracks_async_function_error(
        self, mock_get_service: MagicMock
    ) -> None:
        """Test tracking errors in async function."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_errors("AsyncErrors")
        async def failing_async() -> None:
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError, match="Async error"):
            asyncio.run(failing_async())

        mock_service.put_metric.assert_called_once()

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_no_error_no_metric(self, mock_get_service: MagicMock) -> None:
        """Test no metric recorded when no error."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_errors("NoError")
        def successful_function() -> str:
            return "success"

        result = successful_function()
        assert result == "success"
        mock_service.put_metric.assert_not_called()

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_includes_error_type_dimension(
        self, mock_get_service: MagicMock
    ) -> None:
        """Test error type is included as dimension."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_errors()
        def type_error_function() -> None:
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            type_error_function()

        call_args = mock_service.put_metric.call_args
        dims = call_args[0][3]  # dimensions argument
        assert any(d.value == "TypeError" for d in dims)


class TestCountInvocations:
    """Tests for count_invocations decorator."""

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_counts_sync_invocation(self, mock_get_service: MagicMock) -> None:
        """Test counting sync function invocations."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @count_invocations("TestInvocations", operation="test_op")
        def counted_function() -> str:
            return "counted"

        result = counted_function()

        assert result == "counted"
        mock_service.put_metric.assert_called_once()
        call_args = mock_service.put_metric.call_args
        assert call_args[0][0] == "TestInvocations"
        assert call_args[0][1] == 1

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_counts_async_invocation(self, mock_get_service: MagicMock) -> None:
        """Test counting async function invocations."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @count_invocations("AsyncInvocations")
        async def async_counted() -> str:
            return "async_counted"

        result = asyncio.run(async_counted())

        assert result == "async_counted"
        mock_service.put_metric.assert_called_once()

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_multiple_invocations(self, mock_get_service: MagicMock) -> None:
        """Test multiple invocations are counted."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @count_invocations()
        def multi_call() -> None:
            pass

        multi_call()
        multi_call()
        multi_call()

        assert mock_service.put_metric.call_count == 3


class TestTrackAll:
    """Tests for track_all combined decorator."""

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_tracks_all_metrics_on_success(
        self, mock_get_service: MagicMock
    ) -> None:
        """Test tracking all metrics on successful execution."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_all(operation="all_test")
        def all_tracked() -> str:
            time.sleep(0.01)
            return "all_done"

        result = all_tracked()

        assert result == "all_done"
        # Should record invocation and latency (2 calls)
        assert mock_service.put_metric.call_count == 2

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_tracks_all_metrics_on_error(
        self, mock_get_service: MagicMock
    ) -> None:
        """Test tracking all metrics including error."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_all(operation="error_all")
        def all_error() -> None:
            raise ValueError("All error")

        with pytest.raises(ValueError):
            all_error()

        # Should record invocation, error, and latency (3 calls)
        assert mock_service.put_metric.call_count == 3

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_async_track_all(self, mock_get_service: MagicMock) -> None:
        """Test track_all with async function."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_all(operation="async_all")
        async def async_all_tracked() -> str:
            await asyncio.sleep(0.01)
            return "async_all"

        result = asyncio.run(async_all_tracked())

        assert result == "async_all"
        assert mock_service.put_metric.call_count == 2


class TestDecoratorPreservation:
    """Tests for decorator function preservation."""

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_preserves_function_name(self, mock_get_service: MagicMock) -> None:
        """Test decorator preserves function name."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_latency()
        def original_name() -> None:
            pass

        assert original_name.__name__ == "original_name"

    @patch("cloud_optimizer.metrics.decorators.get_metrics_service")
    def test_preserves_docstring(self, mock_get_service: MagicMock) -> None:
        """Test decorator preserves docstring."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        @track_errors()
        def documented_function() -> None:
            """This is a docstring."""
            pass

        assert documented_function.__doc__ == "This is a docstring."
