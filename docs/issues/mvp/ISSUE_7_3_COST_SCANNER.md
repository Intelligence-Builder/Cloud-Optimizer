# 7.3 Cost Analysis Scanner

## Parent Epic
Epic 7: MVP Phase 2 - Security & Cost Scanning

## Overview

Implement cost analysis scanning that identifies savings opportunities in AWS accounts. Uses Cost Explorer API, Trusted Advisor, and resource analysis to provide actionable cost optimization recommendations with estimated dollar savings.

## Background

Cost optimization is a key value driver for trial customers. The scanner must:
- Identify unused/underutilized resources
- Provide rightsizing recommendations
- Calculate estimated savings in dollars
- Integrate with chat for cost-related questions
- Stay within trial limits

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| CST-001 | Cost Explorer integration | Query last 30 days spend by service, identify trends |
| CST-002 | Unused resource detection | Identify idle EC2, unattached EBS, unused EIPs |
| CST-003 | Rightsizing recommendations | EC2 rightsizing based on utilization metrics |
| CST-004 | Reserved Instance analysis | RI coverage and savings recommendations |
| CST-005 | Savings estimation | Calculate monthly savings for each recommendation |

## Technical Specification

### Cost Scanner Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Cost Scanner                                  │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                     Data Sources                                 ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  ││
│  │  │ Cost Explorer│  │ CloudWatch   │  │ Resource Inventory   │  ││
│  │  │ - Spend data │  │ - Utilization│  │ - EC2, EBS, EIP      │  ││
│  │  │ - Trends     │  │ - Metrics    │  │ - Snapshots          │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                              │                                       │
│  ┌───────────────────────────┼───────────────────────────────────┐  │
│  │                    Analyzers                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐│  │
│  │  │ Unused      │  │ Rightsizing │  │ Reserved Instance       ││  │
│  │  │ Resources   │  │ Analysis    │  │ Analysis                ││  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘│  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                    ┌─────────▼─────────┐                            │
│                    │ Cost Findings     │                            │
│                    │ (with $ savings)  │                            │
│                    └───────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Database Schema

```sql
-- Cost findings table
CREATE TABLE cost_findings (
    finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES scan_jobs(job_id),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    aws_account_id VARCHAR(12) NOT NULL,

    -- Finding details
    category VARCHAR(50) NOT NULL,       -- 'unused_resource', 'rightsizing', 'reserved_instance'
    resource_type VARCHAR(50) NOT NULL,  -- 'ec2_instance', 'ebs_volume', etc.
    resource_id VARCHAR(255) NOT NULL,
    resource_name VARCHAR(255),
    region VARCHAR(20) NOT NULL,

    -- Cost analysis
    current_monthly_cost DECIMAL(10, 2),
    recommended_monthly_cost DECIMAL(10, 2),
    estimated_monthly_savings DECIMAL(10, 2),
    estimated_annual_savings DECIMAL(10, 2),
    confidence VARCHAR(10),              -- 'high', 'medium', 'low'

    -- Recommendation
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    recommendation_type VARCHAR(50),     -- 'terminate', 'resize', 'purchase_ri'

    -- For rightsizing
    current_instance_type VARCHAR(50),
    recommended_instance_type VARCHAR(50),
    utilization_data JSONB,              -- CPU/memory/network metrics

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'open',  -- open, implemented, dismissed
    implemented_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cost_findings_job ON cost_findings(job_id);
CREATE INDEX idx_cost_findings_tenant ON cost_findings(tenant_id);
CREATE INDEX idx_cost_findings_category ON cost_findings(category);
CREATE INDEX idx_cost_findings_savings ON cost_findings(estimated_monthly_savings DESC);

-- Cost summary table (per scan)
CREATE TABLE cost_summaries (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES scan_jobs(job_id),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    aws_account_id VARCHAR(12) NOT NULL,

    -- Spend summary
    total_monthly_spend DECIMAL(12, 2),
    spend_by_service JSONB,              -- {"EC2": 1500, "RDS": 800, ...}
    spend_trend_30d DECIMAL(5, 2),       -- % change vs previous 30 days

    -- Savings summary
    total_potential_monthly_savings DECIMAL(12, 2),
    savings_by_category JSONB,           -- {"unused": 500, "rightsizing": 300}

    -- Resource counts
    total_resources_analyzed INTEGER,
    resources_with_recommendations INTEGER,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Cost Scanner Service

```python
# src/cloud_optimizer/scanners/cost/cost_scanner.py
from decimal import Decimal

