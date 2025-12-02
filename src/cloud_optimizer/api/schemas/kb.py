"""Knowledge Base API schemas.

Pydantic models for KB request/response validation.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Response schemas


class ComplianceControlResponse(BaseModel):
    """Compliance framework control response."""

    framework: str = Field(..., description="Framework name (e.g., CIS, NIST)")
    control_id: str = Field(..., description="Control identifier")
    name: str = Field(..., description="Control name")
    description: str = Field(..., description="Control description")
    requirements: List[str] = Field(
        default_factory=list, description="List of requirements"
    )
    aws_services: List[str] = Field(
        default_factory=list, description="Related AWS services"
    )
    implementation_guidance: str = Field(
        default="", description="Implementation guidance"
    )


class ServiceBestPracticeResponse(BaseModel):
    """AWS service best practice response."""

    service: str = Field(..., description="AWS service name")
    category: str = Field(..., description="Practice category")
    title: str = Field(..., description="Practice title")
    description: str = Field(..., description="Practice description")
    compliance_frameworks: List[str] = Field(
        default_factory=list, description="Related compliance frameworks"
    )
    implementation: str = Field(default="", description="Implementation description")
    terraform_example: str = Field(default="", description="Terraform code example")
    cli_example: str = Field(default="", description="AWS CLI example")
    console_steps: List[str] = Field(
        default_factory=list, description="AWS Console steps"
    )


class SecurityPatternResponse(BaseModel):
    """Security pattern response."""

    pattern_id: str = Field(..., description="Pattern identifier")
    name: str = Field(..., description="Pattern name")
    category: str = Field(..., description="Pattern category")
    description: str = Field(..., description="Pattern description")
    applicable_services: List[str] = Field(
        default_factory=list, description="Applicable AWS services"
    )
    compliance_frameworks: List[str] = Field(
        default_factory=list, description="Related compliance frameworks"
    )
    implementation_steps: List[str] = Field(
        default_factory=list, description="Implementation steps"
    )
    code_examples: Dict[str, str] = Field(
        default_factory=dict, description="Code examples by type"
    )


class RemediationTemplateResponse(BaseModel):
    """Remediation template response."""

    template_id: str = Field(..., description="Template identifier")
    rule_id: str = Field(..., description="Security rule ID")
    title: str = Field(..., description="Remediation title")
    description: str = Field(..., description="Remediation description")
    terraform: str = Field(default="", description="Terraform remediation code")
    cli: str = Field(default="", description="CLI remediation commands")
    console_steps: List[str] = Field(
        default_factory=list, description="Console remediation steps"
    )


class KBEntryResponse(BaseModel):
    """Unified KB entry response for search results."""

    entry_type: str = Field(..., description="Entry type (control/practice/pattern)")
    control_name: str = Field(..., description="Entry name/title")
    description: str = Field(..., description="Entry description")
    guidance: str = Field(default="", description="Implementation guidance")
    framework: Optional[str] = Field(None, description="Related framework")
    service: Optional[str] = Field(None, description="Related AWS service")
    terraform: str = Field(default="", description="Terraform example")
    cli: str = Field(default="", description="CLI example")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class FrameworkListResponse(BaseModel):
    """List of available frameworks."""

    frameworks: List[str] = Field(..., description="Framework names")
    total: int = Field(..., description="Total number of frameworks")


class ServiceListResponse(BaseModel):
    """List of available services."""

    services: List[str] = Field(..., description="Service names")
    total: int = Field(..., description="Total number of services")


class KBStatisticsResponse(BaseModel):
    """Knowledge Base statistics."""

    frameworks: int = Field(..., description="Number of frameworks")
    total_controls: int = Field(..., description="Total number of controls")
    services: int = Field(..., description="Number of services")
    total_practices: int = Field(..., description="Total number of practices")
    patterns: int = Field(..., description="Number of security patterns")
    remediation_templates: int = Field(
        ..., description="Number of remediation templates"
    )


class FrameworkControlsResponse(BaseModel):
    """Framework controls response."""

    framework: str = Field(..., description="Framework name")
    controls: List[ComplianceControlResponse] = Field(
        ..., description="List of controls"
    )
    total: int = Field(..., description="Total number of controls")


class ServicePracticesResponse(BaseModel):
    """Service best practices response."""

    service: str = Field(..., description="Service name")
    practices: List[ServiceBestPracticeResponse] = Field(
        ..., description="List of best practices"
    )
    total: int = Field(..., description="Total number of practices")


class SearchResultsResponse(BaseModel):
    """Search results response."""

    query: str = Field(..., description="Search query")
    results: List[KBEntryResponse] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    limit: int = Field(..., description="Result limit applied")
