# Epic 1: Platform Foundation

## Overview

Build the core platform infrastructure for Intelligence-Builder that enables Cloud Optimizer v2 to consume GraphRAG capabilities via SDK.

**Priority**: Critical
**Dependencies**: None

## Objectives

1. Create a unified graph database abstraction layer supporting PostgreSQL CTE and Memgraph backends
2. Build the pattern detection engine as a core platform capability
3. Implement the pluggable domain module system for extensibility

## Deliverables

### 1.1 Graph Database Abstraction Layer
- GraphBackendProtocol - Abstract interface for graph operations
- PostgresCTEBackend - CTE-based implementation
- MemgraphBackend - Native Cypher implementation
- GraphBackendFactory - Backend instantiation and switching

### 1.2 Pattern Engine Core
- PatternDefinition - Pattern specification model
- PatternRegistry - Pattern storage and lookup
- PatternMatcher - Text pattern matching engine
- ConfidenceScorer - Multi-factor confidence scoring
- PatternDetector - Main detection orchestrator

### 1.3 Domain Module System
- BaseDomain - Abstract domain class
- DomainRegistry - Domain registration and discovery
- EntityTypeDefinition - Entity type specification
- RelationshipTypeDefinition - Relationship type specification
- DomainLoader - Dynamic domain loading

## Acceptance Criteria

- [ ] All protocol methods implemented for both graph backends
- [ ] Unit test coverage > 80%
- [ ] Integration tests passing for both backends
- [ ] Performance within 20% parity between backends
- [ ] Configuration-based backend switching works
- [ ] Pattern matching performance < 20ms per KB
- [ ] Confidence scoring accuracy > 85% on test set
- [ ] Domain registration works without platform restart
- [ ] Entity/relationship type validation enforced

## Technical Details

See `docs/platform/TECHNICAL_DESIGN.md` for implementation specifications.

## Sub-Tasks

- #6 - 1.1 Graph Database Abstraction Layer
- #7 - 1.2 Pattern Engine Core
- #8 - 1.3 Domain Module System

---

## Integration Test Specification

### Test Environment

| Component | Configuration | Notes |
|-----------|---------------|-------|
| PostgreSQL | localhost:5432/test_intelligence | Fresh schema per test run |
| Memgraph | localhost:7687 | Empty graph per test run |
| Python | 3.11+ | pytest-asyncio required |

```yaml
# tests/integration/conftest.py environment
TEST_POSTGRES_URL: postgresql://test:test@localhost:5432/test_intelligence
TEST_MEMGRAPH_URI: bolt://localhost:7687
TEST_SCHEMA: intelligence_test
```

### End-to-End Test Scenarios

| ID | Scenario | Components | Input | Expected Output |
|----|----------|------------|-------|-----------------|
| E1-INT-01 | Graph Backend Parity | PostgresCTE, Memgraph | Create 100 nodes, 200 edges | Identical query results from both |
| E1-INT-02 | Full Traversal Flow | GraphBackend → API | Start node + depth 3 | Correct subgraph returned |
| E1-INT-03 | Pattern Detection Pipeline | PatternMatcher → Scorer → Detector | 10KB security document | Entities with confidence scores |
| E1-INT-04 | Domain Hot Registration | DomainRegistry → PatternRegistry | New domain module | Patterns available without restart |
| E1-INT-05 | Backend Switching | Factory → Both Backends | Same operations | Results match within tolerance |

### Test Data Fixtures

```
tests/
├── fixtures/
│   ├── graph/
│   │   ├── sample_nodes_100.json      # 100 test nodes
│   │   ├── sample_edges_200.json      # 200 test relationships
│   │   └── expected_traversal.json    # Expected traversal results
│   ├── patterns/
│   │   ├── test_document_10kb.txt     # Sample document for pattern detection
│   │   ├── expected_matches.json      # Expected pattern matches
│   │   └── confidence_test_cases.json # Confidence scoring test cases
│   └── domains/
│       ├── test_domain/               # Sample domain for registration test
│       │   ├── __init__.py
│       │   └── domain.py
│       └── expected_registration.json
```

### Integration Test Implementation

