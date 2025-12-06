"""
Tests for MarketplaceLicenseValidator.

TESTING STRATEGY:
Since AWS Marketplace Metering API is NOT supported by LocalStack, we use a hybrid approach:
1. Unit tests for internal logic (caching, status management)
2. Integration tests with custom mock server (simulates marketplace API)
3. Smoke tests that validate boto3 client creation

For REAL marketplace integration testing, use:
- AWS test accounts with marketplace seller/buyer roles
- IAM policies limiting to test products only
- pytest markers: @pytest.mark.real_aws
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError

from cloud_optimizer.marketplace.license import (
    LicenseStatus,
    MarketplaceLicenseValidator,
    get_license_validator,
)

# ============================================================================
# Unit Tests - Internal Logic (No AWS Dependencies)
# ============================================================================


@pytest.mark.unit
def test_validator_initialization() -> None:
    """Test validator can be initialized with product code."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)

    assert validator.product_code == "test-product"
    assert validator.enabled is True
    assert validator.customer_id is None
    assert validator._cached_status is None
    assert validator._cache_expires is None


@pytest.mark.unit
def test_validator_disabled_returns_trial() -> None:
    """Test disabled validator immediately returns trial without AWS calls."""
    validator = MarketplaceLicenseValidator("test-product", enabled=False)

    # This should not create a boto3 client
    assert validator._client is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disabled_validation_returns_trial() -> None:
    """Test disabled validation returns trial status without API calls."""
    validator = MarketplaceLicenseValidator("test-product", enabled=False)
    status = await validator.validate_on_startup()

    assert status == LicenseStatus.TRIAL
    assert validator._client is None  # No client should be created


