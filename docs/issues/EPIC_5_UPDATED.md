# Epic 5: Smart-Scaffold Integration & Cutover

## Overview

Migrate Smart-Scaffold to use Intelligence-Builder for knowledge graph functionality while preserving local context system and workflow coordination.

**Priority**: Medium
**Dependencies**: Epic 4 (Remaining Pillars) complete

## Objectives

1. Migrate Smart-Scaffold knowledge graph to IB platform
2. Integrate SS context system with IB entities
3. Complete production cutover with validation

## Architecture After Migration

```
Smart-Scaffold
├── Local Systems (PostgreSQL)
│   ├── Context records (revision-controlled)
│   ├── Workflow events (temporal)
│   └── Session state
│
└── Intelligence-Builder Platform (via SDK)
    ├── Issues, PRs, commits as entities
    ├── Relationships (implements, tests, modifies)
    ├── Vector search for similar issues
    └── Graph traversal for implementation paths
```

## Deliverables

### 5.1 Smart-Scaffold KG Migration
- Analyze current SS KG schema
- Map SS entities to IB entity types
- Create migration scripts
- Plan hybrid operation period

### 5.2 Context System Integration
- Port context system to work with IB
- Maintain local JSON context
- Create context-to-entity sync
- Preserve workflow coordination

### 5.3 Production Cutover
- Deploy IB with all domains
- Migrate SS to use IB
- Run parallel operation period
- Validate data integrity
- Complete cutover
- Archive old KG code

## Acceptance Criteria

- [ ] SS uses IB for knowledge graph operations
- [ ] Context system works with IB
- [ ] No data loss during migration
- [ ] Performance meets requirements (< 200ms API response)
- [ ] All integration tests passing
- [ ] Workflow coordination maintained
- [ ] Old KG code archived

## Sub-Tasks

- #19 - 5.1 Smart-Scaffold KG Migration
- #20 - 5.2 Context System Integration
- #21 - 5.3 Production Cutover

---

## Integration Test Specification

### Test Environment

| Component | Configuration | Notes |
|-----------|---------------|-------|
| IB Platform | localhost:8000 | Full platform with all domains |
| Smart-Scaffold | localhost:8081 | Application under test |
| Legacy KG | localhost:7687 | Memgraph (for comparison) |
| PostgreSQL | localhost:5432 | Local context storage |

```yaml
# tests/integration/conftest.py
IB_PLATFORM_URL: http://localhost:8000
SS_APP_URL: http://localhost:8081
LEGACY_KG_URI: bolt://localhost:7687
POSTGRES_URL: postgresql://test:test@localhost:5432/ss_test
TEST_TIMEOUT: 60
```

### End-to-End Test Scenarios

| ID | Scenario | Flow | Input | Expected Output |
|----|----------|------|-------|-----------------|
| E5-INT-01 | Entity Migration | SS KG → IB | All SS entities | 100% entity migration |
| E5-INT-02 | Relationship Migration | SS KG → IB | All SS relationships | 100% relationship migration |
| E5-INT-03 | Context Integration | Context → IB Entity | Context JSON | Linked entity in IB |
| E5-INT-04 | Query Parity | Same query both systems | Test queries | Equivalent results |
| E5-INT-05 | Parallel Operation | Both systems active | Live operations | Results match |
| E5-INT-06 | Rollback Procedure | IB → Legacy | Failure scenario | Clean rollback |
| E5-INT-07 | Performance Validation | IB-only operation | Load test | < 200ms API |

### Test Data Fixtures

```
tests/
├── fixtures/
│   └── smart_scaffold/
│       ├── legacy_kg/
│       │   ├── sample_entities.json       # 1000 test entities
│       │   ├── sample_relationships.json  # 2000 test relationships
│       │   └── expected_migration.json    # Expected IB state
│       ├── context/
│       │   ├── sample_context.json        # Test context records
│       │   └── expected_entities.json     # Expected IB entities from context
│       └── queries/
│           ├── test_queries.json          # 20 test queries
│           └── expected_results.json      # Expected results per query
```