```python
# tests/integration/test_epic1_platform.py
"""Epic 1 Integration Tests - Platform Foundation"""

import pytest
from uuid import uuid4

class TestGraphBackendParity:
    """E1-INT-01: Verify PostgresCTE and Memgraph produce identical results."""

    @pytest.fixture
    async def populated_backends(self, postgres_backend, memgraph_backend, sample_nodes, sample_edges):
        """Populate both backends with identical data."""
        for node in sample_nodes:
            await postgres_backend.create_node(**node)
            await memgraph_backend.create_node(**node)
        for edge in sample_edges:
            await postgres_backend.create_edge(**edge)
            await memgraph_backend.create_edge(**edge)
        return postgres_backend, memgraph_backend

    @pytest.mark.asyncio
    async def test_traversal_results_match(self, populated_backends):
        """Both backends return same nodes for identical traversal."""
        pg, mg = populated_backends
        start_node = "node-001"

        pg_result = await pg.traverse(start_node, max_depth=3)
        mg_result = await mg.traverse(start_node, max_depth=3)

        pg_ids = {n.id for n in pg_result}
        mg_ids = {n.id for n in mg_result}
        assert pg_ids == mg_ids, f"Mismatch: PG={len(pg_ids)}, MG={len(mg_ids)}"

    @pytest.mark.asyncio
    async def test_shortest_path_match(self, populated_backends):
        """Both backends find same shortest path."""
        pg, mg = populated_backends

        pg_path = await pg.find_shortest_path("node-001", "node-050")
        mg_path = await mg.find_shortest_path("node-001", "node-050")

        assert pg_path.length == mg_path.length
        assert [n.id for n in pg_path.nodes] == [n.id for n in mg_path.nodes]


class TestPatternDetectionPipeline:
    """E1-INT-03: Full pattern detection flow."""

    @pytest.mark.asyncio
    async def test_document_to_entities(self, pattern_detector, test_document):
        """Pattern detection produces expected entities with confidence."""
        results = pattern_detector.process_document(
            document_text=test_document,
            document_id=uuid4(),
            domains=["security"]
        )

        assert results["entities_found"] >= 5
        assert all(e["confidence"] >= 0.5 for e in results["entities"])
        assert any(e["type"] == "vulnerability" for e in results["entities"])

    @pytest.mark.asyncio
    async def test_confidence_scoring_accuracy(self, pattern_detector, confidence_test_cases):
        """Confidence scoring meets 85% accuracy target."""
        correct = 0
        for case in confidence_test_cases:
            result = pattern_detector.detect_patterns(case["text"], min_confidence=0.0)
            if result and abs(result[0].final_confidence - case["expected_confidence"]) < 0.1:
                correct += 1

        accuracy = correct / len(confidence_test_cases)
        assert accuracy >= 0.85, f"Confidence accuracy {accuracy:.1%} < 85%"


class TestDomainHotRegistration:
    """E1-INT-04: Domain registration without restart."""

    @pytest.mark.asyncio
    async def test_register_new_domain_patterns_available(self, domain_registry, pattern_registry):
        """New domain's patterns become available immediately."""
        # Verify pattern not present
        initial_patterns = pattern_registry.get_by_domain("test_domain")
        assert len(initial_patterns) == 0

        # Register new domain
        from tests.fixtures.domains.test_domain import TestDomain
        await domain_registry.register(TestDomain())

        # Verify patterns now available
        new_patterns = pattern_registry.get_by_domain("test_domain")
        assert len(new_patterns) >= 1
```

### Performance Benchmarks

| Operation | Requirement | Test Method | Fixture Size |
|-----------|-------------|-------------|--------------|
| Node creation (batch 1000) | < 2s | `pytest-benchmark` | 1000 nodes |
| Edge creation (batch 1000) | < 2s | `pytest-benchmark` | 1000 edges |
| Traversal depth 3 | < 100ms | Timing assertion | 1000 node graph |
| Shortest path | < 50ms | Timing assertion | 1000 node graph |
| Pattern match 1KB | < 20ms | Timing assertion | 1KB document |
| Pattern match 100KB | < 2s | Timing assertion | 100KB document |

```python
# tests/integration/test_epic1_performance.py
@pytest.mark.benchmark
class TestPerformanceBenchmarks:

    def test_batch_node_creation(self, benchmark, postgres_backend, sample_nodes_1000):
        """Batch create 1000 nodes < 2s."""
        result = benchmark(postgres_backend.batch_create_nodes, sample_nodes_1000)
        assert benchmark.stats["mean"] < 2.0

    def test_traversal_performance(self, benchmark, populated_graph, start_node):
        """Traversal depth 3 < 100ms."""
        result = benchmark(populated_graph.traverse, start_node, max_depth=3)
        assert benchmark.stats["mean"] < 0.1  # 100ms

    def test_pattern_matching_1kb(self, benchmark, pattern_detector, doc_1kb):
        """Pattern matching 1KB < 20ms."""
        result = benchmark(pattern_detector.detect_patterns, doc_1kb)
        assert benchmark.stats["mean"] < 0.02  # 20ms
```

### CI Integration

```yaml
# .github/workflows/integration-tests.yml
epic1-integration:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:15
      env:
        POSTGRES_DB: test_intelligence
        POSTGRES_USER: test
        POSTGRES_PASSWORD: test
    memgraph:
      image: memgraph/memgraph:latest
      ports:
        - 7687:7687

  steps:
    - uses: actions/checkout@v4
    - run: pip install -r requirements-test.txt
    - run: pytest tests/integration/test_epic1_*.py -v --tb=short
```
