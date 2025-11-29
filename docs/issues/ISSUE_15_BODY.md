## Parent Epic
Part of #4 (Epic 4: Remaining Cloud Optimizer Pillars)

## Reference Documentation
- **See `docs/platform/TECHNICAL_DESIGN.md` Section 3 for domain module system**
- **AWS Well-Architected Framework - Cost Optimization Pillar**

## Objective
Implement Cost Optimization domain in Intelligence-Builder and integrate into CO v2.

## Domain Definition

### Entity Types (5)

| Entity Type | Required Properties | Optional Properties | Description |
|-------------|---------------------|---------------------|-------------|
| cost_anomaly | name, amount, baseline | period, service, account | Unusual spending pattern |
| savings_opportunity | name, estimated_savings | resource_type, recommendation | Potential cost reduction |
| reserved_instance | name, instance_type | utilization, expiration, coverage | RI recommendation |
| rightsizing_recommendation | name, current_size, recommended_size | savings_percent, resource_arn | Instance sizing |
| idle_resource | name, resource_type, resource_arn | last_activity, monthly_cost | Unused resource |

### Relationship Types

| Relationship | Source | Target | Description |
|--------------|--------|--------|-------------|
| affects | cost_anomaly | savings_opportunity | Anomaly reveals opportunity |
| recommends | savings_opportunity | rightsizing_recommendation | Opportunity suggests action |
| covers | reserved_instance | idle_resource | RI could cover resource |

## IB Domain Implementation

```python
# src/platform/domains/cost/domain.py
class CostOptimizationDomain(BaseDomain):
    name = "cost_optimization"
    display_name = "Cost Optimization"
    version = "1.0.0"

    entity_types = [
        EntityTypeDefinition(
            name="cost_anomaly",
            description="Unusual spending pattern detected",
            required_properties=["name", "amount", "baseline"],
            optional_properties=["period", "service", "account"],
        ),
        # ... 4 more entity types
    ]
```

## CO v2 Integration

### AWS Cost Explorer Scanner
```python
# src/cloud_optimizer/integrations/aws/cost.py
class CostExplorerScanner(BaseAWSScanner):
    """Scans AWS Cost Explorer for optimization opportunities."""

    async def scan(self, account_id: str, region: str) -> List[dict]:
        ce = self._get_client("ce", "us-east-1")  # Cost Explorer is global

        findings = []
        findings.extend(await self._find_anomalies(ce, account_id))
        findings.extend(await self._find_idle_resources(ce, account_id))
        findings.extend(await self._get_ri_recommendations(ce, account_id))

        return findings
```

## Test Scenarios
```python
class TestCostOptimizationDomain:
    def test_domain_has_5_entity_types()
    def test_cost_anomaly_requires_amount()
    def test_savings_requires_estimated_savings()

class TestCostExplorerScanner:
    async def test_detects_spending_anomaly()
    async def test_finds_idle_resources()
    async def test_gets_ri_recommendations()
```

## Acceptance Criteria
- [ ] Domain registered in IB with 5 entity types
- [ ] Pattern detection for cost-related text
- [ ] AWS Cost Explorer integration
- [ ] Anomaly detection working
- [ ] RI recommendations extracted
- [ ] Dashboard displays cost metrics
- [ ] Cross-domain relationships (cost -> security)
