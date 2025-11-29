## Parent Epic
Part of #5 (Epic 5: Smart-Scaffold Integration & Cutover)

## Reference Documentation
- **See `docs/smart-scaffold/SMART_SCAFFOLD_INTEGRATION.md`**
- **See `docs/platform/PROJECT_GOALS.md` for success criteria**

## Objective
Complete production cutover with validation and archive old KG code.

## Cutover Checklist

### Pre-Cutover Validation
- [ ] All entities migrated (count verification)
- [ ] All relationships migrated (count verification)
- [ ] Random sample validation (100 entities)
- [ ] Query result comparison (10 test queries)
- [ ] Performance benchmarks met (< 200ms API)
- [ ] Integration tests passing (100%)
- [ ] Rollback procedure documented and tested

### Cutover Steps

#### Step 1: Final Migration
```bash
# Run final migration with validation
python scripts/migrate_ss_to_ib.py --mode=production --validate

# Expected output:
# Migrated 5,432 entities
# Migrated 12,847 relationships
# Validation: 100% match
```

#### Step 2: Switch DNS/Configuration
```yaml
# Update Smart-Scaffold configuration
knowledge_graph:
  backend: "intelligence-builder"  # Was: "local-memgraph"
  ib_platform_url: "https://ib.example.com"
  ib_api_key: "${IB_API_KEY}"
  tenant_id: "smart-scaffold"
```

#### Step 3: Parallel Operation Period
```python
# Run both systems for 1 week, comparing results
class ParallelValidator:
    """Validates IB results against legacy system."""

    async def validate_query(self, query: str):
        legacy_result = await self.legacy_kg.query(query)
        ib_result = await self.ib_client.search.hybrid(query)

        if not self._results_match(legacy_result, ib_result):
            self.log_discrepancy(query, legacy_result, ib_result)

        return ib_result  # Always return IB result
```

#### Step 4: Complete Cutover
```bash
# Disable legacy KG writes
export SS_LEGACY_KG_ENABLED=false

# Verify IB-only operation
smart-scaffold health --check-ib-only
```

#### Step 5: Archive Old Code
```bash
# Move old KG code to archive
mkdir -p archive/legacy_kg
mv smart_scaffold/knowledge_graph/legacy/* archive/legacy_kg/

# Remove from imports
# Update __init__.py files
```

## Data Integrity Validation

### Entity Count Verification
```python
async def verify_entity_counts():
    """Verify entity counts match between systems."""
    ss_counts = await ss_kg.count_by_type()
    ib_counts = await ib_client.entities.count_by_type(domain="development")

    for entity_type, ss_count in ss_counts.items():
        ib_count = ib_counts.get(entity_type, 0)
        if ss_count != ib_count:
            raise ValidationError(
                f"Count mismatch for {entity_type}: SS={ss_count}, IB={ib_count}"
            )

    print("Entity counts verified!")
```

### Relationship Verification
```python
async def verify_relationships():
    """Verify relationship integrity."""
    ss_rels = await ss_kg.count_relationships_by_type()
    ib_rels = await ib_client.relationships.count_by_type()

    for rel_type, ss_count in ss_rels.items():
        ib_count = ib_rels.get(rel_type, 0)
        if ss_count != ib_count:
            raise ValidationError(
                f"Relationship mismatch for {rel_type}: SS={ss_count}, IB={ib_count}"
            )
```

### Query Result Comparison
```python
TEST_QUERIES = [
    "Find all issues implementing feature X",
    "What commits modified file Y?",
    "Which PRs reference issue Z?",
    # ... 7 more test queries
]

async def verify_query_results():
    """Compare query results between systems."""
    for query in TEST_QUERIES:
        ss_result = await ss_kg.query(query)
        ib_result = await ib_client.search.hybrid(query)

        if not results_equivalent(ss_result, ib_result):
            log_discrepancy(query, ss_result, ib_result)
```

## Rollback Procedure

### If Issues Detected
```bash
# 1. Switch back to legacy KG
export SS_KNOWLEDGE_GRAPH_BACKEND=legacy

# 2. Restart services
systemctl restart smart-scaffold

# 3. Investigate discrepancies
python scripts/analyze_discrepancies.py
```

## Archive Structure
```
archive/
└── legacy_kg/
    ├── README.md           # Why this was archived
    ├── memgraph_backend.py # Old Memgraph implementation
    ├── local_graph.py      # Old local graph code
    └── migrations/         # Old migration scripts
```

## Performance Validation
| Metric | Requirement | Pre-Cutover | Post-Cutover |
|--------|-------------|-------------|--------------|
| API Response | < 200ms | | |
| Entity Create | < 50ms | | |
| Graph Traversal | < 100ms | | |
| Vector Search | < 150ms | | |

## Test Scenarios
```python
class TestCutover:
    async def test_entity_count_verification()
    async def test_relationship_verification()
    async def test_query_comparison()
    async def test_rollback_procedure()

class TestPostCutover:
    async def test_ib_only_operation()
    async def test_performance_requirements()
    async def test_legacy_code_removed()
```

## Acceptance Criteria
- [ ] SS uses IB for all knowledge graph operations
- [ ] Context system works with IB
- [ ] No data loss during migration (verified)
- [ ] Performance meets requirements (< 200ms)
- [ ] All integration tests passing
- [ ] Workflow coordination maintained
- [ ] Old KG code archived with documentation
- [ ] Rollback tested and documented
