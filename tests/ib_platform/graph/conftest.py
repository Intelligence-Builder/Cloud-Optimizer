"""
Test fixtures for graph backend integration tests.

These fixtures connect to REAL databases (PostgreSQL, Memgraph).
No mocks are used - all tests run against actual infrastructure.

Requirements:
    docker-compose -f docker/docker-compose.test.yml up -d
"""

import asyncio
import os
from typing import AsyncGenerator, List
from uuid import uuid4

import pytest
import pytest_asyncio

from src.ib_platform.graph.backends.memgraph import MemgraphBackend
from src.ib_platform.graph.backends.postgres_cte import PostgresCTEBackend
from src.ib_platform.graph.protocol import (
    GraphEdge,
    GraphNode,
    TraversalDirection,
    TraversalParams,
)

# Test database configuration - uses Docker test containers
POSTGRES_TEST_CONFIG = {
    "host": os.getenv("TEST_POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("TEST_POSTGRES_PORT", "5434")),
    "user": os.getenv("TEST_POSTGRES_USER", "test"),
    "password": os.getenv("TEST_POSTGRES_PASSWORD", "test"),
    "database": os.getenv("TEST_POSTGRES_DB", "test_intelligence"),
}

MEMGRAPH_TEST_CONFIG = {
    "uri": os.getenv("TEST_MEMGRAPH_URI", "bolt://localhost:7688"),
    "username": os.getenv("TEST_MEMGRAPH_USER", ""),
    "password": os.getenv("TEST_MEMGRAPH_PASSWORD", ""),
}


# ============================================================================
# Sample Data Fixtures (no mocks - real data structures)
# ============================================================================


@pytest.fixture
def sample_node_data():
    """Sample node data for testing."""
    return {
        "labels": ["TestNode", "Entity"],
        "properties": {
            "name": "Test Node",
            "description": "A test node for integration testing",
            "custom_field": "custom_value",
        },
    }


@pytest.fixture
def sample_edge_data():
    """Sample edge data for testing."""
    return {
        "edge_type": "TEST_RELATIONSHIP",
        "properties": {
            "weight": 0.8,
            "confidence": 0.9,
            "custom_field": "edge_value",
        },
    }


@pytest.fixture
def sample_graph_nodes():
    """Sample graph nodes for testing."""
    return [
        GraphNode(
            id=uuid4(),
            labels=["Node"],
            properties={"name": f"Node {i}"},
        )
        for i in range(5)
    ]


@pytest.fixture
def sample_graph_edges(sample_graph_nodes):
    """Sample graph edges for testing."""
    edges = []
    for i in range(len(sample_graph_nodes) - 1):
        edges.append(
            GraphEdge(
                id=uuid4(),
                source_id=sample_graph_nodes[i].id,
                target_id=sample_graph_nodes[i + 1].id,
                edge_type="CONNECTS_TO",
                properties={},
                weight=1.0,
                confidence=1.0,
            )
        )
    return edges


@pytest.fixture
def traversal_params():
    """Default traversal parameters."""
    return TraversalParams(
        max_depth=3,
        direction=TraversalDirection.BOTH,
        edge_types=None,
        node_labels=None,
        limit=100,
    )


# ============================================================================
# Real Database Connection Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def asyncpg_pool():
    """
    Create a REAL asyncpg connection pool to PostgreSQL test database.

    This connects to the Docker PostgreSQL container.
    """
    import asyncpg

    try:
        pool = await asyncpg.create_pool(
            host=POSTGRES_TEST_CONFIG["host"],
            port=POSTGRES_TEST_CONFIG["port"],
            user=POSTGRES_TEST_CONFIG["user"],
            password=POSTGRES_TEST_CONFIG["password"],
            database=POSTGRES_TEST_CONFIG["database"],
            min_size=1,
            max_size=5,
        )
        yield pool
        await pool.close()
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest_asyncio.fixture(scope="function")
async def postgres_backend(asyncpg_pool) -> AsyncGenerator[PostgresCTEBackend, None]:
    """
    PostgresCTE backend with REAL database connection.

    Cleans up test data after each test.
    """
    backend = PostgresCTEBackend(
        connection_pool=asyncpg_pool,
        schema="intelligence",
    )
    await backend.connect()

    yield backend

    # Cleanup: Delete all test data after each test
    async with asyncpg_pool.acquire() as conn:
        await conn.execute("DELETE FROM intelligence.relationships")
        await conn.execute("DELETE FROM intelligence.entities")

    await backend.disconnect()


@pytest_asyncio.fixture(scope="function")
async def memgraph_backend() -> AsyncGenerator[MemgraphBackend, None]:
    """
    Memgraph backend with REAL database connection.

    Cleans up test data after each test.
    """
    try:
        backend = MemgraphBackend(
            uri=MEMGRAPH_TEST_CONFIG["uri"],
            username=MEMGRAPH_TEST_CONFIG["username"] or None,
            password=MEMGRAPH_TEST_CONFIG["password"] or None,
        )
        await backend.connect()

        yield backend

        # Cleanup: Delete all test data
        if backend.is_connected:
            try:
                await backend.execute_query("MATCH (n) DETACH DELETE n")
            except Exception:
                pass  # Ignore cleanup errors

        await backend.disconnect()
    except Exception as e:
        pytest.skip(f"Memgraph not available: {e}")


# ============================================================================
# Pre-populated Database Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def populated_postgres_backend(
    postgres_backend,
) -> AsyncGenerator[PostgresCTEBackend, None]:
    """
    PostgresCTE backend pre-populated with test graph data.

    Creates a test graph with:
    - 10 nodes in a chain
    - 9 edges connecting them
    - Additional cross-links for path testing
    """
    nodes = []

    # Create 10 nodes
    for i in range(10):
        node = await postgres_backend.create_node(
            labels=["TestNode"],
            properties={
                "name": f"Node-{i}",
                "index": i,
                "description": f"Test node number {i}",
            },
        )
        nodes.append(node)

    # Create chain edges (0->1->2->...->9)
    for i in range(9):
        await postgres_backend.create_edge(
            source_id=nodes[i].id,
            target_id=nodes[i + 1].id,
            edge_type="NEXT",
            properties={"order": i},
        )

    # Create some cross-links for interesting paths
    # 0 -> 5 (shortcut)
    await postgres_backend.create_edge(
        source_id=nodes[0].id,
        target_id=nodes[5].id,
        edge_type="SHORTCUT",
        properties={"shortcut": True},
    )

    # 3 -> 8 (another shortcut)
    await postgres_backend.create_edge(
        source_id=nodes[3].id,
        target_id=nodes[8].id,
        edge_type="SHORTCUT",
        properties={"shortcut": True},
    )

    # Store node IDs for test access
    postgres_backend._test_nodes = nodes

    yield postgres_backend


