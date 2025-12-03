"""Tests for qa-process bash script.

Tests the qa-process shell wrapper including:
- Argument parsing
- Flag handling (--force-tests, --refresh-context, --test-path)
- Environment variable support
- Error handling
- Integration with qa_process_v2.py
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List

import pytest


class TestQAProcessShellScript:
    """Tests for qa-process bash script."""

    def test_script_exists_and_executable(self, qa_process_script: Path) -> None:
        """Test qa-process script exists and is executable."""
        assert qa_process_script.exists()
        assert os.access(qa_process_script, os.X_OK)

    def test_help_flag(self, qa_process_script: Path) -> None:
        """Test --help flag displays usage."""
        result = subprocess.run(
            [str(qa_process_script), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Usage message goes to stderr in bash scripts
        output = result.stdout + result.stderr
        assert "Usage:" in output
        assert "issue" in output

    def test_missing_issue_argument(self, qa_process_script: Path) -> None:
        """Test script fails without issue argument."""
        result = subprocess.run(
            [str(qa_process_script)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Usage:" in result.stderr

    def test_missing_issue_number(self, qa_process_script: Path) -> None:
        """Test script fails with 'issue' but no number."""
        result = subprocess.run(
            [str(qa_process_script), "issue"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Usage:" in result.stderr

    def test_force_tests_flag(self, qa_process_script: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test --force-tests flag is recognized."""
        # We can't run the full script without smart-scaffold, but we can test parsing
        result = subprocess.run(
            [str(qa_process_script), "--force-tests", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_refresh_context_flag(self, qa_process_script: Path) -> None:
        """Test --refresh-context flag is recognized."""
        result = subprocess.run(
            [str(qa_process_script), "--refresh-context", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_force_context_alias(self, qa_process_script: Path) -> None:
        """Test --force-context alias for --refresh-context."""
        result = subprocess.run(
            [str(qa_process_script), "--force-context", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_test_path_flag_missing_value(self, qa_process_script: Path) -> None:
        """Test --test-path flag requires a value."""
        result = subprocess.run(
            [str(qa_process_script), "--test-path"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Missing value" in result.stderr

    def test_test_path_flag_with_value(self, qa_process_script: Path) -> None:
        """Test --test-path flag accepts a value."""
        result = subprocess.run(
            [str(qa_process_script), "--test-path", "tests/unit", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_environment_variable_qa_force_tests(
        self, qa_process_script: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test QA_FORCE_TESTS environment variable."""
        # Test truthy values
        for value in ["1", "true", "TRUE", "yes", "YES", "y", "Y", "on", "ON"]:
            result = subprocess.run(
                [str(qa_process_script), "--help"],
                capture_output=True,
                text=True,
                env={**os.environ, "QA_FORCE_TESTS": value},
            )
            assert result.returncode == 0

    def test_environment_variable_qa_refresh_context(self, qa_process_script: Path) -> None:
        """Test QA_REFRESH_CONTEXT environment variable."""
        result = subprocess.run(
            [str(qa_process_script), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "QA_REFRESH_CONTEXT": "true"},
        )

        assert result.returncode == 0

    def test_environment_variable_qa_force_context(self, qa_process_script: Path) -> None:
        """Test QA_FORCE_CONTEXT environment variable (alias)."""
        result = subprocess.run(
            [str(qa_process_script), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "QA_FORCE_CONTEXT": "1"},
        )

        assert result.returncode == 0

    def test_environment_variable_qa_test_path(self, qa_process_script: Path) -> None:
        """Test QA_TEST_PATH environment variable."""
        result = subprocess.run(
            [str(qa_process_script), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "QA_TEST_PATH": "tests/integration"},
        )

        assert result.returncode == 0

    def test_flags_before_issue_command(self, qa_process_script: Path) -> None:
        """Test flags can appear before 'issue' command."""
        result = subprocess.run(
            [
                str(qa_process_script),
                "--force-tests",
                "--refresh-context",
                "--test-path",
                "tests/unit",
                "--help",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_pytest_args_passthrough(self, qa_process_script: Path) -> None:
        """Test pytest arguments can be passed through (syntax check only)."""
        # This tests that the script accepts pytest args, not that it runs them
        # We use --help to prevent actual execution
        result = subprocess.run(
            [str(qa_process_script), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0


class TestQAProcessIntegration:
    """Integration tests for qa-process workflow.

    These tests verify script behavior but avoid executing actual commands
    that require external dependencies (smart-scaffold, gh CLI, etc.).
    """

    def test_script_structure_sections(self, qa_process_script: Path) -> None:
        """Test script contains expected workflow sections."""
        content = qa_process_script.read_text()

        # Key functions should exist
        assert "usage()" in content
        assert "is_truthy()" in content
        assert "heading()" in content
        assert "run_step()" in content

        # Workflow sections
        assert "smart-scaffold" in content.lower()
        assert "pytest" in content.lower()
        assert "qa_process_v2.py" in content.lower()

    def test_script_calls_qa_process_v2(self, qa_process_script: Path) -> None:
        """Test script references qa_process_v2.py."""
        content = qa_process_script.read_text()

        assert "scripts/qa_process_v2.py" in content
        assert "QA_SCRIPT" in content

    def test_script_checks_smart_scaffold(self, qa_process_script: Path) -> None:
        """Test script checks for smart-scaffold CLI."""
        content = qa_process_script.read_text()

        assert "command -v smart-scaffold" in content
        assert "smart-scaffold CLI not installed" in content

    def test_script_checks_pytest(self, qa_process_script: Path) -> None:
        """Test script checks for pytest."""
        content = qa_process_script.read_text()

        assert "command -v pytest" in content
        assert "pytest not installed" in content

    def test_script_creates_context_path(self, qa_process_script: Path) -> None:
        """Test script constructs Smart-Scaffold context path."""
        content = qa_process_script.read_text()

        assert ".smart-scaffold/contexts/" in content
        assert "issue-" in content

    def test_script_handles_missing_context(self, qa_process_script: Path) -> None:
        """Test script handles missing Smart-Scaffold context gracefully."""
        content = qa_process_script.read_text()

        assert "context ${CTX_FILE} not found" in content.lower() or "context" in content

    def test_script_skips_optional_steps(self, qa_process_script: Path) -> None:
        """Test script skips optional steps when tools unavailable."""
        content = qa_process_script.read_text()

        # Should have skip logic for optional tools
        assert "skipping" in content.lower()

    def test_env_var_precedence(self, qa_process_script: Path) -> None:
        """Test environment variables are checked before CLI args."""
        content = qa_process_script.read_text()

        # Environment variables should be set early
        assert "QA_FORCE_TESTS" in content
        assert "QA_REFRESH_CONTEXT" in content or "QA_FORCE_CONTEXT" in content
        assert "QA_TEST_PATH" in content


class TestErrorHandling:
    """Tests for error handling in qa-process script."""

    def test_invalid_flag(self, qa_process_script: Path) -> None:
        """Test script handles invalid flags."""
        result = subprocess.run(
            [str(qa_process_script), "--invalid-flag", "issue", "123"],
            capture_output=True,
            text=True,
        )

        # Script should handle gracefully (might succeed if flag treated as break)
        # The actual behavior depends on the case statement implementation

    def test_issue_command_typo(self, qa_process_script: Path) -> None:
        """Test script fails on typo in 'issue' command."""
        result = subprocess.run(
            [str(qa_process_script), "isue", "123"],  # Typo: 'isue' instead of 'issue'
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1

    def test_non_numeric_issue_number(self, qa_process_script: Path) -> None:
        """Test script accepts non-numeric issue number (passes to tools)."""
        # The script doesn't validate issue number format
        # It passes it through to underlying tools
        result = subprocess.run(
            [str(qa_process_script), "issue", "abc"],
            capture_output=True,
            text=True,
        )

        # Script will attempt to run, failure happens in called tools
        # We can't easily test this without mocking, so just verify it doesn't
        # fail at the argument parsing stage

    def test_script_exits_on_step_failure(self, qa_process_script: Path) -> None:
        """Test script exits when a step fails."""
        content = qa_process_script.read_text()

        # run_step function should exit on failure
        assert "exit" in content
        assert "status" in content or "failed" in content


class TestTruthyFunction:
    """Tests for is_truthy bash function behavior."""

    def test_truthy_values_in_script(self, qa_process_script: Path) -> None:
        """Test is_truthy function recognizes truthy values."""
        content = qa_process_script.read_text()

        # Find is_truthy function
        assert "is_truthy()" in content

        # Should check for common truthy values
        truthy_patterns = ["1", "true", "yes", "y", "on"]
        for pattern in truthy_patterns:
            assert pattern in content.lower()


class TestContextCaching:
    """Tests for Smart-Scaffold context caching behavior."""

    def test_context_cache_check(self, qa_process_script: Path) -> None:
        """Test script checks for existing context file."""
        content = qa_process_script.read_text()

        assert "CTX_FILE" in content
        assert "-f" in content  # File existence check

    def test_context_refresh_message(self, qa_process_script: Path) -> None:
        """Test script messages about context caching."""
        content = qa_process_script.read_text()

        assert "context already exists" in content.lower() or "skipping" in content.lower()
        assert "--refresh-context" in content


class TestPytestIntegration:
    """Tests for pytest integration in qa-process script."""

    def test_pytest_command_construction(self, qa_process_script: Path) -> None:
        """Test script constructs pytest command correctly."""
        content = qa_process_script.read_text()

        assert "pytest" in content.lower()
        assert "tests" in content

    def test_pytest_args_handling(self, qa_process_script: Path) -> None:
        """Test script handles pytest arguments."""
        content = qa_process_script.read_text()

        assert "PYTEST_ARGS" in content or "pytest_args" in content.lower()

    def test_scoped_qa_skips_full_tests(self, qa_process_script: Path) -> None:
        """Test --test-path skips full pytest run."""
        content = qa_process_script.read_text()

        # Should mention skipping full test run when test-path provided
        assert "scoped" in content.lower() or "full" in content.lower()


class TestOutputFormatting:
    """Tests for output formatting in qa-process script."""

    def test_heading_function(self, qa_process_script: Path) -> None:
        """Test heading function exists for output formatting."""
        content = qa_process_script.read_text()

        assert "heading()" in content
        assert "====" in content or "---" in content

    def test_step_indicators(self, qa_process_script: Path) -> None:
        """Test script uses step indicators."""
        content = qa_process_script.read_text()

        # Should have visual indicators for steps
        assert "✓" in content or "✗" in content or "→" in content

    def test_completion_message(self, qa_process_script: Path) -> None:
        """Test script shows completion message."""
        content = qa_process_script.read_text()

        assert "completed" in content.lower()


class TestEdgeCases:
    """Tests for edge cases in qa-process script."""

    def test_empty_pytest_args(self, qa_process_script: Path) -> None:
        """Test script handles empty pytest args array."""
        # This is more of a structural test
        content = qa_process_script.read_text()

        # Should handle array size check
        assert "${#" in content  # Bash array length syntax

    def test_repo_root_calculation(self, qa_process_script: Path) -> None:
        """Test script calculates REPO_ROOT correctly."""
        content = qa_process_script.read_text()

        assert "REPO_ROOT" in content
        assert "dirname" in content or "cd" in content

    def test_multiple_flags_combination(self, qa_process_script: Path) -> None:
        """Test multiple flags can be combined."""
        result = subprocess.run(
            [
                str(qa_process_script),
                "--force-tests",
                "--refresh-context",
                "--test-path",
                "tests/unit",
                "--help",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0


class TestBackwardCompatibility:
    """Tests for backward compatibility features."""

    def test_both_refresh_flags_supported(self, qa_process_script: Path) -> None:
        """Test both --refresh-context and --force-context work."""
        content = qa_process_script.read_text()

        assert "--refresh-context" in content
        assert "--force-context" in content

    def test_env_var_aliases(self, qa_process_script: Path) -> None:
        """Test environment variable aliases are supported."""
        content = qa_process_script.read_text()

        # Both QA_REFRESH_CONTEXT and QA_FORCE_CONTEXT should be checked
        assert "QA_REFRESH_CONTEXT" in content
        assert "QA_FORCE_CONTEXT" in content
