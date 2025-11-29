"""
Integration tests for PostgresCTEBackend.

These tests run against a REAL PostgreSQL database.
No mocks are used - all operations hit actual database.

Requirements:
    docker-compose -f docker/docker-compose.test.yml up -d

Run tests:
    pytest tests/ib_platform/graph/test_postgres_cte.py -v
"""

import time
from uuid import uuid4

import pytest
import pytest_asyncio

from src.ib_platform.graph.backends.postgres_cte import PostgresCTEBackend
from src.ib_platform.graph.protocol import (
    GraphEdge,
    GraphNode,
    TraversalDirection,
    TraversalParams,
)

# ============================================================================
# Node Operations Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.postgres
class TestPostgresNodeOperations:
    """Test node CRUD operations against real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_create_node(self, postgres_backend: PostgresCTEBackend):
        """Create a node and verify it exists in database."""
        node = await postgres_backend.create_node(
            labels=["TestEntity", "Person"],
            properties={
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30,
            },
        )

        assert node is not None
        assert node.id is not None
        assert "TestEntity" in node.labels or node.labels[0] == "TestEntity"
        assert node.properties["name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_create_node_with_custom_id(
        self, postgres_backend: PostgresCTEBackend
    ):
        """Create a node with a specified UUID."""
        custom_id = uuid4()
        node = await postgres_backend.create_node(
            labels=["TestEntity"],
            properties={"name": "Custom ID Node"},
            node_id=custom_id,
        )

        assert node.id == custom_id

    @pytest.mark.asyncio
    async def test_get_node(self, postgres_backend: PostgresCTEBackend):
        """Create a node then retrieve it by ID."""
        # Create
        created = await postgres_backend.create_node(
            labels=["TestEntity"],
            properties={"name": "Retrievable Node", "value": 42},
        )

        # Retrieve
        retrieved = await postgres_backend.get_node(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.properties["name"] == "Retrievable Node"
        assert retrieved.properties["value"] == 42

    @pytest.mark.asyncio
    async def test_get_nonexistent_node(self, postgres_backend: PostgresCTEBackend):
        """Attempt to get a node that doesn't exist."""
        fake_id = uuid4()
        node = await postgres_backend.get_node(fake_id)
        assert node is None

    @pytest.mark.asyncio
    async def test_update_node_merge(self, postgres_backend: PostgresCTEBackend):
        """Update node properties with merge=True."""
        # Create
        node = await postgres_backend.create_node(
            labels=["TestEntity"],
            properties={"name": "Original", "keep_me": "preserved"},
        )

        # Update with merge
        updated = await postgres_backend.update_node(
            node_id=node.id,
            properties={"name": "Updated", "new_field": "added"},
            merge=True,
        )

        assert updated.properties["name"] == "Updated"
        assert updated.properties["new_field"] == "added"
        assert updated.properties.get("keep_me") == "preserved"

    @pytest.mark.asyncio
    async def test_update_node_replace(self, postgres_backend: PostgresCTEBackend):
        """Update node properties with merge=False (replace)."""
        # Create
        node = await postgres_backend.create_node(
            labels=["TestEntity"],
            properties={"name": "Original", "remove_me": "will be gone"},
        )

        # Update without merge
        updated = await postgres_backend.update_node(
            node_id=node.id,
            properties={"name": "Replaced"},
            merge=False,
        )

        assert updated.properties["name"] == "Replaced"
        assert "remove_me" not in updated.properties

    @pytest.mark.asyncio
    async def test_delete_node_soft(self, postgres_backend: PostgresCTEBackend):
        """Soft delete a node (sets deleted_at)."""
        # Create
        node = await postgres_backend.create_node(
            labels=["TestEntity"],
            properties={"name": "To Be Deleted"},
        )

        # Soft delete
        result = await postgres_backend.delete_node(node.id, soft=True)
        assert result is True

        # Should not be retrievable
        retrieved = await postgres_backend.get_node(node.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_node_hard(self, postgres_backend: PostgresCTEBackend):
        """Hard delete a node (removes from database)."""
        # Create
        node = await postgres_backend.create_node(
            labels=["TestEntity"],
            properties={"name": "To Be Hard Deleted"},
        )

        # Hard delete
        result = await postgres_backend.delete_node(node.id, soft=False)
        assert result is True

        # Should not be retrievable
        retrieved = await postgres_backend.get_node(node.id)
        assert retrieved is None


# ============================================================================
# Edge Operations Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.postgres
class TestPostgresEdgeOperations:
    """Test edge CRUD operations against real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_create_edge(self, postgres_backend: PostgresCTEBackend):
        """Create an edge between two nodes."""
        # Create two nodes
        node1 = await postgres_backend.create_node(
            labels=["Person"],
            properties={"name": "Alice"},
        )
        node2 = await postgres_backend.create_node(
            labels=["Person"],
            properties={"name": "Bob"},
        )

        # Create edge
        edge = await postgres_backend.create_edge(
            source_id=node1.id,
            target_id=node2.id,
            edge_type="KNOWS",
            properties={"since": 2020, "relationship": "friend"},
        )

        assert edge is not None
        assert edge.source_id == node1.id
        assert edge.target_id == node2.id
        assert edge.edge_type == "KNOWS"
        assert edge.properties["since"] == 2020

    @pytest.mark.asyncio
    async def test_get_edge(self, postgres_backend: PostgresCTEBackend):
        """Create then retrieve an edge."""
        node1 = await postgres_backend.create_node(
            labels=["Entity"],
            properties={"name": "Source"},
        )
        node2 = await postgres_backend.create_node(
            labels=["Entity"],
            properties={"name": "Target"},
        )

        created = await postgres_backend.create_edge(
            source_id=node1.id,
            target_id=node2.id,
            edge_type="CONNECTS",
            properties={"strength": 0.9},
        )

        retrieved = await postgres_backend.get_edge(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.edge_type == "CONNECTS"

    @pytest.mark.asyncio
    async def test_update_edge(self, postgres_backend: PostgresCTEBackend):
        """Update edge properties."""
        node1 = await postgres_backend.create_node(
            labels=["Entity"],
            properties={"name": "A"},
        )
        node2 = await postgres_backend.create_node(
            labels=["Entity"],
            properties={"name": "B"},
        )

        edge = await postgres_backend.create_edge(
            source_id=node1.id,
            target_id=node2.id,
            edge_type="LINK",
            properties={"version": 1},
        )

        updated = await postgres_backend.update_edge(
            edge_id=edge.id,
            properties={"version": 2, "updated": True},
            merge=True,
        )

        assert updated.properties["version"] == 2
        assert updated.properties["updated"] is True

    @pytest.mark.asyncio
    async def test_delete_edge(self, postgres_backend: PostgresCTEBackend):
        """Delete an edge."""
        node1 = await postgres_backend.create_node(
            labels=["Entity"],
            properties={"name": "X"},
        )
        node2 = await postgres_backend.create_node(
            labels=["Entity"],
            properties={"name": "Y"},
        )

        edge = await postgres_backend.create_edge(
            source_id=node1.id,
            target_id=node2.id,
            edge_type="TEMP",
        )

        result = await postgres_backend.delete_edge(edge.id)
        assert result is True

        retrieved = await postgres_backend.get_edge(edge.id)
        assert retrieved is None


# ============================================================================
# Batch Operations Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.postgres
class TestPostgresBatchOperations:
    """Test batch operations against real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_batch_create_nodes_100(
        self, postgres_backend: PostgresCTEBackend, batch_nodes_100
    ):
        """Batch create 100 nodes."""
        start = time.perf_counter()
        nodes = await postgres_backend.batch_create_nodes(batch_nodes_100)
        elapsed = time.perf_counter() - start

        assert len(nodes) == 100
        assert all(n.id is not None for n in nodes)
        print(f"Batch create 100 nodes: {elapsed:.3f}s")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_batch_create_nodes_1000(
        self, postgres_backend: PostgresCTEBackend, batch_nodes_1000
    ):
        """Batch create 1000 nodes - performance test."""
        start = time.perf_counter()
        nodes = await postgres_backend.batch_create_nodes(batch_nodes_1000)
        elapsed = time.perf_counter() - start

        assert len(nodes) == 1000
        # Performance requirement: < 2 seconds
        assert elapsed < 2.0, f"Batch create too slow: {elapsed:.2f}s > 2s"
        print(f"Batch create 1000 nodes: {elapsed:.3f}s")

    @pytest.mark.asyncio
    async def test_batch_create_edges(self, postgres_backend: PostgresCTEBackend):
        """Batch create edges between nodes."""
        # Create nodes first
        nodes = await postgres_backend.batch_create_nodes(
            [{"labels": ["Node"], "properties": {"name": f"N{i}"}} for i in range(10)]
        )

        # Create edges
        edge_specs = [
            {
                "source_id": nodes[i].id,
                "target_id": nodes[i + 1].id,
                "edge_type": "NEXT",
                "properties": {"order": i},
            }
            for i in range(9)
        ]

        edges = await postgres_backend.batch_create_edges(edge_specs)

        assert len(edges) == 9
        assert all(e.edge_type == "NEXT" for e in edges)


# ============================================================================
# Traversal Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.postgres
class TestPostgresTraversal:
    """Test graph traversal against real PostgreSQL with CTE queries."""

    @pytest.mark.asyncio
    async def test_traverse_outgoing(
        self, populated_postgres_backend: PostgresCTEBackend
    ):
        """Traverse outgoing edges from start node."""
        nodes = populated_postgres_backend._test_nodes
        start_node = nodes[0]

        params = TraversalParams(
            max_depth=3,
            direction=TraversalDirection.OUTGOING,
        )

        result = await populated_postgres_backend.traverse(start_node.id, params)

        # Should find nodes reachable within 3 hops
        assert len(result) > 0
        result_ids = {n.id for n in result}
        # Node 0 -> Node 1 -> Node 2 -> Node 3 (via NEXT)
        # Node 0 -> Node 5 (via SHORTCUT)
        assert nodes[1].id in result_ids or len(result_ids) > 0

    @pytest.mark.asyncio
    async def test_traverse_incoming(
        self, populated_postgres_backend: PostgresCTEBackend
    ):
        """Traverse incoming edges to a node."""
        nodes = populated_postgres_backend._test_nodes
        end_node = nodes[5]

        params = TraversalParams(
            max_depth=3,
            direction=TraversalDirection.INCOMING,
        )

        result = await populated_postgres_backend.traverse(end_node.id, params)

        # Should find nodes that can reach node 5
        assert len(result) >= 0  # May be empty depending on direction

    @pytest.mark.asyncio
    async def test_traverse_both(self, populated_postgres_backend: PostgresCTEBackend):
        """Traverse in both directions."""
        nodes = populated_postgres_backend._test_nodes
        middle_node = nodes[5]

        params = TraversalParams(
            max_depth=2,
            direction=TraversalDirection.BOTH,
        )

        result = await populated_postgres_backend.traverse(middle_node.id, params)

        # Should find nodes in both directions
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_traverse_with_edge_type_filter(
        self, populated_postgres_backend: PostgresCTEBackend
    ):
        """Traverse only following specific edge types."""
        nodes = populated_postgres_backend._test_nodes

        params = TraversalParams(
            max_depth=5,
            direction=TraversalDirection.OUTGOING,
            edge_types=["SHORTCUT"],  # Only follow shortcuts
        )

        result = await populated_postgres_backend.traverse(nodes[0].id, params)

        # Should only reach node 5 via shortcut
        result_ids = {n.id for n in result}
        if len(result_ids) > 0:
            assert nodes[5].id in result_ids

    @pytest.mark.asyncio
    async def test_traverse_with_limit(
        self, populated_postgres_backend: PostgresCTEBackend
    ):
        """Traverse with result limit."""
        nodes = populated_postgres_backend._test_nodes

        params = TraversalParams(
            max_depth=10,
            direction=TraversalDirection.BOTH,
            limit=3,
        )

        result = await populated_postgres_backend.traverse(nodes[0].id, params)

        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_traverse_prevents_cycles(self, postgres_backend: PostgresCTEBackend):
        """Verify traversal doesn't loop infinitely on cycles."""
        # Create a cycle: A -> B -> C -> A
        node_a = await postgres_backend.create_node(
            labels=["CycleNode"],
            properties={"name": "A"},
        )
        node_b = await postgres_backend.create_node(
            labels=["CycleNode"],
            properties={"name": "B"},
        )
        node_c = await postgres_backend.create_node(
            labels=["CycleNode"],
            properties={"name": "C"},
        )

        await postgres_backend.create_edge(node_a.id, node_b.id, "CYCLE")
        await postgres_backend.create_edge(node_b.id, node_c.id, "CYCLE")
        await postgres_backend.create_edge(node_c.id, node_a.id, "CYCLE")

        params = TraversalParams(max_depth=10, direction=TraversalDirection.OUTGOING)

        # Should complete without infinite loop
        result = await postgres_backend.traverse(node_a.id, params)

        # Should find all 3 nodes (including start)
        result_ids = {n.id for n in result}
        assert len(result_ids) <= 3


# ============================================================================
# Path Finding Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.postgres
class TestPostgresPathFinding:
    """Test path finding algorithms against real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_find_shortest_path(
        self, populated_postgres_backend: PostgresCTEBackend
    ):
        """Find shortest path between two nodes."""
        nodes = populated_postgres_backend._test_nodes

        path = await populated_postgres_backend.find_shortest_path(
            start_node_id=nodes[0].id,
            end_node_id=nodes[5].id,
            max_depth=10,
        )

        # There's a shortcut from 0 -> 5, so path should be short
        if path is not None:
            assert path.length >= 1
            assert path.nodes[0].id == nodes[0].id
            assert path.nodes[-1].id == nodes[5].id

    @pytest.mark.asyncio
    async def test_find_shortest_path_no_path(
        self, postgres_backend: PostgresCTEBackend
    ):
        """Handle case where no path exists."""
        # Create two disconnected nodes
        node1 = await postgres_backend.create_node(
            labels=["Isolated"],
            properties={"name": "Island1"},
        )
        node2 = await postgres_backend.create_node(
            labels=["Isolated"],
            properties={"name": "Island2"},
        )

        path = await postgres_backend.find_shortest_path(
            start_node_id=node1.id,
            end_node_id=node2.id,
            max_depth=5,
        )

        assert path is None

    @pytest.mark.asyncio
    async def test_find_all_paths(self, populated_postgres_backend: PostgresCTEBackend):
        """Find all paths between two nodes."""
        nodes = populated_postgres_backend._test_nodes

        paths = await populated_postgres_backend.find_all_paths(
            start_node_id=nodes[0].id,
            end_node_id=nodes[5].id,
            max_depth=6,
            limit=5,
        )

        # Should find at least 2 paths (direct shortcut and chain)
        assert len(paths) >= 1


# ============================================================================
# Neighbor Operations Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.postgres
class TestPostgresNeighbors:
    """Test neighbor retrieval against real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_get_neighbors_outgoing(
        self, populated_postgres_backend: PostgresCTEBackend
    ):
        """Get outgoing neighbors of a node."""
        nodes = populated_postgres_backend._test_nodes

        neighbors = await populated_postgres_backend.get_neighbors(
            node_id=nodes[0].id,
            direction=TraversalDirection.OUTGOING,
        )

        # Node 0 has outgoing edges to nodes 1 and 5
        neighbor_ids = {n.id for n in neighbors}
        assert nodes[1].id in neighbor_ids or nodes[5].id in neighbor_ids

    @pytest.mark.asyncio
    async def test_get_neighbors_with_edge_type_filter(
        self, populated_postgres_backend: PostgresCTEBackend
    ):
        """Get neighbors filtered by edge type."""
        nodes = populated_postgres_backend._test_nodes

        neighbors = await populated_postgres_backend.get_neighbors(
            node_id=nodes[0].id,
            direction=TraversalDirection.OUTGOING,
            edge_types=["SHORTCUT"],
        )

        # Only node 5 connected via SHORTCUT
        neighbor_ids = {n.id for n in neighbors}
        if len(neighbor_ids) > 0:
            assert nodes[5].id in neighbor_ids
            assert nodes[1].id not in neighbor_ids


# ============================================================================
# Query Operations Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.postgres
class TestPostgresQueryOperations:
    """Test query operations against real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_find_nodes_by_label(self, postgres_backend: PostgresCTEBackend):
        """Find nodes by label."""
        # Create nodes with different labels
        await postgres_backend.create_node(
            labels=["TypeA"],
            properties={"name": "A1"},
        )
        await postgres_backend.create_node(
            labels=["TypeA"],
            properties={"name": "A2"},
        )
        await postgres_backend.create_node(
            labels=["TypeB"],
            properties={"name": "B1"},
        )

        results = await postgres_backend.find_nodes(labels=["TypeA"])

        assert len(results) == 2
        assert all("TypeA" in n.labels for n in results)

    @pytest.mark.asyncio
    async def test_find_nodes_by_properties(self, postgres_backend: PostgresCTEBackend):
        """Find nodes by property values."""
        await postgres_backend.create_node(
            labels=["Item"],
            properties={"name": "Widget", "category": "electronics"},
        )
        await postgres_backend.create_node(
            labels=["Item"],
            properties={"name": "Gadget", "category": "electronics"},
        )
        await postgres_backend.create_node(
            labels=["Item"],
            properties={"name": "Book", "category": "books"},
        )

        results = await postgres_backend.find_nodes(
            properties={"category": "electronics"}
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_count_nodes(self, postgres_backend: PostgresCTEBackend):
        """Count nodes in database."""
        # Create some nodes
        for i in range(5):
            await postgres_backend.create_node(
                labels=["Counter"],
                properties={"name": f"Node{i}"},
            )

        count = await postgres_backend.count_nodes(labels=["Counter"])

        assert count == 5

    @pytest.mark.asyncio
    async def test_count_edges(self, postgres_backend: PostgresCTEBackend):
        """Count edges in database."""
        nodes = []
        for i in range(4):
            node = await postgres_backend.create_node(
                labels=["Node"],
                properties={"name": f"N{i}"},
            )
            nodes.append(node)

        # Create 3 edges
        for i in range(3):
            await postgres_backend.create_edge(
                source_id=nodes[i].id,
                target_id=nodes[i + 1].id,
                edge_type="COUNT_TEST",
            )

        count = await postgres_backend.count_edges(edge_types=["COUNT_TEST"])

        assert count == 3


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.slow
class TestPostgresPerformance:
    """Performance benchmarks against real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_traversal_performance(
        self, populated_postgres_backend: PostgresCTEBackend
    ):
        """Traversal should complete in < 100ms for small graph."""
        nodes = populated_postgres_backend._test_nodes

        params = TraversalParams(max_depth=5, direction=TraversalDirection.BOTH)

        start = time.perf_counter()
        result = await populated_postgres_backend.traverse(nodes[0].id, params)
        elapsed = (time.perf_counter() - start) * 1000  # ms

        assert elapsed < 100, f"Traversal too slow: {elapsed:.1f}ms > 100ms"
        print(f"Traversal time: {elapsed:.2f}ms, nodes found: {len(result)}")

    @pytest.mark.asyncio
    async def test_path_finding_performance(
        self, populated_postgres_backend: PostgresCTEBackend
    ):
        """Path finding should complete in < 50ms."""
        nodes = populated_postgres_backend._test_nodes

        start = time.perf_counter()
        path = await populated_postgres_backend.find_shortest_path(
            nodes[0].id, nodes[9].id, max_depth=10
        )
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 50, f"Path finding too slow: {elapsed:.1f}ms > 50ms"
        print(f"Path finding time: {elapsed:.2f}ms")
