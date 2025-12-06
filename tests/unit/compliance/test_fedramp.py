"""Unit tests for FedRAMP compliance framework.

Issue #153: 10.1.1 Add FedRAMP compliance framework.
Tests for FedRAMP controls.yaml structure and content validation.
"""

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml


class TestFedRAMPControlsFile:
    """Test FedRAMP controls.yaml file structure and content."""

    @pytest.fixture
    def controls_file(self) -> Path:
        """Get path to FedRAMP controls file."""
        return Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "fedramp" / "controls.yaml"

    @pytest.fixture
    def controls_data(self, controls_file: Path) -> Dict[str, Any]:
        """Load and parse FedRAMP controls YAML."""
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_controls_file_exists(self, controls_file: Path) -> None:
        """Test that FedRAMP controls file exists."""
        assert controls_file.exists(), "FedRAMP controls.yaml should exist"

    def test_framework_metadata(self, controls_data: Dict[str, Any]) -> None:
        """Test framework metadata is correct."""
        assert controls_data["framework"] == "FedRAMP"
        assert "Rev5" in controls_data["version"]
        assert "Federal Risk" in controls_data["description"]
        assert controls_data["total_controls"] == 421

    def test_baselines_defined(self, controls_data: Dict[str, Any]) -> None:
        """Test Low, Moderate, High baselines are defined."""
        baselines = controls_data.get("baselines", {})
        assert "low" in baselines
        assert "moderate" in baselines
        assert "high" in baselines
        assert baselines["low"] == 125
        assert baselines["moderate"] == 325
        assert baselines["high"] == 421

    def test_control_families_defined(self, controls_data: Dict[str, Any]) -> None:
        """Test all 18 control families are defined."""
        families = controls_data.get("control_families", [])
        assert len(families) == 18, "Should have 18 control families"

        family_ids = [f["id"] for f in families]
        required_families = ["AC", "AU", "AT", "CM", "CP", "IA", "IR", "MA",
                            "MP", "PS", "PE", "PL", "RA", "CA", "SC", "SI", "SA", "PM"]
        for fam in required_families:
            assert fam in family_ids, f"Missing control family: {fam}"

    def test_has_controls(self, controls_data: Dict[str, Any]) -> None:
        """Test controls list exists and has items."""
        controls = controls_data.get("controls", [])
        assert len(controls) >= 20, "Should have at least 20 sample controls"

    def test_control_structure(self, controls_data: Dict[str, Any]) -> None:
        """Test each control has required fields."""
        required_fields = ["control_id", "name", "family", "description"]

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
        """Test control IDs follow NIST 800-53 format (XX-N)."""
        import re
        pattern = re.compile(r"^[A-Z]{2}-\d+$")

        for control in controls_data["controls"]:
            control_id = control["control_id"]
            assert pattern.match(control_id), \
                f"Control ID {control_id} should match format XX-N (e.g., AC-2)"

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


class TestFedRAMPControlFamilies:
    """Test FedRAMP control family coverage."""

    @pytest.fixture
    def controls_data(self) -> Dict[str, Any]:
        """Load FedRAMP controls."""
        controls_file = Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "fedramp" / "controls.yaml"
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_access_control_family(self, controls_data: Dict[str, Any]) -> None:
        """Test Access Control (AC) family controls exist."""
        ac_controls = [c for c in controls_data["controls"]
                       if c["family"] == "AC"]
        assert len(ac_controls) >= 5, "Should have multiple AC controls"

    def test_audit_accountability_family(self, controls_data: Dict[str, Any]) -> None:
        """Test Audit and Accountability (AU) family controls exist."""
        au_controls = [c for c in controls_data["controls"]
                       if c["family"] == "AU"]
        assert len(au_controls) >= 4, "Should have multiple AU controls"

    def test_configuration_management_family(self, controls_data: Dict[str, Any]) -> None:
        """Test Configuration Management (CM) family controls exist."""
        cm_controls = [c for c in controls_data["controls"]
                       if c["family"] == "CM"]
        assert len(cm_controls) >= 3, "Should have multiple CM controls"

    def test_incident_response_family(self, controls_data: Dict[str, Any]) -> None:
        """Test Incident Response (IR) family controls exist."""
        ir_controls = [c for c in controls_data["controls"]
                       if c["family"] == "IR"]
        assert len(ir_controls) >= 2, "Should have multiple IR controls"

    def test_system_communications_family(self, controls_data: Dict[str, Any]) -> None:
        """Test System and Communications Protection (SC) family controls exist."""
        sc_controls = [c for c in controls_data["controls"]
                       if c["family"] == "SC"]
        assert len(sc_controls) >= 5, "Should have multiple SC controls"

    def test_system_integrity_family(self, controls_data: Dict[str, Any]) -> None:
        """Test System and Information Integrity (SI) family controls exist."""
        si_controls = [c for c in controls_data["controls"]
                       if c["family"] == "SI"]
        assert len(si_controls) >= 3, "Should have multiple SI controls"


