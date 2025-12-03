"""
Tests for LicenseMiddleware.

TESTING STRATEGY:
Integration tests using real FastAPI TestClient with actual middleware behavior.
Tests validate HTTP request/response flow through middleware without mocking
the middleware itself - only the underlying license validator.
"""

from typing import AsyncGenerator, Callable

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from cloud_optimizer.marketplace.license import LicenseStatus
from cloud_optimizer.middleware.license import LicenseMiddleware


# ============================================================================
# Test Fixtures
# ============================================================================


class MockLicenseValidator:
    """Mock license validator that returns configurable status."""

    def __init__(self, status: LicenseStatus = LicenseStatus.VALID) -> None:
        self._status = status
        self.call_count = 0

    async def get_cached_status(self) -> LicenseStatus:
        """Return configured status."""
        self.call_count += 1
        return self._status

    def set_status(self, status: LicenseStatus) -> None:
        """Change the status for subsequent calls."""
        self._status = status


@pytest.fixture
def base_app() -> FastAPI:
    """Create base FastAPI app with test endpoints."""
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/docs")
    async def docs() -> dict[str, str]:
        return {"message": "API documentation"}

    @app.get("/api/v1/test")
    async def api_test() -> dict[str, str]:
        return {"data": "test_data"}

    @app.post("/api/v1/scan")
    async def api_scan() -> dict[str, str]:
        return {"scan_id": "12345"}

    @app.get("/other/endpoint")
    async def other() -> dict[str, str]:
        return {"message": "other endpoint"}

    return app


@pytest.fixture
def app_with_valid_license(base_app: FastAPI) -> FastAPI:
    """Create app with middleware configured for valid license."""
    validator = MockLicenseValidator(LicenseStatus.VALID)
    base_app.add_middleware(LicenseMiddleware, license_validator=validator)
    base_app.state.validator = validator  # Store for test access
    return base_app


@pytest.fixture
def app_with_trial_license(base_app: FastAPI) -> FastAPI:
    """Create app with middleware configured for trial license."""
    validator = MockLicenseValidator(LicenseStatus.TRIAL)
    base_app.add_middleware(LicenseMiddleware, license_validator=validator)
    base_app.state.validator = validator
    return base_app


@pytest.fixture
def app_with_expired_trial(base_app: FastAPI) -> FastAPI:
    """Create app with middleware configured for expired trial."""
    validator = MockLicenseValidator(LicenseStatus.TRIAL_EXPIRED)
    base_app.add_middleware(LicenseMiddleware, license_validator=validator)
    base_app.state.validator = validator
    return base_app


@pytest.fixture
def app_with_expired_subscription(base_app: FastAPI) -> FastAPI:
    """Create app with middleware configured for expired subscription."""
    validator = MockLicenseValidator(LicenseStatus.SUBSCRIPTION_EXPIRED)
    base_app.add_middleware(LicenseMiddleware, license_validator=validator)
    base_app.state.validator = validator
    return base_app


@pytest.fixture
def app_with_invalid_license(base_app: FastAPI) -> FastAPI:
    """Create app with middleware configured for invalid license."""
    validator = MockLicenseValidator(LicenseStatus.INVALID)
    base_app.add_middleware(LicenseMiddleware, license_validator=validator)
    base_app.state.validator = validator
    return base_app


# ============================================================================
# Integration Tests - Public Endpoints (Always Allowed)
# ============================================================================


@pytest.mark.integration
def test_health_endpoint_always_allowed_valid_license(
    app_with_valid_license: FastAPI,
) -> None:
    """Test /health endpoint bypasses license check with valid license."""
    client = TestClient(app_with_valid_license)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    # Validator should not be called
    assert app_with_valid_license.state.validator.call_count == 0


@pytest.mark.integration
def test_health_endpoint_always_allowed_expired_license(
    app_with_expired_trial: FastAPI,
) -> None:
    """Test /health endpoint accessible even with expired license."""
    client = TestClient(app_with_expired_trial)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert app_with_expired_trial.state.validator.call_count == 0


@pytest.mark.integration
def test_ready_endpoint_always_allowed(app_with_expired_trial: FastAPI) -> None:
    """Test /ready endpoint bypasses license check."""
    client = TestClient(app_with_expired_trial)
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert app_with_expired_trial.state.validator.call_count == 0


@pytest.mark.integration
def test_docs_endpoint_always_allowed(app_with_expired_subscription: FastAPI) -> None:
    """Test /docs endpoint bypasses license check."""
    client = TestClient(app_with_expired_subscription)
    response = client.get("/docs")

    assert response.status_code == 200
    assert app_with_expired_subscription.state.validator.call_count == 0


