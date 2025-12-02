# 7.4 Findings Management System

## Parent Epic
Epic 7: MVP Phase 2 - Security & Cost Scanning

## Overview

Implement the findings management system that stores, queries, and tracks remediation status for security and cost findings. Provides API for chat interface to query findings and display them to users.

## Background

After scanning, findings need to be:
- Stored persistently for reference
- Queryable by chat interface ("What did you find?")
- Trackable for remediation status
- Filterable by severity, service, compliance framework
- Accessible for reporting

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FND-001 | Finding storage | Store findings with full context, support both security and cost |
| FND-002 | Finding queries | Filter by severity, service, compliance, date range |
| FND-003 | Status tracking | Track open/acknowledged/resolved/false_positive status |
| FND-004 | Finding details | Include remediation steps, code snippets, documentation links |
| FND-005 | Finding summary | Aggregate statistics for dashboard and chat |

## Technical Specification

### Finding Service

```python
# src/cloud_optimizer/services/findings.py
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

class FindingsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_findings(
        self,
        tenant_id: UUID,
        filters: FindingFilters = None,
        pagination: Pagination = None,
    ) -> FindingsPage:
        """Get findings with filtering and pagination."""
        query = select(SecurityFinding).where(
            SecurityFinding.tenant_id == tenant_id
        )

        # Apply filters
        if filters:
            if filters.severity:
                query = query.where(SecurityFinding.severity.in_(filters.severity))
            if filters.resource_type:
                query = query.where(SecurityFinding.resource_type.in_(filters.resource_type))
            if filters.status:
                query = query.where(SecurityFinding.status.in_(filters.status))
            if filters.compliance_framework:
                # JSONB containment query
                query = query.where(
                    SecurityFinding.compliance_frameworks.contains([filters.compliance_framework])
                )
            if filters.job_id:
                query = query.where(SecurityFinding.job_id == filters.job_id)
            if filters.search:
                # Full-text search on title and description
                search_pattern = f"%{filters.search}%"
                query = query.where(
                    or_(
                        SecurityFinding.title.ilike(search_pattern),
                        SecurityFinding.description.ilike(search_pattern),
                        SecurityFinding.resource_id.ilike(search_pattern),
                    )
                )

        # Default sort by severity, then created_at
        query = query.order_by(
            case(
                (SecurityFinding.severity == "critical", 1),
                (SecurityFinding.severity == "high", 2),
                (SecurityFinding.severity == "medium", 3),
                (SecurityFinding.severity == "low", 4),
            ),
            SecurityFinding.created_at.desc(),
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()

        # Apply pagination
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.limit)
        else:
            query = query.limit(100)

        result = await self.db.execute(query)
        findings = result.scalars().all()

        return FindingsPage(
            items=findings,
            total=total,
            page=pagination.page if pagination else 1,
            page_size=pagination.limit if pagination else len(findings),
        )

    async def get_finding(self, tenant_id: UUID, finding_id: UUID) -> SecurityFinding:
        """Get single finding with full details."""
        result = await self.db.execute(
            select(SecurityFinding)
            .where(SecurityFinding.finding_id == finding_id)
            .where(SecurityFinding.tenant_id == tenant_id)
        )
        finding = result.scalar_one_or_none()
        if not finding:
            raise FindingNotFoundException()
        return finding

    async def update_status(
        self,
        tenant_id: UUID,
        finding_id: UUID,
        status: str,
        notes: str = None,
    ) -> SecurityFinding:
        """Update finding status."""
        finding = await self.get_finding(tenant_id, finding_id)

        finding.status = status
        if status == "resolved":
            finding.resolved_at = datetime.utcnow()

        finding.updated_at = datetime.utcnow()
        await self.db.commit()

        return finding

    async def get_summary(self, tenant_id: UUID) -> FindingsSummary:
        """Get aggregated findings summary."""
        # Severity breakdown
        severity_query = select(
            SecurityFinding.severity,
            func.count(SecurityFinding.finding_id).label("count"),
        ).where(
            SecurityFinding.tenant_id == tenant_id,
            SecurityFinding.status == "open",
        ).group_by(SecurityFinding.severity)

        severity_result = await self.db.execute(severity_query)
        by_severity = {row.severity: row.count for row in severity_result}

        # Resource type breakdown
        resource_query = select(
            SecurityFinding.resource_type,
            func.count(SecurityFinding.finding_id).label("count"),
        ).where(
            SecurityFinding.tenant_id == tenant_id,
            SecurityFinding.status == "open",
        ).group_by(SecurityFinding.resource_type)

        resource_result = await self.db.execute(resource_query)
        by_resource = {row.resource_type: row.count for row in resource_result}

        # Status breakdown
        status_query = select(
            SecurityFinding.status,
            func.count(SecurityFinding.finding_id).label("count"),
        ).where(
            SecurityFinding.tenant_id == tenant_id,
        ).group_by(SecurityFinding.status)

        status_result = await self.db.execute(status_query)
        by_status = {row.status: row.count for row in status_result}

        # Total counts
        total_open = sum(
            count for status, count in by_status.items() if status == "open"
        )

        return FindingsSummary(
            total_findings=sum(by_status.values()),
            open_findings=total_open,
            by_severity=by_severity,
            by_resource_type=by_resource,
            by_status=by_status,
        )

    async def get_for_chat(self, tenant_id: UUID, query: str) -> list[FindingForChat]:
        """Get findings formatted for chat response."""
        # Parse natural language query for filters
        filters = self._parse_chat_query(query)

        # Get top findings
        page = await self.get_findings(
            tenant_id,
            filters=filters,
            pagination=Pagination(limit=10),
        )

        return [
            FindingForChat(
                resource=f.resource_name or f.resource_id,
                title=f.title,
                severity=f.severity,
                compliance=f.compliance_frameworks,
                remediation=f.remediation_steps[0] if f.remediation_steps else None,
            )
            for f in page.items
        ]

    def _parse_chat_query(self, query: str) -> FindingFilters:
        """Parse natural language into filters."""
        filters = FindingFilters()

        query_lower = query.lower()

        # Severity keywords
        if "critical" in query_lower:
            filters.severity = ["critical"]
        elif "high" in query_lower:
            filters.severity = ["critical", "high"]

        # Resource types
        if "s3" in query_lower or "bucket" in query_lower:
            filters.resource_type = ["s3_bucket"]
        elif "ec2" in query_lower or "instance" in query_lower:
            filters.resource_type = ["ec2_instance"]
        elif "rds" in query_lower or "database" in query_lower:
            filters.resource_type = ["rds_instance"]

        # Compliance frameworks
        if "hipaa" in query_lower:
            filters.compliance_framework = "HIPAA"
        elif "soc" in query_lower or "soc2" in query_lower:
            filters.compliance_framework = "SOC2"
        elif "pci" in query_lower:
            filters.compliance_framework = "PCI-DSS"

        return filters
```

