"""Findings management service."""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cloud_optimizer.models.finding import (
    Finding,
    FindingSeverity,
    FindingStatus,
    FindingType,
)

logger = logging.getLogger(__name__)


class FindingsService:
    """Service for managing security and cost findings."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize findings service.

        Args:
            db: Async database session
        """
        self.db = db

    async def create_finding(
        self,
        scan_job_id: UUID,
        aws_account_id: UUID,
        rule_id: str,
        finding_type: FindingType,
        severity: FindingSeverity,
        service: str,
        resource_type: str,
        resource_id: str,
        region: str,
        title: str,
        description: str,
        recommendation: str,
        evidence: dict | None = None,
        compliance_frameworks: list | None = None,
        resource_arn: str | None = None,
        potential_savings: float | None = None,
    ) -> Finding:
        """Create a new finding.

        Args:
            scan_job_id: ID of the scan job that found this issue
            aws_account_id: ID of the AWS account
            rule_id: Rule identifier that triggered this finding
            finding_type: Type of finding (security or cost)
            severity: Severity level
            service: AWS service name
            resource_type: Type of AWS resource
            resource_id: Resource identifier
            region: AWS region
            title: Short finding title
            description: Detailed description
            recommendation: Remediation recommendation
            evidence: Additional evidence data
            compliance_frameworks: List of applicable compliance frameworks
            resource_arn: AWS resource ARN
            potential_savings: Estimated cost savings (for cost findings)

        Returns:
            Created or updated finding
        """
        # Check for existing finding (deduplication)
        existing = await self._find_existing(aws_account_id, rule_id, resource_id)
        if existing:
            existing.last_seen_at = datetime.now(timezone.utc)
            existing.evidence = evidence or {}
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        finding = Finding(
            scan_job_id=scan_job_id,
            aws_account_id=aws_account_id,
            rule_id=rule_id,
            finding_type=finding_type,
            severity=severity,
            service=service,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_arn=resource_arn,
            region=region,
            title=title,
            description=description,
            recommendation=recommendation,
            evidence=evidence or {},
            compliance_frameworks=compliance_frameworks or [],
            potential_savings=potential_savings,
        )
        self.db.add(finding)
        await self.db.commit()
        await self.db.refresh(finding)
        return finding

    async def _find_existing(
        self, aws_account_id: UUID, rule_id: str, resource_id: str
    ) -> Optional[Finding]:
        """Find existing open finding for deduplication.

        Args:
            aws_account_id: AWS account ID
            rule_id: Rule identifier
            resource_id: Resource identifier

        Returns:
            Existing finding if found, None otherwise
        """
        result = await self.db.execute(
            select(Finding).where(
                Finding.aws_account_id == aws_account_id,
                Finding.rule_id == rule_id,
                Finding.resource_id == resource_id,
                Finding.status == FindingStatus.OPEN,
            )
        )
        return result.scalar_one_or_none()

    async def get_finding(self, finding_id: UUID) -> Optional[Finding]:
        """Get a finding by ID.

        Args:
            finding_id: Finding ID

        Returns:
            Finding if found, None otherwise
        """
        return await self.db.get(Finding, finding_id)

    async def get_findings_by_account(
        self,
        aws_account_id: UUID,
        severity: Optional[FindingSeverity] = None,
        status: Optional[FindingStatus] = None,
        service: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Finding]:
        """Get findings for an AWS account with optional filters.

        Args:
            aws_account_id: AWS account ID
            severity: Filter by severity level
            status: Filter by status
            service: Filter by AWS service
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of findings
        """
        query = select(Finding).where(Finding.aws_account_id == aws_account_id)

        if severity:
            query = query.where(Finding.severity == severity)
        if status:
            query = query.where(Finding.status == status)
        if service:
            query = query.where(Finding.service == service)

        query = query.order_by(Finding.first_seen_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self, finding_id: UUID, status: FindingStatus
    ) -> Optional[Finding]:
        """Update finding status.

        Args:
            finding_id: Finding ID
            status: New status

        Returns:
            Updated finding if found, None otherwise
        """
        finding = await self.get_finding(finding_id)
        if finding:
            finding.status = status
            if status == FindingStatus.RESOLVED:
                finding.resolved_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(finding)
        return finding

    async def get_summary(self, aws_account_id: UUID) -> dict:
        """Get findings summary for an account.

        Args:
            aws_account_id: AWS account ID

        Returns:
            Summary dictionary with counts by severity and status
        """
        result = await self.db.execute(
            select(
                Finding.severity,
                Finding.status,
                func.count(Finding.finding_id).label("count"),
            )
            .where(Finding.aws_account_id == aws_account_id)
            .group_by(Finding.severity, Finding.status)
        )

        summary = {
            "total": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            "by_status": {
                "open": 0,
                "resolved": 0,
                "suppressed": 0,
                "false_positive": 0,
            },
        }

        for row in result:
            count = row.count
            summary["total"] += count
            summary["by_severity"][row.severity.value] += count
            summary["by_status"][row.status.value] += count

        return summary
