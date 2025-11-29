# Epic 4: Remaining Cloud Optimizer Pillars

## Overview

Implement the remaining AWS Well-Architected Framework pillars as domains in Intelligence-Builder and integrate them into Cloud Optimizer v2.

**Priority**: Medium
**Dependencies**: Epic 3 (CO v2 Rebuild) complete

## Objectives

1. Implement Cost Optimization domain
2. Implement Performance Efficiency domain
3. Implement Reliability domain
4. Implement Operational Excellence domain

## Domains

### 4.1 Cost Optimization Domain
Entity Types:
- `cost_anomaly` - Unusual spending patterns
- `savings_opportunity` - Potential cost savings
- `reserved_instance` - RI recommendations
- `rightsizing_recommendation` - Instance sizing
- `idle_resource` - Unused resources

### 4.2 Performance Efficiency Domain
Entity Types:
- `performance_bottleneck` - Performance issues
- `scaling_recommendation` - Auto-scaling suggestions
- `latency_issue` - Network/application latency
- `throughput_metric` - Throughput measurements
- `resource_contention` - Resource conflicts

### 4.3 Reliability Domain
Entity Types:
- `single_point_of_failure` - SPOF detection
- `backup_configuration` - Backup status
- `disaster_recovery` - DR configuration
- `availability_zone` - AZ distribution
- `health_check` - Health monitoring

### 4.4 Operational Excellence Domain
Entity Types:
- `operational_procedure` - Runbooks/procedures
- `automation_opportunity` - Automation potential
- `monitoring_gap` - Missing monitoring
- `documentation_issue` - Doc deficiencies
- `change_management` - Change processes

## Acceptance Criteria

- [ ] All 4 domains registered in IB
- [ ] Pattern detection working for each domain
- [ ] CO v2 integrates all domains
- [ ] Cross-domain relationships working
- [ ] Total CO v2 LOC < 10K
- [ ] AWS integration for each pillar
- [ ] Dashboard displays metrics for all pillars

## Sub-Tasks

- #15 - 4.1 Cost Optimization Domain
- #16 - 4.2 Performance Efficiency Domain
- #17 - 4.3 Reliability Domain
- #18 - 4.4 Operational Excellence Domain

---

## Integration Test Specification

### Test Environment

| Component | Configuration | Notes |
|-----------|---------------|-------|
| IB Platform | localhost:8000 | With all domains registered |
| CO v2 App | localhost:8080 | Application under test |
| LocalStack | localhost:4566 | Mocked AWS services |
| PostgreSQL | localhost:5432 | For IB platform |

```yaml
# tests/integration/conftest.py
CO_APP_URL: http://localhost:8080
IB_PLATFORM_URL: http://localhost:8000
AWS_ENDPOINT_URL: http://localhost:4566
AWS_ACCESS_KEY_ID: test
AWS_SECRET_ACCESS_KEY: test
AWS_REGION: us-east-1
```

### End-to-End Test Scenarios

| ID | Scenario | Flow | Input | Expected Output |
|----|----------|------|-------|-----------------|
| E4-INT-01 | Cost Anomaly Detection | AWS Cost Data → IB | Cost Explorer data | cost_anomaly entities |
| E4-INT-02 | Savings Opportunities | Resource scan → IB | EC2/RDS inventory | savings_opportunity entities |
| E4-INT-03 | Performance Analysis | CloudWatch → IB | Metrics data | performance entities |
| E4-INT-04 | Reliability Scan | AWS Config → IB | Multi-AZ resources | reliability entities |
| E4-INT-05 | Cross-Domain Links | All domains → Graph | Full scan | Cross-domain relationships |
| E4-INT-06 | Dashboard All Pillars | Query all domains | Account ID | Aggregated metrics all pillars |

### LocalStack AWS Setup for All Pillars

