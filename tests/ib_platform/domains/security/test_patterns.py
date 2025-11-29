"""Tests for Security Domain Pattern Detection.

This module contains comprehensive tests for security pattern detection,
including pattern matching accuracy, confidence factor application, and
entity/relationship extraction validation.
"""

import re
from pathlib import Path
from typing import Dict, List, Set

import pytest

from src.ib_platform.domains.security.factors import (
    SECURITY_CONFIDENCE_FACTORS,
    detect_aws_service_context,
    detect_compliance_framework,
    detect_cve_reference,
    detect_severity_context,
)
from src.ib_platform.domains.security.patterns import SECURITY_PATTERNS
from src.ib_platform.patterns.models import PatternCategory

# --- Fixtures ---


@pytest.fixture
def security_test_document() -> str:
    """Load security test document fixture.

    Returns:
        Content of security test document
    """
    fixture_path = (
        Path(__file__).parent.parent.parent.parent
        / "fixtures"
        / "security_test_doc.txt"
    )
    return fixture_path.read_text()


@pytest.fixture
def pattern_by_name() -> Dict[str, object]:
    """Create pattern lookup dictionary by name.

    Returns:
        Dictionary mapping pattern names to pattern definitions
    """
    return {pattern.name: pattern for pattern in SECURITY_PATTERNS}


# --- Pattern Definition Tests ---


class TestPatternDefinitions:
    """Test pattern definition structure and validity."""

    def test_all_patterns_defined(self) -> None:
        """Verify all 10 required patterns are defined."""
        expected_patterns = {
            "cve_reference",
            "aws_arn",
            "compliance_framework",
            "cvss_score",
            "severity_indicator",
            "encryption_reference",
            "security_group",
            "iam_policy",
            "mitigates_relationship",
            "protects_relationship",
        }
        actual_patterns = {pattern.name for pattern in SECURITY_PATTERNS}
        assert expected_patterns == actual_patterns, (
            f"Missing patterns: {expected_patterns - actual_patterns}, "
            f"Extra patterns: {actual_patterns - expected_patterns}"
        )

    def test_pattern_count(self) -> None:
        """Verify exactly 10 patterns are defined."""
        assert len(SECURITY_PATTERNS) == 10

    def test_patterns_have_required_fields(self) -> None:
        """Verify all patterns have required fields populated."""
        for pattern in SECURITY_PATTERNS:
            assert pattern.id is not None
            assert pattern.name
            assert pattern.domain == "security"
            assert pattern.category in PatternCategory
            assert pattern.regex_pattern
            assert pattern.output_type
            assert 0.0 <= pattern.base_confidence <= 1.0

    def test_pattern_regex_compiles(self) -> None:
        """Verify all regex patterns compile successfully."""
        for pattern in SECURITY_PATTERNS:
            try:
                compiled = pattern.compiled
                assert compiled is not None
            except re.error as e:
                pytest.fail(f"Pattern {pattern.name} regex failed to compile: {e}")

    def test_pattern_categories(self) -> None:
        """Verify patterns have correct categories."""
        entity_patterns = {
            "cve_reference",
            "aws_arn",
            "compliance_framework",
            "encryption_reference",
            "security_group",
            "iam_policy",
        }
        context_patterns = {"cvss_score", "severity_indicator"}
        relationship_patterns = {"mitigates_relationship", "protects_relationship"}

        for pattern in SECURITY_PATTERNS:
            if pattern.name in entity_patterns:
                assert pattern.category == PatternCategory.ENTITY
            elif pattern.name in context_patterns:
                assert pattern.category == PatternCategory.CONTEXT
            elif pattern.name in relationship_patterns:
                assert pattern.category == PatternCategory.RELATIONSHIP
            else:
                pytest.fail(f"Unknown pattern: {pattern.name}")

    def test_confidence_scores_in_spec(self) -> None:
        """Verify patterns have confidence scores matching specifications."""
        expected_confidences = {
            "cve_reference": 0.95,
            "aws_arn": 0.95,
            "compliance_framework": 0.90,
            "cvss_score": 0.90,
            "severity_indicator": 0.85,
            "encryption_reference": 0.80,
            "security_group": 0.80,
            "iam_policy": 0.75,
            "mitigates_relationship": 0.75,
            "protects_relationship": 0.75,
        }

        for pattern in SECURITY_PATTERNS:
            expected = expected_confidences[pattern.name]
            assert pattern.base_confidence == expected, (
                f"Pattern {pattern.name} has confidence {pattern.base_confidence}, "
                f"expected {expected}"
            )


