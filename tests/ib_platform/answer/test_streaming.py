"""Tests for SSE streaming handler."""

import json
import pytest
from uuid import uuid4

from ib_platform.answer.streaming import StreamingHandler


@pytest.mark.asyncio
async def test_streaming_handler_initialization(
    mock_anthropic_client, mock_kb_service, mock_findings_service
):
    """Test StreamingHandler initialization."""
    from ib_platform.answer.service import AnswerService

    answer_service = AnswerService(
        anthropic_client=mock_anthropic_client,
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    handler = StreamingHandler(answer_service)

    assert handler.answer_service is answer_service


@pytest.mark.asyncio
async def test_stream_answer(
    mock_anthropic_client, mock_kb_service, mock_findings_service, simple_nlu_result
):
    """Test streaming answer with SSE formatting."""
    from ib_platform.answer.service import AnswerService

    answer_service = AnswerService(
        anthropic_client=mock_anthropic_client,
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    handler = StreamingHandler(answer_service)

    events = []
    async for event in handler.stream_answer(
        question="How do I secure S3?",
        nlu_result=simple_nlu_result,
        aws_account_id=uuid4(),
    ):
        events.append(event)

    # Should have start event, chunk events, and done event
    assert len(events) > 2

    # Check start event
    assert "event: start" in events[0]
    assert "data:" in events[0]

    # Check chunk events
    chunk_events = [e for e in events if "event: chunk" in e]
    assert len(chunk_events) > 0

    # Check done event
    assert "event: done" in events[-1]

    # Verify SSE format
    for event in events:
        assert "event:" in event
        assert "data:" in event
        assert event.endswith("\n\n")


@pytest.mark.asyncio
async def test_stream_answer_includes_metadata(
    mock_anthropic_client, mock_kb_service, mock_findings_service, simple_nlu_result
):
    """Test that done event includes metadata."""
    from ib_platform.answer.service import AnswerService

    answer_service = AnswerService(
        anthropic_client=mock_anthropic_client,
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    handler = StreamingHandler(answer_service)

    events = []
    async for event in handler.stream_answer(
        question="How do I secure S3?",
        nlu_result=simple_nlu_result,
        aws_account_id=uuid4(),
    ):
        events.append(event)

    # Get done event
    done_event = events[-1]
    assert "event: done" in done_event

    # Parse data
    data_line = [line for line in done_event.split("\n") if line.startswith("data:")][0]
    data = json.loads(data_line.replace("data: ", ""))

    assert data["type"] == "done"
    assert "total_chunks" in data
    assert "response_length" in data


@pytest.mark.asyncio
async def test_stream_answer_handles_errors(
    mock_kb_service, mock_findings_service, simple_nlu_result
):
    """Test that streaming handles errors gracefully."""
    from ib_platform.answer.service import AnswerService
    from unittest.mock import AsyncMock

    # Create a client that raises an error
    class ErrorMessages:
        def stream(self, **kwargs):
            raise Exception("API Error")

        async def create(self, **kwargs):
            raise Exception("API Error")

    error_client = AsyncMock()
    error_client.messages = ErrorMessages()

    answer_service = AnswerService(
        anthropic_client=error_client,
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    handler = StreamingHandler(answer_service)

    events = []
    async for event in handler.stream_answer(
        question="How do I secure S3?",
        nlu_result=simple_nlu_result,
    ):
        events.append(event)

    # Should have start and chunk events (errors become text chunks)
    assert any("event: start" in e for e in events)
    assert any("event: chunk" in e for e in events)
    # Error text should be in one of the chunks
    all_chunks = "".join(events)
    assert "Error" in all_chunks or "error" in all_chunks


@pytest.mark.asyncio
async def test_stream_answer_simple(
    mock_anthropic_client, mock_kb_service, mock_findings_service, simple_nlu_result
):
    """Test simple text streaming without SSE formatting."""
    from ib_platform.answer.service import AnswerService

    answer_service = AnswerService(
        anthropic_client=mock_anthropic_client,
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    handler = StreamingHandler(answer_service)

    chunks = []
    async for chunk in handler.stream_answer_simple(
        question="How do I secure S3?",
        nlu_result=simple_nlu_result,
        aws_account_id=uuid4(),
    ):
        chunks.append(chunk)

    # Should have received text chunks (no SSE formatting)
    assert len(chunks) > 0
    assert all(not chunk.startswith("event:") for chunk in chunks)
    assert all(not chunk.startswith("data:") for chunk in chunks)


@pytest.mark.asyncio
async def test_format_sse_event():
    """Test SSE event formatting."""
    from ib_platform.answer.service import AnswerService

    # Create a minimal service for testing
    handler = StreamingHandler(None)  # type: ignore

    event = handler._format_sse_event(
        "test",
        {"key": "value", "number": 42},
    )

    assert event.startswith("event: test\n")
    assert "data:" in event
    assert event.endswith("\n\n")

    # Parse the JSON data
    data_line = [line for line in event.split("\n") if line.startswith("data:")][0]
    data = json.loads(data_line.replace("data: ", ""))

    assert data["key"] == "value"
    assert data["number"] == 42


def test_create_streaming_headers():
    """Test SSE header creation."""
    headers = StreamingHandler.create_streaming_headers()

    assert headers["Cache-Control"] == "no-cache"
    assert headers["Connection"] == "keep-alive"
    assert headers["Content-Type"] == "text/event-stream"
    assert headers["X-Accel-Buffering"] == "no"