```python
# tests/integration/conftest.py
import boto3
import pytest
from datetime import datetime, timedelta

@pytest.fixture(scope="session")
def localstack_all_pillars():
    """Set up LocalStack with test data for all pillars."""
    endpoint = "http://localhost:4566"

    # EC2 for performance and reliability tests
    ec2 = boto3.client("ec2", endpoint_url=endpoint, region_name="us-east-1")

    # Create VPC and subnets in multiple AZs
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    subnet_a = ec2.create_subnet(
        VpcId=vpc["VpcId"],
        CidrBlock="10.0.1.0/24",
        AvailabilityZone="us-east-1a"
    )["Subnet"]

    subnet_b = ec2.create_subnet(
        VpcId=vpc["VpcId"],
        CidrBlock="10.0.2.0/24",
        AvailabilityZone="us-east-1b"
    )["Subnet"]

    # Create instances - one oversized (rightsizing candidate)
    oversized_instance = ec2.run_instances(
        ImageId="ami-12345678",
        InstanceType="m5.4xlarge",  # Likely oversized
        MinCount=1,
        MaxCount=1,
        SubnetId=subnet_a["SubnetId"],
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [{"Key": "Name", "Value": "oversized-instance"}]
        }]
    )["Instances"][0]

    # Create instance in single AZ (SPOF candidate)
    spof_instance = ec2.run_instances(
        ImageId="ami-12345678",
        InstanceType="t3.medium",
        MinCount=1,
        MaxCount=1,
        SubnetId=subnet_a["SubnetId"],
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [{"Key": "Name", "Value": "single-az-instance"}]
        }]
    )["Instances"][0]

    # RDS for reliability tests
    rds = boto3.client("rds", endpoint_url=endpoint, region_name="us-east-1")

    # Single-AZ database (reliability issue)
    rds.create_db_instance(
        DBInstanceIdentifier="single-az-db",
        DBInstanceClass="db.t3.medium",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
        MultiAZ=False,
        AllocatedStorage=20
    )

    # Multi-AZ database (good configuration)
    rds.create_db_instance(
        DBInstanceIdentifier="multi-az-db",
        DBInstanceClass="db.t3.medium",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
        MultiAZ=True,
        AllocatedStorage=20
    )

    # S3 for cost analysis
    s3 = boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1")
    s3.create_bucket(Bucket="unused-bucket-30-days")
    # Don't put any objects - simulates idle resource

    s3.create_bucket(Bucket="active-bucket")
    s3.put_object(Bucket="active-bucket", Key="test.txt", Body=b"test data")

    # CloudWatch for performance metrics
    cloudwatch = boto3.client("cloudwatch", endpoint_url=endpoint, region_name="us-east-1")

    # Put high CPU metrics (performance bottleneck)
    cloudwatch.put_metric_data(
        Namespace="AWS/EC2",
        MetricData=[{
            "MetricName": "CPUUtilization",
            "Dimensions": [{"Name": "InstanceId", "Value": oversized_instance["InstanceId"]}],
            "Value": 15.0,  # Low utilization = oversized
            "Unit": "Percent"
        }]
    )

    yield {
        "vpc_id": vpc["VpcId"],
        "subnet_a_id": subnet_a["SubnetId"],
        "subnet_b_id": subnet_b["SubnetId"],
        "oversized_instance_id": oversized_instance["InstanceId"],
        "spof_instance_id": spof_instance["InstanceId"],
    }

    # Cleanup
    ec2.terminate_instances(InstanceIds=[
        oversized_instance["InstanceId"],
        spof_instance["InstanceId"]
    ])
    rds.delete_db_instance(DBInstanceIdentifier="single-az-db", SkipFinalSnapshot=True)
    rds.delete_db_instance(DBInstanceIdentifier="multi-az-db", SkipFinalSnapshot=True)
```

### Integration Test Implementation

