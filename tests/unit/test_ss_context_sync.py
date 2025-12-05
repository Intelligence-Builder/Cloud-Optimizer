"""
Unit tests for Smart-Scaffold Context Sync and Workflow Coordinator.

Tests context-to-entity synchronization and workflow operations.
"""

from typing import List, Optional

import pytest

from cloud_optimizer.integrations.smart_scaffold.context_sync import (
    ContextIBSync,
    SyncResult,
    WorkflowCoordinator,
)
from cloud_optimizer.integrations.smart_scaffold.runtime import LocalIBService


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_initial_state(self):
        """Result starts with zero counts."""
        result = SyncResult()
        assert result.synced == 0
        assert result.failed == 0
        assert result.entity_ids == {}
        assert result.errors == []

    def test_add_success(self):
        """add_success increments synced and stores entity ID."""
        result = SyncResult()
        result.add_success("ctx-001", "ib-entity-001")

        assert result.synced == 1
        assert result.entity_ids["ctx-001"] == "ib-entity-001"

    def test_add_failure(self):
        """add_failure increments failed and adds error."""
        result = SyncResult()
        result.add_failure("ctx-001", "Sync error")

        assert result.failed == 1
        assert "ctx-001" in result.errors[0]
        assert "Sync error" in result.errors[0]


class TestContextIBSync:
    """Tests for ContextIBSync class."""

    @pytest.fixture
    def mock_service(self):
        """Create LocalIBService-based context service."""
        return ContextIBTestService()

    @pytest.fixture
    def sync(self, mock_service):
        """Create context sync instance."""
        return ContextIBSync(mock_service)

    def test_build_entity_data(self, sync):
        """Build entity data from context record."""
        context = {
            "id": "ctx-001",
            "name": "Issue 42 Context",
            "type": "issue_context",
            "revision": 5,
            "content": {"key": "value"},
            "session_id": "sess-123",
            "task_id": "task-456",
            "issue_number": 42,
            "created_at": "2024-01-15T10:00:00Z",
        }

        entity_data = sync._build_entity_data(context)

        assert entity_data["entity_type"] == "context_record"
        assert entity_data["domain"] == "workflow"
        assert entity_data["name"] == "Issue 42 Context"
        assert entity_data["properties"]["context_id"] == "ctx-001"
        assert entity_data["properties"]["revision"] == 5
        assert entity_data["properties"]["context_type"] == "issue_context"
        assert entity_data["properties"]["issue_number"] == 42
        assert entity_data["metadata"]["source"] == "smart-scaffold"

    def test_build_entity_data_with_defaults(self, sync):
        """Build entity data uses defaults for missing fields."""
        context = {
            "id": "ctx-002",
        }

        entity_data = sync._build_entity_data(context)

        assert entity_data["name"] == "context-ctx-002"
        assert entity_data["properties"]["revision"] == 1
        assert entity_data["properties"]["context_type"] == "general"
        assert "synced_at" in entity_data["metadata"]

    @pytest.mark.asyncio
    async def test_sync_context(self, sync, mock_service):
        """Sync single context to IB."""
        context = {
            "id": "ctx-001",
            "name": "Test Context",
            "revision": 1,
            "content": {"test": "data"},
        }

        result = await sync.sync_context(context)

        assert result.synced == 1
        assert result.failed == 0
        assert "ctx-001" in result.entity_ids
        assert len(mock_service.created_entities) == 1

    @pytest.mark.asyncio
    async def test_sync_context_with_failure(self, mock_service):
        """Sync handles service failure gracefully."""
        mock_service.fail_next = True
        sync = ContextIBSync(mock_service)

        context = {"id": "ctx-fail", "name": "Failing Context"}

        result = await sync.sync_context(context)

        assert result.synced == 0
        assert result.failed == 1
        assert "ctx-fail" in result.errors[0]

    @pytest.mark.asyncio
    async def test_sync_session_end(self, sync, mock_service):
        """Sync context at session end."""
        context = {
            "id": "ctx-session",
            "name": "Session End Context",
            "content": {"final": "state"},
        }

        result = await sync.sync_session_end("sess-123", context)

        assert result.synced == 1
        created = mock_service.created_entities[0]
        assert created["properties"]["session_id"] == "sess-123"
        assert created["properties"]["finalized"] is True

    @pytest.mark.asyncio
    async def test_sync_batch(self, sync):
        """Sync multiple contexts in batch."""
        contexts = [
            {"id": "ctx-001", "name": "Context 1"},
            {"id": "ctx-002", "name": "Context 2"},
            {"id": "ctx-003", "name": "Context 3"},
        ]

        result = await sync.sync_batch(contexts)

        assert result.synced == 3
        assert result.failed == 0
        assert len(result.entity_ids) == 3

    @pytest.mark.asyncio
    async def test_sync_context_with_references(self, sync, mock_service):
        """Sync context creates reference relationships."""
        await mock_service.create_entity(
            {
                "entity_type": "github_issue",
                "name": "Issue 42",
                "metadata": {"original_id": "issue-42"},
            }
        )

        context = {
            "id": "ctx-refs",
            "name": "Context with Refs",
            "references": [
                {"type": "issue", "id": "issue-42"},
            ],
        }

        result = await sync.sync_context(context)

        assert result.synced == 1
        assert len(mock_service.created_relationships) == 1


