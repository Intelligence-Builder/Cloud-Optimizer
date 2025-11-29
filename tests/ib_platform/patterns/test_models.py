"""Tests for pattern engine data models."""

import re
from uuid import uuid4

import pytest

from ib_platform.patterns.models import (
    ConfidenceFactor,
    PatternCategory,
    PatternDefinition,
    PatternMatch,
    PatternPriority,
)


class TestPatternDefinition:
    """Tests for PatternDefinition model."""

    def test_create_pattern_with_defaults(self) -> None:
        """Test creating pattern with default values."""
        pattern = PatternDefinition(
            id=uuid4(),
            name="test_pattern",
            domain="test",
            category=PatternCategory.ENTITY,
            regex_pattern=r"\btest\b",
            output_type="test_entity",
        )

        assert pattern.base_confidence == 0.75
        assert pattern.priority == PatternPriority.NORMAL
        assert pattern.flags == re.IGNORECASE
        assert pattern.version == "1.0.0"

    def test_compiled_pattern_cached(self) -> None:
        """Test that compiled regex is cached."""
        pattern = PatternDefinition(
            id=uuid4(),
            name="test",
            domain="test",
            category=PatternCategory.ENTITY,
            regex_pattern=r"\btest\b",
            output_type="test",
        )

        # First access compiles
        compiled1 = pattern.compiled
        # Second access returns cached
        compiled2 = pattern.compiled

        assert compiled1 is compiled2

    def test_invalid_confidence_raises_error(self) -> None:
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="base_confidence must be"):
            PatternDefinition(
                id=uuid4(),
                name="test",
                domain="test",
                category=PatternCategory.ENTITY,
                regex_pattern=r"\btest\b",
                output_type="test",
                base_confidence=1.5,  # Invalid: > 1.0
            )

    def test_pattern_with_capture_groups(self) -> None:
        """Test pattern with named capture groups."""
        pattern = PatternDefinition(
            id=uuid4(),
            name="test",
            domain="test",
            category=PatternCategory.RELATIONSHIP,
            regex_pattern=r"(?P<source>\w+) links (?P<target>\w+)",
            output_type="links",
            capture_groups={"source": "source entity", "target": "target entity"},
        )

        assert pattern.capture_groups is not None
        assert "source" in pattern.capture_groups
        assert "target" in pattern.capture_groups


class TestPatternMatch:
    """Tests for PatternMatch model."""

    def test_create_pattern_match(self) -> None:
        """Test creating a pattern match."""
        pattern_id = uuid4()
        match = PatternMatch(
            pattern_id=pattern_id,
            pattern_name="test_pattern",
            domain="security",
            category=PatternCategory.ENTITY,
            matched_text="CVE-2021-44228",
            start_position=10,
            end_position=25,
            output_type="vulnerability",
            output_value="CVE-2021-44228",
        )

        assert match.pattern_id == pattern_id
        assert match.matched_text == "CVE-2021-44228"
        assert match.base_confidence == 0.75
        assert match.final_confidence == 0.75

    def test_match_with_captured_groups(self) -> None:
        """Test match with captured groups."""
        match = PatternMatch(
            pattern_id=uuid4(),
            pattern_name="test",
            domain="test",
            category=PatternCategory.RELATIONSHIP,
            matched_text="A mitigates B",
            start_position=0,
            end_position=13,
            output_type="mitigates",
            output_value="A mitigates B",
            captured_groups={"source": "A", "target": "B"},
        )

        assert match.captured_groups is not None
        assert match.captured_groups["source"] == "A"
        assert match.captured_groups["target"] == "B"

    def test_invalid_confidence_bounds(self) -> None:
        """Test that invalid confidence bounds raise errors."""
        with pytest.raises(ValueError, match="final_confidence must be"):
            PatternMatch(
                pattern_id=uuid4(),
                pattern_name="test",
                domain="test",
                category=PatternCategory.ENTITY,
                matched_text="test",
                start_position=0,
                end_position=4,
                output_type="test",
                output_value="test",
                final_confidence=1.5,  # Invalid
            )


class TestConfidenceFactor:
    """Tests for ConfidenceFactor model."""

    def test_create_positive_factor(self) -> None:
        """Test creating a positive confidence factor."""
        factor = ConfidenceFactor(
            name="test_factor",
            description="Test positive factor",
            weight=0.15,
            detector="detect_test",
            is_positive=True,
            max_adjustment=0.20,
        )

        assert factor.is_positive is True
        assert factor.weight == 0.15
        assert factor.max_adjustment == 0.20

    def test_create_negative_factor(self) -> None:
        """Test creating a negative confidence factor."""
        factor = ConfidenceFactor(
            name="negation",
            description="Negation decreases confidence",
            weight=0.20,
            detector="detect_negation",
            is_positive=False,
            max_adjustment=0.25,
        )

        assert factor.is_positive is False

    def test_invalid_weight_raises_error(self) -> None:
        """Test that invalid weight raises ValueError."""
        with pytest.raises(ValueError, match="weight must be"):
            ConfidenceFactor(
                name="test",
                description="test",
                weight=1.5,  # Invalid: > 1.0
                detector="test",
            )

    def test_invalid_max_adjustment_raises_error(self) -> None:
        """Test that invalid max_adjustment raises ValueError."""
        with pytest.raises(ValueError, match="max_adjustment must be"):
            ConfidenceFactor(
                name="test",
                description="test",
                weight=0.5,
                detector="test",
                max_adjustment=1.5,  # Invalid: > 1.0
            )

    def test_factor_with_category_filter(self) -> None:
        """Test factor with category filter."""
        factor = ConfidenceFactor(
            name="test",
            description="test",
            weight=0.1,
            detector="test",
            applies_to_categories=[PatternCategory.ENTITY, PatternCategory.CONTEXT],
        )

        assert factor.applies_to_categories is not None
        assert PatternCategory.ENTITY in factor.applies_to_categories

    def test_factor_with_domain_filter(self) -> None:
        """Test factor with domain filter."""
        factor = ConfidenceFactor(
            name="test",
            description="test",
            weight=0.1,
            detector="test",
            applies_to_domains=["security", "aws"],
        )

        assert factor.applies_to_domains is not None
        assert "security" in factor.applies_to_domains


class TestPatternEnums:
    """Tests for pattern enumerations."""

    def test_pattern_category_values(self) -> None:
        """Test PatternCategory enum values."""
        assert PatternCategory.ENTITY.value == "entity"
        assert PatternCategory.RELATIONSHIP.value == "relationship"
        assert PatternCategory.CONTEXT.value == "context"
        assert PatternCategory.TEMPORAL.value == "temporal"
        assert PatternCategory.QUANTITATIVE.value == "quantitative"

    def test_pattern_priority_values(self) -> None:
        """Test PatternPriority enum values."""
        assert PatternPriority.CRITICAL.value == "critical"
        assert PatternPriority.HIGH.value == "high"
        assert PatternPriority.NORMAL.value == "normal"
        assert PatternPriority.LOW.value == "low"
