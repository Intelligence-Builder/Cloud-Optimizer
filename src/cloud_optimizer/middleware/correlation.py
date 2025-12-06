"""
Correlation ID middleware for request tracing.

Extracts or generates correlation IDs for each request and makes them
available throughout the request lifecycle for logging and tracing.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from cloud_optimizer.logging.config import get_logger, log_metric
from cloud_optimizer.logging.context import (
    CorrelationContext,
    clear_correlation_id,
    clear_request_context,
    generate_correlation_id,
    set_correlation_id,
    set_request_context,
)

# Standard headers for correlation/tracing
CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Amzn-Trace-Id"  # AWS X-Ray trace header

logger = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles correlation ID for request tracing.

    Features:
    - Extracts correlation ID from incoming request headers
    - Generates new correlation ID if not present
    - Adds correlation ID to response headers
    - Sets up request context for logging
    - Logs request start/end with timing metrics
    """

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = CORRELATION_ID_HEADER,
        generate_if_missing: bool = True,
        log_requests: bool = True,
    ):
        super().__init__(app)
        self.header_name = header_name
        self.generate_if_missing = generate_if_missing
        self.log_requests = log_requests

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process request with correlation ID tracking."""
        # Extract or generate correlation ID
        correlation_id = self._extract_correlation_id(request)

        # Set correlation ID in context
        set_correlation_id(correlation_id)

        # Extract trace context (for AWS X-Ray integration)
        trace_context = self._extract_trace_context(request)

        # Build request context
        context = CorrelationContext(
            correlation_id=correlation_id,
            trace_id=trace_context.get("trace_id"),
            span_id=trace_context.get("span_id"),
            parent_span_id=trace_context.get("parent_span_id"),
            request_path=request.url.path,
            request_method=request.method,
        )

        # Set request context for logging
        set_request_context(context.to_dict())

        # Store context on request state for access in handlers
        request.state.correlation_id = correlation_id
        request.state.correlation_context = context

        # Log request start
        start_time = time.perf_counter()
        if self.log_requests:
            logger.info(
                "request_started",
                path=request.url.path,
                method=request.method,
                query_params=str(request.query_params),
                client_host=request.client.host if request.client else None,
            )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id
            response.headers[REQUEST_ID_HEADER] = correlation_id

            # Log request completion
            if self.log_requests:
                logger.info(
                    "request_completed",
                    path=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                )

                # Log as metric for CloudWatch
                log_metric(
                    logger,
                    "RequestLatency",
                    duration_ms,
                    unit="Milliseconds",
                    dimensions={
                        "endpoint": request.url.path,
                        "method": request.method,
                        "status_code": str(response.status_code),
                    },
                )

            return response

        except Exception as e:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log error
            logger.error(
                "request_failed",
                path=request.url.path,
                method=request.method,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )

            # Log error metric
            log_metric(
                logger,
                "RequestError",
                1,
                unit="Count",
                dimensions={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "error_type": type(e).__name__,
                },
            )

            raise

        finally:
            # Clear context after request
            clear_correlation_id()
            clear_request_context()

    def _extract_correlation_id(self, request: Request) -> str:
        """Extract correlation ID from request headers or generate new one."""
        # Check primary header
        correlation_id = request.headers.get(self.header_name)

        # Check alternate headers
        if not correlation_id:
            correlation_id = request.headers.get(REQUEST_ID_HEADER)

        # Generate if missing and configured to do so
        if not correlation_id and self.generate_if_missing:
            correlation_id = generate_correlation_id()

        return correlation_id or generate_correlation_id()

    def _extract_trace_context(self, request: Request) -> dict[str, str | None]:
        """Extract AWS X-Ray trace context from headers."""
        trace_header = request.headers.get(TRACE_ID_HEADER)

        if not trace_header:
            return {}

        # Parse X-Ray trace header format:
        # Root=1-5759e988-bd862e3fe1be46a994272793;Parent=53995c3f42cd8ad8;Sampled=1
        context: dict[str, str | None] = {
            "trace_id": None,
            "span_id": None,
            "parent_span_id": None,
        }

        parts = trace_header.split(";")
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                if key == "Root":
                    context["trace_id"] = value
                elif key == "Parent":
                    context["parent_span_id"] = value

        return context


def get_correlation_id_from_request(request: Request) -> str | None:
    """
    Get correlation ID from request state.

    Args:
        request: FastAPI request object

    Returns:
        Correlation ID if available, None otherwise
    """
    return getattr(request.state, "correlation_id", None)


def get_correlation_context_from_request(
    request: Request,
) -> CorrelationContext | None:
    """
    Get full correlation context from request state.

    Args:
        request: FastAPI request object

    Returns:
        CorrelationContext if available, None otherwise
    """
    return getattr(request.state, "correlation_context", None)
