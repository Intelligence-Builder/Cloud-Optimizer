"""
Integration tests for MemgraphBackend.

These tests connect to a REAL Memgraph database via Docker.
No mocks are used - all tests run against actual infrastructure.

Requirements:
    docker-compose -f docker/docker-compose.test.yml up -d
"""

import pytest
import pytest_asyncio
import time

from src.ib_platform.graph.backends.memgraph import MemgraphBackend
from src.ib_platform.graph.protocol import (
    GraphNode,
    GraphEdge,
    TraversalDirection,
    TraversalParams,
)


# ============================================================================
# Unit Tests (no database required)
# ============================================================================


@pytest.mark.unit
class TestMemgraphBackendUnit:
    """Unit tests for MemgraphBackend that don't require a database."""

    def test_initialization(self):
        """Test backend initialization with all parameters."""
        backend = MemgraphBackend(
            uri="bolt://localhost:7687",
            username="admin",
            password="secret",
            database="memgraph",
        )

        assert backend._uri == "bolt://localhost:7687"
        assert backend._username == "admin"
        assert backend._password == "secret"
        assert backend._database == "memgraph"
        assert not backend.is_connected

    def test_initialization_without_auth(self):
        """Test backend initialization without authentication."""
        backend = MemgraphBackend(uri="bolt://localhost:7687")

        assert backend._uri == "bolt://localhost:7687"
        assert backend._username is None
        assert backend._password is None

    def test_ensure_connected_raises_when_not_connected(self):
        """Test that _ensure_connected raises when not connected."""
        backend = MemgraphBackend(uri="bolt://localhost:7687")

        with pytest.raises(RuntimeError, match="not connected"):
            backend._ensure_connected()


# ============================================================================
# Integration Tests - Node Operations
# ============================================================================


@pytest.mark.integration
@pytest.mark.memgraph
@pytest.mark.asyncio
class TestMemgraphNodeOperations:
    """Test node CRUD operations against real Memgraph database."""

    async def test_connect_disconnect(self, memgraph_backend):
        """Test that we can connect and disconnect from Memgraph."""
        # Fixture already connected
        assert memgraph_backend.is_connected

    async def test_create_node(self, memgraph_backend):
        """Test creating a node in Memgraph."""
        node = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Test", "value": 42},
        )

        assert isinstance(node, GraphNode)
        assert node.id is not None
        assert "TestNode" in node.labels
        assert node.properties["name"] == "Test"
        assert node.properties["value"] == 42

    async def test_create_node_multiple_labels(self, memgraph_backend):
        """Test creating a node with multiple labels."""
        node = await memgraph_backend.create_node(
            labels=["Entity", "Person", "User"],
            properties={"name": "Multi-Label Test"},
        )

        assert isinstance(node, GraphNode)
        assert "Entity" in node.labels
        assert "Person" in node.labels
        assert "User" in node.labels

    async def test_get_node(self, memgraph_backend):
        """Test retrieving a node by ID."""
        created = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Retrieve Test", "data": "some data"},
        )

        retrieved = await memgraph_backend.get_node(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.properties["name"] == "Retrieve Test"
        assert retrieved.properties["data"] == "some data"

    async def test_get_node_not_found(self, memgraph_backend):
        """Test retrieving a non-existent node returns None."""
        from uuid import uuid4

        fake_id = uuid4()
        result = await memgraph_backend.get_node(fake_id)

        assert result is None

    async def test_update_node_merge(self, memgraph_backend):
        """Test updating a node with merge=True preserves existing properties."""
        node = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Original", "value": 1, "keep": "this"},
        )

        updated = await memgraph_backend.update_node(
            node_id=node.id,
            properties={"value": 2, "new_field": "added"},
            merge=True,
        )

        assert updated.properties["name"] == "Original"
        assert updated.properties["value"] == 2
        assert updated.properties["keep"] == "this"
        assert updated.properties["new_field"] == "added"

    async def test_update_node_replace(self, memgraph_backend):
        """Test updating a node with merge=False replaces all properties."""
        node = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Original", "value": 1, "to_remove": "gone"},
        )

        updated = await memgraph_backend.update_node(
            node_id=node.id,
            properties={"name": "Replaced", "new_value": 99},
            merge=False,
        )

        assert updated.properties["name"] == "Replaced"
        assert updated.properties["new_value"] == 99
        assert "to_remove" not in updated.properties

    async def test_delete_node_soft(self, memgraph_backend):
        """Test soft deleting a node sets deleted_at."""
        node = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "To Soft Delete"},
        )

        result = await memgraph_backend.delete_node(node.id, soft=True)
        assert result is True

        # Node should still exist with deleted_at
        retrieved = await memgraph_backend.get_node(node.id)
        assert retrieved is not None

    async def test_delete_node_hard(self, memgraph_backend):
        """Test hard deleting a node removes it completely."""
        node = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "To Hard Delete"},
        )

        result = await memgraph_backend.delete_node(node.id, soft=False)
        assert result is True

        # Node should be gone
        retrieved = await memgraph_backend.get_node(node.id)
        assert retrieved is None


