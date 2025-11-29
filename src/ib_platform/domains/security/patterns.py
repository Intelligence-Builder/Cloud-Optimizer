"""Security Domain Pattern Definitions.

This module defines patterns for detecting security-specific entities and
relationships in text, including CVEs, compliance frameworks, IAM policies,
encryption references, and security relationships.
"""

import re
from typing import List
from uuid import uuid4

from ...patterns.models import PatternCategory, PatternDefinition, PatternPriority

SECURITY_PATTERNS: List[PatternDefinition] = [
    # --- ENTITY PATTERNS ---
    PatternDefinition(
        id=uuid4(),
        name="cve_reference",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\bCVE-\d{4}-\d{4,7}\b",
        output_type="vulnerability",
        base_confidence=0.95,
        priority=PatternPriority.CRITICAL,
        flags=re.IGNORECASE,
        description="Detects CVE (Common Vulnerabilities and Exposures) references",
        examples=[
            "CVE-2023-12345",
            "cve-2024-0001",
            "The vulnerability CVE-2023-44487 affects HTTP/2 servers",
        ],
        tags=["cve", "vulnerability", "security"],
        version="1.0.0",
    ),
    PatternDefinition(
        id=uuid4(),
        name="aws_arn",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\barn:aws:[a-z0-9-]+:[a-z0-9-]*:(\d{12})?:?[a-z0-9/_:-]+\b",
        output_type="identity",
        base_confidence=0.95,
        priority=PatternPriority.HIGH,
        flags=re.IGNORECASE,
        description="Detects AWS ARN (Amazon Resource Name) identifiers",
        examples=[
            "arn:aws:iam::123456789012:user/john",
            "arn:aws:s3:::my-bucket/path",
            "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
        ],
        tags=["aws", "arn", "identity", "resource"],
        version="1.0.0",
    ),
    PatternDefinition(
        id=uuid4(),
        name="compliance_framework",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\b(?:SOC\s*2|SOC2|HIPAA|PCI[-\s]?DSS|GDPR|ISO\s*27001|"
        r"ISO27001|NIST|FedRAMP|FISMA|CIS|CCPA|FERPA)\b",
        output_type="compliance_requirement",
        base_confidence=0.90,
        priority=PatternPriority.HIGH,
        flags=re.IGNORECASE,
        description="Detects compliance framework and regulatory standard references",
        examples=[
            "SOC 2 Type II compliance",
            "HIPAA requirements",
            "PCI-DSS certification",
            "GDPR data privacy",
            "ISO 27001 controls",
        ],
        tags=["compliance", "framework", "regulation", "standard"],
        version="1.0.0",
    ),
    # --- CONTEXT PATTERNS ---
    PatternDefinition(
        id=uuid4(),
        name="cvss_score",
        domain="security",
        category=PatternCategory.CONTEXT,
        regex_pattern=r"\bCVSS\s*(?:score)?\s*[:\s]*(\d+\.?\d*)\b",
        output_type="cvss_score",
        base_confidence=0.90,
        priority=PatternPriority.HIGH,
        flags=re.IGNORECASE,
        capture_groups={"score": r"(\d+\.?\d*)"},
        description="Detects CVSS (Common Vulnerability Scoring System) scores",
        examples=[
            "CVSS: 9.8",
            "CVSS score 7.5",
            "CVSS 5.3",
            "The vulnerability has CVSS 10.0 (critical)",
        ],
        tags=["cvss", "score", "severity", "vulnerability"],
        version="1.0.0",
    ),
    PatternDefinition(
        id=uuid4(),
        name="severity_indicator",
        domain="security",
        category=PatternCategory.CONTEXT,
        regex_pattern=r"\b(?:critical|high|medium|low|informational)\s+"
        r"(?:severity|risk|priority|impact)\b",
        output_type="severity",
        base_confidence=0.85,
        priority=PatternPriority.NORMAL,
        flags=re.IGNORECASE,
        description="Detects severity level indicators for security issues",
        examples=[
            "critical severity",
            "high risk",
            "medium priority",
            "low impact",
            "informational severity",
        ],
        tags=["severity", "risk", "priority", "classification"],
        version="1.0.0",
    ),
    # --- ENTITY PATTERNS (continued) ---
    PatternDefinition(
        id=uuid4(),
        name="encryption_reference",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\b(?:AES|RSA|TLS|SSL|KMS|HSM|"
        r"AES-128|AES-256|RSA-2048|RSA-4096|TLS\s*1\.\d|SSL\s*3\.\d)\b",
        output_type="encryption_config",
        base_confidence=0.80,
        priority=PatternPriority.NORMAL,
        flags=re.IGNORECASE,
        description="Detects encryption algorithm and protocol references",
        examples=[
            "AES-256 encryption",
            "RSA-2048 key",
            "TLS 1.3 protocol",
            "AWS KMS integration",
            "Hardware Security Module (HSM)",
        ],
        tags=["encryption", "crypto", "tls", "ssl", "kms"],
        version="1.0.0",
    ),
    PatternDefinition(
        id=uuid4(),
        name="security_group",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\b(?:security\s+groups?|sg-[a-f0-9]{8,17}|"
        r"network\s+security\s+groups?|NSG)\b",
        output_type="security_group",
        base_confidence=0.80,
        priority=PatternPriority.NORMAL,
        flags=re.IGNORECASE,
        description="Detects security group and network firewall references",
        examples=[
            "security group sg-1234abcd",
            "configure security groups",
            "Network Security Group (NSG)",
            "sg-0a1b2c3d4e5f67890",
        ],
        tags=["security_group", "firewall", "network", "aws", "azure"],
        version="1.0.0",
    ),
    PatternDefinition(
        id=uuid4(),
        name="iam_policy",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\b(?:IAM\s+policy|IAM\s+role|access\s+policy|"
        r"permission\s+policy|role-based\s+access|RBAC)\b",
        output_type="access_policy",
        base_confidence=0.75,
        priority=PatternPriority.NORMAL,
        flags=re.IGNORECASE,
        description="Detects IAM policy and access control references",
        examples=[
            "IAM policy configuration",
            "IAM role assignment",
            "access policy rules",
            "role-based access control (RBAC)",
            "permission policy attached",
        ],
        tags=["iam", "policy", "access", "rbac", "permissions"],
        version="1.0.0",
    ),
    # --- RELATIONSHIP PATTERNS ---
    PatternDefinition(
        id=uuid4(),
        name="mitigates_relationship",
        domain="security",
        category=PatternCategory.RELATIONSHIP,
        regex_pattern=r"(?P<source>[A-Za-z0-9\s_-]+)\s+"
        r"(?:mitigates?|reduces?|addresses?|remediates?)\s+"
        r"(?P<target>[A-Za-z0-9\s_-]+)",
        output_type="mitigates",
        base_confidence=0.75,
        priority=PatternPriority.NORMAL,
        flags=re.IGNORECASE,
        capture_groups={
            "source": r"(?P<source>[A-Za-z0-9\s_-]+)",
            "target": r"(?P<target>[A-Za-z0-9\s_-]+)",
        },
        description="Detects mitigation relationships between controls and vulnerabilities",
        examples=[
            "WAF mitigates SQL injection",
            "Encryption reduces data exposure risk",
            "Patch addresses CVE-2023-12345",
            "This control remediates the security finding",
        ],
        tags=["relationship", "mitigates", "control", "vulnerability"],
        version="1.0.0",
    ),
    PatternDefinition(
        id=uuid4(),
        name="protects_relationship",
        domain="security",
        category=PatternCategory.RELATIONSHIP,
        regex_pattern=r"(?P<source>[A-Za-z0-9\s_-]+)\s+"
        r"(?:protects?|secures?|safeguards?|defends?)\s+"
        r"(?P<target>[A-Za-z0-9\s_-]+)",
        output_type="protects",
        base_confidence=0.75,
        priority=PatternPriority.NORMAL,
        flags=re.IGNORECASE,
        capture_groups={
            "source": r"(?P<source>[A-Za-z0-9\s_-]+)",
            "target": r"(?P<target>[A-Za-z0-9\s_-]+)",
        },
        description="Detects protection relationships between controls and resources",
        examples=[
            "TLS protects data in transit",
            "Security group secures the instance",
            "Firewall safeguards the network",
            "Encryption defends sensitive information",
        ],
        tags=["relationship", "protects", "control", "resource"],
        version="1.0.0",
    ),
]
