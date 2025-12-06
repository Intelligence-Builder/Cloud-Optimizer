"""
Natural Language Understanding (NLU) module for Cloud Optimizer chat interface.

This module provides intent classification, entity extraction, and conversation
context tracking for the AWS security expert system.
"""

from ib_platform.nlu.context import ConversationContext, Message
from ib_platform.nlu.entities import EntityExtractor
from ib_platform.nlu.intents import (
    Intent,
    get_all_intent_examples,
    get_intent_description,
    get_intent_examples,
)
from ib_platform.nlu.models import NLUEntities, NLUResult
from ib_platform.nlu.service import NLUService

__all__ = [
    "Intent",
    "get_intent_examples",
    "get_all_intent_examples",
    "get_intent_description",
    "NLUEntities",
    "NLUResult",
    "EntityExtractor",
    "ConversationContext",
    "Message",
    "NLUService",
]
