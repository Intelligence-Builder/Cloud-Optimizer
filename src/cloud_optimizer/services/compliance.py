"""Compliance framework service."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cloud_optimizer.models.compliance import (
    ComplianceControl,
    ComplianceFramework,
    RuleComplianceMapping,
)
from cloud_optimizer.models.finding import Finding

logger = logging.getLogger(__name__)


# Default compliance mapping data
COMPLIANCE_DATA = {
    "CIS": {
        "display_name": "CIS AWS Foundations Benchmark",
        "version": "1.5.0",
        "description": "Center for Internet Security AWS Foundations Benchmark",
    },
    "PCI-DSS": {
        "display_name": "PCI DSS",
        "version": "4.0",
        "description": "Payment Card Industry Data Security Standard",
    },
    "HIPAA": {
        "display_name": "HIPAA",
        "version": "2023",
        "description": "Health Insurance Portability and Accountability Act",
    },
    "SOC2": {
        "display_name": "SOC 2",
        "version": "2017",
        "description": "Service Organization Control 2",
    },
    "NIST": {
        "display_name": "NIST Cybersecurity Framework",
        "version": "1.1",
        "description": "National Institute of Standards and Technology Cybersecurity Framework",
    },
    "GDPR": {
        "display_name": "GDPR",
        "version": "2016",
        "description": "General Data Protection Regulation",
    },
    "ISO27001": {
        "display_name": "ISO/IEC 27001:2022",
        "version": "2022",
        "description": "Information Security Management System (ISMS) - Annex A Controls",
    },
}


class ComplianceService:
    """Service for compliance framework operations.

    Provides methods to query compliance frameworks, controls, and
    generate compliance reports from security findings.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize compliance service.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_framework(self, name: str) -> Optional[ComplianceFramework]:
        """Get compliance framework by name.

        Args:
            name: Framework name (e.g., "CIS", "PCI-DSS")

        Returns:
            ComplianceFramework or None if not found
        """
        result = await self.db.execute(
            select(ComplianceFramework)
            .where(ComplianceFramework.name == name)
            .options(selectinload(ComplianceFramework.controls))
        )
        return result.scalar_one_or_none()

    async def get_all_frameworks(self) -> List[ComplianceFramework]:
        """Get all compliance frameworks.

        Returns:
            List of all compliance frameworks
        """
        result = await self.db.execute(select(ComplianceFramework))
        return list(result.scalars().all())

    async def get_finding_compliance(self, finding: Finding) -> Dict[str, List[str]]:
        """Get compliance frameworks affected by a finding.

        Args:
            finding: Security or cost finding

        Returns:
            Dictionary mapping framework names to control numbers
        """
        result: Dict[str, List[str]] = {}
        for framework_name in finding.compliance_frameworks:
            framework = await self.get_framework(framework_name)
            if framework:
                result[framework_name] = [c.control_number for c in framework.controls]
        return result

    async def get_compliance_summary(
        self, findings: List[Finding]
    ) -> Dict[str, Dict[str, int]]:
        """Generate compliance summary from findings.

        Args:
            findings: List of security/cost findings

        Returns:
            Dictionary with compliance summary statistics
        """
        summary: Dict[str, Dict[str, int]] = {}
        for finding in findings:
            for framework in finding.compliance_frameworks:
                if framework not in summary:
                    summary[framework] = {"total": 0, "passed": 0, "failed": 0}
                summary[framework]["total"] += 1
                if finding.status.value == "resolved":
                    summary[framework]["passed"] += 1
                else:
                    summary[framework]["failed"] += 1
        return summary

    async def get_framework_compliance_status(
        self, framework_name: str, findings: List[Finding]
    ) -> Dict[str, Any]:
        """Get detailed compliance status for a specific framework.

        Args:
            framework_name: Name of the compliance framework
            findings: List of security/cost findings

        Returns:
            Dictionary with detailed compliance status
        """
        framework = await self.get_framework(framework_name)
        if not framework:
            return {}

        # Filter findings for this framework
        framework_findings = [
            f for f in findings if framework_name in f.compliance_frameworks
        ]

        # Calculate compliance percentage
        total_findings = len(framework_findings)
        passed_findings = len(
            [f for f in framework_findings if f.status.value == "resolved"]
        )
        failed_findings = total_findings - passed_findings

        compliance_percentage = (
            (passed_findings / total_findings * 100) if total_findings > 0 else 100.0
        )

        return {
            "framework_name": framework.display_name,
            "version": framework.version,
            "total_findings": total_findings,
            "passed": passed_findings,
            "failed": failed_findings,
            "compliance_percentage": round(compliance_percentage, 2),
            "controls_affected": len(framework.controls),
        }

    async def seed_frameworks(self) -> None:
        """Seed default compliance frameworks.

        Creates default compliance frameworks if they don't exist.
        This should be called during application initialization.
        """
        for name, data in COMPLIANCE_DATA.items():
            existing = await self.get_framework(name)
            if not existing:
                framework = ComplianceFramework(
                    name=name,
                    display_name=data["display_name"],
                    version=data["version"],
                    description=data["description"],
                )
                self.db.add(framework)
                logger.info(f"Created compliance framework: {name}")
        await self.db.commit()

    async def map_rule_to_control(
        self, rule_id: str, control_id: UUID, notes: Optional[str] = None
    ) -> RuleComplianceMapping:
        """Create a mapping between a scanner rule and compliance control.

        Args:
            rule_id: Scanner rule ID
            control_id: Compliance control ID
            notes: Optional notes about the mapping

        Returns:
            Created RuleComplianceMapping
        """
        mapping = RuleComplianceMapping(
            rule_id=rule_id, control_id=control_id, notes=notes
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def get_rules_for_control(self, control_id: UUID) -> List[str]:
        """Get all scanner rule IDs mapped to a compliance control.

        Args:
            control_id: Compliance control ID

        Returns:
            List of rule IDs
        """
        result = await self.db.execute(
            select(RuleComplianceMapping.rule_id).where(
                RuleComplianceMapping.control_id == control_id
            )
        )
        return list(result.scalars().all())

    async def get_controls_for_rule(self, rule_id: str) -> List[ComplianceControl]:
        """Get all compliance controls mapped to a scanner rule.

        Args:
            rule_id: Scanner rule ID

        Returns:
            List of compliance controls
        """
        result = await self.db.execute(
            select(ComplianceControl)
            .join(RuleComplianceMapping)
            .where(RuleComplianceMapping.rule_id == rule_id)
        )
        return list(result.scalars().all())
