"""
Cloud Optimizer v2 - Cloud cost optimization built on Intelligence-Builder platform.

This package provides cloud infrastructure analysis and optimization recommendations
using the Intelligence-Builder GraphRAG platform for knowledge graph operations.
"""

__version__ = "2.0.0"
__author__ = "Intelligence-Builder Team"

from cloud_optimizer.config import Settings, get_settings

__all__ = ["Settings", "get_settings", "__version__"]
