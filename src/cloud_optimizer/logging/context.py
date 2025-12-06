"""
Correlation ID context management for request tracing.

Provides thread-safe correlation ID storage and retrieval using
contextvars for async compatibility.
"""

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Optional

# Context variable for storing correlation ID per request
_correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)

# Context variable for additional request context
_request_context_var: ContextVar[dict[str, Any]] = ContextVar(
    "request_context", default={}
)


@dataclass
class CorrelationContext:
    """
    Context holder for correlation and tracing information.

    Attributes:
        correlation_id: Unique identifier for the request chain
        trace_id: Optional distributed trace ID (e.g., X-Ray trace ID)
        span_id: Optional span ID for distributed tracing
        parent_span_id: Optional parent span ID
        user_id: Optional authenticated user ID
        tenant_id: Optional tenant ID for multi-tenancy
        request_path: Optional HTTP request path
        request_method: Optional HTTP method
        extra: Additional context fields
    """

    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for logging."""
        result: dict[str, Any] = {
            "correlation_id": self.correlation_id,
        }

        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.span_id:
            result["span_id"] = self.span_id
        if self.parent_span_id:
            result["parent_span_id"] = self.parent_span_id
        if self.user_id:
            result["user_id"] = self.user_id
        if self.tenant_id:
            result["tenant_id"] = self.tenant_id
        if self.request_path:
            result["request_path"] = self.request_path
        if self.request_method:
            result["request_method"] = self.request_method

        result.update(self.extra)
        return result


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID from context.

    Returns:
        The correlation ID if set, None otherwise
    """
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set the correlation ID in context.

    Args:
        correlation_id: Optional ID to set. Generates new if not provided.

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = generate_correlation_id()
    _correlation_id_var.set(correlation_id)
    return correlation_id


def clear_correlation_id() -> None:
    """Clear the correlation ID from context."""
    _correlation_id_var.set(None)


def get_request_context() -> dict[str, Any]:
    """Get the current request context."""
    return _request_context_var.get().copy()


def set_request_context(context: dict[str, Any]) -> None:
    """Set request context fields."""
    current = _request_context_var.get().copy()
    current.update(context)
    _request_context_var.set(current)


def clear_request_context() -> None:
    """Clear all request context."""
    _request_context_var.set({})


def add_correlation_id(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Structlog processor to add correlation ID to log events.

    This processor automatically adds the correlation ID and any
    request context to every log message.
    """
    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    # Add any additional request context
    request_context = get_request_context()
    if request_context:
        event_dict.update(request_context)

    return event_dict


class CorrelationContextManager:
    """
    Context manager for correlation ID scope.

    Usage:
        async with CorrelationContextManager("my-correlation-id"):
            # All logs in this block will include the correlation ID
            logger.info("Processing request")
    """

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        context: Optional[CorrelationContext] = None,
    ):
        # Use correlation_id from context if provided and no explicit ID
        if correlation_id is None and context is not None:
            self.correlation_id = context.correlation_id
        else:
            self.correlation_id = correlation_id or generate_correlation_id()
        self.context = context
        self._token: Optional[Any] = None
        self._context_token: Optional[Any] = None

    def __enter__(self) -> "CorrelationContextManager":
        self._token = _correlation_id_var.set(self.correlation_id)
        if self.context:
            self._context_token = _request_context_var.set(
                self.context.to_dict()
            )
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> None:
        if self._token is not None:
            _correlation_id_var.reset(self._token)
        if self._context_token is not None:
            _request_context_var.reset(self._context_token)

    async def __aenter__(self) -> "CorrelationContextManager":
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)
