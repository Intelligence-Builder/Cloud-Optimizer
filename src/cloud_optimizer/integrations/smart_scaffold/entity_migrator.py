"""Entity migration from Smart-Scaffold to Intelligence-Builder.

Migrates Smart-Scaffold knowledge graph entities to IB platform
while preserving properties and metadata.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class EntityTypeMapping:
    """Mapping configuration for SS entity types to IB.

    Attributes:
        ss_type: Smart-Scaffold entity type name
        ib_domain: Target IB domain
        ib_type: Target IB entity type
        property_mapping: Map SS properties to IB properties
    """

    ss_type: str
    ib_domain: str
    ib_type: str
    property_mapping: Dict[str, str] = field(default_factory=dict)

    def transform_properties(self, ss_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Transform SS properties to IB format."""
        ib_properties = {}
        for ss_key, value in ss_properties.items():
            ib_key = self.property_mapping.get(ss_key, ss_key)
            ib_properties[ib_key] = value
        return ib_properties


# Default entity type mappings
DEFAULT_ENTITY_MAPPINGS: List[EntityTypeMapping] = [
    EntityTypeMapping(
        ss_type="Issue",
        ib_domain="development",
        ib_type="github_issue",
        property_mapping={
            "number": "issue_number",
            "state": "status",
            "created_at": "created_at",
            "updated_at": "updated_at",
            "closed_at": "closed_at",
        },
    ),
    EntityTypeMapping(
        ss_type="PR",
        ib_domain="development",
        ib_type="pull_request",
        property_mapping={
            "number": "pr_number",
            "state": "status",
            "merged": "is_merged",
            "merged_at": "merged_at",
        },
    ),
    EntityTypeMapping(
        ss_type="Commit",
        ib_domain="development",
        ib_type="commit",
        property_mapping={
            "sha": "commit_sha",
            "message": "commit_message",
            "author": "author_name",
            "authored_date": "authored_at",
        },
    ),
    EntityTypeMapping(
        ss_type="File",
        ib_domain="development",
        ib_type="code_file",
        property_mapping={
            "path": "file_path",
            "language": "programming_language",
            "size": "file_size_bytes",
        },
    ),
    EntityTypeMapping(
        ss_type="Function",
        ib_domain="development",
        ib_type="code_function",
        property_mapping={
            "name": "function_name",
            "signature": "function_signature",
            "file_path": "file_path",
            "start_line": "start_line",
            "end_line": "end_line",
        },
    ),
    EntityTypeMapping(
        ss_type="Context",
        ib_domain="workflow",
        ib_type="context_record",
        property_mapping={
            "revision": "revision_number",
            "content": "context_content",
            "session_id": "session_id",
        },
    ),
    EntityTypeMapping(
        ss_type="Session",
        ib_domain="workflow",
        ib_type="workflow_session",
        property_mapping={
            "started_at": "started_at",
            "ended_at": "ended_at",
            "agent_id": "agent_id",
            "task_id": "task_id",
        },
    ),
]


@dataclass
class MigrationResult:
    """Result of entity migration operation.

    Attributes:
        total: Total entities processed
        migrated: Successfully migrated count
        failed: Failed migration count
        skipped: Skipped entities count
        id_mapping: Map of SS entity IDs to IB entity IDs
        errors: List of error messages
        duration_seconds: Migration duration
    """

    total: int = 0
    migrated: int = 0
    failed: int = 0
    skipped: int = 0
    id_mapping: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def add_success(self, ss_id: str, ib_id: str) -> None:
        """Record successful migration."""
        self.migrated += 1
        self.id_mapping[ss_id] = ib_id

    def add_failure(self, ss_id: str, error: str) -> None:
        """Record failed migration."""
        self.failed += 1
        self.errors.append(f"Entity {ss_id}: {error}")

    def add_skipped(self, ss_id: str, reason: str) -> None:
        """Record skipped entity."""
        self.skipped += 1
        self.errors.append(f"Skipped {ss_id}: {reason}")