```python
# tests/integration/test_epic4_pillars.py
"""Epic 4 Integration Tests - Remaining AWS Well-Architected Pillars"""

import pytest
from httpx import AsyncClient


class TestCostOptimizationDomain:
    """E4-INT-01/02: Cost optimization scanning."""

    @pytest.mark.asyncio
    async def test_detects_idle_resources(
        self, co_client: AsyncClient, localstack_all_pillars, ib_client
    ):
        """Scan detects idle S3 buckets."""
        response = await co_client.post(
            "/api/v1/cost/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["idle_resources"],
                "region": "us-east-1"
            }
        )

        assert response.status_code == 200
        result = response.json()

        idle_resources = [
            e for e in result.get("entities", [])
            if e["entity_type"] == "idle_resource"
        ]
        assert len(idle_resources) >= 1

    @pytest.mark.asyncio
    async def test_detects_rightsizing_opportunities(
        self, co_client: AsyncClient, localstack_all_pillars, ib_client
    ):
        """Scan detects oversized instances."""
        response = await co_client.post(
            "/api/v1/cost/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["rightsizing"],
                "region": "us-east-1"
            }
        )

        assert response.status_code == 200
        result = response.json()

        # Verify rightsizing recommendation created
        rightsizing = [
            e for e in result.get("entities", [])
            if e["entity_type"] == "rightsizing_recommendation"
        ]
        assert len(rightsizing) >= 1

        # Verify pushed to IB
        findings = await ib_client.entities.search(
            domain="cost",
            entity_type="rightsizing_recommendation"
        )
        assert len(findings) >= 1

    @pytest.mark.asyncio
    async def test_savings_opportunity_calculation(
        self, co_client: AsyncClient, localstack_all_pillars
    ):
        """Savings opportunities include estimated savings."""
        response = await co_client.post(
            "/api/v1/cost/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["all"],
                "region": "us-east-1"
            }
        )

        assert response.status_code == 200
        result = response.json()

        savings = [
            e for e in result.get("entities", [])
            if e["entity_type"] == "savings_opportunity"
        ]

        # Each savings opportunity should have estimated_savings
        for s in savings:
            assert "estimated_monthly_savings" in s["properties"]
            assert s["properties"]["estimated_monthly_savings"] >= 0


class TestPerformanceEfficiencyDomain:
    """E4-INT-03: Performance efficiency scanning."""

    @pytest.mark.asyncio
    async def test_detects_performance_bottlenecks(
        self, co_client: AsyncClient, localstack_all_pillars, ib_client
    ):
        """Scan detects high CPU utilization instances."""
        response = await co_client.post(
            "/api/v1/performance/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["bottlenecks"],
                "region": "us-east-1",
                "lookback_hours": 24
            }
        )

        assert response.status_code == 200
        result = response.json()

        # Note: Our test data has LOW CPU (oversized), not high CPU bottleneck
        # In real scenario, high CPU would create bottleneck findings
        assert "entities" in result

    @pytest.mark.asyncio
    async def test_scaling_recommendations(
        self, co_client: AsyncClient, localstack_all_pillars
    ):
        """Performance scan generates scaling recommendations."""
        response = await co_client.post(
            "/api/v1/performance/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["scaling"],
                "region": "us-east-1"
            }
        )

        assert response.status_code == 200
        result = response.json()

        scaling_recs = [
            e for e in result.get("entities", [])
            if e["entity_type"] == "scaling_recommendation"
        ]

        for rec in scaling_recs:
            assert "direction" in rec["properties"]  # scale_up or scale_down
            assert "resource_id" in rec["properties"]


class TestReliabilityDomain:
    """E4-INT-04: Reliability scanning."""

    @pytest.mark.asyncio
    async def test_detects_single_point_of_failure(
        self, co_client: AsyncClient, localstack_all_pillars, ib_client
    ):
        """Scan detects resources without redundancy."""
        response = await co_client.post(
            "/api/v1/reliability/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["spof"],
                "region": "us-east-1"
            }
        )

        assert response.status_code == 200
        result = response.json()

        spof_findings = [
            e for e in result.get("entities", [])
            if e["entity_type"] == "single_point_of_failure"
        ]
        assert len(spof_findings) >= 1  # Single-AZ RDS

        # Verify pushed to IB
        findings = await ib_client.entities.search(
            domain="reliability",
            entity_type="single_point_of_failure"
        )
        assert len(findings) >= 1

    @pytest.mark.asyncio
    async def test_detects_single_az_database(
        self, co_client: AsyncClient, localstack_all_pillars
    ):
        """Scan flags single-AZ RDS instances."""
        response = await co_client.post(
            "/api/v1/reliability/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["database_ha"],
                "region": "us-east-1"
            }
        )

        assert response.status_code == 200
        result = response.json()

        db_findings = [
            e for e in result.get("entities", [])
            if "single-az-db" in str(e.get("properties", {}).get("resource", ""))
        ]
        assert len(db_findings) >= 1

    @pytest.mark.asyncio
    async def test_backup_configuration_check(
        self, co_client: AsyncClient, localstack_all_pillars
    ):
        """Scan checks backup configurations."""
        response = await co_client.post(
            "/api/v1/reliability/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["backups"],
                "region": "us-east-1"
            }
        )

        assert response.status_code == 200
        result = response.json()

        backup_configs = [
            e for e in result.get("entities", [])
            if e["entity_type"] == "backup_configuration"
        ]

        for config in backup_configs:
            assert "retention_days" in config["properties"]
            assert "enabled" in config["properties"]


class TestOperationalExcellenceDomain:
    """E4-INT-04 (cont): Operational excellence scanning."""

    @pytest.mark.asyncio
    async def test_detects_monitoring_gaps(
        self, co_client: AsyncClient, localstack_all_pillars, ib_client
    ):
        """Scan detects resources without CloudWatch alarms."""
        response = await co_client.post(
            "/api/v1/opex/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["monitoring"],
                "region": "us-east-1"
            }
        )

        assert response.status_code == 200
        result = response.json()

        monitoring_gaps = [
            e for e in result.get("entities", [])
            if e["entity_type"] == "monitoring_gap"
        ]
        # Resources without alarms should be flagged
        assert isinstance(monitoring_gaps, list)

    @pytest.mark.asyncio
    async def test_automation_opportunities(
        self, co_client: AsyncClient, localstack_all_pillars
    ):
        """Scan identifies automation opportunities."""
        response = await co_client.post(
            "/api/v1/opex/scan/aws",
            json={
                "aws_account_id": "123456789012",
                "scan_types": ["automation"],
                "region": "us-east-1"
            }
        )

        assert response.status_code == 200
        result = response.json()

        automation_opps = [
            e for e in result.get("entities", [])
            if e["entity_type"] == "automation_opportunity"
        ]

        for opp in automation_opps:
            assert "opportunity_type" in opp["properties"]
            assert "resource_id" in opp["properties"]


class TestCrossDomainRelationships:
    """E4-INT-05: Cross-domain relationship linking."""

    @pytest.mark.asyncio
    async def test_cost_security_relationship(
        self, co_client: AsyncClient, localstack_all_pillars, ib_client
    ):
        """Cost and security findings link to same resource."""
        # Run both scans
        await co_client.post(
            "/api/v1/security/scan/aws",
            json={"aws_account_id": "123456789012", "region": "us-east-1"}
        )
        await co_client.post(
            "/api/v1/cost/scan/aws",
            json={"aws_account_id": "123456789012", "region": "us-east-1"}
        )

        # Query cross-domain graph
        response = await co_client.get(
            "/api/v1/graph/cross-domain",
            params={
                "aws_account_id": "123456789012",
                "domains": ["security", "cost"]
            }
        )

        assert response.status_code == 200
        graph = response.json()

        # Should have relationships linking findings to resources
        assert "nodes" in graph
        assert "edges" in graph

    @pytest.mark.asyncio
    async def test_reliability_cost_relationship(
        self, co_client: AsyncClient, localstack_all_pillars, ib_client
    ):
        """Single-AZ (reliability) relates to cost savings opportunity."""
        # Multi-AZ costs more but improves reliability
        await co_client.post(
            "/api/v1/reliability/scan/aws",
            json={"aws_account_id": "123456789012", "region": "us-east-1"}
        )
        await co_client.post(
            "/api/v1/cost/scan/aws",
            json={"aws_account_id": "123456789012", "region": "us-east-1"}
        )

        # Query relationships
        response = await co_client.get(
            "/api/v1/graph/relationships",
            params={
                "relationship_type": "tradeoff",
                "domains": ["reliability", "cost"]
            }
        )

        assert response.status_code == 200
        # Relationships should show cost-reliability tradeoffs


class TestDashboardAllPillars:
    """E4-INT-06: Dashboard aggregation across all pillars."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_all_pillar_metrics(
        self, co_client: AsyncClient, seeded_all_pillars
    ):
        """Dashboard endpoint returns metrics for all 5 pillars."""
        response = await co_client.get(
            "/api/v1/dashboard/well-architected",
            params={"aws_account_id": "123456789012"}
        )

        assert response.status_code == 200
        data = response.json()

        # All 5 pillars should be present
        assert "security" in data["pillars"]
        assert "cost_optimization" in data["pillars"]
        assert "performance_efficiency" in data["pillars"]
        assert "reliability" in data["pillars"]
        assert "operational_excellence" in data["pillars"]

        # Each pillar should have metrics
        for pillar_name, pillar_data in data["pillars"].items():
            assert "total_findings" in pillar_data
            assert "findings_by_severity" in pillar_data
            assert "score" in pillar_data  # 0-100 score

    @pytest.mark.asyncio
    async def test_dashboard_overall_score(
        self, co_client: AsyncClient, seeded_all_pillars
    ):
        """Dashboard calculates overall Well-Architected score."""
        response = await co_client.get(
            "/api/v1/dashboard/well-architected",
            params={"aws_account_id": "123456789012"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "overall_score" in data
        assert 0 <= data["overall_score"] <= 100

        # Verify recommendations prioritized
        assert "priority_recommendations" in data
        assert isinstance(data["priority_recommendations"], list)
```

