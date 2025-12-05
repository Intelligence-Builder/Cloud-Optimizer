"""Tests for security scan engine."""

from __future__ import annotations

from uuid import uuid4

import pytest

from cloud_optimizer.models.finding import Finding
from cloud_optimizer.services.security_scanner import SecurityScanEngine


class DummyScanner:
    """Simple scanner that returns predetermined findings."""

    def __init__(self, region: str, session) -> None:
        self.region = region
        self.session = session

    def get_scanner_name(self) -> str:
        return "DummyScanner"

    async def scan(self, account_id: str):
        return [
            {
                "finding_type": "s3_public_access",
                "severity": "critical",
                "title": "Dummy Finding",
                "description": "Bucket is public.",
                "resource_arn": f"arn:aws:s3:::{account_id}-bucket",
                "resource_id": f"{account_id}-bucket",
                "resource_type": "s3_bucket",
                "service": "s3",
                "region": "us-east-1",
                "remediation": "Block public access.",
                "metadata": {},
            }
        ]


class StubAWSConnectionService:
    """Avoid boto3 calls in tests."""

    def __init__(self, *_args, **_kwargs):
        pass

    async def get_session(self, _account_id):
        return object()


@pytest.mark.asyncio
async def test_security_scan_engine_persists_findings(
    db_session, test_user, test_aws_account
) -> None:
    """Engine should store findings and update job metadata."""
    scanner = SecurityScanEngine(
        db_session,
        scanner_registry={"s3": DummyScanner},
        aws_connection_service_factory=lambda _: StubAWSConnectionService(),
    )

    job = await scanner.start_security_scan(
        user_id=test_user.user_id,
        account_id=test_aws_account.account_id,
        scan_types=["s3"],
        region="us-east-1",
    )

    assert job.status.value == "completed"
    assert job.total_findings == 1

    findings = (
        await db_session.execute(
            Finding.__table__.select().where(Finding.scan_job_id == job.job_id)
        )
    ).fetchall()
    assert findings, "Expected finding to be persisted"
    row = findings[0]
    assert row.rule_id == "S3_001"
    assert row.service == "s3"
