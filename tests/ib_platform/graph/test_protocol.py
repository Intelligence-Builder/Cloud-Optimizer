"""
Tests for graph protocol data classes.

Tests the GraphNode, GraphEdge, GraphPath, and TraversalParams dataclasses.
"""

from uuid import uuid4

import pytest

from src.ib_platform.graph.protocol import (
    GraphEdge,
    GraphNode,
    GraphPath,
    TraversalDirection,
    TraversalParams,
)


class TestGraphNode:
    """Tests for GraphNode dataclass."""

    def test_create_basic_node(self):
        """Test creating a basic graph node."""
        node_id = uuid4()
        node = GraphNode(
            id=node_id,
            labels=["Entity", "Test"],
            properties={"name": "Test Node", "value": 42},
        )

        assert node.id == node_id
        assert node.labels == ["Entity", "Test"]
        assert node.properties["name"] == "Test Node"
        assert node.properties["value"] == 42
        assert node.depth is None
        assert node.path is None

    def test_create_node_with_depth(self):
        """Test creating a node with traversal depth."""
        node_id = uuid4()
        node = GraphNode(
            id=node_id,
            labels=["Entity"],
            properties={"name": "Test"},
            depth=3,
        )

        assert node.depth == 3

    def test_create_node_with_path(self):
        """Test creating a node with path information."""
        node_id = uuid4()
        path_ids = [uuid4(), uuid4(), node_id]
        node = GraphNode(
            id=node_id,
            labels=["Entity"],
            properties={"name": "Test"},
            path=path_ids,
        )

        assert node.path == path_ids
        assert len(node.path) == 3

    def test_node_with_empty_properties(self):
        """Test node handles empty properties correctly."""
        node = GraphNode(
            id=uuid4(),
            labels=["Entity"],
            properties={},
        )

        assert node.properties == {}


class TestGraphEdge:
    """Tests for GraphEdge dataclass."""

    def test_create_basic_edge(self):
        """Test creating a basic graph edge."""
        edge_id = uuid4()
        source_id = uuid4()
        target_id = uuid4()

        edge = GraphEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type="CONNECTS_TO",
            properties={"description": "test edge"},
        )

        assert edge.id == edge_id
        assert edge.source_id == source_id
        assert edge.target_id == target_id
        assert edge.edge_type == "CONNECTS_TO"
        assert edge.properties["description"] == "test edge"
        assert edge.weight == 1.0
        assert edge.confidence == 1.0

    def test_create_edge_with_weight_and_confidence(self):
        """Test creating an edge with custom weight and confidence."""
        edge = GraphEdge(
            id=uuid4(),
            source_id=uuid4(),
            target_id=uuid4(),
            edge_type="WEIGHTED",
            properties={},
            weight=0.7,
            confidence=0.85,
        )

        assert edge.weight == 0.7
        assert edge.confidence == 0.85

    def test_edge_type_validation(self):
        """Test that edge_type cannot be empty."""
        with pytest.raises(ValueError, match="edge_type cannot be empty"):
            GraphEdge(
                id=uuid4(),
                source_id=uuid4(),
                target_id=uuid4(),
                edge_type="",
                properties={},
            )

    def test_edge_weight_validation(self):
        """Test that weight must be between 0 and 1."""
        with pytest.raises(ValueError, match="weight must be between 0 and 1"):
            GraphEdge(
                id=uuid4(),
                source_id=uuid4(),
                target_id=uuid4(),
                edge_type="TEST",
                properties={},
                weight=1.5,
            )

    def test_edge_confidence_validation(self):
        """Test that confidence must be between 0 and 1."""
        with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
            GraphEdge(
                id=uuid4(),
                source_id=uuid4(),
                target_id=uuid4(),
                edge_type="TEST",
                properties={},
                confidence=-0.1,
            )

    def test_edge_with_empty_properties(self):
        """Test edge handles empty properties correctly."""
        edge = GraphEdge(
            id=uuid4(),
            source_id=uuid4(),
            target_id=uuid4(),
            edge_type="TEST",
            properties={},
        )

        assert edge.properties == {}