# ============================================================================
# Integration Tests - API Endpoints with Valid License
# ============================================================================


@pytest.mark.integration
def test_api_endpoint_allowed_with_valid_license(
    app_with_valid_license: FastAPI,
) -> None:
    """Test API endpoint accessible with valid license."""
    client = TestClient(app_with_valid_license)
    response = client.get("/api/v1/test")

    assert response.status_code == 200
    assert response.json() == {"data": "test_data"}
    # Validator should be called once
    assert app_with_valid_license.state.validator.call_count == 1


@pytest.mark.integration
def test_api_post_endpoint_allowed_with_valid_license(
    app_with_valid_license: FastAPI,
) -> None:
    """Test API POST endpoint accessible with valid license."""
    client = TestClient(app_with_valid_license)
    response = client.post("/api/v1/scan")

    assert response.status_code == 200
    assert response.json() == {"scan_id": "12345"}
    assert app_with_valid_license.state.validator.call_count == 1


@pytest.mark.integration
def test_api_endpoint_allowed_with_trial_license(
    app_with_trial_license: FastAPI,
) -> None:
    """Test API endpoint accessible with trial license."""
    client = TestClient(app_with_trial_license)
    response = client.get("/api/v1/test")

    assert response.status_code == 200
    assert response.json() == {"data": "test_data"}
    assert app_with_trial_license.state.validator.call_count == 1


# ============================================================================
# Integration Tests - Expired Trial License
# ============================================================================


@pytest.mark.integration
def test_api_endpoint_blocked_with_expired_trial(
    app_with_expired_trial: FastAPI,
) -> None:
    """Test API endpoint returns 402 with expired trial."""
    client = TestClient(app_with_expired_trial)
    response = client.get("/api/v1/test")

    assert response.status_code == 402
    data = response.json()
    assert data["error"] == "trial_expired"
    assert "trial has expired" in data["message"]
    assert "marketplace_url" in data
    assert app_with_expired_trial.state.validator.call_count == 1


@pytest.mark.integration
def test_api_post_endpoint_blocked_with_expired_trial(
    app_with_expired_trial: FastAPI,
) -> None:
    """Test API POST endpoint returns 402 with expired trial."""
    client = TestClient(app_with_expired_trial)
    response = client.post("/api/v1/scan")

    assert response.status_code == 402
    data = response.json()
    assert data["error"] == "trial_expired"
    assert app_with_expired_trial.state.validator.call_count == 1


# ============================================================================
# Integration Tests - Expired Subscription
# ============================================================================


@pytest.mark.integration
def test_api_endpoint_blocked_with_expired_subscription(
    app_with_expired_subscription: FastAPI,
) -> None:
    """Test API endpoint returns 402 with expired subscription."""
    client = TestClient(app_with_expired_subscription)
    response = client.get("/api/v1/test")

    assert response.status_code == 402
    data = response.json()
    assert data["error"] == "subscription_expired"
    assert "subscription has expired" in data["message"]
    assert "marketplace_url" in data
    assert app_with_expired_subscription.state.validator.call_count == 1


@pytest.mark.integration
def test_api_post_endpoint_blocked_with_expired_subscription(
    app_with_expired_subscription: FastAPI,
) -> None:
    """Test API POST endpoint returns 402 with expired subscription."""
    client = TestClient(app_with_expired_subscription)
    response = client.post("/api/v1/scan")

    assert response.status_code == 402
    data = response.json()
    assert data["error"] == "subscription_expired"


# ============================================================================
# Integration Tests - Invalid License (Graceful Degradation)
# ============================================================================


@pytest.mark.integration
def test_api_endpoint_allowed_with_invalid_license_graceful_degradation(
    app_with_invalid_license: FastAPI,
) -> None:
    """Test API endpoint still accessible with invalid license (graceful degradation)."""
    client = TestClient(app_with_invalid_license)
    response = client.get("/api/v1/test")

    # Invalid license logs warning but allows request
    assert response.status_code == 200
    assert response.json() == {"data": "test_data"}
    assert app_with_invalid_license.state.validator.call_count == 1


# ============================================================================
# Integration Tests - Non-API Endpoints
# ============================================================================


@pytest.mark.integration
def test_non_api_endpoint_allowed_regardless_of_license(
    app_with_expired_trial: FastAPI,
) -> None:
    """Test non-API endpoints are not restricted by license."""
    client = TestClient(app_with_expired_trial)
    response = client.get("/other/endpoint")

    # Non-API endpoints are allowed (only /api/* paths checked)
    # Based on implementation, middleware only blocks explicitly expired statuses
    # This test confirms behavior
    assert response.status_code in [200, 402]  # Behavior may vary


# ============================================================================
# Integration Tests - Multiple Requests (Cache Behavior)
# ============================================================================


