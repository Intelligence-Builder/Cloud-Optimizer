"""Knowledge Base service for querying and searching KB content.

This module provides a singleton service for loading, caching, and querying
knowledge base content including compliance controls, best practices, patterns,
and remediation templates.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from ib_platform.kb.loader import KBLoader
from ib_platform.kb.models import (
    ComplianceControl,
    KBEntry,
    RemediationTemplate,
    SecurityPattern,
    ServiceBestPractice,
)

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """Singleton service for Knowledge Base operations.

    Loads KB data at startup and caches it in memory for fast queries.
    Provides search, filtering, and retrieval methods.

    Example:
        >>> kb_service = KnowledgeBaseService.get_instance()
        >>> kb_service.load()
        >>> controls = kb_service.get_framework_controls("CIS")
        >>> results = kb_service.search("encryption", limit=10)
    """

    _instance: Optional["KnowledgeBaseService"] = None

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Initialize the Knowledge Base service.

        Args:
            data_dir: Path to data directory (defaults to data/compliance)
        """
        self.loader = KBLoader(data_dir)
        self._loaded = False

        # Cache for loaded data
        self._frameworks: Dict[str, List[ComplianceControl]] = {}
        self._services: Dict[str, List[ServiceBestPractice]] = {}
        self._patterns: List[SecurityPattern] = []
        self._remediation: Dict[str, RemediationTemplate] = {}

    @classmethod
    def get_instance(cls, data_dir: Optional[Path] = None) -> "KnowledgeBaseService":
        """Get or create the singleton instance.

        Args:
            data_dir: Path to data directory (only used on first call)

        Returns:
            The singleton KnowledgeBaseService instance
        """
        if cls._instance is None:
            cls._instance = cls(data_dir)
        return cls._instance

    def load(self) -> None:
        """Load all knowledge base data from YAML files.

        Loads frameworks, services, patterns, and remediation templates into
        memory for fast access. This should be called once at application startup.
        """
        logger.info("Loading Knowledge Base data...")

        self._frameworks = self.loader.load_frameworks()
        self._services = self.loader.load_services()
        self._patterns = self.loader.load_patterns()
        self._remediation = self.loader.load_remediation()

        self._loaded = True
        logger.info(
            f"KB loaded: {len(self._frameworks)} frameworks, "
            f"{len(self._services)} services, "
            f"{len(self._patterns)} patterns, "
            f"{len(self._remediation)} remediation templates"
        )

    def is_loaded(self) -> bool:
        """Check if KB data has been loaded.

        Returns:
            True if data has been loaded, False otherwise
        """
        return self._loaded

    def get_framework_controls(
        self, framework: str
    ) -> Optional[List[ComplianceControl]]:
        """Get all controls for a specific framework.

        Args:
            framework: Framework name (case-insensitive, e.g., "CIS", "NIST")

        Returns:
            List of ComplianceControl objects, or None if framework not found

        Example:
            >>> controls = kb_service.get_framework_controls("CIS")
        """
        framework_upper = framework.upper()
        return self._frameworks.get(framework_upper)

    def get_control(
        self, framework: str, control_id: str
    ) -> Optional[ComplianceControl]:
        """Get a specific control from a framework.

        Args:
            framework: Framework name (case-insensitive)
            control_id: Control identifier (case-sensitive)

        Returns:
            ComplianceControl object, or None if not found

        Example:
            >>> control = kb_service.get_control("CIS", "1.1")
        """
        controls = self.get_framework_controls(framework)
        if not controls:
            return None

        for control in controls:
            if control.control_id == control_id:
                return control
        return None

    def get_service_best_practices(
        self, service: str, category: Optional[str] = None
    ) -> List[ServiceBestPractice]:
        """Get best practices for an AWS service.

        Args:
            service: AWS service name (case-insensitive, e.g., "S3", "EC2")
            category: Optional category filter (e.g., "security", "cost")

        Returns:
            List of ServiceBestPractice objects (empty if service not found)

        Example:
            >>> practices = kb_service.get_service_best_practices("S3", "security")
        """
        service_upper = service.upper()
        practices = self._services.get(service_upper, [])

        if category:
            category_lower = category.lower()
            practices = [p for p in practices if p.category.lower() == category_lower]

        return practices

    def get_for_framework(self, framework: str) -> List[KBEntry]:
        """Get all KB entries related to a framework.

        Converts ComplianceControl objects to unified KBEntry format.

        Args:
            framework: Framework name (case-insensitive)

        Returns:
            List of KBEntry objects

        Example:
            >>> entries = kb_service.get_for_framework("CIS")
        """
        controls = self.get_framework_controls(framework)
        if not controls:
            return []

        entries = []
        for control in controls:
            entry = KBEntry(
                entry_type="control",
                control_name=control.name,
                description=control.description,
                guidance=control.implementation_guidance,
                framework=control.framework,
                service=None,
                terraform="",
                cli="",
                metadata={
                    "control_id": control.control_id,
                    "requirements": control.requirements,
                    "aws_services": control.aws_services,
                },
            )
            entries.append(entry)

        return entries

    def get_for_service(self, service: str) -> List[KBEntry]:
        """Get all KB entries related to an AWS service.

        Converts ServiceBestPractice objects to unified KBEntry format.

        Args:
            service: AWS service name (case-insensitive)

        Returns:
            List of KBEntry objects

        Example:
            >>> entries = kb_service.get_for_service("S3")
        """
        practices = self.get_service_best_practices(service)
        if not practices:
            return []

        entries = []
        for practice in practices:
            entry = KBEntry(
                entry_type="practice",
                control_name=practice.title,
                description=practice.description,
                guidance=practice.implementation,
                framework=None,
                service=practice.service,
                terraform=practice.terraform_example,
                cli=practice.cli_example,
                metadata={
                    "category": practice.category,
                    "compliance_frameworks": practice.compliance_frameworks,
                    "console_steps": practice.console_steps,
                },
            )
            entries.append(entry)

        return entries

    def get_remediation(self, rule_id: str) -> Optional[RemediationTemplate]:
        """Get remediation template for a specific rule.

        Args:
            rule_id: Security rule identifier (case-sensitive)

        Returns:
            RemediationTemplate object, or None if not found

        Example:
            >>> template = kb_service.get_remediation("s3-bucket-public-read-prohibited")
        """
        return self._remediation.get(rule_id)

    def search(self, query: str, limit: int = 10) -> List[KBEntry]:
        """Search KB entries by keyword.

        Performs case-insensitive keyword search across all KB content types.
        Searches in names, descriptions, and guidance text.

        Args:
            query: Search query string
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of matching KBEntry objects, sorted by relevance

        Example:
            >>> results = kb_service.search("encryption", limit=20)
        """
        query_lower = query.lower()
        results: List[KBEntry] = []

        # Search compliance controls
        for framework_controls in self._frameworks.values():
            for control in framework_controls:
                score = 0
                if query_lower in control.name.lower():
                    score += 3
                if query_lower in control.description.lower():
                    score += 2
                if query_lower in control.implementation_guidance.lower():
                    score += 1

                if score > 0:
                    entry = KBEntry(
                        entry_type="control",
                        control_name=control.name,
                        description=control.description,
                        guidance=control.implementation_guidance,
                        framework=control.framework,
                        service=None,
                        terraform="",
                        cli="",
                        metadata={
                            "control_id": control.control_id,
                            "requirements": control.requirements,
                            "aws_services": control.aws_services,
                            "score": score,
                        },
                    )
                    results.append(entry)

        # Search service best practices
        for service_practices in self._services.values():
            for practice in service_practices:
                score = 0
                if query_lower in practice.title.lower():
                    score += 3
                if query_lower in practice.description.lower():
                    score += 2
                if query_lower in practice.implementation.lower():
                    score += 1

                if score > 0:
                    entry = KBEntry(
                        entry_type="practice",
                        control_name=practice.title,
                        description=practice.description,
                        guidance=practice.implementation,
                        framework=None,
                        service=practice.service,
                        terraform=practice.terraform_example,
                        cli=practice.cli_example,
                        metadata={
                            "category": practice.category,
                            "compliance_frameworks": practice.compliance_frameworks,
                            "score": score,
                        },
                    )
                    results.append(entry)

        # Search security patterns
        for pattern in self._patterns:
            score = 0
            if query_lower in pattern.name.lower():
                score += 3
            if query_lower in pattern.description.lower():
                score += 2

            if score > 0:
                entry = KBEntry(
                    entry_type="pattern",
                    control_name=pattern.name,
                    description=pattern.description,
                    guidance=" ".join(pattern.implementation_steps),
                    framework=None,
                    service=None,
                    terraform=pattern.code_examples.get("terraform", ""),
                    cli=pattern.code_examples.get("cli", ""),
                    metadata={
                        "pattern_id": pattern.pattern_id,
                        "category": pattern.category,
                        "applicable_services": pattern.applicable_services,
                        "compliance_frameworks": pattern.compliance_frameworks,
                        "score": score,
                    },
                )
                results.append(entry)

        # Search remediation templates
        for template in self._remediation.values():
            score = 0
            if query_lower in template.title.lower():
                score += 3
            if query_lower in template.description.lower():
                score += 2

            if score > 0:
                entry = KBEntry(
                    entry_type="remediation",
                    control_name=template.title,
                    description=template.description,
                    guidance=template.description,
                    framework=None,
                    service=None,
                    terraform=template.terraform,
                    cli=template.cli,
                    metadata={
                        "template_id": template.template_id,
                        "rule_id": template.rule_id,
                        "console_steps": template.console_steps,
                        "score": score,
                    },
                )
                results.append(entry)

        # Sort by score (highest first)
        results.sort(key=lambda e: e.metadata.get("score", 0), reverse=True)

        # Apply limit
        return results[:limit]

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about KB content.

        Returns:
            Dictionary with counts of various KB data types

        Example:
            >>> stats = kb_service.get_statistics()
            >>> print(f"Total frameworks: {stats['frameworks']}")
        """
        total_controls = sum(len(controls) for controls in self._frameworks.values())
        total_practices = sum(len(practices) for practices in self._services.values())

        return {
            "frameworks": len(self._frameworks),
            "total_controls": total_controls,
            "services": len(self._services),
            "total_practices": total_practices,
            "patterns": len(self._patterns),
            "remediation_templates": len(self._remediation),
        }


# Convenience function for getting the singleton instance
def get_kb_service() -> KnowledgeBaseService:
    """Get the Knowledge Base service instance.

    Returns:
        The singleton KnowledgeBaseService instance
    """
    return KnowledgeBaseService.get_instance()
