"""
Unit tests for Smart-Scaffold Entity Migrator.

Tests entity transformation and migration logic without AWS dependencies.
"""

import pytest

from cloud_optimizer.integrations.smart_scaffold.entity_migrator import (
    DEFAULT_ENTITY_MAPPINGS,
    EntityMigrator,
    EntityTypeMapping,
    MigrationResult,
)


class TestEntityTypeMapping:
    """Tests for EntityTypeMapping dataclass."""

    def test_default_mappings_exist(self):
        """Default mappings cover all SS entity types."""
        expected_types = {
            "Issue",
            "PR",
            "Commit",
            "File",
            "Function",
            "Context",
            "Session",
        }
        actual_types = {m.ss_type for m in DEFAULT_ENTITY_MAPPINGS}
        assert expected_types == actual_types

    def test_issue_mapping(self):
        """Issue type maps to github_issue in development domain."""
        mapping = next(m for m in DEFAULT_ENTITY_MAPPINGS if m.ss_type == "Issue")
        assert mapping.ib_domain == "development"
        assert mapping.ib_type == "github_issue"
        assert "number" in mapping.property_mapping

    def test_pr_mapping(self):
        """PR type maps to pull_request in development domain."""
        mapping = next(m for m in DEFAULT_ENTITY_MAPPINGS if m.ss_type == "PR")
        assert mapping.ib_domain == "development"
        assert mapping.ib_type == "pull_request"

    def test_context_mapping(self):
        """Context type maps to context_record in workflow domain."""
        mapping = next(m for m in DEFAULT_ENTITY_MAPPINGS if m.ss_type == "Context")
        assert mapping.ib_domain == "workflow"
        assert mapping.ib_type == "context_record"

    def test_transform_properties(self):
        """Property transformation uses mapping."""
        mapping = EntityTypeMapping(
            ss_type="Test",
            ib_domain="test",
            ib_type="test_entity",
            property_mapping={"old_key": "new_key", "keep_key": "keep_key"},
        )

        ss_props = {"old_key": "value1", "keep_key": "value2", "unmapped": "value3"}
        ib_props = mapping.transform_properties(ss_props)

        assert ib_props["new_key"] == "value1"
        assert ib_props["keep_key"] == "value2"
        assert ib_props["unmapped"] == "value3"


class TestMigrationResult:
    """Tests for MigrationResult dataclass."""

    def test_initial_state(self):
        """Result starts with zero counts."""
        result = MigrationResult()
        assert result.total == 0
        assert result.migrated == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.id_mapping == {}
        assert result.errors == []

    def test_add_success(self):
        """add_success increments migrated and updates mapping."""
        result = MigrationResult(total=1)
        result.add_success("ss-123", "ib-456")

        assert result.migrated == 1
        assert result.id_mapping["ss-123"] == "ib-456"

    def test_add_failure(self):
        """add_failure increments failed and adds error."""
        result = MigrationResult(total=1)
        result.add_failure("ss-123", "Connection error")

        assert result.failed == 1
        assert "ss-123" in result.errors[0]
        assert "Connection error" in result.errors[0]

    def test_add_skipped(self):
        """add_skipped increments skipped and adds reason."""
        result = MigrationResult(total=1)
        result.add_skipped("ss-123", "No mapping")

        assert result.skipped == 1
        assert "Skipped" in result.errors[0]


