## Parent Epic
Part of #4 (Epic 4: Remaining Cloud Optimizer Pillars)

## Reference Documentation
- **See `docs/platform/TECHNICAL_DESIGN.md` Section 3 for domain module system**
- **AWS Well-Architected Framework - Reliability Pillar**

## Objective
Implement Reliability domain in Intelligence-Builder and integrate into CO v2.

## Domain Definition

### Entity Types (5)

| Entity Type | Required Properties | Optional Properties | Description |
|-------------|---------------------|---------------------|-------------|
| single_point_of_failure | name, resource | impact, mitigation | SPOF detection |
| backup_configuration | name, resource | frequency, retention, last_backup | Backup status |
| disaster_recovery | name, strategy | rpo, rto, failover_region | DR configuration |
| availability_zone | name, region | resources, health_status | AZ distribution |
| health_check | name, target | protocol, interval, threshold | Health monitoring |

### Relationship Types

| Relationship | Source | Target | Description |
|--------------|--------|--------|-------------|
| mitigated_by | single_point_of_failure | backup_configuration | SPOF has backup |
| protected_by | availability_zone | disaster_recovery | AZ has DR plan |
| monitors | health_check | single_point_of_failure | Health check watches SPOF |

## IB Domain Implementation

```python
class ReliabilityDomain(BaseDomain):
    name = "reliability"
    display_name = "Reliability"
    version = "1.0.0"

    entity_types = [
        EntityTypeDefinition(
            name="single_point_of_failure",
            description="Single point of failure detected",
            required_properties=["name", "resource"],
            optional_properties=["impact", "mitigation"],
        ),
        # ... 4 more entity types
    ]
```

## CO v2 Integration

### Reliability Scanner
```python
class ReliabilityScanner(BaseAWSScanner):
    """Scans for reliability issues and SPOF."""

    async def scan(self, account_id: str, region: str) -> List[dict]:
        findings = []

        # Check for single-AZ deployments
        findings.extend(await self._find_single_az_resources(account_id, region))

        # Check backup configurations
        findings.extend(await self._check_backups(account_id, region))

        # Verify health checks exist
        findings.extend(await self._verify_health_checks(account_id, region))

        return findings

    async def _find_single_az_resources(self, account_id: str, region: str):
        """Find resources deployed in single AZ (SPOF)."""
        ec2 = self._get_client("ec2", region)
        rds = self._get_client("rds", region)

        findings = []
        # Check RDS for single-AZ
        dbs = rds.describe_db_instances()["DBInstances"]
        for db in dbs:
            if not db.get("MultiAZ"):
                findings.append({
                    "title": f"RDS {db['DBInstanceIdentifier']} is single-AZ",
                    "severity": "medium",
                    "resource_arn": db["DBInstanceArn"],
                    # ...
                })

        return findings
```

## Test Scenarios
```python
class TestReliabilityDomain:
    def test_domain_has_5_entity_types()
    def test_spof_requires_resource()

class TestReliabilityScanner:
    async def test_detects_single_az_rds()
    async def test_checks_backup_configuration()
    async def test_verifies_health_checks()
```

## Acceptance Criteria
- [ ] Domain registered in IB with 5 entity types
- [ ] SPOF detection for RDS, ELB, EC2
- [ ] Backup configuration verification
- [ ] Multi-AZ deployment checking
- [ ] Health check inventory
- [ ] Dashboard displays reliability metrics
