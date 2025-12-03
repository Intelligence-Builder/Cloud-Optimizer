"""Tests for qa_process_v2.py script.

Tests the QA process automation script including:
- Configuration loading
- Evidence validation
- GitHub hand-off (dry-run mode)
- CLI argument parsing
- Error handling
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# Add src to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestQAConfig:
    """Tests for QAConfig class."""

    def test_config_from_env_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test QAConfig creation from environment with defaults."""
        from scripts.qa_process_v2 import QAConfig

        # Clear relevant env vars
        for key in [
            "QA_PROJECT_NUMBER",
            "QA_PROJECT_OWNER",
            "QA_PROJECT_TYPE",
            "QA_EVIDENCE_PATH",
            "QA_DRY_RUN",
            "QA_VERBOSE",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = QAConfig.from_env()

        assert config.project_number == 5
        assert config.project_owner == "Intelligence-Builder"
        assert config.project_type == "organization"
        assert config.evidence_base_path == Path("evidence")
        assert config.dry_run is False
        assert config.verbose is False

    def test_config_from_env_custom(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test QAConfig creation from environment with custom values."""
        from scripts.qa_process_v2 import QAConfig

        monkeypatch.setenv("QA_PROJECT_NUMBER", "10")
        monkeypatch.setenv("QA_PROJECT_OWNER", "TestOrg")
        monkeypatch.setenv("QA_PROJECT_TYPE", "user")
        monkeypatch.setenv("QA_EVIDENCE_PATH", "/tmp/evidence")
        monkeypatch.setenv("QA_DRY_RUN", "true")
        monkeypatch.setenv("QA_VERBOSE", "true")

        config = QAConfig.from_env()

        assert config.project_number == 10
        assert config.project_owner == "TestOrg"
        assert config.project_type == "user"
        assert config.evidence_base_path == Path("/tmp/evidence")
        assert config.dry_run is True
        assert config.verbose is True

    def test_config_from_file(self, temp_config_file: Path) -> None:
        """Test QAConfig loading from JSON file."""
        from scripts.qa_process_v2 import QAConfig

        config = QAConfig.from_file(temp_config_file)

        assert config.project_number == 5
        assert config.project_owner == "Intelligence-Builder"
        assert config.project_type == "organization"

    def test_config_from_file_not_found(self) -> None:
        """Test QAConfig loading from non-existent file raises error."""
        from scripts.qa_process_v2 import QAConfig

        with pytest.raises(FileNotFoundError):
            QAConfig.from_file(Path("/nonexistent/config.json"))


class TestEvidenceValidator:
    """Tests for EvidenceValidator class."""

    def test_validate_valid_structure(self, valid_evidence_structure: Path) -> None:
        """Test validation passes for valid evidence structure."""
        from scripts.qa_process_v2 import EvidenceValidator, IssueContext, QAConfig

        config = QAConfig()
        validator = EvidenceValidator(config)

        context = IssueContext(
            issue_number=123,
            title="Test Issue",
            body="",
            labels=[],
            evidence_dir=valid_evidence_structure,
            config=config,
        )

        result = validator.validate(context)

        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert "context_manifest.json" in result["metadata"]["artifacts_found"]
        assert "tests/pytest-summary.md" in result["metadata"]["artifacts_found"]

    def test_validate_invalid_structure(self, invalid_evidence_structure: Path) -> None:
        """Test validation fails for invalid evidence structure."""
        from scripts.qa_process_v2 import EvidenceValidator, IssueContext, QAConfig

        config = QAConfig()
        validator = EvidenceValidator(config)

        context = IssueContext(
            issue_number=456,
            title="Test Issue",
            body="",
            labels=[],
            evidence_dir=invalid_evidence_structure,
            config=config,
        )

        result = validator.validate(context)

        assert result["valid"] is False
        assert any("pytest-summary.md" in issue for issue in result["issues"])

    def test_validate_missing_qa_directory(self, missing_evidence_structure: Path) -> None:
        """Test validation fails when qa directory is missing."""
        from scripts.qa_process_v2 import EvidenceValidator, IssueContext, QAConfig

        config = QAConfig()
        validator = EvidenceValidator(config)

        context = IssueContext(
            issue_number=789,
            title="Test Issue",
            body="",
            labels=[],
            evidence_dir=missing_evidence_structure,
            config=config,
        )

        result = validator.validate(context)

        assert result["valid"] is False
        assert any("QA evidence directory not found" in issue for issue in result["issues"])

    def test_validate_malformed_json(self, malformed_json_evidence: Path) -> None:
        """Test validation fails for malformed JSON manifest."""
        from scripts.qa_process_v2 import EvidenceValidator, IssueContext, QAConfig

        config = QAConfig()
        validator = EvidenceValidator(config)

        context = IssueContext(
            issue_number=999,
            title="Test Issue",
            body="",
            labels=[],
            evidence_dir=malformed_json_evidence,
            config=config,
        )

        result = validator.validate(context)

        assert result["valid"] is False
        assert any("not valid JSON" in issue for issue in result["issues"])

    def test_validate_static_analysis_warnings(self, temp_evidence_dir: Path) -> None:
        """Test validation produces warnings for missing optional artifacts."""
        from scripts.qa_process_v2 import EvidenceValidator, IssueContext, QAConfig

        # Create structure with required but not optional files
        issue_dir = temp_evidence_dir / "issue_111"
        qa_dir = issue_dir / "qa"
        qa_dir.mkdir(parents=True)

        manifest = {"issue": 111}
        (qa_dir / "context_manifest.json").write_text(json.dumps(manifest))

        tests_dir = qa_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "pytest-summary.md").write_text("# Summary")

        config = QAConfig()
        validator = EvidenceValidator(config)

        context = IssueContext(
            issue_number=111,
            title="Test Issue",
            body="",
            labels=[],
            evidence_dir=issue_dir,
            config=config,
        )

        result = validator.validate(context)

        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("static_analysis" in warning for warning in result["warnings"])


class TestGitHubHandOff:
    """Tests for GitHubHandOff class."""

    def test_handoff_dry_run_valid(self, valid_evidence_structure: Path, capsys: pytest.CaptureFixture) -> None:
        """Test GitHub hand-off in dry-run mode with valid evidence."""
        from scripts.qa_process_v2 import GitHubHandOff, IssueContext, QAConfig

        config = QAConfig(dry_run=True, verbose=True)
        handoff = GitHubHandOff(config)

        context = IssueContext(
            issue_number=123,
            title="Test Issue",
            body="",
            labels=[],
            evidence_dir=valid_evidence_structure,
            config=config,
        )

        validation_result = {"valid": True, "metadata": {"artifacts_found": ["test1", "test2"]}}

        success = handoff.execute(context, validation_result)

        assert success is True

        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out
        assert "issue comment 123" in captured.out
        assert "qa-verified" in captured.out

    def test_handoff_dry_run_invalid(self, invalid_evidence_structure: Path, capsys: pytest.CaptureFixture) -> None:
        """Test GitHub hand-off in dry-run mode with invalid evidence."""
        from scripts.qa_process_v2 import GitHubHandOff, IssueContext, QAConfig

        config = QAConfig(dry_run=True, verbose=True)
        handoff = GitHubHandOff(config)

        context = IssueContext(
            issue_number=456,
            title="Test Issue",
            body="",
            labels=[],
            evidence_dir=invalid_evidence_structure,
            config=config,
        )

        validation_result = {"valid": False, "issues": ["Missing artifact"]}

        success = handoff.execute(context, validation_result)

        assert success is True

        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out
        assert "qa-failed" in captured.out


class TestCLICommands:
    """Tests for CLI commands via subprocess."""

    def test_cli_help(self, qa_process_v2_script: Path) -> None:
        """Test --help flag displays usage information."""
        result = subprocess.run(
            ["python", str(qa_process_v2_script), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "QA Process V2" in result.stdout
        assert "run" in result.stdout
        assert "validate" in result.stdout
        assert "handoff" in result.stdout

    def test_cli_version(self, qa_process_v2_script: Path) -> None:
        """Test --version flag displays version."""
        result = subprocess.run(
            ["python", str(qa_process_v2_script), "--version"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "2.0.0" in result.stdout

    def test_validate_missing_issue(self, qa_process_v2_script: Path) -> None:
        """Test validate command fails without --issue argument."""
        result = subprocess.run(
            ["python", str(qa_process_v2_script), "validate"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "missing" in result.stderr.lower()

    def test_validate_dry_run(self, qa_process_v2_script: Path, valid_evidence_structure: Path) -> None:
        """Test validate command with dry-run flag."""
        result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "validate",
                "--issue",
                "123",
                "--dry-run",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "QA_EVIDENCE_PATH": str(valid_evidence_structure.parent)},
        )

        # Should succeed with valid structure
        assert result.returncode == 0
        assert "Validation PASSED" in result.stdout

    def test_validate_invalid_evidence(
        self, qa_process_v2_script: Path, invalid_evidence_structure: Path
    ) -> None:
        """Test validate command with invalid evidence structure."""
        result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "validate",
                "--issue",
                "456",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "QA_EVIDENCE_PATH": str(invalid_evidence_structure.parent)},
        )

        # Should fail with invalid structure
        assert result.returncode == 1
        assert "Validation FAILED" in result.stdout

    def test_handoff_missing_report(self, qa_process_v2_script: Path, temp_evidence_dir: Path) -> None:
        """Test handoff command fails when validation report is missing."""
        result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "handoff",
                "--issue",
                "999",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "QA_EVIDENCE_PATH": str(temp_evidence_dir)},
        )

        assert result.returncode == 1
        # Error message goes to stdout (not stderr due to click.echo)
        assert "Validation report not found" in result.stdout or "Validation report not found" in result.stderr

    def test_handoff_with_report(self, qa_process_v2_script: Path, valid_evidence_structure: Path) -> None:
        """Test handoff command with valid validation report."""
        # Create validation report
        report_dir = valid_evidence_structure / "qa"
        report = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "metadata": {"artifacts_found": ["test"]},
        }
        (report_dir / "validation_report.json").write_text(json.dumps(report))

        result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "handoff",
                "--issue",
                "123",
                "--dry-run",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "QA_EVIDENCE_PATH": str(valid_evidence_structure.parent)},
        )

        assert result.returncode == 0
        assert "Hand-off completed successfully" in result.stdout
        assert "[DRY-RUN]" in result.stdout

    def test_run_command_dry_run(self, qa_process_v2_script: Path, valid_evidence_structure: Path) -> None:
        """Test run command (validate + handoff) in dry-run mode."""
        result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "run",
                "--issue",
                "123",
                "--dry-run",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "QA_EVIDENCE_PATH": str(valid_evidence_structure.parent)},
        )

        assert result.returncode == 0
        assert "Step 1: Validation" in result.stdout
        assert "Step 2: GitHub Hand-off" in result.stdout
        assert "QA Run Completed" in result.stdout

    def test_config_file_loading(
        self, qa_process_v2_script: Path, temp_config_file: Path, valid_evidence_structure: Path
    ) -> None:
        """Test loading configuration from file."""
        # Config file already has the correct evidence_base_path set by fixture
        result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "validate",
                "--issue",
                "123",
                "--config",
                str(temp_config_file),
                "--verbose",
            ],
            capture_output=True,
            text=True,
        )

        # Config should load successfully
        assert result.returncode == 0

    def test_project_number_override(self, qa_process_v2_script: Path, valid_evidence_structure: Path) -> None:
        """Test --project flag overrides default project number."""
        result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "validate",
                "--issue",
                "123",
                "--project",
                "10",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "QA_EVIDENCE_PATH": str(valid_evidence_structure.parent)},
        )

        # Should accept custom project number
        assert result.returncode == 0

    def test_custom_output_path(self, qa_process_v2_script: Path, valid_evidence_structure: Path) -> None:
        """Test validate command with custom output path."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = Path(tmp.name)

        try:
            result = subprocess.run(
                [
                    "python",
                    str(qa_process_v2_script),
                    "validate",
                    "--issue",
                    "123",
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, "QA_EVIDENCE_PATH": str(valid_evidence_structure.parent)},
            )

            assert result.returncode == 0
            assert output_path.exists()

            # Verify output is valid JSON
            with open(output_path) as f:
                report = json.load(f)
                assert "valid" in report
        finally:
            output_path.unlink(missing_ok=True)


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_missing_evidence_base_path(self, qa_process_v2_script: Path) -> None:
        """Test behavior when evidence base path doesn't exist."""
        result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "validate",
                "--issue",
                "999",
            ],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "QA_EVIDENCE_PATH": "/nonexistent/path"},
        )

        # Should fail gracefully
        assert result.returncode == 1

    def test_invalid_issue_number(self, qa_process_v2_script: Path) -> None:
        """Test validation with invalid issue number format."""
        result = subprocess.run(
            ["python", str(qa_process_v2_script), "validate", "--issue", "not-a-number"],
            capture_output=True,
            text=True,
        )

        # Click should handle type validation
        assert result.returncode != 0

    def test_custom_validation_manifest(self, qa_process_v2_script: Path, valid_evidence_structure: Path) -> None:
        """Test validate command with custom manifest (feature for future)."""
        manifest_path = valid_evidence_structure / "qa" / "context_manifest.json"

        result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "validate",
                "--issue",
                "123",
                "--manifest",
                str(manifest_path),
            ],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "QA_EVIDENCE_PATH": str(valid_evidence_structure.parent)},
        )

        # Should accept custom manifest path
        assert result.returncode == 0


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_workflow_valid(self, qa_process_v2_script: Path, valid_evidence_structure: Path) -> None:
        """Test complete workflow: validate -> handoff with valid evidence."""
        base_path = str(valid_evidence_structure.parent)
        env = {**subprocess.os.environ, "QA_EVIDENCE_PATH": base_path}

        # Step 1: Validate
        validate_result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "validate",
                "--issue",
                "123",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert validate_result.returncode == 0
        assert "Validation PASSED" in validate_result.stdout

        # Step 2: Handoff
        handoff_result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "handoff",
                "--issue",
                "123",
                "--dry-run",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert handoff_result.returncode == 0
        assert "Hand-off completed" in handoff_result.stdout

    def test_full_workflow_invalid(self, qa_process_v2_script: Path, invalid_evidence_structure: Path) -> None:
        """Test complete workflow: validate -> handoff with invalid evidence."""
        base_path = str(invalid_evidence_structure.parent)
        env = {**subprocess.os.environ, "QA_EVIDENCE_PATH": base_path}

        # Step 1: Validate (should fail)
        validate_result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "validate",
                "--issue",
                "456",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert validate_result.returncode == 1
        assert "Validation FAILED" in validate_result.stdout

        # Report should still be created for handoff
        report_path = invalid_evidence_structure / "qa" / "validation_report.json"
        assert report_path.exists()

    def test_run_command_creates_report(self, qa_process_v2_script: Path, valid_evidence_structure: Path) -> None:
        """Test run command creates validation report."""
        result = subprocess.run(
            [
                "python",
                str(qa_process_v2_script),
                "run",
                "--issue",
                "123",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, "QA_EVIDENCE_PATH": str(valid_evidence_structure.parent)},
        )

        assert result.returncode == 0

        # Check report was created
        report_path = valid_evidence_structure / "qa" / "validation_report.json"
        assert report_path.exists()

        with open(report_path) as f:
            report = json.load(f)
            assert "valid" in report
            assert "metadata" in report
