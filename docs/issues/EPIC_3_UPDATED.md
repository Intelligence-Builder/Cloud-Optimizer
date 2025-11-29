# Epic 3: Cloud Optimizer v2 Clean Rebuild

## Overview

Create a clean, enterprise-grade Cloud Optimizer v2 application that consumes Intelligence-Builder platform services via SDK. Target: < 10K LOC.

**Priority**: High
**Dependencies**: Epic 2 (Security Domain) complete

## Objectives

1. Set up new clean repository with proper CI/CD and quality gates
2. Build core application structure with FastAPI and IB SDK integration
3. Implement Security domain features with AWS integration

## Repository Structure

```
cloud-optimizer-v2/
├── .github/workflows/
├── src/cloud_optimizer/
│   ├── main.py           # FastAPI app
│   ├── config.py         # Configuration
│   ├── ib_client.py      # IB SDK client
│   ├── services/         # Business logic
│   ├── api/              # API layer
│   └── integrations/aws/ # AWS integration
├── tests/
├── docker/
└── docs/
```

## Deliverables

### 3.1 Repository Foundation
- GitHub repository setup
- Project structure with clean layout
- CI/CD pipeline with GitHub Actions
- Pre-commit hooks (black, isort, flake8, mypy)
- Docker development environment

### 3.2 Core Application Structure
- FastAPI application with proper lifecycle
- Configuration management
- IB SDK client connection
- Health check endpoints
- Logging and monitoring

### 3.3 Security Domain Integration
- Security service with CO-specific logic
- AWS security scanning (security groups, IAM, encryption)
- Security API endpoints
- Security dashboard endpoints

## Acceptance Criteria

- [ ] Repository clean and minimal (< 10K LOC target, < 5K ideal)
- [ ] Application starts and connects to IB platform
- [ ] Security scanning works with AWS credentials
- [ ] Findings pushed to IB successfully
- [ ] Dashboard displays security metrics
- [ ] Code coverage > 80%
- [ ] All quality gates passing
- [ ] No file > 500 lines

## Sub-Tasks

- #12 - 3.1 Repository Foundation
- #13 - 3.2 Core Application Structure
- #14 - 3.3 Security Domain Integration

---

## Integration Test Specification

### Test Environment

| Component | Configuration | Notes |
|-----------|---------------|-------|
| IB Platform | localhost:8000 or mock | SDK integration point |
| AWS | LocalStack localhost:4566 | Mocked AWS services |
| CO v2 App | localhost:8080 | Application under test |
| PostgreSQL | localhost:5432 | For IB platform |

```yaml
# tests/integration/conftest.py
CO_APP_URL: http://localhost:8080
IB_PLATFORM_URL: http://localhost:8000
AWS_ENDPOINT_URL: http://localhost:4566  # LocalStack
AWS_ACCESS_KEY_ID: test
AWS_SECRET_ACCESS_KEY: test
AWS_REGION: us-east-1
```

### End-to-End Test Scenarios

| ID | Scenario | Flow | Input | Expected Output |
|----|----------|------|-------|-----------------|
| E3-INT-01 | App Startup | Start app → Connect IB | Config | /health returns 200 |
| E3-INT-02 | IB SDK Connection | App → IB Platform | Credentials | /health/ready confirms IB |
| E3-INT-03 | AWS SG Scan | Scan → Transform → IB | AWS account | Findings in IB |
| E3-INT-04 | AWS IAM Scan | Scan → Transform → IB | AWS account | IAM findings in IB |
| E3-INT-05 | Full Security Scan | All scanners → IB | AWS account | Complete findings |
| E3-INT-06 | Dashboard Metrics | Scan → Query IB → Dashboard | Account ID | Aggregated metrics |

### LocalStack AWS Setup

```python
# tests/integration/conftest.py
import boto3
import pytest

@pytest.fixture(scope="session")
def localstack_aws():
    """Set up LocalStack with test data."""
    endpoint = "http://localhost:4566"

    # Create test security groups
    ec2 = boto3.client("ec2", endpoint_url=endpoint, region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    # Risky security group (open SSH)
    risky_sg = ec2.create_security_group(
        GroupName="risky-sg",
        Description="Test risky SG",
        VpcId=vpc["VpcId"]
    )
    ec2.authorize_security_group_ingress(
        GroupId=risky_sg["GroupId"],
        IpPermissions=[{
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 22,
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
        }]
    )

    # Safe security group
    safe_sg = ec2.create_security_group(
        GroupName="safe-sg",
        Description="Test safe SG",
        VpcId=vpc["VpcId"]
    )
    ec2.authorize_security_group_ingress(
        GroupId=safe_sg["GroupId"],
        IpPermissions=[{
            "IpProtocol": "tcp",
            "FromPort": 443,
            "ToPort": 443,
            "IpRanges": [{"CidrIp": "10.0.0.0/8"}]
        }]
    )

    # Create IAM resources
    iam = boto3.client("iam", endpoint_url=endpoint, region_name="us-east-1")
    iam.create_role(
        RoleName="AdminRole",
        AssumeRolePolicyDocument="{}",
    )
    iam.attach_role_policy(
        RoleName="AdminRole",
        PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
    )

    yield {
        "vpc_id": vpc["VpcId"],
        "risky_sg_id": risky_sg["GroupId"],
        "safe_sg_id": safe_sg["GroupId"],
    }

    # Cleanup
    ec2.delete_security_group(GroupId=risky_sg["GroupId"])
    ec2.delete_security_group(GroupId=safe_sg["GroupId"])
    ec2.delete_vpc(VpcId=vpc["VpcId"])
```

### Integration Test Implementation

