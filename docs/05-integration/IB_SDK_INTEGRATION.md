# Intelligence-Builder SDK Integration Guide

**Version:** 1.0.0
**Last Updated:** 2025-11-29
**Audience:** Developers integrating Cloud Optimizer with Intelligence-Builder

---

## Overview

Cloud Optimizer uses Intelligence-Builder (IB) Platform components for:
- **Graph Database Operations** - Entity and relationship storage
- **Pattern Detection** - Security, cost, and compliance pattern matching
- **Domain Modules** - Pluggable domain-specific logic

This guide covers how to use these components effectively.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLOUD OPTIMIZER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Your Service Code                         │ │
│  │  from ib_platform.graph import GraphBackendFactory          │ │
│  │  from ib_platform.patterns import PatternDetector           │ │
│  │  from ib_platform.domains import SecurityDomain             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    IB Platform Layer                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │ │
│  │  │    Graph     │  │   Patterns   │  │     Domains      │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │  PostgreSQL/Memgraph │
                    └─────────────────────┘
```

---

## Quick Start

### 1. Import Components

```python
# Graph operations
from ib_platform.graph import (
    GraphBackendFactory,
    GraphNode,
    GraphEdge,
    TraversalParams,
    TraversalDirection,
)

# Pattern detection
from ib_platform.patterns import (
    PatternDetector,
    PatternRegistry,
    PatternModel,
)

# Domain modules
from ib_platform.domains import (
    DomainRegistry,
    SecurityDomain,
)
```

### 2. Initialize Backend

```python
import asyncpg

# Create connection pool
pool = await asyncpg.create_pool(
    host="localhost",
    port=5434,
    user="test",
    password="test",
    database="test_intelligence",
)

# Create backend via factory
backend = await GraphBackendFactory.create_async(
    backend_type="postgres",
    connection_pool=pool,
    schema="intelligence",
)

# Connect
await backend.connect()
```

### 3. Basic Operations

```python
# Create a node
node = await backend.create_node(
    labels=["Vulnerability", "Security"],
    properties={
        "cve_id": "CVE-2021-44228",
        "severity": "critical",
        "cvss_score": 10.0,
    }
)

# Create a relationship
edge = await backend.create_edge(
    source_id=vulnerability_node.id,
    target_id=resource_node.id,
    edge_type="AFFECTS",
    properties={"discovered_at": "2025-11-29"},
)

# Traverse the graph
params = TraversalParams(
    max_depth=3,
    direction=TraversalDirection.OUTGOING,
    edge_types=["AFFECTS", "MITIGATES"],
)
connected_nodes = await backend.traverse(node.id, params)
```

---

## Graph Backend Usage

### Creating Nodes

```python
from uuid import uuid4

# Simple node
node = await backend.create_node(
    labels=["Entity"],
    properties={"name": "Test Node"},
)

# Node with specific ID
node = await backend.create_node(
    labels=["Entity"],
    properties={"name": "Specific Node"},
    node_id=uuid4(),
)

# Batch create (efficient for 100+ nodes)
nodes_data = [
    {"labels": ["Entity"], "properties": {"name": f"Node {i}"}}
    for i in range(1000)
]
nodes = await backend.batch_create_nodes(nodes_data)
```

### Creating Edges

```python
# Basic edge
edge = await backend.create_edge(
    source_id=source_node.id,
    target_id=target_node.id,
    edge_type="CONNECTS_TO",
)

# Edge with properties
edge = await backend.create_edge(
    source_id=source_node.id,
    target_id=target_node.id,
    edge_type="DEPENDS_ON",
    properties={
        "strength": 0.8,
        "created_by": "security_scanner",
    },
    weight=0.8,
    confidence=0.95,
)
```

### Traversing Graphs

```python
from ib_platform.graph import TraversalParams, TraversalDirection

# Outgoing traversal
params = TraversalParams(
    max_depth=3,
    direction=TraversalDirection.OUTGOING,
)
downstream_nodes = await backend.traverse(start_node.id, params)

# Filtered traversal
params = TraversalParams(
    max_depth=5,
    direction=TraversalDirection.BOTH,
    edge_types=["AFFECTS", "DEPENDS_ON"],
    node_labels=["Vulnerability", "Resource"],
    limit=100,
)
filtered_nodes = await backend.traverse(start_node.id, params)
```

### Finding Paths

```python
# Shortest path
path = await backend.find_shortest_path(
    start_id=source_node.id,
    end_id=target_node.id,
    max_depth=10,
)
if path:
    print(f"Path length: {len(path.nodes)}")
    for node in path.nodes:
        print(f"  -> {node.properties.get('name')}")

# All paths (for analysis)
paths = await backend.find_all_paths(
    start_id=source_node.id,
    end_id=target_node.id,
    max_depth=5,
    limit=10,
)
```

---

## Pattern Detection

### Registering Patterns

```python
from ib_platform.patterns import PatternRegistry, PatternModel

registry = PatternRegistry()

# Register a security pattern
pattern = PatternModel(
    name="cve_reference",
    domain="security",
    category="entity",
    regex_pattern=r"CVE-\d{4}-\d{4,7}",
    output_type="vulnerability",
    base_confidence=0.9,
)
registry.register(pattern)
```

### Detecting Patterns

```python
from ib_platform.patterns import PatternDetector

