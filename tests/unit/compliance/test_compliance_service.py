"""Unit tests for compliance service.

Issue #157: ISO 27001 compliance framework.
"""

import pytest

from cloud_optimizer.services.compliance import COMPLIANCE_DATA


class TestComplianceData:
    """Test compliance framework data."""

    def test_iso27001_in_compliance_data(self) -> None:
        """Test ISO27001 is included in compliance data."""
        assert "ISO27001" in COMPLIANCE_DATA, "ISO27001 should be in COMPLIANCE_DATA"

    def test_iso27001_display_name(self) -> None:
        """Test ISO27001 has correct display name."""
        iso_data = COMPLIANCE_DATA.get("ISO27001", {})
        assert iso_data.get("display_name") == "ISO/IEC 27001:2022"

    def test_iso27001_version(self) -> None:
        """Test ISO27001 has correct version."""
        iso_data = COMPLIANCE_DATA.get("ISO27001", {})
        assert iso_data.get("version") == "2022"

    def test_iso27001_description(self) -> None:
        """Test ISO27001 has meaningful description."""
        iso_data = COMPLIANCE_DATA.get("ISO27001", {})
        description = iso_data.get("description", "")
        assert "ISMS" in description or "Information Security" in description

    def test_all_frameworks_present(self) -> None:
        """Test all expected frameworks are present."""
        expected_frameworks = [
            "CIS",
            "PCI-DSS",
            "HIPAA",
            "SOC2",
            "NIST",
            "GDPR",
            "ISO27001",
        ]
        for framework in expected_frameworks:
            assert framework in COMPLIANCE_DATA, f"{framework} should be in COMPLIANCE_DATA"

    def test_framework_structure(self) -> None:
        """Test all frameworks have required fields."""
        required_fields = ["display_name", "version", "description"]

        for framework_name, framework_data in COMPLIANCE_DATA.items():
            for field in required_fields:
                assert field in framework_data, \
                    f"{framework_name} missing required field: {field}"

    def test_iso27001_not_empty(self) -> None:
        """Test ISO27001 data is not empty."""
        iso_data = COMPLIANCE_DATA.get("ISO27001", {})
        assert len(iso_data) >= 3, "ISO27001 should have at least 3 fields"


class TestComplianceFrameworkCount:
    """Test compliance framework count."""

    def test_minimum_frameworks(self) -> None:
        """Test minimum number of frameworks are defined."""
        assert len(COMPLIANCE_DATA) >= 7, "Should have at least 7 frameworks"

    def test_framework_versions_not_empty(self) -> None:
        """Test all framework versions are not empty."""
        for name, data in COMPLIANCE_DATA.items():
            assert data.get("version"), f"{name} version should not be empty"
            assert len(data["version"]) > 0, f"{name} version should not be empty string"

    def test_framework_descriptions_meaningful(self) -> None:
        """Test all framework descriptions are meaningful."""
        for name, data in COMPLIANCE_DATA.items():
            desc = data.get("description", "")
            assert len(desc) >= 10, f"{name} description should be meaningful"


class TestISO27001Integration:
    """Test ISO27001 integration with compliance service."""

    def test_iso27001_can_be_queried(self) -> None:
        """Test ISO27001 can be queried from COMPLIANCE_DATA."""
        iso_data = COMPLIANCE_DATA.get("ISO27001")
        assert iso_data is not None
        assert isinstance(iso_data, dict)

    def test_iso27001_fields_types(self) -> None:
        """Test ISO27001 fields have correct types."""
        iso_data = COMPLIANCE_DATA.get("ISO27001", {})

        assert isinstance(iso_data.get("display_name"), str)
        assert isinstance(iso_data.get("version"), str)
        assert isinstance(iso_data.get("description"), str)

    def test_iso27001_version_is_2022(self) -> None:
        """Test ISO27001 version is specifically 2022."""
        iso_data = COMPLIANCE_DATA.get("ISO27001", {})
        version = iso_data.get("version", "")
        assert "2022" in version, "ISO27001 should be 2022 version"
