"""Validation utilities for domain definitions and data.

This module provides utility functions for validating domain definitions,
entity data, and relationship data against domain schemas.
"""

import logging
from typing import Any, Dict, List

from .base import BaseDomain, EntityTypeDefinition, RelationshipTypeDefinition

logger = logging.getLogger(__name__)


def validate_domain_definition(domain: BaseDomain) -> List[str]:
    """Validate a domain definition for completeness and correctness.

    Checks that the domain has valid name, version, entity types,
    and relationship types. Also validates cross-references between
    entity types and relationship type constraints.

    Args:
        domain: Domain instance to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check basic properties
    if not domain.name:
        errors.append("Domain name cannot be empty")
    elif not domain.name.islower() or " " in domain.name:
        errors.append(f"Domain name '{domain.name}' must be lowercase with no spaces")

    if not domain.display_name:
        errors.append("Domain display_name cannot be empty")

    if not domain.version:
        errors.append("Domain version cannot be empty")

    # Check entity types
    if not domain.entity_types:
        errors.append("Domain must define at least one entity type")
    else:
        entity_type_names = {et.name for et in domain.entity_types}

        # Check for duplicate entity type names
        if len(entity_type_names) != len(domain.entity_types):
            errors.append("Domain has duplicate entity type names")

        # Validate each entity type
        for entity_type in domain.entity_types:
            entity_errors = _validate_entity_type(entity_type)
            errors.extend(entity_errors)

    # Check relationship types
    if domain.relationship_types:
        rel_type_names = {rt.name for rt in domain.relationship_types}

        # Check for duplicate relationship type names
        if len(rel_type_names) != len(domain.relationship_types):
            errors.append("Domain has duplicate relationship type names")

        # Validate each relationship type
        for rel_type in domain.relationship_types:
            rel_errors = _validate_relationship_type(rel_type, entity_type_names)
            errors.extend(rel_errors)

    if errors:
        logger.warning(
            f"Domain '{domain.name}' has {len(errors)} validation errors",
            extra={"domain": domain.name, "error_count": len(errors)},
        )
    else:
        logger.info(
            f"Domain '{domain.name}' passed validation",
            extra={"domain": domain.name},
        )

    return errors


def validate_entity_data(
    domain: BaseDomain, entity_type: str, data: Dict[str, Any]
) -> List[str]:
    """Validate entity data against domain schema.

    Args:
        domain: Domain to validate against
        entity_type: Type of entity
        data: Entity data to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Find entity type definition
    entity_def = None
    for et in domain.entity_types:
        if et.name == entity_type:
            entity_def = et
            break

    if not entity_def:
        errors.append(
            f"Entity type '{entity_type}' not found in domain '{domain.name}'"
        )
        return errors

    # Check required properties
    for prop in entity_def.required_properties:
        if prop not in data:
            errors.append(f"Missing required property: {prop}")
        elif data[prop] is None:
            errors.append(f"Required property '{prop}' cannot be None")

    # Check for unexpected properties
    all_valid_properties = set(entity_def.required_properties) | set(
        entity_def.optional_properties
    )
    for prop in data.keys():
        if prop not in all_valid_properties:
            logger.debug(
                f"Unexpected property '{prop}' in entity type '{entity_type}'",
                extra={
                    "domain": domain.name,
                    "entity_type": entity_type,
                    "property": prop,
                },
            )

    return errors


def validate_relationship_data(
    domain: BaseDomain,
    relationship_type: str,
    source_type: str,
    target_type: str,
    data: Dict[str, Any],
) -> List[str]:
    """Validate relationship data against domain schema.

    Args:
        domain: Domain to validate against
        relationship_type: Type of relationship
        source_type: Entity type of source node
        target_type: Entity type of target node
        data: Relationship data to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Find relationship type definition
    rel_def = None
    for rt in domain.relationship_types:
        if rt.name == relationship_type:
            rel_def = rt
            break

    if not rel_def:
        errors.append(
            f"Relationship type '{relationship_type}' not found in "
            f"domain '{domain.name}'"
        )
        return errors

    # Validate source type
    if source_type not in rel_def.valid_source_types:
        errors.append(
            f"Invalid source type '{source_type}' for relationship "
            f"'{relationship_type}'. Valid types: "
            f"{', '.join(rel_def.valid_source_types)}"
        )

    # Validate target type
    if target_type not in rel_def.valid_target_types:
        errors.append(
            f"Invalid target type '{target_type}' for relationship "
            f"'{relationship_type}'. Valid types: "
            f"{', '.join(rel_def.valid_target_types)}"
        )

    # Check for unexpected properties
    if rel_def.properties and data:
        for prop in data.keys():
            if prop not in rel_def.properties:
                logger.debug(
                    f"Unexpected property '{prop}' in relationship "
                    f"type '{relationship_type}'",
                    extra={
                        "domain": domain.name,
                        "relationship_type": relationship_type,
                        "property": prop,
                    },
                )

    return errors


# --- Helper Functions ---


def _validate_entity_type(entity_type: EntityTypeDefinition) -> List[str]:
    """Validate a single entity type definition.

    Args:
        entity_type: Entity type to validate

    Returns:
        List of validation error messages
    """
    errors = []

    if not entity_type.name:
        errors.append("Entity type name cannot be empty")

    if not entity_type.description:
        errors.append(f"Entity type '{entity_type.name}' must have a description")

    # Check for duplicate properties between required and optional
    required_set = set(entity_type.required_properties)
    optional_set = set(entity_type.optional_properties)
    duplicates = required_set & optional_set

    if duplicates:
        errors.append(
            f"Entity type '{entity_type.name}' has properties in both "
            f"required and optional: {', '.join(duplicates)}"
        )

    return errors


def _validate_relationship_type(
    rel_type: RelationshipTypeDefinition, valid_entity_types: set
) -> List[str]:
    """Validate a single relationship type definition.

    Args:
        rel_type: Relationship type to validate
        valid_entity_types: Set of valid entity type names in the domain

    Returns:
        List of validation error messages
    """
    errors = []

    if not rel_type.name:
        errors.append("Relationship type name cannot be empty")

    if not rel_type.description:
        errors.append(f"Relationship type '{rel_type.name}' must have a description")

    if not rel_type.valid_source_types:
        errors.append(
            f"Relationship type '{rel_type.name}' must specify valid_source_types"
        )

    if not rel_type.valid_target_types:
        errors.append(
            f"Relationship type '{rel_type.name}' must specify valid_target_types"
        )

    # Check that referenced entity types exist
    for source_type in rel_type.valid_source_types:
        if source_type not in valid_entity_types:
            errors.append(
                f"Relationship type '{rel_type.name}' references unknown "
                f"source entity type '{source_type}'"
            )

    for target_type in rel_type.valid_target_types:
        if target_type not in valid_entity_types:
            errors.append(
                f"Relationship type '{rel_type.name}' references unknown "
                f"target entity type '{target_type}'"
            )

    return errors
