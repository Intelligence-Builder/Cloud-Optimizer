"""Unit tests for PCI-DSS 4.0 compliance framework.

Tests for PCI-DSS controls.yaml structure and content validation.
"""

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml


class TestPCIDSSControlsFile:
    """Test PCI-DSS controls.yaml file structure and content."""

    @pytest.fixture
    def controls_file(self) -> Path:
        """Get path to PCI-DSS controls file."""
        return Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "pci-dss" / "controls.yaml"

    @pytest.fixture
    def controls_data(self, controls_file: Path) -> Dict[str, Any]:
        """Load and parse PCI-DSS controls YAML."""
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_controls_file_exists(self, controls_file: Path) -> None:
        """Test that PCI-DSS controls file exists."""
        assert controls_file.exists(), "PCI-DSS controls.yaml should exist"

    def test_framework_metadata(self, controls_data: Dict[str, Any]) -> None:
        """Test framework metadata is correct."""
        assert controls_data["framework"] == "PCI-DSS"
        assert controls_data["version"] == "4.0"
        assert "Payment Card Industry" in controls_data["description"]

    def test_has_controls(self, controls_data: Dict[str, Any]) -> None:
        """Test controls list exists and has items."""
        controls = controls_data.get("controls", [])
        assert len(controls) >= 8, "Should have at least 8 controls"

    def test_control_structure(self, controls_data: Dict[str, Any]) -> None:
        """Test each control has required fields."""
        required_fields = ["control_id", "name", "description"]

        for control in controls_data["controls"]:
            for field in required_fields:
                assert field in control, \
                    f"Control {control.get('control_id', 'unknown')} missing {field}"

    def test_control_ids_unique(self, controls_data: Dict[str, Any]) -> None:
        """Test all control IDs are unique."""
        control_ids = [c["control_id"] for c in controls_data["controls"]]
        assert len(control_ids) == len(set(control_ids)), \
            "Control IDs should be unique"

    def test_aws_services_present(self, controls_data: Dict[str, Any]) -> None:
        """Test controls have AWS service mappings."""
        controls_with_services = [
            c for c in controls_data["controls"]
            if c.get("aws_services") and len(c["aws_services"]) > 0
        ]
        coverage = len(controls_with_services) / len(controls_data["controls"])
        assert coverage >= 0.90, f"AWS service coverage {coverage:.0%} should be >= 90%"

    def test_implementation_guidance_present(self, controls_data: Dict[str, Any]) -> None:
        """Test controls have implementation guidance."""
        controls_with_guidance = [
            c for c in controls_data["controls"]
            if c.get("implementation_guidance") and len(c["implementation_guidance"]) > 50
        ]
        coverage = len(controls_with_guidance) / len(controls_data["controls"])
        assert coverage >= 0.90, f"Guidance coverage {coverage:.0%} should be >= 90%"


class TestPCIDSSControlContent:
    """Test specific PCI-DSS control content."""

    @pytest.fixture
    def controls_data(self) -> Dict[str, Any]:
        """Load PCI-DSS controls."""
        controls_file = Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "pci-dss" / "controls.yaml"
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_network_security_control(self, controls_data: Dict[str, Any]) -> None:
        """Test network security control exists (Requirement 1)."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "1.2.1"),
            None
        )
        assert control is not None, "Network security control 1.2.1 should exist"
        assert "network" in control["name"].lower()
        services = control.get("aws_services", [])
        assert "VPC" in services or "Security Groups" in services

    def test_secure_config_control(self, controls_data: Dict[str, Any]) -> None:
        """Test secure configuration control exists (Requirement 2)."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "2.2.1"),
            None
        )
        assert control is not None, "Secure config control 2.2.1 should exist"
        assert "configuration" in control["name"].lower()

    def test_data_protection_control(self, controls_data: Dict[str, Any]) -> None:
        """Test cardholder data protection control exists (Requirement 3)."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "3.3.1"),
            None
        )
        assert control is not None, "Data protection control 3.3.1 should exist"
        services = control.get("aws_services", [])
        assert "KMS" in services, "Should reference AWS KMS"


class TestPCIDSSAWSMappings:
    """Test AWS service mappings in PCI-DSS controls."""

    @pytest.fixture
    def controls_data(self) -> Dict[str, Any]:
        """Load PCI-DSS controls."""
        controls_file = Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "pci-dss" / "controls.yaml"
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_kms_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test KMS is mapped to encryption controls."""
        kms_controls = [
            c for c in controls_data["controls"]
            if "KMS" in c.get("aws_services", [])
        ]
        assert len(kms_controls) >= 1, "KMS should be mapped to encryption controls"

    def test_vpc_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test VPC is mapped to network controls."""
        vpc_controls = [
            c for c in controls_data["controls"]
            if "VPC" in c.get("aws_services", [])
        ]
        assert len(vpc_controls) >= 1, "VPC should be mapped to network controls"

    def test_cloudtrail_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test CloudTrail is mapped to audit controls."""
        cloudtrail_controls = [
            c for c in controls_data["controls"]
            if "CloudTrail" in c.get("aws_services", [])
        ]
        assert len(cloudtrail_controls) >= 1, "CloudTrail should be mapped to audit controls"
