"""Shared fixtures for security domain tests."""

import sys
from pathlib import Path
from typing import Dict

import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from ib_platform.domains.security.domain import SecurityDomain


@pytest.fixture
def security_domain() -> SecurityDomain:
    """Provide a SecurityDomain instance for testing."""
    return SecurityDomain()


@pytest.fixture
def sample_vulnerability_data() -> Dict[str, str]:
    """Provide sample vulnerability entity data."""
    return {
        "name": "CVE-2021-44228",
        "cve_id": "CVE-2021-44228",
        "severity": "critical",
        "cvss_score": "10.0",
        "description": "Log4Shell vulnerability",
    }


@pytest.fixture
def sample_control_data() -> Dict[str, str]:
    """Provide sample control entity data."""
    return {
        "name": "WAF Rule Set",
        "control_type": "preventive",
        "description": "Web Application Firewall rules",
        "implementation_status": "active",
    }


@pytest.fixture
def sample_identity_data() -> Dict[str, str]:
    """Provide sample identity entity data."""
    return {
        "name": "admin-user",
        "identity_type": "user",
        "arn": "arn:aws:iam::123456789:user/admin",
        "mfa_enabled": "True",
    }


@pytest.fixture
def sample_compliance_requirement_data() -> Dict[str, str]:
    """Provide sample compliance requirement entity data."""
    return {
        "name": "SOC2-CC6.1",
        "framework": "SOC2",
        "description": "Logical and Physical Access Controls",
        "control_family": "CC6",
    }


@pytest.fixture
def sample_encryption_config_data() -> Dict[str, str]:
    """Provide sample encryption configuration entity data."""
    return {
        "name": "S3-Encryption",
        "algorithm": "AES-256",
        "key_length": "256",
        "key_management": "AWS KMS",
    }


@pytest.fixture
def sample_threat_data() -> Dict[str, str]:
    """Provide sample threat entity data."""
    return {
        "name": "SQL Injection",
        "threat_type": "injection",
        "description": "Code injection attack on database",
    }


@pytest.fixture
def sample_security_finding_data() -> Dict[str, str]:
    """Provide sample security finding entity data."""
    return {
        "name": "Unencrypted S3 Bucket",
        "severity": "high",
        "finding_type": "misconfiguration",
        "resource": "s3://my-bucket",
    }


@pytest.fixture
def sample_access_policy_data() -> Dict[str, str]:
    """Provide sample access policy entity data."""
    return {
        "name": "AdminAccessPolicy",
        "policy_type": "managed",
        "principals": "arn:aws:iam::123456789:user/admin",
    }


@pytest.fixture
def sample_security_group_data() -> Dict[str, str]:
    """Provide sample security group entity data."""
    return {
        "name": "web-sg",
        "ingress_rules": "80,443",
        "egress_rules": "all",
    }