### Migration Test Fixtures

```python
# tests/integration/conftest.py
import pytest
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "smart_scaffold"


@pytest.fixture(scope="session")
def legacy_kg_data():
    """Load legacy KG test data."""
    entities = json.loads((FIXTURES / "legacy_kg" / "sample_entities.json").read_text())
    relationships = json.loads((FIXTURES / "legacy_kg" / "sample_relationships.json").read_text())
    return {"entities": entities, "relationships": relationships}


@pytest.fixture(scope="session")
async def populated_legacy_kg(legacy_kg_client, legacy_kg_data):
    """Populate legacy KG with test data."""
    for entity in legacy_kg_data["entities"]:
        await legacy_kg_client.create_node(
            labels=[entity["type"]],
            properties=entity["properties"]
        )

    for rel in legacy_kg_data["relationships"]:
        await legacy_kg_client.create_relationship(
            source_id=rel["source"],
            target_id=rel["target"],
            rel_type=rel["type"],
            properties=rel.get("properties", {})
        )

    return legacy_kg_client


@pytest.fixture(scope="session")
def test_queries():
    """Load test queries for parity testing."""
    return json.loads((FIXTURES / "queries" / "test_queries.json").read_text())


@pytest.fixture(scope="session")
def expected_results():
    """Load expected results for test queries."""
    return json.loads((FIXTURES / "queries" / "expected_results.json").read_text())
```

### Integration Test Implementation

