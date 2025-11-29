"""Tests for SecurityDomain implementation."""

import pytest

from ib_platform.domains.security.domain import SecurityDomain


class TestSecurityDomain:
    """Tests for SecurityDomain."""

    def test_domain_name_is_security(self, security_domain: SecurityDomain) -> None:
        """Test that domain name is 'security'."""
        assert security_domain.name == "security"

    def test_has_9_entity_types(self, security_domain: SecurityDomain) -> None:
        """Test that domain has exactly 9 entity types."""
        assert len(security_domain.entity_types) == 9

        entity_names = {et.name for et in security_domain.entity_types}
        expected = {
            "vulnerability",
            "threat",
            "control",
            "compliance_requirement",
            "encryption_config",
            "access_policy",
            "security_group",
            "security_finding",
            "identity",
        }
        assert entity_names == expected

    def test_has_7_relationship_types(self, security_domain: SecurityDomain) -> None:
        """Test that domain has exactly 7 relationship types."""
        assert len(security_domain.relationship_types) == 7

        rel_names = {rt.name for rt in security_domain.relationship_types}
        expected = {
            "mitigates",
            "exposes",
            "requires",
            "implements",
            "violates",
            "protects",
            "grants_access",
        }
        assert rel_names == expected

    def test_vulnerability_requires_name(self, security_domain: SecurityDomain) -> None:
        """Test that vulnerability entity requires name."""
        vuln_type = next(
            et for et in security_domain.entity_types if et.name == "vulnerability"
        )
        assert "name" in vuln_type.required_properties

    def test_control_requires_name_and_type(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test that control entity requires name and control_type."""
        control_type = next(
            et for et in security_domain.entity_types if et.name == "control"
        )
        assert "name" in control_type.required_properties
        assert "control_type" in control_type.required_properties

    def test_security_finding_requires_severity(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test that security_finding requires severity."""
        finding_type = next(
            et for et in security_domain.entity_types if et.name == "security_finding"
        )
        assert "severity" in finding_type.required_properties

    def test_mitigates_only_from_control(self, security_domain: SecurityDomain) -> None:
        """Test that mitigates relationship only from control."""
        mitigates = next(
            rt for rt in security_domain.relationship_types if rt.name == "mitigates"
        )
        assert mitigates.valid_source_types == ["control"]
        assert "vulnerability" in mitigates.valid_target_types
        assert "threat" in mitigates.valid_target_types

    def test_grants_access_only_to_identity(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test that grants_access relationship only to identity."""
        grants_access = next(
            rt
            for rt in security_domain.relationship_types
            if rt.name == "grants_access"
        )
        assert grants_access.valid_source_types == ["access_policy"]
        assert grants_access.valid_target_types == ["identity"]

    def test_validate_valid_vulnerability(
        self, security_domain: SecurityDomain, sample_vulnerability_data: dict
    ) -> None:
        """Test validating valid vulnerability data."""
        errors = security_domain.validate_entity(
            "vulnerability", sample_vulnerability_data
        )
        assert len(errors) == 0

    def test_validate_missing_required_property(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for missing required property."""
        errors = security_domain.validate_entity("vulnerability", {})
        assert len(errors) > 0
        assert any("name" in error for error in errors)

    def test_validate_valid_control(
        self, security_domain: SecurityDomain, sample_control_data: dict
    ) -> None:
        """Test validating valid control data."""
        errors = security_domain.validate_entity("control", sample_control_data)
        assert len(errors) == 0

    def test_validate_control_missing_type(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test control validation fails without control_type."""
        errors = security_domain.validate_entity("control", {"name": "Test Control"})
        assert len(errors) > 0
        assert any("control_type" in error for error in errors)

    def test_validate_mitigates_relationship(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validating mitigates relationship."""
        # Valid relationship
        errors = security_domain.validate_relationship(
            "mitigates", "control", "vulnerability"
        )
        assert len(errors) == 0

        # Invalid source type
        errors = security_domain.validate_relationship(
            "mitigates", "threat", "vulnerability"
        )
        assert len(errors) > 0
        assert any("Invalid source type" in error for error in errors)

    def test_validate_grants_access_relationship(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validating grants_access relationship."""
        # Valid relationship
        errors = security_domain.validate_relationship(
            "grants_access", "access_policy", "identity"
        )
        assert len(errors) == 0

        # Invalid target type
        errors = security_domain.validate_relationship(
            "grants_access", "access_policy", "vulnerability"
        )
        assert len(errors) > 0

    def test_domain_has_no_dependencies(self, security_domain: SecurityDomain) -> None:
        """Test that security domain has no dependencies."""
        assert security_domain.depends_on == []

    def test_supported_operations(self, security_domain: SecurityDomain) -> None:
        """Test that domain lists supported operations."""
        operations = security_domain.get_supported_operations()
        assert len(operations) == 4
        assert "find_unmitigated_vulnerabilities" in operations
        assert "check_compliance_coverage" in operations
        assert "trace_access_path" in operations
        assert "find_encryption_gaps" in operations

    @pytest.mark.asyncio
    async def test_execute_operation(self, security_domain: SecurityDomain) -> None:
        """Test executing domain operations."""
        result = await security_domain.execute_operation(
            "find_unmitigated_vulnerabilities", {"severity": "critical"}
        )
        assert result is not None
        assert result["operation"] == "find_unmitigated_vulnerabilities"

    @pytest.mark.asyncio
    async def test_execute_unknown_operation(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test executing unknown operation raises error."""
        with pytest.raises(NotImplementedError):
            await security_domain.execute_operation("unknown_op", {})

    def test_entity_type_descriptions(self, security_domain: SecurityDomain) -> None:
        """Test that all entity types have descriptions."""
        for entity_type in security_domain.entity_types:
            assert entity_type.description
            assert len(entity_type.description) > 0

    def test_relationship_type_descriptions(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test that all relationship types have descriptions."""
        for rel_type in security_domain.relationship_types:
            assert rel_type.description
            assert len(rel_type.description) > 0
