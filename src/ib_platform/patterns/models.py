"""Pattern Engine Data Models.

Defines core data models for pattern definitions, matches, and confidence
scoring used throughout the pattern detection system.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID


class PatternCategory(str, Enum):
    """Categories of patterns for entity and relationship detection."""

    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    CONTEXT = "context"
    TEMPORAL = "temporal"
    QUANTITATIVE = "quantitative"


class PatternPriority(str, Enum):
    """Priority levels for pattern matching."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class PatternDefinition:
    """Core pattern definition for entity/relationship detection.

    Attributes:
        id: Unique identifier for the pattern
        name: Human-readable pattern name
        domain: Domain this pattern belongs to (e.g., "security", "aws")
        category: Type of pattern (entity, relationship, etc.)
        regex_pattern: Regular expression pattern string
        output_type: Type of entity/relationship this pattern produces
        flags: Regex compilation flags (default: re.IGNORECASE)
        capture_groups: Named capture groups mapping
        base_confidence: Base confidence score (0.0-1.0)
        priority: Pattern matching priority
        requires_context: Context markers that must be present
        excludes_context: Context markers that disqualify a match
        version: Pattern version for tracking changes
        description: Human-readable description
        examples: Example texts that match this pattern
        tags: Optional tags for categorization
    """

    # Required fields first (no defaults)
    id: UUID
    name: str
    domain: str
    category: PatternCategory
    regex_pattern: str
    output_type: str

    # Optional fields with defaults
    flags: int = re.IGNORECASE
    capture_groups: Optional[Dict[str, str]] = None
    base_confidence: float = 0.75
    priority: PatternPriority = PatternPriority.NORMAL
    requires_context: Optional[List[str]] = None
    excludes_context: Optional[List[str]] = None
    version: str = "1.0.0"
    description: str = ""
    examples: Optional[List[str]] = None
    tags: Optional[List[str]] = None

    # Cached compiled pattern
    _compiled: Optional[re.Pattern[str]] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate confidence bounds after initialization."""
        if not 0.0 <= self.base_confidence <= 1.0:
            raise ValueError(
                f"base_confidence must be between 0.0 and 1.0, "
                f"got {self.base_confidence}"
            )

    @property
    def compiled(self) -> re.Pattern[str]:
        """Get compiled regex pattern (cached).

        Returns:
            Compiled regular expression pattern
        """
        if self._compiled is None:
            self._compiled = re.compile(self.regex_pattern, self.flags)
        return self._compiled


@dataclass
class PatternMatch:
    """Result of pattern matching operation.

    Represents a single match of a pattern in text, including position,
    extracted values, and confidence scoring information.

    Attributes:
        pattern_id: ID of the pattern that matched
        pattern_name: Name of the pattern that matched
        domain: Domain of the pattern
        category: Category of the pattern
        matched_text: The actual text that matched
        start_position: Character offset where match starts
        end_position: Character offset where match ends
        output_type: Type of entity/relationship produced
        output_value: Extracted primary value
        captured_groups: Named capture group values
        base_confidence: Pattern's base confidence score
        final_confidence: Confidence after applying factors
        applied_factors: List of confidence factors applied
        surrounding_context: Text context around the match
        metadata: Additional metadata for the match
    """

    pattern_id: UUID
    pattern_name: str
    domain: str
    category: PatternCategory

    matched_text: str
    start_position: int
    end_position: int

    output_type: str
    output_value: str
    captured_groups: Optional[Dict[str, str]] = None

    base_confidence: float = 0.75
    final_confidence: float = 0.75
    applied_factors: Optional[List[Dict[str, Any]]] = None

    surrounding_context: str = ""
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate confidence bounds after initialization."""
        if not 0.0 <= self.base_confidence <= 1.0:
            raise ValueError(
                f"base_confidence must be between 0.0 and 1.0, "
                f"got {self.base_confidence}"
            )
        if not 0.0 <= self.final_confidence <= 1.0:
            raise ValueError(
                f"final_confidence must be between 0.0 and 1.0, "
                f"got {self.final_confidence}"
            )


@dataclass
class ConfidenceFactor:
    """Factor that adjusts confidence scores based on context.

    Confidence factors analyze the context around a match and adjust
    the confidence score up or down based on detected signals.

    Attributes:
        name: Unique name for the factor
        description: Human-readable description
        weight: How much this factor affects confidence
        detector: Name of detector function (e.g., "detect_negation")
        is_positive: Whether this factor increases confidence
        max_adjustment: Maximum adjustment allowed
        applies_to_categories: Pattern categories this applies to
        applies_to_domains: Domains this factor applies to
    """

    name: str
    description: str
    weight: float
    detector: str
    is_positive: bool = True
    max_adjustment: float = 0.2
    applies_to_categories: Optional[List[PatternCategory]] = None
    applies_to_domains: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Validate weight and max_adjustment bounds."""
        if not 0.0 <= abs(self.weight) <= 1.0:
            raise ValueError(
                f"weight must be between 0.0 and 1.0, got {self.weight}"
            )
        if not 0.0 <= self.max_adjustment <= 1.0:
            raise ValueError(
                f"max_adjustment must be between 0.0 and 1.0, "
                f"got {self.max_adjustment}"
            )
