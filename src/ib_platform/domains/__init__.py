"""Domain Module System for Intelligence-Builder Platform.

This module provides the core domain abstraction layer that enables
applications to define and manage domain-specific entity types,
relationship types, patterns, and operations.
"""

from .base import BaseDomain, EntityTypeDefinition, RelationshipTypeDefinition
from .loader import DomainLoader
from .registry import DomainRegistry
from .validation import validate_domain_definition, validate_entity_data

__all__ = [
    "BaseDomain",
    "EntityTypeDefinition",
    "RelationshipTypeDefinition",
    "DomainRegistry",
    "DomainLoader",
    "validate_domain_definition",
    "validate_entity_data",
]
