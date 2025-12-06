"""Rate Limiting Configuration for Cloud Optimizer.

Issue #162: Penetration testing preparation.
Implements rate limiting and DDoS protection for API endpoints.
"""

from datetime import datetime, timedelta
from typing import Callable, Optional

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from cloud_optimizer.config import get_settings


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: int = 60,
    ) -> None:
        """Initialize rate limit exception.

        Args:
            detail: Error message.
            retry_after: Seconds until rate limit resets.
        """
        super().__init__(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for development/testing.

    For production, use Redis-based rate limiting.
    """

    def __init__(self) -> None:
        """Initialize rate limiter storage."""
        self._requests: dict[str, list[datetime]] = {}

    def _clean_old_requests(
        self,
        key: str,
        window: timedelta,
    ) -> None:
        """Remove requests outside the time window.

        Args:
            key: Rate limit key.
            window: Time window for rate limiting.
        """
        if key not in self._requests:
            return

        cutoff = datetime.utcnow() - window
        self._requests[key] = [
            ts for ts in self._requests[key] if ts > cutoff
        ]

    def is_allowed(
        self,
        key: str,
        limit: int,
        window: timedelta,
    ) -> tuple[bool, int]:
        """Check if request is allowed under rate limit.

        Args:
            key: Rate limit key (e.g., IP or user ID).
            limit: Maximum requests allowed in window.
            window: Time window for rate limiting.

        Returns:
            Tuple of (is_allowed, remaining_requests).
        """
        self._clean_old_requests(key, window)

        if key not in self._requests:
            self._requests[key] = []

        current_count = len(self._requests[key])

        if current_count >= limit:
            return False, 0

        self._requests[key].append(datetime.utcnow())
        return True, limit - current_count - 1


# Global rate limiter instance
_rate_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get or create the rate limiter instance.

    Returns:
        Rate limiter instance.
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


class RateLimitConfig:
    """Rate limit configuration for different endpoint categories."""

    # Authentication endpoints - stricter limits to prevent brute force
    AUTH_LIMIT = 5  # requests
    AUTH_WINDOW = timedelta(minutes=1)

    # General API endpoints - per user
    API_LIMIT = 100  # requests
    API_WINDOW = timedelta(minutes=1)

    # Global limit - per IP for unauthenticated requests
    GLOBAL_LIMIT = 1000  # requests
    GLOBAL_WINDOW = timedelta(minutes=1)

    # Health check - unlimited
    HEALTH_LIMIT = 10000
    HEALTH_WINDOW = timedelta(minutes=1)


def get_client_identifier(request: Request) -> str:
    """Get unique identifier for the client.

    Uses X-Forwarded-For header if behind proxy, otherwise uses client IP.

    Args:
        request: FastAPI request object.

    Returns:
        Client identifier string.
    """
    # Check for X-Forwarded-For header (common when behind load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def get_rate_limit_key(
    request: Request,
    user_id: Optional[str] = None,
) -> str:
    """Generate rate limit key based on request context.

    Args:
        request: FastAPI request object.
        user_id: Optional authenticated user ID.

    Returns:
        Rate limit key string.
    """
    client_ip = get_client_identifier(request)
    path = request.url.path

    # Use user ID if authenticated, otherwise use IP
    identity = user_id or client_ip

    # Categorize endpoints
    if path.startswith("/api/v1/auth"):
        return f"auth:{client_ip}"
    elif path.startswith("/health"):
        return f"health:{client_ip}"
    else:
        return f"api:{identity}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on all requests."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process request and enforce rate limits.

        Args:
            request: FastAPI request object.
            call_next: Next middleware/handler in chain.

        Returns:
            Response object.
        """
        settings = get_settings()

        # Skip rate limiting if disabled
        if settings.debug:
            # Relaxed rate limiting in debug mode
            return await call_next(request)

        rate_limiter = get_rate_limiter()
        path = request.url.path

        # Determine rate limit based on endpoint
        if path.startswith("/health"):
            limit = RateLimitConfig.HEALTH_LIMIT
            window = RateLimitConfig.HEALTH_WINDOW
        elif path.startswith("/api/v1/auth"):
            limit = RateLimitConfig.AUTH_LIMIT
            window = RateLimitConfig.AUTH_WINDOW
        else:
            limit = RateLimitConfig.API_LIMIT
            window = RateLimitConfig.API_WINDOW

        # Get rate limit key
        key = get_rate_limit_key(request)

        # Check rate limit
        is_allowed, remaining = rate_limiter.is_allowed(key, limit, window)

        if not is_allowed:
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": int(window.total_seconds()),
                    }
                },
                headers={
                    "Retry-After": str(int(window.total_seconds())),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


# Rate limit decorator for specific endpoints
def rate_limit(
    limit: int = 100,
    window_seconds: int = 60,
) -> Callable:
    """Decorator to apply rate limiting to specific endpoints.

    Args:
        limit: Maximum requests allowed in window.
        window_seconds: Time window in seconds.

    Returns:
        Decorator function.
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(request: Request, *args, **kwargs):
            rate_limiter = get_rate_limiter()
            key = get_rate_limit_key(request)
            window = timedelta(seconds=window_seconds)

            is_allowed, remaining = rate_limiter.is_allowed(key, limit, window)

            if not is_allowed:
                raise RateLimitExceeded(
                    detail="Rate limit exceeded for this endpoint",
                    retry_after=window_seconds,
                )

            return await func(request, *args, **kwargs)

        return wrapper
    return decorator
