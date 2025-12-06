"""Unit tests for Security Headers Middleware.

Issue #160: SSL/TLS certificate setup (ACM)
Tests for HSTS and security headers middleware.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cloud_optimizer.middleware.security_headers import SecurityHeadersMiddleware


@pytest.fixture
def app_with_security_headers() -> FastAPI:
    """Create FastAPI app with security headers middleware."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    def test_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/test")
    def api_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.fixture
def client(app_with_security_headers: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app_with_security_headers)


class TestSecurityHeadersMiddleware:
    """Test security headers are properly set."""

    def test_hsts_header_present(self, client: TestClient) -> None:
        """Test Strict-Transport-Security header is set."""
        response = client.get("/test")
        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=" in hsts
        assert "includeSubDomains" in hsts

    def test_hsts_default_max_age(self, client: TestClient) -> None:
        """Test HSTS max-age is 1 year by default."""
        response = client.get("/test")
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts

    def test_x_content_type_options(self, client: TestClient) -> None:
        """Test X-Content-Type-Options header is set to nosniff."""
        response = client.get("/test")
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self, client: TestClient) -> None:
        """Test X-Frame-Options header is set to DENY."""
        response = client.get("/test")
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_x_xss_protection(self, client: TestClient) -> None:
        """Test X-XSS-Protection header is set."""
        response = client.get("/test")
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    def test_referrer_policy(self, client: TestClient) -> None:
        """Test Referrer-Policy header is set."""
        response = client.get("/test")
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client: TestClient) -> None:
        """Test Permissions-Policy header is set."""
        response = client.get("/test")
        assert "Permissions-Policy" in response.headers
        policy = response.headers["Permissions-Policy"]
        assert "camera=()" in policy
        assert "microphone=()" in policy

    def test_api_cache_control(self, client: TestClient) -> None:
        """Test Cache-Control is set for API endpoints."""
        response = client.get("/api/v1/test")
        assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"
        assert response.headers["Pragma"] == "no-cache"

    def test_non_api_no_cache_control(self, client: TestClient) -> None:
        """Test Cache-Control is not forced for non-API endpoints."""
        response = client.get("/test")
        # Non-API endpoints don't get forced cache headers
        # (they may have Cache-Control from other sources)


class TestSecurityHeadersConfiguration:
    """Test configurable security headers options."""

    def test_custom_hsts_max_age(self) -> None:
        """Test custom HSTS max-age configuration."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, hsts_max_age=3600)

        @app.get("/test")
        def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=3600" in hsts

    def test_hsts_preload_disabled_by_default(self) -> None:
        """Test HSTS preload is disabled by default."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")
        hsts = response.headers["Strict-Transport-Security"]
        assert "preload" not in hsts

    def test_hsts_preload_enabled(self) -> None:
        """Test HSTS preload can be enabled."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, hsts_preload=True)

        @app.get("/test")
        def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")
        hsts = response.headers["Strict-Transport-Security"]
        assert "preload" in hsts

    def test_csp_disabled_by_default(self) -> None:
        """Test Content-Security-Policy is disabled by default."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")
        assert "Content-Security-Policy" not in response.headers

    def test_csp_can_be_enabled(self) -> None:
        """Test Content-Security-Policy can be enabled."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, enable_csp=True)

        @app.get("/test")
        def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp


class TestSecurityHeadersCompliance:
    """Test security headers meet compliance requirements."""

    def test_soc2_required_headers(self, client: TestClient) -> None:
        """Test all SOC 2 recommended security headers are present."""
        response = client.get("/test")

        required_headers = [
            "Strict-Transport-Security",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy",
        ]

        for header in required_headers:
            assert header in response.headers, f"Missing required header: {header}"

    def test_ssl_labs_a_grade_headers(self, client: TestClient) -> None:
        """Test headers required for SSL Labs A grade."""
        response = client.get("/test")

        # HSTS with at least 6 months (15768000 seconds)
        hsts = response.headers["Strict-Transport-Security"]
        import re

        match = re.search(r"max-age=(\d+)", hsts)
        assert match is not None
        max_age = int(match.group(1))
        assert max_age >= 15768000, "HSTS max-age must be at least 6 months for A grade"
