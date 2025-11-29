## Parent Epic
Part of #4 (Epic 4: Remaining Cloud Optimizer Pillars)

## Reference Documentation
- **See `docs/platform/TECHNICAL_DESIGN.md` Section 3 for domain module system**
- **AWS Well-Architected Framework - Operational Excellence Pillar**

## Objective
Implement Operational Excellence domain in Intelligence-Builder and integrate into CO v2.

## Domain Definition

### Entity Types (5)

| Entity Type | Required Properties | Optional Properties | Description |
|-------------|---------------------|---------------------|-------------|
| operational_procedure | name, type | document_url, last_updated | Runbook/procedure |
| automation_opportunity | name, task | complexity, estimated_savings | Automation potential |
| monitoring_gap | name, resource | missing_metrics, severity | Missing monitoring |
| documentation_issue | name, component | issue_type, priority | Doc deficiency |
| change_management | name, change_type | approval_status, risk_level | Change process |

### Relationship Types

| Relationship | Source | Target | Description |
|--------------|--------|--------|-------------|
| documents | operational_procedure | change_management | Procedure covers change |
| automates | automation_opportunity | operational_procedure | Automation replaces manual |
| reveals | monitoring_gap | documentation_issue | Gap shows doc need |

## IB Domain Implementation

```python
class OperationalExcellenceDomain(BaseDomain):
    name = "operational_excellence"
    display_name = "Operational Excellence"
    version = "1.0.0"

    entity_types = [
        EntityTypeDefinition(
            name="operational_procedure",
            description="Runbook or operational procedure",
            required_properties=["name", "type"],
            optional_properties=["document_url", "last_updated"],
        ),
        # ... 4 more entity types
    ]
```

## CO v2 Integration

### Systems Manager Scanner
```python
class SystemsManagerScanner(BaseAWSScanner):
    """Scans AWS Systems Manager for operational insights."""

    async def scan(self, account_id: str, region: str) -> List[dict]:
        ssm = self._get_client("ssm", region)
        cw = self._get_client("cloudwatch", region)

        findings = []

        # Check for missing runbooks
        findings.extend(await self._check_runbooks(ssm))

        # Check for unmonitored resources
        findings.extend(await self._find_monitoring_gaps(cw, account_id, region))

        # Check for automation opportunities
        findings.extend(await self._find_automation_opportunities(ssm))

        return findings

    async def _find_monitoring_gaps(self, cw, account_id: str, region: str):
        """Find resources without CloudWatch alarms."""
        ec2 = self._get_client("ec2", region)

        # Get all EC2 instances
        instances = ec2.describe_instances()
        instance_ids = [i["InstanceId"] for r in instances["Reservations"] for i in r["Instances"]]

        # Get alarms
        alarms = cw.describe_alarms()["MetricAlarms"]
        monitored = {a["Dimensions"][0]["Value"] for a in alarms if a["Dimensions"]}

        findings = []
        for iid in instance_ids:
            if iid not in monitored:
                findings.append({
                    "title": f"EC2 {iid} has no CloudWatch alarms",
                    "severity": "medium",
                    "resource_arn": f"arn:aws:ec2:{region}:{account_id}:instance/{iid}",
                    # ...
                })

        return findings
```

## Test Scenarios
```python
class TestOperationalExcellenceDomain:
    def test_domain_has_5_entity_types()
    def test_procedure_requires_type()

class TestSystemsManagerScanner:
    async def test_checks_runbook_coverage()
    async def test_finds_monitoring_gaps()
    async def test_identifies_automation_opportunities()
```

## Acceptance Criteria
- [ ] Domain registered in IB with 5 entity types
- [ ] Systems Manager integration
- [ ] Monitoring gap detection
- [ ] Runbook inventory
- [ ] Automation opportunity identification
- [ ] Dashboard displays operational metrics
- [ ] Cross-domain relationships working
