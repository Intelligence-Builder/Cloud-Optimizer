"""
Graph Backend Protocol - Defines the interface for graph database backends.

This module provides the protocol (interface) that all graph backends must implement,
along with data classes for graph operations.
"""

import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID

logger = logging.getLogger(__name__)


class TraversalDirection(str, Enum):
    """Direction for graph traversal."""

    OUTGOING = "outgoing"
    INCOMING = "incoming"
    BOTH = "both"


@dataclass
class GraphNode:
    """
    Represents a node in the graph.

    Attributes:
        id: Unique identifier for the node
        labels: List of labels/types for this node
        properties: Key-value properties of the node
        depth: Optional depth in traversal (from start node)
        path: Optional path of node IDs from start to this node
    """

    id: UUID
    labels: List[str]
    properties: Dict[str, Any]
    depth: Optional[int] = None
    path: Optional[List[UUID]] = None

    def __post_init__(self) -> None:
        """Validate node data."""
        if not self.labels:
            logger.warning(f"Node {self.id} has no labels")
        if self.properties is None:
            self.properties = {}


@dataclass
class GraphEdge:
    """
    Represents an edge (relationship) in the graph.

    Attributes:
        id: Unique identifier for the edge
        source_id: Source node UUID
        target_id: Target node UUID
        edge_type: Type/label of the relationship
        properties: Key-value properties of the edge
        weight: Edge weight (default 1.0)
        confidence: Confidence score for this relationship (default 1.0)
    """

    id: UUID
    source_id: UUID
    target_id: UUID
    edge_type: str
    properties: Dict[str, Any]
    weight: float = 1.0
    confidence: float = 1.0

    def __post_init__(self) -> None:
        """Validate edge data."""
        if not self.edge_type:
            raise ValueError("edge_type cannot be empty")
        if self.source_id == self.target_id:
            logger.warning(f"Self-loop detected: {self.id}")
        if not 0 <= self.weight <= 1:
            raise ValueError(f"weight must be between 0 and 1, got {self.weight}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(
                f"confidence must be between 0 and 1, got {self.confidence}"
            )
        if self.properties is None:
            self.properties = {}


@dataclass
class GraphPath:
    """
    Represents a path through the graph.

    Attributes:
        nodes: Ordered list of nodes in the path
        edges: Ordered list of edges connecting the nodes
        total_weight: Total weight of the path
        length: Number of edges in the path
    """

    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_weight: float
    length: int

    def __post_init__(self) -> None:
        """Validate path data."""
        if len(self.nodes) != len(self.edges) + 1:
            raise ValueError(
                f"Path must have exactly one more node than edges. "
                f"Got {len(self.nodes)} nodes and {len(self.edges)} edges"
            )
        if len(self.edges) != self.length:
            logger.warning(
                f"Path length mismatch: {self.length} vs {len(self.edges)} edges"
            )


