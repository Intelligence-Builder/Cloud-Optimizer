# Epic 2: Security Domain Implementation

## Overview

Implement the Security domain as the priority domain for Cloud Optimizer v2, including entity types, relationship types, detection patterns, and API endpoints.

**Priority**: High
**Dependencies**: Epic 1 (Platform Foundation) complete

## Objectives

1. Define complete Security domain with 9 entity types and 7 relationship types
2. Create security-specific detection patterns for CVEs, compliance, IAM, encryption
3. Build Security API endpoints for scanning and analysis

## Entity Types

- `vulnerability` - CVEs, security flaws
- `threat` - Threat actors, attack vectors
- `control` - Security controls (WAF, encryption)
- `compliance_requirement` - SOC2, HIPAA, PCI requirements
- `encryption_config` - Encryption settings
- `access_policy` - IAM policies
- `security_group` - Network security groups
- `security_finding` - Audit findings
- `identity` - Users, roles, service accounts

## Relationship Types

- `mitigates` - Control mitigates vulnerability
- `exposes` - Resource exposes to vulnerability
- `requires` - Compliance requires control
- `implements` - Control implements compliance
- `violates` - Finding violates compliance
- `protects` - Security group protects resource
- `grants_access` - Policy grants access to identity

## Acceptance Criteria

- [ ] All 9 entity types registered and validated
- [ ] All 7 relationship types working
- [ ] Pattern detection accuracy > 85% on test documents
- [ ] CVE pattern extracts CVE ID, year, and severity
- [ ] Compliance patterns detect SOC2, HIPAA, PCI-DSS, GDPR
- [ ] API endpoints functional with proper error handling
- [ ] Integration tests passing
- [ ] OpenAPI documentation complete

## API Endpoints

```
POST   /api/v1/security/scan
GET    /api/v1/security/vulnerabilities
GET    /api/v1/security/vulnerabilities/{id}
POST   /api/v1/security/vulnerabilities
GET    /api/v1/security/controls
POST   /api/v1/security/controls
GET    /api/v1/security/compliance
POST   /api/v1/security/compliance/check
GET    /api/v1/security/findings
GET    /api/v1/security/graph
```

## Sub-Tasks

- #9 - 2.1 Security Domain Definition
- #10 - 2.2 Security Patterns Implementation
- #11 - 2.3 Security API Endpoints

---

## Integration Test Specification

### Test Environment

| Component | Configuration | Notes |
|-----------|---------------|-------|
| IB Platform | localhost:8000 | Running with security domain |
| PostgreSQL | localhost:5432/intelligence | With security schema |
| API Server | localhost:8080 | FastAPI test server |

```yaml
# tests/integration/conftest.py
IB_PLATFORM_URL: http://localhost:8000
IB_API_KEY: test-api-key
TENANT_ID: test-security
TEST_TIMEOUT: 30
```

### End-to-End Test Scenarios

| ID | Scenario | Flow | Input | Expected Output |
|----|----------|------|-------|-----------------|
| E2-INT-01 | CVE Scan Flow | POST /scan → IB entities | Text with CVE-2021-44228 | vulnerability entity created |
| E2-INT-02 | Compliance Detection | POST /scan → compliance entities | SOC2/HIPAA document | compliance_requirement entities |
| E2-INT-03 | Mitigation Graph | Create vuln → Create control → Link | vulnerability + control | mitigates relationship |
| E2-INT-04 | Compliance Coverage | /compliance/check | framework=SOC2 | coverage percentage + gaps |
| E2-INT-05 | Security Graph Query | /graph | entity_types filter | Visualization-ready subgraph |
| E2-INT-06 | Full Scan Pipeline | Document → Entities → Relationships | Security assessment doc | Complete knowledge graph |

### Test Data Fixtures

```
tests/
├── fixtures/
│   └── security/
│       ├── documents/
│       │   ├── cve_report.txt              # CVE references
│       │   ├── compliance_audit.txt         # SOC2/HIPAA content
│       │   ├── aws_security_config.json     # IAM/SG configs
│       │   └── full_security_assessment.md  # Complete assessment
│       ├── expected/
│       │   ├── cve_entities.json            # Expected CVE entities
│       │   ├── compliance_entities.json     # Expected compliance entities
│       │   └── full_assessment_graph.json   # Expected full graph
│       └── api_requests/
│           ├── scan_cve_request.json
│           ├── create_vulnerability.json
│           └── compliance_check_soc2.json
```