# --- Pattern Matching Tests ---


class TestPatternMatching:
    """Test pattern matching against real text."""

    def test_cve_reference_detection(
        self, security_test_document: str, pattern_by_name: Dict[str, object]
    ) -> None:
        """Test CVE reference pattern detection."""
        pattern = pattern_by_name["cve_reference"]
        matches = list(pattern.compiled.finditer(security_test_document))

        # Document contains CVE-2023-44487, CVE-2023-12345, CVE-2024-0001
        assert (
            len(matches) >= 3
        ), f"Expected at least 3 CVE matches, found {len(matches)}"

        # Verify specific CVEs are detected
        cve_ids = {match.group(0).upper() for match in matches}
        assert "CVE-2023-44487" in cve_ids
        assert "CVE-2023-12345" in cve_ids
        assert "CVE-2024-0001" in cve_ids

    def test_aws_arn_detection(
        self, security_test_document: str, pattern_by_name: Dict[str, object]
    ) -> None:
        """Test AWS ARN pattern detection."""
        pattern = pattern_by_name["aws_arn"]
        matches = list(pattern.compiled.finditer(security_test_document))

        # Document contains multiple ARNs
        assert (
            len(matches) >= 5
        ), f"Expected at least 5 ARN matches, found {len(matches)}"

        # Verify ARN format
        for match in matches:
            arn = match.group(0)
            assert arn.startswith("arn:aws:"), f"Invalid ARN format: {arn}"

    def test_compliance_framework_detection(
        self, security_test_document: str, pattern_by_name: Dict[str, object]
    ) -> None:
        """Test compliance framework pattern detection."""
        pattern = pattern_by_name["compliance_framework"]
        matches = list(pattern.compiled.finditer(security_test_document))

        # Document mentions SOC 2, HIPAA, PCI-DSS, GDPR, NIST, FedRAMP, CIS, CCPA, ISO 27001, FISMA
        assert (
            len(matches) >= 10
        ), f"Expected at least 10 framework matches, found {len(matches)}"

        frameworks = {match.group(0).upper() for match in matches}
        assert any("SOC" in f and "2" in f for f in frameworks)
        assert any("HIPAA" in f for f in frameworks)
        assert any("PCI" in f for f in frameworks)

    def test_cvss_score_detection(
        self, security_test_document: str, pattern_by_name: Dict[str, object]
    ) -> None:
        """Test CVSS score pattern detection."""
        pattern = pattern_by_name["cvss_score"]
        matches = list(pattern.compiled.finditer(security_test_document))

        # Document contains CVSS 10.0, CVSS: 8.5
        assert (
            len(matches) >= 2
        ), f"Expected at least 2 CVSS matches, found {len(matches)}"

    def test_severity_indicator_detection(
        self, security_test_document: str, pattern_by_name: Dict[str, object]
    ) -> None:
        """Test severity indicator pattern detection."""
        pattern = pattern_by_name["severity_indicator"]
        matches = list(pattern.compiled.finditer(security_test_document))

        # Document contains critical severity, high risk, medium priority, informational severity
        assert (
            len(matches) >= 4
        ), f"Expected at least 4 severity matches, found {len(matches)}"

    def test_encryption_reference_detection(
        self, security_test_document: str, pattern_by_name: Dict[str, object]
    ) -> None:
        """Test encryption reference pattern detection."""
        pattern = pattern_by_name["encryption_reference"]
        matches = list(pattern.compiled.finditer(security_test_document))

        # Document mentions AES-128, AES-256, KMS, TLS 1.3, TLS 1.2, RSA-2048, RSA-4096, HSM, SSL
        assert (
            len(matches) >= 8
        ), f"Expected at least 8 encryption matches, found {len(matches)}"

        encryption_types = {match.group(0).upper() for match in matches}
        assert any("AES" in e for e in encryption_types)
        assert any("TLS" in e for e in encryption_types)

    def test_security_group_detection(
        self, security_test_document: str, pattern_by_name: Dict[str, object]
    ) -> None:
        """Test security group pattern detection."""
        pattern = pattern_by_name["security_group"]
        matches = list(pattern.compiled.finditer(security_test_document))

        # Document contains security group sg-..., NSG references
        assert (
            len(matches) >= 4
        ), f"Expected at least 4 security group matches, found {len(matches)}"

    def test_iam_policy_detection(
        self, security_test_document: str, pattern_by_name: Dict[str, object]
    ) -> None:
        """Test IAM policy pattern detection."""
        pattern = pattern_by_name["iam_policy"]
        matches = list(pattern.compiled.finditer(security_test_document))

        # Document contains IAM policy, IAM role, access policy, RBAC
        assert (
            len(matches) >= 6
        ), f"Expected at least 6 IAM policy matches, found {len(matches)}"

    def test_mitigates_relationship_detection(
        self, security_test_document: str, pattern_by_name: Dict[str, object]
    ) -> None:
        """Test mitigates relationship pattern detection."""
        pattern = pattern_by_name["mitigates_relationship"]
        matches = list(pattern.compiled.finditer(security_test_document))

        # Document contains: "WAF mitigates", "mitigates SQL injection", "reduces", "addresses", "remediates"
        assert (
            len(matches) >= 4
        ), f"Expected at least 4 mitigates matches, found {len(matches)}"

    def test_protects_relationship_detection(
        self, security_test_document: str, pattern_by_name: Dict[str, object]
    ) -> None:
        """Test protects relationship pattern detection."""
        pattern = pattern_by_name["protects_relationship"]
        matches = list(pattern.compiled.finditer(security_test_document))

        # Document contains: "TLS protects", "secures", "safeguards", "defends", "protects"
        assert (
            len(matches) >= 4
        ), f"Expected at least 4 protects matches, found {len(matches)}"