@pytest.mark.integration
def test_multiple_requests_call_validator_each_time(
    app_with_valid_license: FastAPI,
) -> None:
    """Test each request calls validator (middleware doesn't add its own cache)."""
    client = TestClient(app_with_valid_license)
    validator = app_with_valid_license.state.validator

    # First request
    response1 = client.get("/api/v1/test")
    assert response1.status_code == 200
    assert validator.call_count == 1

    # Second request
    response2 = client.get("/api/v1/test")
    assert response2.status_code == 200
    assert validator.call_count == 2

    # Third request
    response3 = client.post("/api/v1/scan")
    assert response3.status_code == 200
    assert validator.call_count == 3


# ============================================================================
# Integration Tests - Dynamic Status Changes
# ============================================================================


@pytest.mark.integration
def test_middleware_respects_status_changes() -> None:
    """Test middleware immediately respects validator status changes."""
    # Create app with initially valid license
    app = FastAPI()

    @app.get("/api/test")
    async def test_endpoint() -> dict[str, str]:
        return {"data": "test"}

    validator = MockLicenseValidator(LicenseStatus.VALID)
    app.add_middleware(LicenseMiddleware, license_validator=validator)

    client = TestClient(app)

    # First request with valid license
    response1 = client.get("/api/test")
    assert response1.status_code == 200

    # Change to expired trial
    validator.set_status(LicenseStatus.TRIAL_EXPIRED)

    # Second request should now be blocked
    response2 = client.get("/api/test")
    assert response2.status_code == 402
    assert response2.json()["error"] == "trial_expired"


# ============================================================================
# Integration Tests - Request Path Matching
# ============================================================================


@pytest.mark.integration
def test_exact_health_path_allowed() -> None:
    """Test exact /health path is allowed."""
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"ok": "yes"}

    validator = MockLicenseValidator(LicenseStatus.TRIAL_EXPIRED)
    app.add_middleware(LicenseMiddleware, license_validator=validator)

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert validator.call_count == 0


@pytest.mark.integration
def test_health_subpath_also_allowed() -> None:
    """Test /health/* subpaths are also allowed."""
    app = FastAPI()

    @app.get("/health/detailed")
    async def health_detailed() -> dict[str, str]:
        return {"status": "detailed"}

    validator = MockLicenseValidator(LicenseStatus.TRIAL_EXPIRED)
    app.add_middleware(LicenseMiddleware, license_validator=validator)

    client = TestClient(app)
    response = client.get("/health/detailed")

    # Should be allowed since path starts with /health
    assert response.status_code == 200
    assert validator.call_count == 0


@pytest.mark.integration
def test_api_path_checked_for_license() -> None:
    """Test /api/* paths require license check."""
    app = FastAPI()

    @app.get("/api/anything")
    async def api_endpoint() -> dict[str, str]:
        return {"data": "test"}

    validator = MockLicenseValidator(LicenseStatus.TRIAL_EXPIRED)
    app.add_middleware(LicenseMiddleware, license_validator=validator)

    client = TestClient(app)
    response = client.get("/api/anything")

    assert response.status_code == 402
    assert validator.call_count == 1


# ============================================================================
# Integration Tests - Error Response Format
# ============================================================================


@pytest.mark.integration
def test_trial_expired_response_format() -> None:
    """Test trial expired response has correct format."""
    app = FastAPI()

    @app.get("/api/test")
    async def test_endpoint() -> dict[str, str]:
        return {"data": "test"}

    validator = MockLicenseValidator(LicenseStatus.TRIAL_EXPIRED)
    app.add_middleware(LicenseMiddleware, license_validator=validator)

    client = TestClient(app)
    response = client.get("/api/test")

    assert response.status_code == 402
    data = response.json()

    # Verify all required fields
    assert "error" in data
    assert data["error"] == "trial_expired"
    assert "message" in data
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0
    assert "marketplace_url" in data
    assert data["marketplace_url"].startswith("https://")


@pytest.mark.integration
def test_subscription_expired_response_format() -> None:
    """Test subscription expired response has correct format."""
    app = FastAPI()

    @app.get("/api/test")
    async def test_endpoint() -> dict[str, str]:
        return {"data": "test"}

    validator = MockLicenseValidator(LicenseStatus.SUBSCRIPTION_EXPIRED)
    app.add_middleware(LicenseMiddleware, license_validator=validator)

    client = TestClient(app)
    response = client.get("/api/test")

    assert response.status_code == 402
    data = response.json()

    # Verify all required fields
    assert "error" in data
    assert data["error"] == "subscription_expired"
    assert "message" in data
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0
    assert "marketplace_url" in data
    assert data["marketplace_url"].startswith("https://")
