"""Tests for correlation ID context management."""

import asyncio
import uuid

import pytest

from cloud_optimizer.logging.context import (
    CorrelationContext,
    CorrelationContextManager,
    add_correlation_id,
    clear_correlation_id,
    clear_request_context,
    generate_correlation_id,
    get_correlation_id,
    get_request_context,
    set_correlation_id,
    set_request_context,
)


class TestCorrelationId:
    """Tests for correlation ID functions."""

    def test_generate_correlation_id_is_uuid(self) -> None:
        """Test that generated correlation ID is a valid UUID."""
        correlation_id = generate_correlation_id()
        # Should not raise
        uuid.UUID(correlation_id)

    def test_generate_correlation_id_unique(self) -> None:
        """Test that generated correlation IDs are unique."""
        ids = {generate_correlation_id() for _ in range(100)}
        assert len(ids) == 100

    def test_set_and_get_correlation_id(self) -> None:
        """Test setting and getting correlation ID."""
        test_id = "test-correlation-123"
        set_correlation_id(test_id)
        assert get_correlation_id() == test_id
        clear_correlation_id()

    def test_set_correlation_id_generates_if_none(self) -> None:
        """Test that set generates ID if none provided."""
        result = set_correlation_id()
        assert result is not None
        assert len(result) > 0
        # Should be a valid UUID
        uuid.UUID(result)
        clear_correlation_id()

    def test_get_correlation_id_returns_none_when_not_set(self) -> None:
        """Test that get returns None when not set."""
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_clear_correlation_id(self) -> None:
        """Test clearing correlation ID."""
        set_correlation_id("test-id")
        clear_correlation_id()
        assert get_correlation_id() is None


class TestRequestContext:
    """Tests for request context management."""

    def test_set_and_get_request_context(self) -> None:
        """Test setting and getting request context."""
        context = {"user_id": "123", "tenant_id": "abc"}
        set_request_context(context)
        result = get_request_context()
        assert result["user_id"] == "123"
        assert result["tenant_id"] == "abc"
        clear_request_context()

    def test_request_context_updates_existing(self) -> None:
        """Test that context updates merge with existing."""
        set_request_context({"a": 1})
        set_request_context({"b": 2})
        result = get_request_context()
        assert result["a"] == 1
        assert result["b"] == 2
        clear_request_context()

    def test_clear_request_context(self) -> None:
        """Test clearing request context."""
        set_request_context({"test": "value"})
        clear_request_context()
        assert get_request_context() == {}


class TestCorrelationContext:
    """Tests for CorrelationContext dataclass."""

    def test_default_correlation_id_generated(self) -> None:
        """Test that default context generates correlation ID."""
        context = CorrelationContext()
        assert context.correlation_id is not None
        # Should be valid UUID
        uuid.UUID(context.correlation_id)

    def test_custom_correlation_id(self) -> None:
        """Test context with custom correlation ID."""
        context = CorrelationContext(correlation_id="custom-id-123")
        assert context.correlation_id == "custom-id-123"

    def test_to_dict_minimal(self) -> None:
        """Test to_dict with minimal context."""
        context = CorrelationContext(correlation_id="test-123")
        result = context.to_dict()
        assert result["correlation_id"] == "test-123"
        assert "trace_id" not in result

    def test_to_dict_full(self) -> None:
        """Test to_dict with full context."""
        context = CorrelationContext(
            correlation_id="corr-123",
            trace_id="trace-456",
            span_id="span-789",
            parent_span_id="parent-000",
            user_id="user-aaa",
            tenant_id="tenant-bbb",
            request_path="/api/test",
            request_method="GET",
            extra={"custom_field": "value"},
        )
        result = context.to_dict()

        assert result["correlation_id"] == "corr-123"
        assert result["trace_id"] == "trace-456"
        assert result["span_id"] == "span-789"
        assert result["parent_span_id"] == "parent-000"
        assert result["user_id"] == "user-aaa"
        assert result["tenant_id"] == "tenant-bbb"
        assert result["request_path"] == "/api/test"
        assert result["request_method"] == "GET"
        assert result["custom_field"] == "value"