# --- Confidence Factor Tests ---


class TestConfidenceFactors:
    """Test confidence factor definitions and detection."""

    def test_all_factors_defined(self) -> None:
        """Verify all 4 required confidence factors are defined."""
        expected_factors = {
            "severity_context",
            "cve_reference",
            "compliance_framework",
            "aws_service_context",
        }
        actual_factors = {factor.name for factor in SECURITY_CONFIDENCE_FACTORS}
        assert expected_factors == actual_factors

    def test_factor_count(self) -> None:
        """Verify exactly 4 confidence factors are defined."""
        assert len(SECURITY_CONFIDENCE_FACTORS) == 4

    def test_factor_weights(self) -> None:
        """Verify confidence factors have correct weights."""
        expected_weights = {
            "severity_context": 0.15,
            "cve_reference": 0.15,
            "compliance_framework": 0.10,
            "aws_service_context": 0.10,
        }

        for factor in SECURITY_CONFIDENCE_FACTORS:
            expected = expected_weights[factor.name]
            assert (
                factor.weight == expected
            ), f"Factor {factor.name} has weight {factor.weight}, expected {expected}"

    def test_severity_context_detector(self) -> None:
        """Test severity context detector function."""
        # Positive cases
        assert detect_severity_context("This is a critical vulnerability")
        assert detect_severity_context("High risk of data breach")
        assert detect_severity_context("Medium severity issue")
        assert detect_severity_context("Low impact finding")

        # Negative cases
        assert not detect_severity_context("This is a normal operation")
        assert not detect_severity_context("No security issues found")

    def test_cve_reference_detector(self) -> None:
        """Test CVE reference detector function."""
        # Positive cases
        assert detect_cve_reference("Related to CVE-2023-12345")
        assert detect_cve_reference("Fixes cve-2024-0001")

        # Negative cases
        assert not detect_cve_reference("No vulnerability reference")
        assert not detect_cve_reference("CVE without number")

    def test_compliance_framework_detector(self) -> None:
        """Test compliance framework detector function."""
        # Positive cases
        assert detect_compliance_framework("Must comply with SOC 2")
        assert detect_compliance_framework("HIPAA requirements apply")
        assert detect_compliance_framework("PCI-DSS certification needed")
        assert detect_compliance_framework("GDPR compliance required")

        # Negative cases
        assert not detect_compliance_framework("No compliance mentioned")
        assert not detect_compliance_framework("Standard security practices")

    def test_aws_service_context_detector(self) -> None:
        """Test AWS service context detector function."""
        # Positive cases
        assert detect_aws_service_context("AWS infrastructure security")
        assert detect_aws_service_context("EC2 instance configuration")
        assert detect_aws_service_context("S3 bucket permissions")
        assert detect_aws_service_context("IAM role assignment")
        assert detect_aws_service_context("Security group sg-12345")

        # Negative cases
        assert not detect_aws_service_context("Generic cloud security")
        assert not detect_aws_service_context("On-premises infrastructure")


# --- Integration Tests ---


