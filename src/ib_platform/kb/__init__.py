"""Knowledge Base module for Cloud Optimizer.

This module provides data models, loading, and querying capabilities for:
- Compliance framework controls (CIS, NIST, PCI-DSS, etc.)
- AWS service best practices
- Security patterns
- Remediation templates
"""

from ib_platform.kb.loader import KBLoader
from ib_platform.kb.models import (
    ComplianceControl,
    KBEntry,
    RemediationTemplate,
    SecurityPattern,
    ServiceBestPractice,
)
from ib_platform.kb.service import KnowledgeBaseService

__all__ = [
    "ComplianceControl",
    "ServiceBestPractice",
    "SecurityPattern",
    "RemediationTemplate",
    "KBEntry",
    "KBLoader",
    "KnowledgeBaseService",
]
