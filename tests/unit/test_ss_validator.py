"""
Unit tests for Smart-Scaffold Migration Validator and Cutover Manager.

Tests validation logic and cutover operations.
"""

import pytest

from cloud_optimizer.integrations.smart_scaffold.validator import (
    CutoverManager,
    MigrationValidator,
    ParallelValidator,
    ValidationResult,
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_initial_state(self):
        """Result starts as passed."""
        result = ValidationResult()
        assert result.passed is True
        assert result.entity_count_match is True
        assert result.relationship_count_match is True
        assert result.sample_validation_passed is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error(self):
        """add_error sets passed to False."""
        result = ValidationResult()
        result.add_error("Entity count mismatch")

        assert result.passed is False
        assert "Entity count mismatch" in result.errors

    def test_add_warning(self):
        """add_warning does not affect passed status."""
        result = ValidationResult()
        result.add_warning("Performance may be slow")

        assert result.passed is True
        assert "Performance may be slow" in result.warnings

    def test_to_dict(self):
        """to_dict returns all fields."""
        result = ValidationResult()
        result.add_error("Test error")
        result.add_warning("Test warning")
        result.metrics["test_metric"] = 100

        data = result.to_dict()

        assert data["passed"] is False
        assert "Test error" in data["errors"]
        assert "Test warning" in data["warnings"]
        assert data["metrics"]["test_metric"] == 100


class TestMigrationValidator:
    """Tests for MigrationValidator class."""

    @pytest.fixture
    def mock_ss_kg(self):
        """Create mock SS knowledge graph."""
        return MockSSKnowledgeGraph()

    @pytest.fixture
    def mock_ib_service(self):
        """Create mock IB service."""
        return MockValidatorIBService()

    @pytest.fixture
    def entity_mapping(self):
        """Entity ID mapping."""
        return {
            "issue-001": "ib-001",
            "issue-002": "ib-002",
            "pr-001": "ib-003",
        }

    @pytest.fixture
    def validator(self, mock_ss_kg, mock_ib_service, entity_mapping):
        """Create validator instance."""
        return MigrationValidator(mock_ss_kg, mock_ib_service, entity_mapping)

    @pytest.mark.asyncio
    async def test_validate_entity_counts_match(
        self, validator, mock_ss_kg, mock_ib_service
    ):
        """Entity counts match between systems."""
        mock_ss_kg.entity_counts = {"Issue": 10, "PR": 5}
        mock_ib_service.entity_counts = {"github_issue": 10, "pull_request": 5}

        passed, metrics = await validator.validate_entity_counts()

        assert passed is True
        assert metrics["mismatches"] == []

    @pytest.mark.asyncio
    async def test_validate_entity_counts_mismatch(
        self, validator, mock_ss_kg, mock_ib_service
    ):
        """Entity counts mismatch is detected."""
        mock_ss_kg.entity_counts = {"Issue": 10, "PR": 5}
        mock_ib_service.entity_counts = {"github_issue": 8, "pull_request": 5}

        passed, metrics = await validator.validate_entity_counts()

        assert passed is False
        assert len(metrics["mismatches"]) == 1
        assert metrics["mismatches"][0]["ss_type"] == "Issue"
        assert metrics["mismatches"][0]["difference"] == 2

    @pytest.mark.asyncio
    async def test_validate_relationship_counts_match(
        self, validator, mock_ss_kg, mock_ib_service
    ):
        """Relationship counts match between systems."""
        mock_ss_kg.relationship_counts = {"implements": 20, "tests": 10}
        mock_ib_service.relationship_counts = {"implements": 20, "tests": 10}

        passed, metrics = await validator.validate_relationship_counts()

        assert passed is True

    @pytest.mark.asyncio
    async def test_validate_random_sample_pass(
        self, validator, mock_ss_kg, mock_ib_service
    ):
        """Random sample validation passes when entities match."""
        mock_ss_kg.entities = {
            "issue-001": {"name": "Issue 1", "type": "Issue"},
            "issue-002": {"name": "Issue 2", "type": "Issue"},
        }
        mock_ib_service.entities = {
            "ib-001": {"name": "Issue 1", "entity_type": "github_issue"},
            "ib-002": {"name": "Issue 2", "entity_type": "github_issue"},
        }

        passed, metrics = await validator.validate_random_sample(sample_size=2)

        assert passed is True
        assert metrics["matched"] == 2
        assert metrics["validated"] == 2
        assert metrics["mismatched"] == 0

    @pytest.mark.asyncio
    async def test_validate_random_sample_mismatch(
        self, validator, mock_ss_kg, mock_ib_service
    ):
        """Random sample validation detects mismatches."""
        mock_ss_kg.entities = {
            "issue-001": {"name": "Issue 1", "type": "Issue"},
        }
        mock_ib_service.entities = {
            "ib-001": {"name": "Different Name", "entity_type": "github_issue"},
        }

        passed, metrics = await validator.validate_random_sample(sample_size=1)

        assert passed is False
        assert metrics["mismatched"] == 1

    @pytest.mark.asyncio
    async def test_validate_random_sample_no_mapping(self, mock_ss_kg, mock_ib_service):
        """Random sample validation skips when no mapping available."""
        validator = MigrationValidator(mock_ss_kg, mock_ib_service, {})

        passed, metrics = await validator.validate_random_sample()

        assert passed is True
        assert "skipped" in metrics

    @pytest.mark.asyncio
    async def test_validate_all(self, validator, mock_ss_kg, mock_ib_service):
        """validate_all runs all validations."""
        mock_ss_kg.entity_counts = {"Issue": 5}
        mock_ib_service.entity_counts = {"github_issue": 5}
        mock_ss_kg.relationship_counts = {"implements": 3}
        mock_ib_service.relationship_counts = {"implements": 3}

        result = await validator.validate_all()

        assert "validated_at" in result.metrics
        assert "entity_counts" in result.metrics
        assert "relationship_counts" in result.metrics


class TestCutoverManager:
    """Tests for CutoverManager class."""

    @pytest.fixture
    def mock_ss_kg(self):
        """Create mock SS knowledge graph."""
        return MockSSKnowledgeGraph()

    @pytest.fixture
    def mock_ib_service(self):
        """Create mock IB service."""
        return MockValidatorIBService()

    @pytest.fixture
    def manager(self, mock_ss_kg, mock_ib_service):
        """Create cutover manager."""
        return CutoverManager(mock_ss_kg, mock_ib_service)

    def test_initial_mode_is_legacy(self, manager):
        """Manager starts in legacy mode."""
        assert manager.mode == "legacy"

    @pytest.mark.asyncio
    async def test_enable_parallel_mode(self, manager):
        """Enable parallel mode."""
        result = await manager.enable_parallel_mode()

        assert result is True
        assert manager.mode == "parallel"

    @pytest.mark.asyncio
    async def test_enable_ib_only_mode(self, manager):
        """Enable IB-only mode."""
        result = await manager.enable_ib_only_mode()

        assert result is True
        assert manager.mode == "ib_only"

    @pytest.mark.asyncio
    async def test_rollback_to_legacy(self, manager):
        """Rollback to legacy mode."""
        await manager.enable_ib_only_mode()
        result = await manager.rollback_to_legacy()

        assert result is True
        assert manager.mode == "legacy"

    @pytest.mark.asyncio
    async def test_log_discrepancy(self, manager):
        """Log discrepancy between systems."""
        await manager.log_discrepancy(
            query="test query",
            ss_result=[1, 2, 3],
            ib_result=[1, 2],
        )

        discrepancies = manager.get_discrepancies()
        assert len(discrepancies) == 1
        assert discrepancies[0]["query"] == "test query"
        assert discrepancies[0]["ss_result_count"] == 3
        assert discrepancies[0]["ib_result_count"] == 2

    @pytest.mark.asyncio
    async def test_complete_cutover(self, manager):
        """Complete cutover to IB."""
        await manager.enable_parallel_mode()
        await manager.log_discrepancy("q", [], [])

        result = await manager.complete_cutover()

        assert result["status"] == "completed"
        assert result["previous_mode"] == "parallel"
        assert result["discrepancy_count"] == 1
        assert manager.mode == "ib_only"

    @pytest.mark.asyncio
    async def test_verify_cutover(self, manager, mock_ss_kg, mock_ib_service):
        """Verify cutover runs validation."""
        mock_ss_kg.entity_counts = {"Issue": 5}
        mock_ib_service.entity_counts = {"github_issue": 5}
        mock_ss_kg.relationship_counts = {}
        mock_ib_service.relationship_counts = {}

        result = await manager.verify_cutover()

        assert isinstance(result, ValidationResult)


class TestParallelValidator:
    """Tests for ParallelValidator helper."""

    @pytest.mark.asyncio
    async def test_parallel_validator_matches(self):
        """Parallel validator reports matches when counts align."""
        mock_ss_kg = MockSSKnowledgeGraph()
        mock_ib_service = MockValidatorIBService()
        validator = ParallelValidator(mock_ss_kg, mock_ib_service)

        mock_ss_kg.query_results = [{"id": "issue-001"}]
        mock_ib_service.search_entities_result = {"entities": [{"entity_id": "ib-001"}]}

        result = await validator.validate_query("issue")

        assert result["matches"] is True

    @pytest.mark.asyncio
    async def test_parallel_validator_logs_mismatch(self):
        """Parallel validator detects mismatch counts."""
        mock_ss_kg = MockSSKnowledgeGraph()
        mock_ib_service = MockValidatorIBService()
        manager = CutoverManager(mock_ss_kg, mock_ib_service)
        validator = ParallelValidator(mock_ss_kg, mock_ib_service, manager)

        mock_ss_kg.query_results = [{"id": "issue-001"}, {"id": "issue-002"}]
        mock_ib_service.search_entities_result = {"entities": [{"entity_id": "ib-001"}]}

        result = await validator.validate_query("issue")

        assert result["matches"] is False
        assert len(manager.get_discrepancies()) == 1


# ============================================================================
# Mock Services for Testing
# ============================================================================


class MockSSKnowledgeGraph:
    """Mock Smart-Scaffold knowledge graph."""

    def __init__(self):
        self.entity_counts = {}
        self.relationship_counts = {}
        self.entities = {}
        self.query_results = []

    async def count_by_type(self) -> dict:
        """Return entity counts by type."""
        return self.entity_counts

    async def count_relationships_by_type(self) -> dict:
        """Return relationship counts by type."""
        return self.relationship_counts

    async def get_node(self, node_id: str) -> dict:
        """Get entity by ID."""
        return self.entities.get(node_id)

    async def query(self, query: str):
        """Return query results."""
        return self.query_results


class MockValidatorIBService:
    """Mock IB service for validator testing."""

    def __init__(self):
        self.entity_counts = {}
        self.relationship_counts = {}
        self.entities = {}
        self.search_entities_result = {"entities": []}

    async def query_entities(self, entity_type: str = None, limit: int = 100, **kwargs):
        """Mock entity query."""
        if limit == 0:
            # Count query
            count = self.entity_counts.get(entity_type, 0)
            return {"total": count, "entities": []}
        return {"entities": [], "total": 0}

    async def query_relationships(self, relationship_type: str = None, **kwargs):
        """Mock relationship query."""
        count = self.relationship_counts.get(relationship_type, 0)
        return {"total": count, "relationships": []}

    async def get_entity_by_id(self, entity_id: str) -> dict:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    async def search_entities(self, **kwargs):
        """Mock search."""
        return self.search_entities_result
