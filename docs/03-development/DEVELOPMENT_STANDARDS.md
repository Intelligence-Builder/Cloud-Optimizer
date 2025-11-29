# Development Standards

**Version:** 1.0.0
**Last Updated:** 2025-11-29

---

## Overview

This document defines the coding standards, practices, and quality requirements for Cloud Optimizer development. Following these standards ensures consistent, maintainable, and high-quality code.

---

## Code Quality Requirements

### Mandatory Standards

| Requirement | Standard | Tool |
|-------------|----------|------|
| Code formatting | Black (88 char line length) | `black` |
| Import sorting | isort (Black compatible) | `isort` |
| Type hints | All functions must have type hints | `mypy` |
| Docstrings | Google/NumPy style for public APIs | `interrogate` |
| Test coverage | Minimum 80% per module | `pytest-cov` |
| File length | Maximum 500 lines per file | Manual review |

### Quality Gates

Before any commit:
```bash
# Format code
python -m black src/ tests/
python -m isort src/ tests/

# Check types
python -m mypy src/ --strict

# Run tests
PYTHONPATH=src pytest tests/ --cov=src --cov-report=term-missing

# Verify no syntax errors
python -m py_compile src/**/*.py
```

---

## Coding Patterns

### Type Hints

```python
# Good - fully typed
async def create_node(
    labels: List[str],
    properties: Dict[str, Any],
    node_id: Optional[UUID] = None,
) -> GraphNode:
    """Create a new graph node."""
    ...

# Bad - missing types
async def create_node(labels, properties, node_id=None):
    ...
```

### Async/Await

```python
# Good - proper async usage
async def process_nodes(node_ids: List[UUID]) -> List[GraphNode]:
    tasks = [self.get_node(nid) for nid in node_ids]
    return await asyncio.gather(*tasks)

# Bad - blocking in async context
async def process_nodes(node_ids: List[UUID]) -> List[GraphNode]:
    results = []
    for nid in node_ids:
        results.append(await self.get_node(nid))  # Sequential, not parallel
    return results
```

### Error Handling

```python
# Good - specific exceptions with context
class NodeNotFoundError(Exception):
    """Raised when a graph node is not found."""
    def __init__(self, node_id: UUID):
        self.node_id = node_id
        super().__init__(f"Node not found: {node_id}")

async def get_node(node_id: UUID) -> GraphNode:
    node = await self._fetch_node(node_id)
    if node is None:
        raise NodeNotFoundError(node_id)
    return node

# Bad - generic exceptions
async def get_node(node_id: UUID) -> GraphNode:
    node = await self._fetch_node(node_id)
    if node is None:
        raise Exception("Node not found")  # No context
    return node
```

### Dataclasses

```python
# Good - immutable dataclass with validation
from dataclasses import dataclass, field
from typing import List, Dict, Any
from uuid import UUID, uuid4

@dataclass(frozen=True)
class GraphNode:
    """Represents a node in the knowledge graph."""
    id: UUID = field(default_factory=uuid4)
    labels: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.labels:
            object.__setattr__(self, 'labels', ['Node'])
```

---

## Project Structure

### Source Code Organization

```
src/
├── ib_platform/              # Platform components (DO NOT modify for CO-specific logic)
│   ├── graph/                # Graph database abstraction
│   ├── patterns/             # Pattern detection engine
│   └── domains/              # Domain module system
│
└── cloud_optimizer/          # Application-specific code
    ├── __init__.py
    ├── services/             # Business logic services
    │   ├── __init__.py
    │   ├── security.py       # Security analysis service
    │   ├── cost.py           # Cost analysis service
    │   └── waf.py            # WAF assessment service
    ├── routers/              # API endpoints
    │   ├── __init__.py
    │   ├── security.py
    │   ├── cost.py
    │   └── waf.py
    └── models/               # Data models
        ├── __init__.py
        ├── security.py
        ├── cost.py
        └── waf.py
```

### Test Organization

```
tests/
├── conftest.py               # Shared fixtures
├── ib_platform/              # Platform tests
│   ├── graph/                # Graph backend tests
│   ├── patterns/             # Pattern engine tests
│   └── domains/              # Domain module tests
│
└── cloud_optimizer/          # Application tests
    ├── services/             # Service tests
    ├── routers/              # API tests
    └── integration/          # End-to-end tests
```

