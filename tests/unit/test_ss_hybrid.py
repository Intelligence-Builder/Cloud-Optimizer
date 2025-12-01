"""
Tests for the HybridKnowledgeGraph dual-write adapter.
"""

from typing import Any, Dict, List

import pytest

from cloud_optimizer.integrations.smart_scaffold.hybrid import HybridKnowledgeGraph


class MockIBService:
    """Minimal IB service mock."""

    def __init__(self) -> None:
        self.created_entities: List[Dict[str, Any]] = []
        self.created_relationships: List[Dict[str, Any]] = []
        self.queries: List[Dict[str, Any]] = []

    async def create_entity(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        self.created_entities.append(entity_data)
        return {"entity_id": f"ib-{len(self.created_entities)}", **entity_data}

    async def create_relationship(self, rel_data: Dict[str, Any]) -> Dict[str, Any]:
        self.created_relationships.append(rel_data)
        return {"relationship_id": f"rel-{len(self.created_relationships)}", **rel_data}

    async def search_entities(
        self, query_text: str, entity_types=None, limit: int = 10
    ) -> Dict[str, Any]:
        self.queries.append(
            {"query_text": query_text, "entity_types": entity_types, "limit": limit}
        )
        return {"total": 0, "entities": []}


class MockSSKG:
    """Simulated Smart-Scaffold client."""

    def __init__(self) -> None:
        self.entities: List[Dict[str, Any]] = []
        self.relationships: List[Dict[str, Any]] = []

    async def create_entity(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        self.entities.append(entity_data)
        return entity_data

    async def create_relationship(self, rel_data: Dict[str, Any]) -> Dict[str, Any]:
        self.relationships.append(rel_data)
        return rel_data


@pytest.mark.asyncio
async def test_query_uses_ib_search():
    ib_service = MockIBService()
    ss_kg = MockSSKG()
    hybrid = HybridKnowledgeGraph(ss_kg, ib_service)

    await hybrid.query("auth bug", ["github_issue"], limit=5)

    assert ib_service.queries[0]["query_text"] == "auth bug"
    assert ib_service.queries[0]["limit"] == 5


@pytest.mark.asyncio
async def test_create_entity_dual_writes():
    ib_service = MockIBService()
    ss_kg = MockSSKG()
    hybrid = HybridKnowledgeGraph(ss_kg, ib_service, dual_write=True)

    result = await hybrid.create_entity({"entity_type": "context_record", "name": "ctx"})

    assert result["entity_id"] == "ib-1"
    assert ss_kg.entities[0]["name"] == "ctx"


@pytest.mark.asyncio
async def test_create_relationship_dual_writes():
    ib_service = MockIBService()
    ss_kg = MockSSKG()
    hybrid = HybridKnowledgeGraph(ss_kg, ib_service, dual_write=True)

    rel = {"relationship_type": "references", "source_id": "ctx-1", "target_id": "issue-1"}
    await hybrid.create_relationship(rel)

    assert ib_service.created_relationships[0] == rel
    assert ss_kg.relationships[0] == rel


@pytest.mark.asyncio
async def test_dual_write_toggle():
    ib_service = MockIBService()
    ss_kg = MockSSKG()
    hybrid = HybridKnowledgeGraph(ss_kg, ib_service, dual_write=False)

    await hybrid.create_entity({"entity_type": "context_record", "name": "ctx"})

    assert ss_kg.entities == []
