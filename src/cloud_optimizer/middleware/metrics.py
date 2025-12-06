"""
Metrics middleware for CloudWatch metric emission.

Issue #166: Application metrics with CloudWatch Metrics.
Sends request metrics directly to CloudWatch via MetricsService.
"""

import time
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from cloud_optimizer.logging.config import get_logger
from cloud_optimizer.metrics.service import MetricsService, get_metrics_service

logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that emits request metrics to CloudWatch.

    Features:
    - Records request count, latency, and errors
    - Excludes health check endpoints from metrics
    - Uses MetricsService for CloudWatch integration
    """

    def __init__(
        self,
        app: ASGIApp,
        metrics_service: Optional[MetricsService] = None,
        excluded_paths: Optional[list[str]] = None,
    ):
        """Initialize metrics middleware.

        Args:
            app: ASGI application
            metrics_service: Optional MetricsService instance
            excluded_paths: Paths to exclude from metrics
        """
        super().__init__(app)
        self._metrics_service = metrics_service
        self.excluded_paths = excluded_paths or [
            "/health",
            "/healthz",
            "/ready",
            "/readyz",
            "/live",
            "/livez",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

    @property
    def metrics_service(self) -> MetricsService:
        """Get metrics service (lazy initialization)."""
        if self._metrics_service is None:
            self._metrics_service = get_metrics_service()
        return self._metrics_service

    def _should_record_metrics(self, path: str) -> bool:
        """Check if metrics should be recorded for this path."""
        return not any(path.startswith(excluded) for excluded in self.excluded_paths)

    def _normalize_path(self, path: str) -> str:
        """Normalize path for metric dimensions.

        Replaces dynamic path segments (UUIDs, IDs) with placeholders
        to prevent high cardinality dimensions.
        """
        import re

        # Replace UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
            flags=re.IGNORECASE,
        )
        # Replace numeric IDs
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
        return path

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process request and emit metrics."""
        path = request.url.path

        # Skip excluded paths
        if not self._should_record_metrics(path):
            return await call_next(request)

        # Record request timing
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record successful request metrics
            normalized_path = self._normalize_path(path)
            self.metrics_service.record_request(
                endpoint=normalized_path,
                method=request.method,
                status_code=response.status_code,
                latency_ms=duration_ms,
            )

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record error metrics
            normalized_path = self._normalize_path(path)
            self.metrics_service.record_request(
                endpoint=normalized_path,
                method=request.method,
                status_code=500,
                latency_ms=duration_ms,
            )

            logger.error(
                "request_metrics_error",
                path=path,
                method=request.method,
                error=str(e),
            )
            raise
