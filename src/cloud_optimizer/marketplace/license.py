"""AWS Marketplace License Validator Service."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from cloud_optimizer.marketplace.models import LicenseStatus

logger = logging.getLogger(__name__)


class MarketplaceLicenseValidator:
    """Validates AWS Marketplace license status."""

    def __init__(self, product_code: str, enabled: bool = True) -> None:
        """
        Initialize the license validator.

        Args:
            product_code: AWS Marketplace product code
            enabled: Whether marketplace validation is enabled
        """
        self.product_code = product_code
        self.enabled = enabled
        self._client: Optional[boto3.client] = None
        self._cached_status: Optional[LicenseStatus] = None
        self._cache_expires: Optional[datetime] = None
        self._customer_id: Optional[str] = None

    @property
    def client(self) -> boto3.client:
        """Get or create the AWS Marketplace Metering client."""
        if self._client is None:
            self._client = boto3.client("meteringmarketplace")
        return self._client

    async def validate_on_startup(self) -> LicenseStatus:
        """
        Validate license on container startup.

        Returns:
            LicenseStatus: The current license status

        Raises:
            Exception: If license validation encounters unexpected errors
        """
        if not self.enabled:
            logger.info("Marketplace validation disabled, using trial mode")
            return LicenseStatus.TRIAL

        try:
            response = self.client.register_usage(
                ProductCode=self.product_code,
                PublicKeyVersion=1,
            )
            self._customer_id = response.get("CustomerIdentifier")
            logger.info(f"License validated for customer: {self._customer_id}")
            return LicenseStatus.VALID
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "CustomerNotEntitledException":
                logger.warning("Customer not entitled, switching to trial mode")
                return LicenseStatus.TRIAL
            elif error_code == "CustomerNotSubscribedException":
                logger.error("Customer subscription expired")
                return LicenseStatus.SUBSCRIPTION_EXPIRED
            else:
                logger.error(f"License validation error: {e}")
                return LicenseStatus.INVALID
        except Exception as e:
            logger.error(f"License validation failed: {e}")
            return LicenseStatus.INVALID

    async def get_cached_status(self) -> LicenseStatus:
        """
        Get cached license status, refreshing if expired.

        Returns:
            LicenseStatus: The current license status
        """
        if self._cache_expires and datetime.now(timezone.utc) < self._cache_expires:
            if self._cached_status is not None:
                return self._cached_status

        self._cached_status = await self.validate_on_startup()
        self._cache_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        return self._cached_status

    @property
    def customer_id(self) -> Optional[str]:
        """Get the AWS Marketplace customer identifier."""
        return self._customer_id


# Singleton instance
_license_validator: Optional[MarketplaceLicenseValidator] = None


def get_license_validator() -> MarketplaceLicenseValidator:
    """Get the singleton license validator instance."""
    global _license_validator
    if _license_validator is None:
        from cloud_optimizer.config import get_settings

        settings = get_settings()
        _license_validator = MarketplaceLicenseValidator(
            product_code=settings.marketplace_product_code,
            enabled=settings.marketplace_enabled,
        )
    return _license_validator
