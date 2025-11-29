"""
Graph Backend Factory.

Factory for creating graph backend instances based on configuration.
"""

import logging
from enum import Enum
from typing import Any, Dict

from .backends.memgraph import MemgraphBackend
from .backends.postgres_cte import PostgresCTEBackend
from .protocol import GraphBackendProtocol

logger = logging.getLogger(__name__)


class GraphBackendType(str, Enum):
    """Supported graph backend types."""

    POSTGRES_CTE = "postgres_cte"
    MEMGRAPH = "memgraph"


class GraphBackendFactory:
    """
    Factory for creating graph backend instances.

    Usage:
        backend = GraphBackendFactory.create(
            GraphBackendType.POSTGRES_CTE,
            connection_pool=pool,
            schema="intelligence",
        )
        await backend.connect()
    """

    @staticmethod
    def create(
        backend_type: GraphBackendType,
        **kwargs: Any,
    ) -> GraphBackendProtocol:
        """
        Create a graph backend instance.

        Args:
            backend_type: Type of backend to create
            **kwargs: Backend-specific configuration parameters

        Returns:
            Configured GraphBackendProtocol instance

        Raises:
            ValueError: If backend_type is unknown or required params missing

        Examples:
            PostgresCTE backend:
                backend = GraphBackendFactory.create(
                    GraphBackendType.POSTGRES_CTE,
                    connection_pool=pool,
                    schema="intelligence",
                )

            Memgraph backend:
                backend = GraphBackendFactory.create(
                    GraphBackendType.MEMGRAPH,
                    uri="bolt://localhost:7687",
                    username="admin",
                    password="secret",
                )
        """
        logger.info(f"Creating graph backend: {backend_type}")

        if backend_type == GraphBackendType.POSTGRES_CTE:
            return GraphBackendFactory._create_postgres_cte(**kwargs)

        elif backend_type == GraphBackendType.MEMGRAPH:
            return GraphBackendFactory._create_memgraph(**kwargs)

        else:
            raise ValueError(f"Unknown backend type: {backend_type}")

    @staticmethod
    def _create_postgres_cte(**kwargs: Any) -> PostgresCTEBackend:
        """
        Create PostgresCTE backend instance.

        Required kwargs:
            connection_pool: asyncpg.Pool instance

        Optional kwargs:
            schema: Database schema name (default: "intelligence")
            entities_table: Entities table name (default: "entities")
            relationships_table: Relationships table name (default: "relationships")
        """
        connection_pool = kwargs.get("connection_pool")
        if not connection_pool:
            raise ValueError("connection_pool is required for PostgresCTE backend")

        backend = PostgresCTEBackend(
            connection_pool=connection_pool,
            schema=kwargs.get("schema", "intelligence"),
            entities_table=kwargs.get("entities_table", "entities"),
            relationships_table=kwargs.get("relationships_table", "relationships"),
        )

        logger.debug(
            f"Created PostgresCTEBackend with schema: {kwargs.get('schema', 'intelligence')}"
        )
        return backend

    @staticmethod
    def _create_memgraph(**kwargs: Any) -> MemgraphBackend:
        """
        Create Memgraph backend instance.

        Required kwargs:
            uri: Memgraph connection URI (e.g., "bolt://localhost:7687")

        Optional kwargs:
            username: Authentication username
            password: Authentication password
            database: Specific database name
        """
        uri = kwargs.get("uri")
        if not uri:
            raise ValueError("uri is required for Memgraph backend")

        backend = MemgraphBackend(
            uri=uri,
            username=kwargs.get("username"),
            password=kwargs.get("password"),
            database=kwargs.get("database"),
        )

        logger.debug(f"Created MemgraphBackend with URI: {uri}")
        return backend

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> GraphBackendProtocol:
        """
        Create a graph backend from a configuration dictionary.

        Args:
            config: Configuration dictionary with 'type' and backend-specific params

        Returns:
            Configured GraphBackendProtocol instance

        Raises:
            ValueError: If config is invalid

        Example:
            config = {
                "type": "postgres_cte",
                "connection_pool": pool,
                "schema": "intelligence"
            }
            backend = GraphBackendFactory.create_from_config(config)
        """
        backend_type_str = config.get("type")
        if not backend_type_str:
            raise ValueError("Configuration must include 'type' field")

        try:
            backend_type = GraphBackendType(backend_type_str)
        except ValueError:
            raise ValueError(
                f"Invalid backend type: {backend_type_str}. "
                f"Must be one of: {[t.value for t in GraphBackendType]}"
            )

        # Remove 'type' from kwargs
        kwargs = {k: v for k, v in config.items() if k != "type"}

        return GraphBackendFactory.create(backend_type, **kwargs)
