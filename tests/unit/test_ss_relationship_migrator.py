"""
Unit tests for Smart-Scaffold Relationship Migrator.

Tests relationship transformation and migration logic.
"""

import pytest

from cloud_optimizer.integrations.smart_scaffold.relationship_migrator import (
    DEFAULT_RELATIONSHIP_MAPPINGS,
    RelationshipMigrationResult,
    RelationshipMigrator,
    RelationshipTypeMapping,
)
from cloud_optimizer.integrations.smart_scaffold.runtime import LocalIBService


class TestRelationshipTypeMapping:
    """Tests for RelationshipTypeMapping dataclass."""

    def test_default_mappings_exist(self):
        """Default mappings cover common relationship types."""
        expected_types = {
            "implements",
            "IMPLEMENTS",
            "tests",
            "TESTS",
            "modifies",
            "MODIFIES",
            "references",
            "REFERENCES",
            "depends_on",
            "DEPENDS_ON",
            "contains",
            "CONTAINS",
            "belongs_to",
            "BELONGS_TO",
        }
        actual_types = {m.ss_type for m in DEFAULT_RELATIONSHIP_MAPPINGS}
        assert expected_types.issubset(actual_types)

    def test_implements_mapping(self):
        """implements relationship maps to development domain."""
        mapping = next(
            m for m in DEFAULT_RELATIONSHIP_MAPPINGS if m.ss_type == "implements"
        )
        assert mapping.ib_type == "implements"
        assert mapping.ib_domain == "development"

    def test_belongs_to_mapping(self):
        """belongs_to relationship maps to workflow domain."""
        mapping = next(
            m for m in DEFAULT_RELATIONSHIP_MAPPINGS if m.ss_type == "belongs_to"
        )
        assert mapping.ib_type == "belongs_to"
        assert mapping.ib_domain == "workflow"


class TestRelationshipMigrationResult:
    """Tests for RelationshipMigrationResult dataclass."""

    def test_initial_state(self):
        """Result starts with zero counts."""
        result = RelationshipMigrationResult()
        assert result.total == 0
        assert result.migrated == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.errors == []

    def test_add_success(self):
        """add_success increments migrated."""
        result = RelationshipMigrationResult(total=1)
        result.add_success()
        assert result.migrated == 1

    def test_add_failure(self):
        """add_failure increments failed and adds error."""
        result = RelationshipMigrationResult(total=1)
        result.add_failure("a->b", "Connection error")
        assert result.failed == 1
        assert "a->b" in result.errors[0]

    def test_add_skipped(self):
        """add_skipped increments skipped."""
        result = RelationshipMigrationResult(total=1)
        result.add_skipped("a->b", "Missing entity")
        assert result.skipped == 1


class TestRelationshipMigratorTransform:
    """Tests for RelationshipMigrator transformation logic."""

    @pytest.fixture
    def entity_mapping(self):
        """Entity ID mapping from entity migration."""
        return {
            "issue-001": "ib-001",
            "issue-002": "ib-002",
            "pr-001": "ib-003",
            "commit-001": "ib-004",
            "file-001": "ib-005",
        }

    @pytest.fixture
    def migrator(self, entity_mapping):
        """Create migrator with mock service and entity mapping."""
        mock_service = RelationshipIBTestService()
        return RelationshipMigrator(mock_service, entity_mapping)

    def test_transform_implements_relationship(self, migrator):
        """Transform implements relationship to IB format."""
        ss_rel = {
            "type": "implements",
            "source_id": "pr-001",
            "target_id": "issue-001",
            "properties": {"status": "complete"},
        }

        ib_rel, error = migrator.transform_relationship(ss_rel)

        assert error is None
        assert ib_rel["source_id"] == "ib-003"
        assert ib_rel["target_id"] == "ib-001"
        assert ib_rel["relationship_type"] == "implements"
        assert ib_rel["domain"] == "development"
        assert ib_rel["metadata"]["migrated_from"] == "smart-scaffold"

    def test_transform_modifies_relationship(self, migrator):
        """Transform modifies relationship to IB format."""
        ss_rel = {
            "type": "modifies",
            "source_id": "commit-001",
            "target_id": "file-001",
        }

        ib_rel, error = migrator.transform_relationship(ss_rel)

        assert error is None
        assert ib_rel["relationship_type"] == "modifies"
        assert ib_rel["source_id"] == "ib-004"
        assert ib_rel["target_id"] == "ib-005"

    def test_transform_uppercase_type(self, migrator):
        """Uppercase relationship types are handled."""
        ss_rel = {
            "type": "IMPLEMENTS",
            "source_id": "pr-001",
            "target_id": "issue-001",
        }

        ib_rel, error = migrator.transform_relationship(ss_rel)

        assert error is None
        assert ib_rel["relationship_type"] == "implements"

    def test_transform_missing_type_returns_error(self, migrator):
        """Relationship without type returns error."""
        ss_rel = {"source_id": "a", "target_id": "b"}

        ib_rel, error = migrator.transform_relationship(ss_rel)

        assert ib_rel is None
        assert "missing 'type'" in error.lower()

    def test_transform_missing_source_returns_error(self, migrator):
        """Relationship without source_id returns error."""
        ss_rel = {"type": "implements", "target_id": "issue-001"}

        ib_rel, error = migrator.transform_relationship(ss_rel)

        assert ib_rel is None
        assert "missing" in error.lower()

    def test_transform_missing_target_returns_error(self, migrator):
        """Relationship without target_id returns error."""
        ss_rel = {"type": "implements", "source_id": "pr-001"}

        ib_rel, error = migrator.transform_relationship(ss_rel)

        assert ib_rel is None
        assert "missing" in error.lower()

    def test_transform_unknown_source_returns_error(self, migrator):
        """Relationship with unmapped source returns error."""
        ss_rel = {
            "type": "implements",
            "source_id": "unknown-001",
            "target_id": "issue-001",
        }

        ib_rel, error = migrator.transform_relationship(ss_rel)

        assert ib_rel is None
        assert "not found in mapping" in error.lower()

    def test_transform_unknown_target_returns_error(self, migrator):
        """Relationship with unmapped target returns error."""
        ss_rel = {
            "type": "implements",
            "source_id": "pr-001",
            "target_id": "unknown-001",
        }

        ib_rel, error = migrator.transform_relationship(ss_rel)

        assert ib_rel is None
        assert "not found in mapping" in error.lower()

    def test_transform_unknown_type_returns_error(self, migrator):
        """Relationship with unknown type returns error."""
        ss_rel = {
            "type": "unknown_relationship",
            "source_id": "pr-001",
            "target_id": "issue-001",
        }

        ib_rel, error = migrator.transform_relationship(ss_rel)

        assert ib_rel is None
        assert "no mapping" in error.lower()


