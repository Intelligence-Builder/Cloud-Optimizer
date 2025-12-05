"""Tests for Findings API."""
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from cloud_optimizer.models.aws_account import (
    AWSAccount,
    ConnectionStatus,
    ConnectionType,
)
from cloud_optimizer.models.finding import FindingSeverity, FindingStatus, FindingType
from cloud_optimizer.models.scan_job import ScanJob, ScanStatus, ScanType
from cloud_optimizer.services.findings import FindingsService


@pytest_asyncio.fixture
async def authorized_account(async_client, db_session):
    """Register a user via API and create an AWS account owned by that user."""
    email = f"findings-{uuid4()}@example.com"
    password = "ValidPass123!"
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Findings Tester"},
    )
    assert response.status_code == 201
    payload = response.json()
    user_id = UUID(payload["user"]["user_id"])
    headers = {"Authorization": f"Bearer {payload['tokens']['access_token']}"}

    account = AWSAccount(
        user_id=user_id,
        aws_account_id="123456789012",
        friendly_name="api-test-account",
        connection_type=ConnectionType.IAM_ROLE,
        role_arn="arn:aws:iam::123456789012:role/CloudOptimizerRole",
        external_id=str(uuid4()),
        status=ConnectionStatus.ACTIVE,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)

    return {"headers": headers, "account": account}


@pytest.mark.asyncio
async def test_findings_api_structure(async_client, authorized_account):
    """Test that findings API endpoints can be queried with real auth."""
    account = authorized_account["account"]
    headers = authorized_account["headers"]

    response = await async_client.get(
        f"/api/v1/findings/accounts/{account.account_id}", headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["findings"] == []


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
