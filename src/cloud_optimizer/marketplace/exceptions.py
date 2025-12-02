"""
AWS Marketplace exception classes.

Custom exceptions for marketplace-related errors including license validation,
metering, and subscription management.
"""

from typing import Any, Dict, Optional

from cloud_optimizer.exceptions import CloudOptimizerError


class MarketplaceException(CloudOptimizerError):
    """Base exception for marketplace errors."""

    error_code: str = "MARKETPLACE_ERROR"

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """
        Initialize MarketplaceException.

        Args:
            message: Error message
            details: Additional error details
            error_code: Specific error code (overrides class default)
        """
        super().__init__(message, details)
        if error_code:
            self.error_code = error_code


class LicenseValidationException(MarketplaceException):
    """Exception raised when license validation fails."""

    error_code = "LICENSE_VALIDATION_FAILED"


class MeteringException(MarketplaceException):
    """Exception raised when usage metering fails."""

    error_code = "METERING_FAILED"


class SubscriptionExpiredException(MarketplaceException):
    """Exception raised when subscription has expired."""

    error_code = "SUBSCRIPTION_EXPIRED"


class TrialExpiredException(MarketplaceException):
    """Exception raised when trial period has expired."""

    error_code = "TRIAL_EXPIRED"
