"""
Graph Database Abstraction Layer.

This module provides a unified interface for graph operations across
different backend implementations (PostgreSQL CTE, Memgraph, etc.).
"""

from .factory import GraphBackendFactory, GraphBackendType
from .protocol import (
    GraphBackendProtocol,
    GraphEdge,
    GraphNode,
    GraphPath,
    TraversalDirection,
    TraversalParams,
)

__all__ = [
    # Protocol and data classes
    "GraphBackendProtocol",
    "GraphNode",
    "GraphEdge",
    "GraphPath",
    "TraversalParams",
    "TraversalDirection",
    # Factory
    "GraphBackendFactory",
    "GraphBackendType",
]