```python
# tests/integration/test_epic5_migration.py
"""Epic 5 Integration Tests - Smart-Scaffold Migration"""

import pytest
from httpx import AsyncClient


class TestEntityMigration:
    """E5-INT-01: Entity migration from legacy KG to IB."""

    @pytest.mark.asyncio
    async def test_all_entities_migrated(
        self, populated_legacy_kg, migration_script, ib_client
    ):
        """All entities from legacy KG are migrated to IB."""
        # Count entities in legacy
        legacy_count = await populated_legacy_kg.count_nodes()

        # Run migration
        result = await migration_script.migrate_entities()

        assert result["migrated"] == legacy_count
        assert result["failed"] == 0

        # Verify in IB
        ib_count = await ib_client.entities.count(domain="development")
        assert ib_count >= legacy_count

    @pytest.mark.asyncio
    async def test_entity_properties_preserved(
        self, populated_legacy_kg, migration_script, ib_client
    ):
        """Entity properties are correctly preserved during migration."""
        # Get sample entity from legacy
        legacy_entity = await populated_legacy_kg.get_node("issue-001")

        # Run migration
        await migration_script.migrate_entities()

        # Verify properties in IB
        ib_entity = await ib_client.entities.get(
            domain="development",
            entity_id="issue-001"
        )

        assert ib_entity.properties["title"] == legacy_entity["title"]
        assert ib_entity.properties["status"] == legacy_entity["status"]
        assert ib_entity.properties["created_at"] == legacy_entity["created_at"]

    @pytest.mark.asyncio
    async def test_entity_type_mapping(
        self, populated_legacy_kg, migration_script, ib_client
    ):
        """Legacy entity types are correctly mapped to IB types."""
        type_mapping = {
            "Issue": "github_issue",
            "PullRequest": "pull_request",
            "Commit": "commit",
            "File": "code_file",
        }

        await migration_script.migrate_entities()

        for legacy_type, ib_type in type_mapping.items():
            legacy_count = await populated_legacy_kg.count_nodes(label=legacy_type)
            ib_count = await ib_client.entities.count(
                domain="development",
                entity_type=ib_type
            )
            assert ib_count == legacy_count, f"Mismatch for {legacy_type} -> {ib_type}"


class TestRelationshipMigration:
    """E5-INT-02: Relationship migration from legacy KG to IB."""

    @pytest.mark.asyncio
    async def test_all_relationships_migrated(
        self, populated_legacy_kg, migration_script, ib_client
    ):
        """All relationships from legacy KG are migrated to IB."""
        # Count relationships in legacy
        legacy_count = await populated_legacy_kg.count_relationships()

        # Run migration (entities first, then relationships)
        await migration_script.migrate_entities()
        result = await migration_script.migrate_relationships()

        assert result["migrated"] == legacy_count
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_relationship_type_mapping(
        self, populated_legacy_kg, migration_script, ib_client
    ):
        """Legacy relationship types map correctly to IB."""
        type_mapping = {
            "IMPLEMENTS": "implements",
            "TESTS": "tests",
            "MODIFIES": "modifies",
            "REFERENCES": "references",
        }

        await migration_script.migrate_entities()
        await migration_script.migrate_relationships()

        for legacy_type, ib_type in type_mapping.items():
            ib_rels = await ib_client.relationships.search(
                relationship_type=ib_type
            )
            # Verify at least some relationships of each type
            legacy_rels = await populated_legacy_kg.count_relationships(type=legacy_type)
            assert len(ib_rels) == legacy_rels


class TestContextIntegration:
    """E5-INT-03: Context system integration with IB."""

    @pytest.mark.asyncio
    async def test_context_creates_entity(
        self, ss_client: AsyncClient, ib_client
    ):
        """Creating context also creates linked entity in IB."""
        # Create context in SS
        response = await ss_client.post(
            "/api/v1/context",
            json={
                "type": "issue_context",
                "content": {"issue_number": 123, "title": "Test Issue"},
                "metadata": {"repo": "test/repo"}
            }
        )

        assert response.status_code == 201
        context_id = response.json()["id"]

        # Verify entity created in IB
        entities = await ib_client.entities.search(
            domain="development",
            filters={"properties.context_id": context_id}
        )
        assert len(entities) == 1
        assert entities[0].properties["issue_number"] == 123

    @pytest.mark.asyncio
    async def test_context_sync_bidirectional(
        self, ss_client: AsyncClient, ib_client
    ):
        """Context updates sync bidirectionally with IB."""
        # Create context
        response = await ss_client.post(
            "/api/v1/context",
            json={
                "type": "issue_context",
                "content": {"issue_number": 456, "status": "open"}
            }
        )
        context_id = response.json()["id"]

        # Update via IB
        entity = (await ib_client.entities.search(
            domain="development",
            filters={"properties.context_id": context_id}
        ))[0]

        await ib_client.entities.update(
            entity_id=entity.id,
            properties={"status": "closed"}
        )

        # Verify context updated in SS
        context = await ss_client.get(f"/api/v1/context/{context_id}")
        assert context.json()["content"]["status"] == "closed"


class TestQueryParity:
    """E5-INT-04: Query result parity between systems."""

    @pytest.mark.asyncio
    async def test_text_search_parity(
        self, populated_legacy_kg, ib_client, ss_client
    ):
        """Text search returns equivalent results from both systems."""
        query = "authentication bug fix"

        # Query legacy
        legacy_results = await populated_legacy_kg.text_search(query)

        # Query IB via SS
        response = await ss_client.get(
            "/api/v1/search",
            params={"q": query, "backend": "ib"}
        )
        ib_results = response.json()["results"]

        # Results should be equivalent (same entities, may differ in order)
        legacy_ids = {r["id"] for r in legacy_results}
        ib_ids = {r["id"] for r in ib_results}

        # Allow small variance (IB may have better vector search)
        overlap = len(legacy_ids & ib_ids) / max(len(legacy_ids), len(ib_ids))
        assert overlap >= 0.8, f"Result overlap {overlap:.1%} < 80%"

    @pytest.mark.asyncio
    async def test_graph_traversal_parity(
        self, populated_legacy_kg, ib_client, test_queries, expected_results
    ):
        """Graph traversal queries return equivalent results."""
        for query_name, query_def in test_queries.items():
            if query_def["type"] != "traversal":
                continue

            # Execute on legacy
            legacy_result = await populated_legacy_kg.traverse(
                start_id=query_def["start"],
                max_depth=query_def["depth"],
                relationship_types=query_def.get("rel_types")
            )

            # Execute on IB
            ib_result = await ib_client.graph.traverse(
                start_entity_id=query_def["start"],
                max_depth=query_def["depth"],
                relationship_types=query_def.get("rel_types")
            )

            # Compare node sets
            legacy_nodes = {n["id"] for n in legacy_result["nodes"]}
            ib_nodes = {n.id for n in ib_result.nodes}

            assert legacy_nodes == ib_nodes, f"Mismatch for query: {query_name}"


class TestParallelOperation:
    """E5-INT-05: Parallel operation of both systems."""

    @pytest.mark.asyncio
    async def test_dual_write_consistency(
        self, ss_client: AsyncClient, populated_legacy_kg, ib_client
    ):
        """Writes go to both systems during parallel operation."""
        # Enable parallel mode
        await ss_client.post("/api/v1/config", json={"parallel_mode": True})

        # Create new entity via SS
        response = await ss_client.post(
            "/api/v1/issues",
            json={"title": "Test Parallel Issue", "body": "Testing dual write"}
        )
        new_id = response.json()["id"]

        # Verify in legacy
        legacy_entity = await populated_legacy_kg.get_node(new_id)
        assert legacy_entity is not None
        assert legacy_entity["title"] == "Test Parallel Issue"

        # Verify in IB
        ib_entity = await ib_client.entities.get(
            domain="development",
            entity_id=new_id
        )
        assert ib_entity is not None
        assert ib_entity.properties["title"] == "Test Parallel Issue"

    @pytest.mark.asyncio
    async def test_discrepancy_logging(
        self, ss_client: AsyncClient, populated_legacy_kg, ib_client
    ):
        """Discrepancies between systems are logged."""
        # Enable parallel mode with discrepancy logging
        await ss_client.post("/api/v1/config", json={
            "parallel_mode": True,
            "log_discrepancies": True
        })

        # Manually create discrepancy (entity in one but not other)
        await ib_client.entities.create(
            domain="development",
            entity_type="github_issue",
            entity_id="discrepancy-test",
            properties={"title": "IB Only Issue"}
        )

        # Query that should detect discrepancy
        response = await ss_client.get(
            "/api/v1/search",
            params={"q": "discrepancy-test"}
        )

        # Check discrepancy log
        log_response = await ss_client.get("/api/v1/admin/discrepancies")
        discrepancies = log_response.json()["discrepancies"]

        assert any(d["entity_id"] == "discrepancy-test" for d in discrepancies)


class TestRollbackProcedure:
    """E5-INT-06: Rollback procedure validation."""

    @pytest.mark.asyncio
    async def test_rollback_restores_legacy_operation(
        self, ss_client: AsyncClient, populated_legacy_kg
    ):
        """Rollback switches back to legacy KG cleanly."""
        # Start in IB mode
        await ss_client.post("/api/v1/config", json={"backend": "ib"})

        # Create entity in IB mode
        response = await ss_client.post(
            "/api/v1/issues",
            json={"title": "IB Mode Issue"}
        )
        ib_issue_id = response.json()["id"]

        # Trigger rollback
        rollback_response = await ss_client.post("/api/v1/admin/rollback")
        assert rollback_response.status_code == 200

        # Verify now using legacy
        config = await ss_client.get("/api/v1/config")
        assert config.json()["backend"] == "legacy"

        # Legacy queries should work
        legacy_results = await ss_client.get("/api/v1/issues")
        assert legacy_results.status_code == 200

    @pytest.mark.asyncio
    async def test_rollback_preserves_data(
        self, ss_client: AsyncClient, populated_legacy_kg, ib_client
    ):
        """Rollback does not lose any data."""
        # Get counts before operations
        initial_legacy_count = await populated_legacy_kg.count_nodes()

        # Switch to IB, create some data, then rollback
        await ss_client.post("/api/v1/config", json={"backend": "ib"})

        for i in range(5):
            await ss_client.post(
                "/api/v1/issues",
                json={"title": f"Test Issue {i}"}
            )

        await ss_client.post("/api/v1/admin/rollback")

        # Legacy should have all original data
        final_legacy_count = await populated_legacy_kg.count_nodes()
        assert final_legacy_count >= initial_legacy_count


class TestPerformanceValidation:
    """E5-INT-07: Performance requirements validation."""

    @pytest.mark.asyncio
    async def test_api_response_under_200ms(
        self, ss_client: AsyncClient, seeded_ib_data
    ):
        """API responses complete within 200ms."""
        import time

        endpoints = [
            "/api/v1/issues",
            "/api/v1/issues/123",
            "/api/v1/search?q=test",
            "/api/v1/graph/traverse?start=issue-001&depth=2",
        ]

        for endpoint in endpoints:
            start = time.perf_counter()
            response = await ss_client.get(endpoint)
            elapsed = (time.perf_counter() - start) * 1000  # ms

            assert response.status_code in [200, 404], f"Endpoint {endpoint} failed"
            assert elapsed < 200, f"Endpoint {endpoint} took {elapsed:.1f}ms > 200ms"

    @pytest.mark.asyncio
    async def test_entity_creation_under_50ms(
        self, ss_client: AsyncClient, ib_client
    ):
        """Entity creation completes within 50ms."""
        import time

        times = []
        for i in range(10):
            start = time.perf_counter()
            await ss_client.post(
                "/api/v1/issues",
                json={"title": f"Performance Test {i}", "body": "Test body"}
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        assert avg_time < 50, f"Average creation time {avg_time:.1f}ms > 50ms"

    @pytest.mark.asyncio
    async def test_graph_traversal_under_100ms(
        self, ss_client: AsyncClient, seeded_ib_data
    ):
        """Graph traversal completes within 100ms."""
        import time

        start = time.perf_counter()
        response = await ss_client.get(
            "/api/v1/graph/traverse",
            params={"start": "issue-001", "depth": 3}
        )
        elapsed = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert elapsed < 100, f"Traversal took {elapsed:.1f}ms > 100ms"

    @pytest.mark.asyncio
    async def test_vector_search_under_150ms(
        self, ss_client: AsyncClient, seeded_ib_data
    ):
        """Vector search completes within 150ms."""
        import time

        start = time.perf_counter()
        response = await ss_client.get(
            "/api/v1/search/similar",
            params={"text": "authentication security vulnerability fix"}
        )
        elapsed = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert elapsed < 150, f"Vector search took {elapsed:.1f}ms > 150ms"
```

