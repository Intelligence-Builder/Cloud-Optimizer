"""SSE streaming handler for answer generation.

Provides Server-Sent Events (SSE) streaming for real-time response delivery
to the chat interface.
"""

import json
import logging
from typing import Any, AsyncIterator
from uuid import UUID

from ib_platform.answer.service import AnswerService

logger = logging.getLogger(__name__)


class StreamingHandler:
    """Handle SSE streaming of answer chunks.

    Wraps the AnswerService to provide Server-Sent Events formatted streaming
    for real-time response delivery to chat interfaces.

    Example:
        >>> handler = StreamingHandler(answer_service)
        >>> async for event in handler.stream_answer("How to secure S3?", nlu_result):
        ...     # Send event to client
        ...     pass
    """

    def __init__(self, answer_service: AnswerService) -> None:
        """Initialize the streaming handler.

        Args:
            answer_service: AnswerService instance for generating responses
        """
        self.answer_service = answer_service

    async def stream_answer(
        self,
        question: str,
        nlu_result: Any,
        aws_account_id: UUID | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        """Generate SSE events for streaming response.

        Args:
            question: User's question
            nlu_result: NLU processing result with intent and entities
            aws_account_id: Optional AWS account ID for finding queries
            conversation_history: Optional previous conversation messages

        Yields:
            SSE-formatted event strings (event: type\\ndata: {...}\\n\\n)

        Example:
            >>> async for event in handler.stream_answer("How to secure RDS?", nlu_result):
            ...     yield event  # In FastAPI StreamingResponse
        """
        try:
            # Send start event
            yield self._format_sse_event("start", {"type": "start"})

            # Stream answer chunks
            full_response = ""
            chunk_count = 0

            async for chunk in self.answer_service.generate_streaming(
                question=question,
                nlu_result=nlu_result,
                aws_account_id=aws_account_id,
                conversation_history=conversation_history,
            ):
                full_response += chunk
                chunk_count += 1
                yield self._format_sse_event(
                    "chunk",
                    {
                        "content": chunk,
                        "chunk_number": chunk_count,
                    },
                )

            # Extract metadata from NLU result
            intent = getattr(nlu_result, "intent", None)
            entities = getattr(nlu_result, "entities", None)

            metadata = {
                "type": "done",
                "total_chunks": chunk_count,
                "response_length": len(full_response),
            }

            if intent:
                metadata["intent"] = (
                    intent.value if hasattr(intent, "value") else str(intent)
                )

            if entities:
                metadata["entities"] = {
                    "aws_services": getattr(entities, "aws_services", []),
                    "compliance_frameworks": getattr(
                        entities, "compliance_frameworks", []
                    ),
                }

            # Send completion event with metadata
            yield self._format_sse_event("done", metadata)

            logger.info(
                f"Completed streaming answer: {chunk_count} chunks, "
                f"{len(full_response)} characters"
            )

        except Exception as e:
            logger.error(f"Error during streaming: {e}", exc_info=True)
            yield self._format_sse_event(
                "error",
                {
                    "type": "error",
                    "message": str(e),
                    "error_type": type(e).__name__,
                },
            )

    async def stream_answer_simple(
        self,
        question: str,
        nlu_result: Any,
        aws_account_id: UUID | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        """Generate simple text streaming (no SSE formatting).

        Useful for clients that just want the raw text stream without SSE events.

        Args:
            question: User's question
            nlu_result: NLU processing result with intent and entities
            aws_account_id: Optional AWS account ID for finding queries
            conversation_history: Optional previous conversation messages

        Yields:
            Raw text chunks

        Example:
            >>> async for chunk in handler.stream_answer_simple("Secure EC2?", nlu_result):
            ...     print(chunk, end="")
        """
        try:
            async for chunk in self.answer_service.generate_streaming(
                question=question,
                nlu_result=nlu_result,
                aws_account_id=aws_account_id,
                conversation_history=conversation_history,
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Error during simple streaming: {e}", exc_info=True)
            yield f"\n\n⚠️ Error: {str(e)}"

    def _format_sse_event(self, event: str, data: dict[str, Any]) -> str:
        """Format data as SSE event.

        Args:
            event: Event type (e.g., "start", "chunk", "done", "error")
            data: Event data to serialize as JSON

        Returns:
            SSE-formatted event string

        Example:
            >>> handler._format_sse_event("chunk", {"content": "Hello"})
            'event: chunk\\ndata: {"content": "Hello"}\\n\\n'
        """
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    @staticmethod
    def create_streaming_headers() -> dict[str, str]:
        """Create headers for SSE streaming response.

        Returns:
            Dictionary of headers for SSE response

        Example:
            >>> headers = StreamingHandler.create_streaming_headers()
            >>> # Use with FastAPI StreamingResponse
            >>> StreamingResponse(generate(), headers=headers)
        """
        return {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
