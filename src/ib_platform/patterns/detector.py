"""Pattern Detector - Main Orchestrator for Pattern Detection.

Coordinates pattern matching, confidence scoring, and filtering to detect
entities and relationships from unstructured text.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .matcher import PatternMatcher
from .models import PatternCategory, PatternMatch
from .registry import PatternRegistry
from .scorer import ConfidenceScorer, get_default_confidence_factors

logger = logging.getLogger(__name__)


class PatternDetector:
    """Main orchestrator for pattern-based entity and relationship detection.

    Coordinates pattern matching, confidence scoring, and result filtering
    to extract structured information from unstructured text.

    Example:
        >>> registry = PatternRegistry()
        >>> detector = PatternDetector(registry)
        >>> matches = detector.detect_patterns(
        ...     text="CVE-2021-44228 vulnerability found",
        ...     domains=["security"],
        ...     min_confidence=0.7
        ... )
    """

    def __init__(
        self,
        registry: PatternRegistry,
        confidence_scorer: Optional[ConfidenceScorer] = None,
    ) -> None:
        """Initialize pattern detector.

        Args:
            registry: Pattern registry containing pattern definitions
            confidence_scorer: Optional custom confidence scorer
                (uses default if not provided)
        """
        self.registry = registry
        self.matcher = PatternMatcher()

        if confidence_scorer is None:
            factors = get_default_confidence_factors()
            self.scorer = ConfidenceScorer(factors)
        else:
            self.scorer = confidence_scorer

        logger.info("Pattern detector initialized")

    def detect_patterns(
        self,
        text: str,
        domains: Optional[List[str]] = None,
        categories: Optional[List[PatternCategory]] = None,
        min_confidence: float = 0.0,
    ) -> List[PatternMatch]:
        """Detect all patterns in text with filtering.

        Args:
            text: Text to analyze
            domains: Optional list of domains to filter by
            categories: Optional list of categories to filter by
            min_confidence: Minimum confidence threshold (default: 0.0)

        Returns:
            List of pattern matches meeting criteria

        Example:
            >>> matches = detector.detect_patterns(
            ...     text="Found CVE-2021-44228 and CVE-2023-12345",
            ...     domains=["security"],
            ...     categories=[PatternCategory.ENTITY],
            ...     min_confidence=0.8
            ... )
        """
        logger.info(
            "Starting pattern detection",
            extra={
                "text_length": len(text),
                "domains": domains,
                "categories": [c.value for c in categories]
                if categories
                else None,
                "min_confidence": min_confidence,
            },
        )

        # Get applicable patterns
        patterns = self._get_applicable_patterns(domains, categories)
        logger.debug(
            f"Using {len(patterns)} patterns for detection",
            extra={"pattern_count": len(patterns)},
        )

        # Match all patterns
        matches = self.matcher.match_all(text, patterns)
        logger.debug(
            f"Found {len(matches)} raw matches",
            extra={"raw_matches": len(matches)},
        )

        # Apply confidence scoring
        for match in matches:
            self.scorer.score(match, text)

        # Filter by confidence
        filtered_matches = [
            m for m in matches if m.final_confidence >= min_confidence
        ]

        logger.info(
            "Pattern detection complete",
            extra={
                "total_matches": len(filtered_matches),
                "raw_matches": len(matches),
                "filtered_out": len(matches) - len(filtered_matches),
            },
        )

        return filtered_matches

    def detect_entities(
        self,
        text: str,
        domains: Optional[List[str]] = None,
        min_confidence: float = 0.7,
    ) -> List[PatternMatch]:
        """Detect entity patterns in text.

        Args:
            text: Text to analyze
            domains: Optional list of domains to filter by
            min_confidence: Minimum confidence threshold (default: 0.7)

        Returns:
            List of entity pattern matches

        Example:
            >>> entities = detector.detect_entities(
            ...     text="AWS Lambda function with IAM role",
            ...     domains=["aws"],
            ...     min_confidence=0.75
            ... )
        """
        return self.detect_patterns(
            text=text,
            domains=domains,
            categories=[PatternCategory.ENTITY],
            min_confidence=min_confidence,
        )

    def detect_relationships(
        self,
        text: str,
        entities: List[PatternMatch],
        domains: Optional[List[str]] = None,
        min_confidence: float = 0.7,
    ) -> List[PatternMatch]:
        """Detect relationship patterns between entities.

        Args:
            text: Text to analyze
            entities: Previously detected entities
            domains: Optional list of domains to filter by
            min_confidence: Minimum confidence threshold (default: 0.7)

        Returns:
            List of relationship pattern matches

        Example:
            >>> entities = detector.detect_entities(text, ["security"])
            >>> relationships = detector.detect_relationships(
            ...     text=text,
            ...     entities=entities,
            ...     domains=["security"]
            ... )
        """
        # Get relationship patterns
        rel_matches = self.detect_patterns(
            text=text,
            domains=domains,
            categories=[PatternCategory.RELATIONSHIP],
            min_confidence=min_confidence,
        )

        # Enhance with entity context
        for rel_match in rel_matches:
            # Find nearby entities
            nearby = self._find_nearby_entities(rel_match, entities)
            if nearby:
                if rel_match.metadata is None:
                    rel_match.metadata = {}
                rel_match.metadata["nearby_entities"] = [
                    {"name": e.output_value, "type": e.output_type}
                    for e in nearby
                ]

        logger.debug(
            "Relationship detection complete",
            extra={
                "relationships_found": len(rel_matches),
                "entities_count": len(entities),
            },
        )

        return rel_matches

    def process_document(
        self,
        document_text: str,
        document_id: Optional[str] = None,
        domains: Optional[List[str]] = None,
        min_confidence: float = 0.7,
    ) -> Dict[str, Any]:
        """Process a complete document for entities and relationships.

        Args:
            document_text: Full document text
            document_id: Optional document identifier
            domains: Optional list of domains to filter by
            min_confidence: Minimum confidence threshold (default: 0.7)

        Returns:
            Dictionary with entities, relationships, and metadata

        Example:
            >>> result = detector.process_document(
            ...     document_text=security_report,
            ...     document_id="report-001",
            ...     domains=["security"]
            ... )
            >>> result.keys()
            dict_keys(['document_id', 'entities', 'relationships', 'stats'])
        """
        doc_id = document_id or str(uuid4())

        logger.info(
            "Processing document",
            extra={
                "document_id": doc_id,
                "text_length": len(document_text),
                "domains": domains,
            },
        )

        # Detect entities
        entities = self.detect_entities(
            text=document_text, domains=domains, min_confidence=min_confidence
        )

        # Detect relationships
        relationships = self.detect_relationships(
            text=document_text,
            entities=entities,
            domains=domains,
            min_confidence=min_confidence,
        )

        # Compile statistics
        stats = self._compile_statistics(entities, relationships)

        result = {
            "document_id": doc_id,
            "entities": entities,
            "relationships": relationships,
            "stats": stats,
        }

        logger.info(
            "Document processing complete",
            extra={
                "document_id": doc_id,
                "entities_count": len(entities),
                "relationships_count": len(relationships),
            },
        )

        return result

    def _get_applicable_patterns(
        self,
        domains: Optional[List[str]] = None,
        categories: Optional[List[PatternCategory]] = None,
    ) -> List[Any]:
        """Get patterns matching domain and category filters.

        Args:
            domains: Optional domain filter
            categories: Optional category filter

        Returns:
            List of applicable pattern definitions
        """
        if domains is None and categories is None:
            # No filters - return all patterns
            return self.registry.list_all()

        patterns = []

        if domains is not None:
            # Get patterns for each domain
            for domain in domains:
                domain_patterns = self.registry.get_by_domain(domain)
                patterns.extend(domain_patterns)

            # Apply category filter if specified
            if categories is not None:
                patterns = [
                    p for p in patterns if p.category in categories
                ]
        else:
            # Only category filter
            for category in categories:  # type: ignore
                cat_patterns = self.registry.get_by_category(category)
                patterns.extend(cat_patterns)

        # Remove duplicates
        seen = set()
        unique_patterns = []
        for pattern in patterns:
            if pattern.id not in seen:
                seen.add(pattern.id)
                unique_patterns.append(pattern)

        return unique_patterns

    def _find_nearby_entities(
        self, relationship: PatternMatch, entities: List[PatternMatch]
    ) -> List[PatternMatch]:
        """Find entities near a relationship match.

        Args:
            relationship: Relationship pattern match
            entities: List of entity matches

        Returns:
            List of entities within proximity of relationship
        """
        nearby: List[PatternMatch] = []
        proximity_threshold = 200  # characters

        for entity in entities:
            # Check if entity is within proximity of relationship
            distance = min(
                abs(entity.start_position - relationship.start_position),
                abs(entity.end_position - relationship.end_position),
            )

            if distance <= proximity_threshold:
                nearby.append(entity)

        return nearby

    def _compile_statistics(
        self, entities: List[PatternMatch], relationships: List[PatternMatch]
    ) -> Dict[str, Any]:
        """Compile statistics about detected patterns.

        Args:
            entities: List of entity matches
            relationships: List of relationship matches

        Returns:
            Statistics dictionary
        """
        # Count by type
        entity_types: Dict[str, int] = {}
        for entity in entities:
            entity_types[entity.output_type] = (
                entity_types.get(entity.output_type, 0) + 1
            )

        relationship_types: Dict[str, int] = {}
        for rel in relationships:
            relationship_types[rel.output_type] = (
                relationship_types.get(rel.output_type, 0) + 1
            )

        # Calculate average confidence
        avg_entity_conf = (
            sum(e.final_confidence for e in entities) / len(entities)
            if entities
            else 0.0
        )
        avg_rel_conf = (
            sum(r.final_confidence for r in relationships) / len(relationships)
            if relationships
            else 0.0
        )

        return {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "entity_types": entity_types,
            "relationship_types": relationship_types,
            "avg_entity_confidence": avg_entity_conf,
            "avg_relationship_confidence": avg_rel_conf,
        }
