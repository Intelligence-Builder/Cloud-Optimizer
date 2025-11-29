"""Base domain abstraction for Intelligence-Builder platform.

This module defines the core abstractions for domain modules, including
entity types, relationship types, and the base domain class that all
domain implementations must inherit from.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EntityTypeDefinition:
    """Defines an entity type within a domain.

    Entity types specify the structure and validation rules for entities
    that can be created within a domain.

    Attributes:
        name: Unique name for this entity type
        description: Human-readable description
        required_properties: List of property names that must be provided
        optional_properties: List of property names that may be provided
        parent_type: Optional parent entity type for inheritance
    """

    name: str
    description: str
    required_properties: List[str]
    optional_properties: List[str] = field(default_factory=list)
    parent_type: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate entity type definition."""
        if not self.name:
            raise ValueError("Entity type name cannot be empty")
        if not self.required_properties:
            logger.warning(
                f"Entity type '{self.name}' has no required properties",
                extra={"entity_type": self.name},
            )


@dataclass
class RelationshipTypeDefinition:
    """Defines a relationship type within a domain.

    Relationship types specify the valid connections between entities
    and the properties that can be associated with those connections.

    Attributes:
        name: Unique name for this relationship type
        description: Human-readable description
        valid_source_types: List of entity types that can be sources
        valid_target_types: List of entity types that can be targets
        properties: List of property names for the relationship
        cardinality: one_to_one, one_to_many, or many_to_many
        is_bidirectional: Whether relationship is bidirectional
    """

    name: str
    description: str
    valid_source_types: List[str]
    valid_target_types: List[str]
    properties: List[str] = field(default_factory=list)
    cardinality: str = "many_to_many"
    is_bidirectional: bool = False

    def __post_init__(self) -> None:
        """Validate relationship type definition."""
        if not self.name:
            raise ValueError("Relationship type name cannot be empty")
        if not self.valid_source_types:
            raise ValueError(
                f"Relationship '{self.name}' must specify valid_source_types"
            )
        if not self.valid_target_types:
            raise ValueError(
                f"Relationship '{self.name}' must specify valid_target_types"
            )
        if self.cardinality not in ("one_to_one", "one_to_many", "many_to_many"):
            raise ValueError(
                f"Invalid cardinality '{self.cardinality}' for relationship "
                f"'{self.name}'. Must be one_to_one, one_to_many, or many_to_many"
            )


class BaseDomain(ABC):
    """Abstract base class for all platform domains.

    Domains define:
    - Entity types and their validation rules
    - Relationship types and their constraints
    - Patterns for entity/relationship detection (optional)
    - Confidence factors for scoring (optional)
    - Custom operations specific to the domain (optional)

    All domain implementations must inherit from this class and implement
    the required abstract properties.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique domain identifier (lowercase, no spaces)."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable domain name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Domain schema version (semantic versioning)."""
        ...

    @property
    @abstractmethod
    def entity_types(self) -> List[EntityTypeDefinition]:
        """Entity types defined in this domain."""
        ...

    @property
    @abstractmethod
    def relationship_types(self) -> List[RelationshipTypeDefinition]:
        """Relationship types defined in this domain."""
        ...

    @property
    def patterns(self) -> List[Any]:
        """Patterns for entity/relationship detection.

        Override this to provide domain-specific pattern definitions.
        Default implementation returns empty list.
        """
        return []

    @property
    def confidence_factors(self) -> List[Any]:
        """Domain-specific confidence factors for scoring.

        Override this to provide custom confidence scoring logic.
        Default implementation returns empty list.
        """
        return []

    @property
    def depends_on(self) -> List[str]:
        """Other domains this domain depends on.

        Returns list of domain names that must be registered before
        this domain can be registered.
        """
        return []

    # --- Lifecycle Hooks ---

    async def on_entity_create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Called before entity creation.

        Override this to modify entity data or perform validation
        before the entity is created in the system.

        Args:
            entity: Entity data dictionary

        Returns:
            Modified entity data dictionary
        """
        return entity

    async def on_relationship_create(
        self, relationship: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Called before relationship creation.

        Override this to modify relationship data or perform validation
        before the relationship is created in the system.

        Args:
            relationship: Relationship data dictionary

        Returns:
            Modified relationship data dictionary
        """
        return relationship

    # --- Validation ---

    def validate_entity(
        self, entity_type: str, properties: Dict[str, Any]
    ) -> List[str]:
        """Validate entity data against domain schema.

        Args:
            entity_type: Type of entity to validate
            properties: Entity properties to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        entity_def = self._get_entity_type(entity_type)
        if not entity_def:
            errors.append(f"Unknown entity type: {entity_type}")
            return errors

        # Check required properties
        for prop in entity_def.required_properties:
            if prop not in properties:
                errors.append(
                    f"Missing required property '{prop}' for entity type '{entity_type}'"
                )

        return errors

    def validate_relationship(
        self, rel_type: str, source_type: str, target_type: str
    ) -> List[str]:
        """Validate relationship type against domain schema.

        Args:
            rel_type: Type of relationship
            source_type: Entity type of source node
            target_type: Entity type of target node

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        rel_def = self._get_relationship_type(rel_type)
        if not rel_def:
            errors.append(f"Unknown relationship type: {rel_type}")
            return errors

        # Check valid source types
        if source_type not in rel_def.valid_source_types:
            errors.append(
                f"Invalid source type '{source_type}' for relationship '{rel_type}'. "
                f"Valid types: {', '.join(rel_def.valid_source_types)}"
            )

        # Check valid target types
        if target_type not in rel_def.valid_target_types:
            errors.append(
                f"Invalid target type '{target_type}' for relationship '{rel_type}'. "
                f"Valid types: {', '.join(rel_def.valid_target_types)}"
            )

        return errors

    # --- Custom Operations ---

    async def execute_operation(self, operation: str, params: Dict[str, Any]) -> Any:
        """Execute a domain-specific operation.

        Override this to implement custom domain operations.

        Args:
            operation: Operation name
            params: Operation parameters

        Returns:
            Operation result

        Raises:
            NotImplementedError: If operation is not implemented
        """
        raise NotImplementedError(
            f"Operation '{operation}' not implemented in domain '{self.name}'"
        )

    def get_supported_operations(self) -> List[str]:
        """List of supported custom operations.

        Override this to list available custom operations.

        Returns:
            List of operation names
        """
        return []

    # --- Helper Methods ---

    def _get_entity_type(self, name: str) -> Optional[EntityTypeDefinition]:
        """Get entity type definition by name.

        Args:
            name: Entity type name

        Returns:
            EntityTypeDefinition if found, None otherwise
        """
        for entity_type in self.entity_types:
            if entity_type.name == name:
                return entity_type
        return None

    def _get_relationship_type(self, name: str) -> Optional[RelationshipTypeDefinition]:
        """Get relationship type definition by name.

        Args:
            name: Relationship type name

        Returns:
            RelationshipTypeDefinition if found, None otherwise
        """
        for rel_type in self.relationship_types:
            if rel_type.name == name:
                return rel_type
        return None
