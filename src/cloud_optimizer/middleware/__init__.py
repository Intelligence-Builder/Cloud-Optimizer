"""Middleware module for Cloud Optimizer."""

from cloud_optimizer.middleware.auth import (
    AuthMiddleware,
    get_current_user,
    get_current_user_optional,
)
from cloud_optimizer.middleware.correlation import (
    CorrelationIdMiddleware,
    get_correlation_context_from_request,
    get_correlation_id_from_request,
)
from cloud_optimizer.middleware.license import LicenseMiddleware
from cloud_optimizer.middleware.metrics import MetricsMiddleware
from cloud_optimizer.middleware.security_headers import SecurityHeadersMiddleware

__all__ = [
    "AuthMiddleware",
    "get_current_user",
    "get_current_user_optional",
    "CorrelationIdMiddleware",
    "get_correlation_id_from_request",
    "get_correlation_context_from_request",
    "LicenseMiddleware",
    "MetricsMiddleware",
    "SecurityHeadersMiddleware",
]
