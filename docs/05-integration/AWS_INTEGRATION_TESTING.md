# AWS Integration Testing Guide

This guide covers the dual-mode AWS integration testing infrastructure for Cloud Optimizer, supporting both LocalStack (free, local) and real AWS environments.

## Overview

Cloud Optimizer's integration tests can run in two modes:

| Mode | Use Case | Cost | Setup |
|------|----------|------|-------|
| **LocalStack** (default) | Development, CI/CD | Free | Docker only |
| **Real AWS** | Full validation, pre-production | AWS charges apply | AWS credentials |

## Quick Start

```bash
# LocalStack mode (default)
docker-compose -f docker/docker-compose.test.yml up -d
PYTHONPATH=src pytest tests/integration/

# Real AWS mode
USE_REAL_AWS=true PYTHONPATH=src pytest tests/integration/
```

## Prerequisites

### LocalStack Mode

1. Docker installed and running
2. Start test containers:
   ```bash
   docker-compose -f docker/docker-compose.test.yml up -d
   ```

### Real AWS Mode

1. AWS account with appropriate permissions
2. AWS credentials configured (see [AWS Credentials Setup](#aws-credentials-setup))
3. IAM user with required permissions (see [IAM Permissions](#iam-permissions))

## AWS Credentials Setup

### Option 1: AWS CLI (Recommended)

```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output (json)
```

### Option 2: Manual Configuration

Create `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

Create `~/.aws/config`:
```ini
[default]
region = us-east-1
output = json
```

### Option 3: Environment Variables

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

## IAM Permissions

The IAM user running tests requires specific permissions. Choose one:

### Option A: PowerUserAccess (Broader)

Attach the AWS managed policy `PowerUserAccess` to your IAM user. This provides broad access suitable for development/testing.

### Option B: Custom Policy (Minimal)

Create and attach a custom policy with minimal required permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CloudOptimizerTesting",
            "Effect": "Allow",
            "Action": [
                "ec2:CreateVolume",
                "ec2:DeleteVolume",
                "ec2:CreateTags",
                "ec2:DescribeVolumes",
                "ec2:AllocateAddress",
                "ec2:ReleaseAddress",
                "ec2:DescribeAddresses",
                "ec2:DescribeInstances",
                "ec2:DescribeSecurityGroups",
                "cloudwatch:GetMetricData",
                "cloudwatch:ListMetrics",
                "ce:GetCostAndUsage",
                "rds:DescribeDBInstances",
                "elasticloadbalancing:DescribeLoadBalancers",
                "ssm:DescribeInstanceInformation",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_REAL_AWS` | `false` | Set to `true` to use real AWS instead of LocalStack |
| `LOCALSTACK_ENDPOINT` | `http://localhost:4566` | LocalStack endpoint URL |
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region for tests |

### Test Markers

Tests use pytest markers for conditional execution:

```python
@pytest.mark.skipif(not USE_REAL_AWS, reason="Requires real AWS")
async def test_cost_explorer_full_scan(self):
    ...
```

## Running Tests

### All Integration Tests

```bash
# LocalStack
PYTHONPATH=src pytest tests/integration/ -v

# Real AWS
USE_REAL_AWS=true PYTHONPATH=src pytest tests/integration/ -v
```

### Specific Test Files

```bash
# Epic 4 Scanner Tests
USE_REAL_AWS=true PYTHONPATH=src pytest tests/integration/test_epic4_scanners.py -v

# Security Tests
USE_REAL_AWS=true PYTHONPATH=src pytest tests/integration/test_security_integration.py -v
```

### Test Selection by Marker

```bash
# Only integration tests
pytest -m integration

# Only real AWS tests (when in real AWS mode)
USE_REAL_AWS=true pytest -m integration
```

## Test Coverage by Mode

### LocalStack Mode (15 tests pass, 6 skip)

Services available in LocalStack Community:
- ✅ EC2 (instances, volumes, security groups, EIPs)
- ✅ S3 (buckets, objects)
- ✅ IAM (users, policies, roles)
- ✅ STS (identity)
- ⚠️ CloudWatch (limited - no metrics data)

Services NOT available in LocalStack Community:
- ❌ Cost Explorer (ce)
- ❌ RDS
- ❌ ELB/ALB
- ❌ SSM (disabled)

### Real AWS Mode (21 tests pass)

All services available:
- ✅ Cost Explorer - Full cost analysis and recommendations
- ✅ RDS - Database reliability checks
- ✅ ELB/ALB - Load balancer health checks
- ✅ SSM - Systems Manager agent status
- ✅ CloudWatch - Full metrics and alarms

## Architecture

### Test Infrastructure

```
tests/integration/
├── aws_conftest.py          # Dual-mode AWS fixtures
├── conftest.py              # General test fixtures
├── test_epic4_scanners.py   # Cost, Performance, Reliability, Operations
├── test_epic5_ss_integration.py
└── test_security_integration.py
```

### Key Components

**`aws_conftest.py`** provides:

```python
# Mode detection
USE_REAL_AWS = os.getenv("USE_REAL_AWS", "false").lower() in ("true", "1", "yes")

# Universal client creation
def create_client(service_name: str) -> Any:
    """Create boto3 client for LocalStack or real AWS."""
    if USE_REAL_AWS:
        return boto3.client(service_name, config=AWS_CONFIG)
    else:
        return boto3.client(
            service_name,
            endpoint_url=LOCALSTACK_ENDPOINT,
            aws_access_key_id="test",
            aws_secret_access_key="test",
            config=AWS_CONFIG,
        )

# Fixtures for all AWS services
@pytest.fixture
def ec2_client(aws_mode: str) -> Generator[Any, None, None]:
    ...

@pytest.fixture
def s3_client(aws_mode: str) -> Generator[Any, None, None]:
    ...
```

## Resource Cleanup

### Automatic Cleanup

Test fixtures automatically clean up resources:

```python
@pytest.fixture
def ec2_client() -> Generator[Any, None, None]:
    client = create_client("ec2")
    yield client

    # Cleanup on teardown
    volumes = client.describe_volumes(
        Filters=[{"Name": "tag:test", "Values": ["true"]}]
    )
    for vol in volumes.get("Volumes", []):
        client.delete_volume(VolumeId=vol["VolumeId"])
```

### Manual Cleanup

If tests fail mid-execution, clean up manually:

```bash
# Find test resources (tagged with "test=true")
aws ec2 describe-volumes --filters "Name=tag:test,Values=true"
aws ec2 describe-addresses

# Delete orphaned resources
aws ec2 delete-volume --volume-id vol-xxx
aws ec2 release-address --allocation-id eipalloc-xxx
```

## Troubleshooting

### LocalStack Not Available

```
SKIPPED: LocalStack not available at http://localhost:4566
```

**Solution**: Start LocalStack containers:
```bash
docker-compose -f docker/docker-compose.test.yml up -d
docker-compose -f docker/docker-compose.test.yml ps  # Verify running
```

### AWS Credentials Not Found

```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solution**: Configure AWS credentials (see [AWS Credentials Setup](#aws-credentials-setup))

### Permission Denied

```
botocore.exceptions.ClientError: An error occurred (UnauthorizedOperation)
```

**Solution**: Add required IAM permissions (see [IAM Permissions](#iam-permissions))

### Verify AWS Access

```bash
# Test credentials
python3 -c "import boto3; print(boto3.client('sts').get_caller_identity())"
```

## Cost Considerations

When using real AWS:

1. **EC2 Resources**: Tests create/delete EBS volumes and Elastic IPs
   - EBS: ~$0.10/GB-month (tests use small volumes briefly)
   - EIP: Free when attached, $0.005/hour when unattached

2. **API Calls**: Minimal costs for DescribeX operations

3. **Cost Explorer**: GetCostAndUsage API calls
   - First 10 requests/day: Free
   - Additional: $0.01 per request

**Estimated cost per full test run**: < $0.01

## CI/CD Integration

### GitHub Actions Example

```yaml
jobs:
  test-localstack:
    runs-on: ubuntu-latest
    services:
      localstack:
        image: localstack/localstack:latest
        ports:
          - 4566:4566
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: PYTHONPATH=src pytest tests/integration/ -v

  test-real-aws:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'  # Only on main branch
    steps:
      - uses: actions/checkout@v4
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Run tests
        run: USE_REAL_AWS=true PYTHONPATH=src pytest tests/integration/ -v
```

## Related Documentation

- [Development Standards](../03-development/DEVELOPMENT_STANDARDS.md)
- [IB SDK Integration](./IB_SDK_INTEGRATION.md)
- [Smart-Scaffold Integration](./SMART_SCAFFOLD_INTEGRATION.md)