class EntityMigrator:
    """Migrate Smart-Scaffold entities to Intelligence-Builder.

    This class handles the migration of entities from Smart-Scaffold's
    knowledge graph to the Intelligence-Builder platform, preserving
    properties and tracking ID mappings for relationship migration.

    Example:
        >>> migrator = EntityMigrator(ib_service)
        >>> result = await migrator.migrate_all(ss_entities)
        >>> print(f"Migrated {result.migrated} entities")
    """

    def __init__(
        self,
        ib_service: Any,
        type_mappings: Optional[List[EntityTypeMapping]] = None,
        batch_size: int = 100,
    ) -> None:
        """Initialize entity migrator.

        Args:
            ib_service: Intelligence-Builder service instance
            type_mappings: Custom entity type mappings (uses defaults if None)
            batch_size: Number of entities to process per batch
        """
        self.ib_service = ib_service
        self.batch_size = batch_size

        # Build type mapping lookup
        mappings = type_mappings or DEFAULT_ENTITY_MAPPINGS
        self._type_map: Dict[str, EntityTypeMapping] = {m.ss_type: m for m in mappings}

        self.logger = logging.getLogger(__name__)

    def get_type_mapping(self, ss_type: str) -> Optional[EntityTypeMapping]:
        """Get IB type mapping for SS entity type.

        Args:
            ss_type: Smart-Scaffold entity type

        Returns:
            EntityTypeMapping if found, None otherwise
        """
        return self._type_map.get(ss_type)

    def transform_entity(
        self, ss_entity: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Transform SS entity to IB format.

        Args:
            ss_entity: Smart-Scaffold entity dict with 'type', 'id',
                       'name', and 'properties' keys

        Returns:
            Tuple of (IB entity dict, error message if any)
        """
        ss_type = ss_entity.get("type")
        if not ss_type:
            return None, "Entity missing 'type' field"

        mapping = self.get_type_mapping(ss_type)
        if not mapping:
            return None, f"No mapping for entity type: {ss_type}"

        ss_id = ss_entity.get("id")
        if not ss_id:
            return None, "Entity missing 'id' field"

        ss_name = ss_entity.get("name", f"{ss_type}-{ss_id}")
        ss_properties = ss_entity.get("properties", {})

        ib_entity = {
            "entity_type": mapping.ib_type,
            "domain": mapping.ib_domain,
            "name": ss_name,
            "properties": mapping.transform_properties(ss_properties),
            "metadata": {
                "migrated_from": "smart-scaffold",
                "original_id": ss_id,
                "original_type": ss_type,
                "migrated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        return ib_entity, None

    async def migrate_entity(
        self, ss_entity: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Migrate single entity to IB.

        Args:
            ss_entity: Smart-Scaffold entity to migrate

        Returns:
            Tuple of (IB entity ID if success, error message if failure)
        """
        ss_id = ss_entity.get("id", "unknown")

        # Transform entity
        ib_entity, error = self.transform_entity(ss_entity)
        if error:
            return None, error

        try:
            # Create entity in IB
            result = await self.ib_service.create_entity(ib_entity)
            ib_id = str(result.get("entity_id", result.get("id", "")))

            self.logger.debug(f"Migrated entity {ss_id} -> {ib_id}")
            return ib_id, None

        except Exception as e:
            self.logger.error(f"Failed to migrate entity {ss_id}: {e}")
            return None, str(e)

    async def migrate_batch(
        self, ss_entities: List[Dict[str, Any]], result: MigrationResult
    ) -> None:
        """Migrate batch of entities concurrently.

        Args:
            ss_entities: List of SS entities to migrate
            result: MigrationResult to update with results
        """
        tasks = []
        entity_ids = []

        for entity in ss_entities:
            ss_id = entity.get("id", "unknown")
            entity_ids.append(ss_id)
            tasks.append(self.migrate_entity(entity))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for ss_id, res in zip(entity_ids, results):
            if isinstance(res, Exception):
                result.add_failure(ss_id, str(res))
            elif res[0]:  # Success - (ib_id, None)
                result.add_success(ss_id, res[0])
            else:  # Failure - (None, error)
                result.add_failure(ss_id, res[1] or "Unknown error")

    async def migrate_all(
        self,
        ss_entities: List[Dict[str, Any]],
        progress_callback: Optional[Any] = None,
    ) -> MigrationResult:
        """Migrate all entities from Smart-Scaffold to IB.

        Args:
            ss_entities: List of all SS entities to migrate
            progress_callback: Optional callback(migrated, total) for progress

        Returns:
            MigrationResult with migration statistics and ID mapping
        """
        start_time = datetime.now(timezone.utc)
        result = MigrationResult(total=len(ss_entities))

        self.logger.info(f"Starting migration of {result.total} entities")

        # Process in batches
        for i in range(0, len(ss_entities), self.batch_size):
            batch = ss_entities[i : i + self.batch_size]
            await self.migrate_batch(batch, result)

            if progress_callback:
                progress_callback(result.migrated + result.failed, result.total)

            self.logger.info(
                f"Progress: {result.migrated + result.failed}/{result.total} "
                f"(migrated={result.migrated}, failed={result.failed})"
            )

        end_time = datetime.now(timezone.utc)
        result.duration_seconds = (end_time - start_time).total_seconds()

        self.logger.info(
            f"Migration complete: {result.migrated} migrated, "
            f"{result.failed} failed, {result.skipped} skipped "
            f"in {result.duration_seconds:.2f}s"
        )

        return result

    async def migrate_by_type(
        self,
        ss_entities: List[Dict[str, Any]],
        entity_types: Optional[List[str]] = None,
    ) -> MigrationResult:
        """Migrate entities filtered by type.

        Args:
            ss_entities: List of all SS entities
            entity_types: List of SS entity types to migrate (None = all)

        Returns:
            MigrationResult with migration statistics
        """
        if entity_types:
            filtered = [e for e in ss_entities if e.get("type") in entity_types]
            self.logger.info(
                f"Filtered to {len(filtered)} entities of types: {entity_types}"
            )
        else:
            filtered = ss_entities

        return await self.migrate_all(filtered)
