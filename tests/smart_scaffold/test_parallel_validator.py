"""Smart-Scaffold Parallel Validator Divergence Tests.

Tests the parallel validator's ability to detect divergences between
Smart-Scaffold (SS) and Intelligence-Builder (IB) knowledge graph datasets.

This test suite validates:
1. Missing entity detection
2. Property value mismatch detection
3. Stale data detection (timestamp differences)
4. Relationship divergence detection
5. Complete sync verification (no false positives)

Requirements:
- Smart-Scaffold CLI installed and configured
- Test fixtures in divergent_data_dir
"""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from .conftest import DivergenceScenario, KnowledgeGraphEntry, utc_now_iso


class ParallelValidator:
    """Validates consistency between SS and IB knowledge graphs.

    This is the core validator that compares knowledge graph entries
    from Smart-Scaffold against Intelligence-Builder and reports divergences.
    """

    def __init__(self, ss_data: dict[str, Any], ib_data: dict[str, Any]) -> None:
        """Initialize validator with SS and IB datasets.

        Args:
            ss_data: Smart-Scaffold knowledge graph data
            ib_data: Intelligence-Builder knowledge graph data
        """
        self.ss_data = ss_data
        self.ib_data = ib_data
        self.divergences: list[dict[str, Any]] = []

    def validate(self) -> list[dict[str, Any]]:
        """Run full validation and return divergences.

        Returns:
            List of divergence records with type, entity_id, and details
        """
        self.divergences = []

        # Build lookup maps
        ss_entries = {e["id"]: e for e in self.ss_data.get("entries", [])}
        ib_entries = {e["id"]: e for e in self.ib_data.get("entries", [])}

        # Check for entities missing in IB
        for entity_id, ss_entry in ss_entries.items():
            if entity_id not in ib_entries:
                self.divergences.append(
                    {
                        "type": "missing_in_ib",
                        "entity_id": entity_id,
                        "entity_type": ss_entry.get("entity_type"),
                        "severity": "high",
                    }
                )
            else:
                # Entity exists in both - check for property mismatches
                ib_entry = ib_entries[entity_id]
                self._check_property_mismatches(ss_entry, ib_entry)
                self._check_stale_data(ss_entry, ib_entry)
                self._check_relationship_divergence(ss_entry, ib_entry)

        # Check for entities missing in SS (reverse check)
        for entity_id, ib_entry in ib_entries.items():
            if entity_id not in ss_entries:
                self.divergences.append(
                    {
                        "type": "missing_in_ss",
                        "entity_id": entity_id,
                        "entity_type": ib_entry.get("entity_type"),
                        "severity": "high",
                    }
                )

        return self.divergences

    def _check_property_mismatches(
        self, ss_entry: dict[str, Any], ib_entry: dict[str, Any]
    ) -> None:
        """Check for property value mismatches between entries.

        Args:
            ss_entry: Smart-Scaffold entry
            ib_entry: Intelligence-Builder entry
        """
        ss_props = ss_entry.get("properties", {})
        ib_props = ib_entry.get("properties", {})

        # Skip relationship properties (handled separately)
        skip_keys = {"connected_subnets", "relationships", "related_entities"}

        for key, ss_value in ss_props.items():
            if key in skip_keys:
                continue
            if key in ib_props:
                ib_value = ib_props[key]
                if ss_value != ib_value:
                    severity = self._determine_mismatch_severity(
                        key, ss_value, ib_value
                    )
                    self.divergences.append(
                        {
                            "type": "property_mismatch",
                            "entity_id": ss_entry["id"],
                            "property": key,
                            "ss_value": ss_value,
                            "ib_value": ib_value,
                            "severity": severity,
                        }
                    )

    def _check_stale_data(
        self, ss_entry: dict[str, Any], ib_entry: dict[str, Any]
    ) -> None:
        """Check for timestamp divergence indicating stale data.

        Args:
            ss_entry: Smart-Scaffold entry
            ib_entry: Intelligence-Builder entry
        """
        ss_timestamp = ss_entry.get("timestamp")
        ib_timestamp = ib_entry.get("timestamp")

        if not ss_timestamp or not ib_timestamp:
            return

        try:
            ss_dt = datetime.fromisoformat(ss_timestamp.replace("Z", "+00:00"))
            ib_dt = datetime.fromisoformat(ib_timestamp.replace("Z", "+00:00"))

            stale_threshold = timedelta(days=7)  # Consider data stale after 7 days
            if ss_dt - ib_dt > stale_threshold:
                stale_days = (ss_dt - ib_dt).days
                self.divergences.append(
                    {
                        "type": "stale_data",
                        "entity_id": ss_entry["id"],
                        "ss_timestamp": ss_timestamp,
                        "ib_timestamp": ib_timestamp,
                        "stale_days": stale_days,
                        "severity": "medium" if stale_days < 30 else "high",
                    }
                )
        except (ValueError, TypeError):
            pass  # Invalid timestamp format

    def _check_relationship_divergence(
        self, ss_entry: dict[str, Any], ib_entry: dict[str, Any]
    ) -> None:
        """Check for divergence in entity relationships.

        Args:
            ss_entry: Smart-Scaffold entry
            ib_entry: Intelligence-Builder entry
        """
        relationship_keys = {"connected_subnets", "relationships", "related_entities"}

        ss_props = ss_entry.get("properties", {})
        ib_props = ib_entry.get("properties", {})

        for key in relationship_keys:
            if key in ss_props and key in ib_props:
                ss_related = (
                    set(ss_props[key]) if isinstance(ss_props[key], list) else set()
                )
                ib_related = (
                    set(ib_props[key]) if isinstance(ib_props[key], list) else set()
                )

                if ss_related != ib_related:
                    missing_in_ib = list(ss_related - ib_related)
                    missing_in_ss = list(ib_related - ss_related)

                    if missing_in_ib or missing_in_ss:
                        self.divergences.append(
                            {
                                "type": "relationship_divergence",
                                "entity_id": ss_entry["id"],
                                "relationship": key,
                                "ss_related": list(ss_related),
                                "ib_related": list(ib_related),
                                "missing_in_ib": missing_in_ib,
                                "missing_in_ss": missing_in_ss,
                                "severity": "medium",
                            }
                        )

    def _determine_mismatch_severity(
        self, property_name: str, ss_value: Any, ib_value: Any
    ) -> str:
        """Determine severity of a property mismatch.

        Args:
            property_name: Name of the mismatched property
            ss_value: Value in Smart-Scaffold
            ib_value: Value in Intelligence-Builder

        Returns:
            Severity level: 'low', 'medium', or 'high'
        """
        critical_properties = {"status", "severity", "encryption", "public_access"}
        important_properties = {"region", "instance_type", "runtime", "version"}

        if property_name in critical_properties:
            return "high"
        elif property_name in important_properties:
            return "medium"
        return "low"

    def get_summary(self) -> dict[str, Any]:
        """Get summary of validation results.

        Returns:
            Summary dict with counts by type and severity
        """
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}

        for div in self.divergences:
            div_type = div.get("type", "unknown")
            severity = div.get("severity", "unknown")

            by_type[div_type] = by_type.get(div_type, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "total_divergences": len(self.divergences),
            "by_type": by_type,
            "by_severity": by_severity,
            "is_in_sync": len(self.divergences) == 0,
        }