### Finding Models

```python
# src/cloud_optimizer/schemas/findings.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FindingFilters(BaseModel):
    severity: Optional[list[str]] = None
    resource_type: Optional[list[str]] = None
    status: Optional[list[str]] = None
    compliance_framework: Optional[str] = None
    job_id: Optional[UUID] = None
    search: Optional[str] = None


class Pagination(BaseModel):
    page: int = 1
    limit: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class FindingResponse(BaseModel):
    finding_id: UUID
    resource_type: str
    resource_id: str
    resource_name: Optional[str]
    region: str
    rule_id: str
    title: str
    description: str
    severity: str
    compliance_frameworks: list[str]
    remediation_steps: list[str]
    remediation_code: Optional[str]
    documentation_url: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FindingsPage(BaseModel):
    items: list[FindingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


class FindingsSummary(BaseModel):
    total_findings: int
    open_findings: int
    by_severity: dict[str, int]
    by_resource_type: dict[str, int]
    by_status: dict[str, int]


class FindingForChat(BaseModel):
    """Simplified finding for chat responses."""
    resource: str
    title: str
    severity: str
    compliance: list[str]
    remediation: Optional[str]


class UpdateFindingStatus(BaseModel):
    status: str  # open, acknowledged, resolved, false_positive
    notes: Optional[str] = None
```