### Data Integrity Validation Tests

```python
# tests/integration/test_epic5_integrity.py
"""Data integrity validation tests for cutover."""

import pytest
import random


class TestDataIntegrity:
    """Validate data integrity during and after migration."""

    @pytest.mark.asyncio
    async def test_entity_count_verification(
        self, populated_legacy_kg, migration_script, ib_client
    ):
        """Entity counts match between systems."""
        # Get legacy counts by type
        legacy_counts = await populated_legacy_kg.count_by_type()

        # Run migration
        await migration_script.migrate_all()

        # Get IB counts by type
        ib_counts = await ib_client.entities.count_by_type(domain="development")

        for entity_type, legacy_count in legacy_counts.items():
            ib_type = migration_script.type_mapping.get(entity_type, entity_type)
            ib_count = ib_counts.get(ib_type, 0)

            assert legacy_count == ib_count, \
                f"Count mismatch for {entity_type}: Legacy={legacy_count}, IB={ib_count}"

    @pytest.mark.asyncio
    async def test_relationship_count_verification(
        self, populated_legacy_kg, migration_script, ib_client
    ):
        """Relationship counts match between systems."""
        legacy_counts = await populated_legacy_kg.count_relationships_by_type()

        await migration_script.migrate_all()

        ib_counts = await ib_client.relationships.count_by_type()

        for rel_type, legacy_count in legacy_counts.items():
            ib_type = migration_script.rel_type_mapping.get(rel_type, rel_type)
            ib_count = ib_counts.get(ib_type, 0)

            assert legacy_count == ib_count, \
                f"Relationship mismatch for {rel_type}: Legacy={legacy_count}, IB={ib_count}"

    @pytest.mark.asyncio
    async def test_random_sample_validation(
        self, populated_legacy_kg, migration_script, ib_client
    ):
        """Random sample of 100 entities validates correctly."""
        await migration_script.migrate_all()

        # Get all legacy entity IDs
        all_ids = await populated_legacy_kg.get_all_ids()

        # Sample 100 (or all if < 100)
        sample_size = min(100, len(all_ids))
        sample_ids = random.sample(all_ids, sample_size)

        mismatches = []
        for entity_id in sample_ids:
            legacy_entity = await populated_legacy_kg.get_node(entity_id)
            ib_entity = await ib_client.entities.get(
                domain="development",
                entity_id=entity_id
            )

            if not self._entities_match(legacy_entity, ib_entity):
                mismatches.append({
                    "id": entity_id,
                    "legacy": legacy_entity,
                    "ib": ib_entity.properties if ib_entity else None
                })

        assert len(mismatches) == 0, \
            f"Found {len(mismatches)} mismatches in sample: {mismatches[:5]}"

    def _entities_match(self, legacy, ib):
        """Compare legacy and IB entity properties."""
        if legacy is None or ib is None:
            return legacy is None and ib is None

        # Compare key properties
        for key in ["title", "status", "created_at"]:
            if key in legacy and legacy[key] != ib.properties.get(key):
                return False
        return True
```

