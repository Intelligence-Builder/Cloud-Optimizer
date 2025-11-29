"""Tests for domain registry."""

import asyncio
from platform.domains.base import (
    BaseDomain,
    EntityTypeDefinition,
    RelationshipTypeDefinition,
)
from platform.domains.registry import DomainRegistry

import pytest


class SimpleDomain(BaseDomain):
    """Simple test domain."""

    @property
    def name(self) -> str:
        return "simple"

    @property
    def display_name(self) -> str:
        return "Simple Domain"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def entity_types(self) -> list:
        return [
            EntityTypeDefinition(
                name="entity",
                description="Test entity",
                required_properties=["name"],
            )
        ]

    @property
    def relationship_types(self) -> list:
        return [
            RelationshipTypeDefinition(
                name="relates_to",
                description="Test relationship",
                valid_source_types=["entity"],
                valid_target_types=["entity"],
            )
        ]


class DependentDomain(BaseDomain):
    """Domain with dependency."""

    @property
    def name(self) -> str:
        return "dependent"

    @property
    def display_name(self) -> str:
        return "Dependent Domain"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def depends_on(self) -> list:
        return ["simple"]

    @property
    def entity_types(self) -> list:
        return [
            EntityTypeDefinition(
                name="dependent_entity",
                description="Test",
                required_properties=["name"],
            )
        ]

    @property
    def relationship_types(self) -> list:
        return []


