"""Unit tests for ISO 27001:2022 compliance framework.

Issue #157: ISO 27001 compliance framework.
"""

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml


class TestISO27001ControlsFile:
    """Test ISO 27001 controls.yaml file structure and content."""

    @pytest.fixture
    def controls_file(self) -> Path:
        """Get path to ISO 27001 controls file."""
        return Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "iso27001" / "controls.yaml"

    @pytest.fixture
    def controls_data(self, controls_file: Path) -> Dict[str, Any]:
        """Load and parse ISO 27001 controls YAML."""
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_controls_file_exists(self, controls_file: Path) -> None:
        """Test that ISO 27001 controls file exists."""
        assert controls_file.exists(), "ISO 27001 controls.yaml should exist"

    def test_framework_metadata(self, controls_data: Dict[str, Any]) -> None:
        """Test framework metadata is correct."""
        assert controls_data["framework"] == "ISO27001"
        assert controls_data["version"] == "2022"
        assert "27001" in controls_data["description"]
        assert controls_data["total_controls"] == 93

    def test_has_all_domains(self, controls_data: Dict[str, Any]) -> None:
        """Test all 4 control domains are present."""
        domains = controls_data["domains"]
        assert len(domains) == 4, "Should have 4 control domains"

        domain_ids = [d["id"] for d in domains]
        assert "A.5" in domain_ids, "Should have Organizational Controls (A.5)"
        assert "A.6" in domain_ids, "Should have People Controls (A.6)"
        assert "A.7" in domain_ids, "Should have Physical Controls (A.7)"
        assert "A.8" in domain_ids, "Should have Technological Controls (A.8)"

    def test_domain_control_counts(self, controls_data: Dict[str, Any]) -> None:
        """Test each domain has correct control count."""
        domains = {d["id"]: d for d in controls_data["domains"]}

        assert domains["A.5"]["control_count"] == 37, "A.5 should have 37 controls"
        assert domains["A.6"]["control_count"] == 8, "A.6 should have 8 controls"
        assert domains["A.7"]["control_count"] == 14, "A.7 should have 14 controls"
        assert domains["A.8"]["control_count"] == 34, "A.8 should have 34 controls"

    def test_total_controls_count(self, controls_data: Dict[str, Any]) -> None:
        """Test total control count matches expected 93."""
        controls = controls_data["controls"]
        assert len(controls) == 93, f"Should have 93 controls, found {len(controls)}"

    def test_organizational_controls_count(self, controls_data: Dict[str, Any]) -> None:
        """Test A.5 Organizational Controls count."""
        controls = [c for c in controls_data["controls"]
                    if c["control_id"].startswith("A.5")]
        assert len(controls) == 37, f"A.5 should have 37 controls, found {len(controls)}"

    def test_people_controls_count(self, controls_data: Dict[str, Any]) -> None:
        """Test A.6 People Controls count."""
        controls = [c for c in controls_data["controls"]
                    if c["control_id"].startswith("A.6")]
        assert len(controls) == 8, f"A.6 should have 8 controls, found {len(controls)}"

    def test_physical_controls_count(self, controls_data: Dict[str, Any]) -> None:
        """Test A.7 Physical Controls count."""
        controls = [c for c in controls_data["controls"]
                    if c["control_id"].startswith("A.7")]
        assert len(controls) == 14, f"A.7 should have 14 controls, found {len(controls)}"

    def test_technological_controls_count(self, controls_data: Dict[str, Any]) -> None:
        """Test A.8 Technological Controls count."""
        controls = [c for c in controls_data["controls"]
                    if c["control_id"].startswith("A.8")]
        assert len(controls) == 34, f"A.8 should have 34 controls, found {len(controls)}"

    def test_control_structure(self, controls_data: Dict[str, Any]) -> None:
        """Test each control has required fields."""
        required_fields = ["control_id", "name", "domain", "description"]

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
        """Test control IDs follow A.X.Y format."""
        import re
        pattern = re.compile(r"^A\.[5-8]\.\d+$")

        for control in controls_data["controls"]:
            assert pattern.match(control["control_id"]), \
                f"Control ID {control['control_id']} should match A.X.Y format"

    def test_domains_match_control_domains(self, controls_data: Dict[str, Any]) -> None:
        """Test control domains match declared domain types."""
        valid_domains = {"Organizational", "People", "Physical", "Technological"}

        for control in controls_data["controls"]:
            assert control["domain"] in valid_domains, \
                f"Control {control['control_id']} has invalid domain {control['domain']}"

    def test_aws_services_present(self, controls_data: Dict[str, Any]) -> None:
        """Test most controls have AWS service mappings."""
        controls_with_services = [
            c for c in controls_data["controls"]
            if c.get("aws_services") and len(c["aws_services"]) > 0
        ]
        # Most controls should have AWS mappings (allow some physical controls to not have any)
        coverage = len(controls_with_services) / len(controls_data["controls"])
        assert coverage >= 0.85, f"AWS service coverage {coverage:.0%} should be >= 85%"

    def test_implementation_guidance_present(self, controls_data: Dict[str, Any]) -> None:
        """Test controls have implementation guidance."""
        controls_with_guidance = [
            c for c in controls_data["controls"]
            if c.get("implementation_guidance") and len(c["implementation_guidance"]) > 50
        ]
        coverage = len(controls_with_guidance) / len(controls_data["controls"])
        assert coverage >= 0.95, f"Guidance coverage {coverage:.0%} should be >= 95%"