### Sample Test Document

```text
# tests/fixtures/security/documents/full_security_assessment.md

## Security Assessment - Q4 2024

### Critical Vulnerabilities
- CVE-2021-44228 (CVSS: 10.0) - Log4j RCE vulnerability affecting logging infrastructure
- CVE-2023-12345 (CVSS: 8.5) - Authentication bypass in API gateway

### Mitigating Controls
- WAF rules mitigate CVE-2021-44228 by blocking JNDI lookup patterns
- MFA implementation mitigates credential-based attacks

### Compliance Status
Our SOC 2 Type II certification requires:
- Encryption at rest using AES-256 for all PII data
- TLS 1.3 for data in transit (HIPAA requirement)
- PCI-DSS requirement 3.4 for cardholder data encryption

### AWS Configuration Issues
- Security group sg-0abc123def allows ingress 0.0.0.0/0 on port 22
- IAM policy AdminFullAccess grants excessive permissions
- Role arn:aws:iam::123456789012:role/LambdaAdmin has admin access
```

### Integration Test Implementation

```python
# tests/integration/test_epic2_security.py
"""Epic 2 Integration Tests - Security Domain"""

import pytest
from httpx import AsyncClient
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "security"


class TestCVEScanFlow:
    """E2-INT-01: CVE detection creates entities in IB."""

    @pytest.fixture
    def cve_document(self):
        return (FIXTURES / "documents" / "cve_report.txt").read_text()

    @pytest.mark.asyncio
    async def test_scan_creates_vulnerability_entities(self, api_client: AsyncClient, cve_document):
        """POST /scan with CVE text creates vulnerability entities."""
        response = await api_client.post(
            "/api/v1/security/scan",
            json={"text": cve_document, "min_confidence": 0.5}
        )

        assert response.status_code == 200
        result = response.json()
        assert result["entities_found"] >= 2

        # Verify CVE entities created
        vulns = [e for e in result["entities"] if e["entity_type"] == "vulnerability"]
        assert len(vulns) >= 2

        cve_ids = [v["properties"].get("cve_id") for v in vulns]
        assert "CVE-2021-44228" in cve_ids
        assert "CVE-2023-12345" in cve_ids

    @pytest.mark.asyncio
    async def test_cvss_score_extracted(self, api_client: AsyncClient, cve_document):
        """CVE patterns extract CVSS scores."""
        response = await api_client.post(
            "/api/v1/security/scan",
            json={"text": cve_document}
        )

        vulns = [e for e in response.json()["entities"]
                 if e["properties"].get("cve_id") == "CVE-2021-44228"]
        assert vulns[0]["properties"]["cvss_score"] == 10.0


class TestComplianceDetection:
    """E2-INT-02: Compliance framework detection."""

    @pytest.fixture
    def compliance_document(self):
        return (FIXTURES / "documents" / "compliance_audit.txt").read_text()

    @pytest.mark.asyncio
    async def test_detects_multiple_frameworks(self, api_client: AsyncClient, compliance_document):
        """Scan detects SOC2, HIPAA, PCI-DSS references."""
        response = await api_client.post(
            "/api/v1/security/scan",
            json={"text": compliance_document}
        )

        compliance_entities = [
            e for e in response.json()["entities"]
            if e["entity_type"] == "compliance_requirement"
        ]

        frameworks = {e["properties"]["framework"] for e in compliance_entities}
        assert "SOC2" in frameworks or "SOC 2" in frameworks
        assert "HIPAA" in frameworks
        assert "PCI-DSS" in frameworks


class TestMitigationGraph:
    """E2-INT-03: Vulnerability-Control-Mitigates relationship flow."""

    @pytest.mark.asyncio
    async def test_create_mitigation_relationship(self, api_client: AsyncClient):
        """Create vulnerability, control, and mitigates relationship."""
        # 1. Create vulnerability
        vuln_response = await api_client.post(
            "/api/v1/security/vulnerabilities",
            json={
                "name": "Log4Shell",
                "cve_id": "CVE-2021-44228",
                "severity": "critical",
                "cvss_score": 10.0
            }
        )
        assert vuln_response.status_code == 201
        vuln_id = vuln_response.json()["id"]

        # 2. Create control
        control_response = await api_client.post(
            "/api/v1/security/controls",
            json={
                "name": "WAF JNDI Block Rule",
                "control_type": "preventive",
                "effectiveness": 0.95
            }
        )
        assert control_response.status_code == 201
        control_id = control_response.json()["id"]

        # 3. Verify mitigates relationship can be queried
        vuln_detail = await api_client.get(
            f"/api/v1/security/vulnerabilities/{vuln_id}?include_mitigations=true"
        )
        # Note: Relationship would be created via scan or explicit API


class TestComplianceCoverage:
    """E2-INT-04: Compliance coverage check."""

    @pytest.mark.asyncio
    async def test_soc2_coverage_check(self, api_client: AsyncClient, seeded_compliance_data):
        """Check SOC2 compliance returns coverage metrics."""
        response = await api_client.post(
            "/api/v1/security/compliance/check",
            json={"framework": "SOC2"}
        )

        assert response.status_code == 200
        result = response.json()

        assert "total_requirements" in result
        assert "implemented" in result
        assert "coverage_percentage" in result
        assert "gaps" in result
        assert 0 <= result["coverage_percentage"] <= 100


class TestFullScanPipeline:
    """E2-INT-06: Complete security assessment scan."""

    @pytest.fixture
    def full_assessment(self):
        return (FIXTURES / "documents" / "full_security_assessment.md").read_text()

    @pytest.mark.asyncio
    async def test_full_assessment_creates_complete_graph(
        self, api_client: AsyncClient, full_assessment
    ):
        """Full assessment creates entities and relationships."""
        response = await api_client.post(
            "/api/v1/security/scan",
            json={
                "text": full_assessment,
                "include_relationships": True,
                "min_confidence": 0.5
            }
        )

        assert response.status_code == 200
        result = response.json()

        # Verify diverse entity types
        entity_types = {e["entity_type"] for e in result["entities"]}
        assert "vulnerability" in entity_types
        assert "compliance_requirement" in entity_types
        assert "security_group" in entity_types or "access_policy" in entity_types

        # Verify relationships created
        assert result["relationships_found"] >= 1

        # Verify processing time acceptable
        assert result["processing_time_ms"] < 5000  # 5 seconds max
```