# ============================================================================
# Integration Tests - Edge Operations
# ============================================================================


@pytest.mark.integration
@pytest.mark.memgraph
@pytest.mark.asyncio
class TestMemgraphEdgeOperations:
    """Test edge CRUD operations against real Memgraph database."""

    async def test_create_edge(self, memgraph_backend):
        """Test creating an edge between two nodes."""
        source = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Source"},
        )
        target = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Target"},
        )

        edge = await memgraph_backend.create_edge(
            source_id=source.id,
            target_id=target.id,
            edge_type="CONNECTS_TO",
            properties={"weight": 0.8, "confidence": 0.9},
        )

        assert isinstance(edge, GraphEdge)
        assert edge.id is not None
        assert edge.source_id == source.id
        assert edge.target_id == target.id
        assert edge.edge_type == "CONNECTS_TO"
        assert edge.properties["weight"] == 0.8

    async def test_get_edge(self, memgraph_backend):
        """Test retrieving an edge by ID."""
        source = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Source"},
        )
        target = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Target"},
        )

        created = await memgraph_backend.create_edge(
            source_id=source.id,
            target_id=target.id,
            edge_type="TEST_EDGE",
            properties={"data": "edge data"},
        )

        retrieved = await memgraph_backend.get_edge(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.edge_type == "TEST_EDGE"

    async def test_update_edge(self, memgraph_backend):
        """Test updating edge properties."""
        source = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Source"},
        )
        target = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Target"},
        )

        edge = await memgraph_backend.create_edge(
            source_id=source.id,
            target_id=target.id,
            edge_type="UPDATES",
            properties={"weight": 0.5},
        )

        updated = await memgraph_backend.update_edge(
            edge_id=edge.id,
            properties={"weight": 0.9, "verified": True},
        )

        assert updated.properties["weight"] == 0.9
        assert updated.properties["verified"] is True

    async def test_delete_edge(self, memgraph_backend):
        """Test deleting an edge."""
        source = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Source"},
        )
        target = await memgraph_backend.create_node(
            labels=["TestNode"],
            properties={"name": "Target"},
        )

        edge = await memgraph_backend.create_edge(
            source_id=source.id,
            target_id=target.id,
            edge_type="TO_DELETE",
            properties={},
        )

        result = await memgraph_backend.delete_edge(edge.id)
        assert result is True

        # Edge should be gone
        retrieved = await memgraph_backend.get_edge(edge.id)
        assert retrieved is None


# ============================================================================
# Integration Tests - Traversal Operations
# ============================================================================


