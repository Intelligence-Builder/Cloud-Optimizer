## Parent Epic
Part of #5 (Epic 5: Smart-Scaffold Integration & Cutover)

## Reference Documentation
- **See `docs/smart-scaffold/SMART_SCAFFOLD_INTEGRATION.md`**
- **See `docs/platform/TECHNICAL_DESIGN.md` for IB entity types**

## Objective
Migrate Smart-Scaffold knowledge graph to Intelligence-Builder platform.

## Current SS KG Schema Analysis

### Entities in Smart-Scaffold
| SS Entity | Maps to IB Domain | IB Entity Type |
|-----------|-------------------|----------------|
| Issue | development | issue |
| PR | development | pull_request |
| Commit | development | commit |
| File | development | code_file |
| Function | development | code_function |
| Context | workflow | context_record |
| Session | workflow | session |

### Relationships in Smart-Scaffold
| SS Relationship | Maps to IB Relationship |
|-----------------|------------------------|
| implements | implements |
| tests | tests |
| modifies | modifies |
| references | references |
| depends_on | depends_on |

## Migration Scripts

### Entity Migration Script
```python
# scripts/migrate_ss_entities.py
"""Migrate Smart-Scaffold entities to Intelligence-Builder."""

import asyncio
from intelligence_builder_sdk import IBPlatformClient
from smart_scaffold.knowledge_graph import SSKnowledgeGraph


async def migrate_entities(
    ss_kg: SSKnowledgeGraph,
    ib_client: IBPlatformClient,
    batch_size: int = 100,
):
    """Migrate all SS entities to IB."""

    # 1. Export from SS
    ss_entities = await ss_kg.export_all_entities()

    # 2. Transform to IB format
    ib_entities = [transform_entity(e) for e in ss_entities]

    # 3. Batch import to IB
    for i in range(0, len(ib_entities), batch_size):
        batch = ib_entities[i:i + batch_size]
        await ib_client.entities.batch_create(batch)
        print(f"Migrated {i + len(batch)} / {len(ib_entities)} entities")


def transform_entity(ss_entity: dict) -> dict:
    """Transform SS entity to IB format."""
    type_mapping = {
        "Issue": ("development", "issue"),
        "PR": ("development", "pull_request"),
        "Commit": ("development", "commit"),
        "File": ("development", "code_file"),
    }

    domain, entity_type = type_mapping.get(
        ss_entity["type"],
        ("workflow", ss_entity["type"].lower())
    )

    return {
        "entity_type": entity_type,
        "domain": domain,
        "name": ss_entity["name"],
        "properties": ss_entity.get("properties", {}),
        "metadata": {
            "migrated_from": "smart-scaffold",
            "original_id": ss_entity["id"],
        },
    }
```

### Relationship Migration Script
```python
# scripts/migrate_ss_relationships.py
"""Migrate Smart-Scaffold relationships to Intelligence-Builder."""

async def migrate_relationships(
    ss_kg: SSKnowledgeGraph,
    ib_client: IBPlatformClient,
    id_mapping: dict,  # SS ID -> IB ID
):
    """Migrate all SS relationships to IB."""

    ss_rels = await ss_kg.export_all_relationships()

    for rel in ss_rels:
        source_id = id_mapping.get(rel["source_id"])
        target_id = id_mapping.get(rel["target_id"])

        if not source_id or not target_id:
            print(f"Skipping relationship - missing entity: {rel}")
            continue

        await ib_client.relationships.create(
            source_id=source_id,
            target_id=target_id,
            relationship_type=rel["type"],
            domain="development",
        )
```

## Hybrid Operation Plan

### Phase 1: Read from IB, Write to Both
```python
class HybridKnowledgeGraph:
    """Hybrid KG during migration - reads from IB, writes to both."""

    def __init__(self, ss_kg, ib_client):
        self.ss_kg = ss_kg
        self.ib = ib_client

    async def query(self, query: str):
        """Query from IB (source of truth during migration)."""
        return await self.ib.search.hybrid(query)

    async def create_entity(self, entity: dict):
        """Write to both SS and IB."""
        ss_result = await self.ss_kg.create_entity(entity)
        ib_result = await self.ib.entities.create(**entity)
        return ib_result  # Return IB result as primary
```

### Phase 2: IB Only
After validation, switch to IB-only operations.

## Validation Checklist
- [ ] Entity count matches between SS and IB
- [ ] Relationship count matches
- [ ] Random sample of 100 entities verified
- [ ] All relationship types preserved
- [ ] Query results match for test queries
- [ ] Performance benchmarks met (< 200ms)

## Test Scenarios
```python
class TestMigration:
    async def test_entity_transformation()
    async def test_relationship_preservation()
    async def test_batch_migration_performance()
    async def test_hybrid_mode_operations()
```

## Acceptance Criteria
- [ ] Current SS schema fully documented
- [ ] Entity mapping to IB complete
- [ ] Migration scripts tested on sample data
- [ ] Hybrid operation mode working
- [ ] Validation queries passing
- [ ] Rollback plan documented
