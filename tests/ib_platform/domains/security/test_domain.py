"""Comprehensive tests for SecurityDomain implementation.

This module tests all 9 entity types and 7 relationship types defined
in the SecurityDomain, including validation of required properties and
valid source/target constraints.
"""

import logging
from typing import Any, Dict

import pytest

from ib_platform.domains.base import BaseDomain
from ib_platform.domains.security.domain import SecurityDomain

logger = logging.getLogger(__name__)


class TestSecurityDomainBasicProperties:
    """Test basic domain properties and metadata."""

    def test_domain_name_is_security(self, security_domain: SecurityDomain) -> None:
        """Test that domain name is 'security'."""
        assert security_domain.name == "security"

    def test_domain_display_name(self, security_domain: SecurityDomain) -> None:
        """Test domain display name is set correctly."""
        assert security_domain.display_name == "Security & Compliance"

    def test_domain_version(self, security_domain: SecurityDomain) -> None:
        """Test domain version is set."""
        assert security_domain.version == "1.0.0"

    def test_inherits_from_base_domain(self, security_domain: SecurityDomain) -> None:
        """Test that SecurityDomain inherits from BaseDomain."""
        assert isinstance(security_domain, BaseDomain)

    def test_domain_has_no_dependencies(self, security_domain: SecurityDomain) -> None:
        """Test that security domain has no dependencies."""
        assert security_domain.depends_on == []


class TestSecurityDomainEntityTypes:
    """Test all 9 entity types and their properties."""

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

    def test_vulnerability_entity_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test vulnerability entity type has correct properties."""
        vuln_type = next(
            et for et in security_domain.entity_types if et.name == "vulnerability"
        )
        assert vuln_type.description == "Security vulnerability (CVE, etc.)"
        assert vuln_type.required_properties == ["name"]
        assert "cve_id" in vuln_type.optional_properties
        assert "severity" in vuln_type.optional_properties
        assert "cvss_score" in vuln_type.optional_properties

    def test_threat_entity_definition(self, security_domain: SecurityDomain) -> None:
        """Test threat entity type has correct properties."""
        threat_type = next(
            et for et in security_domain.entity_types if et.name == "threat"
        )
        assert threat_type.description == "Threat actor or attack vector"
        assert threat_type.required_properties == ["name"]
        assert "threat_type" in threat_type.optional_properties
        assert "description" in threat_type.optional_properties

    def test_control_entity_definition(self, security_domain: SecurityDomain) -> None:
        """Test control entity type has correct properties."""
        control_type = next(
            et for et in security_domain.entity_types if et.name == "control"
        )
        assert (
            control_type.description
            == "Security control (preventive, detective, corrective)"
        )
        assert "name" in control_type.required_properties
        assert "control_type" in control_type.required_properties
        assert "implementation_status" in control_type.optional_properties

    def test_compliance_requirement_entity_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test compliance_requirement entity type has correct properties."""
        comp_type = next(
            et
            for et in security_domain.entity_types
            if et.name == "compliance_requirement"
        )
        assert comp_type.description == "Compliance requirement (SOC2, HIPAA, etc.)"
        assert "name" in comp_type.required_properties
        assert "framework" in comp_type.required_properties
        assert "control_family" in comp_type.optional_properties

    def test_encryption_config_entity_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test encryption_config entity type has correct properties."""
        enc_type = next(
            et for et in security_domain.entity_types if et.name == "encryption_config"
        )
        assert enc_type.description == "Encryption configuration"
        assert "name" in enc_type.required_properties
        assert "algorithm" in enc_type.required_properties
        assert "key_length" in enc_type.optional_properties

    def test_access_policy_entity_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test access_policy entity type has correct properties."""
        policy_type = next(
            et for et in security_domain.entity_types if et.name == "access_policy"
        )
        assert policy_type.description == "IAM policy or access rule"
        assert policy_type.required_properties == ["name"]
        assert "policy_type" in policy_type.optional_properties
        assert "principals" in policy_type.optional_properties

    def test_security_group_entity_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test security_group entity type has correct properties."""
        sg_type = next(
            et for et in security_domain.entity_types if et.name == "security_group"
        )
        assert sg_type.description == "Network security group or firewall rule"
        assert sg_type.required_properties == ["name"]
        assert "ingress_rules" in sg_type.optional_properties
        assert "egress_rules" in sg_type.optional_properties

    def test_security_finding_entity_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test security_finding entity type has correct properties."""
        finding_type = next(
            et for et in security_domain.entity_types if et.name == "security_finding"
        )
        assert finding_type.description == "Security scan finding or alert"
        assert "name" in finding_type.required_properties
        assert "severity" in finding_type.required_properties
        assert "finding_type" in finding_type.optional_properties

    def test_identity_entity_definition(self, security_domain: SecurityDomain) -> None:
        """Test identity entity type has correct properties."""
        identity_type = next(
            et for et in security_domain.entity_types if et.name == "identity"
        )
        assert identity_type.description == "User, role, or service account"
        assert "name" in identity_type.required_properties
        assert "identity_type" in identity_type.required_properties
        assert "arn" in identity_type.optional_properties
        assert "mfa_enabled" in identity_type.optional_properties


