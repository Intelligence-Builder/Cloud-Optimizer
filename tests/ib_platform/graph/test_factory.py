"""
Tests for GraphBackendFactory.

Tests factory creation of different backend types.
No mocks - uses real database connections for integration tests.

Requirements:
    docker-compose -f docker/docker-compose.test.yml up -d
"""

import pytest

from src.ib_platform.graph.factory import GraphBackendFactory, GraphBackendType
from src.ib_platform.graph.backends.postgres_cte import PostgresCTEBackend
from src.ib_platform.graph.backends.memgraph import MemgraphBackend


# ============================================================================
# Unit Tests - No database required
# ============================================================================


@pytest.mark.unit
class TestGraphBackendFactoryUnit:
    """Unit tests for factory validation logic (no database required)."""

    def test_create_postgres_cte_without_pool_raises(self):
        """Test that creating PostgresCTE without pool raises ValueError."""
        with pytest.raises(ValueError, match="connection_pool is required"):
            GraphBackendFactory.create(GraphBackendType.POSTGRES_CTE)

    def test_create_memgraph_backend(self):
        """Test creating Memgraph backend (no connection needed)."""
        backend = GraphBackendFactory.create(
            GraphBackendType.MEMGRAPH,
            uri="bolt://localhost:7687",
            username="admin",
            password="secret",
        )

        assert isinstance(backend, MemgraphBackend)
        assert backend._uri == "bolt://localhost:7687"

    def test_create_memgraph_without_uri_raises(self):
        """Test that creating Memgraph without URI raises ValueError."""
        with pytest.raises(ValueError, match="uri is required"):
            GraphBackendFactory.create(GraphBackendType.MEMGRAPH)

    def test_create_unknown_backend_type_raises(self):
        """Test that unknown backend type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown backend type"):
            GraphBackendFactory.create("invalid_backend")

    def test_create_from_config_memgraph(self):
        """Test creating Memgraph backend from config (no connection needed)."""
        config = {
            "type": "memgraph",
            "uri": "bolt://localhost:7687",
            "username": "admin",
        }

        backend = GraphBackendFactory.create_from_config(config)

        assert isinstance(backend, MemgraphBackend)
        assert backend._uri == "bolt://localhost:7687"

    def test_create_from_config_without_type_raises(self):
        """Test that config without type raises ValueError."""
        config = {"uri": "bolt://localhost:7687"}

        with pytest.raises(ValueError, match="must include 'type' field"):
            GraphBackendFactory.create_from_config(config)

    def test_create_from_config_invalid_type_raises(self):
        """Test that invalid type in config raises ValueError."""
        config = {"type": "invalid_backend"}

        with pytest.raises(ValueError, match="Invalid backend type"):
            GraphBackendFactory.create_from_config(config)


# ============================================================================
# Integration Tests - Requires real database
# ============================================================================


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.asyncio
class TestGraphBackendFactoryIntegration:
    """Integration tests for factory with real database connections."""

    async def test_create_postgres_cte_backend(self, asyncpg_pool):
        """Test creating PostgresCTE backend with real pool."""
        backend = GraphBackendFactory.create(
            GraphBackendType.POSTGRES_CTE,
            connection_pool=asyncpg_pool,
            schema="intelligence",
        )

        assert isinstance(backend, PostgresCTEBackend)
        assert backend._schema == "intelligence"

        # Verify the backend can actually connect
        await backend.connect()
        assert backend.is_connected
        await backend.disconnect()

    async def test_create_from_config_postgres(self, asyncpg_pool):
        """Test creating PostgresCTE backend from config with real pool."""
        config = {
            "type": "postgres_cte",
            "connection_pool": asyncpg_pool,
            "schema": "intelligence",
        }

        backend = GraphBackendFactory.create_from_config(config)

        assert isinstance(backend, PostgresCTEBackend)
        assert backend._schema == "intelligence"

        # Verify the backend works
        await backend.connect()
        assert backend.is_connected
        await backend.disconnect()


@pytest.mark.unit
class TestGraphBackendType:
    """Test GraphBackendType enum."""

    def test_backend_type_values(self):
        """Test that backend types have correct values."""
        assert GraphBackendType.POSTGRES_CTE.value == "postgres_cte"
        assert GraphBackendType.MEMGRAPH.value == "memgraph"

    def test_backend_type_from_string(self):
        """Test creating backend type from string."""
        assert GraphBackendType("postgres_cte") == GraphBackendType.POSTGRES_CTE
        assert GraphBackendType("memgraph") == GraphBackendType.MEMGRAPH