class TestWorkflowCoordinator:
    """Tests for WorkflowCoordinator class."""

    @pytest.fixture
    def mock_service(self):
        """Create LocalIBService-based workflow service."""
        return WorkflowIBTestService()

    @pytest.fixture
    def coordinator(self, mock_service):
        """Create workflow coordinator."""
        return WorkflowCoordinator(mock_service)

    @pytest.mark.asyncio
    async def test_find_implementation_path(self, coordinator, mock_service):
        """Find implementation path from issue to code."""
        issue = await mock_service.create_entity(
            {
                "entity_type": "github_issue",
                "name": "Test Issue",
                "metadata": {"original_id": "issue-001"},
            }
        )
        pr = await mock_service.create_entity(
            {"entity_type": "pull_request", "name": "PR 1"}
        )
        code_file = await mock_service.create_entity(
            {"entity_type": "code_file", "name": "main.py"}
        )
        await mock_service.create_relationship(
            {
                "source_id": issue["entity_id"],
                "target_id": pr["entity_id"],
                "relationship_type": "implements",
            }
        )
        await mock_service.create_relationship(
            {
                "source_id": pr["entity_id"],
                "target_id": code_file["entity_id"],
                "relationship_type": "modifies",
            }
        )

        path = await coordinator.find_implementation_path("issue-001")

        assert len(path) == 2
        assert path[0]["type"] == "pull_request"
        assert path[1]["type"] == "code_file"

    @pytest.mark.asyncio
    async def test_find_implementation_path_not_found(self, coordinator, mock_service):
        """Find implementation path returns empty for unknown issue."""
        mock_service.query_result = {"entities": []}

        path = await coordinator.find_implementation_path("unknown-issue")

        assert path == []

    @pytest.mark.asyncio
    async def test_find_similar_issues(self, coordinator, mock_service):
        """Find similar issues via vector search."""
        await mock_service.create_entity(
            {
                "entity_type": "github_issue",
                "name": "authentication problem - Auth bug",
            }
        )
        await mock_service.create_entity(
            {
                "entity_type": "github_issue",
                "name": "authentication problem - Login issue",
            }
        )

        similar = await coordinator.find_similar_issues("authentication problem")

        assert len(similar) == 2
        assert "Auth bug" in similar[0]["name"]
        assert "Login issue" in similar[1]["name"]

    @pytest.mark.asyncio
    async def test_find_similar_issues_error(self, coordinator, mock_service):
        """Find similar issues handles errors gracefully."""
        mock_service.fail_search = True

        similar = await coordinator.find_similar_issues("test query")

        assert similar == []

    @pytest.mark.asyncio
    async def test_find_related_patterns(self, coordinator, mock_service):
        """Find patterns related to an issue."""
        issue = await mock_service.create_entity(
            {"entity_type": "github_issue", "name": "Issue Node"}
        )
        pattern = await mock_service.create_entity(
            {
                "entity_type": "pattern",
                "name": "Auth Pattern",
                "properties": {"confidence": 0.9, "occurrences": 5},
            }
        )
        await mock_service.create_relationship(
            {
                "source_id": issue["entity_id"],
                "target_id": pattern["entity_id"],
                "relationship_type": "has_pattern",
            }
        )

        patterns = await coordinator.find_related_patterns(issue["entity_id"])

        assert len(patterns) == 1
        assert patterns[0]["name"] == "Auth Pattern"
        assert patterns[0]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_get_context_for_issue(self, coordinator, mock_service):
        """Get context record for an issue."""
        await mock_service.create_entity(
            {
                "entity_type": "context_record",
                "name": "Issue 42 Context",
                "properties": {"issue_number": 42},
            }
        )

        context = await coordinator.get_context_for_issue(42)

        assert context is not None
        assert context["name"] == "Issue 42 Context"

    @pytest.mark.asyncio
    async def test_get_context_for_issue_not_found(self, coordinator, mock_service):
        """Get context returns None for unknown issue."""
        mock_service.query_result = {"entities": []}

        context = await coordinator.get_context_for_issue(999)

        assert context is None