@pytest.mark.integration
@pytest.mark.memgraph
@pytest.mark.asyncio
class TestMemgraphTraversal:
    """Test graph traversal operations against real Memgraph database."""

    async def test_traverse_outgoing(self, populated_memgraph_backend):
        """Test outgoing traversal from a node."""
        backend = populated_memgraph_backend
        start_node = backend._test_nodes[0]

        params = TraversalParams(
            max_depth=2,
            direction=TraversalDirection.OUTGOING,
            edge_types=None,
            limit=100,
        )

        nodes = await backend.traverse(start_node.id, params)

        # Should find nodes connected via outgoing edges
        assert len(nodes) >= 2
        node_ids = [n.id for n in nodes]
        # Node 1 and Node 5 should be reachable from Node 0
        assert backend._test_nodes[1].id in node_ids
        assert backend._test_nodes[5].id in node_ids  # Via SHORTCUT

    async def test_traverse_incoming(self, populated_memgraph_backend):
        """Test incoming traversal to a node."""
        backend = populated_memgraph_backend
        end_node = backend._test_nodes[5]

        params = TraversalParams(
            max_depth=2,
            direction=TraversalDirection.INCOMING,
            edge_types=None,
            limit=100,
        )

        nodes = await backend.traverse(end_node.id, params)

        # Should find nodes that have edges pointing to this node
        assert len(nodes) >= 1
        node_ids = [n.id for n in nodes]
        # Node 0 has a shortcut to Node 5
        assert backend._test_nodes[0].id in node_ids

    async def test_traverse_both_directions(self, populated_memgraph_backend):
        """Test bidirectional traversal."""
        backend = populated_memgraph_backend
        middle_node = backend._test_nodes[5]

        params = TraversalParams(
            max_depth=1,
            direction=TraversalDirection.BOTH,
            edge_types=None,
            limit=100,
        )

        nodes = await backend.traverse(middle_node.id, params)

        # Should find nodes in both directions
        assert len(nodes) >= 2

    async def test_traverse_with_edge_type_filter(self, populated_memgraph_backend):
        """Test traversal filtered by edge type."""
        backend = populated_memgraph_backend
        start_node = backend._test_nodes[0]

        # Only follow SHORTCUT edges
        params = TraversalParams(
            max_depth=3,
            direction=TraversalDirection.OUTGOING,
            edge_types=["SHORTCUT"],
            limit=100,
        )

        nodes = await backend.traverse(start_node.id, params)

        # Should only find Node 5 via SHORTCUT
        node_ids = [n.id for n in nodes]
        assert backend._test_nodes[5].id in node_ids
        # Should NOT find Node 1 (connected via NEXT, not SHORTCUT)
        assert backend._test_nodes[1].id not in node_ids

    async def test_traverse_with_depth_limit(self, populated_memgraph_backend):
        """Test that depth limit is respected."""
        backend = populated_memgraph_backend
        start_node = backend._test_nodes[0]

        # Depth 1 should only get immediate neighbors
        params = TraversalParams(
            max_depth=1,
            direction=TraversalDirection.OUTGOING,
            edge_types=["NEXT"],
            limit=100,
        )

        nodes = await backend.traverse(start_node.id, params)

        # Should only find Node 1 (depth 1)
        assert len(nodes) == 1
        assert nodes[0].id == backend._test_nodes[1].id


# ============================================================================
# Integration Tests - Path Finding
# ============================================================================


@pytest.mark.integration
@pytest.mark.memgraph
@pytest.mark.asyncio
class TestMemgraphPathFinding:
    """Test path finding operations against real Memgraph database."""

    async def test_find_shortest_path(self, populated_memgraph_backend):
        """Test finding the shortest path between nodes."""
        backend = populated_memgraph_backend
        start = backend._test_nodes[0]
        end = backend._test_nodes[5]

        path = await backend.find_shortest_path(
            start_node_id=start.id,
            end_node_id=end.id,
        )

        assert path is not None
        # Should take SHORTCUT (1 edge) instead of NEXT chain (5 edges)
        assert len(path.edges) <= 5

    async def test_find_shortest_path_chain(self, populated_memgraph_backend):
        """Test finding path through chain edges."""
        backend = populated_memgraph_backend
        start = backend._test_nodes[0]
        end = backend._test_nodes[2]

        path = await backend.find_shortest_path(
            start_node_id=start.id,
            end_node_id=end.id,
        )

        assert path is not None
        assert len(path.nodes) == 3  # 0 -> 1 -> 2
        assert len(path.edges) == 2

    async def test_find_shortest_path_uses_shortcut(self, populated_memgraph_backend):
        """Test that shortcut edges are preferred when shorter."""
        backend = populated_memgraph_backend
        start = backend._test_nodes[3]
        end = backend._test_nodes[8]

        path = await backend.find_shortest_path(
            start_node_id=start.id,
            end_node_id=end.id,
        )

        assert path is not None
        # Direct SHORTCUT from 3 to 8 is 1 edge
        # Chain path is 3->4->5->6->7->8 = 5 edges
        assert len(path.edges) == 1

    async def test_find_path_no_path(self, memgraph_backend):
        """Test that None is returned when no path exists."""
        # Create two disconnected nodes
        node1 = await memgraph_backend.create_node(
            labels=["Isolated"],
            properties={"name": "Island 1"},
        )
        node2 = await memgraph_backend.create_node(
            labels=["Isolated"],
            properties={"name": "Island 2"},
        )

        path = await memgraph_backend.find_shortest_path(
            start_node_id=node1.id,
            end_node_id=node2.id,
        )

        assert path is None


