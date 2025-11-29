"""Tests for base domain classes and definitions."""

from ib_platform.domains.base import (
    BaseDomain,
    EntityTypeDefinition,
    RelationshipTypeDefinition,
)

import pytest


class TestEntityTypeDefinition:
    """Tests for EntityTypeDefinition."""

    def test_create_entity_type(self) -> None:
        """Test creating an entity type definition."""
        entity_type = EntityTypeDefinition(
            name="test_entity",
            description="Test entity type",
            required_properties=["name", "type"],
            optional_properties=["description"],
        )

        assert entity_type.name == "test_entity"
        assert entity_type.description == "Test entity type"
        assert "name" in entity_type.required_properties
        assert "description" in entity_type.optional_properties

    def test_entity_type_with_parent(self) -> None:
        """Test entity type with parent type."""
        entity_type = EntityTypeDefinition(
            name="child_entity",
            description="Child entity type",
            required_properties=["name"],
            parent_type="parent_entity",
        )

        assert entity_type.parent_type == "parent_entity"

    def test_entity_type_requires_name(self) -> None:
        """Test that entity type requires a name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            EntityTypeDefinition(
                name="",
                description="Test",
                required_properties=["name"],
            )


class TestRelationshipTypeDefinition:
    """Tests for RelationshipTypeDefinition."""

    def test_create_relationship_type(self) -> None:
        """Test creating a relationship type definition."""
        rel_type = RelationshipTypeDefinition(
            name="connects_to",
            description="Connection relationship",
            valid_source_types=["node_a"],
            valid_target_types=["node_b"],
            properties=["strength"],
        )

        assert rel_type.name == "connects_to"
        assert "node_a" in rel_type.valid_source_types
        assert "node_b" in rel_type.valid_target_types
        assert "strength" in rel_type.properties

    def test_relationship_cardinality(self) -> None:
        """Test relationship cardinality options."""
        rel_type = RelationshipTypeDefinition(
            name="one_to_many",
            description="One to many relationship",
            valid_source_types=["parent"],
            valid_target_types=["child"],
            cardinality="one_to_many",
        )

        assert rel_type.cardinality == "one_to_many"

    def test_invalid_cardinality(self) -> None:
        """Test that invalid cardinality raises error."""
        with pytest.raises(ValueError, match="Invalid cardinality"):
            RelationshipTypeDefinition(
                name="test",
                description="Test",
                valid_source_types=["a"],
                valid_target_types=["b"],
                cardinality="invalid",
            )

    def test_bidirectional_relationship(self) -> None:
        """Test bidirectional relationship."""
        rel_type = RelationshipTypeDefinition(
            name="peers_with",
            description="Peer relationship",
            valid_source_types=["node"],
            valid_target_types=["node"],
            is_bidirectional=True,
        )

        assert rel_type.is_bidirectional is True


class TestBaseDomain:
    """Tests for BaseDomain abstract class."""

    def test_cannot_instantiate_abstract_domain(self) -> None:
        """Test that BaseDomain cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseDomain()  # type: ignore

    def test_concrete_domain_implementation(self) -> None:
        """Test concrete domain implementation."""

        class TestDomain(BaseDomain):
            @property
            def name(self) -> str:
                return "test"

            @property
            def display_name(self) -> str:
                return "Test Domain"

            @property
            def version(self) -> str:
                return "1.0.0"

            @property
            def entity_types(self) -> list:
                return [
                    EntityTypeDefinition(
                        name="test_entity",
                        description="Test",
                        required_properties=["name"],
                    )
                ]

            @property
            def relationship_types(self) -> list:
                return [
                    RelationshipTypeDefinition(
                        name="test_rel",
                        description="Test",
                        valid_source_types=["test_entity"],
                        valid_target_types=["test_entity"],
                    )
                ]

        domain = TestDomain()
        assert domain.name == "test"
        assert domain.display_name == "Test Domain"
        assert len(domain.entity_types) == 1
        assert len(domain.relationship_types) == 1

    def test_domain_validation_entity(self) -> None:
        """Test entity validation."""

        class TestDomain(BaseDomain):
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
                return [
                    EntityTypeDefinition(
                        name="user",
                        description="User entity",
                        required_properties=["name", "email"],
                    )
                ]

            @property
            def relationship_types(self) -> list:
                return []

        domain = TestDomain()

        # Valid entity
        errors = domain.validate_entity(
            "user", {"name": "John", "email": "john@example.com"}
        )
        assert len(errors) == 0

        # Missing required property
        errors = domain.validate_entity("user", {"name": "John"})
        assert len(errors) == 1
        assert "email" in errors[0]

        # Unknown entity type
        errors = domain.validate_entity("unknown", {"name": "Test"})
        assert len(errors) == 1
        assert "Unknown entity type" in errors[0]

    def test_domain_validation_relationship(self) -> None:
        """Test relationship validation."""

        class TestDomain(BaseDomain):
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
                return [
                    EntityTypeDefinition(
                        name="user",
                        description="User",
                        required_properties=["name"],
                    ),
                    EntityTypeDefinition(
                        name="group",
                        description="Group",
                        required_properties=["name"],
                    ),
                ]

            @property
            def relationship_types(self) -> list:
                return [
                    RelationshipTypeDefinition(
                        name="member_of",
                        description="User is member of group",
                        valid_source_types=["user"],
                        valid_target_types=["group"],
                    )
                ]

        domain = TestDomain()

        # Valid relationship
        errors = domain.validate_relationship("member_of", "user", "group")
        assert len(errors) == 0

        # Invalid source type (keep target valid)
        errors = domain.validate_relationship("member_of", "group", "group")
        assert len(errors) == 1
        assert "Invalid source type" in errors[0]

        # Invalid target type (keep source valid)
        errors = domain.validate_relationship("member_of", "user", "user")
        assert len(errors) == 1
        assert "Invalid target type" in errors[0]
