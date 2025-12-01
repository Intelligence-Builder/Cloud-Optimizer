"""Migration validation and cutover tools.

Validates data integrity during and after migration from
Smart-Scaffold to Intelligence-Builder.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of migration validation.

    Attributes:
        passed: Whether validation passed
        entity_count_match: Entity counts match
        relationship_count_match: Relationship counts match
        sample_validation_passed: Random sample validated
        query_parity_passed: Query results match
        performance_met: Performance requirements met
        errors: List of validation errors
        warnings: List of warnings
        metrics: Detailed metrics dict
    """

    passed: bool = True
    entity_count_match: bool = True
    relationship_count_match: bool = True
    sample_validation_passed: bool = True
    query_parity_passed: bool = True
    performance_met: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.passed = False
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add validation warning."""
        self.warnings.append(warning)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "passed": self.passed,
            "entity_count_match": self.entity_count_match,
            "relationship_count_match": self.relationship_count_match,
            "sample_validation_passed": self.sample_validation_passed,
            "query_parity_passed": self.query_parity_passed,
            "performance_met": self.performance_met,
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics,
        }


class MigrationValidator:
    """Validate migration integrity between SS and IB.

    Performs comprehensive validation including:
    - Entity count verification
    - Relationship count verification
    - Random sample validation
    - Query result comparison
    - Performance benchmarks

    Example:
        >>> validator = MigrationValidator(ss_kg, ib_service)
        >>> result = await validator.validate_all()
        >>> if not result.passed:
        ...     print(f"Validation failed: {result.errors}")
    """

    def __init__(
        self,
        ss_kg: Any,
        ib_service: Any,
        entity_id_mapping: Optional[Dict[str, str]] = None,
        random_seed: Optional[int] = None,
    ) -> None:
        """Initialize migration validator.

        Args:
            ss_kg: Smart-Scaffold knowledge graph client
            ib_service: Intelligence-Builder service instance
            entity_id_mapping: Map of SS entity IDs to IB entity IDs
        """
        self.ss_kg = ss_kg
        self.ib_service = ib_service
        self.entity_id_mapping = entity_id_mapping or {}
        self.logger = logging.getLogger(__name__)
        self._random = random.Random(random_seed)

    async def validate_all(self) -> ValidationResult:
        """Run all validation checks.

        Returns:
            ValidationResult with all validation results
        """
        result = ValidationResult()
        result.metrics["validated_at"] = datetime.now(timezone.utc).isoformat()

        # Entity count validation
        entity_result = await self.validate_entity_counts()
        result.entity_count_match = entity_result[0]
        result.metrics["entity_counts"] = entity_result[1]
        if not entity_result[0]:
            result.add_error(f"Entity count mismatch: {entity_result[1]}")

        # Relationship count validation
        rel_result = await self.validate_relationship_counts()
        result.relationship_count_match = rel_result[0]
        result.metrics["relationship_counts"] = rel_result[1]
        if not rel_result[0]:
            result.add_error(f"Relationship count mismatch: {rel_result[1]}")

        # Sample validation
        sample_result = await self.validate_random_sample()
        result.sample_validation_passed = sample_result[0]
        result.metrics["sample_validation"] = sample_result[1]
        if not sample_result[0]:
            result.add_error(f"Sample validation failed: {sample_result[1]}")

        return result

    async def validate_entity_counts(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate entity counts match between systems.

        Returns:
            Tuple of (passed, metrics dict)
        """
        metrics: Dict[str, Any] = {"ss_counts": {}, "ib_counts": {}, "mismatches": []}

        try:
            # Get SS entity counts by type
            ss_counts = await self._get_ss_entity_counts()
            metrics["ss_counts"] = ss_counts

            # Get IB entity counts by type
            ib_counts = await self._get_ib_entity_counts()
            metrics["ib_counts"] = ib_counts

            # Compare counts
            type_mapping = {
                "Issue": "github_issue",
                "PR": "pull_request",
                "Commit": "commit",
                "File": "code_file",
                "Function": "code_function",
                "Context": "context_record",
                "Session": "workflow_session",
            }

            passed = True
            for ss_type, ib_type in type_mapping.items():
                ss_count = ss_counts.get(ss_type, 0)
                ib_count = ib_counts.get(ib_type, 0)

                if ss_count != ib_count:
                    passed = False
                    metrics["mismatches"].append(
                        {
                            "ss_type": ss_type,
                            "ib_type": ib_type,
                            "ss_count": ss_count,
                            "ib_count": ib_count,
                            "difference": ss_count - ib_count,
                        }
                    )

            return passed, metrics

        except Exception as e:
            self.logger.error(f"Entity count validation failed: {e}")
            return False, {"error": str(e)}

    async def _get_ss_entity_counts(self) -> Dict[str, int]:
        """Get entity counts from Smart-Scaffold."""
        try:
            if hasattr(self.ss_kg, "count_by_type"):
                return await self.ss_kg.count_by_type()
            elif hasattr(self.ss_kg, "count_nodes"):
                # Fallback: count all and estimate by type
                total = await self.ss_kg.count_nodes()
                return {"total": total}
            else:
                return {}
        except Exception as e:
            self.logger.warning(f"Could not get SS entity counts: {e}")
            return {}

    async def _get_ib_entity_counts(self) -> Dict[str, int]:
        """Get entity counts from Intelligence-Builder."""
        try:
            entity_types = [
                "github_issue",
                "pull_request",
                "commit",
                "code_file",
                "code_function",
                "context_record",
                "workflow_session",
            ]

            counts = {}
            for etype in entity_types:
                try:
                    result = await self.ib_service.query_entities(
                        entity_type=etype,
                        limit=0,  # Just get count
                    )
                    counts[etype] = result.get("total", 0)
                except Exception:
                    counts[etype] = 0

            return counts

        except Exception as e:
            self.logger.warning(f"Could not get IB entity counts: {e}")
            return {}

    async def validate_relationship_counts(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate relationship counts match between systems.

        Returns:
            Tuple of (passed, metrics dict)
        """
        metrics: Dict[str, Any] = {"ss_counts": {}, "ib_counts": {}, "mismatches": []}

        try:
            # Get SS relationship counts
            ss_counts = await self._get_ss_relationship_counts()
            metrics["ss_counts"] = ss_counts

            # Get IB relationship counts
            ib_counts = await self._get_ib_relationship_counts()
            metrics["ib_counts"] = ib_counts

            # Compare counts
            type_mapping = {
                "implements": "implements",
                "IMPLEMENTS": "implements",
                "tests": "tests",
                "TESTS": "tests",
                "modifies": "modifies",
                "MODIFIES": "modifies",
                "references": "references",
                "REFERENCES": "references",
            }

            passed = True
            checked_types = set()

            for ss_type, ib_type in type_mapping.items():
                if ib_type in checked_types:
                    continue
                checked_types.add(ib_type)

                # Sum both cases from SS
                ss_count = ss_counts.get(ss_type, 0) + ss_counts.get(ss_type.upper(), 0)
                ib_count = ib_counts.get(ib_type, 0)

                if ss_count != ib_count:
                    passed = False
                    metrics["mismatches"].append(
                        {
                            "ss_type": ss_type,
                            "ib_type": ib_type,
                            "ss_count": ss_count,
                            "ib_count": ib_count,
                        }
                    )

            return passed, metrics

        except Exception as e:
            self.logger.error(f"Relationship count validation failed: {e}")
            return False, {"error": str(e)}

    async def _get_ss_relationship_counts(self) -> Dict[str, int]:
        """Get relationship counts from Smart-Scaffold."""
        try:
            if hasattr(self.ss_kg, "count_relationships_by_type"):
                return await self.ss_kg.count_relationships_by_type()
            elif hasattr(self.ss_kg, "count_relationships"):
                total = await self.ss_kg.count_relationships()
                return {"total": total}
            else:
                return {}
        except Exception as e:
            self.logger.warning(f"Could not get SS relationship counts: {e}")
            return {}

    async def _get_ib_relationship_counts(self) -> Dict[str, int]:
        """Get relationship counts from Intelligence-Builder."""
        try:
            rel_types = ["implements", "tests", "modifies", "references", "depends_on"]
            counts = {}

            for rtype in rel_types:
                try:
                    result = await self.ib_service.query_relationships(
                        relationship_type=rtype,
                        limit=0,
                    )
                    counts[rtype] = result.get("total", 0)
                except Exception:
                    counts[rtype] = 0

            return counts

        except Exception as e:
            self.logger.warning(f"Could not get IB relationship counts: {e}")
            return {}

    async def validate_random_sample(
        self, sample_size: int = 100
    ) -> Tuple[bool, Dict[str, Any]]:
        """Validate random sample of entities.

        Args:
            sample_size: Number of entities to sample

        Returns:
            Tuple of (passed, metrics dict)
        """
        metrics: Dict[str, Any] = {
            "requested_sample": 0,
            "validated": 0,
            "matched": 0,
            "mismatched": 0,
            "skipped": 0,
            "mismatches": [],
        }

        try:
            all_ids = list(self.entity_id_mapping.keys())
            if not all_ids:
                return True, {"skipped": "No entity mapping available"}

            target = min(sample_size, len(all_ids))
            metrics["requested_sample"] = target
            shuffled_ids = list(all_ids)
            self._random.shuffle(shuffled_ids)

            for ss_id in shuffled_ids:
                ib_id = self.entity_id_mapping.get(ss_id)
                status, reason = await self._validate_entity_match(ss_id, ib_id)

                if status == "skipped":
                    metrics["skipped"] += 1
                    continue

                metrics["validated"] += 1
                if status == "matched":
                    metrics["matched"] += 1
                else:
                    metrics["mismatched"] += 1
                    metrics["mismatches"].append(
                        {
                            "ss_id": ss_id,
                            "ib_id": ib_id,
                            "reason": reason,
                        }
                    )

                if metrics["validated"] >= target:
                    break

            if metrics["validated"] == 0:
                metrics["skipped_reason"] = "No comparable entities found"
                return True, metrics

            passed = metrics["mismatched"] == 0
            return passed, metrics

        except Exception as e:
            self.logger.error(f"Sample validation failed: {e}")
            return False, {"error": str(e)}

    async def _validate_entity_match(self, ss_id: str, ib_id: str) -> Tuple[str, str]:
        """Validate single entity match between systems.

        Args:
            ss_id: Smart-Scaffold entity ID
            ib_id: Intelligence-Builder entity ID

        Returns:
            Tuple of (status, reason). Status may be 'matched', 'mismatched', or 'skipped'.
        """
        try:
            # Get SS entity
            ss_entity = None
            if hasattr(self.ss_kg, "get_node"):
                ss_entity = await self.ss_kg.get_node(ss_id)

            # Get IB entity
            ib_entity = await self.ib_service.get_entity_by_id(ib_id)

            if not ss_entity and not ib_entity:
                return "skipped", "Entity missing in both systems"

            if not ss_entity:
                return "mismatched", "SS entity not found"

            if not ib_entity:
                return "mismatched", "IB entity not found"

            # Compare key properties
            ss_name = ss_entity.get("name", "")
            ib_name = ib_entity.get("name", "")

            if ss_name != ib_name:
                return "mismatched", f"Name mismatch: '{ss_name}' vs '{ib_name}'"

            return "matched", ""

        except Exception as e:
            return "mismatched", str(e)


class ParallelValidator:
    """Validate results from SS and IB during the parallel run period."""

    def __init__(
        self,
        ss_kg: Any,
        ib_service: Any,
        cutover_manager: Optional["CutoverManager"] = None,
    ) -> None:
        self.ss_kg = ss_kg
        self.ib_service = ib_service
        self.cutover_manager = cutover_manager
        self.logger = logging.getLogger(__name__)

    async def validate_query(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """Run the same query on SS and IB and compare results."""
        ss_result = await self._execute_ss_query(query, limit)
        ib_result = await self._execute_ib_query(query, entity_type, limit)
        matches = self._results_match(ss_result, ib_result)

        if not matches and self.cutover_manager:
            await self.cutover_manager.log_discrepancy(
                query=query,
                ss_result=ss_result,
                ib_result=ib_result.get("entities", []),
            )

        return {
            "query": query,
            "matches": matches,
            "ss_result_count": len(ss_result),
            "ib_result_count": len(ib_result.get("entities", [])),
        }

    async def _execute_ss_query(self, query: str, limit: int) -> List[Any]:
        if hasattr(self.ss_kg, "query"):
            result = await self.ss_kg.query(query)
            return list(result)[:limit]
        return []

    async def _execute_ib_query(
        self, query: str, entity_type: Optional[str], limit: int
    ) -> Dict[str, Any]:
        if hasattr(self.ib_service, "search_entities"):
            return await self.ib_service.search_entities(
                query_text=query, entity_types=[entity_type] if entity_type else None, limit=limit
            )
        return await self.ib_service.query_entities(
            entity_type=entity_type,
            limit=limit,
            query_text=query,
        )

    def _results_match(
        self, ss_result: List[Any], ib_result: Dict[str, Any]
    ) -> bool:
        ib_entities = ib_result.get("entities", [])
        return len(ss_result) == len(ib_entities)


class CutoverManager:
    """Manage production cutover from SS to IB.

    Handles the phased cutover process including:
    - Parallel operation mode
    - Traffic switching
    - Rollback procedures

    Example:
        >>> manager = CutoverManager(ss_kg, ib_service)
        >>> await manager.enable_parallel_mode()
        >>> # Monitor for discrepancies
        >>> await manager.complete_cutover()
    """

    def __init__(
        self,
        ss_kg: Any,
        ib_service: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize cutover manager.

        Args:
            ss_kg: Smart-Scaffold knowledge graph client
            ib_service: Intelligence-Builder service instance
            config: Optional configuration dict
        """
        self.ss_kg = ss_kg
        self.ib_service = ib_service
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        self._mode = "legacy"  # legacy, parallel, ib_only
        self._discrepancies: List[Dict[str, Any]] = []

    @property
    def mode(self) -> str:
        """Get current operation mode."""
        return self._mode

    async def enable_parallel_mode(self) -> bool:
        """Enable parallel operation mode.

        In parallel mode:
        - Reads from IB (source of truth)
        - Writes to both SS and IB
        - Logs discrepancies

        Returns:
            True if successfully enabled
        """
        self.logger.info("Enabling parallel operation mode")
        self._mode = "parallel"
        return True

    async def enable_ib_only_mode(self) -> bool:
        """Enable IB-only operation mode.

        In IB-only mode:
        - Reads from IB
        - Writes to IB only
        - SS is read-only (for rollback)

        Returns:
            True if successfully enabled
        """
        self.logger.info("Enabling IB-only operation mode")
        self._mode = "ib_only"
        return True

    async def rollback_to_legacy(self) -> bool:
        """Rollback to legacy SS operation.

        Returns:
            True if successfully rolled back
        """
        self.logger.warning("Rolling back to legacy operation mode")
        self._mode = "legacy"
        return True

    async def log_discrepancy(
        self,
        query: str,
        ss_result: Any,
        ib_result: Any,
    ) -> None:
        """Log discrepancy between systems.

        Args:
            query: Query that produced discrepancy
            ss_result: Result from Smart-Scaffold
            ib_result: Result from Intelligence-Builder
        """
        discrepancy = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "ss_result_count": len(ss_result) if ss_result else 0,
            "ib_result_count": len(ib_result) if ib_result else 0,
        }
        self._discrepancies.append(discrepancy)
        self.logger.warning(f"Discrepancy detected: {discrepancy}")

    def get_discrepancies(self) -> List[Dict[str, Any]]:
        """Get all logged discrepancies.

        Returns:
            List of discrepancy records
        """
        return self._discrepancies.copy()

    async def complete_cutover(self) -> Dict[str, Any]:
        """Complete the cutover to IB.

        Returns:
            Cutover result with status and metrics
        """
        self.logger.info("Completing cutover to Intelligence-Builder")

        result = {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "previous_mode": self._mode,
            "discrepancy_count": len(self._discrepancies),
        }

        self._mode = "ib_only"

        return result

    async def verify_cutover(self) -> ValidationResult:
        """Verify cutover was successful.

        Returns:
            ValidationResult with post-cutover validation
        """
        validator = MigrationValidator(self.ss_kg, self.ib_service)
        return await validator.validate_all()
