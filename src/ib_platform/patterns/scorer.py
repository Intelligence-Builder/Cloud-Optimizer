"""Confidence Scorer - Context-based Confidence Adjustment.

Applies confidence factors to pattern matches based on surrounding context
to produce more accurate confidence scores.
"""

import logging
import re
from typing import Any, Dict, List, Tuple

from .models import ConfidenceFactor, PatternCategory, PatternMatch

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Confidence scoring system with pluggable factors.

    Analyzes pattern matches in context and applies confidence factors
    to adjust scores based on detected signals (negation, temporal proximity,
    keyword density, etc.).

    Example:
        >>> factors = get_default_confidence_factors()
        >>> scorer = ConfidenceScorer(factors)
        >>> final_score = scorer.score(match, full_text)
    """

    def __init__(self, factors: List[ConfidenceFactor]) -> None:
        """Initialize scorer with confidence factors.

        Args:
            factors: List of confidence factors to apply
        """
        self.factors = factors
        logger.info(
            "Confidence scorer initialized",
            extra={"factors_count": len(factors)},
        )

    def score(self, match: PatternMatch, text: str) -> float:
        """Calculate final confidence score for a match.

        Args:
            match: Pattern match to score
            text: Full text containing the match

        Returns:
            Final confidence score (0.0-1.0)

        Example:
            >>> final_confidence = scorer.score(match, document_text)
            >>> 0.0 <= final_confidence <= 1.0
            True
        """
        final_score, applied = self.apply_factors(match, text)

        # Update match object
        match.final_confidence = final_score
        match.applied_factors = applied

        logger.debug(
            "Confidence scoring complete",
            extra={
                "pattern_name": match.pattern_name,
                "base_confidence": match.base_confidence,
                "final_confidence": final_score,
                "factors_applied": len(applied),
            },
        )

        return final_score

    def apply_factors(
        self, match: PatternMatch, text: str
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Apply all applicable confidence factors to a match.

        Args:
            match: Pattern match to analyze
            text: Full text containing the match

        Returns:
            Tuple of (final_score, list of applied factors)

        Example:
            >>> score, factors = scorer.apply_factors(match, text)
            >>> len(factors) > 0
            True
        """
        score = match.base_confidence
        applied: List[Dict[str, Any]] = []

        for factor in self.factors:
            # Check if factor applies to this match
            if not self._factor_applies(factor, match):
                continue

            # Detect if factor condition is present
            detected = self._detect_factor(
                factor, match, match.surrounding_context, text
            )

            if detected:
                # Calculate adjustment
                adjustment = factor.weight * factor.max_adjustment
                if not factor.is_positive:
                    adjustment = -adjustment

                # Apply adjustment
                old_score = score
                score = max(0.0, min(1.0, score + adjustment))

                # Record applied factor
                applied.append(
                    {
                        "name": factor.name,
                        "adjustment": adjustment,
                        "old_score": old_score,
                        "new_score": score,
                    }
                )

                logger.debug(
                    "Confidence factor applied",
                    extra={
                        "factor_name": factor.name,
                        "adjustment": adjustment,
                        "old_score": old_score,
                        "new_score": score,
                    },
                )

        return score, applied

    def _factor_applies(self, factor: ConfidenceFactor, match: PatternMatch) -> bool:
        """Check if a factor applies to a match.

        Args:
            factor: Confidence factor
            match: Pattern match

        Returns:
            True if factor should be applied to this match
        """
        # Check category filter
        if factor.applies_to_categories:
            if match.category not in factor.applies_to_categories:
                return False

        # Check domain filter
        if factor.applies_to_domains:
            if match.domain not in factor.applies_to_domains:
                return False

        return True

    def _detect_factor(
        self,
        factor: ConfidenceFactor,
        match: PatternMatch,
        context: str,
        full_text: str,
    ) -> bool:
        """Detect if a factor's condition is present.

        Args:
            factor: Confidence factor to check
            match: Pattern match
            context: Surrounding context
            full_text: Full document text

        Returns:
            True if factor condition is detected
        """
        # Map detector names to detection functions
        detector_map = {
            "detect_negation": self._detect_negation,
            "detect_uncertainty": self._detect_uncertainty,
            "detect_monetary": self._detect_monetary,
            "detect_percentage": self._detect_percentage,
            "detect_temporal": self._detect_temporal,
            "detect_keyword_density": self._detect_keyword_density,
            "detect_multi_occurrence": self._detect_multi_occurrence,
        }

        detector_func = detector_map.get(factor.detector)
        if detector_func is None:
            logger.warning(
                f"Unknown detector function: {factor.detector}",
                extra={"factor_name": factor.name},
            )
            return False

        return detector_func(match, context, full_text)

    def _detect_negation(
        self, match: PatternMatch, context: str, full_text: str
    ) -> bool:
        """Detect negation words near the match."""
        negation_words = r"\b(not|no|never|none|neither|nor|without)\b"
        return bool(re.search(negation_words, context, re.IGNORECASE))

    def _detect_uncertainty(
        self, match: PatternMatch, context: str, full_text: str
    ) -> bool:
        """Detect uncertainty markers near the match."""
        uncertainty_words = r"\b(maybe|might|possibly|perhaps|potentially|unclear)\b"
        return bool(re.search(uncertainty_words, context, re.IGNORECASE))

    def _detect_monetary(
        self, match: PatternMatch, context: str, full_text: str
    ) -> bool:
        """Detect monetary amounts near the match."""
        monetary_pattern = r"[\$£€]\s*[\d,]+\.?\d*|\d+\s*(dollars|euros|pounds)"
        return bool(re.search(monetary_pattern, context, re.IGNORECASE))

    def _detect_percentage(
        self, match: PatternMatch, context: str, full_text: str
    ) -> bool:
        """Detect percentages near the match."""
        percentage_pattern = r"\d+\.?\d*\s*%"
        return bool(re.search(percentage_pattern, context))

    def _detect_temporal(
        self, match: PatternMatch, context: str, full_text: str
    ) -> bool:
        """Detect temporal references near the match."""
        temporal_pattern = (
            r"\b(today|yesterday|tomorrow|now|currently|recently|"
            r"\d{4}-\d{2}-\d{2}|january|february|march|april|may|june|"
            r"july|august|september|october|november|december)\b"
        )
        return bool(re.search(temporal_pattern, context, re.IGNORECASE))

    def _detect_keyword_density(
        self, match: PatternMatch, context: str, full_text: str
    ) -> bool:
        """Detect high density of domain keywords."""
        # Simple heuristic: check if context has multiple domain-related words
        domain_keywords = {
            "security": r"\b(security|vulnerability|threat|risk|attack|"
            r"breach|exploit|malware)\b",
            "aws": r"\b(aws|amazon|ec2|s3|lambda|iam|vpc|cloudwatch)\b",
        }

        pattern = domain_keywords.get(match.domain)
        if not pattern:
            return False

        matches = re.findall(pattern, context, re.IGNORECASE)
        return len(matches) >= 3

    def _detect_multi_occurrence(
        self, match: PatternMatch, context: str, full_text: str
    ) -> bool:
        """Detect if matched value occurs multiple times in document."""
        # Count occurrences of the matched value in full text
        escaped_value = re.escape(match.output_value)
        occurrences = len(re.findall(escaped_value, full_text, re.IGNORECASE))
        return occurrences >= 2


