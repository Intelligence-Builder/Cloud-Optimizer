"""Tests for configuration module."""

import pytest

from cloud_optimizer.config import Settings


class TestSettings:
    """Test Settings configuration."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = Settings()

        assert settings.app_name == "Cloud Optimizer"
        assert settings.app_version == "2.0.0"
        assert settings.debug is False
        assert settings.log_level == "INFO"

    def test_log_level_validation(self) -> None:
        """Test log level validation."""
        # Valid levels
        settings = Settings(log_level="DEBUG")
        assert settings.log_level == "DEBUG"

        settings = Settings(log_level="warning")
        assert settings.log_level == "WARNING"

        # Invalid level
        with pytest.raises(ValueError):
            Settings(log_level="INVALID")

    def test_enabled_domains(self) -> None:
        """Test enabled domains property."""
        # Default: only security enabled
        settings = Settings()
        assert settings.enabled_domains == ["security"]

        # All domains enabled
        settings = Settings(
            enable_security_domain=True,
            enable_cost_domain=True,
            enable_performance_domain=True,
            enable_reliability_domain=True,
            enable_opex_domain=True,
        )
        assert len(settings.enabled_domains) == 5
        assert "security" in settings.enabled_domains
        assert "cost" in settings.enabled_domains

        # No domains enabled
        settings = Settings(enable_security_domain=False)
        assert settings.enabled_domains == []

    def test_ib_platform_settings(self) -> None:
        """Test Intelligence-Builder platform settings."""
        settings = Settings(
            ib_platform_url="http://ib.example.com:8000",
            ib_api_key="test-api-key",
            ib_tenant_id="test-tenant",
        )

        assert settings.ib_platform_url == "http://ib.example.com:8000"
        assert settings.ib_api_key == "test-api-key"
        assert settings.ib_tenant_id == "test-tenant"
