"""
Integration tests for Epic #34 (Expert System / Intelligence-Builder).

These tests exercise the real pattern detection pipeline end-to-end using the
security domain pattern definitions. No mocks or stubs are used; instead we
register the production patterns and verify that natural language input
produces the expected structured entities and relationships.
"""

from __future__ import annotations

import pytest

from ib_platform.domains.security.patterns import SECURITY_PATTERNS
from ib_platform.patterns.detector import PatternDetector
from ib_platform.patterns.models import PatternCategory
from ib_platform.patterns.registry import PatternRegistry


@pytest.mark.integration
def test_security_patterns_detect_entities_and_relationships() -> None:
    """Ensure real security patterns can process complex security prompts."""
    registry = PatternRegistry()
    for pattern in SECURITY_PATTERNS:
        registry.register(pattern)

    detector = PatternDetector(registry)

    text = (
        "CVE-2024-12345 remains critical severity with CVSS 9.8 under HIPAA. "
        "Apply IAM policy hardening and encryption via AWS KMS. "
        "IAM role hardening mitigates SSH exposure on SG-1234 while SOC 2 requires audit logs."
    )

    entities = detector.detect_entities(
        text=text,
        domains=["security"],
        min_confidence=0.6,
    )

    entity_types = {match.output_type for match in entities}
    assert "vulnerability" in entity_types
    assert "compliance_requirement" in entity_types
    assert "access_policy" in entity_types
    assert "encryption_config" in entity_types

    relationships = detector.detect_relationships(
        text=text,
        entities=entities,
        domains=["security"],
        min_confidence=0.5,
    )

    assert any(match.output_type == "mitigates" for match in relationships)
    assert all(match.category == PatternCategory.RELATIONSHIP for match in relationships)