@dataclass
class TraversalParams:
    """
    Parameters for graph traversal operations.

    Attributes:
        max_depth: Maximum depth to traverse
        direction: Direction to traverse (OUTGOING, INCOMING, BOTH)
        edge_types: Optional filter for edge types
        node_labels: Optional filter for node labels
        limit: Optional limit on number of results
    """

    max_depth: int = 3
    direction: TraversalDirection = TraversalDirection.BOTH
    edge_types: Optional[List[str]] = None
    node_labels: Optional[List[str]] = None
    limit: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate traversal parameters."""
        if self.max_depth < 1:
            raise ValueError(f"max_depth must be >= 1, got {self.max_depth}")
        if self.limit is not None and self.limit < 1:
            raise ValueError(f"limit must be >= 1 or None, got {self.limit}")


class GraphBackendProtocol(Protocol):
    """
    Protocol defining the graph backend interface.

    All graph backends must implement this protocol to ensure
    portability across different graph database systems.
    """

    # --- Connection Management ---

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the graph backend.

        Raises:
            ConnectionError: If connection fails
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to the graph backend.

        Should be idempotent - safe to call multiple times.
        """
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if backend is connected.

        Returns:
            True if connected, False otherwise
        """
        ...

    # --- Node Operations ---

    @abstractmethod
    async def create_node(
        self,
        labels: List[str],
        properties: Dict[str, Any],
        node_id: Optional[UUID] = None,
    ) -> GraphNode:
        """
        Create a single node.

        Args:
            labels: List of labels for the node
            properties: Node properties
            node_id: Optional specific UUID to use

        Returns:
            Created GraphNode

        Raises:
            ValueError: If labels is empty or properties are invalid
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def get_node(self, node_id: UUID) -> Optional[GraphNode]:
        """
        Get a node by ID.

        Args:
            node_id: UUID of the node

        Returns:
            GraphNode if found, None otherwise

        Raises:
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def update_node(
        self,
        node_id: UUID,
        properties: Dict[str, Any],
        merge: bool = True,
    ) -> GraphNode:
        """
        Update node properties.

        Args:
            node_id: UUID of the node to update
            properties: Properties to update
            merge: If True, merge with existing properties; if False, replace

        Returns:
            Updated GraphNode

        Raises:
            ValueError: If node not found
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def delete_node(self, node_id: UUID, soft: bool = True) -> bool:
        """
        Delete a node.

        Args:
            node_id: UUID of the node to delete
            soft: If True, soft delete (set deleted_at); if False, hard delete

        Returns:
            True if deleted, False if node not found

        Raises:
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def batch_create_nodes(
        self,
        nodes: List[Dict[str, Any]],
    ) -> List[GraphNode]:
        """
        Batch create multiple nodes.

        Args:
            nodes: List of node specifications with 'labels' and 'properties' keys

        Returns:
            List of created GraphNodes

        Raises:
            ValueError: If any node spec is invalid
            RuntimeError: If not connected
        """
        ...

    # --- Edge Operations ---

    @abstractmethod
    async def create_edge(
        self,
        source_id: UUID,
        target_id: UUID,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None,
        edge_id: Optional[UUID] = None,
    ) -> GraphEdge:
        """
        Create a single edge.

        Args:
            source_id: Source node UUID
            target_id: Target node UUID
            edge_type: Type/label of the relationship
            properties: Optional edge properties
            edge_id: Optional specific UUID to use

        Returns:
            Created GraphEdge

        Raises:
            ValueError: If source or target node not found
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def get_edge(self, edge_id: UUID) -> Optional[GraphEdge]:
        """
        Get an edge by ID.

        Args:
            edge_id: UUID of the edge

        Returns:
            GraphEdge if found, None otherwise

        Raises:
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def update_edge(
        self,
        edge_id: UUID,
        properties: Dict[str, Any],
        merge: bool = True,
    ) -> GraphEdge:
        """
        Update edge properties.

        Args:
            edge_id: UUID of the edge to update
            properties: Properties to update
            merge: If True, merge with existing; if False, replace

        Returns:
            Updated GraphEdge

        Raises:
            ValueError: If edge not found
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def delete_edge(self, edge_id: UUID, soft: bool = True) -> bool:
        """
        Delete an edge.

        Args:
            edge_id: UUID of the edge to delete
            soft: If True, soft delete; if False, hard delete

        Returns:
            True if deleted, False if edge not found

        Raises:
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def batch_create_edges(
        self,
        edges: List[Dict[str, Any]],
    ) -> List[GraphEdge]:
        """
        Batch create multiple edges.

        Args:
            edges: List of edge specifications with required keys

        Returns:
            List of created GraphEdges

        Raises:
            ValueError: If any edge spec is invalid
            RuntimeError: If not connected
        """
        ...

    # --- Traversal Operations ---

    @abstractmethod
    async def traverse(
        self,
        start_node_id: UUID,
        params: TraversalParams,
    ) -> List[GraphNode]:
        """
        Traverse the graph from a starting node.

        Args:
            start_node_id: UUID of the starting node
            params: Traversal parameters

        Returns:
            List of nodes discovered during traversal

        Raises:
            ValueError: If start node not found
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def find_shortest_path(
        self,
        start_node_id: UUID,
        end_node_id: UUID,
        max_depth: int = 10,
        edge_types: Optional[List[str]] = None,
    ) -> Optional[GraphPath]:
        """
        Find the shortest path between two nodes.

        Args:
            start_node_id: Starting node UUID
            end_node_id: Target node UUID
            max_depth: Maximum path length to search
            edge_types: Optional filter for edge types

        Returns:
            GraphPath if path found, None otherwise

        Raises:
            ValueError: If nodes not found
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def find_all_paths(
        self,
        start_node_id: UUID,
        end_node_id: UUID,
        max_depth: int = 5,
        limit: int = 10,
    ) -> List[GraphPath]:
        """
        Find all paths between two nodes.

        Args:
            start_node_id: Starting node UUID
            end_node_id: Target node UUID
            max_depth: Maximum path length to search
            limit: Maximum number of paths to return

        Returns:
            List of GraphPaths (may be empty)

        Raises:
            ValueError: If nodes not found
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def get_neighbors(
        self,
        node_id: UUID,
        direction: TraversalDirection = TraversalDirection.BOTH,
        edge_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[GraphNode]:
        """
        Get immediate neighbors of a node.

        Args:
            node_id: UUID of the node
            direction: Direction to traverse
            edge_types: Optional filter for edge types
            limit: Optional limit on results

        Returns:
            List of neighboring nodes

        Raises:
            ValueError: If node not found
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def get_subgraph(
        self,
        node_ids: List[UUID],
        include_edges: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract a subgraph containing specified nodes.

        Args:
            node_ids: List of node UUIDs to include
            include_edges: If True, include edges between the nodes

        Returns:
            Dictionary with 'nodes' and optionally 'edges' keys

        Raises:
            RuntimeError: If not connected
        """
        ...

    # --- Query Operations ---

    @abstractmethod
    async def find_nodes(
        self,
        labels: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[GraphNode]:
        """
        Find nodes matching criteria.

        Args:
            labels: Optional label filter
            properties: Optional property filter (exact match)
            limit: Optional limit on results

        Returns:
            List of matching GraphNodes

        Raises:
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def find_edges(
        self,
        edge_types: Optional[List[str]] = None,
        source_id: Optional[UUID] = None,
        target_id: Optional[UUID] = None,
        limit: Optional[int] = None,
    ) -> List[GraphEdge]:
        """
        Find edges matching criteria.

        Args:
            edge_types: Optional edge type filter
            source_id: Optional source node filter
            target_id: Optional target node filter
            limit: Optional limit on results

        Returns:
            List of matching GraphEdges

        Raises:
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a native query (Cypher or SQL depending on backend).

        Use sparingly - prefer protocol methods for portability.

        Args:
            query: Native query string
            parameters: Optional query parameters

        Returns:
            List of result dictionaries

        Raises:
            RuntimeError: If not connected
            ValueError: If query is invalid
        """
        ...

    # --- Statistics ---

    @abstractmethod
    async def count_nodes(
        self,
        labels: Optional[List[str]] = None,
    ) -> int:
        """
        Count nodes, optionally filtered by labels.

        Args:
            labels: Optional label filter

        Returns:
            Node count

        Raises:
            RuntimeError: If not connected
        """
        ...

    @abstractmethod
    async def count_edges(
        self,
        edge_types: Optional[List[str]] = None,
    ) -> int:
        """
        Count edges, optionally filtered by type.

        Args:
            edge_types: Optional edge type filter

        Returns:
            Edge count

        Raises:
            RuntimeError: If not connected
        """
        ...
