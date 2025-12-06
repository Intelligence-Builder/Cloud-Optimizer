"""Unit tests for health check endpoints.

Tests the /health, /ready, and /live endpoints for Cloud Optimizer.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cloud_optimizer.api.routers.health import (
    ComponentStatus,
    HealthResponse,
    check_database,
    check_intelligence_builder,
    router,
)


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app with health router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestComponentStatus:
    """Tests for ComponentStatus model."""

    def test_component_status_healthy(self) -> None:
        """Test healthy component status."""
        status = ComponentStatus(
            name="database",
            status="healthy",
            message="Connection successful",
            response_time_ms=5.5,
        )
        assert status.name == "database"
        assert status.status == "healthy"
        assert status.message == "Connection successful"
        assert status.response_time_ms == 5.5

    def test_component_status_unhealthy(self) -> None:
        """Test unhealthy component status."""
        status = ComponentStatus(
            name="database",
            status="unhealthy",
            message="Connection failed",
            response_time_ms=1000.0,
        )
        assert status.status == "unhealthy"

    def test_component_status_degraded(self) -> None:
        """Test degraded component status."""
        status = ComponentStatus(
            name="intelligence_builder",
            status="degraded",
            message="Service not initialized",
            response_time_ms=0.0,
        )
        assert status.status == "degraded"


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_health_response_healthy(self) -> None:
        """Test healthy response model."""
        response = HealthResponse(
            status="healthy",
            version="2.0.0",
            timestamp=datetime.utcnow(),
            components=[
                ComponentStatus(
                    name="database",
                    status="healthy",
                    message="OK",
                    response_time_ms=5.0,
                ),
            ],
        )
        assert response.status == "healthy"
        assert response.version == "2.0.0"
        assert len(response.components) == 1


class TestCheckDatabase:
    """Tests for database health check function."""

    @pytest.mark.asyncio
    async def test_check_database_healthy(self) -> None:
        """Test database health check when connection succeeds."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        # Create async context manager mock
        mock_engine.connect = MagicMock(return_value=AsyncMock())
        mock_engine.connect.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "cloud_optimizer.api.routers.health.get_engine", return_value=mock_engine
        ):
            result = await check_database()

        assert result.name == "database"
        assert result.status == "healthy"
        assert "successful" in result.message.lower()
        assert result.response_time_ms is not None
        assert result.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_check_database_unhealthy(self) -> None:
        """Test database health check when connection fails."""
        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(side_effect=Exception("Connection refused"))

        with patch(
            "cloud_optimizer.api.routers.health.get_engine", return_value=mock_engine
        ):
            result = await check_database()

        assert result.name == "database"
        assert result.status == "unhealthy"
        assert "failed" in result.message.lower()


class TestCheckIntelligenceBuilder:
    """Tests for Intelligence-Builder health check function."""

    @pytest.mark.asyncio
    async def test_check_ib_not_initialized(self) -> None:
        """Test IB health check when service not initialized."""
        mock_request = MagicMock()
        mock_request.app.state = MagicMock(spec=[])  # No ib_service attribute

        result = await check_intelligence_builder(mock_request)

        assert result.name == "intelligence_builder"
        assert result.status == "degraded"
        assert "not initialized" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_ib_not_configured(self) -> None:
        """Test IB health check when service is None."""
        mock_request = MagicMock()
        mock_request.app.state.ib_service = None

        result = await check_intelligence_builder(mock_request)

        assert result.name == "intelligence_builder"
        assert result.status == "degraded"
        assert "not configured" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_ib_not_connected(self) -> None:
        """Test IB health check when service exists but not connected."""
        mock_request = MagicMock()
        mock_request.app.state.ib_service = MagicMock()
        mock_request.app.state.ib_service.is_connected = False

        result = await check_intelligence_builder(mock_request)

        assert result.name == "intelligence_builder"
        assert result.status == "degraded"
        assert "not connected" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_ib_healthy(self) -> None:
        """Test IB health check when service is connected."""
        mock_request = MagicMock()
        mock_request.app.state.ib_service = MagicMock()
        mock_request.app.state.ib_service.is_connected = True

        result = await check_intelligence_builder(mock_request)

        assert result.name == "intelligence_builder"
        assert result.status == "healthy"
        assert "connected" in result.message.lower()


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_endpoint_all_healthy(self, client: TestClient) -> None:
        """Test health endpoint when all components healthy."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine.connect = MagicMock(return_value=AsyncMock())
        mock_engine.connect.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "cloud_optimizer.api.routers.health.get_engine", return_value=mock_engine
        ):
            # Mock app state for IB
            client.app.state.ib_service = MagicMock()
            client.app.state.ib_service.is_connected = True

            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert len(data["components"]) == 2

    def test_health_endpoint_database_unhealthy(self, client: TestClient) -> None:
        """Test health endpoint when database is unhealthy."""
        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(side_effect=Exception("Connection refused"))

        with patch(
            "cloud_optimizer.api.routers.health.get_engine", return_value=mock_engine
        ):
            client.app.state.ib_service = MagicMock()
            client.app.state.ib_service.is_connected = True

            response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"

    def test_health_endpoint_degraded(self, client: TestClient) -> None:
        """Test health endpoint when IB is degraded."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine.connect = MagicMock(return_value=AsyncMock())
        mock_engine.connect.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "cloud_optimizer.api.routers.health.get_engine", return_value=mock_engine
        ):
            # IB not connected - should be degraded
            client.app.state.ib_service = MagicMock()
            client.app.state.ib_service.is_connected = False

            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"


class TestReadinessEndpoint:
    """Tests for /ready endpoint."""

    def test_ready_endpoint_success(self, client: TestClient) -> None:
        """Test readiness endpoint when database is healthy."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine.connect = MagicMock(return_value=AsyncMock())
        mock_engine.connect.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "cloud_optimizer.api.routers.health.get_engine", return_value=mock_engine
        ):
            response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True

    def test_ready_endpoint_not_ready(self, client: TestClient) -> None:
        """Test readiness endpoint when database is unhealthy."""
        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(side_effect=Exception("Connection refused"))

        with patch(
            "cloud_optimizer.api.routers.health.get_engine", return_value=mock_engine
        ):
            response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["ready"] is False
        assert "reason" in data


class TestLivenessEndpoint:
    """Tests for /live endpoint."""

    def test_live_endpoint_always_returns_true(self, client: TestClient) -> None:
        """Test liveness endpoint always returns alive."""
        response = client.get("/live")

        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True
