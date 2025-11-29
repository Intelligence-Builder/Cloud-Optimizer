"""Pattern Engine - Entity and Relationship Detection.

This module provides pattern-based detection of entities and relationships
from unstructured text, with confidence scoring and domain-specific logic.
"""

from .detector import PatternDetector
from .matcher import PatternMatcher
from .models import (
    ConfidenceFactor,
    PatternCategory,
    PatternDefinition,
    PatternMatch,
    PatternPriority,
)
from .registry import PatternRegistry
from .scorer import ConfidenceScorer

__all__ = [
    "PatternDetector",
    "PatternMatcher",
    "PatternRegistry",
    "ConfidenceScorer",
    "PatternDefinition",
    "PatternMatch",
    "ConfidenceFactor",
    "PatternCategory",
    "PatternPriority",
]
