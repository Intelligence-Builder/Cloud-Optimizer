"""Data models for Knowledge Base entries.

These dataclasses define the structure for various knowledge base content types
including compliance controls, best practices, security patterns, and remediation
templates.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ComplianceControl:
    """Compliance framework control definition.

    Represents a single control from a compliance framework like CIS, NIST, or PCI-DSS.

    Attributes:
        framework: Framework name (e.g., "CIS", "NIST", "PCI-DSS")
        control_id: Unique identifier within the framework (e.g., "1.1", "AC-2")
        name: Control name/title
        description: Detailed control description
        requirements: List of specific requirements
        aws_services: List of AWS services related to this control
        implementation_guidance: Step-by-step implementation guidance
    """

    framework: str
    control_id: str
    name: str
    description: str
    requirements: List[str] = field(default_factory=list)
    aws_services: List[str] = field(default_factory=list)
    implementation_guidance: str = ""


@dataclass
class ServiceBestPractice:
    """AWS service best practice recommendation.

    Represents a best practice or recommendation for an AWS service.

    Attributes:
        service: AWS service name (e.g., "EC2", "S3", "RDS")
        category: Category of best practice (e.g., "security", "cost", "performance")
        title: Practice title
        description: Detailed description
        compliance_frameworks: Related compliance frameworks
        implementation: Implementation description
        terraform_example: Terraform code example (if applicable)
        cli_example: AWS CLI example (if applicable)
        console_steps: AWS Console step-by-step instructions
    """

    service: str
    category: str
    title: str
    description: str
    compliance_frameworks: List[str] = field(default_factory=list)
    implementation: str = ""
    terraform_example: str = ""
    cli_example: str = ""
    console_steps: List[str] = field(default_factory=list)


@dataclass
class SecurityPattern:
    """Security pattern definition.

    Represents a reusable security pattern or architecture.

    Attributes:
        pattern_id: Unique pattern identifier
        name: Pattern name
        category: Pattern category (e.g., "encryption", "access-control", "monitoring")
        description: Detailed pattern description
        applicable_services: AWS services where this pattern applies
        compliance_frameworks: Related compliance frameworks
        implementation_steps: Step-by-step implementation instructions
        code_examples: Dict of code examples by type (terraform, cli, sdk, etc.)
    """

    pattern_id: str
    name: str
    category: str
    description: str
    applicable_services: List[str] = field(default_factory=list)
    compliance_frameworks: List[str] = field(default_factory=list)
    implementation_steps: List[str] = field(default_factory=list)
    code_examples: Dict[str, str] = field(default_factory=dict)


@dataclass
class RemediationTemplate:
    """Remediation template for security findings.

    Provides remediation guidance for specific security rules or findings.

    Attributes:
        template_id: Unique template identifier
        rule_id: Related security rule ID
        title: Remediation title
        description: Detailed remediation description
        terraform: Terraform remediation code
        cli: AWS CLI remediation commands
        console_steps: AWS Console remediation steps
    """

    template_id: str
    rule_id: str
    title: str
    description: str
    terraform: str = ""
    cli: str = ""
    console_steps: List[str] = field(default_factory=list)


@dataclass
class KBEntry:
    """Unified knowledge base entry.

    A simplified, unified representation of knowledge base content that can be
    used for search and retrieval across different content types.

    Attributes:
        entry_type: Type of entry ("control", "practice", "pattern", "remediation")
        control_name: Name/title of the entry
        description: Entry description
        guidance: Implementation or remediation guidance
        framework: Related framework (if applicable)
        service: Related AWS service (if applicable)
        terraform: Terraform example/code (if applicable)
        cli: CLI example/code (if applicable)
        metadata: Additional metadata as key-value pairs
    """

    entry_type: str
    control_name: str
    description: str
    guidance: str = ""
    framework: Optional[str] = None
    service: Optional[str] = None
    terraform: str = ""
    cli: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
