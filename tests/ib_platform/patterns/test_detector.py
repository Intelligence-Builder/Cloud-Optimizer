"""Tests for pattern detector orchestrator."""

from uuid import uuid4

import pytest

from ib_platform.patterns.detector import PatternDetector
from ib_platform.patterns.models import (
    PatternCategory,
    PatternDefinition,
)
from ib_platform.patterns.registry import PatternRegistry
from ib_platform.patterns.scorer import ConfidenceScorer


class TestPatternDetector:
    """Tests for PatternDetector class."""

    @pytest.fixture
    def detector(self, populated_registry: PatternRegistry) -> PatternDetector:
        """Pattern detector with populated registry."""
        return PatternDetector(populated_registry)

    def test_detect_patterns_basic(
        self,
        detector: PatternDetector,
        sample_text_with_cves: str,
    ) -> None:
        """Test basic pattern detection."""
        matches = detector.detect_patterns(
            text=sample_text_with_cves,
            domains=["security"],
            min_confidence=0.0,
        )

        assert len(matches) > 0
        assert all(m.domain == "security" for m in matches)

    def test_detect_patterns_with_confidence_filter(
        self,
        detector: PatternDetector,
        sample_text_with_cves: str,
    ) -> None:
        """Test filtering by minimum confidence."""
        all_matches = detector.detect_patterns(
            text=sample_text_with_cves,
            domains=["security"],
            min_confidence=0.0,
        )

        high_conf_matches = detector.detect_patterns(
            text=sample_text_with_cves,
            domains=["security"],
            min_confidence=0.9,
        )

        assert len(high_conf_matches) <= len(all_matches)

    def test_detect_patterns_with_category_filter(
        self,
        detector: PatternDetector,
        sample_text_with_cves: str,
    ) -> None:
        """Test filtering by category."""
        entity_matches = detector.detect_patterns(
            text=sample_text_with_cves,
            domains=["security"],
            categories=[PatternCategory.ENTITY],
        )

        assert all(m.category == PatternCategory.ENTITY for m in entity_matches)

    def test_detect_entities(
        self,
        detector: PatternDetector,
        sample_text_with_cves: str,
    ) -> None:
        """Test entity-specific detection."""
        entities = detector.detect_entities(
            text=sample_text_with_cves,
            domains=["security"],
            min_confidence=0.7,
        )

        assert len(entities) > 0
        assert all(e.category == PatternCategory.ENTITY for e in entities)

    def test_detect_relationships(
        self,
        populated_registry: PatternRegistry,
        sample_relationship_pattern: PatternDefinition,
    ) -> None:
        """Test relationship detection."""
        populated_registry.register(sample_relationship_pattern)
        detector = PatternDetector(populated_registry)

        text = "CVE-2021-44228 vulnerability. Firewall mitigates vulnerability."

        # First detect entities
        entities = detector.detect_entities(text, domains=["security"])

        # Then detect relationships
        relationships = detector.detect_relationships(
            text=text,
            entities=entities,
            domains=["security"],
        )

        assert len(relationships) > 0
        assert all(
            r.category == PatternCategory.RELATIONSHIP for r in relationships
        )

    def test_process_document(
        self,
        detector: PatternDetector,
        sample_text_with_cves: str,
    ) -> None:
        """Test complete document processing."""
        result = detector.process_document(
            document_text=sample_text_with_cves,
            document_id="test-doc-001",
            domains=["security"],
        )

        assert result["document_id"] == "test-doc-001"
        assert "entities" in result
        assert "relationships" in result
        assert "stats" in result
        assert isinstance(result["entities"], list)
        assert isinstance(result["stats"], dict)

    def test_process_document_generates_id(
        self,
        detector: PatternDetector,
        sample_text_with_cves: str,
    ) -> None:
        """Test that process_document generates ID if not provided."""
        result = detector.process_document(
            document_text=sample_text_with_cves,
            domains=["security"],
        )

        assert "document_id" in result
        assert result["document_id"] is not None

    def test_process_document_statistics(
        self,
        detector: PatternDetector,
        sample_text_with_cves: str,
    ) -> None:
        """Test that document statistics are calculated."""
        result = detector.process_document(
            document_text=sample_text_with_cves,
            domains=["security"],
        )

        stats = result["stats"]

        assert "total_entities" in stats
        assert "total_relationships" in stats
        assert "entity_types" in stats
        assert "avg_entity_confidence" in stats

        if stats["total_entities"] > 0:
            assert 0.0 <= stats["avg_entity_confidence"] <= 1.0

    def test_detect_patterns_empty_text(
        self,
        detector: PatternDetector,
    ) -> None:
        """Test detection on empty text."""
        matches = detector.detect_patterns(
            text="",
            domains=["security"],
        )

        assert len(matches) == 0

    def test_detect_patterns_no_matches(
        self,
        detector: PatternDetector,
    ) -> None:
        """Test detection when no patterns match."""
        matches = detector.detect_patterns(
            text="This text has no security-related content xyz123",
            domains=["security"],
        )

        # May or may not have matches depending on patterns
        assert isinstance(matches, list)

    def test_detect_patterns_multiple_domains(
        self,
        populated_registry: PatternRegistry,
    ) -> None:
        """Test detection across multiple domains."""
        # Add an AWS pattern
        aws_pattern = PatternDefinition(
            id=uuid4(),
            name="ec2_instance",
            domain="aws",
            category=PatternCategory.ENTITY,
            regex_pattern=r"\bi-[a-f0-9]{8,17}\b",
            output_type="ec2_instance",
            base_confidence=0.85,
        )
        populated_registry.register(aws_pattern)

        detector = PatternDetector(populated_registry)

        text = "CVE-2021-44228 affects i-1234567890abcdef0 instance"

        matches = detector.detect_patterns(
            text=text,
            domains=["security", "aws"],
        )

        domains_found = {m.domain for m in matches}
        assert len(domains_found) >= 1  # Should find at least one domain

    def test_custom_confidence_scorer(
        self,
        populated_registry: PatternRegistry,
        sample_confidence_factors: list,
    ) -> None:
        """Test using custom confidence scorer."""
        custom_scorer = ConfidenceScorer(sample_confidence_factors)
        detector = PatternDetector(populated_registry, custom_scorer)

        text = "CVE-2021-44228 costs $50,000"

        matches = detector.detect_patterns(text, domains=["security"])

        # Should use custom scorer
        assert len(matches) > 0

    def test_nearby_entities_detection(
        self,
        populated_registry: PatternRegistry,
        sample_relationship_pattern: PatternDefinition,
    ) -> None:
        """Test that relationships detect nearby entities."""
        populated_registry.register(sample_relationship_pattern)
        detector = PatternDetector(populated_registry)

        text = "IAM policy mitigates CVE-2021-44228 vulnerability"

        entities = detector.detect_entities(text, domains=["security"])
        relationships = detector.detect_relationships(
            text, entities, domains=["security"]
        )

        if relationships:
            # Check if nearby entities are recorded
            for rel in relationships:
                if rel.metadata and "nearby_entities" in rel.metadata:
                    assert isinstance(rel.metadata["nearby_entities"], list)

    def test_confidence_scoring_applied(
        self,
        detector: PatternDetector,
        sample_text_with_negation: str,
    ) -> None:
        """Test that confidence scoring is applied to matches."""
        matches = detector.detect_patterns(
            text=sample_text_with_negation,
            domains=["security"],
        )

        if matches:
            # Check that final confidence may differ from base
            for match in matches:
                assert hasattr(match, "final_confidence")
                assert match.final_confidence >= 0.0
                assert match.final_confidence <= 1.0

    def test_detect_patterns_performance(
        self,
        detector: PatternDetector,
    ) -> None:
        """Test detection performance on larger text."""
        import time

        # Generate larger text
        text = (
            "Security report with CVE-2021-44228 and IAM policy issues. " * 100
        )

        start = time.perf_counter()
        matches = detector.detect_patterns(
            text=text,
            domains=["security"],
        )
        elapsed = time.perf_counter() - start

        # Should complete in reasonable time (< 1 second for 6KB text)
        assert elapsed < 1.0
        assert isinstance(matches, list)

    def test_get_applicable_patterns_no_filters(
        self,
        detector: PatternDetector,
    ) -> None:
        """Test getting patterns with no filters."""
        patterns = detector._get_applicable_patterns()

        assert len(patterns) > 0

    def test_get_applicable_patterns_domain_filter(
        self,
        detector: PatternDetector,
    ) -> None:
        """Test getting patterns with domain filter."""
        patterns = detector._get_applicable_patterns(domains=["security"])

        assert all(p.domain == "security" for p in patterns)

    def test_get_applicable_patterns_category_filter(
        self,
        detector: PatternDetector,
    ) -> None:
        """Test getting patterns with category filter."""
        patterns = detector._get_applicable_patterns(
            categories=[PatternCategory.ENTITY]
        )

        assert all(p.category == PatternCategory.ENTITY for p in patterns)

    def test_compile_statistics(
        self,
        detector: PatternDetector,
        sample_text_with_cves: str,
    ) -> None:
        """Test statistics compilation."""
        entities = detector.detect_entities(
            text=sample_text_with_cves,
            domains=["security"],
        )

        stats = detector._compile_statistics(entities, [])

        assert stats["total_entities"] == len(entities)
        assert stats["total_relationships"] == 0
        assert isinstance(stats["entity_types"], dict)

        if entities:
            assert stats["avg_entity_confidence"] > 0.0
