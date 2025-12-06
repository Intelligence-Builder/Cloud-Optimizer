"""Tests for response formatter."""

from uuid import uuid4

import pytest

from cloud_optimizer.models.finding import Finding, FindingSeverity, FindingStatus
from ib_platform.answer.formatter import ResponseFormatter


def test_get_severity_icon():
    """Test severity icon retrieval."""
    assert ResponseFormatter.get_severity_icon("critical") == "🔴"
    assert ResponseFormatter.get_severity_icon("high") == "🟠"
    assert ResponseFormatter.get_severity_icon("medium") == "🟡"
    assert ResponseFormatter.get_severity_icon("low") == "🟢"
    assert ResponseFormatter.get_severity_icon("info") == "ℹ️"
    assert ResponseFormatter.get_severity_icon("unknown") == "⚪"


def test_format_security_advice_basic():
    """Test basic security advice formatting."""
    content = "Enable MFA for all IAM users."

    result = ResponseFormatter.format_security_advice(content)

    assert "Enable MFA for all IAM users." in result


def test_format_security_advice_with_findings():
    """Test security advice formatting with findings."""
    content = "Enable MFA for all IAM users."

    finding = Finding(
        finding_id=uuid4(),
        scan_job_id=uuid4(),
        aws_account_id=uuid4(),
        rule_id="iam-mfa-enabled",
        finding_type="security",
        severity=FindingSeverity.HIGH,
        status=FindingStatus.OPEN,
        service="IAM",
        resource_type="User",
        resource_id="user-123",
        region="us-east-1",
        title="MFA not enabled",
        description="IAM user does not have MFA enabled",
        recommendation="Enable MFA",
        evidence={},
        compliance_frameworks=["CIS"],
    )

    result = ResponseFormatter.format_security_advice(content, findings=[finding])

    assert "Related Findings" in result
    assert "MFA not enabled" in result
    assert "🟠" in result  # High severity icon


def test_format_security_advice_with_compliance():
    """Test security advice formatting with compliance frameworks."""
    content = "Enable MFA for all IAM users."

    result = ResponseFormatter.format_security_advice(
        content,
        compliance=["CIS", "NIST", "HIPAA"],
    )

    assert "Compliance Frameworks" in result
    assert "CIS" in result
    assert "NIST" in result
    assert "HIPAA" in result


def test_format_remediation():
    """Test remediation formatting."""
    result = ResponseFormatter.format_remediation(
        title="Enable S3 Bucket Encryption",
        steps=[
            "Navigate to S3 console",
            "Select the bucket",
            "Enable default encryption",
        ],
    )

    assert "## Remediation: Enable S3 Bucket Encryption" in result
    assert "### Steps:" in result
    assert "1. Navigate to S3 console" in result
    assert "2. Select the bucket" in result
    assert "3. Enable default encryption" in result


def test_format_remediation_with_code():
    """Test remediation formatting with code example."""
    code = """resource "aws_s3_bucket_server_side_encryption_configuration" "example" {
  bucket = aws_s3_bucket.example.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}"""

    result = ResponseFormatter.format_remediation(
        title="Enable S3 Bucket Encryption",
        steps=["Apply Terraform configuration"],
        code=code,
        language="hcl",
    )

    assert "### Code Example (hcl):" in result
    assert "```hcl" in result
    assert code in result
    assert "```" in result


def test_format_finding_summary():
    """Test finding summary formatting."""
    findings = [
        Finding(
            finding_id=uuid4(),
            scan_job_id=uuid4(),
            aws_account_id=uuid4(),
            rule_id="rule-1",
            finding_type="security",
            severity=FindingSeverity.CRITICAL,
            status=FindingStatus.OPEN,
            service="S3",
            resource_type="Bucket",
            resource_id="bucket-1",
            region="us-east-1",
            title="Public bucket",
            description="Bucket is public",
            recommendation="Make private",
            evidence={},
            compliance_frameworks=["CIS"],
        ),
        Finding(
            finding_id=uuid4(),
            scan_job_id=uuid4(),
            aws_account_id=uuid4(),
            rule_id="rule-2",
            finding_type="security",
            severity=FindingSeverity.HIGH,
            status=FindingStatus.OPEN,
            service="IAM",
            resource_type="User",
            resource_id="user-1",
            region="us-east-1",
            title="No MFA",
            description="User has no MFA",
            recommendation="Enable MFA",
            evidence={},
            compliance_frameworks=["NIST"],
        ),
    ]

    result = ResponseFormatter.format_finding_summary(findings)

    assert "## Security Findings Summary" in result
    assert "### 🔴 CRITICAL (1)" in result
    assert "### 🟠 HIGH (1)" in result
    assert "Public bucket" in result
    assert "No MFA" in result


def test_format_finding_summary_empty():
    """Test finding summary with no findings."""
    result = ResponseFormatter.format_finding_summary([])

    assert "No security findings detected" in result


def test_format_code_snippet():
    """Test code snippet formatting."""
    code = "aws s3api put-bucket-encryption --bucket my-bucket"

    result = ResponseFormatter.format_code_snippet(
        code,
        language="bash",
        description="Enable S3 bucket encryption",
    )

    assert "Enable S3 bucket encryption" in result
    assert "```bash" in result
    assert code in result
    assert "```" in result


def test_format_compliance_mapping():
    """Test compliance control mapping formatting."""
    result = ResponseFormatter.format_compliance_mapping(
        control_name="Enable MFA",
        framework="CIS",
        requirements=[
            "MFA for all users",
            "MFA for console access",
            "MFA for API access",
        ],
        implementation="Use AWS IAM to configure MFA for all users",
    )

    assert "## CIS: Enable MFA" in result
    assert "### Requirements:" in result
    assert "MFA for all users" in result
    assert "### Implementation:" in result
    assert "Use AWS IAM" in result


def test_format_multi_code_example():
    """Test multi-code example formatting."""
    terraform = 'resource "aws_s3_bucket" "example" {}'
    cli = "aws s3api create-bucket --bucket my-bucket"
    console_steps = [
        "Open S3 console",
        "Click Create bucket",
        "Enter bucket name",
        "Click Create",
    ]

    result = ResponseFormatter.format_multi_code_example(
        terraform=terraform,
        cli=cli,
        console_steps=console_steps,
    )

    assert "## Implementation Examples" in result
    assert "### Terraform" in result
    assert "```hcl" in result
    assert terraform in result
    assert "### AWS CLI" in result
    assert "```bash" in result
    assert cli in result
    assert "### AWS Console" in result
    assert "1. Open S3 console" in result
    assert "4. Click Create" in result


def test_format_multi_code_example_partial():
    """Test multi-code example with only some examples."""
    terraform = 'resource "aws_s3_bucket" "example" {}'

    result = ResponseFormatter.format_multi_code_example(terraform=terraform)

    assert "### Terraform" in result
    assert terraform in result
    assert "### AWS CLI" not in result
    assert "### AWS Console" not in result
