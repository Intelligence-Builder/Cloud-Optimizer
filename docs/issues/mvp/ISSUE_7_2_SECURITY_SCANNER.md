# 7.2 Security Scanner Engine

## Parent Epic
Epic 7: MVP Phase 2 - Security & Cost Scanning

## Overview

Implement the security scanning engine that analyzes AWS account configurations against security best practices and compliance frameworks. The scanner detects misconfigurations in S3, EC2, RDS, IAM, and other core AWS services.

## Background

The security scanner is the core value proposition for trial customers. It must:
- Scan AWS resources efficiently (< 5 minutes for typical account)
- Detect real misconfigurations that matter
- Map findings to compliance frameworks (HIPAA, SOC2, etc.)
- Provide actionable remediation guidance
- Rate-limit scans based on trial limits

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| SEC-001 | S3 scanning | Public access, encryption, versioning, logging checks |
| SEC-002 | EC2 scanning | Security groups, IMDSv2, EBS encryption, public IPs |
| SEC-003 | RDS scanning | Encryption, public access, backup retention, Multi-AZ |
| SEC-004 | IAM scanning | Password policy, MFA, unused credentials, key rotation |
| SEC-005 | Scan orchestration | Parallel scanning, progress tracking, cancellation |
| SEC-006 | Finding generation | Severity scoring, compliance mapping, remediation steps |

## Technical Specification

### Scanner Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Scan Orchestrator                            │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  ScanJob                                                        ││
│  │  - job_id, tenant_id, aws_account_id                            ││
│  │  - status: pending → running → completed/failed                 ││
│  │  - progress: 0-100%                                             ││
│  └─────────────────────────────────────────────────────────────────┘│
│                              │                                       │
│         ┌────────────────────┼────────────────────┐                 │
│         ▼                    ▼                    ▼                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │ S3 Scanner  │     │ EC2 Scanner │     │ RDS Scanner │  ...      │
│  │ - Buckets   │     │ - Instances │     │ - Instances │           │
│  │ - Policies  │     │ - Sec Groups│     │ - Clusters  │           │
│  │ - Logging   │     │ - Volumes   │     │ - Snapshots │           │
│  └─────────────┘     └─────────────┘     └─────────────┘           │
│         │                    │                    │                 │
│         └────────────────────┼────────────────────┘                 │
│                              ▼                                       │
│                    ┌─────────────────┐                              │
│                    │ Finding Store    │                              │
│                    │ (PostgreSQL)     │                              │
│                    └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Database Schema

```sql
-- Scan jobs table
CREATE TABLE scan_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    aws_account_id UUID NOT NULL REFERENCES aws_accounts(account_id),
    scan_type VARCHAR(20) NOT NULL,  -- 'security', 'cost', 'full'
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    progress INTEGER NOT NULL DEFAULT 0,  -- 0-100
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    stats JSONB,  -- {resources_scanned: 150, findings_count: 12, ...}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Security findings table
CREATE TABLE security_findings (
    finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES scan_jobs(job_id),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    aws_account_id VARCHAR(12) NOT NULL,

    -- Finding details
    resource_type VARCHAR(50) NOT NULL,  -- 's3_bucket', 'ec2_instance', etc.
    resource_id VARCHAR(255) NOT NULL,   -- ARN or ID
    resource_name VARCHAR(255),          -- Friendly name
    region VARCHAR(20) NOT NULL,

    -- Classification
    rule_id VARCHAR(50) NOT NULL,        -- 'S3_001', 'EC2_001', etc.
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(10) NOT NULL,       -- 'critical', 'high', 'medium', 'low'

    -- Compliance mapping
    compliance_frameworks JSONB,          -- ['HIPAA', 'SOC2', 'CIS']

    -- Remediation
    remediation_steps TEXT[],
    remediation_code TEXT,               -- Terraform/CloudFormation snippet
    documentation_url TEXT,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'open',  -- open, acknowledged, resolved, false_positive
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_findings_job ON security_findings(job_id);
CREATE INDEX idx_findings_tenant ON security_findings(tenant_id);
CREATE INDEX idx_findings_severity ON security_findings(severity);
CREATE INDEX idx_findings_rule ON security_findings(rule_id);
CREATE INDEX idx_findings_resource ON security_findings(resource_type, resource_id);
```

### Scanner Base Class

