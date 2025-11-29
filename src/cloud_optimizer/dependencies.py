"""Dependency injection for Cloud Optimizer."""

import logging
from typing import Optional

from fastapi import Request

from .config import Settings, get_settings
from .services.intelligence_builder import IntelligenceBuilderService

logger = logging.getLogger(__name__)


async def get_ib_client(request: Request) -> Optional[IntelligenceBuilderService]:
    """
    Get Intelligence-Builder service from application state.

    Args:
        request: FastAPI request object

    Returns:
        IntelligenceBuilderService instance if available, None otherwise
    """
    if hasattr(request.app.state, "ib_service"):
        return request.app.state.ib_service
    return None


def get_current_settings() -> Settings:
    """
    Dependency for settings injection.

    Returns:
        Settings instance with current configuration
    """
    return get_settings()
