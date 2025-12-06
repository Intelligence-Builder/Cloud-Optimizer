"""X-Ray Tracing Middleware for FastAPI.

Issue #167: Distributed tracing with X-Ray.
"""

import time
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from cloud_optimizer.logging.config import get_logger
from cloud_optimizer.logging.context import get_correlation_id
from cloud_optimizer.tracing.config import TracingConfig
from cloud_optimizer.tracing.service import get_tracing_service

logger = get_logger(__name__)

# X-Ray trace header name
XRAY_TRACE_HEADER = "X-Amzn-Trace-Id"


class XRayMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for AWS X-Ray distributed tracing.

    Creates X-Ray segments for each incoming request and propagates
    trace context to downstream services.

    Features:
    - Automatic segment creation for requests
    - Integration with existing correlation ID middleware
    - Request/response metadata capture
    - Error and exception tracking
    - Path-based exclusion for health checks
    """

    def __init__(
        self,
        app: ASGIApp,
        config: Optional[TracingConfig] = None,
    ) -> None:
        """Initialize X-Ray middleware.

        Args:
            app: The ASGI application.
            config: Optional TracingConfig for customization.
        """
        super().__init__(app)
        self.config = config or TracingConfig()
        self._tracing = get_tracing_service()

    def _should_trace(self, path: str) -> bool:
        """Check if request path should be traced.

        Args:
            path: Request path

        Returns:
            True if path should be traced
        """
        if not self.config.enabled:
            return False

        # Check excluded paths
        for excluded in self.config.excluded_paths:
            if path.startswith(excluded.rstrip("*")):
                return False

        return True

    def _parse_trace_header(
        self, header: Optional[str]
    ) -> tuple[Optional[str], Optional[str], Optional[bool]]:
        """Parse X-Ray trace header.

        Format: Root=1-5759e988-bd862e3fe1be46a994272793;Parent=53995c3f42cd8ad8;Sampled=1

        Args:
            header: X-Ray trace header value

        Returns:
            Tuple of (trace_id, parent_id, sampled)
        """
        if not header:
            return None, None, None

        trace_id = None
        parent_id = None
        sampled = None

        parts = header.split(";")
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key == "Root":
                    trace_id = value
                elif key == "Parent":
                    parent_id = value
                elif key == "Sampled":
                    sampled = value == "1"

        return trace_id, parent_id, sampled

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process request with X-Ray tracing.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler in the chain.

        Returns:
            Response with X-Ray trace header.
        """
        path = request.url.path

        # Skip tracing for excluded paths
        if not self._should_trace(path):
            return await call_next(request)

        # Parse incoming trace header
        trace_header = request.headers.get(XRAY_TRACE_HEADER)
        trace_id, parent_id, sampled = self._parse_trace_header(trace_header)

        # Get correlation ID
        correlation_id = get_correlation_id()

        # Create segment name from method and path
        segment_name = f"{request.method} {path}"

        start_time = time.perf_counter()
        status_code = 500
        error_occurred = False

        # Begin segment
        with self._tracing.segment(
            name=segment_name,
            trace_id=trace_id,
            parent_id=parent_id,
        ) as segment:
            try:
                # Add request annotations
                if segment:
                    self._tracing.add_annotation("http.method", request.method)
                    self._tracing.add_annotation("http.url", str(request.url))
                    if correlation_id:
                        self._tracing.add_annotation("correlation_id", correlation_id)

                    # Add request metadata
                    self._tracing.add_metadata(
                        "request",
                        {
                            "method": request.method,
                            "url": str(request.url),
                            "path": path,
                            "query_string": str(request.query_params),
                            "headers": dict(request.headers)
                            if self.config.capture_request_body
                            else {},
                            "client_host": request.client.host if request.client else None,
                        },
                        namespace="http",
                    )

                # Call the next middleware/handler
                response = await call_next(request)
                status_code = response.status_code

                # Add response annotations
                if segment:
                    self._tracing.add_annotation("http.status_code", status_code)

                    # Mark as error for 5xx responses
                    if status_code >= 500:
                        segment.add_error_flag()
                        error_occurred = True
                    elif status_code >= 400:
                        segment.add_throttle_flag() if status_code == 429 else None

                    # Add response metadata
                    self._tracing.add_metadata(
                        "response",
                        {
                            "status_code": status_code,
                            "content_length": response.headers.get("content-length"),
                            "content_type": response.headers.get("content-type"),
                        },
                        namespace="http",
                    )

                # Add trace header to response
                outgoing_trace_header = self._tracing.get_trace_header()
                if outgoing_trace_header:
                    response.headers[XRAY_TRACE_HEADER] = outgoing_trace_header

                return response

            except Exception as e:
                error_occurred = True
                self._tracing.add_exception(e)

                # Log the error
                logger.error(
                    "request_error",
                    path=path,
                    method=request.method,
                    error=str(e),
                    correlation_id=correlation_id,
                )
                raise

            finally:
                # Calculate and record latency
                duration_ms = (time.perf_counter() - start_time) * 1000

                if segment:
                    self._tracing.add_metadata(
                        "latency_ms",
                        duration_ms,
                        namespace="performance",
                    )

                logger.debug(
                    "xray_segment_complete",
                    path=path,
                    duration_ms=round(duration_ms, 2),
                    status_code=status_code,
                    error=error_occurred,
                    sampled=self._tracing.is_sampled(),
                )