detector = PatternDetector(registry=registry)

# Detect patterns in text
text = "Found CVE-2021-44228 affecting production servers"
matches = await detector.detect(text, domain="security")

for match in matches:
    print(f"Pattern: {match.pattern_name}")
    print(f"Match: {match.matched_text}")
    print(f"Confidence: {match.confidence}")
```

---

## Domain Modules

### Using SecurityDomain

```python
from ib_platform.domains import SecurityDomain

domain = SecurityDomain()

# Validate entity data
entity_data = {
    "name": "CVE-2021-44228",
    "cve_id": "CVE-2021-44228",
    "severity": "critical",
}
errors = domain.validate_entity("vulnerability", entity_data)
if errors:
    print(f"Validation errors: {errors}")

# Validate relationship
errors = domain.validate_relationship(
    rel_type="EXPLOITS",
    source_type="threat",
    target_type="vulnerability",
)
```

### Available Entity Types (SecurityDomain)

| Entity Type | Required Properties | Description |
|-------------|---------------------|-------------|
| vulnerability | name, cve_id | CVE or security vulnerability |
| threat | name, threat_type | Threat actor or threat |
| control | name, control_type | Security control |
| identity | name, identity_type | User, role, or service account |
| compliance_standard | name | Compliance framework |
| asset | name, asset_type | Cloud resource or asset |
| incident | name | Security incident |
| risk_assessment | name | Risk assessment record |
| finding | name | Security finding |

### Available Relationship Types

| Relationship | Source Types | Target Types |
|--------------|--------------|--------------|
| EXPLOITS | threat | vulnerability |
| MITIGATES | control | vulnerability, threat |
| HAS_ACCESS_TO | identity | asset |
| REQUIRES_COMPLIANCE | asset | compliance_standard |
| DETECTED_IN | vulnerability | asset |
| TRIGGERS | incident | finding |
| ASSESSED_BY | asset | risk_assessment |

---

## Best Practices

### 1. Use Context Managers

```python
# Good - proper resource cleanup
async with backend:
    node = await backend.create_node(...)

# Or manually
await backend.connect()
try:
    node = await backend.create_node(...)
finally:
    await backend.disconnect()
```

### 2. Batch Operations for Scale

```python
# Good - batch for many items
nodes = await backend.batch_create_nodes(nodes_data)  # 1000 nodes in ~2s

# Bad - individual creates
for data in nodes_data:
    await backend.create_node(**data)  # 1000 nodes in ~30s
```

### 3. Use Appropriate Traversal Depth

```python
# Good - reasonable depth for most use cases
params = TraversalParams(max_depth=3)

# Bad - excessive depth can be slow
params = TraversalParams(max_depth=100)  # Very slow
```

### 4. Filter Early

```python
# Good - filter in query
params = TraversalParams(
    edge_types=["AFFECTS"],  # Only specific edges
    node_labels=["Vulnerability"],  # Only specific nodes
    limit=100,  # Limit results
)

# Bad - fetch all, filter in Python
all_nodes = await backend.traverse(start, TraversalParams(max_depth=10))
filtered = [n for n in all_nodes if "Vulnerability" in n.labels]  # Inefficient
```

---

## Error Handling

```python
from ib_platform.graph.protocol import (
    GraphConnectionError,
    NodeNotFoundError,
    EdgeNotFoundError,
    TraversalError,
)

try:
    node = await backend.get_node(node_id)
    if node is None:
        # Handle missing node
        pass
except GraphConnectionError as e:
    # Handle connection issues
    logger.error(f"Database connection failed: {e}")
except TraversalError as e:
    # Handle traversal failures
    logger.error(f"Traversal failed: {e}")
```

---

## Testing Integration

```python
import pytest
from ib_platform.graph import PostgresCTEBackend

@pytest.fixture
async def backend(asyncpg_pool):
    """Real backend for integration tests."""
    backend = PostgresCTEBackend(
        connection_pool=asyncpg_pool,
        schema="intelligence",
    )
    await backend.connect()
    yield backend
    # Cleanup
    async with asyncpg_pool.acquire() as conn:
        await conn.execute("DELETE FROM intelligence.relationships")
        await conn.execute("DELETE FROM intelligence.entities")
    await backend.disconnect()

@pytest.mark.asyncio
async def test_create_and_traverse(backend):
    """Test creating nodes and traversing."""
    # Create nodes
    node1 = await backend.create_node(["Entity"], {"name": "Node1"})
    node2 = await backend.create_node(["Entity"], {"name": "Node2"})

    # Create edge
    await backend.create_edge(node1.id, node2.id, "CONNECTS")

    # Traverse
    params = TraversalParams(max_depth=1)
    connected = await backend.traverse(node1.id, params)

    assert len(connected) == 1
    assert connected[0].id == node2.id
```

---

## Related Documentation

- [DOMAIN_PATTERNS.md](./DOMAIN_PATTERNS.md) - Domain-specific patterns
- [ARCHITECTURE.md](../02-architecture/ARCHITECTURE.md) - System architecture
- [TESTING_GUIDE.md](../03-development/TESTING_GUIDE.md) - Testing guide