class TestEntityMigratorTransform:
    """Tests for EntityMigrator transformation logic."""

    @pytest.fixture
    def migrator(self):
        """Create migrator with mock IB service."""
        mock_service = MockIBService()
        return EntityMigrator(mock_service)

    def test_transform_issue_entity(self, migrator):
        """Transform Issue entity to IB format."""
        ss_entity = {
            "type": "Issue",
            "id": "issue-123",
            "name": "Fix authentication bug",
            "properties": {
                "number": 42,
                "state": "open",
                "created_at": "2024-01-15T10:00:00Z",
            },
        }

        ib_entity, error = migrator.transform_entity(ss_entity)

        assert error is None
        assert ib_entity["entity_type"] == "github_issue"
        assert ib_entity["domain"] == "development"
        assert ib_entity["name"] == "Fix authentication bug"
        assert ib_entity["properties"]["issue_number"] == 42
        assert ib_entity["properties"]["status"] == "open"
        assert ib_entity["metadata"]["migrated_from"] == "smart-scaffold"
        assert ib_entity["metadata"]["original_id"] == "issue-123"

    def test_transform_pr_entity(self, migrator):
        """Transform PR entity to IB format."""
        ss_entity = {
            "type": "PR",
            "id": "pr-456",
            "name": "Add new feature",
            "properties": {
                "number": 99,
                "state": "merged",
                "merged": True,
            },
        }

        ib_entity, error = migrator.transform_entity(ss_entity)

        assert error is None
        assert ib_entity["entity_type"] == "pull_request"
        assert ib_entity["properties"]["pr_number"] == 99
        assert ib_entity["properties"]["is_merged"] is True

    def test_transform_commit_entity(self, migrator):
        """Transform Commit entity to IB format."""
        ss_entity = {
            "type": "Commit",
            "id": "abc123",
            "name": "Initial commit",
            "properties": {
                "sha": "abc123def456",
                "message": "Initial commit",
                "author": "developer",
            },
        }

        ib_entity, error = migrator.transform_entity(ss_entity)

        assert error is None
        assert ib_entity["entity_type"] == "commit"
        assert ib_entity["properties"]["commit_sha"] == "abc123def456"
        assert ib_entity["properties"]["author_name"] == "developer"

    def test_transform_file_entity(self, migrator):
        """Transform File entity to IB format."""
        ss_entity = {
            "type": "File",
            "id": "file-001",
            "name": "main.py",
            "properties": {
                "path": "src/main.py",
                "language": "python",
                "size": 1024,
            },
        }

        ib_entity, error = migrator.transform_entity(ss_entity)

        assert error is None
        assert ib_entity["entity_type"] == "code_file"
        assert ib_entity["properties"]["file_path"] == "src/main.py"
        assert ib_entity["properties"]["programming_language"] == "python"

    def test_transform_context_entity(self, migrator):
        """Transform Context entity to workflow domain."""
        ss_entity = {
            "type": "Context",
            "id": "ctx-001",
            "name": "Issue 42 Context",
            "properties": {
                "revision": 5,
                "content": {"key": "value"},
                "session_id": "sess-123",
            },
        }

        ib_entity, error = migrator.transform_entity(ss_entity)

        assert error is None
        assert ib_entity["entity_type"] == "context_record"
        assert ib_entity["domain"] == "workflow"
        assert ib_entity["properties"]["revision_number"] == 5

    def test_transform_missing_type_returns_error(self, migrator):
        """Entity without type returns error."""
        ss_entity = {"id": "no-type", "name": "Missing type"}

        ib_entity, error = migrator.transform_entity(ss_entity)

        assert ib_entity is None
        assert "missing 'type'" in error.lower()

    def test_transform_missing_id_returns_error(self, migrator):
        """Entity without ID returns error."""
        ss_entity = {"type": "Issue", "name": "Missing ID"}

        ib_entity, error = migrator.transform_entity(ss_entity)

        assert ib_entity is None
        assert "missing 'id'" in error.lower()

    def test_transform_unknown_type_returns_error(self, migrator):
        """Entity with unknown type returns error."""
        ss_entity = {"type": "UnknownType", "id": "unk-123", "name": "Unknown"}

        ib_entity, error = migrator.transform_entity(ss_entity)

        assert ib_entity is None
        assert "no mapping" in error.lower()