### API Router

```python
# src/cloud_optimizer/api/routers/findings.py
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/api/v1/findings", tags=["findings"])

@router.get("", response_model=FindingsPage)
async def list_findings(
    severity: list[str] = Query(None),
    resource_type: list[str] = Query(None),
    status: list[str] = Query(None),
    compliance: str = Query(None),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: UUID = Depends(get_tenant_id),
    findings_service: FindingsService = Depends(get_findings_service),
):
    """List findings with filtering and pagination."""
    filters = FindingFilters(
        severity=severity,
        resource_type=resource_type,
        status=status,
        compliance_framework=compliance,
        search=search,
    )
    pagination = Pagination(page=page, limit=limit)

    return await findings_service.get_findings(tenant_id, filters, pagination)


@router.get("/summary", response_model=FindingsSummary)
async def get_summary(
    tenant_id: UUID = Depends(get_tenant_id),
    findings_service: FindingsService = Depends(get_findings_service),
):
    """Get aggregated findings summary."""
    return await findings_service.get_summary(tenant_id)


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    findings_service: FindingsService = Depends(get_findings_service),
):
    """Get finding details."""
    return await findings_service.get_finding(tenant_id, finding_id)


@router.put("/{finding_id}/status", response_model=FindingResponse)
async def update_status(
    finding_id: UUID,
    body: UpdateFindingStatus,
    tenant_id: UUID = Depends(get_tenant_id),
    findings_service: FindingsService = Depends(get_findings_service),
):
    """Update finding status."""
    return await findings_service.update_status(
        tenant_id, finding_id, body.status, body.notes
    )


@router.get("/for-chat", response_model=list[FindingForChat])
async def get_for_chat(
    query: str = Query(..., description="Natural language query"),
    tenant_id: UUID = Depends(get_tenant_id),
    findings_service: FindingsService = Depends(get_findings_service),
):
    """Get findings formatted for chat response."""
    return await findings_service.get_for_chat(tenant_id, query)
```

## API Endpoints

```
GET  /api/v1/findings                # List findings (with filters)
GET  /api/v1/findings/summary        # Get aggregated summary
GET  /api/v1/findings/:id            # Get finding details
PUT  /api/v1/findings/:id/status     # Update status
GET  /api/v1/findings/for-chat       # Get findings for chat
GET  /api/v1/findings/export         # Export findings (CSV/JSON)
```

## Files to Create

```
src/cloud_optimizer/services/
└── findings.py                  # Findings service

src/cloud_optimizer/schemas/
└── findings.py                  # Pydantic schemas

src/cloud_optimizer/api/routers/
└── findings.py                  # API endpoints

tests/services/
└── test_findings.py             # Findings service tests

tests/api/
└── test_findings_api.py         # API tests
```

## Testing Requirements

### Unit Tests
- [ ] `test_findings_filters.py` - Filter query building
- [ ] `test_findings_pagination.py` - Pagination logic
- [ ] `test_findings_summary.py` - Aggregation logic
- [ ] `test_chat_query_parsing.py` - NL to filters

### Integration Tests
- [ ] `test_findings_service.py` - Full service with DB
- [ ] `test_findings_api.py` - API endpoints

## Acceptance Criteria Checklist

- [ ] Findings stored with full context
- [ ] Filter by severity works
- [ ] Filter by resource type works
- [ ] Filter by status works
- [ ] Filter by compliance framework works
- [ ] Full-text search works
- [ ] Pagination with correct totals
- [ ] Status update persists
- [ ] Summary aggregation accurate
- [ ] Chat query parsing extracts filters
- [ ] Export to CSV/JSON works
- [ ] 80%+ test coverage

## Dependencies

- 7.2 Security Scanner (generates findings)
- 7.3 Cost Scanner (generates findings)

## Blocked By

- 7.2 Security Scanner

## Blocks

- 8.3 Security Analysis (IB queries findings)

## Estimated Effort

1 week

## Labels

`findings`, `data`, `api`, `mvp`, `phase-2`, `P0`
