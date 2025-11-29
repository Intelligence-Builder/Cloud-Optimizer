"""Domain registry for managing registered domains.

This module provides a thread-safe registry for managing domain registrations,
including dependency validation and lifecycle management.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .base import BaseDomain, EntityTypeDefinition, RelationshipTypeDefinition

logger = logging.getLogger(__name__)


class DomainRegistry:
    """Central registry for all domains in the platform.

    This registry manages domain registrations, validates dependencies,
    and provides thread-safe access to domain definitions.

    All operations that modify the registry are protected by an asyncio.Lock
    to ensure thread safety in concurrent environments.
    """

    def __init__(self) -> None:
        """Initialize the domain registry."""
        self._domains: Dict[str, BaseDomain] = {}
        self._lock = asyncio.Lock()
        logger.info("Domain registry initialized")

    async def register(self, domain: BaseDomain) -> None:
        """Register a domain with dependency validation.

        Args:
            domain: Domain instance to register

        Raises:
            ValueError: If domain dependencies are not met or domain
                       is already registered
        """
        async with self._lock:
            # Check if already registered
            if domain.name in self._domains:
                raise ValueError(f"Domain '{domain.name}' is already registered")

            # Validate dependencies
            for dep in domain.depends_on:
                if dep not in self._domains:
                    raise ValueError(
                        f"Domain '{domain.name}' depends on '{dep}' "
                        f"which is not registered"
                    )

            # Register the domain
            self._domains[domain.name] = domain
            logger.info(
                f"Registered domain '{domain.name}' (version {domain.version})",
                extra={
                    "domain": domain.name,
                    "version": domain.version,
                    "entity_types": len(domain.entity_types),
                    "relationship_types": len(domain.relationship_types),
                },
            )

    async def unregister(self, domain_name: str) -> None:
        """Unregister a domain after checking for dependents.

        Args:
            domain_name: Name of domain to unregister

        Raises:
            ValueError: If other domains depend on this domain or
                       domain is not registered
        """
        async with self._lock:
            # Check if domain exists
            if domain_name not in self._domains:
                raise ValueError(f"Domain '{domain_name}' is not registered")

            # Check for dependent domains
            dependents = []
            for name, domain in self._domains.items():
                if domain_name in domain.depends_on:
                    dependents.append(name)

            if dependents:
                raise ValueError(
                    f"Cannot unregister '{domain_name}': domains depend on it: "
                    f"{', '.join(dependents)}"
                )

            # Unregister the domain
            del self._domains[domain_name]
            logger.info(
                f"Unregistered domain '{domain_name}'",
                extra={"domain": domain_name},
            )

    def get(self, name: str) -> Optional[BaseDomain]:
        """Get a domain by name.

        This is a read-only operation and does not require locking.

        Args:
            name: Domain name

        Returns:
            Domain instance if found, None otherwise
        """
        return self._domains.get(name)

    def list_domains(self) -> List[str]:
        """List all registered domain names.

        Returns:
            List of domain names
        """
        return list(self._domains.keys())

    def get_all_entity_types(self) -> Dict[str, List[EntityTypeDefinition]]:
        """Get all entity types from all domains.

        Returns:
            Dictionary mapping domain names to their entity type definitions
        """
        return {name: domain.entity_types for name, domain in self._domains.items()}

    def get_all_relationship_types(self) -> Dict[str, List[RelationshipTypeDefinition]]:
        """Get all relationship types from all domains.

        Returns:
            Dictionary mapping domain names to their relationship type definitions
        """
        return {
            name: domain.relationship_types for name, domain in self._domains.items()
        }

    def get_all_patterns(self, domains: Optional[List[str]] = None) -> List[Any]:
        """Get all patterns from specified domains.

        Args:
            domains: Optional list of domain names to get patterns from.
                    If None, gets patterns from all domains.

        Returns:
            List of pattern definitions from specified domains
        """
        patterns = []

        target_domains = domains or list(self._domains.keys())

        for name in target_domains:
            domain = self._domains.get(name)
            if domain:
                patterns.extend(domain.patterns)

        return patterns

    def validate_entity(
        self, domain_name: str, entity_type: str, properties: Dict[str, Any]
    ) -> List[str]:
        """Validate entity data against domain schema.

        Args:
            domain_name: Name of domain to validate against
            entity_type: Type of entity
            properties: Entity properties

        Returns:
            List of validation error messages (empty if valid)
        """
        domain = self.get(domain_name)
        if not domain:
            return [f"Domain '{domain_name}' not found"]

        return domain.validate_entity(entity_type, properties)

    def validate_relationship(
        self, domain_name: str, rel_type: str, source_type: str, target_type: str
    ) -> List[str]:
        """Validate relationship against domain schema.

        Args:
            domain_name: Name of domain to validate against
            rel_type: Type of relationship
            source_type: Entity type of source node
            target_type: Entity type of target node

        Returns:
            List of validation error messages (empty if valid)
        """
        domain = self.get(domain_name)
        if not domain:
            return [f"Domain '{domain_name}' not found"]

        return domain.validate_relationship(rel_type, source_type, target_type)

    def get_domain_info(self, domain_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a domain.

        Args:
            domain_name: Name of domain

        Returns:
            Dictionary with domain info or None if not found
        """
        domain = self.get(domain_name)
        if not domain:
            return None

        return {
            "name": domain.name,
            "display_name": domain.display_name,
            "version": domain.version,
            "entity_types": [
                {
                    "name": et.name,
                    "description": et.description,
                    "required_properties": et.required_properties,
                    "optional_properties": et.optional_properties,
                }
                for et in domain.entity_types
            ],
            "relationship_types": [
                {
                    "name": rt.name,
                    "description": rt.description,
                    "valid_source_types": rt.valid_source_types,
                    "valid_target_types": rt.valid_target_types,
                    "cardinality": rt.cardinality,
                    "is_bidirectional": rt.is_bidirectional,
                }
                for rt in domain.relationship_types
            ],
            "depends_on": domain.depends_on,
            "patterns_count": len(domain.patterns),
            "confidence_factors_count": len(domain.confidence_factors),
            "supported_operations": domain.get_supported_operations(),
        }
