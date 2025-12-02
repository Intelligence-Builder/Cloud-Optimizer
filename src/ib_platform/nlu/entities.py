"""
Entity extraction for Cloud Optimizer NLU.

Extracts AWS services, compliance frameworks, finding IDs, and resource identifiers
from user queries using regex-based pattern matching.
"""

import re
from typing import List, Set

from ib_platform.nlu.models import NLUEntities


class EntityExtractor:
    """
    Extracts entities from user queries.

    Supports extraction of:
    - AWS service names (S3, EC2, IAM, RDS, Lambda, etc.)
    - Compliance frameworks (SOC2, HIPAA, PCI-DSS, GDPR, etc.)
    - Finding identifiers (SEC-001, FND-12345, etc.)
    - AWS resource identifiers (ARNs, bucket names, instance IDs, etc.)
    """

    # AWS service name patterns
    AWS_SERVICES = {
        "S3",
        "EC2",
        "IAM",
        "RDS",
        "Lambda",
        "VPC",
        "CloudWatch",
        "CloudTrail",
        "Config",
        "GuardDuty",
        "SecurityHub",
        "KMS",
        "CloudFormation",
        "ECS",
        "EKS",
        "DynamoDB",
        "SNS",
        "SQS",
        "API Gateway",
        "Route53",
        "ELB",
        "ALB",
        "NLB",
        "AutoScaling",
        "CloudFront",
        "WAF",
        "Shield",
        "Secrets Manager",
        "Systems Manager",
        "ACM",
        "Certificate Manager",
    }

    # Compliance framework patterns
    COMPLIANCE_FRAMEWORKS = {
        "SOC2",
        "SOC 2",
        "HIPAA",
        "PCI-DSS",
        "PCI DSS",
        "GDPR",
        "ISO 27001",
        "ISO27001",
        "NIST",
        "FedRAMP",
        "CCPA",
        "CIS",
    }

    # Regex patterns for entity extraction
    PATTERNS = {
        # Finding IDs: SEC-001, FND-12345, FINDING-123, CVE-2023-12345, etc.
        "finding_id": re.compile(
            r"\b(?:SEC|FND|FINDING)-\d+\b|CVE-\d{4}-\d{4,7}", re.IGNORECASE
        ),
        # ARN: arn:aws:service:region:account-id:resource (simplified S3 ARN with :::)
        "arn": re.compile(
            r"arn:aws:[a-z0-9-]+:[a-z0-9-]*:(?:\d{12}:)?[a-zA-Z0-9-_/:.*]+",
            re.IGNORECASE,
        ),
        # S3 bucket names
        "s3_bucket": re.compile(
            r"\b(?:s3://)?([a-z0-9][a-z0-9-]{1,61}[a-z0-9])(?:/|\b)",
            re.IGNORECASE,
        ),
        # EC2 instance IDs: i-1234567890abcdef0
        "instance_id": re.compile(r"\bi-[0-9a-f]{8,17}\b", re.IGNORECASE),
        # Security group IDs: sg-1234567890abcdef0
        "security_group": re.compile(r"\bsg-[0-9a-f]{8,17}\b", re.IGNORECASE),
        # VPC IDs: vpc-1234567890abcdef0
        "vpc_id": re.compile(r"\bvpc-[0-9a-f]{8,17}\b", re.IGNORECASE),
        # Subnet IDs: subnet-1234567890abcdef0
        "subnet_id": re.compile(r"\bsubnet-[0-9a-f]{8,17}\b", re.IGNORECASE),
    }

    def extract(self, text: str) -> NLUEntities:
        """
        Extract all entities from text.

        Args:
            text: User query text

        Returns:
            NLUEntities with all extracted entities
        """
        return NLUEntities(
            aws_services=self.extract_aws_services(text),
            compliance_frameworks=self.extract_compliance_frameworks(text),
            finding_ids=self.extract_finding_ids(text),
            resource_ids=self.extract_resource_ids(text),
        )

    def extract_aws_services(self, text: str) -> List[str]:
        """
        Extract AWS service names from text.

        Args:
            text: User query text

        Returns:
            List of AWS service names found
        """
        services: Set[str] = set()

        # Case-insensitive search for AWS service names
        text_upper = text.upper()
        for service in self.AWS_SERVICES:
            # Match whole words or service names with word boundaries
            pattern = r"\b" + re.escape(service.upper()) + r"\b"
            if re.search(pattern, text_upper):
                services.add(service)

        return sorted(list(services))

    def extract_compliance_frameworks(self, text: str) -> List[str]:
        """
        Extract compliance framework names from text.

        Args:
            text: User query text

        Returns:
            List of compliance frameworks found
        """
        frameworks: Set[str] = set()

        # Case-insensitive search for compliance frameworks
        text_upper = text.upper()
        for framework in self.COMPLIANCE_FRAMEWORKS:
            pattern = r"\b" + re.escape(framework.upper()) + r"\b"
            if re.search(pattern, text_upper):
                # Normalize to standard format
                normalized = self._normalize_framework(framework)
                frameworks.add(normalized)

        return sorted(list(frameworks))

    def extract_finding_ids(self, text: str) -> List[str]:
        """
        Extract security finding identifiers from text.

        Args:
            text: User query text

        Returns:
            List of finding IDs found
        """
        matches = self.PATTERNS["finding_id"].findall(text)
        return list(set(matches))  # Remove duplicates

    def extract_resource_ids(self, text: str) -> List[str]:
        """
        Extract AWS resource identifiers from text.

        Extracts ARNs, bucket names, instance IDs, security group IDs, etc.

        Args:
            text: User query text

        Returns:
            List of resource identifiers found
        """
        resources: Set[str] = set()

        # Extract ARNs
        resources.update(self.PATTERNS["arn"].findall(text))

        # Extract S3 bucket names (capture group)
        bucket_matches = self.PATTERNS["s3_bucket"].finditer(text)
        for match in bucket_matches:
            if match.group(1):
                resources.add(match.group(1))

        # Extract EC2 instance IDs
        resources.update(self.PATTERNS["instance_id"].findall(text))

        # Extract security group IDs
        resources.update(self.PATTERNS["security_group"].findall(text))

        # Extract VPC IDs
        resources.update(self.PATTERNS["vpc_id"].findall(text))

        # Extract subnet IDs
        resources.update(self.PATTERNS["subnet_id"].findall(text))

        return sorted(list(resources))

    @staticmethod
    def _normalize_framework(framework: str) -> str:
        """
        Normalize compliance framework name to standard format.

        Args:
            framework: Raw framework name

        Returns:
            Normalized framework name
        """
        framework_upper = framework.upper()
        normalization_map = {
            "SOC 2": "SOC2",
            "PCI DSS": "PCI-DSS",
            "ISO27001": "ISO 27001",
        }
        return normalization_map.get(framework_upper, framework.upper())