# ============================================================================
# LocalIBService-based helpers for testing
# ============================================================================


class ContextIBTestService(LocalIBService):
    """LocalIBService extension for context sync tests."""

    def __init__(self):
        super().__init__()
        self.fail_next = False

    @property
    def created_entities(self):
        """Expose created entities for assertions."""
        return list(self._entities.values())

    @property
    def created_relationships(self):
        """Expose created relationships for assertions."""
        return list(self._relationships)

    async def create_entity(self, entity_data: dict) -> dict:
        if self.fail_next:
            self.fail_next = False
            raise Exception("Simulated failure")
        return await super().create_entity(entity_data)

    async def query_entities(self, entity_type=None, limit: int = 100, **filters):
        """Support both IB-style filters dict and LocalIBService kwargs."""
        filter_kwargs = filters.pop("filters", {})
        combined = {**filters, **filter_kwargs}
        return await super().query_entities(
            entity_type=entity_type,
            limit=limit,
            **combined,
        )


class WorkflowIBTestService(ContextIBTestService):
    """Workflow-specific test service with traversal/search helpers."""

    def __init__(self):
        super().__init__()
        self.fail_search = False

    async def traverse_graph(
        self,
        entity_id: str,
        depth: int = 1,
        relationship_types: Optional[List[str]] = None,
    ) -> dict:
        """Traverse stored relationships up to depth."""
        nodes: list[dict] = []
        visited = set()
        frontier: list[tuple[str, int]] = [(entity_id, 0)]

        while frontier:
            current_id, current_depth = frontier.pop(0)
            for rel in self._relationships:
                if rel.get("source_id") != current_id:
                    continue
                rel_type = rel.get("relationship_type")
                if relationship_types and rel_type not in relationship_types:
                    continue
                target_id = rel.get("target_id")
                if not target_id or target_id in visited:
                    continue
                visited.add(target_id)
                entity = await self.get_entity_by_id(target_id)
                if entity:
                    nodes.append(entity)
                if current_depth + 1 < depth:
                    frontier.append((target_id, current_depth + 1))

        return {"nodes": nodes}

    async def search_entities(self, **kwargs):
        if self.fail_search:
            raise Exception("Search failed")
        return await super().search_entities(**kwargs)
