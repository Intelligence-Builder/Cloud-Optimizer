"""Smart-Scaffold integration for Intelligence-Builder platform.

This module provides migration and integration tools for Smart-Scaffold
to use Intelligence-Builder for knowledge graph operations.

Components:
- EntityMigrator: Migrate SS entities to IB
- RelationshipMigrator: Migrate SS relationships to IB
- ContextIBSync: Sync SS context records to IB
- WorkflowCoordinator: Use IB for graph operations
- MigrationValidator: Validate migration integrity
- CutoverManager: Manage production cutover
"""

from cloud_optimizer.integrations.smart_scaffold.context_sync import (
    ContextIBSync,
    SyncResult,
    WorkflowCoordinator,
)
from cloud_optimizer.integrations.smart_scaffold.hybrid import HybridKnowledgeGraph
from cloud_optimizer.integrations.smart_scaffold.entity_migrator import (
    EntityMigrator,
    EntityTypeMapping,
    MigrationResult,
)
from cloud_optimizer.integrations.smart_scaffold.relationship_migrator import (
    RelationshipMigrationResult,
    RelationshipMigrator,
    RelationshipTypeMapping,
)
from cloud_optimizer.integrations.smart_scaffold.validator import (
    CutoverManager,
    MigrationValidator,
    ParallelValidator,
    ValidationResult,
)

__all__ = [
    # Entity Migration (Issue #19)
    "EntityMigrator",
    "EntityTypeMapping",
    "MigrationResult",
    # Relationship Migration (Issue #19)
    "RelationshipMigrator",
    "RelationshipTypeMapping",
    "RelationshipMigrationResult",
    # Context Integration (Issue #20)
    "ContextIBSync",
    "SyncResult",
    "WorkflowCoordinator",
    "HybridKnowledgeGraph",
    # Cutover Validation (Issue #21)
    "MigrationValidator",
    "ValidationResult",
    "CutoverManager",
    "ParallelValidator",
]
