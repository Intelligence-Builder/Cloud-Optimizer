"""Tests for MarketplaceLicenseValidator."""

import pytest
from unittest.mock import patch, MagicMock

from cloud_optimizer.marketplace.license import (
    MarketplaceLicenseValidator,
    LicenseStatus,
)


@pytest.mark.asyncio
async def test_valid_subscription(valid_subscription_client):
    """Test license validation with valid subscription."""
    with patch('cloud_optimizer.marketplace.license.boto3.client', return_value=valid_subscription_client):
        validator = MarketplaceLicenseValidator("test-product", enabled=True)
        validator._client = valid_subscription_client
        status = await validator.validate_on_startup()
        assert status == LicenseStatus.VALID
        assert validator.customer_id == "customer-123"


@pytest.mark.asyncio
async def test_expired_subscription(expired_subscription_client):
    """Test license validation with expired subscription."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)
    validator._client = expired_subscription_client
    status = await validator.validate_on_startup()
    assert status == LicenseStatus.SUBSCRIPTION_EXPIRED


@pytest.mark.asyncio
async def test_trial_status(trial_client):
    """Test license validation returns trial status."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)
    validator._client = trial_client
    status = await validator.validate_on_startup()
    assert status == LicenseStatus.TRIAL


@pytest.mark.asyncio
async def test_disabled_validation():
    """Test disabled validation returns trial."""
    validator = MarketplaceLicenseValidator("test-product", enabled=False)
    status = await validator.validate_on_startup()
    assert status == LicenseStatus.TRIAL


@pytest.mark.asyncio
async def test_cached_status(valid_subscription_client):
    """Test license status is cached."""
    validator = MarketplaceLicenseValidator("test-product", enabled=True)
    validator._client = valid_subscription_client

    # First call
    status1 = await validator.get_cached_status()
    assert status1 == LicenseStatus.VALID

    # Second call should use cache
    status2 = await validator.get_cached_status()
    assert status2 == LicenseStatus.VALID

    # register_usage should only be called once
    assert valid_subscription_client.register_usage.call_count == 1
