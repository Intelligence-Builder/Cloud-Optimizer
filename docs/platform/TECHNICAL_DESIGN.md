# Intelligence-Builder Platform: Technical Design

**Document Version**: 1.0
**Created**: 2025-11-28
**Status**: Active

---

## Overview

This document provides detailed technical specifications for the Intelligence-Builder platform components. It is intended for developers implementing the platform.

### Design Philosophy: Platform for Clean Applications

This technical design supports a **clean-slate rebuild** strategy:

- **IB is the platform** - All graph operations, pattern detection, and domain logic are defined here
- **Applications are thin clients** - CO v2, Smart-Scaffold, and future apps consume IB via SDK
- **No shortcuts** - Applications must use the SDK; direct database access is prohibited
- **Quality enforced** - No file >500 lines, no function >10 complexity, 80% test coverage

Every technical decision is made with this question: *Does this enable applications to be cleaner and simpler?*

---

## Table of Contents

1. [Graph Database Abstraction Layer](#1-graph-database-abstraction-layer)
2. [Pattern Engine](#2-pattern-engine)
3. [Domain Module System](#3-domain-module-system)
4. [Core Orchestrator](#4-core-orchestrator)
5. [Security Domain (Priority)](#5-security-domain-priority)
6. [API Specifications](#6-api-specifications)
7. [Database Schema](#7-database-schema)
8. [SDK Design](#8-sdk-design)

---

## 1. Graph Database Abstraction Layer

### 1.1 Purpose

Provide a unified interface for graph operations that works across multiple backends (PostgreSQL CTE, Memgraph, future backends).

### 1.2 Protocol Definition

```python
# src/platform/graph/protocol.py

from typing import Protocol, List, Dict, Any, Optional, TypeVar, Generic
from uuid import UUID
from dataclasses import dataclass
from enum import Enum
from abc import abstractmethod


class TraversalDirection(str, Enum):
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    BOTH = "both"


@dataclass
class GraphNode:
    """Represents a node in the graph."""
    id: UUID
    labels: List[str]
    properties: Dict[str, Any]

    # Optional metadata
    depth: Optional[int] = None
    path: Optional[List[UUID]] = None


@dataclass
class GraphEdge:
    """Represents an edge in the graph."""
    id: UUID
    source_id: UUID
    target_id: UUID
    edge_type: str
    properties: Dict[str, Any]

    # Optional metadata
    weight: float = 1.0
    confidence: float = 1.0


@dataclass
class GraphPath:
    """Represents a path through the graph."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_weight: float
    length: int


@dataclass
class TraversalParams:
    """Parameters for graph traversal."""
    max_depth: int = 3
    direction: TraversalDirection = TraversalDirection.BOTH
    edge_types: Optional[List[str]] = None
    node_labels: Optional[List[str]] = None
    limit: Optional[int] = None


class GraphBackendProtocol(Protocol):
    """
    Protocol defining the graph backend interface.

    All graph backends must implement this protocol.
    """

    # --- Connection Management ---

    async def connect(self) -> None:
        """Establish connection to the graph backend."""
        ...

    async def disconnect(self) -> None:
        """Close connection to the graph backend."""
        ...

    @property
    def is_connected(self) -> bool:
        """Check if backend is connected."""
        ...

    # --- Node Operations ---

    async def create_node(
        self,
        labels: List[str],
        properties: Dict[str, Any],
        node_id: Optional[UUID] = None,
    ) -> GraphNode:
        """Create a single node."""
        ...

    async def get_node(self, node_id: UUID) -> Optional[GraphNode]:
        """Get a node by ID."""
        ...

    async def update_node(
        self,
        node_id: UUID,
        properties: Dict[str, Any],
        merge: bool = True,
    ) -> GraphNode:
        """Update node properties."""
        ...

    async def delete_node(self, node_id: UUID, soft: bool = True) -> bool:
        """Delete a node (soft delete by default)."""
        ...

    async def batch_create_nodes(
        self,
        nodes: List[Dict[str, Any]],
    ) -> List[GraphNode]:
        """Batch create multiple nodes."""
        ...

    # --- Edge Operations ---

    async def create_edge(
        self,
        source_id: UUID,
        target_id: UUID,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None,
        edge_id: Optional[UUID] = None,
    ) -> GraphEdge:
        """Create a single edge."""
        ...

    async def get_edge(self, edge_id: UUID) -> Optional[GraphEdge]:
        """Get an edge by ID."""
        ...

    async def update_edge(
        self,
        edge_id: UUID,
        properties: Dict[str, Any],
        merge: bool = True,
    ) -> GraphEdge:
        """Update edge properties."""
        ...

    async def delete_edge(self, edge_id: UUID, soft: bool = True) -> bool:
        """Delete an edge (soft delete by default)."""
        ...

    async def batch_create_edges(
        self,
        edges: List[Dict[str, Any]],
    ) -> List[GraphEdge]:
        """Batch create multiple edges."""
        ...

    # --- Traversal Operations ---

    async def traverse(
        self,
        start_node_id: UUID,
        params: TraversalParams,
    ) -> List[GraphNode]:
        """
        Traverse the graph from a starting node.

        Returns nodes discovered during traversal.
        """
        ...

    async def find_shortest_path(
        self,
        start_node_id: UUID,
        end_node_id: UUID,
        max_depth: int = 10,
        edge_types: Optional[List[str]] = None,
    ) -> Optional[GraphPath]:
        """Find the shortest path between two nodes."""
        ...

    async def find_all_paths(
        self,
        start_node_id: UUID,
        end_node_id: UUID,
        max_depth: int = 5,
        limit: int = 10,
    ) -> List[GraphPath]:
        """Find all paths between two nodes."""
        ...

    async def get_neighbors(
        self,
        node_id: UUID,
        direction: TraversalDirection = TraversalDirection.BOTH,
        edge_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[GraphNode]:
        """Get immediate neighbors of a node."""
        ...

    async def get_subgraph(
        self,
        node_ids: List[UUID],
        include_edges: bool = True,
    ) -> Dict[str, Any]:
        """Extract a subgraph containing specified nodes."""
        ...

    # --- Query Operations ---

    async def find_nodes(
        self,
        labels: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[GraphNode]:
        """Find nodes matching criteria."""
        ...

    async def find_edges(
        self,
        edge_types: Optional[List[str]] = None,
        source_id: Optional[UUID] = None,
        target_id: Optional[UUID] = None,
        limit: Optional[int] = None,
    ) -> List[GraphEdge]:
        """Find edges matching criteria."""
        ...

    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a native query (Cypher or SQL depending on backend).

        Use sparingly - prefer protocol methods for portability.
        """
        ...

    # --- Statistics ---

    async def count_nodes(
        self,
        labels: Optional[List[str]] = None,
    ) -> int:
        """Count nodes, optionally filtered by labels."""
        ...

    async def count_edges(
        self,
        edge_types: Optional[List[str]] = None,
    ) -> int:
        """Count edges, optionally filtered by type."""
        ...
```

### 1.3 PostgreSQL CTE Backend

```python
# src/platform/graph/backends/postgres_cte.py

from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
import asyncpg

from ..protocol import (
    GraphBackendProtocol, GraphNode, GraphEdge, GraphPath,
    TraversalParams, TraversalDirection
)


class PostgresCTEBackend(GraphBackendProtocol):
    """
    PostgreSQL CTE-based graph backend.

    Uses recursive Common Table Expressions for graph traversal.
    This is the default backend - no additional infrastructure required.
    """

    def __init__(
        self,
        connection_pool: asyncpg.Pool,
        schema: str = "intelligence",
        entities_table: str = "entities",
        relationships_table: str = "relationships",
    ):
        self._pool = connection_pool
        self._schema = schema
        self._entities_table = f"{schema}.{entities_table}"
        self._relationships_table = f"{schema}.{relationships_table}"
        self._connected = False

    async def connect(self) -> None:
        """Verify connection is available."""
        async with self._pool.acquire() as conn:
            await conn.execute("SELECT 1")
        self._connected = True

    async def disconnect(self) -> None:
        """No-op for pooled connections."""
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # --- Node Operations ---

    async def create_node(
        self,
        labels: List[str],
        properties: Dict[str, Any],
        node_id: Optional[UUID] = None,
    ) -> GraphNode:
        """Create a node in the entities table."""
        node_id = node_id or uuid4()

        # Extract standard fields
        entity_type = labels[0] if labels else "entity"
        name = properties.pop("name", str(node_id))
        description = properties.pop("description", None)

        query = f"""
            INSERT INTO {self._entities_table}
            (entity_id, entity_type, name, description, metadata, tags)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING entity_id, entity_type, name, description, metadata, tags, created_at
        """

        async with self._pool.acquire() as conn:
            record = await conn.fetchrow(
                query,
                node_id,
                entity_type,
                name,
                description,
                properties,  # Remaining properties go to metadata
                labels,      # Labels stored as tags
            )

        return GraphNode(
            id=record["entity_id"],
            labels=record["tags"] or [],
            properties={
                "name": record["name"],
                "description": record["description"],
                **(record["metadata"] or {}),
            },
        )

    async def batch_create_nodes(
        self,
        nodes: List[Dict[str, Any]],
    ) -> List[GraphNode]:
        """Batch create nodes using COPY or multi-value INSERT."""
        if not nodes:
            return []

        created = []

        # Process in batches of 1000
        batch_size = 1000
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]

            # Build multi-value INSERT
            values = []
            params = []
            param_idx = 1

            for node_spec in batch:
                node_id = node_spec.get("id") or uuid4()
                labels = node_spec.get("labels", ["entity"])
                props = node_spec.get("properties", {})

                entity_type = labels[0] if labels else "entity"
                name = props.pop("name", str(node_id))
                description = props.pop("description", None)

                values.append(
                    f"(${param_idx}, ${param_idx+1}, ${param_idx+2}, "
                    f"${param_idx+3}, ${param_idx+4}, ${param_idx+5})"
                )
                params.extend([node_id, entity_type, name, description, props, labels])
                param_idx += 6

            query = f"""
                INSERT INTO {self._entities_table}
                (entity_id, entity_type, name, description, metadata, tags)
                VALUES {', '.join(values)}
                RETURNING entity_id, entity_type, name, metadata, tags
            """

            async with self._pool.acquire() as conn:
                records = await conn.fetch(query, *params)

            for record in records:
                created.append(GraphNode(
                    id=record["entity_id"],
                    labels=record["tags"] or [],
                    properties={
                        "name": record["name"],
                        **(record["metadata"] or {}),
                    },
                ))

        return created

    # --- Traversal Operations ---

    async def traverse(
        self,
        start_node_id: UUID,
        params: TraversalParams,
    ) -> List[GraphNode]:
        """
        Traverse graph using recursive CTE.
        """
        # Build direction-specific join condition
        if params.direction == TraversalDirection.OUTGOING:
            rel_filter = "r.from_entity_id = node.entity_id"
            next_entity = "r.to_entity_id"
        elif params.direction == TraversalDirection.INCOMING:
            rel_filter = "r.to_entity_id = node.entity_id"
            next_entity = "r.from_entity_id"
        else:  # BOTH
            rel_filter = "(r.from_entity_id = node.entity_id OR r.to_entity_id = node.entity_id)"
            next_entity = """
                CASE
                    WHEN r.from_entity_id = node.entity_id THEN r.to_entity_id
                    ELSE r.from_entity_id
                END
            """

        # Build edge type filter
        type_filter = ""
        query_params = [start_node_id, params.max_depth]

        if params.edge_types:
            placeholders = ", ".join([f"${i}" for i in range(3, 3 + len(params.edge_types))])
            type_filter = f"AND r.relationship_type IN ({placeholders})"
            query_params.extend(params.edge_types)

        query = f"""
            WITH RECURSIVE graph_traversal AS (
                -- Base case: start node
                SELECT
                    e.entity_id,
                    e.name,
                    e.entity_type,
                    e.metadata,
                    e.tags,
                    0 as depth,
                    ARRAY[e.entity_id] as path
                FROM {self._entities_table} e
                WHERE e.entity_id = $1
                  AND e.deleted_at IS NULL

                UNION ALL

                -- Recursive case: follow relationships
                SELECT
                    e.entity_id,
                    e.name,
                    e.entity_type,
                    e.metadata,
                    e.tags,
                    node.depth + 1 as depth,
                    node.path || e.entity_id as path
                FROM graph_traversal node
                JOIN {self._relationships_table} r ON {rel_filter}
                    AND r.deleted_at IS NULL
                    {type_filter}
                JOIN {self._entities_table} e ON e.entity_id = {next_entity}
                    AND e.deleted_at IS NULL
                WHERE node.depth < $2
                  AND NOT (e.entity_id = ANY(node.path))  -- Prevent cycles
            )
            SELECT DISTINCT entity_id, name, entity_type, metadata, tags, depth, path
            FROM graph_traversal
            ORDER BY depth, name
        """

        if params.limit:
            query += f" LIMIT {params.limit}"

        async with self._pool.acquire() as conn:
            records = await conn.fetch(query, *query_params)

        return [
            GraphNode(
                id=r["entity_id"],
                labels=r["tags"] or [r["entity_type"]],
                properties={"name": r["name"], **(r["metadata"] or {})},
                depth=r["depth"],
                path=r["path"],
            )
            for r in records
        ]

    async def find_shortest_path(
        self,
        start_node_id: UUID,
        end_node_id: UUID,
        max_depth: int = 10,
        edge_types: Optional[List[str]] = None,
    ) -> Optional[GraphPath]:
        """
        Find shortest path using recursive CTE with BFS.
        """
        type_filter = ""
        query_params = [start_node_id, end_node_id, max_depth]

        if edge_types:
            placeholders = ", ".join([f"${i}" for i in range(4, 4 + len(edge_types))])
            type_filter = f"AND r.relationship_type IN ({placeholders})"
            query_params.extend(edge_types)

        query = f"""
            WITH RECURSIVE path_search AS (
                -- Base case
                SELECT
                    $1::uuid as current_node,
                    ARRAY[$1::uuid] as node_path,
                    ARRAY[]::uuid[] as edge_path,
                    0.0::double precision as total_weight,
                    0 as length

                UNION ALL

                -- Recursive case
                SELECT
                    r.to_entity_id as current_node,
                    ps.node_path || r.to_entity_id as node_path,
                    ps.edge_path || r.relationship_id as edge_path,
                    ps.total_weight + (1.0 - COALESCE(r.weight, 1.0)::float) as total_weight,
                    ps.length + 1 as length
                FROM path_search ps
                JOIN {self._relationships_table} r
                    ON r.from_entity_id = ps.current_node
                    AND r.deleted_at IS NULL
                    {type_filter}
                WHERE ps.length < $3
                  AND NOT (r.to_entity_id = ANY(ps.node_path))
                  AND ps.current_node != $2
            )
            SELECT node_path, edge_path, total_weight, length
            FROM path_search
            WHERE current_node = $2
            ORDER BY total_weight, length
            LIMIT 1
        """

        async with self._pool.acquire() as conn:
            record = await conn.fetchrow(query, *query_params)

        if not record:
            return None

        # Fetch actual nodes and edges for the path
        nodes = await self._fetch_nodes_by_ids(record["node_path"])
        edges = await self._fetch_edges_by_ids(record["edge_path"])

        return GraphPath(
            nodes=nodes,
            edges=edges,
            total_weight=float(record["total_weight"]),
            length=record["length"],
        )

    # --- Helper Methods ---

    async def _fetch_nodes_by_ids(self, node_ids: List[UUID]) -> List[GraphNode]:
        """Fetch nodes by IDs maintaining order."""
        if not node_ids:
            return []

        query = f"""
            SELECT entity_id, name, entity_type, metadata, tags
            FROM {self._entities_table}
            WHERE entity_id = ANY($1)
              AND deleted_at IS NULL
        """

        async with self._pool.acquire() as conn:
            records = await conn.fetch(query, node_ids)

        # Maintain order
        node_map = {r["entity_id"]: r for r in records}
        return [
            GraphNode(
                id=node_map[nid]["entity_id"],
                labels=node_map[nid]["tags"] or [node_map[nid]["entity_type"]],
                properties={
                    "name": node_map[nid]["name"],
                    **(node_map[nid]["metadata"] or {}),
                },
            )
            for nid in node_ids
            if nid in node_map
        ]

    async def _fetch_edges_by_ids(self, edge_ids: List[UUID]) -> List[GraphEdge]:
        """Fetch edges by IDs maintaining order."""
        if not edge_ids:
            return []

        query = f"""
            SELECT relationship_id, from_entity_id, to_entity_id,
                   relationship_type, weight, confidence, properties
            FROM {self._relationships_table}
            WHERE relationship_id = ANY($1)
              AND deleted_at IS NULL
        """

        async with self._pool.acquire() as conn:
            records = await conn.fetch(query, edge_ids)

        edge_map = {r["relationship_id"]: r for r in records}
        return [
            GraphEdge(
                id=edge_map[eid]["relationship_id"],
                source_id=edge_map[eid]["from_entity_id"],
                target_id=edge_map[eid]["to_entity_id"],
                edge_type=edge_map[eid]["relationship_type"],
                properties=edge_map[eid]["properties"] or {},
                weight=float(edge_map[eid]["weight"] or 1.0),
                confidence=float(edge_map[eid]["confidence"] or 1.0),
            )
            for eid in edge_ids
            if eid in edge_map
        ]
```

### 1.4 Memgraph Backend

```python
# src/platform/graph/backends/memgraph.py

from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from neo4j import GraphDatabase, Driver

from ..protocol import (
    GraphBackendProtocol, GraphNode, GraphEdge, GraphPath,
    TraversalParams, TraversalDirection
)


class MemgraphBackend(GraphBackendProtocol):
    """
    Memgraph-based graph backend.

    Uses native Cypher for graph operations.
    Optimal for complex traversals and pattern matching.
    """

    def __init__(
        self,
        uri: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self._uri = uri
        self._username = username
        self._password = password
        self._database = database
        self._driver: Optional[Driver] = None

    async def connect(self) -> None:
        """Establish connection to Memgraph."""
        auth = None
        if self._username and self._password:
            auth = (self._username, self._password)

        self._driver = GraphDatabase.driver(self._uri, auth=auth)

        # Verify connection
        with self._driver.session(database=self._database) as session:
            session.run("RETURN 1")

    async def disconnect(self) -> None:
        """Close connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    def _ensure_connected(self) -> Driver:
        if not self._driver:
            raise RuntimeError("Not connected to Memgraph")
        return self._driver

    # --- Node Operations ---

    async def create_node(
        self,
        labels: List[str],
        properties: Dict[str, Any],
        node_id: Optional[UUID] = None,
    ) -> GraphNode:
        """Create a node in Memgraph."""
        driver = self._ensure_connected()
        node_id = node_id or uuid4()

        labels_str = ":".join(labels) if labels else "Node"

        query = f"""
            CREATE (n:{labels_str} $props)
            SET n.id = $node_id
            RETURN n
        """

        with driver.session(database=self._database) as session:
            result = session.run(
                query,
                props=properties,
                node_id=str(node_id),
            )
            record = result.single()
            node = record["n"]

        return GraphNode(
            id=UUID(node["id"]),
            labels=list(node.labels),
            properties=dict(node),
        )

    async def batch_create_nodes(
        self,
        nodes: List[Dict[str, Any]],
    ) -> List[GraphNode]:
        """Batch create nodes using UNWIND."""
        if not nodes:
            return []

        driver = self._ensure_connected()
        created = []

        # Group by label combination for efficient queries
        from collections import defaultdict
        by_labels: Dict[str, List[Dict]] = defaultdict(list)

        for node_spec in nodes:
            node_id = str(node_spec.get("id") or uuid4())
            labels = node_spec.get("labels", ["Node"])
            props = {**node_spec.get("properties", {}), "id": node_id}

            labels_key = ":".join(sorted(labels))
            by_labels[labels_key].append({
                "id": node_id,
                "labels": labels,
                "props": props,
            })

        with driver.session(database=self._database) as session:
            for labels_str, group in by_labels.items():
                query = f"""
                    UNWIND $nodes AS node
                    CREATE (n:{labels_str})
                    SET n = node.props
                    RETURN n
                """

                result = session.run(query, nodes=group)
                for record in result:
                    node = record["n"]
                    created.append(GraphNode(
                        id=UUID(node["id"]),
                        labels=list(node.labels),
                        properties=dict(node),
                    ))

        return created

    # --- Traversal Operations ---

    async def traverse(
        self,
        start_node_id: UUID,
        params: TraversalParams,
    ) -> List[GraphNode]:
        """
        Traverse graph using native Cypher.
        """
        driver = self._ensure_connected()

        # Build relationship pattern
        rel_pattern = ""
        if params.edge_types:
            rel_types = "|".join(params.edge_types)
            rel_pattern = f"[:{rel_types}]"

        # Build direction pattern
        if params.direction == TraversalDirection.OUTGOING:
            pattern = f"(start)-{rel_pattern}*1..{params.max_depth}->(connected)"
        elif params.direction == TraversalDirection.INCOMING:
            pattern = f"(start)<-{rel_pattern}*1..{params.max_depth}-(connected)"
        else:
            pattern = f"(start)-{rel_pattern}*1..{params.max_depth}-(connected)"

        query = f"""
            MATCH {pattern}
            WHERE start.id = $start_id
            RETURN DISTINCT connected, length(shortestPath((start)-[*]-(connected))) as depth
            ORDER BY depth
        """

        if params.limit:
            query += f" LIMIT {params.limit}"

        with driver.session(database=self._database) as session:
            result = session.run(query, start_id=str(start_node_id))

            nodes = []
            for record in result:
                node = record["connected"]
                nodes.append(GraphNode(
                    id=UUID(node["id"]),
                    labels=list(node.labels),
                    properties=dict(node),
                    depth=record["depth"],
                ))

        return nodes

    async def find_shortest_path(
        self,
        start_node_id: UUID,
        end_node_id: UUID,
        max_depth: int = 10,
        edge_types: Optional[List[str]] = None,
    ) -> Optional[GraphPath]:
        """
        Find shortest path using native shortestPath().
        """
        driver = self._ensure_connected()

        rel_pattern = ""
        if edge_types:
            rel_types = "|".join(edge_types)
            rel_pattern = f":{rel_types}"

        query = f"""
            MATCH (start {{id: $start_id}}), (end {{id: $end_id}})
            MATCH path = shortestPath((start)-[{rel_pattern}*1..{max_depth}]-(end))
            RETURN path
        """

        with driver.session(database=self._database) as session:
            result = session.run(
                query,
                start_id=str(start_node_id),
                end_id=str(end_node_id),
            )
            record = result.single()

            if not record:
                return None

            path = record["path"]

            nodes = [
                GraphNode(
                    id=UUID(node["id"]),
                    labels=list(node.labels),
                    properties=dict(node),
                )
                for node in path.nodes
            ]

            edges = [
                GraphEdge(
                    id=UUID(rel.get("id", str(uuid4()))),
                    source_id=UUID(rel.start_node["id"]),
                    target_id=UUID(rel.end_node["id"]),
                    edge_type=rel.type,
                    properties=dict(rel),
                )
                for rel in path.relationships
            ]

            return GraphPath(
                nodes=nodes,
                edges=edges,
                total_weight=len(edges),  # Simple weight
                length=len(edges),
            )
```

### 1.5 Backend Factory

```python
# src/platform/graph/factory.py

from typing import Optional
from enum import Enum

from .protocol import GraphBackendProtocol
from .backends.postgres_cte import PostgresCTEBackend
from .backends.memgraph import MemgraphBackend


class GraphBackendType(str, Enum):
    POSTGRES_CTE = "postgres_cte"
    MEMGRAPH = "memgraph"


class GraphBackendFactory:
    """Factory for creating graph backend instances."""

    @staticmethod
    def create(
        backend_type: GraphBackendType,
        **kwargs,
    ) -> GraphBackendProtocol:
        """
        Create a graph backend instance.

        Args:
            backend_type: Type of backend to create
            **kwargs: Backend-specific configuration

        Returns:
            Configured GraphBackendProtocol instance
        """
        if backend_type == GraphBackendType.POSTGRES_CTE:
            return PostgresCTEBackend(
                connection_pool=kwargs["connection_pool"],
                schema=kwargs.get("schema", "intelligence"),
            )

        elif backend_type == GraphBackendType.MEMGRAPH:
            return MemgraphBackend(
                uri=kwargs["uri"],
                username=kwargs.get("username"),
                password=kwargs.get("password"),
                database=kwargs.get("database"),
            )

        else:
            raise ValueError(f"Unknown backend type: {backend_type}")
```

---

## 2. Pattern Engine

### 2.1 Core Models

```python
# src/platform/patterns/models.py

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from uuid import UUID
from enum import Enum
import re


class PatternCategory(str, Enum):
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    CONTEXT = "context"
    TEMPORAL = "temporal"
    QUANTITATIVE = "quantitative"


class PatternPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class PatternDefinition:
    """
    Core pattern definition for entity/relationship detection.
    """
    id: UUID
    name: str
    domain: str
    category: PatternCategory

    # Pattern specification
    regex_pattern: str
    flags: int = re.IGNORECASE

    # Output
    output_type: str
    capture_groups: Optional[Dict[str, str]] = None

    # Scoring
    base_confidence: float = 0.75
    priority: PatternPriority = PatternPriority.NORMAL

    # Context
    requires_context: Optional[List[str]] = None
    excludes_context: Optional[List[str]] = None

    # Metadata
    version: str = "1.0.0"
    description: str = ""
    examples: Optional[List[str]] = None
    tags: Optional[List[str]] = None

    # Cached compiled pattern
    _compiled: Optional[re.Pattern] = field(default=None, repr=False)

    @property
    def compiled(self) -> re.Pattern:
        if self._compiled is None:
            self._compiled = re.compile(self.regex_pattern, self.flags)
        return self._compiled


@dataclass
class PatternMatch:
    """Result of pattern matching."""
    pattern_id: UUID
    pattern_name: str
    domain: str
    category: PatternCategory

    matched_text: str
    start_position: int
    end_position: int

    output_type: str
    output_value: str
    captured_groups: Optional[Dict[str, str]] = None

    base_confidence: float = 0.75
    final_confidence: float = 0.75
    applied_factors: Optional[List[Dict[str, Any]]] = None

    surrounding_context: str = ""
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConfidenceFactor:
    """Factor that adjusts confidence scores."""
    name: str
    description: str
    weight: float
    detector: str
    is_positive: bool = True
    max_adjustment: float = 0.2
    applies_to_categories: Optional[List[PatternCategory]] = None
    applies_to_domains: Optional[List[str]] = None
```

### 2.2 Pattern Engine

See [Strategic Design](./STRATEGIC_DESIGN.md) for the complete Pattern Engine implementation. Key methods:

- `detect_patterns(text, domains, categories, min_confidence)` - Main detection entry point
- `detect_entities(text, domains, min_confidence)` - Entity-specific detection
- `detect_relationships(text, entities, domains, min_confidence)` - Relationship detection
- `process_document(document_text, document_id, domains)` - Full document processing

### 2.3 Confidence Scoring

Built-in factors:
- `monetary_context` - Nearby monetary amounts (+0.15)
- `percentage_context` - Nearby percentages (+0.10)
- `temporal_proximity` - Nearby temporal references (+0.10)
- `negation_presence` - Negation words (-0.20)
- `uncertainty_markers` - Uncertainty words (-0.15)
- `keyword_density` - Domain keyword density (+0.10)
- `multi_occurrence` - Multiple occurrences (+0.10)
- `relationship_support` - Participates in relationships (+0.15)

---

## 3. Domain Module System

### 3.1 Base Domain

```python
# src/platform/domains/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..patterns.models import PatternDefinition, ConfidenceFactor


@dataclass
class EntityTypeDefinition:
    """Defines an entity type within a domain."""
    name: str
    description: str
    required_properties: List[str]
    optional_properties: List[str] = None
    parent_type: Optional[str] = None


@dataclass
class RelationshipTypeDefinition:
    """Defines a relationship type within a domain."""
    name: str
    description: str
    valid_source_types: List[str]
    valid_target_types: List[str]
    properties: List[str] = None
    cardinality: str = "many_to_many"
    is_bidirectional: bool = False


class BaseDomain(ABC):
    """
    Abstract base class for all platform domains.

    Domains define:
    - Entity types
    - Relationship types
    - Patterns for detection
    - Confidence factors
    - Custom operations
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique domain identifier."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Domain schema version."""
        ...

    @property
    @abstractmethod
    def entity_types(self) -> List[EntityTypeDefinition]:
        """Entity types defined in this domain."""
        ...

    @property
    @abstractmethod
    def relationship_types(self) -> List[RelationshipTypeDefinition]:
        """Relationship types defined in this domain."""
        ...

    @property
    def patterns(self) -> List[PatternDefinition]:
        """Patterns for entity/relationship detection."""
        return []

    @property
    def confidence_factors(self) -> List[ConfidenceFactor]:
        """Domain-specific confidence factors."""
        return []

    @property
    def depends_on(self) -> List[str]:
        """Other domains this domain depends on."""
        return []

    # --- Lifecycle Hooks ---

    async def on_entity_create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Called before entity creation."""
        return entity

    async def on_relationship_create(self, rel: Dict[str, Any]) -> Dict[str, Any]:
        """Called before relationship creation."""
        return rel

    # --- Validation ---

    def validate_entity(self, entity_type: str, properties: Dict) -> List[str]:
        """Validate entity against domain schema. Returns list of errors."""
        errors = []

        entity_def = self._get_entity_type(entity_type)
        if not entity_def:
            errors.append(f"Unknown entity type: {entity_type}")
            return errors

        for prop in entity_def.required_properties:
            if prop not in properties:
                errors.append(f"Missing required property: {prop}")

        return errors

    # --- Custom Operations ---

    async def execute_operation(
        self,
        operation: str,
        params: Dict[str, Any],
    ) -> Any:
        """Execute a domain-specific operation."""
        raise NotImplementedError(f"Operation '{operation}' not implemented")

    def get_supported_operations(self) -> List[str]:
        """List of supported custom operations."""
        return []

    # --- Helpers ---

    def _get_entity_type(self, name: str) -> Optional[EntityTypeDefinition]:
        for et in self.entity_types:
            if et.name == name:
                return et
        return None
```

### 3.2 Domain Registry

```python
# src/platform/domains/registry.py

from typing import Dict, List, Optional
import asyncio

from .base import BaseDomain


class DomainRegistry:
    """
    Central registry for all domains in the platform.
    """

    def __init__(self):
        self._domains: Dict[str, BaseDomain] = {}
        self._lock = asyncio.Lock()

    async def register(self, domain: BaseDomain) -> None:
        """Register a domain."""
        async with self._lock:
            # Validate dependencies
            for dep in domain.depends_on:
                if dep not in self._domains:
                    raise ValueError(
                        f"Domain '{domain.name}' depends on '{dep}' which is not registered"
                    )

            self._domains[domain.name] = domain

    async def unregister(self, domain_name: str) -> None:
        """Unregister a domain."""
        async with self._lock:
            # Check no other domains depend on this
            for name, domain in self._domains.items():
                if domain_name in domain.depends_on:
                    raise ValueError(
                        f"Cannot unregister '{domain_name}': '{name}' depends on it"
                    )

            del self._domains[domain_name]

    def get(self, name: str) -> Optional[BaseDomain]:
        """Get a domain by name."""
        return self._domains.get(name)

    def list_domains(self) -> List[str]:
        """List all registered domain names."""
        return list(self._domains.keys())

    def get_all_patterns(self, domains: Optional[List[str]] = None) -> List:
        """Get all patterns from specified domains (or all)."""
        patterns = []

        target_domains = domains or list(self._domains.keys())

        for name in target_domains:
            domain = self._domains.get(name)
            if domain:
                patterns.extend(domain.patterns)

        return patterns
```

---

## 4. Core Orchestrator

See [Strategic Design](./STRATEGIC_DESIGN.md) for the complete Core Orchestrator implementation.

Key extension points for applications:
- `on_query_received(context)` - Modify context before planning
- `select_strategy(context)` - Override strategy selection
- `on_plan_created(plan, context)` - Modify execution plan
- `on_results_ready(result, context)` - Post-process results

---

## 5. Security Domain (Priority)

### 5.1 Domain Definition

```python
# src/platform/domains/security/domain.py

from uuid import uuid4
from typing import List

from ..base import BaseDomain, EntityTypeDefinition, RelationshipTypeDefinition
from ...patterns.models import PatternDefinition, PatternCategory, ConfidenceFactor


class SecurityDomain(BaseDomain):
    """
    Security domain for vulnerability, threat, and compliance analysis.

    This is the priority domain for initial implementation.
    """

    name = "security"
    display_name = "Security & Compliance"
    version = "1.0.0"

    entity_types = [
        EntityTypeDefinition(
            name="vulnerability",
            description="Security vulnerability (CVE, etc.)",
            required_properties=["name"],
            optional_properties=["cve_id", "severity", "cvss_score", "description", "affected_systems"],
        ),
        EntityTypeDefinition(
            name="threat",
            description="Threat actor or attack vector",
            required_properties=["name"],
            optional_properties=["threat_type", "description", "indicators"],
        ),
        EntityTypeDefinition(
            name="control",
            description="Security control (preventive, detective, corrective)",
            required_properties=["name", "control_type"],
            optional_properties=["description", "implementation_status", "effectiveness"],
        ),
        EntityTypeDefinition(
            name="compliance_requirement",
            description="Compliance requirement (SOC2, HIPAA, etc.)",
            required_properties=["name", "framework"],
            optional_properties=["description", "control_family", "requirement_id"],
        ),
        EntityTypeDefinition(
            name="encryption_config",
            description="Encryption configuration",
            required_properties=["name", "algorithm"],
            optional_properties=["key_length", "key_management", "scope"],
        ),
        EntityTypeDefinition(
            name="access_policy",
            description="IAM policy or access rule",
            required_properties=["name"],
            optional_properties=["policy_type", "principals", "resources", "actions", "conditions"],
        ),
        EntityTypeDefinition(
            name="security_group",
            description="Network security group or firewall rule",
            required_properties=["name"],
            optional_properties=["ingress_rules", "egress_rules", "vpc"],
        ),
        EntityTypeDefinition(
            name="security_finding",
            description="Security scan finding or alert",
            required_properties=["name", "severity"],
            optional_properties=["finding_type", "resource", "remediation", "status"],
        ),
        EntityTypeDefinition(
            name="identity",
            description="User, role, or service account",
            required_properties=["name", "identity_type"],
            optional_properties=["arn", "policies", "groups", "mfa_enabled"],
        ),
    ]

    relationship_types = [
        RelationshipTypeDefinition(
            name="mitigates",
            description="Control mitigates vulnerability or threat",
            valid_source_types=["control"],
            valid_target_types=["vulnerability", "threat"],
            properties=["effectiveness", "implementation_date"],
        ),
        RelationshipTypeDefinition(
            name="exposes",
            description="Configuration exposes to vulnerability or threat",
            valid_source_types=["encryption_config", "access_policy", "security_group"],
            valid_target_types=["vulnerability", "threat"],
            properties=["risk_level"],
        ),
        RelationshipTypeDefinition(
            name="requires",
            description="Entity requires compliance requirement",
            valid_source_types=["control", "encryption_config", "access_policy"],
            valid_target_types=["compliance_requirement"],
        ),
        RelationshipTypeDefinition(
            name="implements",
            description="Control implements compliance requirement",
            valid_source_types=["control"],
            valid_target_types=["compliance_requirement"],
            properties=["coverage_percentage"],
        ),
        RelationshipTypeDefinition(
            name="violates",
            description="Finding violates policy or requirement",
            valid_source_types=["security_finding"],
            valid_target_types=["access_policy", "compliance_requirement"],
        ),
        RelationshipTypeDefinition(
            name="protects",
            description="Control or encryption protects resource",
            valid_source_types=["control", "encryption_config", "security_group"],
            valid_target_types=["identity", "security_group"],
        ),
        RelationshipTypeDefinition(
            name="grants_access",
            description="Policy grants access to identity",
            valid_source_types=["access_policy"],
            valid_target_types=["identity"],
            properties=["permission_level"],
        ),
    ]

    @property
    def patterns(self) -> List[PatternDefinition]:
        return SECURITY_PATTERNS

    @property
    def confidence_factors(self) -> List[ConfidenceFactor]:
        return SECURITY_CONFIDENCE_FACTORS

    # --- Custom Operations ---

    def get_supported_operations(self) -> List[str]:
        return [
            "find_unmitigated_vulnerabilities",
            "check_compliance_coverage",
            "trace_access_path",
            "find_encryption_gaps",
        ]

    async def execute_operation(self, operation: str, params: dict) -> any:
        if operation == "find_unmitigated_vulnerabilities":
            return await self._find_unmitigated(params)
        elif operation == "check_compliance_coverage":
            return await self._check_compliance(params)
        elif operation == "trace_access_path":
            return await self._trace_access(params)
        elif operation == "find_encryption_gaps":
            return await self._find_encryption_gaps(params)
        raise NotImplementedError(f"Operation '{operation}' not implemented")


# --- Security Patterns ---

SECURITY_PATTERNS = [
    # CVE Pattern
    PatternDefinition(
        id=uuid4(),
        name="cve_reference",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\bCVE-\d{4}-\d{4,7}\b",
        output_type="vulnerability",
        base_confidence=0.95,
        description="CVE identifier reference",
        examples=["CVE-2021-44228", "CVE-2023-12345"],
    ),

    # IAM/Identity Patterns
    PatternDefinition(
        id=uuid4(),
        name="iam_policy",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\b(?:IAM\s+)?(?:policy|role|permission|principal)(?:\s+\w+){0,3}\b",
        output_type="access_policy",
        base_confidence=0.75,
        description="IAM policy reference",
    ),

    # Encryption Patterns
    PatternDefinition(
        id=uuid4(),
        name="encryption_reference",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\b(?:AES|RSA|TLS|SSL|KMS|encrypt(?:ion)?|decrypt(?:ion)?)-?\d*\b",
        output_type="encryption_config",
        base_confidence=0.80,
        description="Encryption reference",
    ),

    # Compliance Framework Patterns
    PatternDefinition(
        id=uuid4(),
        name="compliance_framework",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\b(?:SOC\s*2|HIPAA|PCI[\s-]DSS|GDPR|ISO\s*27001|FedRAMP|NIST)\b",
        output_type="compliance_requirement",
        base_confidence=0.90,
        description="Compliance framework reference",
    ),

    # Security Group Patterns
    PatternDefinition(
        id=uuid4(),
        name="security_group",
        domain="security",
        category=PatternCategory.ENTITY,
        regex_pattern=r"\b(?:security\s+group|firewall|ingress|egress|sg-[a-f0-9]+)\b",
        output_type="security_group",
        base_confidence=0.80,
        description="Security group reference",
    ),

    # Severity Patterns (Context)
    PatternDefinition(
        id=uuid4(),
        name="severity_indicator",
        domain="security",
        category=PatternCategory.CONTEXT,
        regex_pattern=r"\b(?:critical|high|medium|low|informational)\s+(?:severity|risk|priority)\b",
        output_type="severity",
        base_confidence=0.85,
        description="Severity indicator",
    ),

    # CVSS Score Pattern (Context)
    PatternDefinition(
        id=uuid4(),
        name="cvss_score",
        domain="security",
        category=PatternCategory.CONTEXT,
        regex_pattern=r"\bCVSS[:\s]*(\d+\.?\d*)\b",
        output_type="cvss_score",
        base_confidence=0.90,
        description="CVSS score",
    ),

    # Relationship: Mitigates
    PatternDefinition(
        id=uuid4(),
        name="mitigates_relationship",
        domain="security",
        category=PatternCategory.RELATIONSHIP,
        regex_pattern=r"(?P<source>\b\w+(?:\s+\w+){0,3})\s+(?:mitigates?|addresses?|fixes?|patches?|remediates?)\s+(?P<target>\b\w+(?:\s+\w+){0,3})",
        output_type="mitigates",
        base_confidence=0.75,
        description="Mitigation relationship",
    ),

    # Relationship: Protects
    PatternDefinition(
        id=uuid4(),
        name="protects_relationship",
        domain="security",
        category=PatternCategory.RELATIONSHIP,
        regex_pattern=r"(?P<source>\b\w+(?:\s+\w+){0,3})\s+(?:protects?|secures?|guards?)\s+(?P<target>\b\w+(?:\s+\w+){0,3})",
        output_type="protects",
        base_confidence=0.75,
        description="Protection relationship",
    ),
]


# --- Security Confidence Factors ---

SECURITY_CONFIDENCE_FACTORS = [
    ConfidenceFactor(
        name="severity_context",
        description="Nearby severity indicators boost confidence",
        weight=0.15,
        detector="detect_severity_context",
        is_positive=True,
        max_adjustment=0.15,
        applies_to_domains=["security"],
    ),
    ConfidenceFactor(
        name="cve_reference",
        description="CVE reference nearby boosts confidence",
        weight=0.15,
        detector="detect_cve_context",
        is_positive=True,
        max_adjustment=0.15,
        applies_to_domains=["security"],
    ),
    ConfidenceFactor(
        name="compliance_framework",
        description="Compliance framework reference boosts confidence",
        weight=0.10,
        detector="detect_compliance_context",
        is_positive=True,
        max_adjustment=0.10,
        applies_to_domains=["security"],
    ),
]
```

---

## 6. API Specifications

### 6.1 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/entities` | POST | Create entity |
| `/api/v1/entities/batch` | POST | Batch create entities |
| `/api/v1/entities/{id}` | GET | Get entity by ID |
| `/api/v1/entities/{id}` | PUT | Update entity |
| `/api/v1/entities/{id}` | DELETE | Delete entity |
| `/api/v1/entities/search` | POST | Search entities |
| `/api/v1/relationships` | POST | Create relationship |
| `/api/v1/relationships/batch` | POST | Batch create relationships |
| `/api/v1/relationships/{id}` | GET | Get relationship by ID |
| `/api/v1/graph/traverse` | POST | Traverse graph |
| `/api/v1/graph/path` | POST | Find path between nodes |
| `/api/v1/graph/subgraph` | POST | Extract subgraph |
| `/api/v1/search/vector` | POST | Vector similarity search |
| `/api/v1/search/hybrid` | POST | Hybrid vector + keyword search |
| `/api/v1/patterns` | GET | List patterns |
| `/api/v1/patterns` | POST | Register pattern |
| `/api/v1/patterns/detect` | POST | Detect patterns in text |
| `/api/v1/domains` | GET | List domains |
| `/api/v1/domains/{name}` | GET | Get domain details |
| `/api/v1/domains/{name}/operations/{op}` | POST | Execute domain operation |
| `/api/v1/ingest` | POST | Ingest document |
| `/api/v1/orchestrate` | POST | Query orchestration |

### 6.2 Request/Response Examples

See OpenAPI specification (to be generated).

---

## 7. Database Schema

### 7.1 Core Tables

```sql
-- Intelligence schema
CREATE SCHEMA IF NOT EXISTS intelligence;

-- Entities table
CREATE TABLE intelligence.entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    embedding vector(384),
    embedding_model VARCHAR(100),
    domain VARCHAR(100),
    confidence DECIMAL(3,2) DEFAULT 1.0,
    source_document_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT valid_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- Relationships table
CREATE TABLE intelligence.relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    from_entity_id UUID NOT NULL REFERENCES intelligence.entities(entity_id),
    to_entity_id UUID NOT NULL REFERENCES intelligence.entities(entity_id),
    relationship_type VARCHAR(100) NOT NULL,
    weight DECIMAL(3,2) DEFAULT 1.0,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    properties JSONB DEFAULT '{}',
    evidence TEXT,
    domain VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT no_self_loop CHECK (from_entity_id != to_entity_id),
    CONSTRAINT valid_weight CHECK (weight >= 0 AND weight <= 1),
    CONSTRAINT valid_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- Patterns table
CREATE TABLE intelligence.patterns (
    pattern_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    domain VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    regex_pattern TEXT NOT NULL,
    output_type VARCHAR(100) NOT NULL,
    base_confidence DECIMAL(3,2) DEFAULT 0.75,
    priority VARCHAR(20) DEFAULT 'normal',
    version VARCHAR(20) DEFAULT '1.0.0',
    description TEXT,
    examples TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_pattern_name UNIQUE (domain, name, version)
);

-- Domains table
CREATE TABLE intelligence.domains (
    domain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    entity_types JSONB NOT NULL DEFAULT '[]',
    relationship_types JSONB NOT NULL DEFAULT '[]',
    depends_on TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_entities_tenant ON intelligence.entities(tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_type ON intelligence.entities(entity_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_domain ON intelligence.entities(domain) WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_embedding ON intelligence.entities USING ivfflat (embedding vector_cosine_ops) WHERE deleted_at IS NULL;

CREATE INDEX idx_relationships_tenant ON intelligence.relationships(tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_relationships_from ON intelligence.relationships(from_entity_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_relationships_to ON intelligence.relationships(to_entity_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_relationships_type ON intelligence.relationships(relationship_type) WHERE deleted_at IS NULL;

CREATE INDEX idx_patterns_domain ON intelligence.patterns(domain) WHERE is_active = TRUE;
CREATE INDEX idx_patterns_category ON intelligence.patterns(category) WHERE is_active = TRUE;
```

---

## 8. SDK Design

### 8.1 Python SDK

```python
# intelligence_builder_sdk/client.py

from typing import Optional, List, Dict, Any
from uuid import UUID
import httpx

from .models import Entity, Relationship, GraphNode, GraphPath, PatternMatch


class IBPlatformClient:
    """
    Intelligence-Builder Platform SDK Client.

    Provides easy access to all platform capabilities.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        tenant_id: str,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Tenant-ID": tenant_id,
            },
            timeout=timeout,
        )

        # Sub-clients
        self.entities = EntityClient(self._client)
        self.relationships = RelationshipClient(self._client)
        self.graph = GraphClient(self._client)
        self.search = SearchClient(self._client)
        self.patterns = PatternClient(self._client)
        self.domains = DomainClient(self._client)
        self.ingest = IngestClient(self._client)
        self.orchestrate = OrchestrationClient(self._client)

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


class EntityClient:
    """Entity operations."""

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def create(
        self,
        entity_type: str,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
        domain: Optional[str] = None,
        embedding: Optional[List[float]] = None,
    ) -> Entity:
        """Create an entity."""
        response = await self._client.post(
            "/api/v1/entities",
            json={
                "entity_type": entity_type,
                "name": name,
                "properties": properties or {},
                "domain": domain,
                "embedding": embedding,
            },
        )
        response.raise_for_status()
        return Entity(**response.json())

    async def get(self, entity_id: UUID) -> Optional[Entity]:
        """Get entity by ID."""
        response = await self._client.get(f"/api/v1/entities/{entity_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return Entity(**response.json())

    async def batch_create(
        self,
        entities: List[Dict[str, Any]],
    ) -> List[Entity]:
        """Batch create entities."""
        response = await self._client.post(
            "/api/v1/entities/batch",
            json={"entities": entities},
        )
        response.raise_for_status()
        return [Entity(**e) for e in response.json()["entities"]]


class GraphClient:
    """Graph operations."""

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def traverse(
        self,
        start_node_id: UUID,
        max_depth: int = 3,
        direction: str = "both",
        edge_types: Optional[List[str]] = None,
    ) -> List[GraphNode]:
        """Traverse graph from starting node."""
        response = await self._client.post(
            "/api/v1/graph/traverse",
            json={
                "start_node_id": str(start_node_id),
                "max_depth": max_depth,
                "direction": direction,
                "edge_types": edge_types,
            },
        )
        response.raise_for_status()
        return [GraphNode(**n) for n in response.json()["nodes"]]

    async def find_path(
        self,
        start_id: UUID,
        end_id: UUID,
        max_depth: int = 10,
    ) -> Optional[GraphPath]:
        """Find shortest path between nodes."""
        response = await self._client.post(
            "/api/v1/graph/path",
            json={
                "start_node_id": str(start_id),
                "end_node_id": str(end_id),
                "max_depth": max_depth,
            },
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("path"):
            return None
        return GraphPath(**data["path"])
```

---

## References

- [Project Goals](./PROJECT_GOALS.md)
- [Strategic Design](./STRATEGIC_DESIGN.md)
- [Implementation Plan](./IMPLEMENTATION_PLAN.md)
