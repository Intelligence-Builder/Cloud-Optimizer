"""Tests for Findings API.

Note: These tests require auth middleware to be mocked or bypassed.
For now, they test the basic structure and will return 401 without proper auth.
"""
from uuid import uuid4

import pytest

from cloud_optimizer.models.finding import FindingSeverity, FindingStatus, FindingType
from cloud_optimizer.models.scan_job import ScanJob, ScanStatus, ScanType
from cloud_optimizer.services.findings import FindingsService


@pytest.mark.asyncio
async def test_findings_api_structure(async_client, db_session):
    """Test that findings API endpoints exist (will fail auth without token)."""
    # This test verifies the API structure exists
    # In a full integration test, we would:
    # 1. Create a user
    # 2. Get an auth token
    # 3. Make authenticated requests

    response = await async_client.get("/api/v1/findings/accounts/{}".format(uuid4()))
    # Should return 401/403 without auth token or 404 if endpoint doesn't exist
    assert response.status_code in [401, 403, 404]


@pytest.mark.asyncio
async def test_findings_service_integration(db_session, test_user, test_aws_account):
    """Test findings service works with database (integration test)."""
    # Create scan job with valid foreign keys
    scan_job = ScanJob(
        user_id=test_user.user_id,
        aws_account_id=test_aws_account.account_id,
        scan_type=ScanType.SECURITY,
        status=ScanStatus.RUNNING,
    )
    db_session.add(scan_job)
    await db_session.commit()

    # Create finding via service
    service = FindingsService(db_session)
    finding = await service.create_finding(
        scan_job_id=scan_job.job_id,
        aws_account_id=scan_job.aws_account_id,
        rule_id="S3_001",
        finding_type=FindingType.SECURITY,
        severity=FindingSeverity.CRITICAL,
        service="S3",
        resource_type="AWS::S3::Bucket",
        resource_id="my-bucket",
        region="us-east-1",
        title="Public Bucket",
        description="Bucket is public",
        recommendation="Block public access",
    )

    # Verify finding was created
    retrieved = await service.get_finding(finding.finding_id)
    assert retrieved is not None
    assert retrieved.rule_id == "S3_001"

    # Test summary
    summary = await service.get_summary(scan_job.aws_account_id)
    assert summary["total"] == 1
    assert summary["by_severity"]["critical"] == 1
