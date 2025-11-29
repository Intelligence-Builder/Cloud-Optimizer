"""Pattern Registry - Central Management of Patterns.

Provides thread-safe registration and retrieval of pattern definitions
with filtering by domain, category, and other attributes.
"""

import logging
from threading import RLock
from typing import Dict, List, Optional
from uuid import UUID

from .models import PatternCategory, PatternDefinition

logger = logging.getLogger(__name__)


class PatternRegistry:
    """Central registry for pattern definitions.

    Provides thread-safe storage and retrieval of pattern definitions.
    Patterns can be filtered by domain, category, priority, and other attributes.

    Example:
        >>> registry = PatternRegistry()
        >>> registry.register(pattern_def)
        >>> patterns = registry.get_by_domain("security")
    """

    def __init__(self) -> None:
        """Initialize empty pattern registry."""
        self._patterns: Dict[UUID, PatternDefinition] = {}
        self._lock = RLock()
        logger.info("Pattern registry initialized")

    def register(self, pattern: PatternDefinition) -> None:
        """Register a pattern definition.

        Args:
            pattern: Pattern definition to register

        Raises:
            ValueError: If pattern with same ID already exists
        """
        with self._lock:
            if pattern.id in self._patterns:
                raise ValueError(f"Pattern with ID {pattern.id} is already registered")

            self._patterns[pattern.id] = pattern
            logger.info(
                "Pattern registered",
                extra={
                    "pattern_id": str(pattern.id),
                    "pattern_name": pattern.name,
                    "domain": pattern.domain,
                    "category": pattern.category.value,
                },
            )

    def unregister(self, pattern_id: UUID) -> None:
        """Unregister a pattern definition.

        Args:
            pattern_id: ID of pattern to unregister

        Raises:
            KeyError: If pattern not found
        """
        with self._lock:
            if pattern_id not in self._patterns:
                raise KeyError(f"Pattern with ID {pattern_id} not found")

            pattern = self._patterns.pop(pattern_id)
            logger.info(
                "Pattern unregistered",
                extra={
                    "pattern_id": str(pattern_id),
                    "pattern_name": pattern.name,
                },
            )

    def get(self, pattern_id: UUID) -> Optional[PatternDefinition]:
        """Get a pattern by ID.

        Args:
            pattern_id: Pattern ID to retrieve

        Returns:
            Pattern definition if found, None otherwise
        """
        with self._lock:
            return self._patterns.get(pattern_id)

    def get_by_domain(
        self, domain: str, category: Optional[PatternCategory] = None
    ) -> List[PatternDefinition]:
        """Get all patterns for a specific domain.

        Args:
            domain: Domain name to filter by
            category: Optional category filter

        Returns:
            List of matching pattern definitions
        """
        with self._lock:
            patterns = [p for p in self._patterns.values() if p.domain == domain]

            if category is not None:
                patterns = [p for p in patterns if p.category == category]

            logger.debug(
                "Retrieved patterns by domain",
                extra={
                    "domain": domain,
                    "category": category.value if category else None,
                    "count": len(patterns),
                },
            )

            return patterns

    def get_by_category(self, category: PatternCategory) -> List[PatternDefinition]:
        """Get all patterns for a specific category.

        Args:
            category: Category to filter by

        Returns:
            List of matching pattern definitions
        """
        with self._lock:
            patterns = [p for p in self._patterns.values() if p.category == category]

            logger.debug(
                "Retrieved patterns by category",
                extra={"category": category.value, "count": len(patterns)},
            )

            return patterns

    def list_all(self) -> List[PatternDefinition]:
        """Get all registered patterns.

        Returns:
            List of all pattern definitions
        """
        with self._lock:
            return list(self._patterns.values())

    def count(self) -> int:
        """Get total number of registered patterns.

        Returns:
            Number of registered patterns
        """
        with self._lock:
            return len(self._patterns)

    def clear(self) -> None:
        """Remove all registered patterns.

        Warning:
            This cannot be undone. Use with caution.
        """
        with self._lock:
            count = len(self._patterns)
            self._patterns.clear()
            logger.warning(f"Pattern registry cleared ({count} patterns removed)")