class TestPatternDetectionAccuracy:
    """Test overall pattern detection accuracy against test document."""

    def test_overall_detection_accuracy(self, security_test_document: str) -> None:
        """Verify pattern detection accuracy is above 85%."""
        # Count expected occurrences manually from fixture
        expected_detections = {
            "cve_reference": 3,  # CVE-2023-44487, CVE-2023-12345, CVE-2024-0001
            "aws_arn": 5,  # Multiple ARNs throughout document
            "compliance_framework": 12,  # SOC2, HIPAA, PCI-DSS, GDPR, NIST, FedRAMP, CIS, CCPA, ISO27001, FISMA
            "cvss_score": 2,  # CVSS 10.0, CVSS: 8.5
            "severity_indicator": 4,  # critical severity, high risk, medium priority, informational severity
            "encryption_reference": 12,  # AES-128, AES-256, KMS, TLS, RSA, HSM, SSL
            "security_group": 6,  # Multiple security group references
            "iam_policy": 8,  # IAM policy, role, RBAC references
            "mitigates_relationship": 5,  # mitigates, reduces, addresses, remediates
            "protects_relationship": 5,  # protects, secures, safeguards, defends
        }

        total_expected = sum(expected_detections.values())
        total_detected = 0

        pattern_results = {}
        for pattern in SECURITY_PATTERNS:
            matches = list(pattern.compiled.finditer(security_test_document))
            detected_count = len(matches)
            expected_count = expected_detections[pattern.name]

            # Calculate detection rate for this pattern
            detection_rate = (
                min(detected_count / expected_count, 1.0) if expected_count > 0 else 1.0
            )
            pattern_results[pattern.name] = {
                "expected": expected_count,
                "detected": detected_count,
                "rate": detection_rate,
            }

            total_detected += min(detected_count, expected_count)

        # Calculate overall accuracy
        overall_accuracy = (
            total_detected / total_expected if total_expected > 0 else 0.0
        )

        # Print detailed results for debugging
        print("\n=== Pattern Detection Results ===")
        for name, result in pattern_results.items():
            print(
                f"{name:30} Expected: {result['expected']:3} Detected: {result['detected']:3} "
                f"Rate: {result['rate']:.1%}"
            )
        print(f"\nOverall Accuracy: {overall_accuracy:.1%}")

        # Verify accuracy is above threshold
        assert (
            overall_accuracy >= 0.85
        ), f"Detection accuracy {overall_accuracy:.1%} is below required 85% threshold"

    def test_pattern_examples_match(self) -> None:
        """Verify all pattern examples match their own patterns."""
        for pattern in SECURITY_PATTERNS:
            if pattern.examples:
                for example in pattern.examples:
                    matches = list(pattern.compiled.finditer(example))
                    assert (
                        len(matches) > 0
                    ), f"Pattern {pattern.name} did not match its own example: '{example}'"

    def test_no_false_positives_on_clean_text(self) -> None:
        """Verify patterns don't match on clearly unrelated text."""
        clean_text = """
        This is a normal business document about quarterly sales results.
        Revenue increased by 15% compared to last quarter.
        The marketing team delivered excellent campaign performance.
        Customer satisfaction scores remain high across all regions.
        We are planning to expand our product line next year.
        """

        # Most patterns should not match this text
        # (Some might match incidentally, but very few)
        total_matches = 0
        for pattern in SECURITY_PATTERNS:
            matches = list(pattern.compiled.finditer(clean_text))
            total_matches += len(matches)

        # Allow a small number of incidental matches, but not many
        assert (
            total_matches < 3
        ), f"Too many false positives ({total_matches}) on clean text"


# --- Performance Tests ---


class TestPatternPerformance:
    """Test pattern matching performance."""

    def test_pattern_compilation_cached(
        self, pattern_by_name: Dict[str, object]
    ) -> None:
        """Verify pattern compilation is cached."""
        pattern = pattern_by_name["cve_reference"]
        compiled1 = pattern.compiled
        compiled2 = pattern.compiled

        # Should return same object (cached)
        assert compiled1 is compiled2

    def test_large_document_performance(self, security_test_document: str) -> None:
        """Test pattern matching on larger documents."""
        # Create a large document by repeating the test document
        large_document = security_test_document * 10

        # Time all patterns (should complete quickly)
        import time

        start_time = time.time()

        for pattern in SECURITY_PATTERNS:
            list(pattern.compiled.finditer(large_document))

        elapsed = time.time() - start_time

        # Should complete in under 1 second for 10x document
        assert elapsed < 1.0, f"Pattern matching took {elapsed:.2f}s, expected < 1.0s"
