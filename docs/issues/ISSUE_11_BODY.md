## Parent Epic
Part of #2 (Epic 2: Security Domain Implementation)

## Reference Documentation
**See `docs/platform/TECHNICAL_DESIGN.md` Section 6 for API specifications**

## Objective
Build Security API endpoints for scanning and analysis.

## File Structure
```
src/platform/api/
├── __init__.py
├── main.py              # FastAPI app
├── dependencies.py      # Dependency injection
└── v1/
    ├── __init__.py
    ├── security.py      # Security endpoints
    └── schemas/
        └── security.py  # Pydantic models
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/security/scan | Scan text for security entities |
| GET | /api/v1/security/vulnerabilities | List vulnerabilities |
| GET | /api/v1/security/vulnerabilities/{id} | Get vulnerability by ID |
| POST | /api/v1/security/vulnerabilities | Create vulnerability entity |
| GET | /api/v1/security/controls | List security controls |
| POST | /api/v1/security/controls | Create security control |
| GET | /api/v1/security/compliance | List compliance requirements |
| POST | /api/v1/security/compliance/check | Check compliance status |
| GET | /api/v1/security/findings | List security findings |
| GET | /api/v1/security/graph | Get security knowledge graph |

## Key Request/Response Models

### SecurityScanRequest
```python
class SecurityScanRequest(BaseModel):
    text: str
    document_id: Optional[UUID] = None
    min_confidence: float = 0.5
    include_relationships: bool = True
```

### SecurityScanResult
```python
class SecurityScanResult(BaseModel):
    document_id: Optional[UUID]
    entities_found: int
    relationships_found: int
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    processing_time_ms: float
```

### VulnerabilityCreate
```python
class VulnerabilityCreate(BaseModel):
    name: str
    cve_id: Optional[str]  # Pattern: CVE-YYYY-NNNNN
    severity: Optional[SeverityLevel]
    cvss_score: Optional[float]  # 0.0-10.0
    description: Optional[str]
```

### ComplianceCheckResult
```python
class ComplianceCheckResult(BaseModel):
    framework: str
    total_requirements: int
    implemented: int
    gaps: List[Dict[str, Any]]
    coverage_percentage: float
```

## Test Scenarios

```python
class TestSecurityScan:
    async def test_scan_detects_cve()
    async def test_scan_creates_entities()
    async def test_scan_with_relationships()

class TestVulnerabilities:
    async def test_list_vulnerabilities()
    async def test_filter_by_severity()
    async def test_create_vulnerability()
    async def test_get_with_mitigations()

class TestCompliance:
    async def test_compliance_check_soc2()
    async def test_compliance_returns_gaps()
```

## Acceptance Criteria
- [ ] All 10 endpoints implemented and functional
- [ ] Pydantic schemas validate all inputs
- [ ] POST /scan creates entities in knowledge graph
- [ ] GET endpoints support filtering and pagination
- [ ] Compliance check returns coverage metrics
- [ ] Graph endpoint returns visualization-ready data
- [ ] Proper HTTP status codes (200, 201, 400, 404, 500)
- [ ] OpenAPI documentation complete at /docs
- [ ] Integration tests for all endpoints
- [ ] Response time < 200ms for standard queries
