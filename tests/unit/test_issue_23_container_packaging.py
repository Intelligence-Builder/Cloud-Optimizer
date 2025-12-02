"""
Unit tests for Issue #23 (6.1 Container Packaging).

These tests validate the Dockerfile structure without mocking any tooling.
They ensure the production image follows the multi-stage, health-checked
packaging requirements defined for the MVP container product.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

DOCKERFILE_PATH = Path("docker/Dockerfile")


def _load_dockerfile() -> list[str]:
    if not DOCKERFILE_PATH.exists():
        pytest.skip("Dockerfile missing - container packaging not implemented")
    return DOCKERFILE_PATH.read_text(encoding="utf-8").splitlines()


def test_dockerfile_uses_multistage_build() -> None:
    """Dockerfile must contain separate builder and runtime stages."""
    lines = _load_dockerfile()
    from_statements = [line for line in lines if line.strip().startswith("FROM ")]
    assert len(from_statements) >= 2, "Expected multi-stage build with at least 2 FROM statements"
    assert "AS builder" in from_statements[0]
    assert "AS runtime" in from_statements[1]


def test_dockerfile_runs_as_non_root() -> None:
    """Runtime image must switch to the dedicated appuser."""
    lines = _load_dockerfile()
    assert any(line.strip() == "USER appuser" for line in lines), "USER appuser missing"


def test_dockerfile_has_healthcheck_endpoint() -> None:
    """Health check must probe /health endpoint on port 8080."""
    contents = "\n".join(_load_dockerfile())
    match = re.search(r"HEALTHCHECK.*curl.*http://localhost:8080/health", contents, re.DOTALL)
    assert match, "HEALTHCHECK for /health endpoint is required"


def test_dockerfile_entrypoint_runs_uvicorn() -> None:
    """Runtime should launch the FastAPI app via uvicorn."""
    contents = "\n".join(_load_dockerfile())
    assert 'CMD ["uvicorn", "cloud_optimizer.main:app"' in contents