def get_default_confidence_factors() -> List[ConfidenceFactor]:
    """Get built-in confidence factors.

    Returns:
        List of default confidence factors for common patterns

    Example:
        >>> factors = get_default_confidence_factors()
        >>> len(factors)
        8
    """
    return [
        ConfidenceFactor(
            name="monetary_context",
            description="Nearby monetary amounts increase confidence",
            weight=0.15,
            detector="detect_monetary",
            is_positive=True,
            max_adjustment=0.15,
        ),
        ConfidenceFactor(
            name="percentage_context",
            description="Nearby percentages increase confidence",
            weight=0.10,
            detector="detect_percentage",
            is_positive=True,
            max_adjustment=0.10,
        ),
        ConfidenceFactor(
            name="temporal_proximity",
            description="Nearby temporal references increase confidence",
            weight=0.10,
            detector="detect_temporal",
            is_positive=True,
            max_adjustment=0.10,
        ),
        ConfidenceFactor(
            name="negation_presence",
            description="Negation words decrease confidence",
            weight=0.20,
            detector="detect_negation",
            is_positive=False,
            max_adjustment=0.20,
        ),
        ConfidenceFactor(
            name="uncertainty_markers",
            description="Uncertainty words decrease confidence",
            weight=0.15,
            detector="detect_uncertainty",
            is_positive=False,
            max_adjustment=0.15,
        ),
        ConfidenceFactor(
            name="keyword_density",
            description="High domain keyword density increases confidence",
            weight=0.10,
            detector="detect_keyword_density",
            is_positive=True,
            max_adjustment=0.10,
        ),
        ConfidenceFactor(
            name="multi_occurrence",
            description="Multiple occurrences increase confidence",
            weight=0.10,
            detector="detect_multi_occurrence",
            is_positive=True,
            max_adjustment=0.10,
        ),
        ConfidenceFactor(
            name="relationship_support",
            description="Participation in relationships increases confidence",
            weight=0.15,
            detector="detect_relationship_support",
            is_positive=True,
            max_adjustment=0.15,
        ),
    ]