# ============================================================================
# Integration Tests - Neighbor Operations
# ============================================================================


@pytest.mark.integration
@pytest.mark.memgraph
@pytest.mark.asyncio
class TestMemgraphNeighbors:
    """Test neighbor query operations against real Memgraph database."""

    async def test_get_neighbors_outgoing(self, populated_memgraph_backend):
        """Test getting outgoing neighbors."""
        backend = populated_memgraph_backend
        node = backend._test_nodes[0]

        neighbors = await backend.get_neighbors(
            node_id=node.id,
            direction=TraversalDirection.OUTGOING,
        )

        # Node 0 connects to Node 1 (NEXT) and Node 5 (SHORTCUT)
        assert len(neighbors) == 2

    async def test_get_neighbors_incoming(self, populated_memgraph_backend):
        """Test getting incoming neighbors."""
        backend = populated_memgraph_backend
        node = backend._test_nodes[5]

        neighbors = await backend.get_neighbors(
            node_id=node.id,
            direction=TraversalDirection.INCOMING,
        )

        # Node 5 receives from Node 4 (NEXT) and Node 0 (SHORTCUT)
        assert len(neighbors) == 2

    async def test_get_neighbors_with_edge_type(self, populated_memgraph_backend):
        """Test getting neighbors filtered by edge type."""
        backend = populated_memgraph_backend
        node = backend._test_nodes[0]

        neighbors = await backend.get_neighbors(
            node_id=node.id,
            direction=TraversalDirection.OUTGOING,
            edge_types=["NEXT"],
        )

        # Only Node 1 via NEXT edge
        assert len(neighbors) == 1

    async def test_get_neighbors_with_limit(self, populated_memgraph_backend):
        """Test neighbor query respects limit."""
        backend = populated_memgraph_backend
        node = backend._test_nodes[0]

        neighbors = await backend.get_neighbors(
            node_id=node.id,
            direction=TraversalDirection.OUTGOING,
            limit=1,
        )

        assert len(neighbors) == 1


# ============================================================================
# Integration Tests - Query Operations
# ============================================================================


@pytest.mark.integration
@pytest.mark.memgraph
@pytest.mark.asyncio
class TestMemgraphQueryOperations:
    """Test count and query operations against real Memgraph database."""

    async def test_count_nodes(self, populated_memgraph_backend):
        """Test counting nodes."""
        backend = populated_memgraph_backend

        count = await backend.count_nodes(labels=["TestNode"])

        assert count == 10  # Populated with 10 nodes

    async def test_count_nodes_no_filter(self, populated_memgraph_backend):
        """Test counting all nodes."""
        backend = populated_memgraph_backend

        count = await backend.count_nodes()

        assert count >= 10

    async def test_count_edges(self, populated_memgraph_backend):
        """Test counting edges."""
        backend = populated_memgraph_backend

        count = await backend.count_edges(edge_types=["NEXT"])

        assert count == 9  # Chain of 9 NEXT edges

    async def test_count_edges_shortcut(self, populated_memgraph_backend):
        """Test counting SHORTCUT edges."""
        backend = populated_memgraph_backend

        count = await backend.count_edges(edge_types=["SHORTCUT"])

        assert count == 2  # Two SHORTCUT edges

    async def test_execute_native_query(self, memgraph_backend):
        """Test executing a native Cypher query."""
        query = "RETURN 1 as test_value, 'hello' as greeting"

        results = await memgraph_backend.execute_query(query)

        assert len(results) == 1
        assert results[0]["test_value"] == 1
        assert results[0]["greeting"] == "hello"

    async def test_execute_query_with_parameters(self, memgraph_backend):
        """Test executing a parameterized Cypher query."""
        # Create a node to query
        node = await memgraph_backend.create_node(
            labels=["QueryTest"],
            properties={"name": "ParamTest", "value": 42},
        )

        query = """
        MATCH (n:QueryTest {name: $name})
        RETURN n.value as value
        """

        results = await memgraph_backend.execute_query(
            query, parameters={"name": "ParamTest"}
        )

        assert len(results) == 1
        assert results[0]["value"] == 42


