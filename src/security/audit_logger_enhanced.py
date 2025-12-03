"""Simplified enhanced audit logger used by compliance-focused services.

The production repository ships a much richer implementation that streams
events to the CloudGuardian audit pipeline.  For the purposes of the rebuilt
Cloud Optimizer workspace we only need a lightweight async logger that exposes
the same interface so services such as ``AWSMarketplaceUsageTracker`` and the
SNS enterprise monitors can run their integration tests without failing on
missing dependencies.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.config.logging_config import get_logger

logger = get_logger(__name__)


class EnhancedAuditLogger:
    """Minimal async audit logger used for compliance/test scaffolding."""

    def __init__(self) -> None:
        # Keep a lock so that concurrent audit writes do not interleave logs.
        self._lock = asyncio.Lock()

    async def log_event(
        self,
        *,
        event_type: Any,
        user_id: Optional[str],
        tenant_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist a generic audit event."""
        await self._emit(
            category="audit_event",
            payload={
                "event_type": getattr(event_type, "name", event_type),
                "user_id": user_id,
                "tenant_id": tenant_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "outcome": outcome,
                "metadata": metadata or {},
            },
        )

    async def log_security_event(
        self,
        *,
        event_type: str,
        user_id: Optional[str],
        risk_level: str,
        details: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> None:
        """Record a security-specific event such as SLA/compliance alerts."""
        await self._emit(
            category="security_event",
            payload={
                "event_type": event_type,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "risk_level": risk_level,
                "details": details,
            },
        )

    async def log_compliance_event(
        self,
        *,
        framework: str,
        tenant_id: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Convenience helper used by higher level services."""
        await self._emit(
            category="compliance_event",
            payload={
                "framework": framework,
                "tenant_id": tenant_id,
                "status": status,
                "details": details or {},
            },
        )

    async def _emit(self, *, category: str, payload: Dict[str, Any]) -> None:
        """Serialize and log an audit payload in a thread-safe manner."""
        event = {
            "id": str(uuid.uuid4()),
            "category": category,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        async with self._lock:
            logger.info("Enhanced audit event", extra={"audit_event": event})
