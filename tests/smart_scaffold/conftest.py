"""Pytest fixtures for Smart-Scaffold parallel validator tests.

These fixtures provide divergent SS/IB datasets for testing the parallel
validator's ability to detect inconsistencies between knowledge graphs.
"""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import pytest


def utc_now_iso() -> str:
    """Return current UTC time as ISO format string."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class KnowledgeGraphEntry:
    """Represents a knowledge graph entry for testing."""

    id: str
    entity_type: str
    name: str
    properties: dict[str, Any]
    source: str  # 'ss' or 'ib'
    timestamp: str


@dataclass
class DivergenceScenario:
    """Test scenario with divergent SS/IB data."""

    name: str
    ss_entries: list[KnowledgeGraphEntry]
    ib_entries: list[KnowledgeGraphEntry]
    expected_divergences: list[dict[str, Any]]


def create_divergent_fixture_files(
    base_path: Path, scenario: DivergenceScenario
) -> tuple[Path, Path]:
    """Create fixture files for SS and IB datasets.

    Args:
        base_path: Directory to create fixtures in
        scenario: Divergence scenario containing SS and IB data

    Returns:
        Tuple of (ss_fixture_path, ib_fixture_path)
    """
    ss_dir = base_path / "smart_scaffold"
    ib_dir = base_path / "intelligence_builder"
    ss_dir.mkdir(parents=True, exist_ok=True)
    ib_dir.mkdir(parents=True, exist_ok=True)

    # Write SS fixture
    ss_data = {
        "source": "smart_scaffold",
        "timestamp": utc_now_iso(),
        "entries": [
            {
                "id": e.id,
                "entity_type": e.entity_type,
                "name": e.name,
                "properties": e.properties,
                "source": e.source,
                "timestamp": e.timestamp,
            }
            for e in scenario.ss_entries
        ],
    }
    ss_file = ss_dir / f"{scenario.name}_kg.json"
    ss_file.write_text(json.dumps(ss_data, indent=2))

    # Write IB fixture
    ib_data = {
        "source": "intelligence_builder",
        "timestamp": utc_now_iso(),
        "entries": [
            {
                "id": e.id,
                "entity_type": e.entity_type,
                "name": e.name,
                "properties": e.properties,
                "source": e.source,
                "timestamp": e.timestamp,
            }
            for e in scenario.ib_entries
        ],
    }
    ib_file = ib_dir / f"{scenario.name}_kg.json"
    ib_file.write_text(json.dumps(ib_data, indent=2))

    return ss_file, ib_file


@pytest.fixture
def smart_scaffold_available() -> bool:
    """Check if smart-scaffold CLI is available."""
    try:
        result = subprocess.run(
            ["smart-scaffold", "--version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture
def divergent_data_dir(tmp_path: Path) -> Path:
    """Create temporary directory for divergent test data."""
    data_dir = tmp_path / "divergent_fixtures"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def scenario_missing_entity() -> DivergenceScenario:
    """Scenario: Entity exists in SS but missing in IB."""
    base_timestamp = utc_now_iso()

    ss_entries = [
        KnowledgeGraphEntry(
            id="aws-s3-bucket-001",
            entity_type="aws_resource",
            name="production-data-bucket",
            properties={
                "service": "s3",
                "region": "us-east-1",
                "encryption": "AES256",
                "versioning": True,
            },
            source="ss",
            timestamp=base_timestamp,
        ),
        KnowledgeGraphEntry(
            id="aws-ec2-instance-001",
            entity_type="aws_resource",
            name="web-server-prod-1",
            properties={
                "service": "ec2",
                "instance_type": "t3.medium",
                "region": "us-east-1",
            },
            source="ss",
            timestamp=base_timestamp,
        ),
    ]

    ib_entries = [
        KnowledgeGraphEntry(
            id="aws-s3-bucket-001",
            entity_type="aws_resource",
            name="production-data-bucket",
            properties={
                "service": "s3",
                "region": "us-east-1",
                "encryption": "AES256",
                "versioning": True,
            },
            source="ib",
            timestamp=base_timestamp,
        ),
        # Missing: aws-ec2-instance-001 not in IB
    ]

    expected_divergences = [
        {
            "type": "missing_in_ib",
            "entity_id": "aws-ec2-instance-001",
            "entity_type": "aws_resource",
            "severity": "high",
        }
    ]

    return DivergenceScenario(
        name="missing_entity",
        ss_entries=ss_entries,
        ib_entries=ib_entries,
        expected_divergences=expected_divergences,
    )


@pytest.fixture
def scenario_property_mismatch() -> DivergenceScenario:
    """Scenario: Same entity but different property values."""
    base_timestamp = utc_now_iso()

    ss_entries = [
        KnowledgeGraphEntry(
            id="security-finding-001",
            entity_type="security_finding",
            name="S3 Bucket Public Access",
            properties={
                "severity": "critical",
                "status": "open",
                "resource_id": "arn:aws:s3:::my-bucket",
                "remediation": "Enable block public access",
            },
            source="ss",
            timestamp=base_timestamp,
        ),
    ]

    ib_entries = [
        KnowledgeGraphEntry(
            id="security-finding-001",
            entity_type="security_finding",
            name="S3 Bucket Public Access",
            properties={
                "severity": "high",  # Different: SS says "critical"
                "status": "resolved",  # Different: SS says "open"
                "resource_id": "arn:aws:s3:::my-bucket",
                "remediation": "Enable block public access",
            },
            source="ib",
            timestamp=base_timestamp,
        ),
    ]

    expected_divergences = [
        {
            "type": "property_mismatch",
            "entity_id": "security-finding-001",
            "property": "severity",
            "ss_value": "critical",
            "ib_value": "high",
            "severity": "medium",
        },
        {
            "type": "property_mismatch",
            "entity_id": "security-finding-001",
            "property": "status",
            "ss_value": "open",
            "ib_value": "resolved",
            "severity": "high",
        },
    ]

    return DivergenceScenario(
        name="property_mismatch",
        ss_entries=ss_entries,
        ib_entries=ib_entries,
        expected_divergences=expected_divergences,
    )


@pytest.fixture
def scenario_stale_data() -> DivergenceScenario:
    """Scenario: IB has older timestamp than SS (stale data)."""
    ss_timestamp = "2025-12-03T10:00:00Z"
    ib_timestamp = "2025-11-01T10:00:00Z"  # Stale by 32 days

    ss_entries = [
        KnowledgeGraphEntry(
            id="compliance-control-001",
            entity_type="compliance_control",
            name="CIS AWS 2.1.1",
            properties={
                "framework": "CIS",
                "version": "2.0",
                "status": "compliant",
                "last_checked": ss_timestamp,
            },
            source="ss",
            timestamp=ss_timestamp,
        ),
    ]

    ib_entries = [
        KnowledgeGraphEntry(
            id="compliance-control-001",
            entity_type="compliance_control",
            name="CIS AWS 2.1.1",
            properties={
                "framework": "CIS",
                "version": "2.0",
                "status": "non_compliant",  # Old status
                "last_checked": ib_timestamp,
            },
            source="ib",
            timestamp=ib_timestamp,
        ),
    ]

    expected_divergences = [
        {
            "type": "stale_data",
            "entity_id": "compliance-control-001",
            "ss_timestamp": ss_timestamp,
            "ib_timestamp": ib_timestamp,
            "stale_days": 32,
            "severity": "medium",
        },
        {
            "type": "property_mismatch",
            "entity_id": "compliance-control-001",
            "property": "status",
            "ss_value": "compliant",
            "ib_value": "non_compliant",
            "severity": "high",
        },
    ]

    return DivergenceScenario(
        name="stale_data",
        ss_entries=ss_entries,
        ib_entries=ib_entries,
        expected_divergences=expected_divergences,
    )


@pytest.fixture
def scenario_relationship_divergence() -> DivergenceScenario:
    """Scenario: Different relationships between entities."""
    base_timestamp = utc_now_iso()

    ss_entries = [
        KnowledgeGraphEntry(
            id="aws-vpc-001",
            entity_type="aws_resource",
            name="production-vpc",
            properties={
                "service": "vpc",
                "cidr": "10.0.0.0/16",
                "connected_subnets": ["subnet-001", "subnet-002", "subnet-003"],
            },
            source="ss",
            timestamp=base_timestamp,
        ),
    ]

    ib_entries = [
        KnowledgeGraphEntry(
            id="aws-vpc-001",
            entity_type="aws_resource",
            name="production-vpc",
            properties={
                "service": "vpc",
                "cidr": "10.0.0.0/16",
                "connected_subnets": ["subnet-001", "subnet-002"],  # Missing subnet-003
            },
            source="ib",
            timestamp=base_timestamp,
        ),
    ]

    expected_divergences = [
        {
            "type": "relationship_divergence",
            "entity_id": "aws-vpc-001",
            "relationship": "connected_subnets",
            "ss_related": ["subnet-001", "subnet-002", "subnet-003"],
            "ib_related": ["subnet-001", "subnet-002"],
            "missing_in_ib": ["subnet-003"],
            "severity": "medium",
        }
    ]

    return DivergenceScenario(
        name="relationship_divergence",
        ss_entries=ss_entries,
        ib_entries=ib_entries,
        expected_divergences=expected_divergences,
    )


@pytest.fixture
def scenario_complete_sync() -> DivergenceScenario:
    """Scenario: SS and IB are completely in sync (no divergence)."""
    base_timestamp = utc_now_iso()

    shared_entries = [
        KnowledgeGraphEntry(
            id="aws-lambda-001",
            entity_type="aws_resource",
            name="data-processor-lambda",
            properties={
                "service": "lambda",
                "runtime": "python3.11",
                "memory": 1024,
                "timeout": 300,
            },
            source="ss",  # Will be duplicated for IB
            timestamp=base_timestamp,
        ),
        KnowledgeGraphEntry(
            id="security-group-001",
            entity_type="aws_resource",
            name="web-sg",
            properties={
                "service": "ec2-security-group",
                "vpc_id": "vpc-001",
                "ingress_rules": ["tcp/443", "tcp/80"],
            },
            source="ss",
            timestamp=base_timestamp,
        ),
    ]

    ss_entries = shared_entries
    ib_entries = [
        KnowledgeGraphEntry(
            id=e.id,
            entity_type=e.entity_type,
            name=e.name,
            properties=e.properties.copy(),
            source="ib",
            timestamp=e.timestamp,
        )
        for e in shared_entries
    ]

    return DivergenceScenario(
        name="complete_sync",
        ss_entries=ss_entries,
        ib_entries=ib_entries,
        expected_divergences=[],  # No divergences expected
    )


@pytest.fixture
def all_divergence_scenarios(
    scenario_missing_entity: DivergenceScenario,
    scenario_property_mismatch: DivergenceScenario,
    scenario_stale_data: DivergenceScenario,
    scenario_relationship_divergence: DivergenceScenario,
    scenario_complete_sync: DivergenceScenario,
) -> list[DivergenceScenario]:
    """All divergence test scenarios."""
    return [
        scenario_missing_entity,
        scenario_property_mismatch,
        scenario_stale_data,
        scenario_relationship_divergence,
        scenario_complete_sync,
    ]


@pytest.fixture
def fixture_files(
    divergent_data_dir: Path,
    all_divergence_scenarios: list[DivergenceScenario],
) -> dict[str, tuple[Path, Path]]:
    """Create all fixture files and return paths.

    Returns:
        Dict mapping scenario name to (ss_path, ib_path) tuple
    """
    files = {}
    for scenario in all_divergence_scenarios:
        ss_path, ib_path = create_divergent_fixture_files(divergent_data_dir, scenario)
        files[scenario.name] = (ss_path, ib_path)
    return files