---

## Testing Standards

### Test Requirements

1. **No Mocks for Core Logic** - Use real database connections
2. **Descriptive Names** - Test names describe the scenario
3. **Arrange-Act-Assert** - Clear test structure
4. **Fixtures Over Setup** - Use pytest fixtures

### Test Example

```python
import pytest
from uuid import uuid4

class TestGraphNode:
    """Tests for GraphNode operations."""

    @pytest.mark.asyncio
    async def test_create_node_with_labels(self, postgres_backend):
        """Creating a node with labels stores them correctly."""
        # Arrange
        labels = ["TestNode", "Entity"]
        properties = {"name": "Test"}

        # Act
        node = await postgres_backend.create_node(
            labels=labels,
            properties=properties
        )

        # Assert
        assert node.id is not None
        assert node.labels == labels
        assert node.properties["name"] == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_node_returns_none(self, postgres_backend):
        """Getting a nonexistent node returns None."""
        # Act
        node = await postgres_backend.get_node(uuid4())

        # Assert
        assert node is None
```

### Integration Test Requirements

```python
# tests/ib_platform/graph/conftest.py

@pytest_asyncio.fixture(scope="function")
async def postgres_backend(asyncpg_pool):
    """Real PostgreSQL backend for integration tests."""
    backend = PostgresCTEBackend(
        connection_pool=asyncpg_pool,
        schema="intelligence",
    )
    await backend.connect()

    yield backend

    # Cleanup after each test
    async with asyncpg_pool.acquire() as conn:
        await conn.execute("DELETE FROM intelligence.relationships")
        await conn.execute("DELETE FROM intelligence.entities")

    await backend.disconnect()
```

---

## Documentation Standards

### Docstring Format (Google Style)

```python
async def traverse(
    self,
    start_node_id: UUID,
    params: TraversalParams,
) -> List[GraphNode]:
    """Traverse the graph from a starting node.

    Performs a breadth-first traversal of the graph, returning all
    reachable nodes within the specified parameters.

    Args:
        start_node_id: UUID of the starting node.
        params: Traversal configuration including max_depth, direction,
            and optional filters.

    Returns:
        List of GraphNode objects reachable from the start node,
        ordered by traversal depth.

    Raises:
        NodeNotFoundError: If start_node_id doesn't exist.
        TraversalError: If traversal fails due to database issues.

    Example:
        >>> params = TraversalParams(max_depth=3, direction=TraversalDirection.OUTGOING)
        >>> nodes = await backend.traverse(start_id, params)
        >>> print(f"Found {len(nodes)} connected nodes")
    """
    ...
```

### Module Documentation

Each module should have a docstring explaining:
- Purpose of the module
- Key classes/functions
- Usage examples

```python
"""Graph database abstraction layer.

This module provides a unified interface for graph database operations,
supporting multiple backends (PostgreSQL CTE, Memgraph).

Key Components:
    - GraphBackendProtocol: Interface for all backends
    - PostgresCTEBackend: PostgreSQL with recursive CTEs
    - MemgraphBackend: Native Memgraph with Cypher
    - GraphBackendFactory: Factory for backend instantiation

Example:
    >>> from ib_platform.graph import GraphBackendFactory
    >>> backend = await GraphBackendFactory.create("postgres", config)
    >>> node = await backend.create_node(["Entity"], {"name": "Test"})
"""
```

---

## Git Workflow

### Commit Messages

Format:
```
<type>: <description>

<optional body>

<optional footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance

Example:
```
feat: Add vulnerability detection to SecurityDomain

Implements CVE detection patterns and compliance checking
for the security domain module.

Issue: #6
```

### Branch Naming

- `feature/<issue-number>-<short-description>`
- `fix/<issue-number>-<short-description>`
- `docs/<description>`

---

## Security Guidelines

### Never Commit
- API keys or secrets
- Credentials in code
- .env files with real values
- AWS access keys

### Always Use
- Environment variables for secrets
- Parameterized SQL queries
- Input validation
- Output encoding

---

## Related Documentation

- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Detailed testing guide
- [QUALITY_GATES.md](./QUALITY_GATES.md) - Quality gate requirements
- [ARCHITECTURE.md](../02-architecture/ARCHITECTURE.md) - System architecture
