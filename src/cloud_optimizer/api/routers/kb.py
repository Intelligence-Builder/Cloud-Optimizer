"""Knowledge Base API endpoints for Cloud Optimizer.

Provides access to compliance controls, best practices, security patterns,
and remediation templates.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from cloud_optimizer.api.schemas.kb import (
    ComplianceControlResponse,
    FrameworkControlsResponse,
    FrameworkListResponse,
    KBEntryResponse,
    KBStatisticsResponse,
    RemediationTemplateResponse,
    SearchResultsResponse,
    ServiceListResponse,
    ServicePracticesResponse,
)
from ib_platform.kb.service import KnowledgeBaseService, get_kb_service

router = APIRouter()


def get_kb() -> KnowledgeBaseService:
    """Dependency to get Knowledge Base service.

    Returns:
        KnowledgeBaseService singleton instance
    """
    kb = get_kb_service()
    if not kb.is_loaded():
        kb.load()
    return kb


KBServiceDep = Annotated[KnowledgeBaseService, Depends(get_kb)]


@router.get(
    "/frameworks",
    response_model=FrameworkListResponse,
    summary="List available compliance frameworks",
    description="Get a list of all available compliance frameworks in the KB",
)
async def list_frameworks(kb: KBServiceDep) -> FrameworkListResponse:
    """List all available compliance frameworks.

    Returns:
        FrameworkListResponse with framework names and count
    """
    stats = kb.get_statistics()
    framework_names = sorted(
        [name for name in kb._frameworks.keys()]  # noqa: SLF001
    )

    return FrameworkListResponse(
        frameworks=framework_names,
        total=stats["frameworks"],
    )


@router.get(
    "/frameworks/{framework_id}/controls",
    response_model=FrameworkControlsResponse,
    summary="Get framework controls",
    description="Get all controls for a specific compliance framework",
    responses={
        404: {"description": "Framework not found"},
    },
)
async def get_framework_controls(
    framework_id: str,
    kb: KBServiceDep,
) -> FrameworkControlsResponse:
    """Get all controls for a specific framework.

    Args:
        framework_id: Framework identifier (e.g., "CIS", "NIST", "PCI-DSS")
        kb: Knowledge Base service dependency

    Returns:
        FrameworkControlsResponse with controls list

    Raises:
        404: If framework is not found
    """
    controls = kb.get_framework_controls(framework_id)

    if controls is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Framework '{framework_id}' not found",
        )

    # Convert to response models
    control_responses = [
        ComplianceControlResponse(
            framework=c.framework,
            control_id=c.control_id,
            name=c.name,
            description=c.description,
            requirements=c.requirements,
            aws_services=c.aws_services,
            implementation_guidance=c.implementation_guidance,
        )
        for c in controls
    ]

    return FrameworkControlsResponse(
        framework=framework_id.upper(),
        controls=control_responses,
        total=len(control_responses),
    )


@router.get(
    "/services",
    response_model=ServiceListResponse,
    summary="List available AWS services",
    description="Get a list of all AWS services with best practices in the KB",
)
async def list_services(kb: KBServiceDep) -> ServiceListResponse:
    """List all AWS services with best practices.

    Returns:
        ServiceListResponse with service names and count
    """
    stats = kb.get_statistics()
    service_names = sorted(
        [name for name in kb._services.keys()]  # noqa: SLF001
    )

    return ServiceListResponse(
        services=service_names,
        total=stats["services"],
    )


@router.get(
    "/services/{service_id}/practices",
    response_model=ServicePracticesResponse,
    summary="Get service best practices",
    description="Get best practices for a specific AWS service",
    responses={
        404: {"description": "Service not found or no practices available"},
    },
)
async def get_service_practices(
    service_id: str,
    category: Optional[str] = Query(
        None,
        description="Filter by category (e.g., security, cost, performance)",
    ),
    kb: KBServiceDep = Depends(get_kb),
) -> ServicePracticesResponse:
    """Get best practices for a specific AWS service.

    Args:
        service_id: AWS service identifier (e.g., "S3", "EC2", "RDS")
        category: Optional category filter
        kb: Knowledge Base service dependency

    Returns:
        ServicePracticesResponse with practices list

    Raises:
        404: If service is not found or has no practices
    """
    practices = kb.get_service_best_practices(service_id, category)

    if not practices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_id}' not found or has no practices",
        )

    # Convert to response models - use model_validate instead of direct assignment
    from cloud_optimizer.api.schemas.kb import ServiceBestPracticeResponse

    practice_responses = [
        ServiceBestPracticeResponse(
            service=p.service,
            category=p.category,
            title=p.title,
            description=p.description,
            compliance_frameworks=p.compliance_frameworks,
            implementation=p.implementation,
            terraform_example=p.terraform_example,
            cli_example=p.cli_example,
            console_steps=p.console_steps,
        )
        for p in practices
    ]

    return ServicePracticesResponse(
        service=service_id.upper(),
        practices=practice_responses,
        total=len(practice_responses),
    )


@router.get(
    "/search",
    response_model=SearchResultsResponse,
    summary="Search Knowledge Base",
    description="Search KB entries by keyword across all content types",
)
async def search_kb(
    q: str = Query(..., description="Search query", min_length=1),
    limit: int = Query(10, description="Maximum results to return", ge=1, le=100),
    kb: KBServiceDep = Depends(get_kb),
) -> SearchResultsResponse:
    """Search Knowledge Base entries by keyword.

    Performs case-insensitive search across compliance controls, best practices,
    security patterns, and remediation templates.

    Args:
        q: Search query string
        limit: Maximum number of results (1-100, default: 10)
        kb: Knowledge Base service dependency

    Returns:
        SearchResultsResponse with matching entries
    """
    results = kb.search(q, limit)

    # Convert to response models
    entry_responses = [
        KBEntryResponse(
            entry_type=e.entry_type,
            control_name=e.control_name,
            description=e.description,
            guidance=e.guidance,
            framework=e.framework,
            service=e.service,
            terraform=e.terraform,
            cli=e.cli,
            metadata=e.metadata,
        )
        for e in results
    ]

    return SearchResultsResponse(
        query=q,
        results=entry_responses,
        total=len(entry_responses),
        limit=limit,
    )


@router.get(
    "/remediation/{rule_id}",
    response_model=RemediationTemplateResponse,
    summary="Get remediation template",
    description="Get remediation guidance for a specific security rule",
    responses={
        404: {"description": "Remediation template not found"},
    },
)
async def get_remediation(
    rule_id: str,
    kb: KBServiceDep,
) -> RemediationTemplateResponse:
    """Get remediation template for a security rule.

    Args:
        rule_id: Security rule identifier
        kb: Knowledge Base service dependency

    Returns:
        RemediationTemplateResponse with remediation guidance

    Raises:
        404: If remediation template is not found
    """
    template = kb.get_remediation(rule_id)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Remediation template for rule '{rule_id}' not found",
        )

    return RemediationTemplateResponse(
        template_id=template.template_id,
        rule_id=template.rule_id,
        title=template.title,
        description=template.description,
        terraform=template.terraform,
        cli=template.cli,
        console_steps=template.console_steps,
    )


@router.get(
    "/stats",
    response_model=KBStatisticsResponse,
    summary="Get Knowledge Base statistics",
    description="Get counts and statistics about KB content",
)
async def get_statistics(kb: KBServiceDep) -> KBStatisticsResponse:
    """Get Knowledge Base statistics.

    Returns:
        KBStatisticsResponse with counts of various KB data types
    """
    stats = kb.get_statistics()

    return KBStatisticsResponse(
        frameworks=stats["frameworks"],
        total_controls=stats["total_controls"],
        services=stats["services"],
        total_practices=stats["total_practices"],
        patterns=stats["patterns"],
        remediation_templates=stats["remediation_templates"],
    )
