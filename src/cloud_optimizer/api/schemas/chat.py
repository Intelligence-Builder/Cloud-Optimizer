"""Chat API schemas for Cloud Optimizer.

Pydantic models for chat requests and responses.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single chat message.

    Attributes:
        role: Message role (user or assistant)
        content: Message content
    """

    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request to send a chat message.

    Attributes:
        message: User's message/question
        aws_account_id: Optional AWS account ID for finding queries
        conversation_history: Optional previous messages in conversation
    """

    message: str = Field(..., min_length=1, description="User's question or message")
    aws_account_id: UUID | None = Field(
        None, description="AWS account ID for finding queries"
    )
    conversation_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Previous messages in conversation",
    )


class ChatResponse(BaseModel):
    """Response to a chat message (non-streaming).

    Attributes:
        answer: Generated answer
        intent: Detected intent from NLU
        entities: Extracted entities from NLU
        context_used: Information about context used
    """

    answer: str = Field(..., description="Generated answer")
    intent: str | None = Field(None, description="Detected intent from NLU")
    entities: dict[str, Any] = Field(
        default_factory=dict, description="Extracted entities from NLU"
    )
    context_used: dict[str, int] = Field(
        default_factory=dict,
        description="Context usage stats (kb_entries, findings, documents)",
    )


class StreamEvent(BaseModel):
    """SSE stream event.

    Attributes:
        event: Event type (start, chunk, done, error)
        data: Event data
    """

    event: str = Field(..., description="Event type")
    data: dict[str, Any] = Field(..., description="Event data")


class HealthCheckResponse(BaseModel):
    """Health check response for chat service.

    Attributes:
        status: Service status
        kb_loaded: Whether KB is loaded
        anthropic_available: Whether Anthropic client is available
    """

    status: str = Field(..., description="Service status")
    kb_loaded: bool = Field(..., description="Whether KB is loaded")
    anthropic_available: bool = Field(
        ..., description="Whether Anthropic client is available"
    )
