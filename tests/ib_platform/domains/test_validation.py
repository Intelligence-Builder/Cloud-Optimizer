"""Tests for domain validation utilities."""

import pytest

from ib_platform.domains.base import (
    BaseDomain,
    EntityTypeDefinition,
    RelationshipTypeDefinition,
)
from ib_platform.domains.security.domain import SecurityDomain
from ib_platform.domains.validation import (
    validate_domain_definition,
    validate_entity_data,
    validate_relationship_data,
)


class TestValidateDomainDefinition:
    """Tests for validate_domain_definition function."""

    def test_validate_valid_domain(self, security_domain: SecurityDomain) -> None:
        """Test validating a valid domain."""
        errors = validate_domain_definition(security_domain)
        assert len(errors) == 0

    def test_validate_domain_without_name(self) -> None:
        """Test that domain without name fails validation."""

        class InvalidDomain(BaseDomain):
            @property
            def name(self) -> str:
                return ""

            @property
            def display_name(self) -> str:
                return "Test"

            @property
            def version(self) -> str:
                return "1.0.0"

            @property
            def entity_types(self) -> list:
                return [
                    EntityTypeDefinition(
                        name="test", description="Test", required_properties=["name"]
                    )
                ]

            @property
            def relationship_types(self) -> list:
                return []

        domain = InvalidDomain()
        errors = validate_domain_definition(domain)
        assert len(errors) > 0
        assert any("name cannot be empty" in error for error in errors)

    def test_validate_domain_with_invalid_name_format(self) -> None:
        """Test that domain with spaces in name fails validation."""

        class InvalidDomain(BaseDomain):
            @property
            def name(self) -> str:
                return "Invalid Name"

            @property
            def display_name(self) -> str:
                return "Test"

            @property
            def version(self) -> str:
                return "1.0.0"

            @property
            def entity_types(self) -> list:
                return [
                    EntityTypeDefinition(
                        name="test", description="Test", required_properties=["name"]
                    )
                ]

            @property
            def relationship_types(self) -> list:
                return []

        domain = InvalidDomain()
        errors = validate_domain_definition(domain)
        assert any("lowercase with no spaces" in error for error in errors)

    def test_validate_domain_without_entity_types(self) -> None:
        """Test that domain without entity types fails validation."""

        class InvalidDomain(BaseDomain):
            @property
            def name(self) -> str:
                return "test"

            @property
            def display_name(self) -> str:
                return "Test"

            @property
            def version(self) -> str:
                return "1.0.0"

            @property
            def entity_types(self) -> list:
                return []

            @property
            def relationship_types(self) -> list:
                return []

        domain = InvalidDomain()
        errors = validate_domain_definition(domain)
        assert any("at least one entity type" in error for error in errors)


class TestValidateEntityData:
    """Tests for validate_entity_data function."""

    def test_validate_valid_entity_data(
        self, security_domain: SecurityDomain, sample_vulnerability_data: dict
    ) -> None:
        """Test validating valid entity data."""
        errors = validate_entity_data(
            security_domain, "vulnerability", sample_vulnerability_data
        )
        assert len(errors) == 0

    def test_validate_missing_required_property(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for missing required property."""
        errors = validate_entity_data(security_domain, "vulnerability", {})
        assert len(errors) > 0
        assert any("Missing required property" in error for error in errors)

    def test_validate_none_value_for_required_property(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test that None value for required property fails validation."""
        errors = validate_entity_data(security_domain, "vulnerability", {"name": None})
        assert len(errors) > 0
        assert any("cannot be None" in error for error in errors)

    def test_validate_unknown_entity_type(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for unknown entity type."""
        errors = validate_entity_data(security_domain, "unknown_type", {"name": "test"})
        assert len(errors) > 0
        assert any("not found" in error for error in errors)


class TestValidateRelationshipData:
    """Tests for validate_relationship_data function."""

    def test_validate_valid_relationship_data(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validating valid relationship data."""
        errors = validate_relationship_data(
            security_domain,
            "mitigates",
            "control",
            "vulnerability",
            {"effectiveness": 0.8},
        )
        assert len(errors) == 0

    def test_validate_invalid_source_type(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for invalid source type."""
        errors = validate_relationship_data(
            security_domain, "mitigates", "threat", "vulnerability", {}
        )
        assert len(errors) > 0
        assert any("Invalid source type" in error for error in errors)

    def test_validate_invalid_target_type(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for invalid target type."""
        errors = validate_relationship_data(
            security_domain, "mitigates", "control", "identity", {}
        )
        assert len(errors) > 0
        assert any("Invalid target type" in error for error in errors)

    def test_validate_unknown_relationship_type(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for unknown relationship type."""
        errors = validate_relationship_data(
            security_domain, "unknown_rel", "control", "vulnerability", {}
        )
        assert len(errors) > 0
        assert any("not found" in error for error in errors)