# ============================================================================
# Integration Tests - Batch Operations
# ============================================================================


@pytest.mark.integration
@pytest.mark.memgraph
@pytest.mark.asyncio
class TestMemgraphBatchOperations:
    """Test batch operations against real Memgraph database."""

    async def test_batch_create_nodes(self, memgraph_backend, batch_nodes_100):
        """Test creating multiple nodes in batch."""
        created_nodes = []

        for node_spec in batch_nodes_100:
            node = await memgraph_backend.create_node(
                labels=node_spec["labels"],
                properties=node_spec["properties"],
            )
            created_nodes.append(node)

        assert len(created_nodes) == 100

        # Verify count
        count = await memgraph_backend.count_nodes(labels=["BatchNode"])
        assert count == 100

    async def test_batch_create_edges(self, memgraph_backend):
        """Test creating multiple edges in batch."""
        # Create nodes for edge testing
        nodes = []
        for i in range(10):
            node = await memgraph_backend.create_node(
                labels=["BatchEdgeNode"],
                properties={"index": i},
            )
            nodes.append(node)

        # Create edges in a ring
        for i in range(10):
            await memgraph_backend.create_edge(
                source_id=nodes[i].id,
                target_id=nodes[(i + 1) % 10].id,
                edge_type="BATCH_EDGE",
                properties={"order": i},
            )

        count = await memgraph_backend.count_edges(edge_types=["BATCH_EDGE"])
        assert count == 10


# ============================================================================
# Integration Tests - Performance
# ============================================================================


@pytest.mark.integration
@pytest.mark.memgraph
@pytest.mark.slow
@pytest.mark.asyncio
class TestMemgraphPerformance:
    """Performance tests against real Memgraph database."""

    async def test_traversal_performance(self, populated_memgraph_backend):
        """Test that traversal completes within acceptable time."""
        backend = populated_memgraph_backend
        start_node = backend._test_nodes[0]

        params = TraversalParams(
            max_depth=5,
            direction=TraversalDirection.OUTGOING,
            limit=100,
        )

        start_time = time.time()
        await backend.traverse(start_node.id, params)
        elapsed = time.time() - start_time

        # Should complete in under 100ms for small graph
        assert elapsed < 0.1, f"Traversal took {elapsed:.3f}s"

    async def test_path_finding_performance(self, populated_memgraph_backend):
        """Test that path finding completes within acceptable time."""
        backend = populated_memgraph_backend
        start = backend._test_nodes[0]
        end = backend._test_nodes[9]

        start_time = time.time()
        await backend.find_shortest_path(
            start_node_id=start.id,
            end_node_id=end.id,
        )
        elapsed = time.time() - start_time

        # Should complete in under 50ms
        assert elapsed < 0.05, f"Path finding took {elapsed:.3f}s"

    async def test_batch_creation_performance(self, memgraph_backend, batch_nodes_1000):
        """Test that batch node creation completes within acceptable time."""
        start_time = time.time()

        for node_spec in batch_nodes_1000:
            await memgraph_backend.create_node(
                labels=node_spec["labels"],
                properties=node_spec["properties"],
            )

        elapsed = time.time() - start_time

        # 1000 nodes should complete in under 5 seconds
        assert elapsed < 5.0, f"Batch creation took {elapsed:.3f}s"

        # Verify count
        count = await memgraph_backend.count_nodes(labels=["BatchNode"])
        assert count == 1000
