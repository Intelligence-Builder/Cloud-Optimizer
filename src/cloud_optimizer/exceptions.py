"""Custom exceptions for Cloud Optimizer."""

from typing import Any, Dict, Optional


class CloudOptimizerError(Exception):
    """Base exception for Cloud Optimizer."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize CloudOptimizerError.

        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ConfigurationError(CloudOptimizerError):
    """Configuration-related errors."""

    pass


class IBServiceError(CloudOptimizerError):
    """Intelligence-Builder service errors."""

    pass


class AWSIntegrationError(CloudOptimizerError):
    """AWS integration errors."""

    pass


class ScanError(CloudOptimizerError):
    """Scanning operation errors."""

    pass


class ValidationError(CloudOptimizerError):
    """Validation errors."""

    pass
