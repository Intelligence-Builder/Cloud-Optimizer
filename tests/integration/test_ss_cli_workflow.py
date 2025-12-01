"""
Integration tests for Smart-Scaffold CLI workflows.

These tests execute the shipping CLI entrypoints against real JSON exports
and the in-process LocalIBService (no mocks). They validate that the public
commands can migrate data, emit validation summaries, and clean up evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest

from cloud_optimizer.integrations.smart_scaffold.cli import (
    PATHS,
    run_cleanup_cli,
    run_full_migration_cli,
)


def _sample_entities() -> List[dict]:
    return [
        {
            "id": "issue-100",
            "type": "Issue",
            "name": "Integration Test Issue",
            "properties": {"state": "open", "number": 501},
        },
        {
            "id": "pr-100",
            "type": "PR",
            "name": "Integration Test PR",
            "properties": {"state": "merged", "number": 601},
        },
    ]


def _sample_relationships() -> List[dict]:
    return [
        {"type": "implements", "source_id": "pr-100", "target_id": "issue-100"},
    ]


@pytest.mark.integration
def test_full_migration_cli_generates_mapping(tmp_path: Path, capfd) -> None:
    """Run full migration CLI end-to-end and assert mapping + validation output."""
    entities_path = tmp_path / "entities.json"
    relationships_path = tmp_path / "relationships.json"
    mapping_path = tmp_path / "entity_mapping.json"

    entities_path.write_text(json.dumps(_sample_entities()), encoding="utf-8")
    relationships_path.write_text(json.dumps(_sample_relationships()), encoding="utf-8")

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
            "2",
            "--ib-backend",
            "memory",
        ]
    )

    assert mapping_path.exists()
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    assert set(mapping.keys()) == {"issue-100", "pr-100"}

    captured = capfd.readouterr().out
    assert '"passed": true' in captured


@pytest.mark.integration
def test_cli_cleanup_removes_temp_files(tmp_path: Path) -> None:
    """Ensure cleanup CLI deletes generated migration artifacts."""
    fake_temp = tmp_path / "temp"
    fake_temp.mkdir()
    artifact = fake_temp / "cleanup_me.json"
    artifact.write_text("{}", encoding="utf-8")

    original_temp = PATHS["temp"]
    PATHS["temp"] = fake_temp
    try:
        run_cleanup_cli(["temp-files", "--pattern", "*.json"])
    finally:
        PATHS["temp"] = original_temp

    assert not artifact.exists()
