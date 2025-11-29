"""Security Domain Confidence Factors.

This module defines confidence adjustment factors for security pattern matching.
These factors analyze context around matches to increase or decrease confidence
scores based on surrounding indicators.
"""

from typing import List

from ...patterns.models import ConfidenceFactor, PatternCategory

SECURITY_CONFIDENCE_FACTORS: List[ConfidenceFactor] = [
    ConfidenceFactor(
        name="severity_context",
        description="Increases confidence when severity indicators are nearby",
        weight=0.15,
        detector="detect_severity_context",
        is_positive=True,
        max_adjustment=0.15,
        applies_to_categories=[
            PatternCategory.ENTITY,
            PatternCategory.CONTEXT,
        ],
        applies_to_domains=["security"],
    ),
    ConfidenceFactor(
        name="cve_reference",
        description="Increases confidence when CVE references are nearby",
        weight=0.15,
        detector="detect_cve_reference",
        is_positive=True,
        max_adjustment=0.15,
        applies_to_categories=[
            PatternCategory.ENTITY,
            PatternCategory.RELATIONSHIP,
        ],
        applies_to_domains=["security"],
    ),
    ConfidenceFactor(
        name="compliance_framework",
        description="Increases confidence when compliance frameworks are mentioned",
        weight=0.10,
        detector="detect_compliance_framework",
        is_positive=True,
        max_adjustment=0.10,
        applies_to_categories=[
            PatternCategory.ENTITY,
            PatternCategory.RELATIONSHIP,
        ],
        applies_to_domains=["security"],
    ),
    ConfidenceFactor(
        name="aws_service_context",
        description="Increases confidence when AWS services are mentioned",
        weight=0.10,
        detector="detect_aws_service_context",
        is_positive=True,
        max_adjustment=0.10,
        applies_to_categories=[
            PatternCategory.ENTITY,
            PatternCategory.RELATIONSHIP,
        ],
        applies_to_domains=["security"],
    ),
]


def detect_severity_context(context: str) -> bool:
    """Detect if severity indicators are present in context.

    Args:
        context: Text context to analyze (typically surrounding text)

    Returns:
        True if severity indicators found, False otherwise
    """
    severity_keywords = [
        "critical",
        "high",
        "medium",
        "low",
        "severe",
        "severity",
        "risk",
        "priority",
        "impact",
    ]
    context_lower = context.lower()
    return any(keyword in context_lower for keyword in severity_keywords)


def detect_cve_reference(context: str) -> bool:
    """Detect if CVE references are present in context.

    Args:
        context: Text context to analyze

    Returns:
        True if CVE references found, False otherwise
    """
    import re

    cve_pattern = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
    return bool(cve_pattern.search(context))


def detect_compliance_framework(context: str) -> bool:
    """Detect if compliance framework references are present in context.

    Args:
        context: Text context to analyze

    Returns:
        True if compliance frameworks found, False otherwise
    """
    compliance_keywords = [
        "soc 2",
        "soc2",
        "hipaa",
        "pci-dss",
        "pci dss",
        "gdpr",
        "iso 27001",
        "iso27001",
        "nist",
        "fedramp",
        "fisma",
        "cis",
        "ccpa",
        "ferpa",
    ]
    context_lower = context.lower()
    return any(keyword in context_lower for keyword in compliance_keywords)


def detect_aws_service_context(context: str) -> bool:
    """Detect if AWS service references are present in context.

    Args:
        context: Text context to analyze

    Returns:
        True if AWS services found, False otherwise
    """
    aws_keywords = [
        "aws",
        "amazon",
        "ec2",
        "s3",
        "rds",
        "lambda",
        "iam",
        "kms",
        "cloudtrail",
        "guardduty",
        "security group",
        "vpc",
        "arn:",
    ]
    context_lower = context.lower()
    return any(keyword in context_lower for keyword in aws_keywords)
