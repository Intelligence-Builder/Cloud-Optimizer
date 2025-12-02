"""Answer Generation Engine for Cloud Optimizer.

This module provides the answer generation pipeline that produces expert-level
security responses using LLM (Claude) with context from the knowledge base,
findings, and documents. Supports streaming responses for real-time UI feedback.
"""

from ib_platform.answer.context import AnswerContext, ContextAssembler
from ib_platform.answer.formatter import ResponseFormatter
from ib_platform.answer.service import AnswerService
from ib_platform.answer.streaming import StreamingHandler

__all__ = [
    "AnswerContext",
    "ContextAssembler",
    "AnswerService",
    "StreamingHandler",
    "ResponseFormatter",
]
