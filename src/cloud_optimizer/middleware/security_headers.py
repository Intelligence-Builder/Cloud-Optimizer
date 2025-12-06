"""Security Headers Middleware for Cloud Optimizer.

Issue #160: SSL/TLS certificate setup (ACM)
Implements HSTS and other security headers for SOC 2 compliance.
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from cloud_optimizer.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.

    Headers added:
    - Strict-Transport-Security (HSTS): Forces HTTPS for specified duration
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Legacy XSS protection (for older browsers)
    - Referrer-Policy: Controls referrer information sent
    - Permissions-Policy: Controls browser features
    - Content-Security-Policy: Controls resource loading (if enabled)
    """

    def __init__(
        self,
        app: ASGIApp,
        hsts_max_age: int = 31536000,  # 1 year in seconds
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        enable_csp: bool = False,
        csp_policy: str | None = None,
    ) -> None:
        """Initialize security headers middleware.

        Args:
            app: The ASGI application.
            hsts_max_age: Max age for HSTS header in seconds (default: 1 year).
            hsts_include_subdomains: Include subdomains in HSTS (default: True).
            hsts_preload: Add preload directive to HSTS (default: False).
            enable_csp: Enable Content-Security-Policy header (default: False).
            csp_policy: Custom CSP policy string (default: restrictive policy).
        """
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.enable_csp = enable_csp
        self.csp_policy = csp_policy or self._default_csp_policy()

    def _default_csp_policy(self) -> str:
        """Return default restrictive CSP policy."""
        return (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

    def _build_hsts_header(self) -> str:
        """Build HSTS header value."""
        parts = [f"max-age={self.hsts_max_age}"]
        if self.hsts_include_subdomains:
            parts.append("includeSubDomains")
        if self.hsts_preload:
            parts.append("preload")
        return "; ".join(parts)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Add security headers to response.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler in the chain.

        Returns:
            Response with security headers added.
        """
        response = await call_next(request)

        # HSTS - Strict Transport Security
        # Forces browsers to use HTTPS for all future requests
        response.headers["Strict-Transport-Security"] = self._build_hsts_header()

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Disable various browser features for security
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # Content Security Policy (optional, can break some features)
        if self.enable_csp:
            response.headers["Content-Security-Policy"] = self.csp_policy

        # Cache control for security-sensitive responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response


def get_security_headers_middleware(
    hsts_enabled: bool = True,
    hsts_max_age: int = 31536000,
) -> type[SecurityHeadersMiddleware]:
    """Factory function to create configured security headers middleware.

    Args:
        hsts_enabled: Whether to enable HSTS (default: True).
        hsts_max_age: HSTS max-age in seconds (default: 1 year).

    Returns:
        Configured SecurityHeadersMiddleware class.
    """
    settings = get_settings()

    # In debug mode, use shorter HSTS duration
    if settings.debug:
        hsts_max_age = 300  # 5 minutes for development

    return SecurityHeadersMiddleware
