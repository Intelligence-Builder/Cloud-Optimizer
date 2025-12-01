"""
Tests for Smart-Scaffold migration CLI utilities.
"""

import json
from pathlib import Path

from cloud_optimizer.integrations.smart_scaffold.cli import (
    run_entity_migration_cli,
    run_full_migration_cli,
    run_parallel_validator_cli,
    run_relationship_migration_cli,
)


def _write_entities(tmp_path: Path) -> Path:
    entities = [
        {"id": "issue-001", "type": "Issue", "name": "Test Issue", "properties": {}},
        {"id": "pr-001", "type": "PR", "name": "Test PR", "properties": {}},
    ]
    path = tmp_path / "entities.json"
    path.write_text(json.dumps(entities), encoding="utf-8")
    return path


def _write_relationships(tmp_path: Path) -> Path:
    relationships = [
        {
            "type": "implements",
            "source_id": "pr-001",
            "target_id": "issue-001",
        }
    ]
    path = tmp_path / "relationships.json"
    path.write_text(json.dumps(relationships), encoding="utf-8")
    return path


def test_entity_migration_cli_creates_mapping(tmp_path):
    entities_path = _write_entities(tmp_path)
    mapping_path = tmp_path / "mapping.json"

    run_entity_migration_cli(
        [
            "--input",
            str(entities_path),
            "--mapping-output",
            str(mapping_path),
            "--batch-size",
            "1",
        ]
    )

    assert mapping_path.exists()
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    assert len(mapping) == 2


def test_relationship_migration_cli_reads_mapping(tmp_path):
    entities_path = _write_entities(tmp_path)
    rel_path = _write_relationships(tmp_path)
    mapping_path = tmp_path / "mapping.json"

    # First run entity migration to create mapping file
    run_entity_migration_cli(
        [
            "--input",
            str(entities_path),
            "--mapping-output",
            str(mapping_path),
        ]
    )

    run_relationship_migration_cli(
        [
            "--input",
            str(rel_path),
            "--mapping",
            str(mapping_path),
            "--batch-size",
            "1",
        ]
    )

    # The CLI should not modify the mapping file
    assert mapping_path.exists()


def test_full_migration_cli_with_validation(tmp_path):
    entities_path = _write_entities(tmp_path)
    relationships_path = _write_relationships(tmp_path)
    mapping_path = tmp_path / "mapping.json"

    run_full_migration_cli(
        [
            "--entities",
            str(entities_path),
            "--relationships",
            str(relationships_path),
            "--mapping-output",
            str(mapping_path),
            "--validate",
            "--batch-size",
            "1",
        ]
    )

    assert mapping_path.exists()


def test_parallel_validator_cli(tmp_path):
    entities_path = _write_entities(tmp_path)
    relationships_path = _write_relationships(tmp_path)
    queries_file = tmp_path / "queries.txt"
    queries_file.write_text("Test\n", encoding="utf-8")

    run_parallel_validator_cli(
        [
            "--entities",
            str(entities_path),
            "--relationships",
            str(relationships_path),
            "--queries-file",
            str(queries_file),
            "--prime-from-entities",
        ]
    )
