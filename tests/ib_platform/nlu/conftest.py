"""
Pytest configuration and fixtures for NLU tests.
"""

from typing import Generator
from unittest.mock import Mock

import pytest

from cloud_optimizer.config import Settings
from ib_platform.nlu.context import ConversationContext
from ib_platform.nlu.entities import EntityExtractor
from ib_platform.nlu.service import NLUService


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    settings = Settings()
    settings.anthropic_api_key = "test-api-key-12345"
    return settings


@pytest.fixture
def mock_anthropic_client() -> Mock:
    """Create mock Anthropic client."""
    mock_client = Mock()

    # Mock the messages.create response
    mock_response = Mock()
    mock_content = Mock()
    mock_content.text = '{"intent": "general_question", "confidence": 0.85}'
    mock_response.content = [mock_content]

    mock_client.messages.create.return_value = mock_response

    return mock_client


@pytest.fixture
def entity_extractor() -> EntityExtractor:
    """Create EntityExtractor instance."""
    return EntityExtractor()


@pytest.fixture
def conversation_context() -> ConversationContext:
    """Create ConversationContext instance."""
    return ConversationContext()


@pytest.fixture
def nlu_service(
    mock_settings: Settings, mock_anthropic_client: Mock
) -> Generator[NLUService, None, None]:
    """Create NLUService instance with mocked dependencies."""
    service = NLUService(
        settings=mock_settings,
        anthropic_client=mock_anthropic_client,
    )
    yield service
    # Clean up context after each test
    service.clear_context()
