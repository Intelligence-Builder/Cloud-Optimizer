## Parent Epic
Part of #5 (Epic 5: Smart-Scaffold Integration & Cutover)

## Reference Documentation
- **See `docs/smart-scaffold/SMART_SCAFFOLD_PROCESS_SUMMARY.md`**
- **See `docs/platform/TECHNICAL_DESIGN.md` for IB SDK**

## Objective
Integrate SS context system with IB entities while preserving local JSON context.

## Architecture After Integration

```
Smart-Scaffold
├── Local Systems (PostgreSQL)
│   ├── Context records (revision-controlled)   <- KEEP LOCAL
│   ├── Workflow events (temporal)              <- KEEP LOCAL
│   └── Session state                           <- KEEP LOCAL
│
└── Intelligence-Builder Platform (via SDK)
    ├── Issues, PRs, commits as entities        <- MOVE TO IB
    ├── Relationships (implements, tests)       <- MOVE TO IB
    ├── Vector search for similar issues        <- USE IB
    └── Graph traversal for implementation      <- USE IB
```

## Context System Integration

### Context-to-Entity Sync
```python
# smart_scaffold/integrations/ib_sync.py
"""Sync context records to IB entities."""

from intelligence_builder_sdk import IBPlatformClient


class ContextIBSync:
    """Synchronizes local context with IB entities."""

    def __init__(self, ib_client: IBPlatformClient):
        self.ib = ib_client

    async def sync_context(self, context: dict):
        """Sync context record to IB as context_record entity."""

        # Create or update entity in IB
        entity = await self.ib.entities.upsert(
            entity_type="context_record",
            domain="workflow",
            name=context["name"],
            properties={
                "revision": context["revision"],
                "content": context["content"],
                "created_at": context["created_at"],
            },
            unique_key=f"context:{context['id']}",
        )

        # Link to related entities (issues, PRs)
        for ref in context.get("references", []):
            await self._link_reference(entity.id, ref)

        return entity

    async def _link_reference(self, context_id: str, ref: dict):
        """Create relationship from context to referenced entity."""
        # Find the referenced entity
        target = await self.ib.entities.search(
            domain="development",
            filters={"github_id": ref["github_id"]},
        )

        if target:
            await self.ib.relationships.create(
                source_id=context_id,
                target_id=target[0].id,
                relationship_type="references",
                domain="workflow",
            )
```

### Preserved Local Context
```python
# smart_scaffold/context/local_store.py
"""Local context store - NOT migrated to IB."""

class LocalContextStore:
    """
    Local context storage for revision-controlled context.

    This stays local because:
    1. High-frequency updates during sessions
    2. Revision history needs local JSONB
    3. Session state is ephemeral
    """

    def __init__(self, db_pool):
        self.pool = db_pool

    async def get_context(self, session_id: str) -> dict:
        """Get current context for session."""
        # Local PostgreSQL query
        pass

    async def update_context(self, session_id: str, context: dict):
        """Update context with revision tracking."""
        # Local PostgreSQL with JSONB revision
        pass

    async def sync_to_ib(self, session_id: str, ib_sync: ContextIBSync):
        """Sync finalized context to IB (on session end)."""
        context = await self.get_context(session_id)
        await ib_sync.sync_context(context)
```

### Workflow Coordination
```python
# smart_scaffold/workflow/coordinator.py
"""Workflow coordinator using IB for graph operations."""

class WorkflowCoordinator:
    """Coordinates workflow using IB for knowledge graph."""

    def __init__(self, ib_client: IBPlatformClient, local_store: LocalContextStore):
        self.ib = ib_client
        self.local = local_store

    async def find_implementation_path(self, issue_id: str) -> List[dict]:
        """Find implementation path using IB graph traversal."""
        # Use IB SDK for graph traversal
        path = await self.ib.graph.find_path(
            start_id=issue_id,
            end_pattern={"entity_type": "code_file"},
            max_depth=5,
        )
        return path

    async def find_similar_issues(self, description: str) -> List[dict]:
        """Find similar issues using IB vector search."""
        return await self.ib.search.vector(
            query=description,
            domain="development",
            entity_types=["issue"],
            limit=10,
        )
```

## Test Scenarios
```python
class TestContextIntegration:
    async def test_context_sync_to_ib()
    async def test_local_context_preserved()
    async def test_reference_linking()

class TestWorkflowCoordinator:
    async def test_implementation_path_via_ib()
    async def test_similar_issues_vector_search()
    async def test_local_session_state()
```

## Acceptance Criteria
- [ ] Context sync to IB working
- [ ] Local context store unchanged
- [ ] Workflow coordination using IB graph
- [ ] Vector search for similar issues
- [ ] Reference linking creates relationships
- [ ] Session state remains local
- [ ] Performance < 200ms for sync operations