class TestGraphPath:
    """Tests for GraphPath dataclass."""

    def test_create_valid_path(self):
        """Test creating a valid graph path."""
        # Create path: node1 -> node2 -> node3
        nodes = [
            GraphNode(id=uuid4(), labels=["Node"], properties={"name": f"Node {i}"})
            for i in range(3)
        ]

        edges = [
            GraphEdge(
                id=uuid4(),
                source_id=nodes[0].id,
                target_id=nodes[1].id,
                edge_type="CONNECTS",
                properties={},
            ),
            GraphEdge(
                id=uuid4(),
                source_id=nodes[1].id,
                target_id=nodes[2].id,
                edge_type="CONNECTS",
                properties={},
            ),
        ]

        path = GraphPath(
            nodes=nodes,
            edges=edges,
            total_weight=2.0,
            length=2,
        )

        assert len(path.nodes) == 3
        assert len(path.edges) == 2
        assert path.total_weight == 2.0
        assert path.length == 2

    def test_path_validation(self):
        """Test that path validates node/edge count."""
        nodes = [
            GraphNode(id=uuid4(), labels=["Node"], properties={"name": "Node"})
            for _ in range(3)
        ]

        # Only 1 edge but 3 nodes (should have 2 edges)
        edges = [
            GraphEdge(
                id=uuid4(),
                source_id=nodes[0].id,
                target_id=nodes[1].id,
                edge_type="CONNECTS",
                properties={},
            )
        ]

        with pytest.raises(ValueError, match="exactly one more node than edges"):
            GraphPath(
                nodes=nodes,
                edges=edges,
                total_weight=1.0,
                length=2,
            )

    def test_empty_path(self):
        """Test creating an empty path (single node, no edges)."""
        node = GraphNode(id=uuid4(), labels=["Node"], properties={"name": "Lonely"})

        path = GraphPath(
            nodes=[node],
            edges=[],
            total_weight=0.0,
            length=0,
        )

        assert len(path.nodes) == 1
        assert len(path.edges) == 0
        assert path.length == 0


class TestTraversalParams:
    """Tests for TraversalParams dataclass."""

    def test_create_default_params(self):
        """Test creating traversal params with defaults."""
        params = TraversalParams()

        assert params.max_depth == 3
        assert params.direction == TraversalDirection.BOTH
        assert params.edge_types is None
        assert params.node_labels is None
        assert params.limit is None

    def test_create_custom_params(self):
        """Test creating custom traversal params."""
        params = TraversalParams(
            max_depth=5,
            direction=TraversalDirection.OUTGOING,
            edge_types=["CONNECTS", "RELATES"],
            node_labels=["Entity", "Document"],
            limit=100,
        )

        assert params.max_depth == 5
        assert params.direction == TraversalDirection.OUTGOING
        assert params.edge_types == ["CONNECTS", "RELATES"]
        assert params.node_labels == ["Entity", "Document"]
        assert params.limit == 100

    def test_max_depth_validation(self):
        """Test that max_depth must be >= 1."""
        with pytest.raises(ValueError, match="max_depth must be >= 1"):
            TraversalParams(max_depth=0)

    def test_limit_validation(self):
        """Test that limit must be >= 1 or None."""
        with pytest.raises(ValueError, match="limit must be >= 1 or None"):
            TraversalParams(limit=0)

        # None should be valid
        params = TraversalParams(limit=None)
        assert params.limit is None


class TestTraversalDirection:
    """Tests for TraversalDirection enum."""

    def test_direction_values(self):
        """Test that all direction values are defined."""
        assert TraversalDirection.OUTGOING.value == "outgoing"
        assert TraversalDirection.INCOMING.value == "incoming"
        assert TraversalDirection.BOTH.value == "both"

    def test_direction_from_string(self):
        """Test creating direction from string."""
        assert TraversalDirection("outgoing") == TraversalDirection.OUTGOING
        assert TraversalDirection("incoming") == TraversalDirection.INCOMING
        assert TraversalDirection("both") == TraversalDirection.BOTH
