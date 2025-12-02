"""Middleware module for Cloud Optimizer."""

from cloud_optimizer.middleware.auth import (
    AuthMiddleware,
    get_current_user,
    get_current_user_optional,
)
from cloud_optimizer.middleware.license import LicenseMiddleware

__all__ = [
    "AuthMiddleware",
    "get_current_user",
    "get_current_user_optional",
    "LicenseMiddleware",
]
