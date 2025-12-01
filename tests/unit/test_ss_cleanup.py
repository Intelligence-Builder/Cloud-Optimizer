"""
Tests for cleanup CLI helpers (entity deletion / temp file cleanup).
"""

from pathlib import Path

from cloud_optimizer.integrations.smart_scaffold.cli import _cleanup_temp_files


def test_cleanup_temp_files(tmp_path, caplog):
    caplog.set_level("INFO")
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    file_a = temp_dir / "mapping.json"
    file_b = temp_dir / "validation.json"
    file_a.write_text("{}", encoding="utf-8")
    file_b.write_text("{}", encoding="utf-8")

    # Point PATHS["temp"] to our temp dir for this test
    from cloud_optimizer.integrations.smart_scaffold import cli

    cli.PATHS["temp"] = temp_dir

    _cleanup_temp_files("*.json")

    assert not file_a.exists()
    assert not file_b.exists()
