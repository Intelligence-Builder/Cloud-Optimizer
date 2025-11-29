"""Context system integration with Intelligence-Builder.

Synchronizes Smart-Scaffold context records to IB entities while
preserving local context storage for high-frequency operations.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of context sync operation.

    Attributes:
        synced: Successfully synced count
        failed: Failed sync count
        entity_ids: Map of context IDs to IB entity IDs
        errors: List of error messages
    """

    synced: int = 0
    failed: int = 0
    entity_ids: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def add_success(self, context_id: str, entity_id: str) -> None:
        """Record successful sync."""
        self.synced += 1
        self.entity_ids[context_id] = entity_id

    def add_failure(self, context_id: str, error: str) -> None:
        """Record failed sync."""
        self.failed += 1
        self.errors.append(f"Context {context_id}: {error}")


class ContextIBSync:
    """Synchronize local context with IB entities.

    This class bridges Smart-Scaffold's local context system with
    Intelligence-Builder, creating/updating entities when context
    is finalized while keeping high-frequency updates local.

    Local Storage (PostgreSQL):
    - Context revisions (high-frequency writes)
    - Session state (ephemeral)
    - Workflow events (temporal)

    IB Storage (via SDK):
    - Finalized context records
    - Cross-session context discovery
    - Pattern detection across contexts

    Example:
        >>> sync = ContextIBSync(ib_service)
        >>> result = await sync.sync_context(context_record)
        >>> print(f"Created entity: {result.entity_ids}")
    """

    def __init__(self, ib_service: Any) -> None:
        """Initialize context sync.

        Args:
            ib_service: Intelligence-Builder service instance
        """
        self.ib_service = ib_service
        self.logger = logging.getLogger(__name__)

    async def sync_context(self, context: Dict[str, Any]) -> SyncResult:
        """Sync single context record to IB.

        Creates or updates a context_record entity in IB with the
        context content and metadata.

        Args:
            context: Context record with id, name, revision, content, etc.

        Returns:
            SyncResult with sync status
        """
        result = SyncResult()
        context_id = context.get("id", "unknown")

        try:
            # Build entity data
            entity_data = self._build_entity_data(context)

            # Create or update entity in IB
            ib_result = await self.ib_service.create_entity(entity_data)
            entity_id = str(ib_result.get("entity_id", ib_result.get("id", "")))

            result.add_success(context_id, entity_id)

            # Link to referenced entities
            references = context.get("references", [])
            if references:
                await self._link_references(entity_id, references)

            self.logger.info(f"Synced context {context_id} -> entity {entity_id}")

        except Exception as e:
            self.logger.error(f"Failed to sync context {context_id}: {e}")
            result.add_failure(context_id, str(e))

        return result

    def _build_entity_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build IB entity data from context record.

        Args:
            context: Context record dict

        Returns:
            IB entity data dict
        """
        context_id = context.get("id", "unknown")
        name = context.get("name", f"context-{context_id}")

        return {
            "entity_type": "context_record",
            "domain": "workflow",
            "name": name,
            "properties": {
                "context_id": context_id,
                "revision": context.get("revision", 1),
                "context_type": context.get("type", "general"),
                "content": context.get("content", {}),
                "session_id": context.get("session_id"),
                "task_id": context.get("task_id"),
                "issue_number": context.get("issue_number"),
                "finalized": context.get("finalized", False),
                "finalized_at": context.get("finalized_at"),
                "created_at": context.get(
                    "created_at", datetime.now(timezone.utc).isoformat()
                ),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            "metadata": {
                "source": "smart-scaffold",
                "sync_type": "context_record",
                "synced_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _link_references(
        self, context_entity_id: str, references: List[Dict[str, Any]]
    ) -> None:
        """Link context entity to referenced entities.

        Args:
            context_entity_id: IB entity ID of the context
            references: List of reference dicts with type and id
        """
        for ref in references:
            try:
                ref_type = ref.get("type", "unknown")
                ref_id = ref.get("id") or ref.get("github_id")

                if not ref_id:
                    continue

                # Search for referenced entity in IB
                target_entities = await self._find_referenced_entity(ref_type, ref_id)

                if target_entities:
                    target_id = str(target_entities[0].get("entity_id", ""))
                    await self.ib_service.create_relationship(
                        {
                            "source_id": context_entity_id,
                            "target_id": target_id,
                            "relationship_type": "references",
                            "domain": "workflow",
                        }
                    )
                    self.logger.debug(
                        f"Linked context {context_entity_id} -> {target_id}"
                    )

            except Exception as e:
                self.logger.warning(f"Failed to link reference: {e}")

    async def _find_referenced_entity(
        self, ref_type: str, ref_id: str
    ) -> List[Dict[str, Any]]:
        """Find referenced entity in IB.

        Args:
            ref_type: Type of referenced entity (issue, pr, commit, etc.)
            ref_id: ID or number of referenced entity

        Returns:
            List of matching entities
        """
        # Map reference types to IB entity types
        type_mapping = {
            "issue": "github_issue",
            "pr": "pull_request",
            "pull_request": "pull_request",
            "commit": "commit",
            "file": "code_file",
        }

        ib_type = type_mapping.get(ref_type.lower(), ref_type)

        # Search by original ID in metadata
        try:
            result = await self.ib_service.query_entities(
                entity_type=ib_type,
                filters={"metadata.original_id": ref_id},
                limit=1,
            )
            return result.get("entities", [])
        except Exception:
            # Fallback: search by property
            try:
                result = await self.ib_service.query_entities(
                    entity_type=ib_type,
                    filters={"properties.issue_number": ref_id},
                    limit=1,
                )
                return result.get("entities", [])
            except Exception:
                return []

    async def sync_session_end(
        self, session_id: str, final_context: Dict[str, Any]
    ) -> SyncResult:
        """Sync context at session end.

        Called when a Smart-Scaffold session ends to sync the final
        context state to IB for cross-session discovery.

        Args:
            session_id: Session identifier
            final_context: Final context state

        Returns:
            SyncResult with sync status
        """
        # Add session info to context
        final_context["session_id"] = session_id
        final_context["finalized"] = True
        final_context["finalized_at"] = datetime.now(timezone.utc).isoformat()

        return await self.sync_context(final_context)

    async def sync_batch(self, contexts: List[Dict[str, Any]]) -> SyncResult:
        """Sync multiple context records.

        Args:
            contexts: List of context records to sync

        Returns:
            Aggregated SyncResult
        """
        result = SyncResult()

        for context in contexts:
            single_result = await self.sync_context(context)
            result.synced += single_result.synced
            result.failed += single_result.failed
            result.entity_ids.update(single_result.entity_ids)
            result.errors.extend(single_result.errors)

        return result


class WorkflowCoordinator:
    """Coordinate workflow operations using IB for graph queries.

    Uses IB platform for knowledge graph operations while keeping
    session state and high-frequency operations local.

    Example:
        >>> coordinator = WorkflowCoordinator(ib_service, local_store)
        >>> path = await coordinator.find_implementation_path("issue-123")
        >>> similar = await coordinator.find_similar_issues("auth bug")
    """

    def __init__(self, ib_service: Any, local_store: Optional[Any] = None) -> None:
        """Initialize workflow coordinator.

        Args:
            ib_service: Intelligence-Builder service instance
            local_store: Optional local context store for session state
        """
        self.ib_service = ib_service
        self.local_store = local_store
        self.logger = logging.getLogger(__name__)

    async def find_implementation_path(
        self, issue_id: str, max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """Find implementation path from issue to code.

        Uses IB graph traversal to find path from an issue
        through commits/PRs to code files.

        Args:
            issue_id: Issue entity ID or original SS ID
            max_depth: Maximum traversal depth

        Returns:
            List of nodes in the implementation path
        """
        try:
            # Find the issue entity
            entities = await self.ib_service.query_entities(
                entity_type="github_issue",
                filters={"metadata.original_id": issue_id},
                limit=1,
            )

            if not entities.get("entities"):
                self.logger.warning(f"Issue not found: {issue_id}")
                return []

            entity_id = str(entities["entities"][0].get("entity_id", ""))

            # Traverse graph to find code files
            traversal = await self.ib_service.traverse_graph(
                entity_id=entity_id,
                depth=max_depth,
                relationship_types=["implements", "modifies", "references"],
            )

            # Extract path nodes
            path = []
            for node in traversal.get("nodes", []):
                path.append(
                    {
                        "id": str(node.get("entity_id", "")),
                        "type": node.get("entity_type", ""),
                        "name": node.get("name", ""),
                        "properties": node.get("properties", {}),
                    }
                )

            return path

        except Exception as e:
            self.logger.error(f"Failed to find implementation path: {e}")
            return []

    async def find_similar_issues(
        self, description: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find similar issues using IB vector search.

        Args:
            description: Text description to match
            limit: Maximum number of results

        Returns:
            List of similar issue entities
        """
        try:
            result = await self.ib_service.search_entities(
                query_text=description,
                entity_types=["github_issue"],
                limit=limit,
            )

            return [
                {
                    "id": str(e.get("entity_id", "")),
                    "name": e.get("name", ""),
                    "score": e.get("score", 0.0),
                    "properties": e.get("properties", {}),
                }
                for e in result.get("entities", [])
            ]

        except Exception as e:
            self.logger.error(f"Failed to find similar issues: {e}")
            return []

    async def find_related_patterns(self, issue_id: str) -> List[Dict[str, Any]]:
        """Find patterns related to an issue.

        Args:
            issue_id: Issue entity ID

        Returns:
            List of related pattern entities
        """
        try:
            traversal = await self.ib_service.traverse_graph(
                entity_id=issue_id,
                depth=2,
                relationship_types=["has_pattern", "matches_pattern"],
            )

            patterns = []
            for node in traversal.get("nodes", []):
                if node.get("entity_type") == "pattern":
                    patterns.append(
                        {
                            "id": str(node.get("entity_id", "")),
                            "name": node.get("name", ""),
                            "confidence": node.get("properties", {}).get(
                                "confidence", 0
                            ),
                            "occurrences": node.get("properties", {}).get(
                                "occurrences", 0
                            ),
                        }
                    )

            return patterns

        except Exception as e:
            self.logger.error(f"Failed to find related patterns: {e}")
            return []

    async def get_context_for_issue(
        self, issue_number: int
    ) -> Optional[Dict[str, Any]]:
        """Get context record for an issue.

        Args:
            issue_number: GitHub issue number

        Returns:
            Context record if found
        """
        try:
            result = await self.ib_service.query_entities(
                entity_type="context_record",
                filters={"properties.issue_number": issue_number},
                limit=1,
            )

            entities = result.get("entities", [])
            if entities:
                return entities[0]
            return None

        except Exception as e:
            self.logger.error(f"Failed to get context for issue {issue_number}: {e}")
            return None
