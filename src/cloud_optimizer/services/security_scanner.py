"""Security scanning engine."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cloud_optimizer.integrations.aws import (
    EncryptionScanner,
    IAMScanner,
    S3SecurityScanner,
    SecurityGroupScanner,
)
from cloud_optimizer.models.aws_account import AWSAccount
from cloud_optimizer.models.finding import FindingSeverity, FindingType
from cloud_optimizer.models.scan_job import ScanJob, ScanStatus, ScanType
from cloud_optimizer.security.rule_metadata import get_rule_metadata
from cloud_optimizer.services.aws_connection import AWSConnectionService
from cloud_optimizer.services.findings import FindingsService
from cloud_optimizer.services.trial import TrialService

logger = logging.getLogger(__name__)

DEFAULT_SCAN_TYPES = {
    "s3": S3SecurityScanner,
    "security_groups": SecurityGroupScanner,
    "iam": IAMScanner,
    "encryption": EncryptionScanner,
}

SEVERITY_MAP = {
    "critical": FindingSeverity.CRITICAL,
    "high": FindingSeverity.HIGH,
    "medium": FindingSeverity.MEDIUM,
    "low": FindingSeverity.LOW,
    "info": FindingSeverity.INFO,
}


class SecurityScanEngine:
    """Coordinates AWS security scans and persists findings."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        scanner_registry: Dict[str, type] | None = None,
        aws_connection_service_factory: Callable[[AsyncSession], AWSConnectionService]
        | None = None,
        trial_service_factory: Callable[[AsyncSession], TrialService] | None = None,
        findings_service_factory: Callable[[AsyncSession], FindingsService]
        | None = None,
    ) -> None:
        self.db = db
        self._scanner_registry = scanner_registry or DEFAULT_SCAN_TYPES
        self._aws_conn_factory = aws_connection_service_factory or AWSConnectionService
        self._trial_service_factory = trial_service_factory or TrialService
        self._findings_service_factory = findings_service_factory or FindingsService

    async def start_security_scan(
        self,
        user_id: UUID,
        account_id: UUID,
        *,
        scan_types: Sequence[str] | None = None,
        region: str = "us-east-1",
    ) -> ScanJob:
        """Kick off a security scan for the given account."""
        aws_account = await self._get_account_for_user(account_id, user_id)
        scan_type_list = self._sanitize_scan_types(scan_types)
        trial_service = self._trial_service_factory(self.db)
        await trial_service.check_limit(user_id, "scans")

        job = ScanJob(
            user_id=user_id,
            aws_account_id=account_id,
            scan_type=ScanType.SECURITY,
            status=ScanStatus.PENDING,
            services_to_scan=list(scan_type_list),
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        try:
            await self._execute_scan(job, aws_account, scan_type_list, region)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Security scan failed for job %s", job.job_id)
            job.status = ScanStatus.FAILED
            job.error_message = str(exc)
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise
        else:
            await trial_service.record_usage(user_id, "scans", 1)

        return job

    async def get_scan_job(self, job_id: UUID, user_id: UUID) -> ScanJob:
        """Return scan job if it belongs to the requesting user."""
        result = await self.db.execute(
            select(ScanJob).where(ScanJob.job_id == job_id, ScanJob.user_id == user_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError("Scan job not found")
        return job

    async def _execute_scan(
        self,
        job: ScanJob,
        aws_account: AWSAccount,
        scan_type_list: Iterable[str],
        region: str,
    ) -> None:
        aws_service = self._aws_conn_factory(self.db)
        session = await aws_service.get_session(aws_account.account_id)
        findings_service = self._findings_service_factory(self.db)

        job.status = ScanStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        job.progress = 5
        job.services_to_scan = list(scan_type_list)
        await self.db.commit()

        total_findings = 0
        scan_types = list(scan_type_list)
        for idx, scan_type in enumerate(scan_types, start=1):
            scanner_cls = self._scanner_registry.get(scan_type)
            if not scanner_cls:
                logger.warning("Skipping unknown scan type: %s", scan_type)
                continue

            scanner = scanner_cls(region=region, session=session)
            findings = await scanner.scan(aws_account.aws_account_id)

            created = await self._persist_findings(
                findings_service, job, aws_account, findings
            )
            total_findings += created
            job.progress = self._calc_progress(idx, len(scan_types))
            await self.db.commit()

        job.total_findings = total_findings
        job.status = ScanStatus.COMPLETED
        job.progress = 100
        job.completed_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def _persist_findings(
        self,
        findings_service: FindingsService,
        job: ScanJob,
        aws_account: AWSAccount,
        findings: List[Dict[str, object]],
    ) -> int:
        created = 0
        for finding in findings:
            metadata = get_rule_metadata(finding.get("finding_type", ""))
            severity = self._map_severity(finding.get("severity"))
            if severity is None:
                continue

            await findings_service.create_finding(
                scan_job_id=job.job_id,
                aws_account_id=aws_account.account_id,
                rule_id=metadata.rule_id,
                finding_type=FindingType.SECURITY,
                severity=severity,
                service=finding.get("service") or metadata.service,
                resource_type=finding.get("resource_type", "aws_resource"),
                resource_id=finding.get("resource_id", "unknown"),
                region=finding.get("region", job.aws_account.default_region),
                title=finding.get("title", "Security finding"),
                description=finding.get("description", ""),
                recommendation=finding.get("remediation", "Review configuration."),
                evidence={
                    **finding.get("metadata", {}),
                    "aws_account": aws_account.aws_account_id,
                    "resource_name": finding.get("resource_name"),
                },
                compliance_frameworks=list(metadata.frameworks),
                resource_arn=finding.get("resource_arn"),
            )
            created += 1
        return created

    def _sanitize_scan_types(self, scan_types: Sequence[str] | None) -> List[str]:
        if not scan_types:
            return list(self._scanner_registry.keys())

        valid = []
        for scan in scan_types:
            if scan not in self._scanner_registry:
                logger.warning("Ignoring unknown scan type: %s", scan)
                continue
            valid.append(scan)

        if not valid:
            raise ValueError("No valid scan types provided")
        return valid

    async def _get_account_for_user(
        self, account_id: UUID, user_id: UUID
    ) -> AWSAccount:
        result = await self.db.execute(
            select(AWSAccount).where(
                AWSAccount.account_id == account_id, AWSAccount.user_id == user_id
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise ValueError("AWS account not found")
        return account

    def _calc_progress(self, idx: int, total: int) -> int:
        base = (idx / max(total, 1)) * 85
        return 5 + int(base)

    def _map_severity(self, severity: object) -> FindingSeverity | None:
        if not isinstance(severity, str):
            return None
        return SEVERITY_MAP.get(severity.lower())
