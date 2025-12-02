"""Tests for LicenseMiddleware."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cloud_optimizer.middleware.license import LicenseMiddleware
from cloud_optimizer.marketplace.license import LicenseStatus


@pytest.fixture
def app_with_middleware():
    """Create FastAPI app with license middleware."""
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/api/test")
    async def test_endpoint():
        return {"data": "test"}

    return app


def test_health_endpoint_allowed(app_with_middleware):
    """Test health endpoint bypasses license check."""
    mock_validator = MagicMock()
    app_with_middleware.add_middleware(LicenseMiddleware, license_validator=mock_validator)

    client = TestClient(app_with_middleware)
    response = client.get("/health")

    assert response.status_code == 200
    mock_validator.get_cached_status.assert_not_called()


def test_api_endpoint_checks_license(app_with_middleware):
    """Test API endpoints check license."""
    mock_validator = MagicMock()
    mock_validator.get_cached_status = AsyncMock(return_value=LicenseStatus.VALID)
    app_with_middleware.add_middleware(LicenseMiddleware, license_validator=mock_validator)

    client = TestClient(app_with_middleware)
    response = client.get("/api/test")

    assert response.status_code == 200


def test_expired_trial_returns_402(app_with_middleware):
    """Test expired trial returns 402."""
    mock_validator = MagicMock()
    mock_validator.get_cached_status = AsyncMock(return_value=LicenseStatus.TRIAL_EXPIRED)
    app_with_middleware.add_middleware(LicenseMiddleware, license_validator=mock_validator)

    client = TestClient(app_with_middleware)
    response = client.get("/api/test")

    assert response.status_code == 402
    assert response.json()["error"] == "trial_expired"


def test_expired_subscription_returns_402(app_with_middleware):
    """Test expired subscription returns 402."""
    mock_validator = MagicMock()
    mock_validator.get_cached_status = AsyncMock(return_value=LicenseStatus.SUBSCRIPTION_EXPIRED)
    app_with_middleware.add_middleware(LicenseMiddleware, license_validator=mock_validator)

    client = TestClient(app_with_middleware)
    response = client.get("/api/test")

    assert response.status_code == 402
    assert response.json()["error"] == "subscription_expired"