class TestSecurityDomainRelationshipTypes:
    """Test all 7 relationship types and their constraints."""

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

    def test_mitigates_relationship_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test mitigates relationship has correct source/target types."""
        mitigates = next(
            rt for rt in security_domain.relationship_types if rt.name == "mitigates"
        )
        assert mitigates.description == "Control mitigates vulnerability or threat"
        assert mitigates.valid_source_types == ["control"]
        assert "vulnerability" in mitigates.valid_target_types
        assert "threat" in mitigates.valid_target_types
        assert "effectiveness" in mitigates.properties
        assert "implementation_date" in mitigates.properties

    def test_exposes_relationship_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test exposes relationship has correct source/target types."""
        exposes = next(
            rt for rt in security_domain.relationship_types if rt.name == "exposes"
        )
        assert exposes.description == "Configuration exposes to vulnerability or threat"
        assert "encryption_config" in exposes.valid_source_types
        assert "access_policy" in exposes.valid_source_types
        assert "security_group" in exposes.valid_source_types
        assert "vulnerability" in exposes.valid_target_types
        assert "threat" in exposes.valid_target_types
        assert "risk_level" in exposes.properties

    def test_requires_relationship_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test requires relationship has correct source/target types."""
        requires = next(
            rt for rt in security_domain.relationship_types if rt.name == "requires"
        )
        assert requires.description == "Entity requires compliance requirement"
        assert "control" in requires.valid_source_types
        assert "encryption_config" in requires.valid_source_types
        assert "access_policy" in requires.valid_source_types
        assert requires.valid_target_types == ["compliance_requirement"]

    def test_implements_relationship_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test implements relationship has correct source/target types."""
        implements = next(
            rt for rt in security_domain.relationship_types if rt.name == "implements"
        )
        assert implements.description == "Control implements compliance requirement"
        assert implements.valid_source_types == ["control"]
        assert implements.valid_target_types == ["compliance_requirement"]
        assert "coverage_percentage" in implements.properties

    def test_violates_relationship_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test violates relationship has correct source/target types."""
        violates = next(
            rt for rt in security_domain.relationship_types if rt.name == "violates"
        )
        assert violates.description == "Finding violates policy or requirement"
        assert violates.valid_source_types == ["security_finding"]
        assert "access_policy" in violates.valid_target_types
        assert "compliance_requirement" in violates.valid_target_types

    def test_protects_relationship_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test protects relationship has correct source/target types."""
        protects = next(
            rt for rt in security_domain.relationship_types if rt.name == "protects"
        )
        assert protects.description == "Control or encryption protects resource"
        assert "control" in protects.valid_source_types
        assert "encryption_config" in protects.valid_source_types
        assert "security_group" in protects.valid_source_types
        assert "identity" in protects.valid_target_types
        assert "security_group" in protects.valid_target_types

    def test_grants_access_relationship_definition(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test grants_access relationship has correct source/target types."""
        grants_access = next(
            rt
            for rt in security_domain.relationship_types
            if rt.name == "grants_access"
        )
        assert grants_access.description == "Policy grants access to identity"
        assert grants_access.valid_source_types == ["access_policy"]
        assert grants_access.valid_target_types == ["identity"]
        assert "permission_level" in grants_access.properties


class TestSecurityDomainEntityValidation:
    """Test entity validation enforces required properties."""

    def test_validate_vulnerability_with_required_properties(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation passes for vulnerability with required properties."""
        errors = security_domain.validate_entity(
            "vulnerability", {"name": "CVE-2021-44228"}
        )
        assert len(errors) == 0

    def test_validate_vulnerability_missing_name(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for vulnerability without name."""
        errors = security_domain.validate_entity("vulnerability", {})
        assert len(errors) > 0
        assert any("name" in error for error in errors)

    def test_validate_control_with_all_required(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation passes for control with all required properties."""
        errors = security_domain.validate_entity(
            "control", {"name": "WAF", "control_type": "preventive"}
        )
        assert len(errors) == 0

    def test_validate_control_missing_name(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for control without name."""
        errors = security_domain.validate_entity(
            "control", {"control_type": "preventive"}
        )
        assert len(errors) > 0
        assert any("name" in error for error in errors)

    def test_validate_control_missing_type(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for control without control_type."""
        errors = security_domain.validate_entity("control", {"name": "WAF"})
        assert len(errors) > 0
        assert any("control_type" in error for error in errors)

    def test_validate_compliance_requirement_with_all_required(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation passes for compliance_requirement with required properties."""
        errors = security_domain.validate_entity(
            "compliance_requirement", {"name": "SOC2-CC6.1", "framework": "SOC2"}
        )
        assert len(errors) == 0

    def test_validate_compliance_requirement_missing_framework(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for compliance_requirement without framework."""
        errors = security_domain.validate_entity(
            "compliance_requirement", {"name": "SOC2-CC6.1"}
        )
        assert len(errors) > 0
        assert any("framework" in error for error in errors)

    def test_validate_encryption_config_with_all_required(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation passes for encryption_config with required properties."""
        errors = security_domain.validate_entity(
            "encryption_config", {"name": "S3-Encryption", "algorithm": "AES-256"}
        )
        assert len(errors) == 0

    def test_validate_encryption_config_missing_algorithm(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for encryption_config without algorithm."""
        errors = security_domain.validate_entity(
            "encryption_config", {"name": "S3-Encryption"}
        )
        assert len(errors) > 0
        assert any("algorithm" in error for error in errors)

    def test_validate_security_finding_with_all_required(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation passes for security_finding with required properties."""
        errors = security_domain.validate_entity(
            "security_finding", {"name": "Unencrypted S3 Bucket", "severity": "high"}
        )
        assert len(errors) == 0

    def test_validate_security_finding_missing_severity(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for security_finding without severity."""
        errors = security_domain.validate_entity(
            "security_finding", {"name": "Unencrypted S3 Bucket"}
        )
        assert len(errors) > 0
        assert any("severity" in error for error in errors)

    def test_validate_identity_with_all_required(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation passes for identity with required properties."""
        errors = security_domain.validate_entity(
            "identity", {"name": "admin", "identity_type": "user"}
        )
        assert len(errors) == 0

    def test_validate_identity_missing_identity_type(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for identity without identity_type."""
        errors = security_domain.validate_entity("identity", {"name": "admin"})
        assert len(errors) > 0
        assert any("identity_type" in error for error in errors)

    def test_validate_unknown_entity_type(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for unknown entity type."""
        errors = security_domain.validate_entity("unknown_type", {"name": "test"})
        assert len(errors) > 0
        assert any("Unknown entity type" in error for error in errors)


class TestSecurityDomainRelationshipValidation:
    """Test relationship validation enforces valid source/target types."""

    def test_validate_mitigates_control_to_vulnerability(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test mitigates relationship validates control -> vulnerability."""
        errors = security_domain.validate_relationship(
            "mitigates", "control", "vulnerability"
        )
        assert len(errors) == 0

    def test_validate_mitigates_control_to_threat(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test mitigates relationship validates control -> threat."""
        errors = security_domain.validate_relationship("mitigates", "control", "threat")
        assert len(errors) == 0

    def test_validate_mitigates_invalid_source(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test mitigates relationship rejects invalid source type."""
        errors = security_domain.validate_relationship(
            "mitigates", "threat", "vulnerability"
        )
        assert len(errors) > 0
        assert any("Invalid source type" in error for error in errors)

    def test_validate_mitigates_invalid_target(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test mitigates relationship rejects invalid target type."""
        errors = security_domain.validate_relationship(
            "mitigates", "control", "identity"
        )
        assert len(errors) > 0
        assert any("Invalid target type" in error for error in errors)

    def test_validate_grants_access_policy_to_identity(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test grants_access relationship validates access_policy -> identity."""
        errors = security_domain.validate_relationship(
            "grants_access", "access_policy", "identity"
        )
        assert len(errors) == 0

    def test_validate_grants_access_invalid_source(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test grants_access relationship rejects invalid source type."""
        errors = security_domain.validate_relationship(
            "grants_access", "control", "identity"
        )
        assert len(errors) > 0
        assert any("Invalid source type" in error for error in errors)

    def test_validate_grants_access_invalid_target(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test grants_access relationship rejects invalid target type."""
        errors = security_domain.validate_relationship(
            "grants_access", "access_policy", "vulnerability"
        )
        assert len(errors) > 0
        assert any("Invalid target type" in error for error in errors)

    def test_validate_exposes_encryption_to_vulnerability(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test exposes relationship validates encryption_config -> vulnerability."""
        errors = security_domain.validate_relationship(
            "exposes", "encryption_config", "vulnerability"
        )
        assert len(errors) == 0

    def test_validate_exposes_policy_to_threat(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test exposes relationship validates access_policy -> threat."""
        errors = security_domain.validate_relationship(
            "exposes", "access_policy", "threat"
        )
        assert len(errors) == 0

    def test_validate_implements_control_to_compliance(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test implements relationship validates control -> compliance_requirement."""
        errors = security_domain.validate_relationship(
            "implements", "control", "compliance_requirement"
        )
        assert len(errors) == 0

    def test_validate_violates_finding_to_policy(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test violates relationship validates security_finding -> access_policy."""
        errors = security_domain.validate_relationship(
            "violates", "security_finding", "access_policy"
        )
        assert len(errors) == 0

    def test_validate_protects_control_to_identity(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test protects relationship validates control -> identity."""
        errors = security_domain.validate_relationship(
            "protects", "control", "identity"
        )
        assert len(errors) == 0

    def test_validate_requires_control_to_compliance(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test requires relationship validates control -> compliance_requirement."""
        errors = security_domain.validate_relationship(
            "requires", "control", "compliance_requirement"
        )
        assert len(errors) == 0

    def test_validate_unknown_relationship_type(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test validation fails for unknown relationship type."""
        errors = security_domain.validate_relationship(
            "unknown_rel", "control", "vulnerability"
        )
        assert len(errors) > 0
        assert any("Unknown relationship type" in error for error in errors)


class TestSecurityDomainCustomOperations:
    """Test domain-specific custom operations."""

    def test_supported_operations(self, security_domain: SecurityDomain) -> None:
        """Test that domain lists supported operations."""
        operations = security_domain.get_supported_operations()
        assert len(operations) == 4
        assert "find_unmitigated_vulnerabilities" in operations
        assert "check_compliance_coverage" in operations
        assert "trace_access_path" in operations
        assert "find_encryption_gaps" in operations

    @pytest.mark.asyncio
    async def test_execute_find_unmitigated_vulnerabilities(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test executing find_unmitigated_vulnerabilities operation."""
        result = await security_domain.execute_operation(
            "find_unmitigated_vulnerabilities", {"severity": "critical"}
        )
        assert result is not None
        assert result["operation"] == "find_unmitigated_vulnerabilities"
        assert "params" in result

    @pytest.mark.asyncio
    async def test_execute_check_compliance_coverage(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test executing check_compliance_coverage operation."""
        result = await security_domain.execute_operation(
            "check_compliance_coverage", {"framework": "SOC2"}
        )
        assert result is not None
        assert result["operation"] == "check_compliance_coverage"

    @pytest.mark.asyncio
    async def test_execute_trace_access_path(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test executing trace_access_path operation."""
        result = await security_domain.execute_operation(
            "trace_access_path", {"identity_id": "user-123"}
        )
        assert result is not None
        assert result["operation"] == "trace_access_path"

    @pytest.mark.asyncio
    async def test_execute_find_encryption_gaps(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test executing find_encryption_gaps operation."""
        result = await security_domain.execute_operation(
            "find_encryption_gaps", {"scope": "all"}
        )
        assert result is not None
        assert result["operation"] == "find_encryption_gaps"

    @pytest.mark.asyncio
    async def test_execute_unknown_operation_raises_error(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test executing unknown operation raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await security_domain.execute_operation("unknown_op", {})


class TestSecurityDomainCompleteness:
    """Test overall domain completeness and quality."""

    def test_all_entity_types_have_descriptions(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test that all entity types have non-empty descriptions."""
        for entity_type in security_domain.entity_types:
            assert entity_type.description
            assert len(entity_type.description) > 0

    def test_all_relationship_types_have_descriptions(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test that all relationship types have non-empty descriptions."""
        for rel_type in security_domain.relationship_types:
            assert rel_type.description
            assert len(rel_type.description) > 0

    def test_no_duplicate_entity_names(self, security_domain: SecurityDomain) -> None:
        """Test that entity type names are unique."""
        entity_names = [et.name for et in security_domain.entity_types]
        assert len(entity_names) == len(set(entity_names))

    def test_no_duplicate_relationship_names(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test that relationship type names are unique."""
        rel_names = [rt.name for rt in security_domain.relationship_types]
        assert len(rel_names) == len(set(rel_names))

    def test_all_relationships_reference_valid_entity_types(
        self, security_domain: SecurityDomain
    ) -> None:
        """Test that all relationships reference defined entity types."""
        entity_names = {et.name for et in security_domain.entity_types}

        for rel_type in security_domain.relationship_types:
            for source_type in rel_type.valid_source_types:
                assert source_type in entity_names, (
                    f"Relationship '{rel_type.name}' references unknown "
                    f"source type: {source_type}"
                )
            for target_type in rel_type.valid_target_types:
                assert target_type in entity_names, (
                    f"Relationship '{rel_type.name}' references unknown "
                    f"target type: {target_type}"
                )
