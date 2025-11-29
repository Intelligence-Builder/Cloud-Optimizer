"""
PostgreSQL CTE-based Graph Backend.

Uses recursive Common Table Expressions for graph traversal.
This is the default backend - no additional infrastructure required.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import asyncpg

from ..protocol import (
    GraphBackendProtocol,
    GraphEdge,
    GraphNode,
    GraphPath,
    TraversalDirection,
    TraversalParams,
)

logger = logging.getLogger(__name__)


def _parse_json_field(value: Any) -> Dict[str, Any]:
    """Parse a JSON field that may be a dict or JSON string."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}


class PostgresCTEBackend:
    """
    PostgreSQL CTE-based graph backend.

    Uses recursive Common Table Expressions for graph traversal.
    This is the default backend - no additional infrastructure required.

    Tables used:
        - intelligence.entities
        - intelligence.relationships
    """

    def __init__(
        self,
        connection_pool: asyncpg.Pool,
        schema: str = "intelligence",
        entities_table: str = "entities",
        relationships_table: str = "relationships",
    ) -> None:
        """
        Initialize PostgreSQL CTE backend.

        Args:
            connection_pool: asyncpg connection pool
            schema: Database schema name
            entities_table: Name of entities table
            relationships_table: Name of relationships table
        """
        self._pool = connection_pool
        self._schema = schema
        self._entities_table = f"{schema}.{entities_table}"
        self._relationships_table = f"{schema}.{relationships_table}"
        self._connected = False

    async def connect(self) -> None:
        """Verify connection is available."""
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("SELECT 1")
            self._connected = True
            logger.info("PostgresCTEBackend connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise ConnectionError(f"Failed to verify PostgreSQL connection: {e}") from e

    async def disconnect(self) -> None:
        """No-op for pooled connections."""
        self._connected = False
        logger.info("PostgresCTEBackend disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if backend is connected."""
        return self._connected

    def _ensure_connected(self) -> None:
        """Ensure backend is connected."""
        if not self._connected:
            raise RuntimeError("Backend not connected. Call connect() first.")

    # --- Node Operations ---

    async def create_node(
        self,
        labels: List[str],
        properties: Dict[str, Any],
        node_id: Optional[UUID] = None,
    ) -> GraphNode:
        """
        Create a node in the entities table.

        Args:
            labels: List of labels for the node
            properties: Node properties
            node_id: Optional specific UUID to use

        Returns:
            Created GraphNode
        """
        self._ensure_connected()

        if not labels:
            raise ValueError("labels cannot be empty")

        node_id = node_id or uuid4()

        # Extract standard fields
        entity_type = labels[0]
        name = properties.pop("name", str(node_id))
        description = properties.pop("description", None)

        query = f"""
            INSERT INTO {self._entities_table}
            (entity_id, entity_type, name, description, metadata, tags)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING entity_id, entity_type, name, description, metadata, tags, created_at
        """

        try:
            async with self._pool.acquire() as conn:
                record = await conn.fetchrow(
                    query,
                    node_id,
                    entity_type,
                    name,
                    description,
                    json.dumps(properties),  # Serialize to JSON for JSONB column
                    labels,  # Labels stored as tags (TEXT[] array)
                )

            logger.debug(f"Created node {node_id} with labels {labels}")

            return GraphNode(
                id=record["entity_id"],
                labels=record["tags"] or [],
                properties={
                    "name": record["name"],
                    "description": record["description"],
                    **_parse_json_field(record["metadata"]),
                },
            )
        except Exception as e:
            logger.error(f"Failed to create node: {e}")
            raise

    async def get_node(self, node_id: UUID) -> Optional[GraphNode]:
        """Get a node by ID."""
        self._ensure_connected()

        query = f"""
            SELECT entity_id, entity_type, name, description, metadata, tags
            FROM {self._entities_table}
            WHERE entity_id = $1
              AND deleted_at IS NULL
        """

        async with self._pool.acquire() as conn:
            record = await conn.fetchrow(query, node_id)

        if not record:
            return None

        return GraphNode(
            id=record["entity_id"],
            labels=record["tags"] or [record["entity_type"]],
            properties={
                "name": record["name"],
                "description": record["description"],
                **_parse_json_field(record["metadata"]),
            },
        )

    async def update_node(
        self,
        node_id: UUID,
        properties: Dict[str, Any],
        merge: bool = True,
    ) -> GraphNode:
        """Update node properties."""
        self._ensure_connected()

        # Get current node
        current = await self.get_node(node_id)
        if not current:
            raise ValueError(f"Node {node_id} not found")

        # Merge or replace properties
        if merge:
            new_props = {**current.properties, **properties}
        else:
            new_props = properties

        # Extract standard fields
        name = new_props.pop("name", current.properties.get("name"))
        description = new_props.pop(
            "description", current.properties.get("description")
        )

        query = f"""
            UPDATE {self._entities_table}
            SET name = $2,
                description = $3,
                metadata = $4,
                updated_at = NOW()
            WHERE entity_id = $1
              AND deleted_at IS NULL
            RETURNING entity_id, entity_type, name, description, metadata, tags
        """

        async with self._pool.acquire() as conn:
            record = await conn.fetchrow(
                query, node_id, name, description, json.dumps(new_props)
            )

        if not record:
            raise ValueError(f"Node {node_id} not found or deleted")

        logger.debug(f"Updated node {node_id}")

        return GraphNode(
            id=record["entity_id"],
            labels=record["tags"] or [record["entity_type"]],
            properties={
                "name": record["name"],
                "description": record["description"],
                **_parse_json_field(record["metadata"]),
            },
        )

    async def delete_node(self, node_id: UUID, soft: bool = True) -> bool:
        """Delete a node."""
        self._ensure_connected()

        if soft:
            query = f"""
                UPDATE {self._entities_table}
                SET deleted_at = NOW()
                WHERE entity_id = $1
                  AND deleted_at IS NULL
            """
        else:
            query = f"""
                DELETE FROM {self._entities_table}
                WHERE entity_id = $1
            """

        async with self._pool.acquire() as conn:
            result = await conn.execute(query, node_id)

        deleted = result.split()[-1] == "1"
        if deleted:
            logger.debug(f"{'Soft' if soft else 'Hard'} deleted node {node_id}")
        return deleted

    async def batch_create_nodes(
        self,
        nodes: List[Dict[str, Any]],
    ) -> List[GraphNode]:
        """Batch create nodes using multi-value INSERT."""
        self._ensure_connected()

        if not nodes:
            return []

        created = []

        # Process in batches of 1000
        batch_size = 1000
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i : i + batch_size]

            # Build multi-value INSERT
            values = []
            params = []
            param_idx = 1

            for node_spec in batch:
                node_id = node_spec.get("id") or uuid4()
                labels = node_spec.get("labels", ["entity"])
                props = node_spec.get("properties", {}).copy()

                if not labels:
                    raise ValueError("Each node must have at least one label")

                entity_type = labels[0]
                name = props.pop("name", str(node_id))
                description = props.pop("description", None)

                values.append(
                    f"(${param_idx}, ${param_idx+1}, ${param_idx+2}, "
                    f"${param_idx+3}, ${param_idx+4}, ${param_idx+5})"
                )
                params.extend(
                    [node_id, entity_type, name, description, json.dumps(props), labels]
                )  # Serialize props to JSON
                param_idx += 6

            query = f"""
                INSERT INTO {self._entities_table}
                (entity_id, entity_type, name, description, metadata, tags)
                VALUES {', '.join(values)}
                RETURNING entity_id, entity_type, name, description, metadata, tags
            """

            async with self._pool.acquire() as conn:
                records = await conn.fetch(query, *params)

            for record in records:
                created.append(
                    GraphNode(
                        id=record["entity_id"],
                        labels=record["tags"] or [],
                        properties={
                            "name": record["name"],
                            "description": record["description"],
                            **_parse_json_field(record["metadata"]),
                        },
                    )
                )

        logger.info(f"Batch created {len(created)} nodes")
        return created

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
        self._ensure_connected()

        if not edge_type:
            raise ValueError("edge_type cannot be empty")

        edge_id = edge_id or uuid4()
        properties = properties or {}

        # Extract standard fields
        weight = properties.pop("weight", 1.0)
        confidence = properties.pop("confidence", 1.0)

        query = f"""
            INSERT INTO {self._relationships_table}
            (relationship_id, from_entity_id, to_entity_id, relationship_type,
             weight, confidence, properties)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING relationship_id, from_entity_id, to_entity_id,
                      relationship_type, weight, confidence, properties
        """

        try:
            async with self._pool.acquire() as conn:
                record = await conn.fetchrow(
                    query,
                    edge_id,
                    source_id,
                    target_id,
                    edge_type,
                    weight,
                    confidence,
                    json.dumps(properties),  # Serialize to JSON for JSONB column
                )

            logger.debug(f"Created edge {edge_id}: {source_id} -> {target_id}")

            return GraphEdge(
                id=record["relationship_id"],
                source_id=record["from_entity_id"],
                target_id=record["to_entity_id"],
                edge_type=record["relationship_type"],
                properties=_parse_json_field(record["properties"]),
                weight=float(record["weight"]),
                confidence=float(record["confidence"]),
            )
        except Exception as e:
            logger.error(f"Failed to create edge: {e}")
            raise

    async def get_edge(self, edge_id: UUID) -> Optional[GraphEdge]:
        """Get an edge by ID."""
        self._ensure_connected()

        query = f"""
            SELECT relationship_id, from_entity_id, to_entity_id,
                   relationship_type, weight, confidence, properties
            FROM {self._relationships_table}
            WHERE relationship_id = $1
              AND deleted_at IS NULL
        """

        async with self._pool.acquire() as conn:
            record = await conn.fetchrow(query, edge_id)

        if not record:
            return None

        return GraphEdge(
            id=record["relationship_id"],
            source_id=record["from_entity_id"],
            target_id=record["to_entity_id"],
            edge_type=record["relationship_type"],
            properties=_parse_json_field(record["properties"]),
            weight=float(record["weight"] or 1.0),
            confidence=float(record["confidence"] or 1.0),
        )

    async def update_edge(
        self,
        edge_id: UUID,
        properties: Dict[str, Any],
        merge: bool = True,
    ) -> GraphEdge:
        """Update edge properties."""
        self._ensure_connected()

        # Get current edge
        current = await self.get_edge(edge_id)
        if not current:
            raise ValueError(f"Edge {edge_id} not found")

        # Merge or replace properties
        if merge:
            new_props = {**current.properties, **properties}
        else:
            new_props = properties

        # Extract standard fields
        weight = new_props.pop("weight", current.weight)
        confidence = new_props.pop("confidence", current.confidence)

        query = f"""
            UPDATE {self._relationships_table}
            SET weight = $2,
                confidence = $3,
                properties = $4,
                updated_at = NOW()
            WHERE relationship_id = $1
              AND deleted_at IS NULL
            RETURNING relationship_id, from_entity_id, to_entity_id,
                      relationship_type, weight, confidence, properties
        """

        async with self._pool.acquire() as conn:
            record = await conn.fetchrow(
                query, edge_id, weight, confidence, json.dumps(new_props)
            )

        if not record:
            raise ValueError(f"Edge {edge_id} not found or deleted")

        logger.debug(f"Updated edge {edge_id}")

        return GraphEdge(
            id=record["relationship_id"],
            source_id=record["from_entity_id"],
            target_id=record["to_entity_id"],
            edge_type=record["relationship_type"],
            properties=_parse_json_field(record["properties"]),
            weight=float(record["weight"]),
            confidence=float(record["confidence"]),
        )

    async def delete_edge(self, edge_id: UUID, soft: bool = True) -> bool:
        """Delete an edge."""
        self._ensure_connected()

        if soft:
            query = f"""
                UPDATE {self._relationships_table}
                SET deleted_at = NOW()
                WHERE relationship_id = $1
                  AND deleted_at IS NULL
            """
        else:
            query = f"""
                DELETE FROM {self._relationships_table}
                WHERE relationship_id = $1
            """

        async with self._pool.acquire() as conn:
            result = await conn.execute(query, edge_id)

        deleted = result.split()[-1] == "1"
        if deleted:
            logger.debug(f"{'Soft' if soft else 'Hard'} deleted edge {edge_id}")
        return deleted

    async def batch_create_edges(
        self,
        edges: List[Dict[str, Any]],
    ) -> List[GraphEdge]:
        """Batch create edges using multi-value INSERT."""
        self._ensure_connected()

        if not edges:
            return []

        created = []

        # Process in batches of 1000
        batch_size = 1000
        for i in range(0, len(edges), batch_size):
            batch = edges[i : i + batch_size]

            values = []
            params = []
            param_idx = 1

            for edge_spec in batch:
                edge_id = edge_spec.get("id") or uuid4()
                source_id = edge_spec.get("source_id")
                target_id = edge_spec.get("target_id")
                edge_type = edge_spec.get("edge_type")
                props = edge_spec.get("properties", {}).copy()

                if not all([source_id, target_id, edge_type]):
                    raise ValueError(
                        "Each edge must have source_id, target_id, and edge_type"
                    )

                weight = props.pop("weight", 1.0)
                confidence = props.pop("confidence", 1.0)

                values.append(
                    f"(${param_idx}, ${param_idx+1}, ${param_idx+2}, "
                    f"${param_idx+3}, ${param_idx+4}, ${param_idx+5}, ${param_idx+6})"
                )
                params.extend(
                    [
                        edge_id,
                        source_id,
                        target_id,
                        edge_type,
                        weight,
                        confidence,
                        json.dumps(props),
                    ]  # Serialize to JSON for JSONB column
                )
                param_idx += 7

            query = f"""
                INSERT INTO {self._relationships_table}
                (relationship_id, from_entity_id, to_entity_id, relationship_type,
                 weight, confidence, properties)
                VALUES {', '.join(values)}
                RETURNING relationship_id, from_entity_id, to_entity_id,
                          relationship_type, weight, confidence, properties
            """

            async with self._pool.acquire() as conn:
                records = await conn.fetch(query, *params)

            for record in records:
                created.append(
                    GraphEdge(
                        id=record["relationship_id"],
                        source_id=record["from_entity_id"],
                        target_id=record["to_entity_id"],
                        edge_type=record["relationship_type"],
                        properties=_parse_json_field(record["properties"]),
                        weight=float(record["weight"]),
                        confidence=float(record["confidence"]),
                    )
                )

        logger.info(f"Batch created {len(created)} edges")
        return created

    # --- Traversal Operations ---

    async def traverse(
        self,
        start_node_id: UUID,
        params: TraversalParams,
    ) -> List[GraphNode]:
        """Traverse graph using recursive CTE."""
        self._ensure_connected()

        # Build direction-specific join condition
        if params.direction == TraversalDirection.OUTGOING:
            rel_filter = "r.from_entity_id = node.entity_id"
            next_entity = "r.to_entity_id"
        elif params.direction == TraversalDirection.INCOMING:
            rel_filter = "r.to_entity_id = node.entity_id"
            next_entity = "r.from_entity_id"
        else:  # BOTH
            rel_filter = (
                "(r.from_entity_id = node.entity_id OR r.to_entity_id = node.entity_id)"
            )
            next_entity = """
                CASE
                    WHEN r.from_entity_id = node.entity_id THEN r.to_entity_id
                    ELSE r.from_entity_id
                END
            """

        # Build edge type filter
        type_filter = ""
        query_params: List[Any] = [start_node_id, params.max_depth]

        if params.edge_types:
            placeholders = ", ".join(
                [f"${i}" for i in range(3, 3 + len(params.edge_types))]
            )
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

        nodes = [
            GraphNode(
                id=r["entity_id"],
                labels=r["tags"] or [r["entity_type"]],
                properties={"name": r["name"], **_parse_json_field(r["metadata"])},
                depth=r["depth"],
                path=r["path"],
            )
            for r in records
        ]

        logger.debug(
            f"Traversed from {start_node_id}, found {len(nodes)} nodes at max depth {params.max_depth}"
        )
        return nodes

    async def find_shortest_path(
        self,
        start_node_id: UUID,
        end_node_id: UUID,
        max_depth: int = 10,
        edge_types: Optional[List[str]] = None,
    ) -> Optional[GraphPath]:
        """Find shortest path using recursive CTE with BFS."""
        self._ensure_connected()

        type_filter = ""
        query_params: List[Any] = [start_node_id, end_node_id, max_depth]

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
            logger.debug(f"No path found from {start_node_id} to {end_node_id}")
            return None

        # Fetch actual nodes and edges for the path
        nodes = await self._fetch_nodes_by_ids(record["node_path"])
        edges = await self._fetch_edges_by_ids(record["edge_path"])

        logger.debug(
            f"Found path from {start_node_id} to {end_node_id} with length {record['length']}"
        )

        return GraphPath(
            nodes=nodes,
            edges=edges,
            total_weight=float(record["total_weight"]),
            length=record["length"],
        )

    async def find_all_paths(
        self,
        start_node_id: UUID,
        end_node_id: UUID,
        max_depth: int = 5,
        limit: int = 10,
    ) -> List[GraphPath]:
        """Find all paths between two nodes."""
        self._ensure_connected()

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
                WHERE ps.length < $3
                  AND NOT (r.to_entity_id = ANY(ps.node_path))
            )
            SELECT node_path, edge_path, total_weight, length
            FROM path_search
            WHERE current_node = $2
            ORDER BY total_weight, length
            LIMIT $4
        """

        async with self._pool.acquire() as conn:
            records = await conn.fetch(
                query, start_node_id, end_node_id, max_depth, limit
            )

        paths = []
        for record in records:
            nodes = await self._fetch_nodes_by_ids(record["node_path"])
            edges = await self._fetch_edges_by_ids(record["edge_path"])

            paths.append(
                GraphPath(
                    nodes=nodes,
                    edges=edges,
                    total_weight=float(record["total_weight"]),
                    length=record["length"],
                )
            )

        logger.debug(f"Found {len(paths)} paths from {start_node_id} to {end_node_id}")
        return paths

    async def get_neighbors(
        self,
        node_id: UUID,
        direction: TraversalDirection = TraversalDirection.BOTH,
        edge_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[GraphNode]:
        """Get immediate neighbors of a node."""
        self._ensure_connected()

        # Build direction filter
        if direction == TraversalDirection.OUTGOING:
            dir_filter = "r.from_entity_id = $1"
            neighbor_col = "r.to_entity_id"
        elif direction == TraversalDirection.INCOMING:
            dir_filter = "r.to_entity_id = $1"
            neighbor_col = "r.from_entity_id"
        else:  # BOTH
            dir_filter = "(r.from_entity_id = $1 OR r.to_entity_id = $1)"
            neighbor_col = """
                CASE
                    WHEN r.from_entity_id = $1 THEN r.to_entity_id
                    ELSE r.from_entity_id
                END
            """

        # Build type filter
        type_filter = ""
        query_params: List[Any] = [node_id]

        if edge_types:
            placeholders = ", ".join([f"${i}" for i in range(2, 2 + len(edge_types))])
            type_filter = f"AND r.relationship_type IN ({placeholders})"
            query_params.extend(edge_types)

        query = f"""
            SELECT DISTINCT e.entity_id, e.name, e.entity_type, e.metadata, e.tags
            FROM {self._relationships_table} r
            JOIN {self._entities_table} e ON e.entity_id = {neighbor_col}
            WHERE {dir_filter}
              AND r.deleted_at IS NULL
              AND e.deleted_at IS NULL
              {type_filter}
            ORDER BY e.name
        """

        if limit:
            query += f" LIMIT {limit}"

        async with self._pool.acquire() as conn:
            records = await conn.fetch(query, *query_params)

        neighbors = [
            GraphNode(
                id=r["entity_id"],
                labels=r["tags"] or [r["entity_type"]],
                properties={"name": r["name"], **_parse_json_field(r["metadata"])},
            )
            for r in records
        ]

        logger.debug(f"Found {len(neighbors)} neighbors for node {node_id}")
        return neighbors

    async def get_subgraph(
        self,
        node_ids: List[UUID],
        include_edges: bool = True,
    ) -> Dict[str, Any]:
        """Extract a subgraph containing specified nodes."""
        self._ensure_connected()

        if not node_ids:
            return {"nodes": [], "edges": []}

        # Fetch nodes
        nodes = await self._fetch_nodes_by_ids(node_ids)

        result: Dict[str, Any] = {"nodes": nodes}

        if include_edges:
            # Fetch edges between these nodes
            query = f"""
                SELECT relationship_id, from_entity_id, to_entity_id,
                       relationship_type, weight, confidence, properties
                FROM {self._relationships_table}
                WHERE from_entity_id = ANY($1)
                  AND to_entity_id = ANY($1)
                  AND deleted_at IS NULL
            """

            async with self._pool.acquire() as conn:
                records = await conn.fetch(query, node_ids)

            edges = [
                GraphEdge(
                    id=r["relationship_id"],
                    source_id=r["from_entity_id"],
                    target_id=r["to_entity_id"],
                    edge_type=r["relationship_type"],
                    properties=_parse_json_field(r["properties"]),
                    weight=float(r["weight"] or 1.0),
                    confidence=float(r["confidence"] or 1.0),
                )
                for r in records
            ]

            result["edges"] = edges

        logger.debug(
            f"Extracted subgraph with {len(nodes)} nodes"
            + (f" and {len(result.get('edges', []))} edges" if include_edges else "")
        )
        return result

    # --- Query Operations ---

    async def find_nodes(
        self,
        labels: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[GraphNode]:
        """Find nodes matching criteria."""
        self._ensure_connected()

        conditions = ["deleted_at IS NULL"]
        query_params: List[Any] = []
        param_idx = 1

        if labels:
            # Check if tags array contains any of the labels
            placeholders = ", ".join(
                [f"${i}" for i in range(param_idx, param_idx + len(labels))]
            )
            conditions.append(f"tags && ARRAY[{placeholders}]")
            query_params.extend(labels)
            param_idx += len(labels)

        if properties:
            # Match properties in metadata JSONB
            for key, value in properties.items():
                conditions.append(f"metadata ->> ${param_idx} = ${param_idx + 1}")
                query_params.extend([key, str(value)])
                param_idx += 2

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT entity_id, entity_type, name, description, metadata, tags
            FROM {self._entities_table}
            WHERE {where_clause}
            ORDER BY name
        """

        if limit:
            query += f" LIMIT {limit}"

        async with self._pool.acquire() as conn:
            records = await conn.fetch(query, *query_params)

        nodes = [
            GraphNode(
                id=r["entity_id"],
                labels=r["tags"] or [r["entity_type"]],
                properties={
                    "name": r["name"],
                    "description": r["description"],
                    **_parse_json_field(r["metadata"]),
                },
            )
            for r in records
        ]

        logger.debug(f"Found {len(nodes)} nodes matching criteria")
        return nodes

    async def find_edges(
        self,
        edge_types: Optional[List[str]] = None,
        source_id: Optional[UUID] = None,
        target_id: Optional[UUID] = None,
        limit: Optional[int] = None,
    ) -> List[GraphEdge]:
        """Find edges matching criteria."""
        self._ensure_connected()

        conditions = ["deleted_at IS NULL"]
        query_params: List[Any] = []
        param_idx = 1

        if edge_types:
            placeholders = ", ".join(
                [f"${i}" for i in range(param_idx, param_idx + len(edge_types))]
            )
            conditions.append(f"relationship_type IN ({placeholders})")
            query_params.extend(edge_types)
            param_idx += len(edge_types)

        if source_id:
            conditions.append(f"from_entity_id = ${param_idx}")
            query_params.append(source_id)
            param_idx += 1

        if target_id:
            conditions.append(f"to_entity_id = ${param_idx}")
            query_params.append(target_id)
            param_idx += 1

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT relationship_id, from_entity_id, to_entity_id,
                   relationship_type, weight, confidence, properties
            FROM {self._relationships_table}
            WHERE {where_clause}
            ORDER BY created_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        async with self._pool.acquire() as conn:
            records = await conn.fetch(query, *query_params)

        edges = [
            GraphEdge(
                id=r["relationship_id"],
                source_id=r["from_entity_id"],
                target_id=r["to_entity_id"],
                edge_type=r["relationship_type"],
                properties=_parse_json_field(r["properties"]),
                weight=float(r["weight"] or 1.0),
                confidence=float(r["confidence"] or 1.0),
            )
            for r in records
        ]

        logger.debug(f"Found {len(edges)} edges matching criteria")
        return edges

    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a native SQL query."""
        self._ensure_connected()

        if not query.strip():
            raise ValueError("Query cannot be empty")

        # Convert named parameters to positional if needed
        params = list(parameters.values()) if parameters else []

        async with self._pool.acquire() as conn:
            records = await conn.fetch(query, *params)

        results = [dict(record) for record in records]
        logger.debug(f"Executed query, got {len(results)} results")
        return results

    # --- Statistics ---

    async def count_nodes(
        self,
        labels: Optional[List[str]] = None,
    ) -> int:
        """Count nodes, optionally filtered by labels."""
        self._ensure_connected()

        if labels:
            placeholders = ", ".join([f"${i+1}" for i in range(len(labels))])
            query = f"""
                SELECT COUNT(*)
                FROM {self._entities_table}
                WHERE tags && ARRAY[{placeholders}]
                  AND deleted_at IS NULL
            """
            async with self._pool.acquire() as conn:
                count = await conn.fetchval(query, *labels)
        else:
            query = f"""
                SELECT COUNT(*)
                FROM {self._entities_table}
                WHERE deleted_at IS NULL
            """
            async with self._pool.acquire() as conn:
                count = await conn.fetchval(query)

        logger.debug(
            f"Counted {count} nodes" + (f" with labels {labels}" if labels else "")
        )
        return count

    async def count_edges(
        self,
        edge_types: Optional[List[str]] = None,
    ) -> int:
        """Count edges, optionally filtered by type."""
        self._ensure_connected()

        if edge_types:
            placeholders = ", ".join([f"${i+1}" for i in range(len(edge_types))])
            query = f"""
                SELECT COUNT(*)
                FROM {self._relationships_table}
                WHERE relationship_type IN ({placeholders})
                  AND deleted_at IS NULL
            """
            async with self._pool.acquire() as conn:
                count = await conn.fetchval(query, *edge_types)
        else:
            query = f"""
                SELECT COUNT(*)
                FROM {self._relationships_table}
                WHERE deleted_at IS NULL
            """
            async with self._pool.acquire() as conn:
                count = await conn.fetchval(query)

        logger.debug(
            f"Counted {count} edges"
            + (f" with types {edge_types}" if edge_types else "")
        )
        return count

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
                    **_parse_json_field(node_map[nid]["metadata"]),
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
                properties=_parse_json_field(edge_map[eid]["properties"]),
                weight=float(edge_map[eid]["weight"] or 1.0),
                confidence=float(edge_map[eid]["confidence"] or 1.0),
            )
            for eid in edge_ids
            if eid in edge_map
        ]
