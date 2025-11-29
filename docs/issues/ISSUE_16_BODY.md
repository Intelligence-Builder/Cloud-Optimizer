## Parent Epic
Part of #4 (Epic 4: Remaining Cloud Optimizer Pillars)

## Reference Documentation
- **See `docs/platform/TECHNICAL_DESIGN.md` Section 3 for domain module system**
- **AWS Well-Architected Framework - Performance Efficiency Pillar**

## Objective
Implement Performance Efficiency domain in Intelligence-Builder and integrate into CO v2.

## Domain Definition

### Entity Types (5)

| Entity Type | Required Properties | Optional Properties | Description |
|-------------|---------------------|---------------------|-------------|
| performance_bottleneck | name, resource, metric | threshold, current_value | Performance issue |
| scaling_recommendation | name, resource_type | min_capacity, max_capacity, target | Auto-scaling suggestion |
| latency_issue | name, endpoint | p50, p95, p99, target_latency | Network/app latency |
| throughput_metric | name, resource | requests_per_second, target | Throughput measurement |
| resource_contention | name, resource_type | contention_type, affected_resources | Resource conflict |

### Relationship Types

| Relationship | Source | Target | Description |
|--------------|--------|--------|-------------|
| causes | performance_bottleneck | latency_issue | Bottleneck causes latency |
| resolves | scaling_recommendation | performance_bottleneck | Scaling fixes issue |
| impacts | resource_contention | throughput_metric | Contention affects throughput |

## IB Domain Implementation

```python
class PerformanceEfficiencyDomain(BaseDomain):
    name = "performance_efficiency"
    display_name = "Performance Efficiency"
    version = "1.0.0"

    entity_types = [
        EntityTypeDefinition(
            name="performance_bottleneck",
            description="Identified performance issue",
            required_properties=["name", "resource", "metric"],
            optional_properties=["threshold", "current_value"],
        ),
        # ... 4 more entity types
    ]
```

## CO v2 Integration

### CloudWatch Metrics Scanner
```python
class CloudWatchScanner(BaseAWSScanner):
    """Scans CloudWatch for performance issues."""

    BOTTLENECK_THRESHOLDS = {
        "CPUUtilization": 80,
        "MemoryUtilization": 85,
        "DiskQueueLength": 10,
    }

    async def scan(self, account_id: str, region: str) -> List[dict]:
        cw = self._get_client("cloudwatch", region)

        findings = []
        findings.extend(await self._find_cpu_bottlenecks(cw))
        findings.extend(await self._find_memory_issues(cw))
        findings.extend(await self._analyze_latency(cw))

        return findings
```

## Test Scenarios
```python
class TestPerformanceDomain:
    def test_domain_has_5_entity_types()
    def test_bottleneck_requires_metric()

class TestCloudWatchScanner:
    async def test_detects_cpu_bottleneck()
    async def test_detects_memory_issue()
    async def test_analyzes_latency_percentiles()
```

## Acceptance Criteria
- [ ] Domain registered in IB with 5 entity types
- [ ] CloudWatch metrics integration
- [ ] Bottleneck detection based on thresholds
- [ ] Latency percentile analysis (p50/p95/p99)
- [ ] Auto-scaling recommendations
- [ ] Dashboard displays performance metrics