class TestISO27001ControlContent:
    """Test specific ISO 27001 control content."""

    @pytest.fixture
    def controls_data(self) -> Dict[str, Any]:
        """Load ISO 27001 controls."""
        controls_file = Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "iso27001" / "controls.yaml"
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_a51_policies_control(self, controls_data: Dict[str, Any]) -> None:
        """Test A.5.1 Policies for information security control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "A.5.1"),
            None
        )
        assert control is not None, "A.5.1 control should exist"
        assert "polic" in control["name"].lower()  # matches policy/policies
        assert control["domain"] == "Organizational"

    def test_a63_training_control(self, controls_data: Dict[str, Any]) -> None:
        """Test A.6.3 Security awareness training control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "A.6.3"),
            None
        )
        assert control is not None, "A.6.3 control should exist"
        assert "training" in control["name"].lower() or "awareness" in control["name"].lower()
        assert control["domain"] == "People"

    def test_a71_physical_perimeters_control(self, controls_data: Dict[str, Any]) -> None:
        """Test A.7.1 Physical security perimeters control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "A.7.1"),
            None
        )
        assert control is not None, "A.7.1 control should exist"
        assert "physical" in control["name"].lower()
        assert control["domain"] == "Physical"

    def test_a824_cryptography_control(self, controls_data: Dict[str, Any]) -> None:
        """Test A.8.24 Use of cryptography control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "A.8.24"),
            None
        )
        assert control is not None, "A.8.24 control should exist"
        assert "cryptography" in control["name"].lower()
        assert control["domain"] == "Technological"
        # Should reference AWS KMS
        assert "KMS" in control.get("aws_services", [])

    def test_a815_logging_control(self, controls_data: Dict[str, Any]) -> None:
        """Test A.8.15 Logging control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "A.8.15"),
            None
        )
        assert control is not None, "A.8.15 control should exist"
        assert "logging" in control["name"].lower()
        # Should reference CloudWatch and CloudTrail
        services = control.get("aws_services", [])
        assert "CloudWatch Logs" in services or "CloudTrail" in services

    def test_a527_learning_from_incidents_control(self, controls_data: Dict[str, Any]) -> None:
        """Test A.5.27 Learning from incidents control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "A.5.27"),
            None
        )
        assert control is not None, "A.5.27 control should exist"
        assert "incident" in control["name"].lower()

    def test_a832_change_management_control(self, controls_data: Dict[str, Any]) -> None:
        """Test A.8.32 Change management control."""
        control = next(
            (c for c in controls_data["controls"] if c["control_id"] == "A.8.32"),
            None
        )
        assert control is not None, "A.8.32 control should exist"
        assert "change" in control["name"].lower()
        # Should reference CloudFormation or similar
        services = control.get("aws_services", [])
        assert "CloudFormation" in services or "CodePipeline" in services


