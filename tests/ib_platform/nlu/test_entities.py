"""
Tests for entity extraction.
"""

import pytest

from ib_platform.nlu.entities import EntityExtractor
from ib_platform.nlu.models import NLUEntities


class TestEntityExtractor:
    """Tests for EntityExtractor class."""

    def test_extract_returns_nlu_entities(self, entity_extractor: EntityExtractor) -> None:
        """Test that extract returns NLUEntities object."""
        result = entity_extractor.extract("What about S3 buckets?")
        assert isinstance(result, NLUEntities)

    def test_extract_empty_string(self, entity_extractor: EntityExtractor) -> None:
        """Test extraction from empty string."""
        result = entity_extractor.extract("")
        assert not result.has_entities()


class TestAWSServiceExtraction:
    """Tests for AWS service name extraction."""

    def test_extract_single_service(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting a single AWS service."""
        result = entity_extractor.extract("How do I secure my S3 buckets?")
        assert "S3" in result.aws_services

    def test_extract_multiple_services(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting multiple AWS services."""
        result = entity_extractor.extract(
            "I need help with S3, EC2, and IAM configurations"
        )
        assert "S3" in result.aws_services
        assert "EC2" in result.aws_services
        assert "IAM" in result.aws_services

    def test_case_insensitive_extraction(self, entity_extractor: EntityExtractor) -> None:
        """Test that service extraction is case-insensitive."""
        result = entity_extractor.extract("What about s3 and ec2?")
        assert "S3" in result.aws_services
        assert "EC2" in result.aws_services

    def test_extract_lambda(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting Lambda service."""
        result = entity_extractor.extract("How do I secure Lambda functions?")
        assert "Lambda" in result.aws_services

    def test_extract_rds(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting RDS service."""
        result = entity_extractor.extract("RDS database security best practices")
        assert "RDS" in result.aws_services

    def test_extract_cloudwatch(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting CloudWatch service."""
        result = entity_extractor.extract("Set up CloudWatch monitoring")
        assert "CloudWatch" in result.aws_services

    def test_extract_kms(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting KMS service."""
        result = entity_extractor.extract("Use KMS for encryption")
        assert "KMS" in result.aws_services

    def test_no_false_positives(self, entity_extractor: EntityExtractor) -> None:
        """Test that random words don't get extracted as services."""
        result = entity_extractor.extract("I need help with my application security")
        # Should not extract random words
        assert len(result.aws_services) == 0


class TestComplianceFrameworkExtraction:
    """Tests for compliance framework extraction."""

    def test_extract_soc2(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting SOC2 framework."""
        result = entity_extractor.extract("How do I achieve SOC2 compliance?")
        assert "SOC2" in result.compliance_frameworks

    def test_extract_soc2_with_space(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting SOC 2 (with space)."""
        result = entity_extractor.extract("SOC 2 compliance requirements")
        assert "SOC2" in result.compliance_frameworks

    def test_extract_hipaa(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting HIPAA framework."""
        result = entity_extractor.extract("HIPAA compliance for healthcare data")
        assert "HIPAA" in result.compliance_frameworks

    def test_extract_pci_dss(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting PCI-DSS framework."""
        result = entity_extractor.extract("PCI-DSS requirements for payment data")
        assert "PCI-DSS" in result.compliance_frameworks

    def test_extract_pci_dss_with_space(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting PCI DSS (with space)."""
        result = entity_extractor.extract("PCI DSS compliance checklist")
        assert "PCI-DSS" in result.compliance_frameworks

    def test_extract_gdpr(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting GDPR framework."""
        result = entity_extractor.extract("GDPR data protection requirements")
        assert "GDPR" in result.compliance_frameworks

    def test_extract_iso27001(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting ISO 27001 framework."""
        result = entity_extractor.extract("ISO 27001 certification process")
        assert "ISO 27001" in result.compliance_frameworks

    def test_extract_multiple_frameworks(
        self, entity_extractor: EntityExtractor
    ) -> None:
        """Test extracting multiple compliance frameworks."""
        result = entity_extractor.extract(
            "We need SOC2, HIPAA, and GDPR compliance"
        )
        assert "SOC2" in result.compliance_frameworks
        assert "HIPAA" in result.compliance_frameworks
        assert "GDPR" in result.compliance_frameworks

    def test_case_insensitive_frameworks(
        self, entity_extractor: EntityExtractor
    ) -> None:
        """Test that framework extraction is case-insensitive."""
        result = entity_extractor.extract("hipaa and gdpr compliance")
        assert "HIPAA" in result.compliance_frameworks
        assert "GDPR" in result.compliance_frameworks


class TestFindingIDExtraction:
    """Tests for finding ID extraction."""

    def test_extract_sec_finding(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting SEC-prefixed finding."""
        result = entity_extractor.extract("What is finding SEC-001?")
        assert "SEC-001" in result.finding_ids

    def test_extract_fnd_finding(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting FND-prefixed finding."""
        result = entity_extractor.extract("Explain finding FND-12345")
        assert "FND-12345" in result.finding_ids

    def test_extract_finding_keyword(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting FINDING-prefixed finding."""
        result = entity_extractor.extract("Help with FINDING-789")
        assert "FINDING-789" in result.finding_ids

    def test_extract_cve(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting CVE identifiers."""
        result = entity_extractor.extract("Vulnerability CVE-2023-12345")
        assert "CVE-2023-12345" in result.finding_ids

    def test_extract_multiple_findings(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting multiple finding IDs."""
        result = entity_extractor.extract("Findings SEC-001 and FND-456")
        assert "SEC-001" in result.finding_ids
        assert "FND-456" in result.finding_ids

    def test_case_insensitive_findings(self, entity_extractor: EntityExtractor) -> None:
        """Test that finding extraction is case-insensitive."""
        result = entity_extractor.extract("sec-123 and fnd-456")
        assert len(result.finding_ids) == 2


class TestResourceIDExtraction:
    """Tests for AWS resource ID extraction."""

    def test_extract_arn(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting ARN."""
        arn = "arn:aws:s3:::my-bucket"
        result = entity_extractor.extract(f"Check bucket {arn}")
        assert arn in result.resource_ids

    def test_extract_s3_bucket(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting S3 bucket name."""
        result = entity_extractor.extract("Check bucket my-test-bucket-123")
        assert "my-test-bucket-123" in result.resource_ids

    def test_extract_s3_with_protocol(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting S3 bucket with s3:// protocol."""
        result = entity_extractor.extract("s3://my-bucket/path/to/file")
        assert "my-bucket" in result.resource_ids

    def test_extract_instance_id(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting EC2 instance ID."""
        result = entity_extractor.extract("Instance i-1234567890abcdef0")
        assert "i-1234567890abcdef0" in result.resource_ids

    def test_extract_security_group(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting security group ID."""
        result = entity_extractor.extract("Security group sg-1234567890abcdef0")
        assert "sg-1234567890abcdef0" in result.resource_ids

    def test_extract_vpc_id(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting VPC ID."""
        result = entity_extractor.extract("VPC vpc-1234567890abcdef0")
        assert "vpc-1234567890abcdef0" in result.resource_ids

    def test_extract_subnet_id(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting subnet ID."""
        result = entity_extractor.extract("Subnet subnet-1234567890abcdef0")
        assert "subnet-1234567890abcdef0" in result.resource_ids

    def test_extract_multiple_resources(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting multiple resource IDs."""
        result = entity_extractor.extract(
            "Check i-123456789 and sg-abcdef123 in vpc-999888777"
        )
        assert "i-123456789" in result.resource_ids
        assert "sg-abcdef123" in result.resource_ids
        assert "vpc-999888777" in result.resource_ids

    def test_complex_arn(self, entity_extractor: EntityExtractor) -> None:
        """Test extracting complex ARN."""
        arn = "arn:aws:iam::123456789012:role/MyRole"
        result = entity_extractor.extract(f"IAM role {arn}")
        assert arn in result.resource_ids


class TestNLUEntities:
    """Tests for NLUEntities dataclass."""

    def test_has_entities_empty(self) -> None:
        """Test has_entities with empty entities."""
        entities = NLUEntities()
        assert not entities.has_entities()

    def test_has_entities_with_services(self) -> None:
        """Test has_entities with AWS services."""
        entities = NLUEntities(aws_services=["S3", "EC2"])
        assert entities.has_entities()

    def test_has_entities_with_frameworks(self) -> None:
        """Test has_entities with compliance frameworks."""
        entities = NLUEntities(compliance_frameworks=["SOC2"])
        assert entities.has_entities()

    def test_has_entities_with_findings(self) -> None:
        """Test has_entities with finding IDs."""
        entities = NLUEntities(finding_ids=["SEC-001"])
        assert entities.has_entities()

    def test_has_entities_with_resources(self) -> None:
        """Test has_entities with resource IDs."""
        entities = NLUEntities(resource_ids=["i-1234567890abcdef0"])
        assert entities.has_entities()

    def test_get_all_entities_empty(self) -> None:
        """Test get_all_entities with empty entities."""
        entities = NLUEntities()
        all_entities = entities.get_all_entities()
        assert len(all_entities) == 0

    def test_get_all_entities_combined(self) -> None:
        """Test get_all_entities with mixed entities."""
        entities = NLUEntities(
            aws_services=["S3", "EC2"],
            compliance_frameworks=["SOC2"],
            finding_ids=["SEC-001"],
            resource_ids=["i-123456789"],
        )
        all_entities = entities.get_all_entities()
        assert len(all_entities) == 5
        assert "S3" in all_entities
        assert "SOC2" in all_entities
        assert "SEC-001" in all_entities
        assert "i-123456789" in all_entities


class TestComplexQueries:
    """Tests with complex, real-world queries."""

    def test_complex_security_query(self, entity_extractor: EntityExtractor) -> None:
        """Test extraction from complex security query."""
        query = (
            "How do I fix finding SEC-001 for S3 bucket my-data-bucket "
            "to meet HIPAA compliance requirements?"
        )
        result = entity_extractor.extract(query)

        assert "S3" in result.aws_services
        assert "HIPAA" in result.compliance_frameworks
        assert "SEC-001" in result.finding_ids
        assert "my-data-bucket" in result.resource_ids

    def test_complex_multi_resource_query(
        self, entity_extractor: EntityExtractor
    ) -> None:
        """Test extraction from multi-resource query."""
        query = (
            "Instance i-1234567890abcdef0 in vpc-abcd1234 "
            "with security group sg-9876543210fedcba needs EC2 and IAM review"
        )
        result = entity_extractor.extract(query)

        assert "EC2" in result.aws_services
        assert "IAM" in result.aws_services
        assert "i-1234567890abcdef0" in result.resource_ids
        assert "vpc-abcd1234" in result.resource_ids
        assert "sg-9876543210fedcba" in result.resource_ids

    def test_compliance_frameworks_query(
        self, entity_extractor: EntityExtractor
    ) -> None:
        """Test extraction from compliance-focused query."""
        query = "What S3 and Lambda configurations do I need for SOC2, HIPAA, and GDPR?"
        result = entity_extractor.extract(query)

        assert "S3" in result.aws_services
        assert "Lambda" in result.aws_services
        assert "SOC2" in result.compliance_frameworks
        assert "HIPAA" in result.compliance_frameworks
        assert "GDPR" in result.compliance_frameworks