```python
# src/cloud_optimizer/scanners/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator
import boto3

class BaseScannerRule:
    """Individual security check."""
    rule_id: str
    title: str
    description: str
    severity: str
    compliance_frameworks: list[str]
    remediation_steps: list[str]

    @abstractmethod
    async def check(self, resource: dict, session: boto3.Session) -> Finding | None:
        """Check resource against rule. Returns Finding if violation found."""
        pass


class BaseScanner(ABC):
    """Base class for service scanners."""

    service_name: str
    rules: list[BaseScannerRule]

    def __init__(self, session: boto3.Session):
        self.session = session

    @abstractmethod
    async def list_resources(self, region: str) -> AsyncIterator[dict]:
        """Yield all resources to scan in region."""
        pass

    async def scan(self, regions: list[str]) -> AsyncIterator[Finding]:
        """Scan all resources across regions."""
        for region in regions:
            async for resource in self.list_resources(region):
                for rule in self.rules:
                    finding = await rule.check(resource, self.session)
                    if finding:
                        finding.resource_type = self.service_name
                        finding.region = region
                        yield finding
```

### S3 Scanner Implementation

```python
# src/cloud_optimizer/scanners/s3.py
class S3PublicAccessRule(BaseScannerRule):
    rule_id = "S3_001"
    title = "S3 Bucket Has Public Access"
    description = "S3 bucket allows public access which could expose sensitive data"
    severity = "critical"
    compliance_frameworks = ["HIPAA", "SOC2", "PCI-DSS", "CIS"]
    remediation_steps = [
        "Enable 'Block all public access' in bucket settings",
        "Review bucket policy for Principal: '*'",
        "Review bucket ACL for public grants",
    ]

    async def check(self, bucket: dict, session: boto3.Session) -> Finding | None:
        s3 = session.client("s3")
        bucket_name = bucket["Name"]

        # Check Block Public Access settings
        try:
            public_access = s3.get_public_access_block(Bucket=bucket_name)
            config = public_access["PublicAccessBlockConfiguration"]

            if not all([
                config.get("BlockPublicAcls", False),
                config.get("IgnorePublicAcls", False),
                config.get("BlockPublicPolicy", False),
                config.get("RestrictPublicBuckets", False),
            ]):
                return Finding(
                    resource_id=f"arn:aws:s3:::{bucket_name}",
                    resource_name=bucket_name,
                    rule_id=self.rule_id,
                    title=self.title,
                    description=f"Bucket '{bucket_name}' does not have all public access blocks enabled",
                    severity=self.severity,
                    compliance_frameworks=self.compliance_frameworks,
                    remediation_steps=self.remediation_steps,
                )
        except s3.exceptions.NoSuchPublicAccessBlockConfiguration:
            return Finding(
                resource_id=f"arn:aws:s3:::{bucket_name}",
                resource_name=bucket_name,
                rule_id=self.rule_id,
                title=self.title,
                description=f"Bucket '{bucket_name}' has no public access block configuration",
                severity=self.severity,
                compliance_frameworks=self.compliance_frameworks,
                remediation_steps=self.remediation_steps,
            )

        return None


class S3EncryptionRule(BaseScannerRule):
    rule_id = "S3_002"
    title = "S3 Bucket Not Encrypted"
    description = "S3 bucket does not have default encryption enabled"
    severity = "high"
    compliance_frameworks = ["HIPAA", "SOC2", "PCI-DSS"]
    remediation_steps = [
        "Enable default encryption (SSE-S3 or SSE-KMS)",
        "For PHI/PCI data, use SSE-KMS with CMK",
    ]

    async def check(self, bucket: dict, session: boto3.Session) -> Finding | None:
        s3 = session.client("s3")
        bucket_name = bucket["Name"]

        try:
            s3.get_bucket_encryption(Bucket=bucket_name)
            return None  # Encryption configured
        except s3.exceptions.ClientError as e:
            if "ServerSideEncryptionConfigurationNotFoundError" in str(e):
                return Finding(
                    resource_id=f"arn:aws:s3:::{bucket_name}",
                    resource_name=bucket_name,
                    rule_id=self.rule_id,
                    title=self.title,
                    description=f"Bucket '{bucket_name}' does not have default encryption",
                    severity=self.severity,
                    compliance_frameworks=self.compliance_frameworks,
                    remediation_steps=self.remediation_steps,
                )
            raise


class S3Scanner(BaseScanner):
    service_name = "s3_bucket"
    rules = [
        S3PublicAccessRule(),
        S3EncryptionRule(),
        S3VersioningRule(),
        S3LoggingRule(),
    ]

    async def list_resources(self, region: str) -> AsyncIterator[dict]:
        # S3 is global, only scan once
        if region != "us-east-1":
            return

        s3 = self.session.client("s3")
        response = s3.list_buckets()

        for bucket in response.get("Buckets", []):
            yield bucket
```

