"""
Tests for the HybridKnowledgeGraph dual-write adapter.
"""

from typing import Any, Dict, List

import pytest

from cloud_optimizer.integrations.smart_scaffold.hybrid import HybridKnowledgeGraph
from cloud_optimizer.integrations.smart_scaffold.runtime import LocalIBService


class IBTestService(LocalIBService):
    """LocalIBService wrapper exposing recorded operations."""

    def __init__(self) -> None:
        super().__init__()
        self.queries: List[Dict[str, Any]] = []

    @property
    def created_entities(self) -> List[Dict[str, Any]]:
        return list(self._entities.values())

    @property
    def created_relationships(self) -> List[Dict[str, Any]]:
        return list(self._relationships)

    async def search_entities(
        self, query_text: str, entity_types=None, limit: int = 10
    ) -> Dict[str, Any]:
        self.queries.append(
            {"query_text": query_text, "entity_types": entity_types, "limit": limit}
        )
        return await super().search_entities(
            query_text=query_text, entity_types=entity_types, limit=limit
        )


class SSKnowledgeGraphTestStore(LocalIBService):
    """Local implementation of Smart-Scaffold graph for dual-write checks."""

    @property
    def entities(self) -> List[Dict[str, Any]]:
        return list(self._entities.values())

    @property
    def relationships(self) -> List[Dict[str, Any]]:
        return list(self._relationships)


@pytest.mark.asyncio
async def test_query_uses_ib_search():
    ib_service = IBTestService()
    ss_kg = SSKnowledgeGraphTestStore()
    hybrid = HybridKnowledgeGraph(ss_kg, ib_service)

    await hybrid.query("auth bug", ["github_issue"], limit=5)

    assert ib_service.queries[0]["query_text"] == "auth bug"
    assert ib_service.queries[0]["limit"] == 5


@pytest.mark.asyncio
async def test_create_entity_dual_writes():
    ib_service = IBTestService()
    ss_kg = SSKnowledgeGraphTestStore()
    hybrid = HybridKnowledgeGraph(ss_kg, ib_service, dual_write=True)

    result = await hybrid.create_entity(
        {"entity_type": "context_record", "name": "ctx"}
    )

    assert result["entity_id"].startswith("ib-")
    assert ss_kg.entities[0]["name"] == "ctx"


@pytest.mark.asyncio
async def test_create_relationship_dual_writes():
    ib_service = IBTestService()
    ss_kg = SSKnowledgeGraphTestStore()
    hybrid = HybridKnowledgeGraph(ss_kg, ib_service, dual_write=True)

    rel = {
        "relationship_type": "references",
        "source_id": "ctx-1",
        "target_id": "issue-1",
    }
    await hybrid.create_relationship(rel)

    assert ib_service.created_relationships[0]["source_id"] == rel["source_id"]
    assert ib_service.created_relationships[0]["target_id"] == rel["target_id"]
    assert ss_kg.relationships[0]["relationship_type"] == rel["relationship_type"]


@pytest.mark.asyncio
async def test_dual_write_toggle():
    ib_service = IBTestService()
    ss_kg = SSKnowledgeGraphTestStore()
    hybrid = HybridKnowledgeGraph(ss_kg, ib_service, dual_write=False)

    await hybrid.create_entity({"entity_type": "context_record", "name": "ctx"})

    assert ss_kg.entities == []
