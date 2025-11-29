"""
Security API Pydantic Schemas.

Provides request/response models for security API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Scan Schemas
# ============================================================================


class SecurityScanRequest(BaseModel):
    """Request for security entity scanning."""

    text: str = Field(..., min_length=10, description="Text to scan for security entities")
    document_id: Optional[str] = Field(None, description="Optional document identifier")
    min_confidence: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for entity extraction",
    )
    include_relationships: bool = Field(
        True,
        description="Include relationship extraction",
    )


class SecurityEntity(BaseModel):
    """Security entity extracted from text."""

    entity_id: str = Field(..., description="Unique entity identifier")
    entity_type: str = Field(..., description="Type of security entity")
    name: str = Field(..., description="Entity name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity properties")


class SecurityRelationship(BaseModel):
    """Relationship between security entities."""

    relationship_id: str = Field(..., description="Unique relationship identifier")
    relationship_type: str = Field(..., description="Type of relationship")
    source_entity: str = Field(..., description="Source entity name")
    target_entity: str = Field(..., description="Target entity name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class SecurityScanResult(BaseModel):
    """Result from security scanning."""

    scan_id: str = Field(..., description="Unique scan identifier")
    document_id: Optional[str] = Field(None, description="Document identifier if provided")
    entities_found: List[SecurityEntity] = Field(
        default_factory=list,
        description="Extracted security entities",
    )
    relationships_found: List[SecurityRelationship] = Field(
        default_factory=list,
        description="Extracted relationships",
    )
    entity_count: int = Field(..., description="Total number of entities found")
    relationship_count: int = Field(..., description="Total number of relationships found")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    timestamp: datetime = Field(..., description="Scan timestamp")


# ============================================================================
# Vulnerability Schemas
# ============================================================================


class VulnerabilityBase(BaseModel):
    """Base vulnerability model."""

    name: str = Field(..., min_length=3, description="Vulnerability name")
    cve_id: Optional[str] = Field(
        None,
        pattern=r"^CVE-\d{4}-\d{4,7}$",
        description="CVE identifier",
    )
    severity: str = Field(
        ...,
        pattern="^(low|medium|high|critical)$",
        description="Severity level",
    )
    cvss_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="CVSS score (0-10)",
    )
    description: str = Field(..., min_length=10, description="Vulnerability description")


class VulnerabilityCreate(VulnerabilityBase):
    """Request to create a vulnerability entity."""

    affected_systems: List[str] = Field(
        default_factory=list,
        description="Systems affected by this vulnerability",
    )
    remediation: Optional[str] = Field(None, description="Remediation guidance")


class Vulnerability(VulnerabilityBase):
    """Vulnerability entity response."""

    vulnerability_id: str = Field(..., description="Unique vulnerability identifier")
    affected_systems: List[str] = Field(
        default_factory=list,
        description="Systems affected",
    )
    remediation: Optional[str] = Field(None, description="Remediation guidance")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


# ============================================================================
# Control Schemas
# ============================================================================


class SecurityControlBase(BaseModel):
    """Base security control model."""

    name: str = Field(..., min_length=3, description="Control name")
    control_id: Optional[str] = Field(None, description="Control identifier (e.g., CC1.1)")
    description: str = Field(..., min_length=10, description="Control description")
    category: str = Field(..., description="Control category")


class SecurityControlCreate(SecurityControlBase):
    """Request to create a security control."""

    implementation_status: str = Field(
        "not_implemented",
        pattern="^(not_implemented|partial|implemented)$",
        description="Implementation status",
    )
    framework: Optional[str] = Field(None, description="Associated framework (SOC2, HIPAA, etc.)")


class SecurityControl(SecurityControlBase):
    """Security control response."""

    control_uuid: str = Field(..., description="Unique control UUID")
    implementation_status: str = Field(..., description="Implementation status")
    framework: Optional[str] = Field(None, description="Associated framework")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


# ============================================================================
# Compliance Schemas
# ============================================================================


class ComplianceRequirement(BaseModel):
    """Compliance requirement model."""

    requirement_id: str = Field(..., description="Unique requirement identifier")
    framework: str = Field(..., description="Compliance framework")
    requirement_code: str = Field(..., description="Requirement code")
    description: str = Field(..., description="Requirement description")
    status: str = Field(
        ...,
        pattern="^(compliant|partial|non_compliant|not_applicable)$",
        description="Compliance status",
    )


class ComplianceCheckRequest(BaseModel):
    """Request for compliance check."""

    tenant_id: str = Field(..., description="Tenant ID for compliance check")
    framework: str = Field(
        ...,
        pattern="^(soc2|hipaa|pci_dss|iso27001|gdpr)$",
        description="Compliance framework to check",
    )
    scope: List[str] = Field(
        default_factory=list,
        description="Specific areas to check (empty for all)",
    )


class ComplianceCheckResult(BaseModel):
    """Result from compliance check."""

    check_id: str = Field(..., description="Unique check identifier")
    tenant_id: str = Field(..., description="Tenant ID")
    framework: str = Field(..., description="Compliance framework")
    total_requirements: int = Field(..., description="Total requirements checked")
    implemented: int = Field(..., description="Number of implemented requirements")
    partial: int = Field(..., description="Number of partially implemented requirements")
    gaps: int = Field(..., description="Number of compliance gaps")
    coverage_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Compliance coverage percentage",
    )
    requirements: List[ComplianceRequirement] = Field(
        default_factory=list,
        description="Detailed requirement status",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for improvement",
    )
    timestamp: datetime = Field(..., description="Check timestamp")


# ============================================================================
# Finding Schemas
# ============================================================================


class SecurityFinding(BaseModel):
    """Security finding model."""

    finding_id: str = Field(..., description="Unique finding identifier")
    finding_type: str = Field(..., description="Type of finding")
    severity: str = Field(
        ...,
        pattern="^(low|medium|high|critical)$",
        description="Finding severity",
    )
    title: str = Field(..., description="Finding title")
    description: str = Field(..., description="Detailed description")
    affected_resources: List[str] = Field(
        default_factory=list,
        description="Affected resources",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Remediation recommendations",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score",
    )
    status: str = Field(
        "open",
        pattern="^(open|investigating|resolved|false_positive)$",
        description="Finding status",
    )
    created_at: datetime = Field(..., description="Creation timestamp")


# ============================================================================
# Graph Schemas
# ============================================================================


class GraphNode(BaseModel):
    """Node in security knowledge graph."""

    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(..., description="Type of node")
    label: str = Field(..., description="Node label")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")


class GraphEdge(BaseModel):
    """Edge in security knowledge graph."""

    edge_id: str = Field(..., description="Unique edge identifier")
    edge_type: str = Field(..., description="Type of relationship")
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge properties")


class SecurityGraph(BaseModel):
    """Security knowledge graph response."""

    graph_id: str = Field(..., description="Unique graph identifier")
    nodes: List[GraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: List[GraphEdge] = Field(default_factory=list, description="Graph edges")
    node_count: int = Field(..., description="Total number of nodes")
    edge_count: int = Field(..., description="Total number of edges")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Graph metadata (categories, statistics, etc.)",
    )
    timestamp: datetime = Field(..., description="Graph generation timestamp")