### Scan Orchestrator

```python
# src/cloud_optimizer/services/scan_orchestrator.py
class ScanOrchestrator:
    SCANNERS = [
        S3Scanner,
        EC2Scanner,
        RDSScanner,
        IAMScanner,
    ]

    REGIONS = [
        "us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"
    ]

    def __init__(
        self,
        db: AsyncSession,
        aws_connection_service: AWSConnectionService,
        trial_service: TrialService,
    ):
        self.db = db
        self.aws_connection_service = aws_connection_service
        self.trial_service = trial_service

    async def start_scan(
        self,
        tenant_id: UUID,
        aws_account_id: UUID,
        scan_type: str = "security",
    ) -> ScanJob:
        """Start a new security scan."""
        # Check trial limits
        check = await self.trial_service.check_limit(tenant_id, "scans")
        if not check.allowed:
            raise TrialLimitExceededException("Scan limit reached")

        # Get AWS session
        session = await self.aws_connection_service.get_session(aws_account_id)

        # Create scan job
        job = ScanJob(
            tenant_id=tenant_id,
            aws_account_id=aws_account_id,
            scan_type=scan_type,
            status="pending",
        )
        self.db.add(job)
        await self.db.commit()

        # Start background scan
        asyncio.create_task(self._run_scan(job.job_id, session))

        # Record usage
        await self.trial_service.record_usage(tenant_id, "scans")

        return job

    async def _run_scan(self, job_id: UUID, session: boto3.Session):
        """Execute scan in background."""
        job = await self._get_job(job_id)

        try:
            job.status = "running"
            job.started_at = datetime.utcnow()
            await self.db.commit()

            total_findings = 0
            total_resources = 0
            scanner_count = len(self.SCANNERS)

            for idx, ScannerClass in enumerate(self.SCANNERS):
                scanner = ScannerClass(session)

                async for finding in scanner.scan(self.REGIONS):
                    finding.job_id = job_id
                    finding.tenant_id = job.tenant_id
                    finding.aws_account_id = job.aws_account_id
                    self.db.add(finding)
                    total_findings += 1
                    total_resources += 1

                # Update progress
                job.progress = int((idx + 1) / scanner_count * 100)
                await self.db.commit()

            # Complete job
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.stats = {
                "resources_scanned": total_resources,
                "findings_count": total_findings,
            }
            await self.db.commit()

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await self.db.commit()
            raise

    async def get_scan_status(self, job_id: UUID) -> ScanJob:
        """Get current scan status."""
        return await self._get_job(job_id)

    async def cancel_scan(self, job_id: UUID):
        """Cancel a running scan."""
        job = await self._get_job(job_id)
        if job.status == "running":
            job.status = "cancelled"
            job.completed_at = datetime.utcnow()
            await self.db.commit()
```

## Security Rules Coverage

### S3 Rules
| Rule ID | Title | Severity |
|---------|-------|----------|
| S3_001 | Public Access Enabled | Critical |
| S3_002 | No Default Encryption | High |
| S3_003 | Versioning Disabled | Medium |
| S3_004 | Access Logging Disabled | Medium |

### EC2 Rules
| Rule ID | Title | Severity |
|---------|-------|----------|
| EC2_001 | Security Group Allows 0.0.0.0/0 SSH | Critical |
| EC2_002 | Security Group Allows 0.0.0.0/0 RDP | Critical |
| EC2_003 | Instance Not Using IMDSv2 | High |
| EC2_004 | EBS Volume Not Encrypted | High |
| EC2_005 | Instance Has Public IP | Medium |