class TestParallelValidatorDivergence:
    """Test suite for parallel validator divergence detection."""

    def test_missing_entity_detection(
        self,
        divergent_data_dir: Path,
        scenario_missing_entity: DivergenceScenario,
    ) -> None:
        """Test detection of entities missing from IB."""
        from .conftest import create_divergent_fixture_files

        ss_path, ib_path = create_divergent_fixture_files(
            divergent_data_dir, scenario_missing_entity
        )

        ss_data = json.loads(ss_path.read_text())
        ib_data = json.loads(ib_path.read_text())

        validator = ParallelValidator(ss_data, ib_data)
        divergences = validator.validate()

        # Should detect missing entity
        missing_divergences = [d for d in divergences if d["type"] == "missing_in_ib"]
        assert len(missing_divergences) >= 1

        # Verify specific missing entity
        missing_ids = [d["entity_id"] for d in missing_divergences]
        assert "aws-ec2-instance-001" in missing_ids

        # Verify expected divergence matches
        expected = scenario_missing_entity.expected_divergences[0]
        actual = next(
            d for d in missing_divergences if d["entity_id"] == expected["entity_id"]
        )
        assert actual["entity_type"] == expected["entity_type"]
        assert actual["severity"] == expected["severity"]

    def test_property_mismatch_detection(
        self,
        divergent_data_dir: Path,
        scenario_property_mismatch: DivergenceScenario,
    ) -> None:
        """Test detection of property value mismatches."""
        from .conftest import create_divergent_fixture_files

        ss_path, ib_path = create_divergent_fixture_files(
            divergent_data_dir, scenario_property_mismatch
        )

        ss_data = json.loads(ss_path.read_text())
        ib_data = json.loads(ib_path.read_text())

        validator = ParallelValidator(ss_data, ib_data)
        divergences = validator.validate()

        # Should detect property mismatches
        mismatch_divergences = [
            d for d in divergences if d["type"] == "property_mismatch"
        ]
        assert len(mismatch_divergences) >= 2

        # Verify severity mismatch detected
        severity_mismatch = next(
            (d for d in mismatch_divergences if d["property"] == "severity"),
            None,
        )
        assert severity_mismatch is not None
        assert severity_mismatch["ss_value"] == "critical"
        assert severity_mismatch["ib_value"] == "high"

        # Verify status mismatch detected
        status_mismatch = next(
            (d for d in mismatch_divergences if d["property"] == "status"),
            None,
        )
        assert status_mismatch is not None
        assert status_mismatch["ss_value"] == "open"
        assert status_mismatch["ib_value"] == "resolved"
        assert status_mismatch["severity"] == "high"  # Status is critical

    def test_stale_data_detection(
        self,
        divergent_data_dir: Path,
        scenario_stale_data: DivergenceScenario,
    ) -> None:
        """Test detection of stale data based on timestamps."""
        from .conftest import create_divergent_fixture_files

        ss_path, ib_path = create_divergent_fixture_files(
            divergent_data_dir, scenario_stale_data
        )

        ss_data = json.loads(ss_path.read_text())
        ib_data = json.loads(ib_path.read_text())

        validator = ParallelValidator(ss_data, ib_data)
        divergences = validator.validate()

        # Should detect stale data
        stale_divergences = [d for d in divergences if d["type"] == "stale_data"]
        assert len(stale_divergences) >= 1

        # Verify stale days calculation
        stale = stale_divergences[0]
        assert stale["stale_days"] >= 30

    def test_relationship_divergence_detection(
        self,
        divergent_data_dir: Path,
        scenario_relationship_divergence: DivergenceScenario,
    ) -> None:
        """Test detection of relationship divergences."""
        from .conftest import create_divergent_fixture_files

        ss_path, ib_path = create_divergent_fixture_files(
            divergent_data_dir, scenario_relationship_divergence
        )

        ss_data = json.loads(ss_path.read_text())
        ib_data = json.loads(ib_path.read_text())

        validator = ParallelValidator(ss_data, ib_data)
        divergences = validator.validate()

        # Should detect relationship divergence
        rel_divergences = [
            d for d in divergences if d["type"] == "relationship_divergence"
        ]
        assert len(rel_divergences) >= 1

        # Verify missing relationship detected
        rel_div = rel_divergences[0]
        assert "subnet-003" in rel_div["missing_in_ib"]
        assert rel_div["relationship"] == "connected_subnets"

    def test_complete_sync_no_false_positives(
        self,
        divergent_data_dir: Path,
        scenario_complete_sync: DivergenceScenario,
    ) -> None:
        """Test that synced data produces no divergences (no false positives)."""
        from .conftest import create_divergent_fixture_files

        ss_path, ib_path = create_divergent_fixture_files(
            divergent_data_dir, scenario_complete_sync
        )

        ss_data = json.loads(ss_path.read_text())
        ib_data = json.loads(ib_path.read_text())

        validator = ParallelValidator(ss_data, ib_data)
        divergences = validator.validate()

        # Should have no divergences
        assert len(divergences) == 0

        # Summary should show in sync
        summary = validator.get_summary()
        assert summary["is_in_sync"] is True
        assert summary["total_divergences"] == 0

    def test_validator_summary_stats(
        self,
        divergent_data_dir: Path,
        scenario_property_mismatch: DivergenceScenario,
    ) -> None:
        """Test validator summary statistics."""
        from .conftest import create_divergent_fixture_files

        ss_path, ib_path = create_divergent_fixture_files(
            divergent_data_dir, scenario_property_mismatch
        )

        ss_data = json.loads(ss_path.read_text())
        ib_data = json.loads(ib_path.read_text())

        validator = ParallelValidator(ss_data, ib_data)
        validator.validate()

        summary = validator.get_summary()

        assert "total_divergences" in summary
        assert "by_type" in summary
        assert "by_severity" in summary
        assert "is_in_sync" in summary

        assert summary["total_divergences"] > 0
        assert summary["is_in_sync"] is False
        assert "property_mismatch" in summary["by_type"]