### Performance Benchmarks

| Operation | Requirement | Test Method | Input Size |
|-----------|-------------|-------------|------------|
| POST /scan (1KB) | < 200ms | Response time | 1KB document |
| POST /scan (100KB) | < 5s | Response time | 100KB document |
| GET /vulnerabilities | < 100ms | Response time | 1000 entities |
| GET /graph | < 500ms | Response time | 500 nodes |
| /compliance/check | < 1s | Response time | Full framework |

### API Contract Tests

```python
# tests/integration/test_epic2_api_contracts.py
"""API contract validation for security endpoints."""

class TestSecurityAPIContracts:

    @pytest.mark.asyncio
    async def test_scan_response_schema(self, api_client):
        """POST /scan returns correct schema."""
        response = await api_client.post(
            "/api/v1/security/scan",
            json={"text": "CVE-2021-44228 critical vulnerability"}
        )

        data = response.json()
        assert "entities_found" in data
        assert "relationships_found" in data
        assert "entities" in data
        assert "processing_time_ms" in data
        assert isinstance(data["entities"], list)

    @pytest.mark.asyncio
    async def test_vulnerability_create_validation(self, api_client):
        """POST /vulnerabilities validates input."""
        # Invalid CVE format should fail
        response = await api_client.post(
            "/api/v1/security/vulnerabilities",
            json={"name": "Test", "cve_id": "INVALID"}
        )
        assert response.status_code == 422

        # Missing required field should fail
        response = await api_client.post(
            "/api/v1/security/vulnerabilities",
            json={"cve_id": "CVE-2021-44228"}  # Missing name
        )
        assert response.status_code == 422
```

### CI Integration

```yaml
# .github/workflows/integration-tests.yml
epic2-integration:
  needs: [epic1-integration]
  runs-on: ubuntu-latest
  services:
    ib-platform:
      image: intelligence-builder:latest
      ports:
        - 8000:8000

  steps:
    - uses: actions/checkout@v4
    - run: pip install -r requirements-test.txt
    - run: |
        # Wait for IB platform
        timeout 60 bash -c 'until curl -s localhost:8000/health; do sleep 2; done'
    - run: pytest tests/integration/test_epic2_*.py -v --tb=short
```
