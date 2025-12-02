"""Tests for answer generation service."""

import pytest
from uuid import uuid4

from ib_platform.answer.service import AnswerService, create_answer_service


@pytest.mark.asyncio
async def test_answer_service_initialization(
    mock_anthropic_client, mock_kb_service, mock_findings_service
):
    """Test AnswerService initialization."""
    service = AnswerService(
        anthropic_client=mock_anthropic_client,
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    assert service.client is mock_anthropic_client
    assert service.model == AnswerService.DEFAULT_MODEL
    assert service.max_tokens == AnswerService.DEFAULT_MAX_TOKENS
    assert service.context_assembler is not None


@pytest.mark.asyncio
async def test_answer_service_custom_model(
    mock_anthropic_client, mock_kb_service, mock_findings_service
):
    """Test AnswerService with custom model."""
    custom_model = "claude-3-opus-20240229"
    service = AnswerService(
        anthropic_client=mock_anthropic_client,
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
        model=custom_model,
    )

    assert service.model == custom_model


@pytest.mark.asyncio
async def test_generate_streaming(
    mock_anthropic_client, mock_kb_service, mock_findings_service, simple_nlu_result
):
    """Test streaming answer generation."""
    service = AnswerService(
        anthropic_client=mock_anthropic_client,
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    chunks = []
    async for chunk in service.generate_streaming(
        question="How do I secure S3?",
        nlu_result=simple_nlu_result,
        aws_account_id=uuid4(),
    ):
        chunks.append(chunk)

    # Should have received chunks
    assert len(chunks) > 0
    assert "".join(chunks) == "Here's my security advice."


@pytest.mark.asyncio
async def test_generate_streaming_with_conversation_history(
    mock_anthropic_client,
    mock_kb_service,
    mock_findings_service,
    simple_nlu_result,
    sample_conversation_history,
):
    """Test streaming with conversation history."""
    service = AnswerService(
        anthropic_client=mock_anthropic_client,
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    chunks = []
    async for chunk in service.generate_streaming(
        question="How do I secure S3?",
        nlu_result=simple_nlu_result,
        conversation_history=sample_conversation_history,
    ):
        chunks.append(chunk)

    assert len(chunks) > 0


@pytest.mark.asyncio
async def test_generate_non_streaming(
    mock_anthropic_client, mock_kb_service, mock_findings_service, simple_nlu_result
):
    """Test non-streaming answer generation."""
    service = AnswerService(
        anthropic_client=mock_anthropic_client,
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    answer = await service.generate(
        question="How do I secure S3?",
        nlu_result=simple_nlu_result,
        aws_account_id=uuid4(),
    )

    assert isinstance(answer, str)
    assert len(answer) > 0
    assert answer == "Here's my security advice."


@pytest.mark.asyncio
async def test_generate_handles_anthropic_error(
    mock_kb_service, mock_findings_service, simple_nlu_result
):
    """Test that generation handles Anthropic API errors."""
    from unittest.mock import AsyncMock

    # Create a client that raises an error
    class ErrorMessages:
        def stream(self, **kwargs):
            raise Exception("API Error")

        async def create(self, **kwargs):
            raise Exception("API Error")

    error_client = AsyncMock()
    error_client.messages = ErrorMessages()

    service = AnswerService(
        anthropic_client=error_client,
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    answer = await service.generate(
        question="How do I secure S3?",
        nlu_result=simple_nlu_result,
    )

    # Should return error message instead of raising
    assert "Error generating response" in answer


@pytest.mark.asyncio
async def test_build_messages(
    mock_anthropic_client, mock_kb_service, simple_nlu_result
):
    """Test message building."""
    service = AnswerService(
        anthropic_client=mock_anthropic_client,
        kb_service=mock_kb_service,
    )

    # Assemble context
    context = await service.context_assembler.assemble(nlu_result=simple_nlu_result)

    # Build messages
    messages = service._build_messages("How do I secure S3?", context)

    assert isinstance(messages, list)
    assert len(messages) > 0
    assert messages[-1]["role"] == "user"
    assert "How do I secure S3?" in messages[-1]["content"]


@pytest.mark.asyncio
async def test_build_messages_with_history(
    mock_anthropic_client, mock_kb_service, simple_nlu_result, sample_conversation_history
):
    """Test message building with conversation history."""
    service = AnswerService(
        anthropic_client=mock_anthropic_client,
        kb_service=mock_kb_service,
    )

    # Assemble context with history
    context = await service.context_assembler.assemble(
        nlu_result=simple_nlu_result,
        conversation_history=sample_conversation_history,
    )

    # Build messages
    messages = service._build_messages("How do I secure S3?", context)

    # Should include history
    assert len(messages) > 1
    assert any(msg["role"] == "user" and "What is MFA?" in msg["content"] for msg in messages)
    assert any(msg["role"] == "assistant" for msg in messages)


@pytest.mark.asyncio
async def test_create_answer_service(mock_kb_service):
    """Test factory function for creating AnswerService."""
    service = create_answer_service(
        api_key="test-key",
        kb_service=mock_kb_service,
    )

    assert isinstance(service, AnswerService)
    assert service.kb_service is mock_kb_service