```python
# tests/integration/test_epic3_co_v2.py
"""Epic 3 Integration Tests - Cloud Optimizer v2"""

import pytest
from httpx import AsyncClient


class TestApplicationStartup:
    """E3-INT-01: Application startup and health."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, co_client: AsyncClient):
        """Application health endpoint returns 200."""
        response = await co_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_readiness_with_ib(self, co_client: AsyncClient):
        """Readiness confirms IB platform connection."""
        response = await co_client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "ib_platform" in data


class TestAWSSecurityGroupScan:
    """E3-INT-03: Security group scanning flow."""

    @pytest.mark.asyncio
    async def test_scan_detects_open_ssh(
        self, co_client: AsyncClient, localstack_aws, ib_client
    ):
        """Scan detects security group with open SSH."""
        # Trigger scan
        response = await co_client.post(
            "/api/v1/security/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["security_groups"],
                "region": "us-east-1"
            }
        )

        assert response.status_code == 200
        result = response.json()
        assert result["findings_by_type"]["security_groups"] >= 1

        # Verify finding pushed to IB
        findings = await ib_client.entities.search(
            domain="security",
            entity_type="security_finding",
            filters={"properties.resource": {"$contains": localstack_aws["risky_sg_id"]}}
        )
        assert len(findings) >= 1
        assert findings[0].properties["severity"] == "high"

    @pytest.mark.asyncio
    async def test_scan_ignores_safe_sg(
        self, co_client: AsyncClient, localstack_aws
    ):
        """Scan does not flag safe security groups."""
        response = await co_client.post(
            "/api/v1/security/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["security_groups"],
                "region": "us-east-1"
            }
        )

        # Safe SG should not appear in findings
        entities = response.json().get("entities", [])
        safe_sg_findings = [
            e for e in entities
            if localstack_aws["safe_sg_id"] in str(e.get("properties", {}).get("resource", ""))
        ]
        assert len(safe_sg_findings) == 0


class TestAWSIAMScan:
    """E3-INT-04: IAM scanning flow."""

    @pytest.mark.asyncio
    async def test_scan_detects_admin_role(
        self, co_client: AsyncClient, localstack_aws, ib_client
    ):
        """Scan detects IAM role with admin access."""
        response = await co_client.post(
            "/api/v1/security/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["iam"],
                "region": "us-east-1"
            }
        )

        assert response.status_code == 200
        assert response.json()["findings_by_type"]["iam"] >= 1


class TestFullSecurityScan:
    """E3-INT-05: Complete security scan flow."""

    @pytest.mark.asyncio
    async def test_full_scan_all_types(
        self, co_client: AsyncClient, localstack_aws, ib_client
    ):
        """Full scan runs all scanner types."""
        response = await co_client.post(
            "/api/v1/security/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "region": "us-east-1"
                # No scan_types = all types
            }
        )

        assert response.status_code == 200
        result = response.json()

        # All scan types should be present
        assert "security_groups" in result["findings_by_type"]
        assert "iam" in result["findings_by_type"]
        assert "encryption" in result["findings_by_type"]


class TestDashboardMetrics:
    """E3-INT-06: Dashboard metrics endpoint."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_aggregated_metrics(
        self, co_client: AsyncClient, seeded_findings
    ):
        """Dashboard endpoint returns aggregated security metrics."""
        response = await co_client.get(
            "/api/v1/dashboard/security",
            params={"aws_account_id": "123456789012"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "total_findings" in data
        assert "findings_by_severity" in data
        assert "findings_by_type" in data
        assert "critical" in data["findings_by_severity"]
```

### Performance Benchmarks

| Operation | Requirement | Test Method | Notes |
|-----------|-------------|-------------|-------|
| App startup | < 5s | Timing | Including IB connection |
| SG scan (10 SGs) | < 2s | Response time | LocalStack |
| IAM scan (10 roles) | < 2s | Response time | LocalStack |
| Full scan | < 10s | Response time | All types |
| Dashboard query | < 500ms | Response time | Aggregation |

### LOC Verification Test

```python
# tests/integration/test_epic3_quality.py
"""Quality gate tests for CO v2."""

import subprocess
from pathlib import Path


class TestLOCBudget:
    """Verify LOC stays within budget."""

    def test_total_loc_under_10k(self):
        """Total LOC < 10K."""
        src_path = Path("src/cloud_optimizer")
        result = subprocess.run(
            ["wc", "-l"] + list(src_path.rglob("*.py")),
            capture_output=True, text=True
        )
        total_line = result.stdout.strip().split("\n")[-1]
        total_loc = int(total_line.split()[0])
        assert total_loc < 10000, f"LOC {total_loc} exceeds 10K limit"

    def test_no_file_over_500_lines(self):
        """No single file > 500 lines."""
        src_path = Path("src/cloud_optimizer")
        for py_file in src_path.rglob("*.py"):
            lines = len(py_file.read_text().splitlines())
            assert lines <= 500, f"{py_file} has {lines} lines (max 500)"
```

### CI Integration

```yaml
# .github/workflows/integration-tests.yml
epic3-integration:
  needs: [epic2-integration]
  runs-on: ubuntu-latest
  services:
    localstack:
      image: localstack/localstack:latest
      ports:
        - 4566:4566
      env:
        SERVICES: ec2,iam,s3
    ib-platform:
      image: intelligence-builder:latest
      ports:
        - 8000:8000

  steps:
    - uses: actions/checkout@v4
    - run: pip install -r requirements-test.txt
    - run: |
        # Start CO v2 app
        uvicorn cloud_optimizer.main:app --port 8080 &
        sleep 5
    - run: pytest tests/integration/test_epic3_*.py -v --tb=short
```