class TestDomainRegistry:
    """Tests for DomainRegistry."""

    @pytest.mark.asyncio
    async def test_register_domain(self) -> None:
        """Test registering a domain."""
        registry = DomainRegistry()
        domain = SimpleDomain()

        await registry.register(domain)

        assert "simple" in registry.list_domains()
        assert registry.get("simple") is domain

    @pytest.mark.asyncio
    async def test_register_duplicate_domain(self) -> None:
        """Test that registering duplicate domain raises error."""
        registry = DomainRegistry()
        domain = SimpleDomain()

        await registry.register(domain)

        with pytest.raises(ValueError, match="already registered"):
            await registry.register(domain)

    @pytest.mark.asyncio
    async def test_register_with_dependencies(self) -> None:
        """Test registering domain with dependencies."""
        registry = DomainRegistry()
        simple = SimpleDomain()
        dependent = DependentDomain()

        # Register dependency first
        await registry.register(simple)
        await registry.register(dependent)

        assert "dependent" in registry.list_domains()

    @pytest.mark.asyncio
    async def test_register_missing_dependency(self) -> None:
        """Test that missing dependency raises error."""
        registry = DomainRegistry()
        dependent = DependentDomain()

        with pytest.raises(ValueError, match="not registered"):
            await registry.register(dependent)

    @pytest.mark.asyncio
    async def test_unregister_domain(self) -> None:
        """Test unregistering a domain."""
        registry = DomainRegistry()
        domain = SimpleDomain()

        await registry.register(domain)
        await registry.unregister("simple")

        assert "simple" not in registry.list_domains()
        assert registry.get("simple") is None

    @pytest.mark.asyncio
    async def test_unregister_with_dependents(self) -> None:
        """Test that unregistering with dependents raises error."""
        registry = DomainRegistry()
        simple = SimpleDomain()
        dependent = DependentDomain()

        await registry.register(simple)
        await registry.register(dependent)

        with pytest.raises(ValueError, match="depend on it"):
            await registry.unregister("simple")

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_domain(self) -> None:
        """Test unregistering nonexistent domain raises error."""
        registry = DomainRegistry()

        with pytest.raises(ValueError, match="not registered"):
            await registry.unregister("nonexistent")

    def test_get_domain(self) -> None:
        """Test getting domain by name."""
        registry = DomainRegistry()
        assert registry.get("nonexistent") is None

    def test_list_domains(self) -> None:
        """Test listing all domains."""
        registry = DomainRegistry()
        assert registry.list_domains() == []

    @pytest.mark.asyncio
    async def test_get_all_entity_types(self) -> None:
        """Test getting all entity types."""
        registry = DomainRegistry()
        domain = SimpleDomain()

        await registry.register(domain)

        entity_types = registry.get_all_entity_types()
        assert "simple" in entity_types
        assert len(entity_types["simple"]) == 1
        assert entity_types["simple"][0].name == "entity"

    @pytest.mark.asyncio
    async def test_get_all_relationship_types(self) -> None:
        """Test getting all relationship types."""
        registry = DomainRegistry()
        domain = SimpleDomain()

        await registry.register(domain)

        rel_types = registry.get_all_relationship_types()
        assert "simple" in rel_types
        assert len(rel_types["simple"]) == 1
        assert rel_types["simple"][0].name == "relates_to"

    @pytest.mark.asyncio
    async def test_get_all_patterns(self) -> None:
        """Test getting all patterns."""
        registry = DomainRegistry()
        domain = SimpleDomain()

        await registry.register(domain)

        patterns = registry.get_all_patterns()
        assert isinstance(patterns, list)

        # Test filtering by domain
        patterns = registry.get_all_patterns(domains=["simple"])
        assert isinstance(patterns, list)

    @pytest.mark.asyncio
    async def test_validate_entity(self) -> None:
        """Test entity validation through registry."""
        registry = DomainRegistry()
        domain = SimpleDomain()

        await registry.register(domain)

        # Valid entity
        errors = registry.validate_entity("simple", "entity", {"name": "test"})
        assert len(errors) == 0

        # Invalid entity
        errors = registry.validate_entity("simple", "entity", {})
        assert len(errors) > 0

        # Unknown domain
        errors = registry.validate_entity("unknown", "entity", {"name": "test"})
        assert "not found" in errors[0]

    @pytest.mark.asyncio
    async def test_validate_relationship(self) -> None:
        """Test relationship validation through registry."""
        registry = DomainRegistry()
        domain = SimpleDomain()

        await registry.register(domain)

        # Valid relationship
        errors = registry.validate_relationship(
            "simple", "relates_to", "entity", "entity"
        )
        assert len(errors) == 0

        # Invalid relationship
        errors = registry.validate_relationship(
            "simple", "relates_to", "unknown", "entity"
        )
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_get_domain_info(self) -> None:
        """Test getting comprehensive domain information."""
        registry = DomainRegistry()
        domain = SimpleDomain()

        await registry.register(domain)

        info = registry.get_domain_info("simple")
        assert info is not None
        assert info["name"] == "simple"
        assert info["display_name"] == "Simple Domain"
        assert info["version"] == "1.0.0"
        assert len(info["entity_types"]) == 1
        assert len(info["relationship_types"]) == 1

        # Unknown domain
        info = registry.get_domain_info("unknown")
        assert info is None

    @pytest.mark.asyncio
    async def test_concurrent_registration(self) -> None:
        """Test thread-safe concurrent registration."""
        registry = DomainRegistry()

        class TestDomain1(BaseDomain):
            @property
            def name(self) -> str:
                return "test1"

            @property
            def display_name(self) -> str:
                return "Test 1"

            @property
            def version(self) -> str:
                return "1.0.0"

            @property
            def entity_types(self) -> list:
                return [
                    EntityTypeDefinition(
                        name="e1", description="Test", required_properties=["name"]
                    )
                ]

            @property
            def relationship_types(self) -> list:
                return []

        class TestDomain2(BaseDomain):
            @property
            def name(self) -> str:
                return "test2"

            @property
            def display_name(self) -> str:
                return "Test 2"

            @property
            def version(self) -> str:
                return "1.0.0"

            @property
            def entity_types(self) -> list:
                return [
                    EntityTypeDefinition(
                        name="e2", description="Test", required_properties=["name"]
                    )
                ]

            @property
            def relationship_types(self) -> list:
                return []

        # Register domains concurrently
        await asyncio.gather(
            registry.register(TestDomain1()), registry.register(TestDomain2())
        )

        assert "test1" in registry.list_domains()
        assert "test2" in registry.list_domains()