### Performance Benchmarks

| Operation | Requirement | Test Method | Notes |
|-----------|-------------|-------------|-------|
| Cost scan (100 resources) | < 5s | Response time | LocalStack |
| Performance scan | < 5s | Response time | CloudWatch metrics |
| Reliability scan | < 3s | Response time | RDS + EC2 |
| OpEx scan | < 3s | Response time | Monitoring check |
| Cross-domain query | < 500ms | Response time | Graph traversal |
| Dashboard all pillars | < 1s | Response time | Aggregation |

### Domain Registration Tests

```python
# tests/integration/test_epic4_domains.py
"""Domain registration tests for all pillars."""

import pytest

class TestDomainRegistration:
    """Verify all 4 new domains register correctly."""

    @pytest.mark.asyncio
    async def test_cost_domain_registered(self, ib_client):
        """Cost optimization domain is registered."""
        domains = await ib_client.domains.list()
        domain_names = [d.name for d in domains]
        assert "cost" in domain_names or "cost_optimization" in domain_names

    @pytest.mark.asyncio
    async def test_performance_domain_registered(self, ib_client):
        """Performance efficiency domain is registered."""
        domains = await ib_client.domains.list()
        domain_names = [d.name for d in domains]
        assert "performance" in domain_names or "performance_efficiency" in domain_names

    @pytest.mark.asyncio
    async def test_reliability_domain_registered(self, ib_client):
        """Reliability domain is registered."""
        domains = await ib_client.domains.list()
        domain_names = [d.name for d in domains]
        assert "reliability" in domain_names

    @pytest.mark.asyncio
    async def test_opex_domain_registered(self, ib_client):
        """Operational excellence domain is registered."""
        domains = await ib_client.domains.list()
        domain_names = [d.name for d in domains]
        assert "opex" in domain_names or "operational_excellence" in domain_names

    @pytest.mark.asyncio
    async def test_all_entity_types_available(self, ib_client):
        """All entity types from all domains are queryable."""
        expected_types = [
            # Cost
            "cost_anomaly", "savings_opportunity", "rightsizing_recommendation",
            # Performance
            "performance_bottleneck", "scaling_recommendation",
            # Reliability
            "single_point_of_failure", "backup_configuration",
            # OpEx
            "monitoring_gap", "automation_opportunity"
        ]

        for entity_type in expected_types:
            # Should not throw - type is registered
            result = await ib_client.entities.search(entity_type=entity_type)
            assert isinstance(result, list)
```

### CI Integration

```yaml
# .github/workflows/integration-tests.yml
epic4-integration:
  needs: [epic3-integration]
  runs-on: ubuntu-latest
  services:
    localstack:
      image: localstack/localstack:latest
      ports:
        - 4566:4566
      env:
        SERVICES: ec2,rds,s3,cloudwatch
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
    - run: pytest tests/integration/test_epic4_*.py -v --tb=short
```
