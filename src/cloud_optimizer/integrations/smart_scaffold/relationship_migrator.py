"""Relationship migration from Smart-Scaffold to Intelligence-Builder.

Migrates Smart-Scaffold knowledge graph relationships to IB platform
using the entity ID mapping from entity migration.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RelationshipTypeMapping:
    """Mapping configuration for SS relationship types to IB.

    Attributes:
        ss_type: Smart-Scaffold relationship type name
        ib_type: Target IB relationship type
        ib_domain: Target IB domain
        bidirectional: Whether relationship is bidirectional
    """

    ss_type: str
    ib_type: str
    ib_domain: str = "development"
    bidirectional: bool = False


# Default relationship type mappings
DEFAULT_RELATIONSHIP_MAPPINGS: List[RelationshipTypeMapping] = [
    RelationshipTypeMapping(
        ss_type="implements",
        ib_type="implements",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="IMPLEMENTS",
        ib_type="implements",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="tests",
        ib_type="tests",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="TESTS",
        ib_type="tests",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="modifies",
        ib_type="modifies",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="MODIFIES",
        ib_type="modifies",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="references",
        ib_type="references",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="REFERENCES",
        ib_type="references",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="depends_on",
        ib_type="depends_on",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="DEPENDS_ON",
        ib_type="depends_on",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="contains",
        ib_type="contains",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="CONTAINS",
        ib_type="contains",
        ib_domain="development",
    ),
    RelationshipTypeMapping(
        ss_type="belongs_to",
        ib_type="belongs_to",
        ib_domain="workflow",
    ),
    RelationshipTypeMapping(
        ss_type="BELONGS_TO",
        ib_type="belongs_to",
        ib_domain="workflow",
    ),
]


@dataclass
class RelationshipMigrationResult:
    """Result of relationship migration operation.

    Attributes:
        total: Total relationships processed
        migrated: Successfully migrated count
        failed: Failed migration count
        skipped: Skipped relationships (missing entities)
        errors: List of error messages
        duration_seconds: Migration duration
    """

    total: int = 0
    migrated: int = 0
    failed: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def add_success(self) -> None:
        """Record successful migration."""
        self.migrated += 1

    def add_failure(self, rel_id: str, error: str) -> None:
        """Record failed migration."""
        self.failed += 1
        self.errors.append(f"Relationship {rel_id}: {error}")

    def add_skipped(self, rel_id: str, reason: str) -> None:
        """Record skipped relationship."""
        self.skipped += 1
        self.errors.append(f"Skipped {rel_id}: {reason}")


class RelationshipMigrator:
    """Migrate Smart-Scaffold relationships to Intelligence-Builder.

    This class handles the migration of relationships from Smart-Scaffold's
    knowledge graph to the Intelligence-Builder platform, using the entity
    ID mapping from EntityMigrator.

    Example:
        >>> # First migrate entities
        >>> entity_result = await entity_migrator.migrate_all(ss_entities)
        >>> # Then migrate relationships using ID mapping
        >>> rel_migrator = RelationshipMigrator(ib_service, entity_result.id_mapping)
        >>> rel_result = await rel_migrator.migrate_all(ss_relationships)
    """

    def __init__(
        self,
        ib_service: Any,
        entity_id_mapping: Dict[str, str],
        type_mappings: Optional[List[RelationshipTypeMapping]] = None,
        batch_size: int = 100,
    ) -> None:
        """Initialize relationship migrator.

        Args:
            ib_service: Intelligence-Builder service instance
            entity_id_mapping: Map of SS entity IDs to IB entity IDs
            type_mappings: Custom relationship type mappings
            batch_size: Number of relationships to process per batch
        """
        self.ib_service = ib_service
        self.entity_id_mapping = entity_id_mapping
        self.batch_size = batch_size

        # Build type mapping lookup
        mappings = type_mappings or DEFAULT_RELATIONSHIP_MAPPINGS
        self._type_map: Dict[str, RelationshipTypeMapping] = {
            m.ss_type: m for m in mappings
        }

        self.logger = logging.getLogger(__name__)

    def get_type_mapping(self, ss_type: str) -> Optional[RelationshipTypeMapping]:
        """Get IB type mapping for SS relationship type.

        Args:
            ss_type: Smart-Scaffold relationship type

        Returns:
            RelationshipTypeMapping if found, None otherwise
        """
        return self._type_map.get(ss_type)

    def transform_relationship(
        self, ss_rel: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Transform SS relationship to IB format.

        Args:
            ss_rel: Smart-Scaffold relationship dict with 'type',
                    'source_id', 'target_id', and optional 'properties'

        Returns:
            Tuple of (IB relationship dict, error message if any)
        """
        ss_type = ss_rel.get("type")
        if not ss_type:
            return None, "Relationship missing 'type' field"

        mapping = self.get_type_mapping(ss_type)
        if not mapping:
            return None, f"No mapping for relationship type: {ss_type}"

        # Get source and target IDs
        ss_source_id = ss_rel.get("source_id")
        ss_target_id = ss_rel.get("target_id")

        if not ss_source_id or not ss_target_id:
            return None, "Relationship missing source_id or target_id"

        # Map to IB entity IDs
        ib_source_id = self.entity_id_mapping.get(ss_source_id)
        ib_target_id = self.entity_id_mapping.get(ss_target_id)

        if not ib_source_id:
            return None, f"Source entity not found in mapping: {ss_source_id}"
        if not ib_target_id:
            return None, f"Target entity not found in mapping: {ss_target_id}"

        ss_properties = ss_rel.get("properties", {})

        ib_rel = {
            "source_id": ib_source_id,
            "target_id": ib_target_id,
            "relationship_type": mapping.ib_type,
            "domain": mapping.ib_domain,
            "properties": ss_properties,
            "metadata": {
                "migrated_from": "smart-scaffold",
                "original_source_id": ss_source_id,
                "original_target_id": ss_target_id,
                "original_type": ss_type,
                "migrated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        return ib_rel, None

    async def migrate_relationship(
        self, ss_rel: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Migrate single relationship to IB.

        Args:
            ss_rel: Smart-Scaffold relationship to migrate

        Returns:
            Tuple of (success bool, error message if failure)
        """
        rel_id = f"{ss_rel.get('source_id', '?')}->{ss_rel.get('target_id', '?')}"

        # Transform relationship
        ib_rel, error = self.transform_relationship(ss_rel)
        if error:
            return False, error

        try:
            # Create relationship in IB
            await self.ib_service.create_relationship(ib_rel)

            self.logger.debug(f"Migrated relationship {rel_id}")
            return True, None

        except Exception as e:
            self.logger.error(f"Failed to migrate relationship {rel_id}: {e}")
            return False, str(e)

    async def migrate_batch(
        self,
        ss_relationships: List[Dict[str, Any]],
        result: RelationshipMigrationResult,
    ) -> None:
        """Migrate batch of relationships concurrently.

        Args:
            ss_relationships: List of SS relationships to migrate
            result: RelationshipMigrationResult to update
        """
        tasks = []
        rel_ids = []

        for rel in ss_relationships:
            rel_id = f"{rel.get('source_id', '?')}->{rel.get('target_id', '?')}"
            rel_ids.append(rel_id)
            tasks.append(self.migrate_relationship(rel))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for rel_id, res in zip(rel_ids, results):
            if isinstance(res, Exception):
                result.add_failure(rel_id, str(res))
            elif res[0]:  # Success - (True, None)
                result.add_success()
            else:  # Failure - (False, error)
                error_msg = res[1] or "Unknown error"
                if "not found in mapping" in error_msg:
                    result.add_skipped(rel_id, error_msg)
                else:
                    result.add_failure(rel_id, error_msg)

    async def migrate_all(
        self,
        ss_relationships: List[Dict[str, Any]],
        progress_callback: Optional[Any] = None,
    ) -> RelationshipMigrationResult:
        """Migrate all relationships from Smart-Scaffold to IB.

        Args:
            ss_relationships: List of all SS relationships to migrate
            progress_callback: Optional callback(migrated, total) for progress

        Returns:
            RelationshipMigrationResult with migration statistics
        """
        start_time = datetime.now(timezone.utc)
        result = RelationshipMigrationResult(total=len(ss_relationships))

        self.logger.info(f"Starting migration of {result.total} relationships")

        # Process in batches
        for i in range(0, len(ss_relationships), self.batch_size):
            batch = ss_relationships[i : i + self.batch_size]
            await self.migrate_batch(batch, result)

            if progress_callback:
                progress_callback(
                    result.migrated + result.failed + result.skipped, result.total
                )

            self.logger.info(
                f"Progress: {result.migrated + result.failed + result.skipped}/"
                f"{result.total} (migrated={result.migrated}, "
                f"failed={result.failed}, skipped={result.skipped})"
            )

        end_time = datetime.now(timezone.utc)
        result.duration_seconds = (end_time - start_time).total_seconds()

        self.logger.info(
            f"Relationship migration complete: {result.migrated} migrated, "
            f"{result.failed} failed, {result.skipped} skipped "
            f"in {result.duration_seconds:.2f}s"
        )

        return result

    async def migrate_by_type(
        self,
        ss_relationships: List[Dict[str, Any]],
        relationship_types: Optional[List[str]] = None,
    ) -> RelationshipMigrationResult:
        """Migrate relationships filtered by type.

        Args:
            ss_relationships: List of all SS relationships
            relationship_types: List of SS relationship types to migrate

        Returns:
            RelationshipMigrationResult with migration statistics
        """
        if relationship_types:
            filtered = [
                r for r in ss_relationships if r.get("type") in relationship_types
            ]
            self.logger.info(
                f"Filtered to {len(filtered)} relationships "
                f"of types: {relationship_types}"
            )
        else:
            filtered = ss_relationships

        return await self.migrate_all(filtered)
