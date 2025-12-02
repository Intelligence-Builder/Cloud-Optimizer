"""
AWS Marketplace Integration for Cloud Optimizer.

This package provides license validation, usage metering, and subscription
management for AWS Marketplace integration.
"""

from cloud_optimizer.marketplace.exceptions import (
    LicenseValidationException,
    MarketplaceException,
    MeteringException,
    SubscriptionExpiredException,
    TrialExpiredException,
)
from cloud_optimizer.marketplace.license import (
    MarketplaceLicenseValidator,
    get_license_validator,
)
from cloud_optimizer.marketplace.metering import (
    UsageMeteringService,
    UsageRecord,
    get_metering_service,
)
from cloud_optimizer.marketplace.models import (
    LicenseStatus,
    LicenseStatusResponse,
    MarketplaceConfig,
    UsageReportResponse,
)

__all__ = [
    # Models
    "LicenseStatus",
    "LicenseStatusResponse",
    "MarketplaceConfig",
    "UsageReportResponse",
    "UsageRecord",
    # Exceptions
    "MarketplaceException",
    "LicenseValidationException",
    "MeteringException",
    "SubscriptionExpiredException",
    "TrialExpiredException",
    # Services
    "MarketplaceLicenseValidator",
    "get_license_validator",
    "UsageMeteringService",
    "get_metering_service",
]
