"""Tests for main application module."""

from fastapi.testclient import TestClient

from cloud_optimizer.main import app, create_app


class TestHealthEndpoints:
    """Test health check endpoints."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client = TestClient(app)

    def test_health_check(self) -> None:
        """Test basic health check endpoint."""
        response = self.client.get("/health")

        # Health check can return 200 (healthy/degraded) or 503 (unhealthy)
        # depending on component availability during test
        assert response.status_code in (200, 503)
        data = response.json()
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "version" in data

    def test_readiness_check(self) -> None:
        """Test readiness check endpoint."""
        response = self.client.get("/ready")

        # Readiness check may fail if database isn't available during test
        assert response.status_code in (200, 503)
        data = response.json()
        # API returns {"ready": true/false} or {"ready": false, "reason": "..."}
        assert "ready" in data


class TestAppCreation:
    """Test application creation."""

    def test_create_app(self) -> None:
        """Test create_app returns FastAPI instance."""
        application = create_app()

        assert application is not None
        assert application.title == "Cloud Optimizer"

    def test_openapi_endpoint(self) -> None:
        """Test OpenAPI schema is available."""
        client = TestClient(app)
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert data["info"]["title"] == "Cloud Optimizer"
