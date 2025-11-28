"""
Security Analysis API Router.

Provides endpoints for security analysis using Intelligence-Builder platform.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class AnalyzeTextRequest(BaseModel):
    """Request for text analysis."""

    text: str = Field(..., min_length=10, description="Text to analyze for security patterns")
    source_type: Optional[str] = Field(
        None,
        description="Type of source (e.g., 'vulnerability_report', 'security_scan')",
    )


class AnalyzeTextResponse(BaseModel):
    """Response from text analysis."""

    entities: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    entity_count: int
    relationship_count: int
    processing_time_ms: float


class VulnerabilityReportRequest(BaseModel):
    """Request for vulnerability report analysis."""

    report_text: str = Field(..., min_length=50, description="Full vulnerability report text")
    report_source: str = Field(
        default="security_scan",
        description="Source of the report",
    )


class VulnerabilityReportResponse(BaseModel):
    """Response from vulnerability report analysis."""

    vulnerabilities: List[Dict[str, Any]] = Field(default_factory=list)
    controls: List[Dict[str, Any]] = Field(default_factory=list)
    compliance_impacts: List[Dict[str, Any]] = Field(default_factory=list)
    threat_actors: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    risk_score: float = Field(..., ge=0, le=100)
    entity_count: int
    relationship_count: int
    processing_time_ms: float


class VulnerabilityContextRequest(BaseModel):
    """Request for vulnerability context lookup."""

    cve_id: str = Field(..., pattern=r"^CVE-\d{4}-\d{4,7}$", description="CVE identifier")
    depth: int = Field(default=2, ge=1, le=5, description="Traversal depth")


class VulnerabilityContextResponse(BaseModel):
    """Response with vulnerability context."""

    found: bool
    cve_id: str
    entity_id: Optional[str] = None
    name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    related_controls: List[str] = Field(default_factory=list)
    affected_assets: List[str] = Field(default_factory=list)
    threat_actors: List[str] = Field(default_factory=list)
    remediations: List[str] = Field(default_factory=list)


class DomainSchemaResponse(BaseModel):
    """Response with security domain schema."""

    domain: str
    entity_types: List[Dict[str, Any]]
    relationship_types: List[Dict[str, Any]]


# ============================================================================
# Dependencies
# ============================================================================


async def get_ib_service(request: Request):
    """Get IB service from app state."""
    if not hasattr(request.app.state, "ib_service") or not request.app.state.ib_service:
        raise HTTPException(
            status_code=503,
            detail="Intelligence-Builder service not available. Check configuration.",
        )

    if not request.app.state.ib_service.is_connected:
        raise HTTPException(
            status_code=503,
            detail="Intelligence-Builder service not connected.",
        )

    return request.app.state.ib_service


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/analyze", response_model=AnalyzeTextResponse)
async def analyze_text(
    request: AnalyzeTextRequest,
    ib_service=Depends(get_ib_service),
) -> AnalyzeTextResponse:
    """
    Analyze text for security patterns.

    Detects security entities like:
    - CVE identifiers
    - Compliance requirements (SOC 2, HIPAA, etc.)
    - Threat actors
    - Security controls

    Returns detected entities and relationships.
    """
    result = await ib_service.analyze_security_text(
        text=request.text,
        source_type=request.source_type,
    )

    return AnalyzeTextResponse(
        entities=[
            {
                "type": e.entity_type,
                "name": e.name,
                "confidence": e.confidence,
                "properties": e.properties,
            }
            for e in result.entities
        ],
        relationships=[
            {
                "type": r.relationship_type,
                "source": r.source_entity.name,
                "target": r.target_entity.name,
                "confidence": r.confidence,
            }
            for r in result.relationships
        ],
        entity_count=result.entity_count,
        relationship_count=result.relationship_count,
        processing_time_ms=result.processing_time_ms,
    )


@router.post("/vulnerability-report", response_model=VulnerabilityReportResponse)
async def analyze_vulnerability_report(
    request: VulnerabilityReportRequest,
    ib_service=Depends(get_ib_service),
) -> VulnerabilityReportResponse:
    """
    Analyze a vulnerability report and extract structured data.

    Provides:
    - Detected vulnerabilities with CVE IDs
    - Recommended security controls
    - Compliance impacts
    - Associated threat actors
    - Calculated risk score
    """
    analysis = await ib_service.analyze_vulnerability_report(
        report_text=request.report_text,
        report_source=request.report_source,
    )

    return VulnerabilityReportResponse(**analysis)


@router.get("/vulnerability/{cve_id}/context", response_model=VulnerabilityContextResponse)
async def get_vulnerability_context(
    cve_id: str,
    depth: int = 2,
    ib_service=Depends(get_ib_service),
) -> VulnerabilityContextResponse:
    """
    Get context around a vulnerability from the knowledge graph.

    Returns related:
    - Security controls that mitigate the vulnerability
    - Affected assets
    - Known threat actors
    - Available remediations
    """
    # Validate CVE format
    import re
    if not re.match(r"^CVE-\d{4}-\d{4,7}$", cve_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid CVE ID format. Expected: CVE-YYYY-NNNNN",
        )

    context = await ib_service.get_vulnerability_context(cve_id, depth)
    return VulnerabilityContextResponse(**context)


@router.get("/schema", response_model=DomainSchemaResponse)
async def get_security_schema(
    ib_service=Depends(get_ib_service),
) -> DomainSchemaResponse:
    """
    Get the security domain schema.

    Returns all entity types and relationship types defined
    in the security domain.
    """
    schema = await ib_service.get_security_schema()
    return DomainSchemaResponse(**schema)


@router.get("/health")
async def security_health(request: Request) -> Dict[str, Any]:
    """
    Check security analysis service health.

    Returns IB platform connection status.
    """
    if not hasattr(request.app.state, "ib_service") or not request.app.state.ib_service:
        return {
            "status": "degraded",
            "message": "Intelligence-Builder service not configured",
            "ib_connected": False,
        }

    ib_service = request.app.state.ib_service

    if not ib_service.is_connected:
        return {
            "status": "degraded",
            "message": "Intelligence-Builder service not connected",
            "ib_connected": False,
        }

    # Get IB health
    ib_health = await ib_service.health_check()

    return {
        "status": "healthy" if ib_health.get("status") == "healthy" else "degraded",
        "message": "Security analysis service operational",
        "ib_connected": True,
        "ib_status": ib_health.get("status"),
    }