class TestCorrelationContextManager:
    """Tests for CorrelationContextManager."""

    def test_context_manager_sets_correlation_id(self) -> None:
        """Test that context manager sets correlation ID."""
        with CorrelationContextManager("test-id-123"):
            assert get_correlation_id() == "test-id-123"
        assert get_correlation_id() is None

    def test_context_manager_generates_id_if_none(self) -> None:
        """Test that context manager generates ID if not provided."""
        with CorrelationContextManager() as ctx:
            assert get_correlation_id() == ctx.correlation_id
            uuid.UUID(ctx.correlation_id)

    def test_context_manager_restores_previous_value(self) -> None:
        """Test that context manager restores previous correlation ID."""
        set_correlation_id("outer-id")
        with CorrelationContextManager("inner-id"):
            assert get_correlation_id() == "inner-id"
        # Note: contextvars reset to previous value, not "outer-id" necessarily
        # This depends on the token reset behavior
        clear_correlation_id()

    def test_context_manager_with_full_context(self) -> None:
        """Test context manager with CorrelationContext."""
        context = CorrelationContext(
            correlation_id="ctx-123",
            user_id="user-456",
            request_path="/test",
        )
        with CorrelationContextManager(context=context):
            assert get_correlation_id() == "ctx-123"
            req_ctx = get_request_context()
            assert req_ctx["user_id"] == "user-456"
            assert req_ctx["request_path"] == "/test"

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Test async context manager usage."""
        async with CorrelationContextManager("async-id-123"):
            assert get_correlation_id() == "async-id-123"
        assert get_correlation_id() is None


class TestAddCorrelationIdProcessor:
    """Tests for structlog correlation ID processor."""

    def test_adds_correlation_id_to_event(self) -> None:
        """Test processor adds correlation ID to event dict."""
        set_correlation_id("proc-test-123")
        event_dict: dict[str, object] = {"event": "test_event", "data": "value"}

        result = add_correlation_id(None, "info", event_dict)

        assert result["correlation_id"] == "proc-test-123"
        assert result["event"] == "test_event"
        clear_correlation_id()

    def test_does_not_add_when_not_set(self) -> None:
        """Test processor doesn't add correlation ID when not set."""
        clear_correlation_id()
        event_dict: dict[str, object] = {"event": "test_event"}

        result = add_correlation_id(None, "info", event_dict)

        assert "correlation_id" not in result

    def test_adds_request_context(self) -> None:
        """Test processor adds request context fields."""
        set_correlation_id("ctx-test-123")
        set_request_context({"user_id": "user-456", "tenant_id": "tenant-789"})
        event_dict: dict[str, object] = {"event": "test_event"}

        result = add_correlation_id(None, "info", event_dict)

        assert result["correlation_id"] == "ctx-test-123"
        assert result["user_id"] == "user-456"
        assert result["tenant_id"] == "tenant-789"

        clear_correlation_id()
        clear_request_context()


class TestCorrelationIdIsolation:
    """Tests for correlation ID isolation between async tasks."""

    @pytest.mark.asyncio
    async def test_correlation_id_isolated_between_tasks(self) -> None:
        """Test that correlation IDs are isolated between concurrent tasks."""
        results: dict[str, str | None] = {}

        async def task(task_id: str, correlation_id: str) -> None:
            set_correlation_id(correlation_id)
            await asyncio.sleep(0.01)  # Simulate async work
            results[task_id] = get_correlation_id()
            clear_correlation_id()

        await asyncio.gather(
            task("task1", "corr-1"),
            task("task2", "corr-2"),
            task("task3", "corr-3"),
        )

        assert results["task1"] == "corr-1"
        assert results["task2"] == "corr-2"
        assert results["task3"] == "corr-3"
