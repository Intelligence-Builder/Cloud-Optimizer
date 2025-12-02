"""Tests for Findings service."""
import pytest

from cloud_optimizer.models.finding import FindingSeverity, FindingStatus, FindingType
from cloud_optimizer.models.scan_job import ScanJob, ScanStatus, ScanType
from cloud_optimizer.services.findings import FindingsService


@pytest.mark.asyncio
async def test_create_finding(db_session, test_user, test_aws_account):
    """Test creating a new finding."""
    # Create a scan job first (required by foreign key)
    scan_job = ScanJob(
        user_id=test_user.user_id,
        aws_account_id=test_aws_account.account_id,
        scan_type=ScanType.SECURITY,
        status=ScanStatus.RUNNING,
    )
    db_session.add(scan_job)
    await db_session.commit()

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

    assert finding.finding_id is not None
    assert finding.rule_id == "S3_001"
    assert finding.severity == FindingSeverity.CRITICAL
    assert finding.status == FindingStatus.OPEN


@pytest.mark.asyncio
async def test_deduplication(db_session, test_user, test_aws_account):
    """Test finding deduplication."""
    # Create a scan job
    scan_job = ScanJob(
        user_id=test_user.user_id,
        aws_account_id=test_aws_account.account_id,
        scan_type=ScanType.SECURITY,
        status=ScanStatus.RUNNING,
    )
    db_session.add(scan_job)
    await db_session.commit()

    service = FindingsService(db_session)
    aws_account_id = scan_job.aws_account_id

    # Create first finding
    f1 = await service.create_finding(
        scan_job_id=scan_job.job_id,
        aws_account_id=aws_account_id,
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

    # Create duplicate finding
    f2 = await service.create_finding(
        scan_job_id=scan_job.job_id,
        aws_account_id=aws_account_id,
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

    # Should return same finding (deduplication)
    assert f1.finding_id == f2.finding_id


@pytest.mark.asyncio
async def test_get_findings_by_account(db_session, test_user, test_aws_account):
    """Test getting findings by account."""
    # Create scan job
    scan_job = ScanJob(
        user_id=test_user.user_id,
        aws_account_id=test_aws_account.account_id,
        scan_type=ScanType.SECURITY,
        status=ScanStatus.RUNNING,
    )
    db_session.add(scan_job)
    await db_session.commit()

    service = FindingsService(db_session)

    # Create multiple findings
    await service.create_finding(
        scan_job_id=scan_job.job_id,
        aws_account_id=scan_job.aws_account_id,
        rule_id="S3_001",
        finding_type=FindingType.SECURITY,
        severity=FindingSeverity.CRITICAL,
        service="S3",
        resource_type="AWS::S3::Bucket",
        resource_id="bucket-1",
        region="us-east-1",
        title="Public Bucket 1",
        description="Bucket is public",
        recommendation="Block public access",
    )

    await service.create_finding(
        scan_job_id=scan_job.job_id,
        aws_account_id=scan_job.aws_account_id,
        rule_id="EC2_001",
        finding_type=FindingType.SECURITY,
        severity=FindingSeverity.HIGH,
        service="EC2",
        resource_type="AWS::EC2::Instance",
        resource_id="instance-1",
        region="us-east-1",
        title="Unencrypted Instance",
        description="Instance storage not encrypted",
        recommendation="Enable encryption",
    )

    # Get all findings
    findings = await service.get_findings_by_account(scan_job.aws_account_id)
    assert len(findings) == 2

    # Filter by severity
    critical_findings = await service.get_findings_by_account(
        scan_job.aws_account_id, severity=FindingSeverity.CRITICAL
    )
    assert len(critical_findings) == 1
    assert critical_findings[0].severity == FindingSeverity.CRITICAL


@pytest.mark.asyncio
async def test_update_status(db_session, test_user, test_aws_account):
    """Test updating finding status."""
    # Create scan job
    scan_job = ScanJob(
        user_id=test_user.user_id,
        aws_account_id=test_aws_account.account_id,
        scan_type=ScanType.SECURITY,
        status=ScanStatus.RUNNING,
    )
    db_session.add(scan_job)
    await db_session.commit()

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

    # Update status
    updated = await service.update_status(finding.finding_id, FindingStatus.RESOLVED)
    assert updated.status == FindingStatus.RESOLVED
    assert updated.resolved_at is not None


@pytest.mark.asyncio
async def test_get_summary(db_session, test_user, test_aws_account):
    """Test getting findings summary."""
    # Create scan job
    scan_job = ScanJob(
        user_id=test_user.user_id,
        aws_account_id=test_aws_account.account_id,
        scan_type=ScanType.SECURITY,
        status=ScanStatus.RUNNING,
    )
    db_session.add(scan_job)
    await db_session.commit()

    service = FindingsService(db_session)

    # Create findings with different severities
    await service.create_finding(
        scan_job_id=scan_job.job_id,
        aws_account_id=scan_job.aws_account_id,
        rule_id="S3_001",
        finding_type=FindingType.SECURITY,
        severity=FindingSeverity.CRITICAL,
        service="S3",
        resource_type="AWS::S3::Bucket",
        resource_id="bucket-1",
        region="us-east-1",
        title="Public Bucket",
        description="Bucket is public",
        recommendation="Block public access",
    )

    await service.create_finding(
        scan_job_id=scan_job.job_id,
        aws_account_id=scan_job.aws_account_id,
        rule_id="EC2_001",
        finding_type=FindingType.SECURITY,
        severity=FindingSeverity.HIGH,
        service="EC2",
        resource_type="AWS::EC2::Instance",
        resource_id="instance-1",
        region="us-east-1",
        title="Unencrypted Instance",
        description="Instance storage not encrypted",
        recommendation="Enable encryption",
    )

    summary = await service.get_summary(scan_job.aws_account_id)
    assert summary["total"] == 2
    assert summary["by_severity"]["critical"] == 1
    assert summary["by_severity"]["high"] == 1
    assert summary["by_status"]["open"] == 2
