"""License enforcement middleware for AWS Marketplace."""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class LicenseMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce AWS Marketplace license status."""

    ALWAYS_ALLOWED = [
        "/health",
        "/ready",
        "/live",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    def __init__(self, app, license_validator=None):
        super().__init__(app)
        self._license_validator = license_validator

    @property
    def license_validator(self):
        if self._license_validator is None:
            from cloud_optimizer.marketplace.license import get_license_validator
            self._license_validator = get_license_validator()
        return self._license_validator

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Allow public endpoints
        if any(path.startswith(p) for p in self.ALWAYS_ALLOWED):
            return await call_next(request)

        # Check license status
        from cloud_optimizer.marketplace.license import LicenseStatus

        status = await self.license_validator.get_cached_status()

        if status == LicenseStatus.TRIAL_EXPIRED:
            return JSONResponse(
                status_code=402,
                content={
                    "error": "trial_expired",
                    "message": "Your trial has expired. Please subscribe via AWS Marketplace.",
                    "marketplace_url": "https://aws.amazon.com/marketplace/pp/prodview-cloudoptimizer",
                },
            )

        if status == LicenseStatus.SUBSCRIPTION_EXPIRED:
            return JSONResponse(
                status_code=402,
                content={
                    "error": "subscription_expired",
                    "message": "Your subscription has expired. Please renew via AWS Marketplace.",
                    "marketplace_url": "https://aws.amazon.com/marketplace/pp/prodview-cloudoptimizer",
                },
            )

        if status == LicenseStatus.INVALID:
            logger.warning(f"Invalid license status for request to {path}")
            # Allow request but log warning - graceful degradation

        return await call_next(request)