class TestRelationshipMigratorMigration:
    """Tests for RelationshipMigrator migration operations."""

    @pytest.fixture
    def entity_mapping(self):
        """Entity ID mapping."""
        return {
            "issue-001": "ib-001",
            "issue-002": "ib-002",
            "pr-001": "ib-003",
            "pr-002": "ib-004",
            "commit-001": "ib-005",
        }

    @pytest.fixture
    def mock_service(self):
        """Create mock IB service."""
        return RelationshipIBTestService()

    @pytest.fixture
    def migrator(self, mock_service, entity_mapping):
        """Create migrator."""
        return RelationshipMigrator(mock_service, entity_mapping, batch_size=10)

    @pytest.mark.asyncio
    async def test_migrate_single_relationship(self, migrator):
        """Migrate single relationship successfully."""
        ss_rel = {
            "type": "implements",
            "source_id": "pr-001",
            "target_id": "issue-001",
        }

        success, error = await migrator.migrate_relationship(ss_rel)

        assert success is True
        assert error is None

    @pytest.mark.asyncio
    async def test_migrate_all_relationships(self, migrator):
        """Migrate multiple relationships."""
        ss_rels = [
            {"type": "implements", "source_id": "pr-001", "target_id": "issue-001"},
            {"type": "implements", "source_id": "pr-002", "target_id": "issue-002"},
            {"type": "modifies", "source_id": "commit-001", "target_id": "issue-001"},
        ]

        result = await migrator.migrate_all(ss_rels)

        assert result.total == 3
        assert result.migrated == 3
        assert result.failed == 0
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_migrate_with_missing_entities(self, migrator):
        """Migration skips relationships with missing entities."""
        ss_rels = [
            {"type": "implements", "source_id": "pr-001", "target_id": "issue-001"},
            {"type": "implements", "source_id": "missing", "target_id": "issue-001"},
            {"type": "implements", "source_id": "pr-002", "target_id": "issue-002"},
        ]

        result = await migrator.migrate_all(ss_rels)

        assert result.total == 3
        assert result.migrated == 2
        assert result.skipped == 1
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_migrate_with_service_failure(self, mock_service, entity_mapping):
        """Migration handles service failures."""
        mock_service.fail_count = 1  # Fail first creation

        migrator = RelationshipMigrator(mock_service, entity_mapping)
        ss_rels = [
            {"type": "implements", "source_id": "pr-001", "target_id": "issue-001"},
            {"type": "implements", "source_id": "pr-002", "target_id": "issue-002"},
        ]

        result = await migrator.migrate_all(ss_rels)

        assert result.total == 2
        assert result.migrated == 1
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_migrate_by_type(self, migrator):
        """Migrate relationships filtered by type."""
        ss_rels = [
            {"type": "implements", "source_id": "pr-001", "target_id": "issue-001"},
            {"type": "tests", "source_id": "commit-001", "target_id": "issue-001"},
            {"type": "implements", "source_id": "pr-002", "target_id": "issue-002"},
        ]

        result = await migrator.migrate_by_type(
            ss_rels, relationship_types=["implements"]
        )

        assert result.total == 2
        assert result.migrated == 2

    @pytest.mark.asyncio
    async def test_migrate_records_duration(self, migrator):
        """Migration records duration."""
        ss_rels = [
            {"type": "implements", "source_id": "pr-001", "target_id": "issue-001"}
        ]

        result = await migrator.migrate_all(ss_rels)

        assert result.duration_seconds >= 0


class TestCustomRelationshipMappings:
    """Tests for custom relationship type mappings."""

    def test_custom_mapping_overrides_default(self):
        """Custom mappings can override defaults."""
        custom_mappings = [
            RelationshipTypeMapping(
                ss_type="implements",
                ib_type="custom_implements",
                ib_domain="custom",
            )
        ]

        migrator = RelationshipMigrator(
            RelationshipIBTestService(),
            {"a": "b"},
            type_mappings=custom_mappings,
        )
        mapping = migrator.get_type_mapping("implements")

        assert mapping.ib_type == "custom_implements"
        assert mapping.ib_domain == "custom"


# ============================================================================
# Mock Service for Testing
# ============================================================================


class RelationshipIBTestService(LocalIBService):
    """LocalIBService specialized for relationship migration tests."""

    def __init__(self):
        super().__init__()
        self.fail_count = 0

    async def create_relationship(self, rel_data: dict) -> dict:
        if self.fail_count > 0:
            self.fail_count -= 1
            raise Exception("Simulated failure")
        return await super().create_relationship(rel_data)
