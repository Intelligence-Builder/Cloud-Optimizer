"""Unit tests for X-Ray tracing decorators.

Issue #167: Distributed tracing with X-Ray.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from cloud_optimizer.tracing.decorators import (
    trace_function,
    trace_async_function,
    trace_database,
    trace_http_call,
    trace_scanner,
)
from cloud_optimizer.tracing.service import TracingService


@pytest.fixture
def mock_tracing_service() -> MagicMock:
    """Create mock tracing service."""
    service = MagicMock(spec=TracingService)
    service.subsegment = MagicMock()
    service.subsegment.return_value.__enter__ = MagicMock(return_value=MagicMock())
    service.subsegment.return_value.__exit__ = MagicMock(return_value=None)
    service.add_annotation = MagicMock()
    service.add_metadata = MagicMock()
    service.add_exception = MagicMock()
    return service


@pytest.fixture(autouse=True)
def patch_tracing_service(mock_tracing_service: MagicMock):
    """Patch get_tracing_service to return mock."""
    with patch(
        "cloud_optimizer.tracing.decorators.get_tracing_service",
        return_value=mock_tracing_service,
    ):
        yield


class TestTraceFunction:
    """Test trace_function decorator."""

    def test_traces_sync_function(self, mock_tracing_service: MagicMock) -> None:
        """Test tracing sync functions."""

        @trace_function("test_operation")
        def my_function() -> str:
            return "result"

        result = my_function()

        assert result == "result"
        mock_tracing_service.subsegment.assert_called_with("test_operation", "local")

    def test_uses_function_name_as_default(
        self, mock_tracing_service: MagicMock
    ) -> None:
        """Test default subsegment name from function name."""

        @trace_function()
        def my_named_function() -> None:
            pass

        my_named_function()

        mock_tracing_service.subsegment.assert_called_with("my_named_function", "local")

    def test_captures_exception(self, mock_tracing_service: MagicMock) -> None:
        """Test exception capture in traced function."""

        @trace_function("failing_op")
        def failing_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

    def test_preserves_return_value(self, mock_tracing_service: MagicMock) -> None:
        """Test return value is preserved."""

        @trace_function()
        def returns_dict() -> dict:
            return {"key": "value", "count": 42}

        result = returns_dict()
        assert result == {"key": "value", "count": 42}


class TestTraceAsyncFunction:
    """Test trace_async_function decorator."""

    def test_traces_async_function(self, mock_tracing_service: MagicMock) -> None:
        """Test tracing async functions."""

        @trace_async_function("async_operation")
        async def async_function() -> str:
            await asyncio.sleep(0.01)
            return "async result"

        result = asyncio.run(async_function())

        assert result == "async result"
        mock_tracing_service.subsegment.assert_called()

    def test_captures_async_exception(self, mock_tracing_service: MagicMock) -> None:
        """Test exception capture in async traced function."""

        @trace_async_function("async_failing")
        async def async_failing() -> None:
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError):
            asyncio.run(async_failing())


class TestTraceDatabase:
    """Test trace_database decorator."""

    def test_traces_database_operation(self, mock_tracing_service: MagicMock) -> None:
        """Test database operation tracing."""

        @trace_database(operation="query", database_type="postgresql")
        def query_users() -> list:
            return [{"id": 1, "name": "User"}]

        result = query_users()

        assert len(result) == 1
        mock_tracing_service.subsegment.assert_called()

    def test_async_database_operation(self, mock_tracing_service: MagicMock) -> None:
        """Test async database operation tracing."""

        @trace_database(operation="insert", database_type="postgresql")
        async def insert_user(name: str) -> dict:
            return {"id": 1, "name": name}

        result = asyncio.run(insert_user("Test"))

        assert result["name"] == "Test"
        mock_tracing_service.subsegment.assert_called()


class TestTraceHttpCall:
    """Test trace_http_call decorator."""

    def test_traces_http_call(self, mock_tracing_service: MagicMock) -> None:
        """Test HTTP call tracing."""

        @trace_http_call(service="external-api", operation="get_data")
        def call_api() -> dict:
            return {"status": "ok"}

        result = call_api()

        assert result["status"] == "ok"
        mock_tracing_service.subsegment.assert_called()

    def test_async_http_call(self, mock_tracing_service: MagicMock) -> None:
        """Test async HTTP call tracing."""

        @trace_http_call(service="intelligence-builder", operation="query")
        async def call_ib_api() -> dict:
            return {"response": "data"}

        result = asyncio.run(call_ib_api())

        assert result["response"] == "data"


class TestTraceScanner:
    """Test trace_scanner decorator."""

    def test_traces_scanner(self, mock_tracing_service: MagicMock) -> None:
        """Test scanner tracing."""

        @trace_scanner("iam")
        def scan_iam() -> dict:
            return {"findings_count": 5, "resources_scanned": 100}

        result = scan_iam()

        assert result["findings_count"] == 5
        mock_tracing_service.subsegment.assert_called()

    def test_async_scanner(self, mock_tracing_service: MagicMock) -> None:
        """Test async scanner tracing."""

        @trace_scanner("s3")
        async def scan_s3_buckets() -> dict:
            return {"findings_count": 3, "resources_scanned": 50}

        result = asyncio.run(scan_s3_buckets())

        assert result["findings_count"] == 3

    def test_scanner_error_handling(self, mock_tracing_service: MagicMock) -> None:
        """Test scanner error handling."""

        @trace_scanner("lambda")
        def failing_scan() -> dict:
            raise ConnectionError("AWS connection failed")

        with pytest.raises(ConnectionError):
            failing_scan()


class TestDecoratorPreservation:
    """Test that decorators preserve function metadata."""

    def test_preserves_function_name(self, mock_tracing_service: MagicMock) -> None:
        """Test function name is preserved."""

        @trace_function()
        def original_name() -> None:
            pass

        assert original_name.__name__ == "original_name"

    def test_preserves_docstring(self, mock_tracing_service: MagicMock) -> None:
        """Test docstring is preserved."""

        @trace_database()
        def documented_function() -> None:
            """This is the docstring."""
            pass

        assert documented_function.__doc__ == "This is the docstring."
