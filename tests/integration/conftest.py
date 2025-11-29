"""
Integration test fixtures for Cloud Optimizer.

These fixtures provide shared resources for ALL integration tests.
All tests use REAL connections - NO MOCKS.

Requirements:
    docker-compose -f docker/docker-compose.test.yml up -d

Services:
    - PostgreSQL (port 5434) - Graph database
    - Memgraph (port 7688) - Graph database
    - LocalStack (port 4566) - AWS services
"""

import asyncio
import json
import os
from pathlib import Path
from typing import AsyncGenerator, List, Tuple
from uuid import uuid4

import pytest
import pytest_asyncio

from src.ib_platform.domains.loader import DomainLoader
from src.ib_platform.domains.registry import DomainRegistry
from src.ib_platform.graph.backends.memgraph import MemgraphBackend
from src.ib_platform.graph.backends.postgres_cte import PostgresCTEBackend
from src.ib_platform.graph.factory import GraphBackendFactory
from src.ib_platform.graph.protocol import GraphEdge, GraphNode
from src.ib_platform.patterns.detector import PatternDetector
from src.ib_platform.patterns.matcher import PatternMatcher
from src.ib_platform.patterns.models import PatternCategory, PatternDefinition
from src.ib_platform.patterns.registry import PatternRegistry
from src.ib_platform.patterns.scorer import ConfidenceScorer

# Import from graph test conftest for backend fixtures
from tests.ib_platform.graph.conftest import (
    MEMGRAPH_TEST_CONFIG,
    POSTGRES_TEST_CONFIG,
    asyncpg_pool,
    memgraph_backend,
    postgres_backend,
)

