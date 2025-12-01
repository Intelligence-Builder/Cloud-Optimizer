"""Hybrid adapter used during dual-write migration phases."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from cloud_optimizer.integrations.smart_scaffold.runtime import IBServiceProtocol

logger = logging.getLogger(__name__)


class HybridKnowledgeGraph:
    """Routes read operations to IB while mirroring writes to both systems."""

    def __init__(
        self,
        ss_kg: Any,
        ib_service: IBServiceProtocol,
        dual_write: bool = True,
    ) -> None:
        """
        Initialize hybrid adapter.

        Args:
            ss_kg: Smart-Scaffold knowledge graph client
            ib_service: Intelligence-Builder service (implements protocol)
            dual_write: Whether to write to both systems
        """
        self.ss_kg = ss_kg
        self.ib_service = ib_service
        self.dual_write = dual_write

    async def query(
        self,
        query_text: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Execute queries against the IB service."""
        if hasattr(self.ib_service, "search_entities"):
            return await self.ib_service.search_entities(
                query_text=query_text,
                entity_types=entity_types,
                limit=limit,
            )
        return await self.ib_service.query_entities(
            entity_type=entity_types[0] if entity_types else None,
            limit=limit,
            query_text=query_text,
        )

    async def create_entity(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create entity in IB (and optionally mirror to SS)."""
        ib_entity = await self.ib_service.create_entity(entity_data)
        if self.dual_write and hasattr(self.ss_kg, "create_entity"):
            try:
                await self.ss_kg.create_entity(entity_data)
            except Exception as exc:  # pragma: no cover - best effort
                logger.warning("Failed to mirror entity to SS: %s", exc)
        return ib_entity

    async def create_relationship(self, rel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create relationship in IB (and optionally mirror to SS)."""
        relationship = await self.ib_service.create_relationship(rel_data)
        if self.dual_write and hasattr(self.ss_kg, "create_relationship"):
            try:
                await self.ss_kg.create_relationship(rel_data)
            except Exception as exc:  # pragma: no cover - best effort
                logger.warning("Failed to mirror relationship to SS: %s", exc)
        return relationship

    async def dual_write_enabled(self) -> bool:
        """Expose whether dual-write mode is active."""
        return self.dual_write