class TestFedRAMPControlContent:
    """Test specific FedRAMP control content."""

    @pytest.fixture
    def controls_data(self) -> Dict[str, Any]:
        """Load FedRAMP controls."""
        controls_file = Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "fedramp" / "controls.yaml"
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_ac2_account_management(self, controls_data: Dict[str, Any]) -> None:
        """Test AC-2 Account Management control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "AC-2"),
            None
        )
        assert control is not None, "AC-2 control should exist"
        assert "account" in control["name"].lower()
        services = control.get("aws_services", [])
        assert "IAM" in services, "AC-2 should reference IAM"

    def test_ac6_least_privilege(self, controls_data: Dict[str, Any]) -> None:
        """Test AC-6 Least Privilege control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "AC-6"),
            None
        )
        assert control is not None, "AC-6 control should exist"
        assert "privilege" in control["name"].lower()
        services = control.get("aws_services", [])
        assert "IAM" in services or "IAM Access Analyzer" in services

    def test_au2_event_logging(self, controls_data: Dict[str, Any]) -> None:
        """Test AU-2 Event Logging control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "AU-2"),
            None
        )
        assert control is not None, "AU-2 control should exist"
        assert "logging" in control["name"].lower() or "event" in control["name"].lower()
        services = control.get("aws_services", [])
        assert "CloudTrail" in services, "AU-2 should reference CloudTrail"

    def test_sc7_boundary_protection(self, controls_data: Dict[str, Any]) -> None:
        """Test SC-7 Boundary Protection control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "SC-7"),
            None
        )
        assert control is not None, "SC-7 control should exist"
        assert "boundary" in control["name"].lower()
        services = control.get("aws_services", [])
        assert "VPC" in services or "Security Groups" in services

    def test_sc13_cryptographic_protection(self, controls_data: Dict[str, Any]) -> None:
        """Test SC-13 Cryptographic Protection control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "SC-13"),
            None
        )
        assert control is not None, "SC-13 control should exist"
        assert "cryptographic" in control["name"].lower()
        services = control.get("aws_services", [])
        assert "KMS" in services, "SC-13 should reference KMS"

    def test_si2_flaw_remediation(self, controls_data: Dict[str, Any]) -> None:
        """Test SI-2 Flaw Remediation control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "SI-2"),
            None
        )
        assert control is not None, "SI-2 control should exist"
        assert "flaw" in control["name"].lower() or "remediation" in control["name"].lower()


class TestFedRAMPAWSMappings:
    """Test AWS service mappings in FedRAMP controls."""

    @pytest.fixture
    def controls_data(self) -> Dict[str, Any]:
        """Load FedRAMP controls."""
        controls_file = Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "fedramp" / "controls.yaml"
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_iam_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test IAM is mapped to access control controls."""
        iam_controls = [
            c for c in controls_data["controls"]
            if "IAM" in c.get("aws_services", [])
        ]
        assert len(iam_controls) >= 5, "IAM should be mapped to many controls"

    def test_cloudtrail_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test CloudTrail is mapped to audit controls."""
        cloudtrail_controls = [
            c for c in controls_data["controls"]
            if "CloudTrail" in c.get("aws_services", [])
        ]
        assert len(cloudtrail_controls) >= 3, "CloudTrail should be mapped to audit controls"

    def test_kms_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test KMS is mapped to cryptographic controls."""
        kms_controls = [
            c for c in controls_data["controls"]
            if "KMS" in c.get("aws_services", [])
        ]
        assert len(kms_controls) >= 3, "KMS should be mapped to crypto controls"

    def test_vpc_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test VPC is mapped to network controls."""
        vpc_controls = [
            c for c in controls_data["controls"]
            if "VPC" in c.get("aws_services", [])
        ]
        assert len(vpc_controls) >= 2, "VPC should be mapped to network controls"

    def test_guardduty_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test GuardDuty is mapped to monitoring controls."""
        guardduty_controls = [
            c for c in controls_data["controls"]
            if "GuardDuty" in c.get("aws_services", [])
        ]
        assert len(guardduty_controls) >= 3, "GuardDuty should be mapped to monitoring controls"

    def test_security_hub_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test Security Hub is mapped to security controls."""
        security_hub_controls = [
            c for c in controls_data["controls"]
            if "Security Hub" in c.get("aws_services", [])
        ]
        assert len(security_hub_controls) >= 3, \
            "Security Hub should be mapped to security controls"