### RDS Rules
| Rule ID | Title | Severity |
|---------|-------|----------|
| RDS_001 | Instance Publicly Accessible | Critical |
| RDS_002 | Storage Not Encrypted | High |
| RDS_003 | Backup Retention < 7 Days | Medium |
| RDS_004 | Multi-AZ Not Enabled | Medium |

### IAM Rules
| Rule ID | Title | Severity |
|---------|-------|----------|
| IAM_001 | Root Account Has Access Keys | Critical |
| IAM_002 | MFA Not Enabled for Users | High |
| IAM_003 | Access Keys Not Rotated (>90 days) | High |
| IAM_004 | Password Policy Too Weak | Medium |
| IAM_005 | Unused Credentials (>90 days) | Medium |

## API Endpoints

```
POST /api/v1/scans                   # Start new scan
GET  /api/v1/scans                   # List scans
GET  /api/v1/scans/:id               # Get scan status
POST /api/v1/scans/:id/cancel        # Cancel running scan
GET  /api/v1/scans/:id/findings      # Get findings for scan
```

## Files to Create

```
src/cloud_optimizer/scanners/
├── __init__.py
├── base.py                      # Base scanner classes
├── s3.py                        # S3 scanner
├── ec2.py                       # EC2 scanner
├── rds.py                       # RDS scanner
├── iam.py                       # IAM scanner
└── rules/
    ├── __init__.py
    ├── s3_rules.py
    ├── ec2_rules.py
    ├── rds_rules.py
    └── iam_rules.py

src/cloud_optimizer/services/
└── scan_orchestrator.py         # Scan orchestration

src/cloud_optimizer/models/
├── scan_job.py                  # ScanJob model
└── finding.py                   # Finding model

src/cloud_optimizer/api/routers/
└── scans.py                     # Scan API endpoints

alembic/versions/
└── xxx_create_scan_tables.py    # Migration

tests/scanners/
├── test_s3_scanner.py
├── test_ec2_scanner.py
├── test_rds_scanner.py
├── test_iam_scanner.py
└── test_orchestrator.py
```

## Testing Requirements

### Unit Tests
- [ ] `test_s3_rules.py` - Each S3 rule individually
- [ ] `test_ec2_rules.py` - Each EC2 rule individually
- [ ] `test_rds_rules.py` - Each RDS rule individually
- [ ] `test_iam_rules.py` - Each IAM rule individually
- [ ] `test_finding_generation.py` - Finding creation

### Integration Tests
- [ ] `test_s3_scanner_integration.py` - Full S3 scan (LocalStack)
- [ ] `test_full_scan.py` - Complete scan orchestration

### LocalStack Setup

```yaml
# docker-compose.test.yml additions
localstack:
  image: localstack/localstack:latest
  environment:
    - SERVICES=s3,ec2,rds,iam,sts
    - AWS_DEFAULT_REGION=us-east-1
  ports:
    - "4566:4566"
```

## Acceptance Criteria Checklist

- [ ] S3 scanner detects public buckets, missing encryption
- [ ] EC2 scanner detects open security groups, public IPs
- [ ] RDS scanner detects public access, missing encryption
- [ ] IAM scanner detects weak password policy, unused keys
- [ ] Scan completes in <5 minutes for account with 100 resources
- [ ] Progress tracking shows 0-100% accurately
- [ ] Findings include severity, compliance mapping, remediation
- [ ] Scan cancellation stops processing
- [ ] Trial limit enforced for scans
- [ ] All tests pass with LocalStack
- [ ] 80%+ test coverage

## Dependencies

- 7.1 AWS Account Connection (needs AWS session)

## Blocked By

- 7.1 AWS Account Connection

## Blocks

- 7.4 Findings Management (generates findings)
- 8.3 Security Analysis (IB processes findings)

## Estimated Effort

2 weeks

## Labels

`scanner`, `security`, `aws`, `mvp`, `phase-2`, `P0`

## Implementation Notes (2025-12-03)

- `SecurityScanEngine` orchestrates per-account AWS scans, enforces trial limits, and populates `ScanJob` records with progress and findings counts.
- `/api/v1/security/scans` and `/api/v1/security/scans/{job_id}` provide APIs for starting scans and checking job status; responses use the new `SecurityScanJobResponse` schema.
- `S3SecurityScanner` augments the existing scanner suite with public access, versioning, and logging checks, and `rule_metadata` maps scanner findings to compliance frameworks (HIPAA, SOC2, CIS).
