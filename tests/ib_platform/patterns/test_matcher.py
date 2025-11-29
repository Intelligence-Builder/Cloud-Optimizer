"""Tests for pattern matcher."""

import time

import pytest

from ib_platform.patterns.matcher import PatternMatcher
from ib_platform.patterns.models import PatternDefinition


class TestPatternMatcher:
    """Tests for PatternMatcher class."""

    def test_match_single_pattern(
        self, sample_cve_pattern: PatternDefinition, sample_text_with_cves: str
    ) -> None:
        """Test matching a single pattern."""
        matcher = PatternMatcher()
        matches = matcher.match(sample_text_with_cves, sample_cve_pattern)

        assert len(matches) == 3  # Three CVE references in sample text
        assert all(m.pattern_name == "cve_reference" for m in matches)

    def test_match_extracts_correct_text(
        self, sample_cve_pattern: PatternDefinition
    ) -> None:
        """Test that match extracts correct matched text."""
        matcher = PatternMatcher()
        text = "Found CVE-2021-44228 vulnerability"

        matches = matcher.match(text, sample_cve_pattern)

        assert len(matches) == 1
        assert matches[0].matched_text == "CVE-2021-44228"
        assert matches[0].output_value == "CVE-2021-44228"

    def test_match_records_position(
        self, sample_cve_pattern: PatternDefinition
    ) -> None:
        """Test that match records correct positions."""
        matcher = PatternMatcher()
        text = "Found CVE-2021-44228 in production"

        matches = matcher.match(text, sample_cve_pattern)

        assert len(matches) == 1
        assert matches[0].start_position == 6
        assert matches[0].end_position == 20  # Correct end position

    def test_match_extracts_context(
        self, sample_cve_pattern: PatternDefinition
    ) -> None:
        """Test that match extracts surrounding context."""
        matcher = PatternMatcher()
        text = "Critical vulnerability CVE-2021-44228 found in production system"

        matches = matcher.match(text, sample_cve_pattern)

        assert len(matches) == 1
        assert "Critical vulnerability" in matches[0].surrounding_context
        assert "found in production" in matches[0].surrounding_context

    def test_match_with_capture_groups(
        self, sample_relationship_pattern: PatternDefinition
    ) -> None:
        """Test matching pattern with capture groups."""
        matcher = PatternMatcher()
        text = "Firewall mitigates vulnerability"

        matches = matcher.match(text, sample_relationship_pattern)

        assert len(matches) == 1
        assert matches[0].captured_groups is not None
        assert matches[0].captured_groups["source"] == "Firewall"
        assert matches[0].captured_groups["target"] == "vulnerability"

    def test_match_no_matches_returns_empty(
        self, sample_cve_pattern: PatternDefinition
    ) -> None:
        """Test that no matches returns empty list."""
        matcher = PatternMatcher()
        text = "This text has no CVE references"

        matches = matcher.match(text, sample_cve_pattern)

        assert len(matches) == 0

    def test_match_all_multiple_patterns(
        self,
        sample_cve_pattern: PatternDefinition,
        sample_iam_pattern: PatternDefinition,
    ) -> None:
        """Test matching multiple patterns at once."""
        matcher = PatternMatcher()
        text = "CVE-2021-44228 affects IAM policy configuration"

        patterns = [sample_cve_pattern, sample_iam_pattern]
        matches = matcher.match_all(text, patterns)

        assert len(matches) == 2
        pattern_names = {m.pattern_name for m in matches}
        assert "cve_reference" in pattern_names
        assert "iam_policy" in pattern_names

    def test_extract_context_with_window(self) -> None:
        """Test context extraction with custom window size."""
        matcher = PatternMatcher()
        text = "A" * 50 + "MATCH" + "B" * 50

        context = matcher.extract_context(text, 50, 55, window=10)

        # Actual: 10 before + 5 match + 10 after + ellipsis chars (3+3) = 31
        assert len(context) <= 35  # Be generous for ellipsis
        assert "MATCH" in context

    def test_extract_context_at_boundaries(self) -> None:
        """Test context extraction at text boundaries."""
        matcher = PatternMatcher()
        text = "MATCH at start"

        context = matcher.extract_context(text, 0, 5, window=10)

        assert context.startswith("MATCH")
        assert not context.startswith("...")

    def test_performance_large_text(
        self, sample_cve_pattern: PatternDefinition
    ) -> None:
        """Test matching performance on large text (< 20ms per KB)."""
        matcher = PatternMatcher()

        # Generate 10KB of text with some CVE references
        text = ("CVE-2021-44228 " + "padding text " * 100) * 50
        text_size_kb = len(text) / 1024

        start_time = time.perf_counter()
        matches = matcher.match(text, sample_cve_pattern)
        elapsed_time = time.perf_counter() - start_time

        time_per_kb = (elapsed_time / text_size_kb) * 1000  # Convert to ms

        assert len(matches) > 0  # Should find matches
        assert time_per_kb < 20, f"Performance: {time_per_kb:.2f}ms per KB"

    def test_match_case_insensitive(
        self, sample_iam_pattern: PatternDefinition
    ) -> None:
        """Test case-insensitive matching."""
        matcher = PatternMatcher()
        text = "IAM Policy configuration and iam role settings"

        matches = matcher.match(text, sample_iam_pattern)

        assert len(matches) == 2  # Should match both "IAM Policy" and "iam role"

    def test_match_overlapping_patterns(self) -> None:
        """Test handling of overlapping pattern matches."""
        from uuid import uuid4

        from ib_platform.patterns.models import PatternCategory

        pattern = PatternDefinition(
            id=uuid4(),
            name="test",
            domain="test",
            category=PatternCategory.ENTITY,
            regex_pattern=r"\b\w+\b",  # Match any word
            output_type="word",
        )

        matcher = PatternMatcher()
        text = "word1 word2 word3"

        matches = matcher.match(text, pattern)

        assert len(matches) == 3  # Should find all three words
