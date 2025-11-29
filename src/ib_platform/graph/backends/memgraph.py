"""
Memgraph-based Graph Backend.

Uses native Cypher queries for graph operations.
Optimal for complex traversals and pattern matching.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from neo4j import Driver, GraphDatabase

from ..protocol import (
    GraphBackendProtocol,
    GraphEdge,
    GraphNode,
    GraphPath,
    TraversalDirection,
    TraversalParams,
)

logger = logging.getLogger(__name__)


class MemgraphBackend:
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
    ) -> None:
        """
        Initialize Memgraph backend.

        Args:
            uri: Memgraph connection URI (e.g., "bolt://localhost:7687")
            username: Optional username for authentication
            password: Optional password for authentication
            database: Optional specific database name
        """
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

        try:
            self._driver = GraphDatabase.driver(self._uri, auth=auth)

            # Verify connection
            with self._driver.session(database=self._database) as session:
                session.run("RETURN 1")

            logger.info("MemgraphBackend connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Memgraph: {e}")
            raise ConnectionError(f"Failed to connect to Memgraph: {e}") from e

    async def disconnect(self) -> None:
        """Close connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("MemgraphBackend disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if backend is connected."""
        return self._driver is not None

    def _ensure_connected(self) -> Driver:
        """Ensure backend is connected."""
        if not self._driver:
            raise RuntimeError("Backend not connected. Call connect() first.")
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

        if not labels:
            raise ValueError("labels cannot be empty")

        node_id = node_id or uuid4()
        labels_str = ":".join(labels)

        # Add ID to properties
        props = {**properties, "id": str(node_id)}

        query = f"""
            CREATE (n:{labels_str} $props)
            RETURN n
        """

        try:
            with driver.session(database=self._database) as session:
                result = session.run(query, props=props)
                record = result.single()
                node = record["n"]

            logger.debug(f"Created node {node_id} with labels {labels}")

            return GraphNode(
                id=UUID(node["id"]),
                labels=list(node.labels),
                properties=dict(node),
            )
        except Exception as e:
            logger.error(f"Failed to create node: {e}")
            raise

    async def get_node(self, node_id: UUID) -> Optional[GraphNode]:
        """Get a node by ID."""
        driver = self._ensure_connected()

        query = """
            MATCH (n {id: $node_id})
            RETURN n
        """

        with driver.session(database=self._database) as session:
            result = session.run(query, node_id=str(node_id))
            record = result.single()

            if not record:
                return None

            node = record["n"]
            return GraphNode(
                id=UUID(node["id"]),
                labels=list(node.labels),
                properties=dict(node),
            )

    async def update_node(
        self,
        node_id: UUID,
        properties: Dict[str, Any],
        merge: bool = True,
    ) -> GraphNode:
        """Update node properties."""
        driver = self._ensure_connected()

        if merge:
            # Merge properties with existing
            query = """
                MATCH (n {id: $node_id})
                SET n += $props
                RETURN n
            """
        else:
            # Replace all properties (but keep id)
            query = """
                MATCH (n {id: $node_id})
                SET n = $props
                SET n.id = $node_id
                RETURN n
            """

        with driver.session(database=self._database) as session:
            result = session.run(query, node_id=str(node_id), props=properties)
            record = result.single()

            if not record:
                raise ValueError(f"Node {node_id} not found")

            node = record["n"]
            logger.debug(f"Updated node {node_id}")

            return GraphNode(
                id=UUID(node["id"]),
                labels=list(node.labels),
                properties=dict(node),
            )

    async def delete_node(self, node_id: UUID, soft: bool = True) -> bool:
        """Delete a node."""
        driver = self._ensure_connected()

        if soft:
            # Soft delete by setting deleted_at property
            query = """
                MATCH (n {id: $node_id})
                WHERE n.deleted_at IS NULL
                SET n.deleted_at = timestamp()
                RETURN n
            """
        else:
            # Hard delete
            query = """
                MATCH (n {id: $node_id})
                DETACH DELETE n
                RETURN count(n) as deleted_count
            """

        with driver.session(database=self._database) as session:
            result = session.run(query, node_id=str(node_id))
            record = result.single()

            deleted = record is not None
            if deleted:
                logger.debug(f"{'Soft' if soft else 'Hard'} deleted node {node_id}")
            return deleted

    async def batch_create_nodes(
        self,
        nodes: List[Dict[str, Any]],
    ) -> List[GraphNode]:
        """Batch create nodes using UNWIND."""
        driver = self._ensure_connected()

        if not nodes:
            return []

        created = []

        # Group by label combination for efficient queries
        by_labels: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for node_spec in nodes:
            node_id = str(node_spec.get("id") or uuid4())
            labels = node_spec.get("labels", ["Node"])
            props = {**node_spec.get("properties", {}), "id": node_id}

            if not labels:
                raise ValueError("Each node must have at least one label")

            labels_key = ":".join(sorted(labels))
            by_labels[labels_key].append(
                {"id": node_id, "labels": labels, "props": props}
            )

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
                    created.append(
                        GraphNode(
                            id=UUID(node["id"]),
                            labels=list(node.labels),
                            properties=dict(node),
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
        driver = self._ensure_connected()

        if not edge_type:
            raise ValueError("edge_type cannot be empty")

        edge_id = edge_id or uuid4()
        properties = properties or {}

        # Add edge ID to properties
        props = {**properties, "id": str(edge_id)}

        query = f"""
            MATCH (source {{id: $source_id}})
            MATCH (target {{id: $target_id}})
            CREATE (source)-[r:{edge_type} $props]->(target)
            RETURN r, source, target
        """

        try:
            with driver.session(database=self._database) as session:
                result = session.run(
                    query,
                    source_id=str(source_id),
                    target_id=str(target_id),
                    props=props,
                )
                record = result.single()

                if not record:
                    raise ValueError(f"Source or target node not found")

                rel = record["r"]

                logger.debug(f"Created edge {edge_id}: {source_id} -> {target_id}")

                return GraphEdge(
                    id=UUID(rel.get("id", str(edge_id))),
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=rel.type,
                    properties=dict(rel),
                    weight=float(rel.get("weight", 1.0)),
                    confidence=float(rel.get("confidence", 1.0)),
                )
        except Exception as e:
            logger.error(f"Failed to create edge: {e}")
            raise

    async def get_edge(self, edge_id: UUID) -> Optional[GraphEdge]:
        """Get an edge by ID (excludes soft-deleted edges)."""
        driver = self._ensure_connected()

        query = """
            MATCH (source)-[r {id: $edge_id}]->(target)
            WHERE r.deleted_at IS NULL
            RETURN r, source.id as source_id, target.id as target_id
        """

        with driver.session(database=self._database) as session:
            result = session.run(query, edge_id=str(edge_id))
            record = result.single()

            if not record:
                return None

            rel = record["r"]
            return GraphEdge(
                id=UUID(rel["id"]),
                source_id=UUID(record["source_id"]),
                target_id=UUID(record["target_id"]),
                edge_type=rel.type,
                properties=dict(rel),
                weight=float(rel.get("weight", 1.0)),
                confidence=float(rel.get("confidence", 1.0)),
            )

    async def update_edge(
        self,
        edge_id: UUID,
        properties: Dict[str, Any],
        merge: bool = True,
    ) -> GraphEdge:
        """Update edge properties."""
        driver = self._ensure_connected()

        if merge:
            query = """
                MATCH (source)-[r {id: $edge_id}]->(target)
                SET r += $props
                RETURN r, source.id as source_id, target.id as target_id
            """
        else:
            query = """
                MATCH (source)-[r {id: $edge_id}]->(target)
                SET r = $props
                SET r.id = $edge_id
                RETURN r, source.id as source_id, target.id as target_id
            """

        with driver.session(database=self._database) as session:
            result = session.run(query, edge_id=str(edge_id), props=properties)
            record = result.single()

            if not record:
                raise ValueError(f"Edge {edge_id} not found")

            rel = record["r"]
            logger.debug(f"Updated edge {edge_id}")

            return GraphEdge(
                id=UUID(rel["id"]),
                source_id=UUID(record["source_id"]),
                target_id=UUID(record["target_id"]),
                edge_type=rel.type,
                properties=dict(rel),
                weight=float(rel.get("weight", 1.0)),
                confidence=float(rel.get("confidence", 1.0)),
            )

    async def delete_edge(self, edge_id: UUID, soft: bool = True) -> bool:
        """Delete an edge."""
        driver = self._ensure_connected()

        if soft:
            query = """
                MATCH ()-[r {id: $edge_id}]->()
                WHERE r.deleted_at IS NULL
                SET r.deleted_at = timestamp()
                RETURN r
            """
        else:
            query = """
                MATCH ()-[r {id: $edge_id}]->()
                DELETE r
                RETURN count(r) as deleted_count
            """

        with driver.session(database=self._database) as session:
            result = session.run(query, edge_id=str(edge_id))
            record = result.single()

            deleted = record is not None
            if deleted:
                logger.debug(f"{'Soft' if soft else 'Hard'} deleted edge {edge_id}")
            return deleted

    async def batch_create_edges(
        self,
        edges: List[Dict[str, Any]],
    ) -> List[GraphEdge]:
        """Batch create edges using UNWIND."""
        driver = self._ensure_connected()

        if not edges:
            return []

        # Group by edge type for efficiency
        by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for edge_spec in edges:
            edge_id = str(edge_spec.get("id") or uuid4())
            source_id = edge_spec.get("source_id")
            target_id = edge_spec.get("target_id")
            edge_type = edge_spec.get("edge_type")
            props = {**edge_spec.get("properties", {}), "id": edge_id}

            if not all([source_id, target_id, edge_type]):
                raise ValueError(
                    "Each edge must have source_id, target_id, and edge_type"
                )

            by_type[edge_type].append(
                {
                    "source_id": str(source_id),
                    "target_id": str(target_id),
                    "props": props,
                }
            )

        created = []

        with driver.session(database=self._database) as session:
            for edge_type, group in by_type.items():
                query = f"""
                    UNWIND $edges AS edge
                    MATCH (source {{id: edge.source_id}})
                    MATCH (target {{id: edge.target_id}})
                    CREATE (source)-[r:{edge_type}]->(target)
                    SET r = edge.props
                    RETURN r, source.id as source_id, target.id as target_id
                """

                result = session.run(query, edges=group)
                for record in result:
                    rel = record["r"]
                    created.append(
                        GraphEdge(
                            id=UUID(rel["id"]),
                            source_id=UUID(record["source_id"]),
                            target_id=UUID(record["target_id"]),
                            edge_type=rel.type,
                            properties=dict(rel),
                            weight=float(rel.get("weight", 1.0)),
                            confidence=float(rel.get("confidence", 1.0)),
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
        """Traverse graph using Memgraph-compatible Cypher."""
        driver = self._ensure_connected()

        # Build relationship pattern
        rel_pattern = ""
        if params.edge_types:
            rel_types = "|".join(params.edge_types)
            rel_pattern = f":{rel_types}"

        # Build direction pattern with path variable for depth calculation
        if params.direction == TraversalDirection.OUTGOING:
            pattern = (
                f"path = (start)-[r{rel_pattern}*1..{params.max_depth}]->(connected)"
            )
        elif params.direction == TraversalDirection.INCOMING:
            pattern = (
                f"path = (start)<-[r{rel_pattern}*1..{params.max_depth}]-(connected)"
            )
        else:
            pattern = (
                f"path = (start)-[r{rel_pattern}*1..{params.max_depth}]-(connected)"
            )

        # Memgraph-compatible query using size(relationships(path)) for depth
        query = f"""
            MATCH {pattern}
            WHERE start.id = $start_id
              AND connected.deleted_at IS NULL
            WITH DISTINCT connected, min(size(relationships(path))) as depth
            RETURN connected, depth
            ORDER BY depth
        """

        if params.limit:
            query += f" LIMIT {params.limit}"

        with driver.session(database=self._database) as session:
            result = session.run(query, start_id=str(start_node_id))

            nodes = []
            for record in result:
                node = record["connected"]
                nodes.append(
                    GraphNode(
                        id=UUID(node["id"]),
                        labels=list(node.labels),
                        properties=dict(node),
                        depth=record["depth"],
                    )
                )

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
        """Find shortest path using Memgraph-compatible BFS."""
        driver = self._ensure_connected()

        rel_pattern = ""
        if edge_types:
            rel_types = "|".join(edge_types)
            rel_pattern = f":{rel_types}"

        # Memgraph-compatible: use variable-length path and order by length
        query = f"""
            MATCH (start {{id: $start_id}}), (end {{id: $end_id}})
            MATCH path = (start)-[r{rel_pattern}*1..{max_depth}]-(end)
            RETURN path
            ORDER BY size(relationships(path))
            LIMIT 1
        """

        with driver.session(database=self._database) as session:
            result = session.run(
                query,
                start_id=str(start_node_id),
                end_id=str(end_node_id),
            )
            record = result.single()

            if not record:
                logger.debug(f"No path found from {start_node_id} to {end_node_id}")
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
                    weight=float(rel.get("weight", 1.0)),
                    confidence=float(rel.get("confidence", 1.0)),
                )
                for rel in path.relationships
            ]

            logger.debug(
                f"Found path from {start_node_id} to {end_node_id} with length {len(edges)}"
            )

            return GraphPath(
                nodes=nodes,
                edges=edges,
                total_weight=float(len(edges)),
                length=len(edges),
            )

    async def find_all_paths(
        self,
        start_node_id: UUID,
        end_node_id: UUID,
        max_depth: int = 5,
        limit: int = 10,
    ) -> List[GraphPath]:
        """Find all paths between two nodes."""
        driver = self._ensure_connected()

        query = f"""
            MATCH (start {{id: $start_id}}), (end {{id: $end_id}})
            MATCH path = (start)-[*1..{max_depth}]-(end)
            RETURN path
            ORDER BY length(path)
            LIMIT {limit}
        """

        with driver.session(database=self._database) as session:
            result = session.run(
                query,
                start_id=str(start_node_id),
                end_id=str(end_node_id),
            )

            paths = []
            for record in result:
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
                        weight=float(rel.get("weight", 1.0)),
                        confidence=float(rel.get("confidence", 1.0)),
                    )
                    for rel in path.relationships
                ]

                paths.append(
                    GraphPath(
                        nodes=nodes,
                        edges=edges,
                        total_weight=float(len(edges)),
                        length=len(edges),
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
        driver = self._ensure_connected()

        # Build relationship pattern
        rel_pattern = ""
        if edge_types:
            rel_types = "|".join(edge_types)
            rel_pattern = f":{rel_types}"

        # Build direction pattern
        if direction == TraversalDirection.OUTGOING:
            pattern = f"(n)-[{rel_pattern}]->(neighbor)"
        elif direction == TraversalDirection.INCOMING:
            pattern = f"(n)<-[{rel_pattern}]-(neighbor)"
        else:
            pattern = f"(n)-[{rel_pattern}]-(neighbor)"

        query = f"""
            MATCH {pattern}
            WHERE n.id = $node_id
              AND neighbor.deleted_at IS NULL
            RETURN DISTINCT neighbor
            ORDER BY neighbor.name
        """

        if limit:
            query += f" LIMIT {limit}"

        with driver.session(database=self._database) as session:
            result = session.run(query, node_id=str(node_id))

            neighbors = [
                GraphNode(
                    id=UUID(record["neighbor"]["id"]),
                    labels=list(record["neighbor"].labels),
                    properties=dict(record["neighbor"]),
                )
                for record in result
            ]

        logger.debug(f"Found {len(neighbors)} neighbors for node {node_id}")
        return neighbors

    async def get_subgraph(
        self,
        node_ids: List[UUID],
        include_edges: bool = True,
    ) -> Dict[str, Any]:
        """Extract a subgraph containing specified nodes."""
        driver = self._ensure_connected()

        if not node_ids:
            return {"nodes": [], "edges": []}

        # Fetch nodes
        query_nodes = """
            UNWIND $node_ids AS node_id
            MATCH (n {id: node_id})
            WHERE n.deleted_at IS NULL
            RETURN n
        """

        with driver.session(database=self._database) as session:
            result = session.run(query_nodes, node_ids=[str(nid) for nid in node_ids])

            nodes = [
                GraphNode(
                    id=UUID(record["n"]["id"]),
                    labels=list(record["n"].labels),
                    properties=dict(record["n"]),
                )
                for record in result
            ]

        result_dict: Dict[str, Any] = {"nodes": nodes}

        if include_edges:
            # Fetch edges between these nodes
            query_edges = """
                UNWIND $node_ids AS node_id
                MATCH (source {id: node_id})-[r]->(target)
                WHERE target.id IN $node_ids
                  AND r.deleted_at IS NULL
                RETURN DISTINCT r, source.id as source_id, target.id as target_id
            """

            with driver.session(database=self._database) as session:
                result = session.run(
                    query_edges, node_ids=[str(nid) for nid in node_ids]
                )

                edges = [
                    GraphEdge(
                        id=UUID(record["r"].get("id", str(uuid4()))),
                        source_id=UUID(record["source_id"]),
                        target_id=UUID(record["target_id"]),
                        edge_type=record["r"].type,
                        properties=dict(record["r"]),
                        weight=float(record["r"].get("weight", 1.0)),
                        confidence=float(record["r"].get("confidence", 1.0)),
                    )
                    for record in result
                ]

                result_dict["edges"] = edges

        logger.debug(
            f"Extracted subgraph with {len(nodes)} nodes"
            + (
                f" and {len(result_dict.get('edges', []))} edges"
                if include_edges
                else ""
            )
        )
        return result_dict

    # --- Query Operations ---

    async def find_nodes(
        self,
        labels: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[GraphNode]:
        """Find nodes matching criteria."""
        driver = self._ensure_connected()

        # Build label filter
        label_filter = ""
        if labels:
            label_filter = ":" + ":".join(labels)

        # Build property filter
        where_clauses = ["n.deleted_at IS NULL"]
        params: Dict[str, Any] = {}

        if properties:
            for key, value in properties.items():
                where_clauses.append(f"n.{key} = ${key}")
                params[key] = value

        where_clause = " AND ".join(where_clauses)

        query = f"""
            MATCH (n{label_filter})
            WHERE {where_clause}
            RETURN n
            ORDER BY n.name
        """

        if limit:
            query += f" LIMIT {limit}"

        with driver.session(database=self._database) as session:
            result = session.run(query, **params)

            nodes = [
                GraphNode(
                    id=UUID(record["n"]["id"]),
                    labels=list(record["n"].labels),
                    properties=dict(record["n"]),
                )
                for record in result
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
        driver = self._ensure_connected()

        # Build type filter
        type_filter = ""
        if edge_types:
            type_filter = ":" + "|".join(edge_types)

        # Build pattern
        source_pattern = "{id: $source_id}" if source_id else ""
        target_pattern = "{id: $target_id}" if target_id else ""

        where_clauses = ["r.deleted_at IS NULL"]
        params: Dict[str, Any] = {}

        if source_id:
            params["source_id"] = str(source_id)
        if target_id:
            params["target_id"] = str(target_id)

        where_clause = " AND ".join(where_clauses)

        query = f"""
            MATCH (source{source_pattern})-[r{type_filter}]->(target{target_pattern})
            WHERE {where_clause}
            RETURN r, source.id as source_id, target.id as target_id
            ORDER BY r.created_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        with driver.session(database=self._database) as session:
            result = session.run(query, **params)

            edges = [
                GraphEdge(
                    id=UUID(record["r"].get("id", str(uuid4()))),
                    source_id=UUID(record["source_id"]),
                    target_id=UUID(record["target_id"]),
                    edge_type=record["r"].type,
                    properties=dict(record["r"]),
                    weight=float(record["r"].get("weight", 1.0)),
                    confidence=float(record["r"].get("confidence", 1.0)),
                )
                for record in result
            ]

        logger.debug(f"Found {len(edges)} edges matching criteria")
        return edges

    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a native Cypher query."""
        driver = self._ensure_connected()

        if not query.strip():
            raise ValueError("Query cannot be empty")

        parameters = parameters or {}

        with driver.session(database=self._database) as session:
            result = session.run(query, **parameters)

            results = []
            for record in result:
                # Convert neo4j types to standard Python types
                result_dict = {}
                for key in record.keys():
                    value = record[key]
                    # Handle neo4j node/relationship objects
                    if hasattr(value, "labels"):  # Node
                        result_dict[key] = dict(value)
                    elif hasattr(value, "type"):  # Relationship
                        result_dict[key] = dict(value)
                    else:
                        result_dict[key] = value
                results.append(result_dict)

        logger.debug(f"Executed query, got {len(results)} results")
        return results

    # --- Statistics ---

    async def count_nodes(
        self,
        labels: Optional[List[str]] = None,
    ) -> int:
        """Count nodes, optionally filtered by labels."""
        driver = self._ensure_connected()

        label_filter = ""
        if labels:
            label_filter = ":" + ":".join(labels)

        query = f"""
            MATCH (n{label_filter})
            WHERE n.deleted_at IS NULL
            RETURN count(n) as count
        """

        with driver.session(database=self._database) as session:
            result = session.run(query)
            count = result.single()["count"]

        logger.debug(
            f"Counted {count} nodes" + (f" with labels {labels}" if labels else "")
        )
        return count

    async def count_edges(
        self,
        edge_types: Optional[List[str]] = None,
    ) -> int:
        """Count edges, optionally filtered by type."""
        driver = self._ensure_connected()

        type_filter = ""
        if edge_types:
            type_filter = ":" + "|".join(edge_types)

        query = f"""
            MATCH ()-[r{type_filter}]->()
            WHERE r.deleted_at IS NULL
            RETURN count(r) as count
        """

        with driver.session(database=self._database) as session:
            result = session.run(query)
            count = result.single()["count"]

        logger.debug(
            f"Counted {count} edges"
            + (f" with types {edge_types}" if edge_types else "")
        )
        return count