class TestSmartScaffoldCLIIntegration:
    """Integration tests using Smart-Scaffold CLI.

    These tests require the smart-scaffold CLI to be installed and configured.
    """

    @pytest.mark.skipif(
        not subprocess.run(["which", "smart-scaffold"], capture_output=True).returncode
        == 0,
        reason="smart-scaffold CLI not installed",
    )
    def test_smart_scaffold_ukg_query(self) -> None:
        """Test smart-scaffold UKG query functionality."""
        result = subprocess.run(
            ["smart-scaffold", "ukg", "stats"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should complete (may fail if not configured, but should run)
        assert result.returncode in [0, 1]  # Success or graceful failure

    @pytest.mark.skipif(
        not subprocess.run(["which", "smart-scaffold"], capture_output=True).returncode
        == 0,
        reason="smart-scaffold CLI not installed",
    )
    def test_smart_scaffold_analyze(self, divergent_data_dir: Path) -> None:
        """Test smart-scaffold analyze command."""
        result = subprocess.run(
            ["smart-scaffold", "analyze", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Help should always work
        assert result.returncode == 0
        assert "analyze" in result.stdout.lower()


class TestValidatorEdgeCases:
    """Edge case tests for the parallel validator."""

    def test_empty_ss_data(self) -> None:
        """Test validation with empty SS data."""
        ss_data = {"source": "smart_scaffold", "entries": []}
        ib_data = {
            "source": "intelligence_builder",
            "entries": [
                {
                    "id": "test-001",
                    "entity_type": "test",
                    "name": "test",
                    "properties": {},
                    "timestamp": utc_now_iso(),
                }
            ],
        }

        validator = ParallelValidator(ss_data, ib_data)
        divergences = validator.validate()

        # Should detect entity missing in SS
        assert len(divergences) == 1
        assert divergences[0]["type"] == "missing_in_ss"

    def test_empty_ib_data(self) -> None:
        """Test validation with empty IB data."""
        ss_data = {
            "source": "smart_scaffold",
            "entries": [
                {
                    "id": "test-001",
                    "entity_type": "test",
                    "name": "test",
                    "properties": {},
                    "timestamp": utc_now_iso(),
                }
            ],
        }
        ib_data = {"source": "intelligence_builder", "entries": []}

        validator = ParallelValidator(ss_data, ib_data)
        divergences = validator.validate()

        # Should detect entity missing in IB
        assert len(divergences) == 1
        assert divergences[0]["type"] == "missing_in_ib"

    def test_both_empty(self) -> None:
        """Test validation with both datasets empty."""
        ss_data = {"source": "smart_scaffold", "entries": []}
        ib_data = {"source": "intelligence_builder", "entries": []}

        validator = ParallelValidator(ss_data, ib_data)
        divergences = validator.validate()

        # Should have no divergences
        assert len(divergences) == 0
        assert validator.get_summary()["is_in_sync"] is True

    def test_invalid_timestamp_format(self) -> None:
        """Test handling of invalid timestamp formats."""
        ss_data = {
            "source": "smart_scaffold",
            "entries": [
                {
                    "id": "test-001",
                    "entity_type": "test",
                    "name": "test",
                    "properties": {},
                    "timestamp": "invalid-timestamp",
                }
            ],
        }
        ib_data = {
            "source": "intelligence_builder",
            "entries": [
                {
                    "id": "test-001",
                    "entity_type": "test",
                    "name": "test",
                    "properties": {},
                    "timestamp": "also-invalid",
                }
            ],
        }

        validator = ParallelValidator(ss_data, ib_data)
        divergences = validator.validate()

        # Should not crash, should not report stale data for invalid timestamps
        stale_divergences = [d for d in divergences if d["type"] == "stale_data"]
        assert len(stale_divergences) == 0

    def test_missing_properties(self) -> None:
        """Test handling of entries with missing properties."""
        ss_data = {
            "source": "smart_scaffold",
            "entries": [
                {
                    "id": "test-001",
                    "entity_type": "test",
                    "name": "test",
                    # No properties key
                    "timestamp": utc_now_iso(),
                }
            ],
        }
        ib_data = {
            "source": "intelligence_builder",
            "entries": [
                {
                    "id": "test-001",
                    "entity_type": "test",
                    "name": "test",
                    "properties": {"key": "value"},
                    "timestamp": utc_now_iso(),
                }
            ],
        }

        validator = ParallelValidator(ss_data, ib_data)
        # Should not crash
        divergences = validator.validate()
        assert isinstance(divergences, list)

    def test_nested_properties(self) -> None:
        """Test handling of nested property structures."""
        ss_data = {
            "source": "smart_scaffold",
            "entries": [
                {
                    "id": "test-001",
                    "entity_type": "test",
                    "name": "test",
                    "properties": {
                        "config": {"nested": {"deep": "value"}},
                        "list_prop": [1, 2, 3],
                    },
                    "timestamp": utc_now_iso(),
                }
            ],
        }
        ib_data = {
            "source": "intelligence_builder",
            "entries": [
                {
                    "id": "test-001",
                    "entity_type": "test",
                    "name": "test",
                    "properties": {
                        "config": {"nested": {"deep": "different"}},  # Different value
                        "list_prop": [1, 2, 3],  # Same
                    },
                    "timestamp": utc_now_iso(),
                }
            ],
        }

        validator = ParallelValidator(ss_data, ib_data)
        divergences = validator.validate()

        # Should detect nested property mismatch
        config_mismatch = [d for d in divergences if d.get("property") == "config"]
        assert len(config_mismatch) == 1


class TestValidatorPerformance:
    """Performance tests for the parallel validator."""

    def test_large_dataset_performance(self) -> None:
        """Test validator performance with large datasets."""
        import time

        # Generate large dataset
        num_entries = 1000
        timestamp = utc_now_iso()

        entries = [
            {
                "id": f"entity-{i:05d}",
                "entity_type": "test_entity",
                "name": f"Test Entity {i}",
                "properties": {
                    "index": i,
                    "category": f"cat-{i % 10}",
                    "status": "active" if i % 2 == 0 else "inactive",
                },
                "timestamp": timestamp,
            }
            for i in range(num_entries)
        ]

        ss_data = {"source": "smart_scaffold", "entries": entries}

        # Create IB data with some divergences
        ib_entries = entries.copy()
        # Remove some entries to create missing_in_ib divergences
        ib_entries = [e for e in ib_entries if int(e["id"].split("-")[1]) % 100 != 0]
        # Modify some properties
        for e in ib_entries:
            if int(e["id"].split("-")[1]) % 50 == 0:
                e["properties"]["status"] = "modified"

        ib_data = {"source": "intelligence_builder", "entries": ib_entries}

        # Time the validation
        start = time.time()
        validator = ParallelValidator(ss_data, ib_data)
        divergences = validator.validate()
        elapsed = time.time() - start

        # Should complete in reasonable time (< 5 seconds for 1000 entries)
        assert elapsed < 5.0, f"Validation took {elapsed:.2f}s, expected < 5s"

        # Should detect expected divergences
        assert len(divergences) > 0
        summary = validator.get_summary()
        assert summary["total_divergences"] > 0
