"""Chat API endpoints for Cloud Optimizer.

Provides endpoints for the AWS security chat interface with streaming support.
"""

import logging
import os
from typing import Annotated, Any

from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from cloud_optimizer.api.schemas.chat import (
    ChatRequest,
    ChatResponse,
    HealthCheckResponse,
)
from cloud_optimizer.database import AsyncSessionDep
from cloud_optimizer.services.findings import FindingsService
from ib_platform.answer.service import AnswerService
from ib_platform.answer.streaming import StreamingHandler
from ib_platform.kb.service import KnowledgeBaseService, get_kb_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Service dependencies
_answer_service: AnswerService | None = None
_streaming_handler: StreamingHandler | None = None


def get_kb() -> KnowledgeBaseService:
    """Get Knowledge Base service dependency.

    Returns:
        KnowledgeBaseService singleton instance

    Raises:
        HTTPException: If KB service cannot be loaded
    """
    kb = get_kb_service()
    if not kb.is_loaded():
        try:
            kb.load()
        except Exception as e:
            logger.error(f"Failed to load KB: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Knowledge Base service unavailable",
            ) from e
    return kb


def get_answer_service(
    kb: Annotated[KnowledgeBaseService, Depends(get_kb)],
    db: AsyncSessionDep,
) -> AnswerService:
    """Get or create AnswerService dependency.

    Args:
        kb: Knowledge Base service
        db: Database session

    Returns:
        AnswerService instance

    Raises:
        HTTPException: If Anthropic API key is not configured
    """
    global _answer_service

    if _answer_service is None:
        # Get Anthropic API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ANTHROPIC_API_KEY not configured",
            )

        # Create Anthropic client
        client = AsyncAnthropic(api_key=api_key)

        # Create findings service
        findings_service = FindingsService(db)

        # Create answer service
        _answer_service = AnswerService(
            anthropic_client=client,
            kb_service=kb,
            findings_service=findings_service,
        )

        logger.info("AnswerService initialized")

    return _answer_service


def get_streaming_handler(
    answer_service: Annotated[AnswerService, Depends(get_answer_service)],
) -> StreamingHandler:
    """Get or create StreamingHandler dependency.

    Args:
        answer_service: AnswerService instance

    Returns:
        StreamingHandler instance
    """
    global _streaming_handler

    if _streaming_handler is None:
        _streaming_handler = StreamingHandler(answer_service)
        logger.info("StreamingHandler initialized")

    return _streaming_handler


@router.get(  # type: ignore[misc]
    "/health",
    response_model=HealthCheckResponse,
    summary="Check chat service health",
    description="Check if chat service dependencies are available",
)
async def health_check(
    kb: Annotated[KnowledgeBaseService, Depends(get_kb)],
) -> HealthCheckResponse:
    """Check chat service health.

    Returns:
        HealthCheckResponse with service status
    """
    kb_loaded = kb.is_loaded()
    anthropic_available = bool(os.getenv("ANTHROPIC_API_KEY"))

    status_str = "healthy" if (kb_loaded and anthropic_available) else "degraded"

    return HealthCheckResponse(
        status=status_str,
        kb_loaded=kb_loaded,
        anthropic_available=anthropic_available,
    )


@router.post(  # type: ignore[misc]
    "/message",
    response_model=ChatResponse,
    summary="Send chat message",
    description="Send a message and receive a complete response (non-streaming)",
    responses={
        503: {"description": "Service unavailable (KB or Anthropic not configured)"},
    },
)
async def send_message(
    request: ChatRequest,
    answer_service: Annotated[AnswerService, Depends(get_answer_service)],
) -> ChatResponse:
    """Send a chat message and get complete response.

    Args:
        request: Chat request with message and optional context
        answer_service: Answer service dependency

    Returns:
        ChatResponse with complete answer and metadata

    Raises:
        HTTPException: If message processing fails
    """
    try:
        # For now, create a simple NLU result placeholder
        # This will be replaced with actual NLU service integration
        nlu_result = _create_simple_nlu_result(request.message)

        # Convert conversation history to dict format
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]

        # Generate answer
        answer = await answer_service.generate(
            question=request.message,
            nlu_result=nlu_result,
            aws_account_id=request.aws_account_id,
            conversation_history=conversation_history,
        )

        # Get context stats from answer service
        context = await answer_service.context_assembler.assemble(
            nlu_result=nlu_result,
            aws_account_id=request.aws_account_id,
        )

        return ChatResponse(
            answer=answer,
            intent=getattr(nlu_result, "intent", None),
            entities={
                "aws_services": getattr(
                    getattr(nlu_result, "entities", None), "aws_services", []
                ),
                "compliance_frameworks": getattr(
                    getattr(nlu_result, "entities", None), "compliance_frameworks", []
                ),
            },
            context_used={
                "kb_entries": len(context.kb_entries),
                "findings": len(context.findings),
                "documents": len(context.documents),
            },
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        ) from e


@router.post(  # type: ignore[misc]
    "/stream",
    summary="Stream chat response",
    description="Send a message and receive a streaming response via SSE",
    responses={
        200: {"description": "SSE stream of response chunks"},
        503: {"description": "Service unavailable (KB or Anthropic not configured)"},
    },
)
async def stream_message(
    request: ChatRequest,
    streaming_handler: Annotated[StreamingHandler, Depends(get_streaming_handler)],
) -> StreamingResponse:
    """Stream chat response using Server-Sent Events.

    Args:
        request: Chat request with message and optional context
        streaming_handler: Streaming handler dependency

    Returns:
        StreamingResponse with SSE events

    Raises:
        HTTPException: If streaming setup fails
    """
    try:
        # For now, create a simple NLU result placeholder
        # This will be replaced with actual NLU service integration
        nlu_result = _create_simple_nlu_result(request.message)

        # Convert conversation history to dict format
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]

        # Create streaming generator
        async def generate() -> Any:
            async for event in streaming_handler.stream_answer(
                question=request.message,
                nlu_result=nlu_result,
                aws_account_id=request.aws_account_id,
                conversation_history=conversation_history,
            ):
                yield event

        # Return streaming response
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers=StreamingHandler.create_streaming_headers(),
        )

    except Exception as e:
        logger.error(f"Error setting up stream: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start stream: {str(e)}",
        ) from e


def _create_simple_nlu_result(message: str) -> Any:
    """Create a simple NLU result placeholder.

    This is a temporary implementation until the full NLU pipeline is integrated.
    It performs basic keyword extraction for AWS services and compliance frameworks.

    Args:
        message: User's message

    Returns:
        Simple NLU result object
    """

    class SimpleEntities:
        def __init__(self) -> None:
            self.aws_services: list[str] = []
            self.compliance_frameworks: list[str] = []

    class SimpleNLUResult:
        def __init__(self, query: str) -> None:
            self.query = query
            self.intent = "general_question"
            self.entities = SimpleEntities()

            # Simple keyword extraction
            message_lower = query.lower()

            # Detect AWS services
            services = [
                "s3",
                "ec2",
                "rds",
                "lambda",
                "iam",
                "vpc",
                "cloudtrail",
                "cloudwatch",
                "kms",
            ]
            for service in services:
                if service in message_lower:
                    self.entities.aws_services.append(service.upper())

            # Detect compliance frameworks
            frameworks = ["cis", "nist", "hipaa", "pci", "soc2", "gdpr"]
            for framework in frameworks:
                if framework in message_lower:
                    self.entities.compliance_frameworks.append(framework.upper())

    return SimpleNLUResult(message)
