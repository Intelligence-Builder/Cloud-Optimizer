"""Shared fixtures for pattern engine tests."""

import re
from uuid import uuid4

import pytest

from ib_platform.patterns.models import (
    ConfidenceFactor,
    PatternCategory,
    PatternDefinition,
    PatternPriority,
)
from ib_platform.patterns.registry import PatternRegistry
from ib_platform.patterns.scorer import ConfidenceScorer


@pytest.fixture
def sample_cve_pattern() -> PatternDefinition:
    """Sample CVE pattern for testing."""
    return PatternDefinition(
        id=uuid4(),
        name="cve_reference",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\bCVE-\d{4}-\d{4,7}\b",
        output_type="vulnerability",
        base_confidence=0.95,
        priority=PatternPriority.HIGH,
        description="CVE identifier reference",
        examples=["CVE-2021-44228", "CVE-2023-12345"],
    )


@pytest.fixture
def sample_iam_pattern() -> PatternDefinition:
    """Sample IAM policy pattern for testing."""
    return PatternDefinition(
        id=uuid4(),
        name="iam_policy",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\b(?:IAM\s+)?(?:policy|role|permission)\b",
        flags=re.IGNORECASE,
        output_type="access_policy",
        base_confidence=0.75,
        priority=PatternPriority.NORMAL,
        description="IAM policy reference",
    )


@pytest.fixture
def sample_relationship_pattern() -> PatternDefinition:
    """Sample relationship pattern for testing."""
    return PatternDefinition(
        id=uuid4(),
        name="mitigates_relationship",
        domain="security",
        category=PatternCategory.RELATIONSHIP,
        regex_pattern=r"(?P<source>\w+)\s+mitigates?\s+(?P<target>\w+)",
        flags=re.IGNORECASE,
        output_type="mitigates",
        base_confidence=0.80,
        capture_groups={"source": "source", "target": "target"},
        description="Mitigation relationship",
    )


@pytest.fixture
def pattern_registry() -> PatternRegistry:
    """Empty pattern registry for testing."""
    return PatternRegistry()


@pytest.fixture
def populated_registry(
    pattern_registry: PatternRegistry,
    sample_cve_pattern: PatternDefinition,
    sample_iam_pattern: PatternDefinition,
) -> PatternRegistry:
    """Pattern registry with sample patterns."""
    pattern_registry.register(sample_cve_pattern)
    pattern_registry.register(sample_iam_pattern)
    return pattern_registry


@pytest.fixture
def sample_confidence_factors() -> list[ConfidenceFactor]:
    """Sample confidence factors for testing."""
    return [
        ConfidenceFactor(
            name="negation_presence",
            description="Negation words decrease confidence",
            weight=0.20,
            detector="detect_negation",
            is_positive=False,
            max_adjustment=0.20,
        ),
        ConfidenceFactor(
            name="monetary_context",
            description="Nearby monetary amounts increase confidence",
            weight=0.15,
            detector="detect_monetary",
            is_positive=True,
            max_adjustment=0.15,
        ),
    ]


@pytest.fixture
def confidence_scorer(
    sample_confidence_factors: list[ConfidenceFactor],
) -> ConfidenceScorer:
    """Confidence scorer with sample factors."""
    return ConfidenceScorer(sample_confidence_factors)


@pytest.fixture
def sample_text_with_cves() -> str:
    """Sample text containing CVE references."""
    return """
    Security report for Q4 2023:

    Critical vulnerabilities found:
    - CVE-2021-44228 (Log4Shell) with CVSS score 10.0
    - CVE-2023-12345 affecting authentication

    The patch for CVE-2021-44228 mitigates the vulnerability.
    Cost impact: $50,000 in remediation expenses.
    """


@pytest.fixture
def sample_text_with_negation() -> str:
    """Sample text with negation."""
    return "This is not a CVE-2021-44228 vulnerability."


@pytest.fixture
def sample_text_with_monetary() -> str:
    """Sample text with monetary context."""
    return "CVE-2021-44228 caused losses of $1,500,000 in Q3."
