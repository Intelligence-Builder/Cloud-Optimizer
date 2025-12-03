"""Pytest fixtures for QA process tests."""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator

import pytest


@pytest.fixture
def temp_evidence_dir() -> Iterator[Path]:
    """Create temporary evidence directory structure.

    Yields:
        Path to temporary evidence base directory
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="qa_test_evidence_"))
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def valid_evidence_structure(temp_evidence_dir: Path) -> Path:
    """Create a valid evidence directory structure.

    Args:
        temp_evidence_dir: Base evidence directory

    Returns:
        Path to issue evidence directory with valid structure
    """
    issue_dir = temp_evidence_dir / "issue_123"
    qa_dir = issue_dir / "qa"
    qa_dir.mkdir(parents=True)

    # Create context_manifest.json
    manifest = {
        "issue": 123,
        "timestamp": "2025-12-03T12:00:00Z",
        "artifacts": ["context_manifest.json", "tests/pytest-summary.md"],
    }
    (qa_dir / "context_manifest.json").write_text(json.dumps(manifest, indent=2))

    # Create test summary
    tests_dir = qa_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "pytest-summary.md").write_text(
        """# Test Summary

## Results
- Total: 10
- Passed: 10
- Failed: 0
"""
    )

    # Create static analysis logs
    static_dir = qa_dir / "static_analysis"
    static_dir.mkdir()
    (static_dir / "bandit.log").write_text("No issues found")
    (static_dir / "ruff.log").write_text("All checks passed")

    return issue_dir


@pytest.fixture
def invalid_evidence_structure(temp_evidence_dir: Path) -> Path:
    """Create an invalid evidence directory structure (missing required files).

    Args:
        temp_evidence_dir: Base evidence directory

    Returns:
        Path to issue evidence directory with invalid structure
    """
    issue_dir = temp_evidence_dir / "issue_456"
    qa_dir = issue_dir / "qa"
    qa_dir.mkdir(parents=True)

    # Only create context_manifest.json, missing other required files
    manifest = {"issue": 456, "timestamp": "2025-12-03T12:00:00Z"}
    (qa_dir / "context_manifest.json").write_text(json.dumps(manifest, indent=2))

    return issue_dir


@pytest.fixture
def missing_evidence_structure(temp_evidence_dir: Path) -> Path:
    """Create evidence directory without qa subdirectory.

    Args:
        temp_evidence_dir: Base evidence directory

    Returns:
        Path to issue evidence directory without qa subdirectory
    """
    issue_dir = temp_evidence_dir / "issue_789"
    issue_dir.mkdir(parents=True)
    return issue_dir


@pytest.fixture
def malformed_json_evidence(temp_evidence_dir: Path) -> Path:
    """Create evidence directory with malformed JSON manifest.

    Args:
        temp_evidence_dir: Base evidence directory

    Returns:
        Path to issue evidence directory with malformed JSON
    """
    issue_dir = temp_evidence_dir / "issue_999"
    qa_dir = issue_dir / "qa"
    qa_dir.mkdir(parents=True)

    # Create malformed JSON
    (qa_dir / "context_manifest.json").write_text("{ invalid json }")

    # Create valid test summary
    tests_dir = qa_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "pytest-summary.md").write_text("# Test Summary")

    return issue_dir


@pytest.fixture
def sample_qa_config() -> Dict[str, Any]:
    """Sample QA configuration.

    Returns:
        Configuration dictionary
    """
    return {
        "project_number": 5,
        "project_owner": "Intelligence-Builder",
        "project_type": "organization",
        "evidence_base_path": "evidence",
        "dry_run": False,
        "verbose": False,
        "project_id": "PVT_kwDODc2V1s4BJVrg",
        "status_field_id": "PVTSSF_lADODc2V1s4BJVrgzg5iEqc",
        "status_options": {
            "Backlog": "6dae500e",
            "In Progress": "47fc9ee4",
            "Review": "617b2016",
            "Blocked": "5fb7f92e",
            "Done": "2ab98e29",
        },
    }


@pytest.fixture
def temp_config_file(temp_evidence_dir: Path, sample_qa_config: Dict[str, Any]) -> Path:
    """Create temporary config file.

    Args:
        temp_evidence_dir: Base evidence directory
        sample_qa_config: Configuration dictionary

    Returns:
        Path to config file
    """
    # Update evidence path to point to temp directory
    config = sample_qa_config.copy()
    config["evidence_base_path"] = str(temp_evidence_dir)

    config_path = temp_evidence_dir / "qa_config.json"
    config_path.write_text(json.dumps(config, indent=2))
    return config_path


@pytest.fixture
def mock_gh_output() -> Dict[str, str]:
    """Mock GitHub CLI output responses.

    Returns:
        Dictionary mapping command patterns to output
    """
    return {
        "issue_view": json.dumps(
            {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "labels": [{"name": "bug"}, {"name": "qa-pending"}],
                "state": "OPEN",
            }
        ),
        "issue_comment": "Comment posted successfully",
        "issue_edit": "Issue updated successfully",
        "project_list": json.dumps(
            [
                {
                    "number": 5,
                    "title": "Cloud-Optimizer",
                    "id": "PVT_kwDODc2V1s4BJVrg",
                }
            ]
        ),
    }


@pytest.fixture
def repo_root() -> Path:
    """Get repository root directory.

    Returns:
        Path to repository root
    """
    return Path(__file__).parent.parent.parent


@pytest.fixture
def qa_process_script(repo_root: Path) -> Path:
    """Get path to qa-process shell script.

    Args:
        repo_root: Repository root

    Returns:
        Path to qa-process script
    """
    return repo_root / "qa-process"


@pytest.fixture
def qa_process_v2_script(repo_root: Path) -> Path:
    """Get path to qa_process_v2.py script.

    Args:
        repo_root: Repository root

    Returns:
        Path to qa_process_v2.py script
    """
    return repo_root / "scripts" / "qa_process_v2.py"
