"""Tests for dependency injection module."""

from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from cloud_optimizer.config import Settings
from cloud_optimizer.dependencies import get_current_settings, get_ib_client
from cloud_optimizer.services.intelligence_builder import IntelligenceBuilderService


class TestGetIBClient:
    """Test get_ib_client dependency."""

    @pytest.mark.asyncio
    async def test_get_ib_client_when_service_available(self) -> None:
        """Test getting IB client when service is available in app state."""
        # Create a mock request with app state
        mock_request = MagicMock()
        mock_service = MagicMock(spec=IntelligenceBuilderService)
        mock_request.app.state.ib_service = mock_service

        # Get the service
        result = await get_ib_client(mock_request)

        # Assert we got the service
        assert result is mock_service

    @pytest.mark.asyncio
    async def test_get_ib_client_when_service_not_available(self) -> None:
        """Test getting IB client when service is not in app state."""
        # Create a mock request without ib_service
        mock_request = MagicMock()
        mock_request.app.state = MagicMock(spec=[])  # No ib_service attribute

        # Get the service
        result = await get_ib_client(mock_request)

        # Assert we got None
        assert result is None

    @pytest.mark.asyncio
    async def test_get_ib_client_when_service_is_none(self) -> None:
        """Test getting IB client when service is explicitly None."""
        # Create a mock request with None service
        mock_request = MagicMock()
        mock_request.app.state.ib_service = None

        # Get the service
        result = await get_ib_client(mock_request)

        # Assert we got None
        assert result is None


class TestGetCurrentSettings:
    """Test get_current_settings dependency."""

    def test_get_current_settings_returns_settings(self) -> None:
        """Test that get_current_settings returns Settings instance."""
        settings = get_current_settings()

        assert isinstance(settings, Settings)
        assert settings.app_name == "Cloud Optimizer"
        assert settings.app_version == "2.0.0"

    def test_get_current_settings_is_cached(self) -> None:
        """Test that get_current_settings returns the same instance (cached)."""
        settings1 = get_current_settings()
        settings2 = get_current_settings()

        # Should be the same instance due to lru_cache
        assert settings1 is settings2

    def test_get_current_settings_has_expected_defaults(self) -> None:
        """Test that settings have expected default values."""
        settings = get_current_settings()

        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.enable_security_domain is True
        assert settings.enable_cost_domain is False
