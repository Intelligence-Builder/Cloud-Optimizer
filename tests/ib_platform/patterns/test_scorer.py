"""Tests for confidence scorer."""

from uuid import uuid4

import pytest

from ib_platform.patterns.models import (
    ConfidenceFactor,
    PatternCategory,
    PatternMatch,
)
from ib_platform.patterns.scorer import ConfidenceScorer, get_default_confidence_factors


class TestConfidenceScorer:
    """Tests for ConfidenceScorer class."""

    def test_score_without_factors(self) -> None:
        """Test scoring with no confidence factors applied."""
        scorer = ConfidenceScorer([])

        match = PatternMatch(
            pattern_id=uuid4(),
            pattern_name="test",
            domain="test",
            category=PatternCategory.ENTITY,
            matched_text="test",
            start_position=0,
            end_position=4,
            output_type="test",
            output_value="test",
            base_confidence=0.75,
        )

        final_score = scorer.score(match, "test text")

        assert final_score == 0.75  # No factors, so base confidence
        assert match.final_confidence == 0.75

    def test_score_with_positive_factor(
        self, sample_confidence_factors: list[ConfidenceFactor]
    ) -> None:
        """Test scoring with positive confidence factor."""
        scorer = ConfidenceScorer(sample_confidence_factors)

        match = PatternMatch(
            pattern_id=uuid4(),
            pattern_name="test",
            domain="test",
            category=PatternCategory.ENTITY,
            matched_text="CVE-2021-44228",
            start_position=0,
            end_position=15,
            output_type="vulnerability",
            output_value="CVE-2021-44228",
            base_confidence=0.75,
            surrounding_context="Costs $50,000 to fix CVE-2021-44228",
        )

        final_score = scorer.score(match, "Costs $50,000 to fix CVE-2021-44228")

        # Should be boosted by monetary context factor
        assert final_score > 0.75
        assert match.applied_factors is not None
        assert len(match.applied_factors) > 0

    def test_score_with_negative_factor(
        self, sample_confidence_factors: list[ConfidenceFactor]
    ) -> None:
        """Test scoring with negative confidence factor."""
        scorer = ConfidenceScorer(sample_confidence_factors)

        match = PatternMatch(
            pattern_id=uuid4(),
            pattern_name="test",
            domain="test",
            category=PatternCategory.ENTITY,
            matched_text="CVE-2021-44228",
            start_position=20,
            end_position=35,
            output_type="vulnerability",
            output_value="CVE-2021-44228",
            base_confidence=0.85,
            surrounding_context="This is not a CVE-2021-44228 vulnerability",
        )

        final_score = scorer.score(
            match, "This is not a CVE-2021-44228 vulnerability"
        )

        # Should be decreased by negation factor
        assert final_score < 0.85
        assert match.applied_factors is not None
        assert any(f["name"] == "negation_presence" for f in match.applied_factors)

    def test_score_bounds_at_zero(self) -> None:
        """Test that score never goes below 0.0."""
        # Create very strong negative factor
        strong_negative = ConfidenceFactor(
            name="strong_negative",
            description="Very strong negative",
            weight=1.0,
            detector="detect_negation",
            is_positive=False,
            max_adjustment=1.0,
        )

        scorer = ConfidenceScorer([strong_negative])

        match = PatternMatch(
            pattern_id=uuid4(),
            pattern_name="test",
            domain="test",
            category=PatternCategory.ENTITY,
            matched_text="test",
            start_position=0,
            end_position=4,
            output_type="test",
            output_value="test",
            base_confidence=0.5,
            surrounding_context="not test",
        )

        final_score = scorer.score(match, "not test")

        assert final_score >= 0.0  # Should be bounded at 0.0

    def test_score_bounds_at_one(self) -> None:
        """Test that score never exceeds 1.0."""
        # Create very strong positive factor
        strong_positive = ConfidenceFactor(
            name="strong_positive",
            description="Very strong positive",
            weight=1.0,
            detector="detect_monetary",
            is_positive=True,
            max_adjustment=1.0,
        )

        scorer = ConfidenceScorer([strong_positive])

        match = PatternMatch(
            pattern_id=uuid4(),
            pattern_name="test",
            domain="test",
            category=PatternCategory.ENTITY,
            matched_text="test",
            start_position=0,
            end_position=4,
            output_type="test",
            output_value="test",
            base_confidence=0.9,
            surrounding_context="$10,000 test",
        )

        final_score = scorer.score(match, "$10,000 test")

        assert final_score <= 1.0  # Should be bounded at 1.0

    def test_apply_factors_returns_details(
        self, confidence_scorer: ConfidenceScorer
    ) -> None:
        """Test that apply_factors returns detailed information."""
        match = PatternMatch(
            pattern_id=uuid4(),
            pattern_name="test",
            domain="test",
            category=PatternCategory.ENTITY,
            matched_text="test",
            start_position=0,
            end_position=4,
            output_type="test",
            output_value="test",
            base_confidence=0.75,
            surrounding_context="not $100 test",
        )

        score, applied = confidence_scorer.apply_factors(
            match, "not $100 test"
        )

        assert isinstance(score, float)
        assert isinstance(applied, list)
        for factor in applied:
            assert "name" in factor
            assert "adjustment" in factor
            assert "old_score" in factor
            assert "new_score" in factor

    def test_factor_category_filter(self) -> None:
        """Test that factors respect category filters."""
        # Factor only applies to RELATIONSHIP category
        factor = ConfidenceFactor(
            name="test",
            description="test",
            weight=0.5,
            detector="detect_monetary",
            applies_to_categories=[PatternCategory.RELATIONSHIP],
        )

        scorer = ConfidenceScorer([factor])

        # Create ENTITY match (should not apply)
        entity_match = PatternMatch(
            pattern_id=uuid4(),
            pattern_name="test",
            domain="test",
            category=PatternCategory.ENTITY,
            matched_text="test",
            start_position=0,
            end_position=4,
            output_type="test",
            output_value="test",
            base_confidence=0.75,
            surrounding_context="$100 test",
        )

        score = scorer.score(entity_match, "$100 test")

        # Factor should not apply to ENTITY
        assert score == 0.75  # Unchanged

    def test_factor_domain_filter(self) -> None:
        """Test that factors respect domain filters."""
        # Factor only applies to "security" domain
        factor = ConfidenceFactor(
            name="test",
            description="test",
            weight=0.5,
            detector="detect_monetary",
            applies_to_domains=["security"],
        )

        scorer = ConfidenceScorer([factor])

        # Create match in "aws" domain (should not apply)
        aws_match = PatternMatch(
            pattern_id=uuid4(),
            pattern_name="test",
            domain="aws",
            category=PatternCategory.ENTITY,
            matched_text="test",
            start_position=0,
            end_position=4,
            output_type="test",
            output_value="test",
            base_confidence=0.75,
            surrounding_context="$100 test",
        )

        score = scorer.score(aws_match, "$100 test")

        # Factor should not apply to aws domain
        assert score == 0.75  # Unchanged

    def test_get_default_factors(self) -> None:
        """Test getting default confidence factors."""
        factors = get_default_confidence_factors()

        assert len(factors) == 8
        factor_names = {f.name for f in factors}
        assert "negation_presence" in factor_names
        assert "monetary_context" in factor_names
        assert "keyword_density" in factor_names

    def test_detect_negation(self, confidence_scorer: ConfidenceScorer) -> None:
        """Test negation detection."""
        result = confidence_scorer._detect_negation(
            None, "This is not a problem", ""  # type: ignore
        )
        assert result is True

        result = confidence_scorer._detect_negation(
            None, "This is a problem", ""  # type: ignore
        )
        assert result is False

    def test_detect_monetary(self, confidence_scorer: ConfidenceScorer) -> None:
        """Test monetary detection."""
        result = confidence_scorer._detect_monetary(
            None, "Costs $50,000 to fix", ""  # type: ignore
        )
        assert result is True

        result = confidence_scorer._detect_monetary(
            None, "No cost mentioned", ""  # type: ignore
        )
        assert result is False

    def test_detect_percentage(self, confidence_scorer: ConfidenceScorer) -> None:
        """Test percentage detection."""
        result = confidence_scorer._detect_percentage(
            None, "95.5% success rate", ""  # type: ignore
        )
        assert result is True

        result = confidence_scorer._detect_percentage(
            None, "No percentage here", ""  # type: ignore
        )
        assert result is False

    def test_detect_temporal(self, confidence_scorer: ConfidenceScorer) -> None:
        """Test temporal detection."""
        result = confidence_scorer._detect_temporal(
            None, "Fixed yesterday in production", ""  # type: ignore
        )
        assert result is True

        result = confidence_scorer._detect_temporal(
            None, "No time reference", ""  # type: ignore
        )
        assert result is False

    def test_multiple_factors_combine(self) -> None:
        """Test that multiple factors can combine."""
        factors = [
            ConfidenceFactor(
                name="factor1",
                description="First factor",
                weight=0.10,
                detector="detect_monetary",
                is_positive=True,
                max_adjustment=0.10,
            ),
            ConfidenceFactor(
                name="factor2",
                description="Second factor",
                weight=0.10,
                detector="detect_percentage",
                is_positive=True,
                max_adjustment=0.10,
            ),
        ]

        scorer = ConfidenceScorer(factors)

        match = PatternMatch(
            pattern_id=uuid4(),
            pattern_name="test",
            domain="test",
            category=PatternCategory.ENTITY,
            matched_text="test",
            start_position=0,
            end_position=4,
            output_type="test",
            output_value="test",
            base_confidence=0.70,
            surrounding_context="$100 cost with 95% success",
        )

        final_score = scorer.score(match, "$100 cost with 95% success")

        # Both factors should apply
        assert final_score > 0.70
        assert match.applied_factors is not None
        assert len(match.applied_factors) == 2
