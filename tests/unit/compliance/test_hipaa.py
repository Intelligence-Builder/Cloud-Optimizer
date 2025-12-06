"""Unit tests for HIPAA Security Rule compliance framework.

Tests for HIPAA controls.yaml structure and content validation.
"""

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml


class TestHIPAAControlsFile:
    """Test HIPAA controls.yaml file structure and content."""

    @pytest.fixture
    def controls_file(self) -> Path:
        """Get path to HIPAA controls file."""
        return Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "hipaa" / "controls.yaml"

    @pytest.fixture
    def controls_data(self, controls_file: Path) -> Dict[str, Any]:
        """Load and parse HIPAA controls YAML."""
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_controls_file_exists(self, controls_file: Path) -> None:
        """Test that HIPAA controls file exists."""
        assert controls_file.exists(), "HIPAA controls.yaml should exist"

    def test_framework_metadata(self, controls_data: Dict[str, Any]) -> None:
        """Test framework metadata is correct."""
        assert controls_data["framework"] == "HIPAA"
        assert "Health Insurance" in controls_data["description"] or \
               "Security Rule" in controls_data["description"]

    def test_has_controls(self, controls_data: Dict[str, Any]) -> None:
        """Test controls list exists and has items."""
        controls = controls_data.get("controls", [])
        assert len(controls) >= 5, "Should have at least 5 HIPAA controls"

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

    def test_control_ids_format(self, controls_data: Dict[str, Any]) -> None:
        """Test control IDs follow HIPAA CFR format (164.xxx)."""
        for control in controls_data["controls"]:
            control_id = control["control_id"]
            assert control_id.startswith("164."), \
                f"Control ID {control_id} should start with '164.' (CFR reference)"

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


class TestHIPAAControlContent:
    """Test specific HIPAA control content."""

    @pytest.fixture
    def controls_data(self) -> Dict[str, Any]:
        """Load HIPAA controls."""
        controls_file = Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "hipaa" / "controls.yaml"
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_access_control_exists(self, controls_data: Dict[str, Any]) -> None:
        """Test Access Control (164.312(a)(1)) exists."""
        control = next(
            (c for c in controls_data["controls"]
             if "164.312(a)(1)" in c["control_id"]),
            None
        )
        assert control is not None, "Access Control 164.312(a)(1) should exist"
        assert "access" in control["name"].lower()
        services = control.get("aws_services", [])
        assert "IAM" in services, "Should reference IAM"

    def test_audit_controls_exists(self, controls_data: Dict[str, Any]) -> None:
        """Test Audit Controls (164.312(b)) exists."""
        control = next(
            (c for c in controls_data["controls"]
             if "164.312(b)" in c["control_id"]),
            None
        )
        assert control is not None, "Audit Controls 164.312(b) should exist"
        assert "audit" in control["name"].lower()
        services = control.get("aws_services", [])
        assert "CloudTrail" in services, "Should reference CloudTrail"

    def test_integrity_controls_exists(self, controls_data: Dict[str, Any]) -> None:
        """Test Integrity Controls (164.312(c)(1)) exists."""
        control = next(
            (c for c in controls_data["controls"]
             if "164.312(c)(1)" in c["control_id"]),
            None
        )
        assert control is not None, "Integrity Controls 164.312(c)(1) should exist"
        assert "integrity" in control["name"].lower()

    def test_authentication_control_exists(self, controls_data: Dict[str, Any]) -> None:
        """Test Person/Entity Authentication (164.312(d)) exists."""
        control = next(
            (c for c in controls_data["controls"]
             if "164.312(d)" in c["control_id"]),
            None
        )
        assert control is not None, "Authentication 164.312(d) should exist"
        assert "authentication" in control["name"].lower()


class TestHIPAAAWSMappings:
    """Test AWS service mappings in HIPAA controls."""

    @pytest.fixture
    def controls_data(self) -> Dict[str, Any]:
        """Load HIPAA controls."""
        controls_file = Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "hipaa" / "controls.yaml"
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_iam_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test IAM is mapped to access control controls."""
        iam_controls = [
            c for c in controls_data["controls"]
            if "IAM" in c.get("aws_services", [])
        ]
        assert len(iam_controls) >= 1, "IAM should be mapped to access controls"

    def test_cloudtrail_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test CloudTrail is mapped to audit controls."""
        cloudtrail_controls = [
            c for c in controls_data["controls"]
            if "CloudTrail" in c.get("aws_services", [])
        ]
        assert len(cloudtrail_controls) >= 1, "CloudTrail should be mapped to audit controls"

    def test_kms_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test KMS is mapped to encryption controls."""
        kms_controls = [
            c for c in controls_data["controls"]
            if "KMS" in c.get("aws_services", [])
        ]
        assert len(kms_controls) >= 1, "KMS should be mapped to encryption controls"

    def test_s3_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test S3 is mapped to data protection controls."""
        s3_controls = [
            c for c in controls_data["controls"]
            if "S3" in c.get("aws_services", [])
        ]
        assert len(s3_controls) >= 1, "S3 should be mapped to data protection controls"


class TestHIPAAePHIProtection:
    """Test ePHI (electronic Protected Health Information) specific controls."""

    @pytest.fixture
    def controls_data(self) -> Dict[str, Any]:
        """Load HIPAA controls."""
        controls_file = Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "hipaa" / "controls.yaml"
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_ephi_mentioned_in_controls(self, controls_data: Dict[str, Any]) -> None:
        """Test ePHI is mentioned in control descriptions."""
        ephi_controls = [
            c for c in controls_data["controls"]
            if "ePHI" in c.get("description", "") or "PHI" in c.get("description", "")
        ]
        assert len(ephi_controls) >= 3, "Multiple controls should mention ePHI/PHI"

    def test_encryption_requirements(self, controls_data: Dict[str, Any]) -> None:
        """Test encryption requirements are addressed."""
        encryption_controls = [
            c for c in controls_data["controls"]
            if "encrypt" in c.get("description", "").lower() or
               "encrypt" in c.get("implementation_guidance", "").lower()
        ]
        assert len(encryption_controls) >= 1, "Should have controls addressing encryption"