@pytest_asyncio.fixture(scope="function")
async def populated_memgraph_backend(
    memgraph_backend,
) -> AsyncGenerator[MemgraphBackend, None]:
    """
    Memgraph backend pre-populated with test graph data.

    Creates same test graph as populated_postgres_backend for parity testing.
    """
    nodes = []

    # Create 10 nodes
    for i in range(10):
        node = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={
                "name": f"Node-{i}",
                "index": i,
                "description": f"Test node number {i}",
            },
        )
        nodes.append(node)

    # Create chain edges
    for i in range(9):
        await memgraph_backend.create_edge(
            source_id=nodes[i].id,
            target_id=nodes[i + 1].id,
            edge_type="NEXT",
            properties={"order": i},
        )

    # Create shortcuts
    await memgraph_backend.create_edge(
        source_id=nodes[0].id,
        target_id=nodes[5].id,
        edge_type="SHORTCUT",
        properties={"shortcut": True},
    )

    await memgraph_backend.create_edge(
        source_id=nodes[3].id,
        target_id=nodes[8].id,
        edge_type="SHORTCUT",
        properties={"shortcut": True},
    )

    memgraph_backend._test_nodes = nodes

    yield memgraph_backend


# ============================================================================
# Batch Data Fixtures
# ============================================================================


@pytest.fixture
def batch_nodes_100():
    """Generate 100 node specifications for batch testing."""
    return [
        {
            "labels": ["BatchNode"],
            "properties": {
                "name": f"BatchNode-{i}",
                "index": i,
                "batch": "test-100",
            },
        }
        for i in range(100)
    ]


@pytest.fixture
def batch_nodes_1000():
    """Generate 1000 node specifications for performance testing."""
    return [
        {
            "labels": ["BatchNode"],
            "properties": {
                "name": f"BatchNode-{i}",
                "index": i,
                "batch": "test-1000",
            },
        }
        for i in range(1000)
    ]


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires database)"
    )
    config.addinivalue_line("markers", "slow: mark test as slow (performance tests)")
    config.addinivalue_line("markers", "postgres: mark test as PostgreSQL-specific")
    config.addinivalue_line("markers", "memgraph: mark test as Memgraph-specific")


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if databases not available."""
    # Check if we should skip integration tests
    skip_integration = pytest.mark.skip(reason="Database not available")

    for item in items:
        if "integration" in item.keywords:
            # Tests will be skipped inside fixtures if DB not available
            pass
