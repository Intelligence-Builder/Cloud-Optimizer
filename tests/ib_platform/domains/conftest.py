"""Shared fixtures for domain tests."""

import sys
from pathlib import Path

import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from platform.domains.security.domain import SecurityDomain


@pytest.fixture
def security_domain() -> SecurityDomain:
    """Provide a SecurityDomain instance for testing."""
    return SecurityDomain()


@pytest.fixture
def sample_vulnerability_data() -> dict:
    """Provide sample vulnerability entity data."""
    return {
        "name": "CVE-2021-44228",
        "cve_id": "CVE-2021-44228",
        "severity": "critical",
        "cvss_score": 10.0,
        "description": "Log4Shell vulnerability",
    }


@pytest.fixture
def sample_control_data() -> dict:
    """Provide sample control entity data."""
    return {
        "name": "WAF Rule Set",
        "control_type": "preventive",
        "description": "Web Application Firewall rules",
        "implementation_status": "active",
    }


@pytest.fixture
def sample_identity_data() -> dict:
    """Provide sample identity entity data."""
    return {
        "name": "admin-user",
        "identity_type": "user",
        "arn": "arn:aws:iam::123456789:user/admin",
        "mfa_enabled": True,
    }