### Performance Benchmarks

| Metric | Requirement | Pre-Cutover | Post-Cutover |
|--------|-------------|-------------|--------------|
| API Response | < 200ms | Measure | Verify |
| Entity Create | < 50ms | Measure | Verify |
| Graph Traversal | < 100ms | Measure | Verify |
| Vector Search | < 150ms | Measure | Verify |
| Migration (5K entities) | < 5 min | N/A | Measure |

### CI Integration

```yaml
# .github/workflows/integration-tests.yml
epic5-integration:
  needs: [epic4-integration]
  runs-on: ubuntu-latest
  services:
    localstack:
      image: localstack/localstack:latest
      ports:
        - 4566:4566
    memgraph:
      image: memgraph/memgraph:latest
      ports:
        - 7687:7687
    ib-platform:
      image: intelligence-builder:latest
      ports:
        - 8000:8000
    postgres:
      image: postgres:15
      env:
        POSTGRES_DB: ss_test
        POSTGRES_USER: test
        POSTGRES_PASSWORD: test
      ports:
        - 5432:5432

  steps:
    - uses: actions/checkout@v4
    - run: pip install -r requirements-test.txt
    - run: |
        # Start Smart-Scaffold in test mode
        cd smart-scaffold && python -m smart_scaffold.main --test-mode &
        sleep 10
    - run: pytest tests/integration/test_epic5_*.py -v --tb=short

cutover-validation:
  needs: [epic5-integration]
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main'
  steps:
    - uses: actions/checkout@v4
    - run: pip install -r requirements-test.txt
    - run: |
        # Run full cutover validation suite
        pytest tests/integration/test_epic5_integrity.py -v
        pytest tests/integration/test_epic5_migration.py::TestPerformanceValidation -v
```