# Import AWS/LocalStack fixtures
from tests.integration.aws_conftest import (
    LOCALSTACK_ENDPOINT,
    aws_account_id,
    ec2_client,
    encrypted_bucket,
    iam_client,
    is_localstack_available,
    least_privilege_policy,
    risky_security_group,
    s3_client,
    safe_security_group,
    unencrypted_bucket,
    user_with_mfa,
    user_without_mfa,
    vpc_id,
    wildcard_policy,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_nodes_100() -> List[dict]:
    """Generate 100 test node specifications."""
    return [
        {
            "labels": ["TestNode"],
            "properties": {
                "name": f"node-{i:03d}",
                "index": i,
                "category": chr(65 + (i % 5)),  # A-E
                "batch_id": "test-100",
            },
        }
        for i in range(100)
    ]


@pytest.fixture
def sample_edges_200(sample_nodes_100) -> List[dict]:
    """Generate 200 edge specifications for the 100 nodes."""
    edges = []
    # Create chain edges (0->1->2->...->99) = 99 edges
    for i in range(99):
        edges.append(
            {
                "source_index": i,
                "target_index": i + 1,
                "edge_type": "NEXT",
                "properties": {"order": i},
            }
        )
    # Create cross-links for interesting paths = 9 edges (0->10, 10->20, ..., 80->90)
    for i in range(0, 90, 10):
        edges.append(
            {
                "source_index": i,
                "target_index": i + 10,
                "edge_type": "SHORTCUT",
                "properties": {"skip": 10},
            }
        )
    # Add deterministic connections to reach exactly 200
    # We have 99 + 9 = 108 edges, need 92 more
    import random

    random.seed(42)  # Reproducible
    added = set()
    while len(edges) < 200:
        source = random.randint(0, 99)
        target = random.randint(0, 99)
        key = (source, target)
        if source != target and key not in added:
            added.add(key)
            edges.append(
                {
                    "source_index": source,
                    "target_index": target,
                    "edge_type": "RELATED_TO",
                    "properties": {"random": True},
                }
            )
    return edges


@pytest.fixture
def test_document_10kb() -> str:
    """Load 10KB test document for pattern detection."""
    doc_path = FIXTURES_DIR / "patterns" / "test_document_10kb.txt"
    if doc_path.exists():
        return doc_path.read_text()
    # Fallback: generate sample text
    return (
        """
    Security Assessment Report
    CVE-2023-44487 Critical vulnerability detected.
    Cost impact: $50,000 estimated.
    Timeline: Patch within 24 hours.
    Compliance: SOC 2 85% compliant.
    """
        * 100
    )


@pytest.fixture
def confidence_test_cases() -> List[dict]:
    """Test cases for confidence scoring accuracy."""
    return [
        {
            "text": "CVE-2023-12345 is a critical vulnerability",
            "expected_confidence": 0.95,
            "expected_type": "vulnerability",
        },
        {
            "text": "The cost is approximately $150,000",
            "expected_confidence": 0.85,
            "expected_type": "cost",
        },
        {
            "text": "Complete migration within 30 days",
            "expected_confidence": 0.80,
            "expected_type": "timeline",
        },
        {
            "text": "This is not a security finding",
            "expected_confidence": 0.30,
            "expected_type": None,
        },
        {
            "text": "90% compliance achieved for SOC 2",
            "expected_confidence": 0.85,
            "expected_type": "compliance",
        },
    ]


@pytest_asyncio.fixture
async def populated_backends(
    postgres_backend: PostgresCTEBackend,
    memgraph_backend: MemgraphBackend,
    sample_nodes_100: List[dict],
    sample_edges_200: List[dict],
) -> AsyncGenerator[Tuple[PostgresCTEBackend, MemgraphBackend, List[GraphNode]], None]:
    """
    Populate both backends with identical test data for parity testing.

    Returns tuple of (postgres_backend, memgraph_backend, created_nodes).
    """
    pg_nodes = []
    mg_nodes = []

    # Create nodes in both backends
    for node_spec in sample_nodes_100:
        pg_node = await postgres_backend.create_node(
            labels=node_spec["labels"],
            properties=node_spec["properties"],
        )
        mg_node = await memgraph_backend.create_node(
            labels=node_spec["labels"],
            properties=node_spec["properties"],
        )
        pg_nodes.append(pg_node)
        mg_nodes.append(mg_node)

    # Create edges in both backends
    for edge_spec in sample_edges_200:
        source_idx = edge_spec["source_index"]
        target_idx = edge_spec["target_index"]

        await postgres_backend.create_edge(
            source_id=pg_nodes[source_idx].id,
            target_id=pg_nodes[target_idx].id,
            edge_type=edge_spec["edge_type"],
            properties=edge_spec["properties"],
        )
        await memgraph_backend.create_edge(
            source_id=mg_nodes[source_idx].id,
            target_id=mg_nodes[target_idx].id,
            edge_type=edge_spec["edge_type"],
            properties=edge_spec["properties"],
        )

    # Store node mappings for tests
    postgres_backend._test_nodes = pg_nodes
    memgraph_backend._test_nodes = mg_nodes

    yield postgres_backend, memgraph_backend, pg_nodes


@pytest.fixture
def pattern_registry() -> PatternRegistry:
    """Create pattern registry with security patterns."""
    registry = PatternRegistry()

    # Register security patterns using correct field names
    patterns = [
        PatternDefinition(
            id=uuid4(),
            name="cve_pattern",
            regex_pattern=r"CVE-\d{4}-\d{4,}",
            category=PatternCategory.ENTITY,
            output_type="vulnerability",
            base_confidence=0.95,
            domain="security",
        ),
        PatternDefinition(
            id=uuid4(),
            name="cost_pattern",
            regex_pattern=r"\$[\d,]+(?:\.\d{2})?",
            category=PatternCategory.QUANTITATIVE,
            output_type="cost",
            base_confidence=0.85,
            domain="cost",
        ),
        PatternDefinition(
            id=uuid4(),
            name="timeline_pattern",
            regex_pattern=r"within\s+\d+\s+(?:days?|hours?|weeks?)",
            category=PatternCategory.TEMPORAL,
            output_type="timeline",
            base_confidence=0.80,
            domain="general",
        ),
        PatternDefinition(
            id=uuid4(),
            name="compliance_pattern",
            regex_pattern=r"\d+%\s+compli(?:ant|ance)",
            category=PatternCategory.QUANTITATIVE,
            output_type="compliance",
            base_confidence=0.85,
            domain="compliance",
        ),
    ]

    for pattern in patterns:
        registry.register(pattern)

    return registry


@pytest.fixture
def pattern_detector(pattern_registry: PatternRegistry) -> PatternDetector:
    """Create pattern detector with real components."""
    # PatternDetector creates its own matcher and scorer if not provided
    return PatternDetector(registry=pattern_registry)


@pytest.fixture
def domain_registry() -> DomainRegistry:
    """Create empty domain registry for testing."""
    return DomainRegistry()


@pytest.fixture
def domain_loader() -> DomainLoader:
    """Create domain loader for testing."""
    return DomainLoader()