class TestISO27001AWServiceMappings:
    """Test AWS service mappings in ISO 27001 controls."""

    @pytest.fixture
    def controls_data(self) -> Dict[str, Any]:
        """Load ISO 27001 controls."""
        controls_file = Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "iso27001" / "controls.yaml"
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_iam_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test IAM is mapped to access control-related controls."""
        iam_controls = [
            c for c in controls_data["controls"]
            if "IAM" in c.get("aws_services", [])
        ]
        assert len(iam_controls) >= 10, "IAM should be mapped to many controls"

    def test_cloudtrail_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test CloudTrail is mapped to audit-related controls."""
        cloudtrail_controls = [
            c for c in controls_data["controls"]
            if "CloudTrail" in c.get("aws_services", [])
        ]
        assert len(cloudtrail_controls) >= 5, "CloudTrail should be mapped to audit controls"

    def test_guardduty_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test GuardDuty is mapped to threat detection controls."""
        guardduty_controls = [
            c for c in controls_data["controls"]
            if "GuardDuty" in c.get("aws_services", [])
        ]
        assert len(guardduty_controls) >= 3, "GuardDuty should be mapped to threat controls"

    def test_kms_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test KMS is mapped to cryptography controls."""
        kms_controls = [
            c for c in controls_data["controls"]
            if "KMS" in c.get("aws_services", [])
        ]
        assert len(kms_controls) >= 3, "KMS should be mapped to crypto controls"

    def test_config_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test AWS Config is mapped to configuration controls."""
        config_controls = [
            c for c in controls_data["controls"]
            if "AWS Config" in c.get("aws_services", [])
        ]
        assert len(config_controls) >= 3, "AWS Config should be mapped to config controls"

    def test_security_hub_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test Security Hub is mapped to monitoring controls."""
        security_hub_controls = [
            c for c in controls_data["controls"]
            if "Security Hub" in c.get("aws_services", [])
        ]
        assert len(security_hub_controls) >= 5, \
            "Security Hub should be mapped to security controls"

    def test_vpc_mappings(self, controls_data: Dict[str, Any]) -> None:
        """Test VPC is mapped to network controls."""
        vpc_controls = [
            c for c in controls_data["controls"]
            if "VPC" in c.get("aws_services", [])
        ]
        assert len(vpc_controls) >= 3, "VPC should be mapped to network controls"


class TestISO27001DomainCoverage:
    """Test ISO 27001 domain coverage and organization."""

    @pytest.fixture
    def controls_data(self) -> Dict[str, Any]:
        """Load ISO 27001 controls."""
        controls_file = Path(__file__).parent.parent.parent.parent / \
            "data" / "compliance" / "frameworks" / "iso27001" / "controls.yaml"
        with open(controls_file, "r") as f:
            return yaml.safe_load(f)

    def test_organizational_domain_topics(self, controls_data: Dict[str, Any]) -> None:
        """Test A.5 Organizational controls cover key topics."""
        org_controls = [
            c for c in controls_data["controls"]
            if c["control_id"].startswith("A.5")
        ]
        names = " ".join(c["name"].lower() for c in org_controls)

        # Key organizational topics
        assert "polic" in names, "Should cover policies"  # matches policy/policies
        assert "access" in names, "Should cover access control"
        assert "incident" in names, "Should cover incident management"
        assert "supplier" in names, "Should cover supplier management"

    def test_people_domain_topics(self, controls_data: Dict[str, Any]) -> None:
        """Test A.6 People controls cover key topics."""
        people_controls = [
            c for c in controls_data["controls"]
            if c["control_id"].startswith("A.6")
        ]
        names = " ".join(c["name"].lower() for c in people_controls)

        # Key people topics
        assert "screening" in names or "background" in names, "Should cover screening"
        assert "training" in names or "awareness" in names, "Should cover training"
        assert "termination" in names or "employment" in names, "Should cover employment"

    def test_physical_domain_topics(self, controls_data: Dict[str, Any]) -> None:
        """Test A.7 Physical controls cover key topics."""
        physical_controls = [
            c for c in controls_data["controls"]
            if c["control_id"].startswith("A.7")
        ]
        names = " ".join(c["name"].lower() for c in physical_controls)

        # Key physical topics
        assert "perimeter" in names, "Should cover physical perimeters"
        assert "entry" in names, "Should cover physical entry"
        assert "equipment" in names or "device" in names, "Should cover equipment"

    def test_technological_domain_topics(self, controls_data: Dict[str, Any]) -> None:
        """Test A.8 Technological controls cover key topics."""
        tech_controls = [
            c for c in controls_data["controls"]
            if c["control_id"].startswith("A.8")
        ]
        names = " ".join(c["name"].lower() for c in tech_controls)

        # Key technological topics
        assert "authentication" in names, "Should cover authentication"
        assert "cryptography" in names or "encryption" in names, "Should cover cryptography"
        assert "logging" in names, "Should cover logging"
        assert "network" in names, "Should cover network security"
        assert "backup" in names, "Should cover backup"
        assert "development" in names or "coding" in names, "Should cover secure development"