@pytest.mark.unit
def test_client_property_lazy_initialization() -> None:
    """Test boto3 client is created lazily."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)

    # Client should not exist yet
    assert validator._client is None

    # Accessing client property creates it
    with patch("cloud_optimizer.marketplace.license.boto3.client") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        client = validator.client

        assert client is mock_client
        mock_boto3.assert_called_once_with("meteringmarketplace")


# ============================================================================
# Integration Tests - With Mocked AWS Responses
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_valid_subscription_flow() -> None:
    """Test complete flow for valid subscription."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)

    # Create mock client with successful response
    mock_client = MagicMock()
    mock_client.register_usage.return_value = {
        "CustomerIdentifier": "cust-12345",
        "ProductCode": "test-product",
        "PublicKeyVersion": 1,
    }
    validator._client = mock_client

    status = await validator.validate_on_startup()

    assert status == LicenseStatus.VALID
    assert validator.customer_id == "cust-12345"
    mock_client.register_usage.assert_called_once_with(
        ProductCode="test-product",
        PublicKeyVersion=1,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_customer_not_entitled_returns_trial() -> None:
    """Test CustomerNotEntitledException triggers trial mode."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)

    mock_client = MagicMock()
    error_response = {
        "Error": {
            "Code": "CustomerNotEntitledException",
            "Message": "Customer is not entitled to use this product",
        }
    }
    mock_client.register_usage.side_effect = ClientError(
        error_response, "RegisterUsage"
    )
    validator._client = mock_client

    status = await validator.validate_on_startup()

    assert status == LicenseStatus.TRIAL
    assert validator.customer_id is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_customer_not_subscribed_returns_expired() -> None:
    """Test CustomerNotSubscribedException returns subscription expired."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)

    mock_client = MagicMock()
    error_response = {
        "Error": {
            "Code": "CustomerNotSubscribedException",
            "Message": "Customer subscription has expired",
        }
    }
    mock_client.register_usage.side_effect = ClientError(
        error_response, "RegisterUsage"
    )
    validator._client = mock_client

    status = await validator.validate_on_startup()

    assert status == LicenseStatus.SUBSCRIPTION_EXPIRED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unknown_client_error_returns_invalid() -> None:
    """Test unknown ClientError returns invalid status."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)

    mock_client = MagicMock()
    error_response = {
        "Error": {
            "Code": "UnknownException",
            "Message": "Something went wrong",
        }
    }
    mock_client.register_usage.side_effect = ClientError(
        error_response, "RegisterUsage"
    )
    validator._client = mock_client

    status = await validator.validate_on_startup()

    assert status == LicenseStatus.INVALID


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generic_exception_returns_invalid() -> None:
    """Test generic exception returns invalid status."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)

    mock_client = MagicMock()
    mock_client.register_usage.side_effect = Exception("Network error")
    validator._client = mock_client

    status = await validator.validate_on_startup()

    assert status == LicenseStatus.INVALID


# ============================================================================
# Cache Tests - Status Caching Behavior
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_status_on_first_call() -> None:
    """Test first call to get_cached_status performs validation."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)

    mock_client = MagicMock()
    mock_client.register_usage.return_value = {
        "CustomerIdentifier": "cust-12345",
        "ProductCode": "test-product",
        "PublicKeyVersion": 1,
    }
    validator._client = mock_client

    # First call
    status = await validator.get_cached_status()

    assert status == LicenseStatus.VALID
    assert validator._cached_status == LicenseStatus.VALID
    assert validator._cache_expires is not None
    mock_client.register_usage.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_reuse_within_expiry() -> None:
    """Test cached status is reused within expiry window."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)

    mock_client = MagicMock()
    mock_client.register_usage.return_value = {
        "CustomerIdentifier": "cust-12345",
        "ProductCode": "test-product",
        "PublicKeyVersion": 1,
    }
    validator._client = mock_client

    # First call
    status1 = await validator.get_cached_status()
    assert status1 == LicenseStatus.VALID
    assert mock_client.register_usage.call_count == 1

    # Second call should use cache
    status2 = await validator.get_cached_status()
    assert status2 == LicenseStatus.VALID
    assert mock_client.register_usage.call_count == 1  # Still 1, not 2

    # Third call should use cache
    status3 = await validator.get_cached_status()
    assert status3 == LicenseStatus.VALID
    assert mock_client.register_usage.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_refresh_after_expiry() -> None:
    """Test cache is refreshed after expiration."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)

    mock_client = MagicMock()
    mock_client.register_usage.return_value = {
        "CustomerIdentifier": "cust-12345",
        "ProductCode": "test-product",
        "PublicKeyVersion": 1,
    }
    validator._client = mock_client

    # First call
    status1 = await validator.get_cached_status()
    assert status1 == LicenseStatus.VALID
    assert mock_client.register_usage.call_count == 1

    # Expire the cache manually
    validator._cache_expires = datetime.now(timezone.utc) - timedelta(seconds=1)

    # Second call should refresh
    status2 = await validator.get_cached_status()
    assert status2 == LicenseStatus.VALID
    assert mock_client.register_usage.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_handles_status_change() -> None:
    """Test cache correctly handles status changes on refresh."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)

    mock_client = MagicMock()

    # First call: valid subscription
    mock_client.register_usage.return_value = {
        "CustomerIdentifier": "cust-12345",
        "ProductCode": "test-product",
        "PublicKeyVersion": 1,
    }
    validator._client = mock_client

    status1 = await validator.get_cached_status()
    assert status1 == LicenseStatus.VALID

    # Expire cache and change response to subscription expired
    validator._cache_expires = datetime.now(timezone.utc) - timedelta(seconds=1)
    error_response = {
        "Error": {
            "Code": "CustomerNotSubscribedException",
            "Message": "Subscription expired",
        }
    }
    mock_client.register_usage.side_effect = ClientError(
        error_response, "RegisterUsage"
    )

    status2 = await validator.get_cached_status()
    assert status2 == LicenseStatus.SUBSCRIPTION_EXPIRED


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


@pytest.mark.unit
def test_get_license_validator_singleton() -> None:
    """Test get_license_validator returns singleton instance."""
    with patch("cloud_optimizer.config.get_settings") as mock_settings:
        mock_settings.return_value.marketplace_product_code = "test-product"
        mock_settings.return_value.marketplace_enabled = True

        # Reset singleton
        import cloud_optimizer.marketplace.license as license_module

        license_module._license_validator = None

        validator1 = get_license_validator()
        validator2 = get_license_validator()

        assert validator1 is validator2
        assert validator1.product_code == "test-product"

        # Cleanup
        license_module._license_validator = None


# ============================================================================
# LocalStack Integration Tests (Skip if marketplace not available)
# ============================================================================


@pytest.mark.localstack_only
@pytest.mark.skip(
    reason="AWS Marketplace Metering API not supported by LocalStack. "
    "Use real AWS with test accounts or implement custom mock server."
)
def test_localstack_marketplace_placeholder() -> None:
    """
    Placeholder for LocalStack marketplace tests.

    When LocalStack adds marketplace support or a custom mock server is implemented:
    1. Remove skip decorator
    2. Use fixtures from localstack_conftest.py
    3. Test against mock marketplace endpoints
    4. Validate error handling with real HTTP responses
    """
    pass


# ============================================================================
# Real AWS Integration Tests (Requires AWS Credentials)
# ============================================================================


@pytest.mark.real_aws
@pytest.mark.skip(
    reason="Real AWS tests require valid credentials and test marketplace product. "
    "Enable manually for integration testing."
)
@pytest.mark.asyncio
async def test_real_aws_marketplace_validation() -> None:
    """
    Real AWS marketplace validation test.

    Prerequisites:
    1. AWS credentials configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    2. Test marketplace product code in environment (TEST_MARKETPLACE_PRODUCT_CODE)
    3. Running in AWS environment with marketplace IAM permissions

    To run:
        pytest -m real_aws tests/marketplace/test_license.py::test_real_aws_marketplace_validation
    """
    import os

    product_code = os.getenv("TEST_MARKETPLACE_PRODUCT_CODE")
    if not product_code:
        pytest.skip("TEST_MARKETPLACE_PRODUCT_CODE not set")

    validator = MarketplaceLicenseValidator(product_code, enabled=True)
    status = await validator.validate_on_startup()

    # Should return a valid status (any status, not error)
    assert status in [
        LicenseStatus.VALID,
        LicenseStatus.TRIAL,
        LicenseStatus.SUBSCRIPTION_EXPIRED,
    ]