class CostScanner:
    def __init__(self, session: boto3.Session):
        self.session = session
        self.ce_client = session.client("ce")
        self.ec2_client = session.client("ec2")
        self.cloudwatch = session.client("cloudwatch")

    async def scan(self, regions: list[str]) -> CostScanResult:
        """Run full cost analysis scan."""
        findings = []

        # Get cost data
        spend_data = await self._get_spend_summary()

        # Run analyzers
        findings.extend(await self._analyze_unused_resources(regions))
        findings.extend(await self._analyze_rightsizing(regions))
        findings.extend(await self._analyze_ri_coverage())

        # Calculate totals
        total_savings = sum(f.estimated_monthly_savings for f in findings)

        return CostScanResult(
            findings=findings,
            spend_summary=spend_data,
            total_potential_monthly_savings=total_savings,
        )

    async def _get_spend_summary(self) -> SpendSummary:
        """Get cost summary from Cost Explorer."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=30)

        response = self.ce_client.get_cost_and_usage(
            TimePeriod={
                "Start": start_date.isoformat(),
                "End": end_date.isoformat(),
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        spend_by_service = {}
        total = Decimal("0")

        for result in response.get("ResultsByTime", []):
            for group in result.get("Groups", []):
                service = group["Keys"][0]
                amount = Decimal(group["Metrics"]["UnblendedCost"]["Amount"])
                spend_by_service[service] = float(amount)
                total += amount

        return SpendSummary(
            total_monthly_spend=float(total),
            spend_by_service=spend_by_service,
        )


class UnusedResourceAnalyzer:
    """Detect unused and idle resources."""

    async def analyze(
        self, session: boto3.Session, regions: list[str]
    ) -> list[CostFinding]:
        findings = []

        for region in regions:
            ec2 = session.client("ec2", region_name=region)

            # Unattached EBS volumes
            findings.extend(await self._check_unattached_volumes(ec2, region))

            # Unused Elastic IPs
            findings.extend(await self._check_unused_eips(ec2, region))

            # Idle EC2 instances
            cloudwatch = session.client("cloudwatch", region_name=region)
            findings.extend(
                await self._check_idle_instances(ec2, cloudwatch, region)
            )

        return findings

    async def _check_unattached_volumes(
        self, ec2, region: str
    ) -> list[CostFinding]:
        """Find EBS volumes not attached to any instance."""
        response = ec2.describe_volumes(
            Filters=[{"Name": "status", "Values": ["available"]}]
        )

        findings = []
        for volume in response.get("Volumes", []):
            # Estimate cost based on size and type
            size_gb = volume["Size"]
            volume_type = volume["VolumeType"]
            monthly_cost = self._estimate_ebs_cost(size_gb, volume_type)

            findings.append(
                CostFinding(
                    category="unused_resource",
                    resource_type="ebs_volume",
                    resource_id=volume["VolumeId"],
                    region=region,
                    title="Unattached EBS Volume",
                    description=f"EBS volume {volume['VolumeId']} is not attached to any instance",
                    recommendation="Delete the volume if no longer needed, or attach to an instance",
                    recommendation_type="terminate",
                    current_monthly_cost=monthly_cost,
                    recommended_monthly_cost=Decimal("0"),
                    estimated_monthly_savings=monthly_cost,
                    estimated_annual_savings=monthly_cost * 12,
                    confidence="high",
                )
            )

        return findings

    async def _check_idle_instances(
        self, ec2, cloudwatch, region: str
    ) -> list[CostFinding]:
        """Find EC2 instances with very low CPU utilization."""
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )

        findings = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance["InstanceId"]
                instance_type = instance["InstanceType"]

                # Get CPU utilization for last 14 days
                avg_cpu = await self._get_average_cpu(
                    cloudwatch, instance_id, days=14
                )

                if avg_cpu < 5:  # Less than 5% average CPU
                    monthly_cost = self._estimate_ec2_cost(instance_type)

                    findings.append(
                        CostFinding(
                            category="unused_resource",
                            resource_type="ec2_instance",
                            resource_id=instance_id,
                            region=region,
                            title="Idle EC2 Instance",
                            description=f"Instance {instance_id} has average CPU utilization of {avg_cpu:.1f}%",
                            recommendation="Consider stopping or terminating this instance",
                            recommendation_type="terminate",
                            current_monthly_cost=monthly_cost,
                            recommended_monthly_cost=Decimal("0"),
                            estimated_monthly_savings=monthly_cost,
                            estimated_annual_savings=monthly_cost * 12,
                            confidence="high",
                            utilization_data={"avg_cpu_14d": avg_cpu},
                        )
                    )

        return findings


class RightsizingAnalyzer:
    """Recommend instance type changes based on utilization."""

    # Instance type mappings for downsizing
    DOWNSIZE_MAP = {
        "t3.xlarge": "t3.large",
        "t3.large": "t3.medium",
        "t3.medium": "t3.small",
        "m5.xlarge": "m5.large",
        "m5.large": "t3.large",
        # ... more mappings
    }

    async def analyze(
        self, session: boto3.Session, regions: list[str]
    ) -> list[CostFinding]:
        findings = []

        for region in regions:
            ec2 = session.client("ec2", region_name=region)
            cloudwatch = session.client("cloudwatch", region_name=region)

            response = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )

            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    finding = await self._analyze_instance(
                        instance, ec2, cloudwatch, region
                    )
                    if finding:
                        findings.append(finding)

        return findings

    async def _analyze_instance(
        self, instance: dict, ec2, cloudwatch, region: str
    ) -> CostFinding | None:
        """Analyze single instance for rightsizing opportunity."""
        instance_id = instance["InstanceId"]
        instance_type = instance["InstanceType"]

        # Get utilization metrics
        metrics = await self._get_utilization_metrics(
            cloudwatch, instance_id, days=14
        )

        # Check if underutilized
        if metrics["avg_cpu"] < 40 and instance_type in self.DOWNSIZE_MAP:
            recommended_type = self.DOWNSIZE_MAP[instance_type]

            current_cost = self._get_instance_cost(instance_type)
            recommended_cost = self._get_instance_cost(recommended_type)
            savings = current_cost - recommended_cost

            return CostFinding(
                category="rightsizing",
                resource_type="ec2_instance",
                resource_id=instance_id,
                region=region,
                title="EC2 Rightsizing Opportunity",
                description=f"Instance {instance_id} ({instance_type}) is underutilized with {metrics['avg_cpu']:.1f}% average CPU",
                recommendation=f"Resize from {instance_type} to {recommended_type}",
                recommendation_type="resize",
                current_instance_type=instance_type,
                recommended_instance_type=recommended_type,
                current_monthly_cost=current_cost,
                recommended_monthly_cost=recommended_cost,
                estimated_monthly_savings=savings,
                estimated_annual_savings=savings * 12,
                confidence="medium" if metrics["avg_cpu"] < 20 else "low",
                utilization_data=metrics,
            )

        return None
```

## API Endpoints

```
POST /api/v1/cost/scan               # Start cost analysis scan
GET  /api/v1/cost/summary            # Get cost summary for account
GET  /api/v1/cost/findings           # List cost findings
GET  /api/v1/cost/findings/:id       # Get finding details
PUT  /api/v1/cost/findings/:id       # Update finding status (implemented/dismissed)
GET  /api/v1/cost/savings            # Get total savings potential
```

## Files to Create

```
src/cloud_optimizer/scanners/cost/
├── __init__.py
├── cost_scanner.py              # Main cost scanner
├── spend_analyzer.py            # Cost Explorer integration
├── unused_analyzer.py           # Unused resource detection
├── rightsizing_analyzer.py      # Rightsizing recommendations
├── ri_analyzer.py               # Reserved Instance analysis
└── pricing.py                   # AWS pricing data

src/cloud_optimizer/models/
├── cost_finding.py              # CostFinding model
└── cost_summary.py              # CostSummary model

src/cloud_optimizer/api/routers/
└── cost.py                      # Cost API endpoints

alembic/versions/
└── xxx_create_cost_tables.py    # Migration

data/pricing/
└── ec2_pricing.json             # Cached pricing data

tests/scanners/cost/
├── test_cost_scanner.py
├── test_unused_analyzer.py
├── test_rightsizing_analyzer.py
└── test_ri_analyzer.py
```

## Testing Requirements

### Unit Tests
- [ ] `test_spend_analyzer.py` - Cost Explorer parsing
- [ ] `test_unused_volumes.py` - Unattached EBS detection
- [ ] `test_unused_eips.py` - Unused EIP detection
- [ ] `test_idle_instances.py` - Low CPU instance detection
- [ ] `test_rightsizing.py` - Rightsizing recommendation logic
- [ ] `test_savings_calculation.py` - Dollar amount calculations

### Integration Tests
- [ ] `test_cost_scan_integration.py` - Full scan with LocalStack

### Mocking Strategy

```python
@pytest.fixture
def mock_cost_explorer():
    return {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2024-01-01", "End": "2024-01-31"},
                "Groups": [
                    {"Keys": ["Amazon EC2"], "Metrics": {"UnblendedCost": {"Amount": "1500.00"}}},
                    {"Keys": ["Amazon RDS"], "Metrics": {"UnblendedCost": {"Amount": "800.00"}}},
                ],
            }
        ]
    }
```

## Acceptance Criteria Checklist

- [ ] Cost Explorer data retrieved for last 30 days
- [ ] Spend by service calculated correctly
- [ ] Unattached EBS volumes detected
- [ ] Unused Elastic IPs detected
- [ ] Idle instances (CPU < 5%) detected
- [ ] Rightsizing recommendations generated for underutilized instances
- [ ] Savings calculated in dollars (monthly and annual)
- [ ] Confidence level assigned to each recommendation
- [ ] Findings queryable via API
- [ ] Findings status can be updated (implemented/dismissed)
- [ ] 80%+ test coverage

## Dependencies

- 7.1 AWS Account Connection (needs AWS session)

## Blocked By

- 7.1 AWS Account Connection

## Blocks

- 7.4 Findings Management (generates findings)
- 8.3 Security Analysis (IB processes cost findings)

## Estimated Effort

1.5 weeks

## Labels

`cost`, `optimization`, `scanner`, `mvp`, `phase-2`, `P0`
