"""
Security Analysis API Router.

Provides endpoints for security analysis using Intelligence-Builder platform.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from cloud_optimizer.api.schemas.security import (
    ComplianceCheckRequest,
    ComplianceCheckResult,
    ComplianceRequirement,
    GraphEdge,
    GraphNode,
    SecurityControl,
    SecurityControlCreate,
    SecurityEntity,
    SecurityFinding,
    SecurityGraph,
    SecurityRelationship,
    SecurityScanRequest,
    SecurityScanResult,
    Vulnerability,
    VulnerabilityCreate,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class AnalyzeTextRequest(BaseModel):
    """Request for text analysis."""

    text: str = Field(
        ..., min_length=10, description="Text to analyze for security patterns"
    )
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

    report_text: str = Field(
        ..., min_length=50, description="Full vulnerability report text"
    )
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

    cve_id: str = Field(
        ..., pattern=r"^CVE-\d{4}-\d{4,7}$", description="CVE identifier"
    )
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


async def get_ib_service(request: Request) -> Any:
    """Get IB service from app state.

    Returns:
        IntelligenceBuilderService instance

    Raises:
        HTTPException: If service not available or not connected
    """
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


@router.get(
    "/vulnerability/{cve_id}/context", response_model=VulnerabilityContextResponse
)
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


# ============================================================================
# New Endpoints for Issue #11
# ============================================================================


@router.post("/scan", response_model=SecurityScanResult)
async def scan_text(
    request: SecurityScanRequest,
    ib_service=Depends(get_ib_service),
) -> SecurityScanResult:
    """
    Scan text for security entities and relationships.

    Extracts:
    - Security entities (vulnerabilities, controls, threats, etc.)
    - Relationships between entities
    - Confidence scores for each extraction
    """
    start_time = time.time()
    scan_id = str(uuid4())

    # Use IB service to analyze the text
    result = await ib_service.analyze_security_text(
        text=request.text,
        source_type="security_scan",
    )

    # Filter by confidence threshold
    entities = [
        SecurityEntity(
            entity_id=str(uuid4()),
            entity_type=e.entity_type,
            name=e.name,
            confidence=e.confidence,
            properties=e.properties,
        )
        for e in result.entities
        if e.confidence >= request.min_confidence
    ]

    relationships = []
    if request.include_relationships:
        relationships = [
            SecurityRelationship(
                relationship_id=str(uuid4()),
                relationship_type=r.relationship_type,
                source_entity=r.source_entity.name,
                target_entity=r.target_entity.name,
                confidence=r.confidence,
            )
            for r in result.relationships
            if r.confidence >= request.min_confidence
        ]

    processing_time = (time.time() - start_time) * 1000

    return SecurityScanResult(
        scan_id=scan_id,
        document_id=request.document_id,
        entities_found=entities,
        relationships_found=relationships,
        entity_count=len(entities),
        relationship_count=len(relationships),
        processing_time_ms=processing_time,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/vulnerabilities", response_model=List[Vulnerability])
async def list_vulnerabilities(
    skip: int = 0,
    limit: int = 100,
    severity: Optional[str] = None,
    ib_service=Depends(get_ib_service),
) -> List[Vulnerability]:
    """
    List vulnerabilities from the security knowledge graph.

    Optional filters:
    - severity: Filter by severity (low, medium, high, critical)
    - skip/limit: Pagination
    """
    # Query IB service for vulnerability entities
    query_result = await ib_service.query_entities(
        entity_type="vulnerability",
        filters={"severity": severity} if severity else {},
        skip=skip,
        limit=limit,
    )

    vulnerabilities = [
        Vulnerability(
            vulnerability_id=entity.get("id", str(uuid4())),
            name=entity.get("name", "Unknown"),
            cve_id=entity.get("cve_id"),
            severity=entity.get("severity", "medium"),
            cvss_score=entity.get("cvss_score"),
            description=entity.get("description", "No description available"),
            affected_systems=entity.get("affected_systems", []),
            remediation=entity.get("remediation"),
            created_at=datetime.fromisoformat(
                entity.get("created_at", datetime.now(timezone.utc).isoformat())
            ),
            updated_at=datetime.fromisoformat(entity["updated_at"])
            if entity.get("updated_at")
            else None,
        )
        for entity in query_result.get("entities", [])
    ]

    return vulnerabilities


@router.get("/vulnerabilities/{vulnerability_id}", response_model=Vulnerability)
async def get_vulnerability(
    vulnerability_id: str,
    ib_service=Depends(get_ib_service),
) -> Vulnerability:
    """Get a specific vulnerability by ID."""
    entity = await ib_service.get_entity_by_id(vulnerability_id)

    if not entity:
        raise HTTPException(
            status_code=404,
            detail=f"Vulnerability {vulnerability_id} not found",
        )

    return Vulnerability(
        vulnerability_id=entity.get("id", vulnerability_id),
        name=entity.get("name", "Unknown"),
        cve_id=entity.get("cve_id"),
        severity=entity.get("severity", "medium"),
        cvss_score=entity.get("cvss_score"),
        description=entity.get("description", "No description available"),
        affected_systems=entity.get("affected_systems", []),
        remediation=entity.get("remediation"),
        created_at=datetime.fromisoformat(
            entity.get("created_at", datetime.now(timezone.utc).isoformat())
        ),
        updated_at=datetime.fromisoformat(entity["updated_at"])
        if entity.get("updated_at")
        else None,
    )


@router.post("/vulnerabilities", response_model=Vulnerability, status_code=201)
async def create_vulnerability(
    request: VulnerabilityCreate,
    ib_service=Depends(get_ib_service),
) -> Vulnerability:
    """Create a new vulnerability entity in the knowledge graph."""
    vulnerability_id = str(uuid4())
    now = datetime.now(timezone.utc)

    entity_data = {
        "id": vulnerability_id,
        "entity_type": "vulnerability",
        "name": request.name,
        "cve_id": request.cve_id,
        "severity": request.severity,
        "cvss_score": request.cvss_score,
        "description": request.description,
        "affected_systems": request.affected_systems,
        "remediation": request.remediation,
        "created_at": now.isoformat(),
    }

    # Create entity in IB service
    await ib_service.create_entity(entity_data)

    return Vulnerability(
        vulnerability_id=vulnerability_id,
        name=request.name,
        cve_id=request.cve_id,
        severity=request.severity,
        cvss_score=request.cvss_score,
        description=request.description,
        affected_systems=request.affected_systems,
        remediation=request.remediation,
        created_at=now,
        updated_at=None,
    )


@router.get("/controls", response_model=List[SecurityControl])
async def list_controls(
    skip: int = 0,
    limit: int = 100,
    framework: Optional[str] = None,
    ib_service=Depends(get_ib_service),
) -> List[SecurityControl]:
    """
    List security controls from the knowledge graph.

    Optional filters:
    - framework: Filter by framework (SOC2, HIPAA, etc.)
    - skip/limit: Pagination
    """
    query_result = await ib_service.query_entities(
        entity_type="security_control",
        filters={"framework": framework} if framework else {},
        skip=skip,
        limit=limit,
    )

    controls = [
        SecurityControl(
            control_uuid=entity.get("id", str(uuid4())),
            name=entity.get("name", "Unknown"),
            control_id=entity.get("control_id"),
            description=entity.get("description", "No description available"),
            category=entity.get("category", "general"),
            implementation_status=entity.get(
                "implementation_status", "not_implemented"
            ),
            framework=entity.get("framework"),
            created_at=datetime.fromisoformat(
                entity.get("created_at", datetime.now(timezone.utc).isoformat())
            ),
            updated_at=datetime.fromisoformat(entity["updated_at"])
            if entity.get("updated_at")
            else None,
        )
        for entity in query_result.get("entities", [])
    ]

    return controls


@router.post("/controls", response_model=SecurityControl, status_code=201)
async def create_control(
    request: SecurityControlCreate,
    ib_service=Depends(get_ib_service),
) -> SecurityControl:
    """Create a new security control entity in the knowledge graph."""
    control_uuid = str(uuid4())
    now = datetime.now(timezone.utc)

    entity_data = {
        "id": control_uuid,
        "entity_type": "security_control",
        "name": request.name,
        "control_id": request.control_id,
        "description": request.description,
        "category": request.category,
        "implementation_status": request.implementation_status,
        "framework": request.framework,
        "created_at": now.isoformat(),
    }

    # Create entity in IB service
    await ib_service.create_entity(entity_data)

    return SecurityControl(
        control_uuid=control_uuid,
        name=request.name,
        control_id=request.control_id,
        description=request.description,
        category=request.category,
        implementation_status=request.implementation_status,
        framework=request.framework,
        created_at=now,
        updated_at=None,
    )


@router.get("/compliance", response_model=List[ComplianceRequirement])
async def list_compliance_requirements(
    framework: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    ib_service=Depends(get_ib_service),
) -> List[ComplianceRequirement]:
    """
    List compliance requirements.

    Optional filters:
    - framework: Filter by framework (soc2, hipaa, etc.)
    - status: Filter by compliance status
    - skip/limit: Pagination
    """
    filters = {}
    if framework:
        filters["framework"] = framework
    if status:
        filters["status"] = status

    query_result = await ib_service.query_entities(
        entity_type="compliance_requirement",
        filters=filters,
        skip=skip,
        limit=limit,
    )

    requirements = [
        ComplianceRequirement(
            requirement_id=entity.get("id", str(uuid4())),
            framework=entity.get("framework", "unknown"),
            requirement_code=entity.get("requirement_code", "N/A"),
            description=entity.get("description", "No description available"),
            status=entity.get("status", "not_applicable"),
        )
        for entity in query_result.get("entities", [])
    ]

    return requirements


@router.post("/compliance/check", response_model=ComplianceCheckResult)
async def check_compliance(
    request: ComplianceCheckRequest,
    ib_service=Depends(get_ib_service),
) -> ComplianceCheckResult:
    """
    Check compliance status for a specific framework.

    Analyzes:
    - Total requirements for the framework
    - Implementation status
    - Compliance gaps
    - Coverage percentage
    """
    check_id = str(uuid4())

    # Query all requirements for the framework
    query_result = await ib_service.query_entities(
        entity_type="compliance_requirement",
        filters={"framework": request.framework},
        skip=0,
        limit=1000,
    )

    requirements = []
    implemented = 0
    partial = 0
    gaps = 0

    for entity in query_result.get("entities", []):
        status = entity.get("status", "not_applicable")
        requirement = ComplianceRequirement(
            requirement_id=entity.get("id", str(uuid4())),
            framework=entity.get("framework", request.framework),
            requirement_code=entity.get("requirement_code", "N/A"),
            description=entity.get("description", "No description available"),
            status=status,
        )
        requirements.append(requirement)

        if status == "compliant":
            implemented += 1
        elif status == "partial":
            partial += 1
        elif status == "non_compliant":
            gaps += 1

    total = len(requirements)
    coverage_percentage = (implemented / total * 100) if total > 0 else 0.0

    recommendations = []
    if gaps > 0:
        recommendations.append(
            f"Address {gaps} compliance gap(s) in {request.framework.upper()}"
        )
    if partial > 0:
        recommendations.append(
            f"Complete {partial} partially implemented requirement(s)"
        )
    if coverage_percentage < 100:
        recommendations.append("Implement continuous compliance monitoring")
        recommendations.append("Schedule regular compliance assessments")

    return ComplianceCheckResult(
        check_id=check_id,
        tenant_id=request.tenant_id,
        framework=request.framework,
        total_requirements=total,
        implemented=implemented,
        partial=partial,
        gaps=gaps,
        coverage_percentage=coverage_percentage,
        requirements=requirements,
        recommendations=recommendations,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/findings", response_model=List[SecurityFinding])
async def list_findings(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    ib_service=Depends(get_ib_service),
) -> List[SecurityFinding]:
    """
    List security findings.

    Optional filters:
    - severity: Filter by severity (low, medium, high, critical)
    - status: Filter by status (open, investigating, resolved, false_positive)
    - skip/limit: Pagination
    """
    filters = {}
    if severity:
        filters["severity"] = severity
    if status:
        filters["status"] = status

    query_result = await ib_service.query_entities(
        entity_type="security_finding",
        filters=filters,
        skip=skip,
        limit=limit,
    )

    findings = [
        SecurityFinding(
            finding_id=entity.get("id", str(uuid4())),
            finding_type=entity.get("finding_type", "unknown"),
            severity=entity.get("severity", "medium"),
            title=entity.get("title", "Security Finding"),
            description=entity.get("description", "No description available"),
            affected_resources=entity.get("affected_resources", []),
            recommendations=entity.get("recommendations", []),
            confidence_score=entity.get("confidence_score", 0.8),
            status=entity.get("status", "open"),
            created_at=datetime.fromisoformat(
                entity.get("created_at", datetime.now(timezone.utc).isoformat())
            ),
        )
        for entity in query_result.get("entities", [])
    ]

    return findings


@router.get("/graph", response_model=SecurityGraph)
async def get_security_graph(
    entity_types: Optional[List[str]] = None,
    max_nodes: int = 100,
    ib_service=Depends(get_ib_service),
) -> SecurityGraph:
    """
    Get the security knowledge graph.

    Returns visualization-ready graph data with nodes and edges.

    Optional filters:
    - entity_types: Filter to specific entity types
    - max_nodes: Maximum number of nodes to return
    """
    graph_id = str(uuid4())

    # Query graph data from IB service
    graph_data = await ib_service.get_security_graph(
        entity_types=entity_types,
        max_nodes=max_nodes,
    )

    nodes = [
        GraphNode(
            node_id=node.get("id", str(uuid4())),
            node_type=node.get("type", "unknown"),
            label=node.get("label", "Unknown"),
            properties=node.get("properties", {}),
        )
        for node in graph_data.get("nodes", [])
    ]

    edges = [
        GraphEdge(
            edge_id=edge.get("id", str(uuid4())),
            edge_type=edge.get("type", "related_to"),
            source_id=edge.get("source", ""),
            target_id=edge.get("target", ""),
            properties=edge.get("properties", {}),
        )
        for edge in graph_data.get("edges", [])
    ]

    # Calculate metadata
    node_types = {}
    for node in nodes:
        node_types[node.node_type] = node_types.get(node.node_type, 0) + 1

    edge_types = {}
    for edge in edges:
        edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1

    metadata = {
        "node_types": node_types,
        "edge_types": edge_types,
        "max_nodes_requested": max_nodes,
    }

    return SecurityGraph(
        graph_id=graph_id,
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
        metadata=metadata,
        timestamp=datetime.now(timezone.utc),
    )


# ============================================================================
# Security Analysis Endpoints (Epic 8.3)
# ============================================================================


class AnalyzeFindingsRequest(BaseModel):
    """Request for comprehensive finding analysis."""

    finding_ids: List[str] = Field(..., description="List of finding IDs to analyze")
    include_explanations: bool = Field(default=True, description="Generate LLM explanations")
    include_remediation: bool = Field(default=True, description="Generate remediation plans")
    include_clusters: bool = Field(default=True, description="Correlate and cluster findings")
    target_audience: str = Field(default="general", description="Target audience (general, technical, executive)")
    prefer_terraform: bool = Field(default=True, description="Prefer Terraform in remediation examples")


class AnalyzeFindingsResponse(BaseModel):
    """Response from comprehensive finding analysis."""

    finding_count: int
    prioritized_findings: List[Dict[str, Any]]
    explanations: List[Dict[str, Any]]
    remediation_plans: List[Dict[str, Any]]
    clusters: List[Dict[str, Any]]
    summary: Dict[str, Any]


class ScoreFindingsRequest(BaseModel):
    """Request for finding scoring and prioritization."""

    finding_ids: List[str] = Field(..., description="List of finding IDs to score")


class ScoreFindingsResponse(BaseModel):
    """Response from finding scoring."""

    prioritized_findings: List[Dict[str, Any]]
    summary: Dict[str, Any]


class ExplainFindingRequest(BaseModel):
    """Request for finding explanation."""

    finding_id: str = Field(..., description="Finding ID to explain")
    target_audience: str = Field(default="general", description="Target audience")
    include_technical_details: bool = Field(default=True, description="Include technical details")


class RemediationPlanRequest(BaseModel):
    """Request for remediation plan."""

    finding_id: str = Field(..., description="Finding ID")
    prefer_terraform: bool = Field(default=True, description="Prefer Terraform examples")


class CorrelateFindingsRequest(BaseModel):
    """Request for finding correlation."""

    finding_ids: List[str] = Field(..., description="Finding IDs to correlate")
    min_cluster_size: int = Field(default=2, description="Minimum cluster size")


class CorrelateFindingsResponse(BaseModel):
    """Response from finding correlation."""

    clusters: List[Dict[str, Any]]
    cluster_summary: Dict[str, Any]


async def get_findings_service(request: Request) -> Any:
    """Get findings service from app state.

    Returns:
        FindingsService instance

    Raises:
        HTTPException: If service not available
    """
    if not hasattr(request.app.state, "findings_service"):
        raise HTTPException(
            status_code=503,
            detail="Findings service not available",
        )
    return request.app.state.findings_service


async def get_security_analysis_service(request: Request) -> Any:
    """Get security analysis service from app state.

    Returns:
        SecurityAnalysisService instance

    Raises:
        HTTPException: If service not available
    """
    if not hasattr(request.app.state, "security_analysis_service"):
        raise HTTPException(
            status_code=503,
            detail="Security analysis service not available",
        )
    return request.app.state.security_analysis_service


@router.post("/analysis/comprehensive", response_model=AnalyzeFindingsResponse)
async def analyze_findings_comprehensive(
    request_data: AnalyzeFindingsRequest,
    findings_service=Depends(get_findings_service),
    analysis_service=Depends(get_security_analysis_service),
) -> AnalyzeFindingsResponse:
    """
    Perform comprehensive security analysis on findings.

    Includes:
    - Risk scoring and prioritization
    - LLM-powered explanations
    - Remediation plan generation
    - Finding correlation and clustering

    This is the primary endpoint for end-to-end security analysis.
    """
    # Fetch findings
    findings = []
    for finding_id in request_data.finding_ids:
        from uuid import UUID

        finding = await findings_service.get_finding(UUID(finding_id))
        if finding:
            findings.append(finding)

    if not findings:
        raise HTTPException(
            status_code=404,
            detail="No findings found for the provided IDs",
        )

    # Perform comprehensive analysis
    analysis = await analysis_service.analyze_findings(
        findings=findings,
        include_explanations=request_data.include_explanations,
        include_remediation=request_data.include_remediation,
        include_clusters=request_data.include_clusters,
        target_audience=request_data.target_audience,
        prefer_terraform=request_data.prefer_terraform,
    )

    return AnalyzeFindingsResponse(**analysis)


@router.post("/analysis/score", response_model=ScoreFindingsResponse)
async def score_findings(
    request_data: ScoreFindingsRequest,
    findings_service=Depends(get_findings_service),
    analysis_service=Depends(get_security_analysis_service),
) -> ScoreFindingsResponse:
    """
    Score and prioritize security findings.

    Returns risk scores based on:
    - Severity (0-40 points)
    - Compliance impact (0-30 points)
    - Resource type (0-20 points)
    - Exposure level (0-10 points)
    """
    # Fetch findings
    findings = []
    for finding_id in request_data.finding_ids:
        from uuid import UUID

        finding = await findings_service.get_finding(UUID(finding_id))
        if finding:
            findings.append(finding)

    if not findings:
        raise HTTPException(
            status_code=404,
            detail="No findings found for the provided IDs",
        )

    # Score findings
    prioritized = await analysis_service.score_and_prioritize(findings)

    # Generate summary
    priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for p in prioritized:
        priority_counts[p.priority_rank] += 1

    return ScoreFindingsResponse(
        prioritized_findings=[p.to_dict() for p in prioritized],
        summary={
            "total_findings": len(prioritized),
            "priority_distribution": priority_counts,
        },
    )


@router.post("/analysis/explain")
async def explain_finding(
    request_data: ExplainFindingRequest,
    findings_service=Depends(get_findings_service),
    analysis_service=Depends(get_security_analysis_service),
) -> Dict[str, Any]:
    """
    Generate human-readable explanation for a security finding.

    Uses Claude AI to create contextual explanations tailored to
    the target audience (general, technical, or executive).
    """
    from uuid import UUID

    finding = await findings_service.get_finding(UUID(request_data.finding_id))

    if not finding:
        raise HTTPException(
            status_code=404,
            detail=f"Finding {request_data.finding_id} not found",
        )

    explanation = await analysis_service.explain_finding(
        finding=finding,
        target_audience=request_data.target_audience,
        include_technical_details=request_data.include_technical_details,
    )

    return explanation


@router.post("/analysis/remediation")
async def generate_remediation_plan(
    request_data: RemediationPlanRequest,
    findings_service=Depends(get_findings_service),
    analysis_service=Depends(get_security_analysis_service),
) -> Dict[str, Any]:
    """
    Generate step-by-step remediation plan for a security finding.

    Includes:
    - Detailed remediation steps
    - Terraform and AWS CLI examples
    - Prerequisites and rollback procedures
    - Documentation references
    """
    from uuid import UUID

    finding = await findings_service.get_finding(UUID(request_data.finding_id))

    if not finding:
        raise HTTPException(
            status_code=404,
            detail=f"Finding {request_data.finding_id} not found",
        )

    plan = await analysis_service.generate_remediation_plan(
        finding=finding,
        prefer_terraform=request_data.prefer_terraform,
    )

    return plan.to_dict()


@router.post("/analysis/correlate", response_model=CorrelateFindingsResponse)
async def correlate_findings(
    request_data: CorrelateFindingsRequest,
    findings_service=Depends(get_findings_service),
    analysis_service=Depends(get_security_analysis_service),
) -> CorrelateFindingsResponse:
    """
    Correlate security findings and identify clusters.

    Groups related findings by:
    - Resource type
    - AWS service
    - Compliance framework
    - Rule patterns

    Useful for batch remediation planning.
    """
    # Fetch findings
    findings = []
    for finding_id in request_data.finding_ids:
        from uuid import UUID

        finding = await findings_service.get_finding(UUID(finding_id))
        if finding:
            findings.append(finding)

    if not findings:
        raise HTTPException(
            status_code=404,
            detail="No findings found for the provided IDs",
        )

    # Correlate findings
    from ib_platform.security.correlation import FindingCorrelator

    correlator = FindingCorrelator(min_cluster_size=request_data.min_cluster_size)
    clusters = correlator.correlate_findings(findings)
    cluster_summary = correlator.get_cluster_summary(clusters)

    return CorrelateFindingsResponse(
        clusters=[c.to_dict() for c in clusters],
        cluster_summary=cluster_summary,
    )


@router.get("/analysis/top-findings")
async def analyze_top_findings(
    account_id: str,
    top_n: int = 10,
    target_audience: str = "executive",
    findings_service=Depends(get_findings_service),
    analysis_service=Depends(get_security_analysis_service),
) -> Dict[str, Any]:
    """
    Analyze top N highest priority findings for an AWS account.

    Provides executive-focused analysis suitable for leadership reporting.
    """
    from uuid import UUID

    # Get all open findings for the account
    findings = await findings_service.get_findings_by_account(
        aws_account_id=UUID(account_id),
        status="open",
        limit=1000,
    )

    if not findings:
        raise HTTPException(
            status_code=404,
            detail=f"No findings found for account {account_id}",
        )

    # Analyze top findings
    analysis = await analysis_service.analyze_top_findings(
        findings=findings,
        top_n=top_n,
        target_audience=target_audience,
    )

    return analysis
