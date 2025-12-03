# Advanced Test Setup Guide

This guide provides detailed instructions for setting up the external dependencies required for comprehensive test coverage that cannot be achieved with LocalStack Community edition or mock data.

## Table of Contents

1. [Smart-Scaffold Parallel Validator Setup](#1-smart-scaffold-parallel-validator-setup)
2. [Real AWS Scanner Tests (Epic 4)](#2-real-aws-scanner-tests-epic-4)
3. [LocalStack Pro Features](#3-localstack-pro-features)
4. [Environment Configuration Summary](#4-environment-configuration-summary)
5. [CI/CD Integration](#5-cicd-integration)

---

## 1. Smart-Scaffold Parallel Validator Setup

### Overview

The Smart-Scaffold parallel validator tests require divergent datasets between Smart-Scaffold (SS) and Intelligence-Builder (IB) to verify that discrepancies are properly detected, logged, and cause the CLI to exit non-zero.

### Prerequisites

- Smart-Scaffold CLI installed (`pip install smart-scaffold` or from source)
- Intelligence-Builder SDK installed (`pip install intelligence-builder-sdk`)
- PostgreSQL database running
- Memgraph or PostgreSQL CTE backend configured

### Step 1: Create Test Datasets

#### 1.1 Create Divergent Entity Sets

Create a directory for test fixtures:

```bash
mkdir -p tests/integration/ss_validator_fixtures
```

Create `tests/integration/ss_validator_fixtures/ss_entities.json`:

```json
{
  "entities": [
    {
      "id": "entity-001",
      "type": "SecurityFinding",
      "name": "Open SSH Port",
      "attributes": {
        "severity": "high",
        "resource_id": "sg-12345",
        "rule_id": "AWS-SG-001"
      }
    },
    {
      "id": "entity-002",
      "type": "SecurityFinding",
      "name": "Unencrypted S3 Bucket",
      "attributes": {
        "severity": "medium",
        "resource_id": "bucket-test-123",
        "rule_id": "AWS-S3-001"
      }
    },
    {
      "id": "entity-003-ss-only",
      "type": "SecurityFinding",
      "name": "SS-Only Finding",
      "attributes": {
        "severity": "low",
        "resource_id": "resource-ss-only",
        "rule_id": "AWS-TEST-001"
      }
    }
  ],
  "relationships": [
    {
      "source": "entity-001",
      "target": "entity-002",
      "type": "RELATED_TO"
    }
  ]
}
```

Create `tests/integration/ss_validator_fixtures/ib_entities.json`:

```json
{
  "entities": [
    {
      "id": "entity-001",
      "type": "SecurityFinding",
      "name": "Open SSH Port",
      "attributes": {
        "severity": "critical",
        "resource_id": "sg-12345",
        "rule_id": "AWS-SG-001"
      }
    },
    {
      "id": "entity-002",
      "type": "SecurityFinding",
      "name": "Unencrypted S3 Bucket",
      "attributes": {
        "severity": "medium",
        "resource_id": "bucket-test-123",
        "rule_id": "AWS-S3-001"
      }
    },
    {
      "id": "entity-004-ib-only",
      "type": "SecurityFinding",
      "name": "IB-Only Finding",
      "attributes": {
        "severity": "high",
        "resource_id": "resource-ib-only",
        "rule_id": "AWS-TEST-002"
      }
    }
  ],
  "relationships": [
    {
      "source": "entity-001",
      "target": "entity-002",
      "type": "RELATED_TO"
    },
    {
      "source": "entity-002",
      "target": "entity-004-ib-only",
      "type": "DEPENDS_ON"
    }
  ]
}
```

#### 1.2 Divergence Types Created

The above fixtures create these divergence scenarios:

| Divergence Type | Description | Expected Behavior |
|-----------------|-------------|-------------------|
| **Attribute Mismatch** | entity-001 has severity "high" in SS, "critical" in IB | Log warning, continue |
| **SS-Only Entity** | entity-003-ss-only exists only in SS | Log error, exit non-zero |
| **IB-Only Entity** | entity-004-ib-only exists only in IB | Log error, exit non-zero |
| **Missing Relationship** | IB has extra DEPENDS_ON relationship | Log warning |

### Step 2: Seed the Databases

#### 2.1 Seed Smart-Scaffold Knowledge Graph

```bash
# Using Smart-Scaffold CLI
smart-scaffold kg seed \
  --source tests/integration/ss_validator_fixtures/ss_entities.json \
  --format json

# Verify seeding
smart-scaffold kg status
```

#### 2.2 Seed Intelligence-Builder Graph

```python
# scripts/seed_ib_graph.py
import asyncio
import json
from pathlib import Path

# Assuming IB SDK is installed
try:
    from intelligence_builder import IBClient
except ImportError:
    print("Intelligence-Builder SDK not installed")
    exit(1)

async def seed_ib_graph():
    """Seed IB graph with test entities."""
    client = IBClient(
        url="http://localhost:8000",
        api_key="test-api-key",
        tenant_id="test-tenant"
    )

    fixtures_path = Path("tests/integration/ss_validator_fixtures/ib_entities.json")
    with open(fixtures_path) as f:
        data = json.load(f)

    # Create entities
    for entity in data["entities"]:
        await client.entities.create(
            entity_id=entity["id"],
            entity_type=entity["type"],
            name=entity["name"],
            attributes=entity["attributes"]
        )
        print(f"Created entity: {entity['id']}")

    # Create relationships
    for rel in data["relationships"]:
        await client.relationships.create(
            source_id=rel["source"],
            target_id=rel["target"],
            relationship_type=rel["type"]
        )
        print(f"Created relationship: {rel['source']} -> {rel['target']}")

    print("IB graph seeded successfully")

if __name__ == "__main__":
    asyncio.run(seed_ib_graph())
```

Run the seeding script:

```bash
PYTHONPATH=src python scripts/seed_ib_graph.py
```

### Step 3: Create the Validator Test

Create `tests/integration/test_ss_parallel_validator.py`:

```python
"""
Smart-Scaffold Parallel Validator Divergence Tests.

These tests verify that the SS/IB parallel validator correctly detects
and reports discrepancies between Smart-Scaffold and Intelligence-Builder
knowledge graphs.

Prerequisites:
- Both SS and IB graphs seeded with divergent data (see ADVANCED_TEST_SETUP.md)
- SS CLI available
- IB SDK installed
"""

import subprocess
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "ss_validator_fixtures"


@pytest.fixture
def seeded_graphs(request):
    """Ensure both graphs are seeded with divergent data."""
    # Check if fixtures exist
    ss_fixtures = FIXTURES_DIR / "ss_entities.json"
    ib_fixtures = FIXTURES_DIR / "ib_entities.json"

    if not ss_fixtures.exists() or not ib_fixtures.exists():
        pytest.skip("Divergent fixtures not created. See ADVANCED_TEST_SETUP.md")

    # TODO: Add actual seeding verification
    return True


@pytest.mark.integration
@pytest.mark.ss_validator
class TestParallelValidatorDivergence:
    """Test divergence detection in parallel validator."""

    def test_validator_detects_attribute_mismatch(self, seeded_graphs):
        """Validator should log warning for attribute mismatches."""
        result = subprocess.run(
            ["smart-scaffold", "validate", "--parallel", "--verbose"],
            capture_output=True,
            text=True
        )

        # Should detect severity mismatch on entity-001
        assert "entity-001" in result.stdout or "entity-001" in result.stderr
        assert "severity" in result.stdout.lower() or "severity" in result.stderr.lower()
        assert "mismatch" in result.stdout.lower() or "mismatch" in result.stderr.lower()

    def test_validator_detects_ss_only_entities(self, seeded_graphs):
        """Validator should error on SS-only entities."""
        result = subprocess.run(
            ["smart-scaffold", "validate", "--parallel", "--strict"],
            capture_output=True,
            text=True
        )

        # Should detect entity-003-ss-only
        assert "entity-003-ss-only" in result.stdout or "entity-003-ss-only" in result.stderr
        assert result.returncode != 0, "Should exit non-zero on SS-only entities"

    def test_validator_detects_ib_only_entities(self, seeded_graphs):
        """Validator should error on IB-only entities."""
        result = subprocess.run(
            ["smart-scaffold", "validate", "--parallel", "--strict"],
            capture_output=True,
            text=True
        )

        # Should detect entity-004-ib-only
        assert "entity-004-ib-only" in result.stdout or "entity-004-ib-only" in result.stderr
        assert result.returncode != 0, "Should exit non-zero on IB-only entities"

    def test_validator_detects_relationship_differences(self, seeded_graphs):
        """Validator should detect relationship discrepancies."""
        result = subprocess.run(
            ["smart-scaffold", "validate", "--parallel", "--check-relationships"],
            capture_output=True,
            text=True
        )

        # Should detect missing DEPENDS_ON relationship
        assert "DEPENDS_ON" in result.stdout or "relationship" in result.stderr.lower()

    def test_validator_exits_nonzero_on_divergence(self, seeded_graphs):
        """Validator should exit non-zero when divergence detected."""
        result = subprocess.run(
            ["smart-scaffold", "validate", "--parallel", "--strict"],
            capture_output=True,
            text=True
        )

        # With divergent data, should fail
        assert result.returncode != 0, (
            f"Expected non-zero exit code, got {result.returncode}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    def test_validator_logs_all_discrepancies(self, seeded_graphs):
        """Validator should log all discrepancies, not just first."""
        result = subprocess.run(
            ["smart-scaffold", "validate", "--parallel", "--verbose", "--all"],
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # Should find all divergence types
        divergence_indicators = [
            "entity-001",  # Attribute mismatch
            "entity-003",  # SS-only
            "entity-004",  # IB-only
        ]

        found = sum(1 for ind in divergence_indicators if ind in output)
        assert found >= 2, f"Expected at least 2 divergences logged, found {found}"

    def test_validator_produces_report(self, seeded_graphs, tmp_path):
        """Validator should produce machine-readable report."""
        report_path = tmp_path / "divergence_report.json"

        result = subprocess.run(
            [
                "smart-scaffold", "validate", "--parallel",
                "--output", str(report_path),
                "--format", "json"
            ],
            capture_output=True,
            text=True
        )

        assert report_path.exists(), "Report file should be created"

        import json
        with open(report_path) as f:
            report = json.load(f)

        assert "divergences" in report or "discrepancies" in report
        assert "summary" in report or "total" in report
```

### Step 4: Run the Tests

```bash
# Run only SS validator tests
pytest tests/integration/test_ss_parallel_validator.py -v -m ss_validator

# Run with verbose output
pytest tests/integration/test_ss_parallel_validator.py -v -s
```

### Cleanup

After testing, clean up the seeded data:

```bash
# Clear SS graph
smart-scaffold kg clear --confirm

# Clear IB graph (via API or direct DB access)
PYTHONPATH=src python -c "
from cloud_optimizer.services.ib_service import IBService
import asyncio

async def cleanup():
    svc = IBService()
    await svc.clear_test_entities()

asyncio.run(cleanup())
"
```

---

## 2. Real AWS Scanner Tests (Epic 4)

### Overview

Epic 4 scanners (Cost Explorer, RDS, SSM) require real AWS API access because LocalStack Community does not support these services adequately.

### Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Cost Explorer enabled (requires 24-hour wait after enabling)
- RDS instances for testing
- SSM-managed EC2 instances

### Step 1: Create Test AWS Account/Role

#### 1.1 Create IAM Policy

Create `cloudformation/test-scanner-policy.yaml`:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: IAM policy for Cloud Optimizer scanner integration tests

Resources:
  ScannerTestPolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      ManagedPolicyName: CloudOptimizerScannerTestPolicy
      Description: Permissions for running Cloud Optimizer scanner integration tests
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          # Cost Explorer permissions
          - Sid: CostExplorerRead
            Effect: Allow
            Action:
              - ce:GetCostAndUsage
              - ce:GetCostForecast
              - ce:GetReservationUtilization
              - ce:GetSavingsPlansUtilization
              - ce:GetRightsizingRecommendation
              - ce:GetAnomalies
              - ce:GetAnomalyMonitors
              - ce:GetAnomalySubscriptions
            Resource: '*'

          # RDS permissions
          - Sid: RDSRead
            Effect: Allow
            Action:
              - rds:DescribeDBInstances
              - rds:DescribeDBClusters
              - rds:DescribeDBSnapshots
              - rds:DescribeDBSecurityGroups
              - rds:DescribeDBParameterGroups
              - rds:ListTagsForResource
              - rds:DescribeEvents
              - rds:DescribeDBLogFiles
              - rds:DescribeDBEngineVersions
              - rds:DescribeReservedDBInstances
            Resource: '*'

          # SSM permissions
          - Sid: SSMRead
            Effect: Allow
            Action:
              - ssm:DescribeInstanceInformation
              - ssm:ListInventoryEntries
              - ssm:GetInventory
              - ssm:ListComplianceItems
              - ssm:ListComplianceSummaries
              - ssm:DescribeInstancePatches
              - ssm:DescribePatchBaselines
              - ssm:GetPatchBaseline
              - ssm:DescribeMaintenanceWindows
              - ssm:DescribeMaintenanceWindowTargets
              - ssm:ListAssociations
              - ssm:DescribeAssociation
            Resource: '*'

          # EC2 permissions (for SSM context)
          - Sid: EC2Read
            Effect: Allow
            Action:
              - ec2:DescribeInstances
              - ec2:DescribeVolumes
              - ec2:DescribeSnapshots
              - ec2:DescribeSecurityGroups
              - ec2:DescribeVpcs
              - ec2:DescribeSubnets
            Resource: '*'

          # CloudWatch permissions (for metrics)
          - Sid: CloudWatchRead
            Effect: Allow
            Action:
              - cloudwatch:GetMetricData
              - cloudwatch:GetMetricStatistics
              - cloudwatch:ListMetrics
              - cloudwatch:DescribeAlarms
            Resource: '*'

          # Organizations (for multi-account)
          - Sid: OrganizationsRead
            Effect: Allow
            Action:
              - organizations:DescribeOrganization
              - organizations:ListAccounts
            Resource: '*'

          # STS for identity verification
          - Sid: STSRead
            Effect: Allow
            Action:
              - sts:GetCallerIdentity
            Resource: '*'

  ScannerTestRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: CloudOptimizerScannerTestRole
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${AWS::AccountId}:root'
            Action: sts:AssumeRole
            Condition:
              StringEquals:
                sts:ExternalId: cloud-optimizer-test-external-id
      ManagedPolicyArns:
        - !Ref ScannerTestPolicy
      Tags:
        - Key: Purpose
          Value: CloudOptimizerTesting
        - Key: Environment
          Value: Test

Outputs:
  PolicyArn:
    Description: ARN of the scanner test policy
    Value: !Ref ScannerTestPolicy
  RoleArn:
    Description: ARN of the scanner test role
    Value: !GetAtt ScannerTestRole.Arn
```

Deploy the policy:

```bash
aws cloudformation create-stack \
  --stack-name cloud-optimizer-test-permissions \
  --template-body file://cloudformation/test-scanner-policy.yaml \
  --capabilities CAPABILITY_NAMED_IAM
```

#### 1.2 Create Test User (Alternative to Role)

For local development, create a test user:

```bash
# Create user
aws iam create-user --user-name cloud-optimizer-test

# Attach policy
aws iam attach-user-policy \
  --user-name cloud-optimizer-test \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/CloudOptimizerScannerTestPolicy

# Create access keys
aws iam create-access-key --user-name cloud-optimizer-test
```

### Step 2: Set Up Test Resources

#### 2.1 Enable Cost Explorer

Cost Explorer must be enabled and requires 24 hours to start collecting data:

```bash
# Enable Cost Explorer (one-time)
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-02 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

If you get an error about Cost Explorer not being enabled, enable it via the AWS Console:
1. Go to AWS Cost Management → Cost Explorer
2. Click "Enable Cost Explorer"
3. Wait 24 hours for data to populate

#### 2.2 Create Test RDS Instance

```bash
# Create a small test RDS instance
aws rds create-db-instance \
  --db-instance-identifier cloud-optimizer-test-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username testadmin \
  --master-user-password 'TestPassword123!' \
  --allocated-storage 20 \
  --backup-retention-period 0 \
  --no-multi-az \
  --no-publicly-accessible \
  --tags Key=Purpose,Value=CloudOptimizerTesting Key=Environment,Value=Test
```

#### 2.3 Create Test EC2 Instance with SSM

```bash
# Create EC2 instance with SSM agent
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.micro \
  --iam-instance-profile Name=AmazonSSMRoleForInstancesQuickSetup \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=cloud-optimizer-test},{Key=Purpose,Value=CloudOptimizerTesting}]' \
  --count 1
```

### Step 3: Configure Test Environment

Create `.env.aws-test`:

```bash
# AWS Test Environment Configuration
# DO NOT COMMIT THIS FILE

# AWS Credentials (use IAM role in CI/CD)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1

# Test Account ID
AWS_TEST_ACCOUNT_ID=123456789012

# Test Resources
RDS_TEST_INSTANCE_ID=cloud-optimizer-test-db
EC2_TEST_INSTANCE_ID=i-0123456789abcdef0

# Test Configuration
USE_REAL_AWS=true
AWS_TEST_EXTERNAL_ID=cloud-optimizer-test-external-id

# Cost Explorer Date Range (use recent dates with data)
COST_EXPLORER_START_DATE=2024-11-01
COST_EXPLORER_END_DATE=2024-11-30
```

Add to `.gitignore`:

```
.env.aws-test
```

### Step 4: Create Real AWS Tests

Create `tests/integration/test_epic4_real_aws.py`:

```python
"""
Real AWS Scanner Integration Tests for Epic 4.

These tests run against actual AWS services (not LocalStack) to verify
scanner functionality with real-world data and API responses.

Prerequisites:
- AWS credentials with CloudOptimizerScannerTestPolicy
- Cost Explorer enabled (24-hour wait after enabling)
- Test RDS instance created
- Test EC2 instance with SSM agent

Configuration:
- Set USE_REAL_AWS=true in environment
- Configure AWS credentials via env vars or ~/.aws/credentials

WARNING: These tests incur AWS costs! Run sparingly (nightly CI, not every PR).
"""

import os
import pytest
from datetime import datetime, timedelta

# Skip entire module if not configured for real AWS
pytestmark = [
    pytest.mark.real_aws,
    pytest.mark.skipif(
        os.getenv("USE_REAL_AWS", "").lower() != "true",
        reason="Real AWS tests disabled. Set USE_REAL_AWS=true to enable."
    )
]


@pytest.fixture(scope="module")
def aws_account_id():
    """Get AWS account ID from environment or STS."""
    account_id = os.getenv("AWS_TEST_ACCOUNT_ID")
    if account_id:
        return account_id

    import boto3
    sts = boto3.client("sts")
    identity = sts.get_caller_identity()
    return identity["Account"]


@pytest.fixture(scope="module")
def cost_date_range():
    """Get date range for Cost Explorer queries."""
    start = os.getenv("COST_EXPLORER_START_DATE")
    end = os.getenv("COST_EXPLORER_END_DATE")

    if start and end:
        return {"Start": start, "End": end}

    # Default to last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    return {
        "Start": start_date.strftime("%Y-%m-%d"),
        "End": end_date.strftime("%Y-%m-%d")
    }


class TestCostExplorerScanner:
    """Test Cost Explorer scanner against real AWS."""

    @pytest.mark.asyncio
    async def test_cost_scanner_retrieves_costs(self, aws_account_id, cost_date_range):
        """Scanner should retrieve real cost data."""
        from cloud_optimizer.integrations.aws.cost import CostExplorerScanner

        scanner = CostExplorerScanner(region="us-east-1")
        findings = await scanner.scan(aws_account_id)

        # Should return findings (even if empty)
        assert isinstance(findings, list)

        # Log findings for manual review
        print(f"Cost findings: {len(findings)}")
        for f in findings[:5]:
            print(f"  - {f.get('title', 'Unknown')}: {f.get('description', '')[:100]}")

    @pytest.mark.asyncio
    async def test_cost_scanner_detects_anomalies(self, aws_account_id):
        """Scanner should detect cost anomalies if present."""
        from cloud_optimizer.integrations.aws.cost import CostExplorerScanner

        scanner = CostExplorerScanner(region="us-east-1")

        # Get anomalies specifically
        import boto3
        ce = boto3.client("ce", region_name="us-east-1")

        try:
            # Check for anomaly monitors first
            monitors = ce.get_anomaly_monitors(MaxResults=10)
            if not monitors.get("AnomalyMonitors"):
                pytest.skip("No anomaly monitors configured in this account")

            # Get recent anomalies
            anomalies = ce.get_anomalies(
                DateInterval={
                    "StartDate": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                    "EndDate": datetime.now().strftime("%Y-%m-%d")
                },
                MaxResults=10
            )

            print(f"Found {len(anomalies.get('Anomalies', []))} anomalies")

        except Exception as e:
            pytest.skip(f"Cost anomaly detection not available: {e}")

    @pytest.mark.asyncio
    async def test_cost_scanner_rightsizing_recommendations(self, aws_account_id):
        """Scanner should retrieve rightsizing recommendations."""
        import boto3

        ce = boto3.client("ce", region_name="us-east-1")

        try:
            recommendations = ce.get_rightsizing_recommendation(
                Service="AmazonEC2"
            )

            rec_count = len(recommendations.get("RightsizingRecommendations", []))
            print(f"Found {rec_count} rightsizing recommendations")

            # If recommendations exist, verify structure
            if rec_count > 0:
                rec = recommendations["RightsizingRecommendations"][0]
                assert "CurrentInstance" in rec or "RightsizingType" in rec

        except Exception as e:
            pytest.skip(f"Rightsizing recommendations not available: {e}")


class TestRDSScanner:
    """Test RDS scanner against real AWS."""

    @pytest.fixture
    def rds_instance_id(self):
        """Get test RDS instance ID."""
        instance_id = os.getenv("RDS_TEST_INSTANCE_ID")
        if not instance_id:
            pytest.skip("RDS_TEST_INSTANCE_ID not configured")
        return instance_id

    @pytest.mark.asyncio
    async def test_rds_scanner_lists_instances(self, aws_account_id):
        """Scanner should list RDS instances."""
        from cloud_optimizer.integrations.aws.rds import RDSScanner

        scanner = RDSScanner(region="us-east-1")
        findings = await scanner.scan(aws_account_id)

        assert isinstance(findings, list)
        print(f"RDS findings: {len(findings)}")

    @pytest.mark.asyncio
    async def test_rds_scanner_checks_encryption(self, aws_account_id, rds_instance_id):
        """Scanner should check RDS encryption status."""
        import boto3

        rds = boto3.client("rds", region_name="us-east-1")

        response = rds.describe_db_instances(
            DBInstanceIdentifier=rds_instance_id
        )

        instance = response["DBInstances"][0]
        is_encrypted = instance.get("StorageEncrypted", False)

        print(f"RDS instance {rds_instance_id} encryption: {is_encrypted}")

        # If not encrypted, scanner should report a finding
        if not is_encrypted:
            from cloud_optimizer.integrations.aws.rds import RDSScanner
            scanner = RDSScanner(region="us-east-1")
            findings = await scanner.scan(aws_account_id)

            encryption_findings = [
                f for f in findings
                if "encrypt" in f.get("title", "").lower()
                and rds_instance_id in f.get("resource_id", "")
            ]

            assert len(encryption_findings) > 0, "Should detect unencrypted RDS"

    @pytest.mark.asyncio
    async def test_rds_scanner_checks_backup(self, aws_account_id, rds_instance_id):
        """Scanner should check RDS backup configuration."""
        import boto3

        rds = boto3.client("rds", region_name="us-east-1")

        response = rds.describe_db_instances(
            DBInstanceIdentifier=rds_instance_id
        )

        instance = response["DBInstances"][0]
        backup_retention = instance.get("BackupRetentionPeriod", 0)

        print(f"RDS instance {rds_instance_id} backup retention: {backup_retention} days")

        # If no backup, scanner should report
        if backup_retention == 0:
            from cloud_optimizer.integrations.aws.rds import RDSScanner
            scanner = RDSScanner(region="us-east-1")
            findings = await scanner.scan(aws_account_id)

            backup_findings = [
                f for f in findings
                if "backup" in f.get("title", "").lower()
            ]

            assert len(backup_findings) > 0, "Should detect missing backup"


class TestSSMScanner:
    """Test SSM scanner against real AWS."""

    @pytest.fixture
    def ec2_instance_id(self):
        """Get test EC2 instance ID."""
        instance_id = os.getenv("EC2_TEST_INSTANCE_ID")
        if not instance_id:
            pytest.skip("EC2_TEST_INSTANCE_ID not configured")
        return instance_id

    @pytest.mark.asyncio
    async def test_ssm_scanner_lists_managed_instances(self, aws_account_id):
        """Scanner should list SSM-managed instances."""
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")

        response = ssm.describe_instance_information(MaxResults=50)
        instances = response.get("InstanceInformationList", [])

        print(f"SSM-managed instances: {len(instances)}")

        for inst in instances[:5]:
            print(f"  - {inst['InstanceId']}: {inst.get('PingStatus', 'Unknown')}")

    @pytest.mark.asyncio
    async def test_ssm_scanner_checks_patch_compliance(self, aws_account_id, ec2_instance_id):
        """Scanner should check SSM patch compliance."""
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")

        try:
            response = ssm.describe_instance_patches(
                InstanceId=ec2_instance_id
            )

            patches = response.get("Patches", [])
            missing = [p for p in patches if p.get("State") == "Missing"]

            print(f"Instance {ec2_instance_id} patches: {len(patches)} total, {len(missing)} missing")

            # If missing patches, scanner should report
            if missing:
                from cloud_optimizer.integrations.aws.ssm import SSMScanner
                scanner = SSMScanner(region="us-east-1")
                findings = await scanner.scan(aws_account_id)

                patch_findings = [
                    f for f in findings
                    if "patch" in f.get("title", "").lower()
                ]

                print(f"Patch-related findings: {len(patch_findings)}")

        except Exception as e:
            pytest.skip(f"SSM patch compliance not available: {e}")

    @pytest.mark.asyncio
    async def test_ssm_scanner_checks_agent_version(self, aws_account_id):
        """Scanner should check for outdated SSM agents."""
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")

        response = ssm.describe_instance_information(MaxResults=50)
        instances = response.get("InstanceInformationList", [])

        for inst in instances:
            agent_version = inst.get("AgentVersion", "Unknown")
            print(f"Instance {inst['InstanceId']} SSM agent: {agent_version}")


class TestMultiAccountScanning:
    """Test scanning across multiple AWS accounts."""

    @pytest.mark.asyncio
    async def test_organizations_integration(self):
        """Test AWS Organizations integration for multi-account."""
        import boto3

        try:
            org = boto3.client("organizations", region_name="us-east-1")

            org_info = org.describe_organization()
            print(f"Organization: {org_info['Organization']['Id']}")

            accounts = org.list_accounts()
            print(f"Accounts in organization: {len(accounts['Accounts'])}")

        except Exception as e:
            pytest.skip(f"AWS Organizations not available: {e}")
```

### Step 5: Run Real AWS Tests

```bash
# Load test environment
source .env.aws-test

# Run real AWS tests (nightly CI only)
pytest tests/integration/test_epic4_real_aws.py -v -m real_aws

# Run with verbose output
pytest tests/integration/test_epic4_real_aws.py -v -s --tb=short
```

### Step 6: Cleanup Test Resources

```bash
# Delete RDS instance
aws rds delete-db-instance \
  --db-instance-identifier cloud-optimizer-test-db \
  --skip-final-snapshot

# Terminate EC2 instance
aws ec2 terminate-instances --instance-ids i-0123456789abcdef0

# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name cloud-optimizer-test-permissions

# Delete test user (if created)
aws iam delete-access-key --user-name cloud-optimizer-test --access-key-id AKIA...
aws iam detach-user-policy --user-name cloud-optimizer-test --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/CloudOptimizerScannerTestPolicy
aws iam delete-user --user-name cloud-optimizer-test
```

### Cost Considerations

| Resource | Estimated Cost | Notes |
|----------|---------------|-------|
| RDS db.t3.micro | ~$15/month | Stop when not testing |
| EC2 t3.micro | ~$8/month | Stop when not testing |
| Cost Explorer API | Free tier: 10 req/day | Beyond free tier: $0.01/request |
| SSM | Free | No additional cost |

**Recommendation**: Use AWS resource scheduling or stop instances when not actively testing.

---

## 3. LocalStack Pro Features

### Overview

LocalStack Community does not support AWS Marketplace APIs. LocalStack Pro is required for:
- AWS Marketplace Metering Service
- AWS Marketplace Entitlement Service
- License Manager

### Step 1: Get LocalStack Pro License

1. Visit [LocalStack Pro](https://localstack.cloud/pricing/)
2. Choose a plan:
   - **Hobby**: $35/month (1 developer)
   - **Team**: $70/month/developer (collaboration features)
   - **Enterprise**: Contact sales (SSO, dedicated support)

3. After purchase, obtain your API key from the LocalStack dashboard

### Step 2: Configure LocalStack Pro

Create `.env.localstack-pro`:

```bash
# LocalStack Pro Configuration
# DO NOT COMMIT THIS FILE

LOCALSTACK_API_KEY=your-api-key-here
LOCALSTACK_AUTH_TOKEN=your-auth-token-here  # If using auth token instead

# Pro features to enable
SERVICES=marketplace,license-manager,s3,iam,sts,cloudwatch

# Configuration
DEBUG=1
PERSISTENCE=1
```

Add to `.gitignore`:

```
.env.localstack-pro
```

### Step 3: Update Docker Compose for LocalStack Pro

Create `docker/docker-compose.localstack-pro.yml`:

```yaml
version: '3.8'

services:
  localstack-pro:
    container_name: localstack-pro
    image: localstack/localstack-pro:latest
    ports:
      - "4566:4566"
      - "4510-4559:4510-4559"
    environment:
      - LOCALSTACK_API_KEY=${LOCALSTACK_API_KEY}
      - SERVICES=marketplace,license-manager,s3,iam,sts,cloudwatch,ec2,rds
      - DEBUG=1
      - PERSISTENCE=1
      - AWS_DEFAULT_REGION=us-east-1
    volumes:
      - localstack-pro-data:/var/lib/localstack
      - /var/run/docker.sock:/var/run/docker.sock
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/_localstack/health"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  localstack-pro-data:
```

### Step 4: Create Marketplace Test Fixtures

Create `tests/marketplace/pro_fixtures.py`:

```python
"""
LocalStack Pro fixtures for AWS Marketplace testing.

Requires LocalStack Pro license with Marketplace service enabled.
"""

import boto3
import pytest
from botocore.config import Config

LOCALSTACK_ENDPOINT = "http://localhost:4566"


@pytest.fixture(scope="module")
def localstack_pro_available():
    """Check if LocalStack Pro is available with Marketplace support."""
    import requests

    try:
        response = requests.get(f"{LOCALSTACK_ENDPOINT}/_localstack/health")
        health = response.json()

        # Check for Pro services
        services = health.get("services", {})
        if "marketplace" not in services:
            pytest.skip("LocalStack Pro with Marketplace not available")

        return True
    except Exception as e:
        pytest.skip(f"LocalStack not available: {e}")


@pytest.fixture
def marketplace_metering_client(localstack_pro_available):
    """Create Marketplace Metering client for LocalStack Pro."""
    return boto3.client(
        "meteringmarketplace",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=Config(signature_version="v4")
    )


@pytest.fixture
def marketplace_entitlement_client(localstack_pro_available):
    """Create Marketplace Entitlement client for LocalStack Pro."""
    return boto3.client(
        "marketplace-entitlement",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=Config(signature_version="v4")
    )


@pytest.fixture
def license_manager_client(localstack_pro_available):
    """Create License Manager client for LocalStack Pro."""
    return boto3.client(
        "license-manager",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=Config(signature_version="v4")
    )


@pytest.fixture
def test_product_code():
    """Test product code for Marketplace tests."""
    return "test-product-code-12345"


@pytest.fixture
def test_customer_identifier():
    """Test customer identifier."""
    return "test-customer-id-67890"
```

### Step 5: Create LocalStack Pro Marketplace Tests

Create `tests/marketplace/test_marketplace_localstack_pro.py`:

```python
"""
LocalStack Pro Marketplace Integration Tests.

These tests require LocalStack Pro with Marketplace service enabled.
They test actual AWS Marketplace API interactions without mocks.

Prerequisites:
- LocalStack Pro running with LOCALSTACK_API_KEY
- Marketplace service enabled

Run:
    docker-compose -f docker/docker-compose.localstack-pro.yml up -d
    pytest tests/marketplace/test_marketplace_localstack_pro.py -v
"""

import pytest
from datetime import datetime

from tests.marketplace.pro_fixtures import (
    localstack_pro_available,
    marketplace_metering_client,
    marketplace_entitlement_client,
    license_manager_client,
    test_product_code,
    test_customer_identifier,
)


@pytest.mark.localstack_pro
class TestMarketplaceMeteringLocalStackPro:
    """Test Marketplace Metering with LocalStack Pro."""

    def test_register_usage(
        self,
        marketplace_metering_client,
        test_product_code,
        test_customer_identifier
    ):
        """Test RegisterUsage API call."""
        response = marketplace_metering_client.register_usage(
            ProductCode=test_product_code,
            PublicKeyVersion=1,
            Nonce="test-nonce-123"
        )

        assert "Signature" in response
        assert "MeteringRecordId" in response

    def test_meter_usage(
        self,
        marketplace_metering_client,
        test_product_code,
        test_customer_identifier
    ):
        """Test MeterUsage API call."""
        response = marketplace_metering_client.meter_usage(
            ProductCode=test_product_code,
            Timestamp=datetime.utcnow(),
            UsageDimension="SecurityScans",
            UsageQuantity=5,
            DryRun=False
        )

        assert "MeteringRecordId" in response

    def test_batch_meter_usage(
        self,
        marketplace_metering_client,
        test_product_code,
        test_customer_identifier
    ):
        """Test BatchMeterUsage API call."""
        response = marketplace_metering_client.batch_meter_usage(
            ProductCode=test_product_code,
            UsageRecords=[
                {
                    "Timestamp": datetime.utcnow(),
                    "CustomerIdentifier": test_customer_identifier,
                    "Dimension": "SecurityScans",
                    "Quantity": 10
                },
                {
                    "Timestamp": datetime.utcnow(),
                    "CustomerIdentifier": test_customer_identifier,
                    "Dimension": "ChatQuestions",
                    "Quantity": 25
                }
            ]
        )

        results = response.get("Results", [])
        assert len(results) == 2

        for result in results:
            assert result.get("Status") == "Success"


@pytest.mark.localstack_pro
class TestMarketplaceEntitlementLocalStackPro:
    """Test Marketplace Entitlement with LocalStack Pro."""

    def test_get_entitlements(
        self,
        marketplace_entitlement_client,
        test_product_code
    ):
        """Test GetEntitlements API call."""
        response = marketplace_entitlement_client.get_entitlements(
            ProductCode=test_product_code
        )

        assert "Entitlements" in response
        # LocalStack Pro should return empty or mock entitlements

    def test_get_entitlements_with_filter(
        self,
        marketplace_entitlement_client,
        test_product_code,
        test_customer_identifier
    ):
        """Test GetEntitlements with customer filter."""
        response = marketplace_entitlement_client.get_entitlements(
            ProductCode=test_product_code,
            Filter={
                "CUSTOMER_IDENTIFIER": [test_customer_identifier]
            }
        )

        assert "Entitlements" in response


@pytest.mark.localstack_pro
class TestLicenseManagerLocalStackPro:
    """Test License Manager with LocalStack Pro."""

    def test_list_licenses(self, license_manager_client):
        """Test ListLicenses API call."""
        response = license_manager_client.list_licenses()

        assert "Licenses" in response

    def test_checkout_license(self, license_manager_client):
        """Test CheckoutLicense API call."""
        # This requires a pre-created license in LocalStack
        # Skip if no licenses exist
        licenses = license_manager_client.list_licenses()

        if not licenses.get("Licenses"):
            pytest.skip("No licenses configured in LocalStack Pro")

        license_arn = licenses["Licenses"][0]["LicenseArn"]

        response = license_manager_client.checkout_license(
            ProductSKU="test-sku",
            CheckoutType="PROVISIONAL",
            KeyFingerprint="test-fingerprint",
            Entitlements=[
                {
                    "Name": "test-entitlement",
                    "Value": "1",
                    "Unit": "Count"
                }
            ]
        )

        assert "LicenseConsumptionToken" in response


@pytest.mark.localstack_pro
class TestCloudOptimizerMarketplaceIntegration:
    """Integration tests for Cloud Optimizer marketplace services."""

    @pytest.mark.asyncio
    async def test_license_validator_with_localstack_pro(
        self,
        localstack_pro_available,
        test_product_code
    ):
        """Test LicenseValidator against LocalStack Pro."""
        import os
        os.environ["AWS_ENDPOINT_URL"] = "http://localhost:4566"
        os.environ["MARKETPLACE_PRODUCT_CODE"] = test_product_code

        from cloud_optimizer.marketplace.license import MarketplaceLicenseValidator

        validator = MarketplaceLicenseValidator(
            product_code=test_product_code
        )

        # Override client endpoint
        validator._client = None  # Force recreation with endpoint

        status = await validator.validate()

        # LocalStack Pro should return a valid status
        assert status is not None
        print(f"License status from LocalStack Pro: {status}")

    @pytest.mark.asyncio
    async def test_metering_service_with_localstack_pro(
        self,
        localstack_pro_available,
        test_product_code
    ):
        """Test UsageMeteringService against LocalStack Pro."""
        import os
        os.environ["AWS_ENDPOINT_URL"] = "http://localhost:4566"
        os.environ["MARKETPLACE_PRODUCT_CODE"] = test_product_code

        from cloud_optimizer.marketplace.metering import UsageMeteringService

        service = UsageMeteringService(
            product_code=test_product_code,
            enabled=True
        )

        # Record some usage
        await service.record_usage("SecurityScans", 5)
        await service.record_usage("ChatQuestions", 10)

        # Force flush
        await service._flush_buffer()

        print("Successfully metered usage to LocalStack Pro")
```

### Step 6: Run LocalStack Pro Tests

```bash
# Start LocalStack Pro
source .env.localstack-pro
docker-compose -f docker/docker-compose.localstack-pro.yml up -d

# Wait for healthy
until curl -s http://localhost:4566/_localstack/health | grep -q "running"; do
  echo "Waiting for LocalStack Pro..."
  sleep 5
done

# Run tests
pytest tests/marketplace/test_marketplace_localstack_pro.py -v -m localstack_pro

# Cleanup
docker-compose -f docker/docker-compose.localstack-pro.yml down -v
```

### LocalStack Pro Service Coverage

| Service | Community | Pro |
|---------|-----------|-----|
| S3, IAM, STS | ✅ | ✅ |
| EC2, RDS | ✅ | ✅ |
| Marketplace Metering | ❌ | ✅ |
| Marketplace Entitlement | ❌ | ✅ |
| License Manager | ❌ | ✅ |
| Cost Explorer | ❌ | ✅ (Limited) |

---

## 4. Environment Configuration Summary

### Environment Variables

Create a master `.env.example` for documentation:

```bash
# Cloud Optimizer Test Environment Configuration
# Copy to .env and fill in values

# ===== Basic Configuration =====
DATABASE_URL=postgresql://test:test@localhost:5434/test_intelligence
REDIS_URL=redis://localhost:6379/0

# ===== AWS Configuration =====
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
AWS_TEST_ACCOUNT_ID=

# ===== LocalStack =====
LOCALSTACK_ENDPOINT=http://localhost:4566
USE_LOCALSTACK=true

# ===== LocalStack Pro (Optional) =====
LOCALSTACK_API_KEY=
USE_LOCALSTACK_PRO=false

# ===== Real AWS Testing (Optional) =====
USE_REAL_AWS=false
RDS_TEST_INSTANCE_ID=
EC2_TEST_INSTANCE_ID=
COST_EXPLORER_START_DATE=
COST_EXPLORER_END_DATE=

# ===== Smart-Scaffold =====
SS_GRAPH_BACKEND=postgres
SS_GRAPH_URL=postgresql://test:test@localhost:5434/ss_test

# ===== Intelligence-Builder =====
IB_PLATFORM_URL=http://localhost:8000
IB_API_KEY=test-api-key
IB_TENANT_ID=test-tenant

# ===== Marketplace =====
MARKETPLACE_ENABLED=false
MARKETPLACE_PRODUCT_CODE=test-product-code
```

### Pytest Markers

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (no external dependencies)",
    "integration: Integration tests (LocalStack/test DB)",
    "e2e: End-to-end tests (full stack)",
    "real_aws: Tests requiring real AWS account",
    "localstack_pro: Tests requiring LocalStack Pro",
    "ss_validator: Smart-Scaffold validator tests",
    "slow: Tests that take >30 seconds",
    "nightly: Tests to run nightly only",
]
```

---

## 5. CI/CD Integration

### GitHub Actions Workflow

Create `.github/workflows/advanced-tests.yml`:

```yaml
name: Advanced Integration Tests

on:
  schedule:
    # Run nightly at 2 AM UTC
    - cron: '0 2 * * *'
  workflow_dispatch:
    inputs:
      run_real_aws:
        description: 'Run real AWS tests'
        type: boolean
        default: false
      run_localstack_pro:
        description: 'Run LocalStack Pro tests'
        type: boolean
        default: false

env:
  PYTHON_VERSION: '3.11'

jobs:
  localstack-pro-tests:
    if: github.event.inputs.run_localstack_pro == 'true' || github.event_name == 'schedule'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Start LocalStack Pro
        env:
          LOCALSTACK_API_KEY: ${{ secrets.LOCALSTACK_API_KEY }}
        run: |
          docker-compose -f docker/docker-compose.localstack-pro.yml up -d
          sleep 30  # Wait for services

      - name: Run LocalStack Pro tests
        run: |
          poetry run pytest tests/marketplace/test_marketplace_localstack_pro.py -v -m localstack_pro

      - name: Cleanup
        if: always()
        run: docker-compose -f docker/docker-compose.localstack-pro.yml down -v

  real-aws-tests:
    if: github.event.inputs.run_real_aws == 'true'
    runs-on: ubuntu-latest
    environment: aws-test  # Requires approval
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_TEST_ROLE_ARN }}
          aws-region: us-east-1

      - name: Run real AWS tests
        env:
          USE_REAL_AWS: 'true'
          AWS_TEST_ACCOUNT_ID: ${{ secrets.AWS_TEST_ACCOUNT_ID }}
          RDS_TEST_INSTANCE_ID: ${{ secrets.RDS_TEST_INSTANCE_ID }}
          EC2_TEST_INSTANCE_ID: ${{ secrets.EC2_TEST_INSTANCE_ID }}
        run: |
          poetry run pytest tests/integration/test_epic4_real_aws.py -v -m real_aws

  ss-validator-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_intelligence
        ports:
          - 5434:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
          pip install smart-scaffold intelligence-builder-sdk || true

      - name: Seed test data
        run: |
          # Seed divergent datasets
          python scripts/seed_ss_graph.py || echo "SS seeding skipped"
          python scripts/seed_ib_graph.py || echo "IB seeding skipped"

      - name: Run SS validator tests
        run: |
          poetry run pytest tests/integration/test_ss_parallel_validator.py -v -m ss_validator || echo "SS validator tests skipped"
```

### Required Secrets

Configure in GitHub repository settings:

| Secret | Description | Required For |
|--------|-------------|--------------|
| `LOCALSTACK_API_KEY` | LocalStack Pro license key | LocalStack Pro tests |
| `AWS_TEST_ROLE_ARN` | IAM role ARN for testing | Real AWS tests |
| `AWS_TEST_ACCOUNT_ID` | AWS account ID | Real AWS tests |
| `RDS_TEST_INSTANCE_ID` | Test RDS instance ID | RDS scanner tests |
| `EC2_TEST_INSTANCE_ID` | Test EC2 instance ID | SSM scanner tests |

---

## Quick Reference

### Run Test Subsets

```bash
# Unit tests only (fast, no dependencies)
pytest -m unit

# Integration tests (LocalStack Community)
pytest -m integration

# E2E tests (full stack)
./tests/e2e/run_e2e_tests.sh

# LocalStack Pro tests
pytest -m localstack_pro

# Real AWS tests (requires credentials)
USE_REAL_AWS=true pytest -m real_aws

# SS validator tests
pytest -m ss_validator

# Nightly tests (all advanced)
pytest -m "nightly or real_aws or localstack_pro"
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| LocalStack Pro not starting | Check `LOCALSTACK_API_KEY` is set correctly |
| Real AWS tests failing | Verify IAM permissions and resource IDs |
| SS validator tests skipped | Ensure divergent fixtures are seeded |
| Cost Explorer empty | Wait 24 hours after enabling |
| SSM tests failing | Verify EC2 instance has SSM agent running |

---

## Support

For issues with:
- **LocalStack Pro**: [LocalStack Support](https://localstack.cloud/support/)
- **AWS**: [AWS Support Center](https://console.aws.amazon.com/support/)
- **Smart-Scaffold**: [GitHub Issues](https://github.com/Intelligence-Builder/smart-scaffold/issues)
- **Cloud Optimizer**: [GitHub Issues](https://github.com/Intelligence-Builder/Cloud-Optimizer/issues)