class TestEntityMigratorMigration:
    """Tests for EntityMigrator migration operations."""

    @pytest.fixture
    def mock_service(self):
        """Create mock IB service."""
        return MockIBService()

    @pytest.fixture
    def migrator(self, mock_service):
        """Create migrator with mock service."""
        return EntityMigrator(mock_service, batch_size=10)

    @pytest.mark.asyncio
    async def test_migrate_single_entity(self, migrator):
        """Migrate single entity successfully."""
        ss_entity = {
            "type": "Issue",
            "id": "issue-001",
            "name": "Test Issue",
            "properties": {"number": 1, "state": "open"},
        }

        ib_id, error = await migrator.migrate_entity(ss_entity)

        assert error is None
        assert ib_id is not None
        assert ib_id.startswith("ib-")

    @pytest.mark.asyncio
    async def test_migrate_all_entities(self, migrator):
        """Migrate multiple entities with batch processing."""
        ss_entities = [
            {
                "type": "Issue",
                "id": f"issue-{i}",
                "name": f"Issue {i}",
                "properties": {},
            }
            for i in range(25)
        ]

        result = await migrator.migrate_all(ss_entities)

        assert result.total == 25
        assert result.migrated == 25
        assert result.failed == 0
        assert len(result.id_mapping) == 25

    @pytest.mark.asyncio
    async def test_migrate_with_failures(self, mock_service, migrator):
        """Migration handles individual failures gracefully."""
        # Configure service to fail on specific entity
        mock_service.fail_on_id = "issue-002"

        ss_entities = [
            {"type": "Issue", "id": "issue-001", "name": "Issue 1", "properties": {}},
            {"type": "Issue", "id": "issue-002", "name": "Issue 2", "properties": {}},
            {"type": "Issue", "id": "issue-003", "name": "Issue 3", "properties": {}},
        ]

        result = await migrator.migrate_all(ss_entities)

        assert result.total == 3
        assert result.migrated == 2
        assert result.failed == 1
        assert "issue-001" in result.id_mapping
        assert "issue-002" not in result.id_mapping
        assert "issue-003" in result.id_mapping

    @pytest.mark.asyncio
    async def test_migrate_by_type(self, migrator):
        """Migrate entities filtered by type."""
        ss_entities = [
            {"type": "Issue", "id": "issue-001", "name": "Issue 1", "properties": {}},
            {"type": "PR", "id": "pr-001", "name": "PR 1", "properties": {}},
            {"type": "Issue", "id": "issue-002", "name": "Issue 2", "properties": {}},
        ]

        result = await migrator.migrate_by_type(ss_entities, entity_types=["Issue"])

        assert result.total == 2
        assert result.migrated == 2

    @pytest.mark.asyncio
    async def test_migrate_records_duration(self, migrator):
        """Migration records duration."""
        ss_entities = [
            {"type": "Issue", "id": "issue-001", "name": "Issue 1", "properties": {}}
        ]

        result = await migrator.migrate_all(ss_entities)

        assert result.duration_seconds >= 0


class TestCustomMappings:
    """Tests for custom entity type mappings."""

    def test_custom_mapping_overrides_default(self):
        """Custom mappings can override defaults."""
        custom_mappings = [
            EntityTypeMapping(
                ss_type="Issue",
                ib_domain="custom",
                ib_type="custom_issue",
                property_mapping={"custom_prop": "mapped_prop"},
            )
        ]

        migrator = EntityMigrator(MockIBService(), type_mappings=custom_mappings)
        mapping = migrator.get_type_mapping("Issue")

        assert mapping.ib_domain == "custom"
        assert mapping.ib_type == "custom_issue"

    def test_get_type_mapping_returns_none_for_unknown(self):
        """get_type_mapping returns None for unknown types."""
        migrator = EntityMigrator(MockIBService())
        mapping = migrator.get_type_mapping("NonExistentType")

        assert mapping is None


# ============================================================================
# Mock Service for Testing
# ============================================================================


class MockIBService:
    """Mock IB service for unit testing."""

    def __init__(self):
        self.created_entities = []
        self.fail_on_id = None
        self._counter = 0

    async def create_entity(self, entity_data: dict) -> dict:
        """Mock entity creation."""
        original_id = entity_data.get("metadata", {}).get("original_id", "")

        if self.fail_on_id and original_id == self.fail_on_id:
            raise Exception(f"Simulated failure for {original_id}")

        self._counter += 1
        entity_id = f"ib-{self._counter:06d}"

        result = {
            "entity_id": entity_id,
            "name": entity_data.get("name"),
            "entity_type": entity_data.get("entity_type"),
        }

        self.created_entities.append(result)
        return result
