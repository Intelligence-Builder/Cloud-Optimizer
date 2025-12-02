"""Live Smart-Scaffold knowledge graph client backed by Memgraph."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from smart_scaffold.knowledge_graph.memgraph_adapter import MemgraphAdapter

logger = logging.getLogger(__name__)

DEFAULT_MEMGRAPH_URI = os.getenv("MEMGRAPH_BOLT_URL", "bolt://localhost:7687")
DEFAULT_USERNAME = os.getenv("MEMGRAPH_USERNAME", "smart_scaffold_admin")
DEFAULT_PASSWORD = os.getenv("MEMGRAPH_PASSWORD", "supersecurepass123")


class SSKnowledgeGraph:
    """Minimal interface for exporting Smart-Scaffold KG data.

    The class exposes the subset of methods required by the migration CLI:

    - ``export_all_entities``
    - ``export_all_relationships``
    - ``count_by_type``
    - ``count_relationships_by_type``
    - ``get_node``
    - ``query``
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ) -> None:
        self._adapter = MemgraphAdapter(
            uri=uri or DEFAULT_MEMGRAPH_URI,
            username=username or DEFAULT_USERNAME,
            password=password or DEFAULT_PASSWORD,
            database=database,
        )
        self._connected = False

    async def __aenter__(self) -> "SSKnowledgeGraph":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401 ANN001
        await self.close()

    async def connect(self) -> None:
        """Establish a Memgraph connection (idempotent)."""
        if not self._connected:
            await self._adapter.connect()
            self._connected = True

    async def close(self) -> None:
        """Close the Memgraph connection if open."""
        if self._connected:
            await self._adapter.close()
            self._connected = False

    async def export_all_entities(self) -> List[Dict[str, Any]]:
        """Return all entities as dictionaries."""
        await self.connect()
        rows = await self._adapter.execute_cypher(
            "MATCH (n) RETURN id(n) AS mem_id, labels(n) AS labels, properties(n) AS props"
        )
        return [
            self._format_entity(
                props=row.get("props") or {},
                labels=row.get("labels") or [],
                mem_id=row.get("mem_id"),
            )
            for row in rows
        ]

    async def export_all_relationships(self) -> List[Dict[str, Any]]:
        """Return all relationships as dictionaries."""
        await self.connect()
        rows = await self._adapter.execute_cypher(
            """
            MATCH (source)-[r]->(target)
            RETURN
                id(r) AS rel_id,
                type(r) AS rel_type,
                properties(r) AS rel_props,
                id(source) AS source_mem_id,
                properties(source) AS source_props,
                id(target) AS target_mem_id,
                properties(target) AS target_props
            """
        )
        relationships: List[Dict[str, Any]] = []
        for row in rows:
            source_props = row.get("source_props") or {}
            target_props = row.get("target_props") or {}
            relationships.append(
                {
                    "id": str(row.get("rel_id")),
                    "type": row.get("rel_type", "").lower(),
                    "source_id": self._resolve_entity_id(
                        source_props, row.get("source_mem_id")
                    ),
                    "target_id": self._resolve_entity_id(
                        target_props, row.get("target_mem_id")
                    ),
                    "properties": row.get("rel_props") or {},
                }
            )
        return relationships

    async def count_by_type(self) -> Dict[str, int]:
        """Return counts by primary label."""
        await self.connect()
        rows = await self._adapter.execute_cypher(
            """
            MATCH (n)
            WITH CASE
                WHEN size(labels(n)) = 0 THEN 'Unknown'
                ELSE labels(n)[0]
            END AS lbl
            RETURN lbl AS type, count(*) AS total
            """
        )
        return {row["type"]: row["total"] for row in rows}

    async def count_relationships_by_type(self) -> Dict[str, int]:
        """Return relationship counts by type."""
        await self.connect()
        rows = await self._adapter.execute_cypher(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS total"
        )
        return {row["type"]: row["total"] for row in rows}

    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single node by SS identifier."""
        await self.connect()
        rows = await self._adapter.execute_cypher(
            """
            MATCH (n)
            WHERE n.entity_id = $node_id
               OR n.id = $node_id
               OR n.issue_id = $node_id
               OR n.context_id = $node_id
               OR n.session_id = $node_id
               OR toString(id(n)) = $node_id
            RETURN id(n) AS mem_id, labels(n) AS labels, properties(n) AS props
            LIMIT 1
            """,
            {"node_id": node_id},
        )
        if not rows:
            return None
        row = rows[0]
        return self._format_entity(
            row.get("props") or {}, row.get("labels") or [], row.get("mem_id")
        )

    async def query(self, query_text: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Approximate search by matching name/title/description fields."""
        await self.connect()
        rows = await self._adapter.execute_cypher(
            """
            MATCH (n)
            WHERE toLower(coalesce(n.name, n.title, '')) CONTAINS toLower($query)
               OR toLower(coalesce(n.description, '')) CONTAINS toLower($query)
               OR toLower(coalesce(n.issue_id, '')) CONTAINS toLower($query)
            RETURN id(n) AS mem_id, labels(n) AS labels, properties(n) AS props
            LIMIT $limit
            """,
            {"query": query_text, "limit": limit},
        )
        return [
            self._format_entity(
                row.get("props") or {}, row.get("labels") or [], row.get("mem_id")
            )
            for row in rows
        ]

    # ------------------------------------------------------------------ #
    # Helper utilities
    # ------------------------------------------------------------------ #

    def _format_entity(
        self,
        props: Dict[str, Any],
        labels: List[str],
        mem_id: Optional[int],
    ) -> Dict[str, Any]:
        entity_id = self._resolve_entity_id(props, mem_id)
        name = (
            props.get("name")
            or props.get("title")
            or props.get("issue_id")
            or entity_id
        )
        primary_label = labels[0] if labels else "Entity"

        return {
            "id": entity_id,
            "type": primary_label,
            "name": name,
            "properties": props,
        }

    def _resolve_entity_id(self, props: Dict[str, Any], mem_id: Optional[int]) -> str:
        candidates = [
            props.get("entity_id"),
            props.get("id"),
            props.get("issue_id"),
            props.get("context_id"),
            props.get("session_id"),
            props.get("task_id"),
        ]
        for candidate in candidates:
            if candidate:
                return str(candidate)
        return str(mem_id) if mem_id is not None else ""
