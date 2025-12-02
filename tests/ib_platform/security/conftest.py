"""Pytest fixtures for security module tests."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from cloud_optimizer.models.finding import (
    Finding,
    FindingSeverity,
    FindingStatus,
    FindingType,
)


@pytest.fixture
def sample_finding() -> Finding:
    """Create a sample security finding for testing.

    Returns:
        Sample Finding object
    """
    return Finding(
        finding_id=uuid4(),
        scan_job_id=uuid4(),
        aws_account_id=uuid4(),
        rule_id="AWS-S3-001",
        finding_type=FindingType.SECURITY,
        severity=FindingSeverity.HIGH,
        status=FindingStatus.OPEN,
        service="s3",
        resource_type="aws_s3_bucket",
        resource_id="test-bucket-123",
        resource_arn="arn:aws:s3:::test-bucket-123",
        region="us-east-1",
        title="S3 bucket allows public access",
        description="The S3 bucket test-bucket-123 has public access enabled",
        recommendation="Enable S3 Block Public Access",
        evidence={"public_access": True, "policy": "open"},
        compliance_frameworks=["PCI-DSS", "HIPAA"],
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def critical_finding() -> Finding:
    """Create a critical severity finding.

    Returns:
        Critical Finding object
    """
    return Finding(
        finding_id=uuid4(),
        scan_job_id=uuid4(),
        aws_account_id=uuid4(),
        rule_id="AWS-IAM-999",
        finding_type=FindingType.SECURITY,
        severity=FindingSeverity.CRITICAL,
        status=FindingStatus.OPEN,
        service="iam",
        resource_type="aws_iam_role",
        resource_id="admin-role",
        resource_arn="arn:aws:iam::123456789012:role/admin-role",
        region="us-east-1",
        title="IAM role has overly permissive policy with admin access",
        description="The IAM role admin-role has AdministratorAccess policy attached with public assume role policy",
        recommendation="Remove AdministratorAccess and apply least privilege policy",
        evidence={"policy": "*:*", "public_assume": True},
        compliance_frameworks=["SOC2", "HIPAA"],
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def low_severity_finding() -> Finding:
    """Create a low severity finding.

    Returns:
        Low severity Finding object
    """
    return Finding(
        finding_id=uuid4(),
        scan_job_id=uuid4(),
        aws_account_id=uuid4(),
        rule_id="AWS-EC2-100",
        finding_type=FindingType.SECURITY,
        severity=FindingSeverity.LOW,
        status=FindingStatus.OPEN,
        service="ec2",
        resource_type="aws_instance",
        resource_id="i-1234567890abcdef0",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
        region="us-east-1",
        title="EC2 instance missing recommended tag",
        description="EC2 instance is missing the recommended 'Environment' tag",
        recommendation="Add Environment tag to EC2 instance",
        evidence={"tags": {"Name": "test-instance"}},
        compliance_frameworks=[],
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def multiple_findings(
    sample_finding: Finding,
    critical_finding: Finding,
    low_severity_finding: Finding,
) -> list[Finding]:
    """Create a list of multiple findings for batch testing.

    Args:
        sample_finding: Sample finding fixture
        critical_finding: Critical finding fixture
        low_severity_finding: Low severity finding fixture

    Returns:
        List of Finding objects
    """
    # Create additional findings
    rds_finding = Finding(
        finding_id=uuid4(),
        scan_job_id=uuid4(),
        aws_account_id=uuid4(),
        rule_id="AWS-RDS-001",
        finding_type=FindingType.SECURITY,
        severity=FindingSeverity.HIGH,
        status=FindingStatus.OPEN,
        service="rds",
        resource_type="aws_db_instance",
        resource_id="production-db",
        resource_arn="arn:aws:rds:us-east-1:123456789012:db:production-db",
        region="us-east-1",
        title="RDS instance not encrypted",
        description="RDS database instance is not encrypted at rest",
        recommendation="Create encrypted snapshot and restore to new encrypted instance",
        evidence={"encrypted": False},
        compliance_frameworks=["HIPAA", "PCI-DSS"],
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )

    sg_finding = Finding(
        finding_id=uuid4(),
        scan_job_id=uuid4(),
        aws_account_id=uuid4(),
        rule_id="AWS-EC2-SG-001",
        finding_type=FindingType.SECURITY,
        severity=FindingSeverity.MEDIUM,
        status=FindingStatus.OPEN,
        service="ec2",
        resource_type="aws_security_group",
        resource_id="sg-0123456789abcdef0",
        resource_arn="arn:aws:ec2:us-east-1:123456789012:security-group/sg-0123456789abcdef0",
        region="us-east-1",
        title="Security group allows unrestricted ingress from 0.0.0.0/0",
        description="Security group has rule allowing SSH from any IP address",
        recommendation="Restrict SSH access to specific IP ranges",
        evidence={"ingress": [{"cidr": "0.0.0.0/0", "port": 22}]},
        compliance_frameworks=["CIS"],
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )

    return [
        sample_finding,
        critical_finding,
        low_severity_finding,
        rds_finding,
        sg_finding,
    ]


@pytest.fixture
def same_resource_type_findings() -> list[Finding]:
    """Create multiple findings for the same resource type (for correlation tests).

    Returns:
        List of S3-related findings
    """
    findings = []

    for i in range(3):
        finding = Finding(
            finding_id=uuid4(),
            scan_job_id=uuid4(),
            aws_account_id=uuid4(),
            rule_id=f"AWS-S3-00{i}",
            finding_type=FindingType.SECURITY,
            severity=FindingSeverity.MEDIUM,
            status=FindingStatus.OPEN,
            service="s3",
            resource_type="aws_s3_bucket",
            resource_id=f"test-bucket-{i}",
            resource_arn=f"arn:aws:s3:::test-bucket-{i}",
            region="us-east-1",
            title=f"S3 bucket issue {i}",
            description=f"S3 bucket test-bucket-{i} has configuration issue",
            recommendation="Fix S3 configuration",
            evidence={},
            compliance_frameworks=["PCI-DSS"],
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
        findings.append(finding)

    return findings
