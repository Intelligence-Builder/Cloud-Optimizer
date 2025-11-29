# AI Developer Guide - Cloud Optimizer v2

**Document Version**: 1.0
**Created**: 2025-11-28
**Status**: MANDATORY - Master reference for AI-assisted development
**Project**: Cloud Optimizer v2 (Intelligence-Builder Integration)

## Document Purpose

This guide establishes quality-first standards for AI-assisted development on Cloud Optimizer v2. CO v2 is a **clean-slate rebuild** consuming Intelligence-Builder platform via SDK, targeting **< 10K LOC** with enterprise-grade quality.

## Table of Contents

1. [Architecture Constraints](#1-architecture-constraints)
2. [Quality-First Philosophy](#2-quality-first-philosophy)
3. [Code Generation Standards](#3-code-generation-standards)
4. [File Structure & Limits](#4-file-structure--limits)
5. [IB SDK Integration Patterns](#5-ib-sdk-integration-patterns)
6. [Testing Methodology](#6-testing-methodology)
7. [Quality Assembly Line](#7-quality-assembly-line)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Architecture Constraints

### 1.1 Core Principle: Thin Client

> **Cloud Optimizer v2 is a THIN CLIENT consuming Intelligence-Builder platform services**

CO v2 does NOT implement:
- Graph database operations (use IB SDK)
- Pattern detection (use IB SDK)
- Entity/relationship management (use IB SDK)
- Vector search (use IB SDK)

CO v2 ONLY implements:
- AWS integration and scanning
- Security findings transformation
- Dashboard and API endpoints
- Business logic specific to cloud optimization

### 1.2 Forbidden Patterns

```python
# FORBIDDEN: Direct database access
import asyncpg
conn = await asyncpg.connect(...)  # NEVER DO THIS

# FORBIDDEN: Implementing graph operations
class GraphBackend:  # THIS BELONGS IN IB, NOT CO

# FORBIDDEN: Pattern detection
import re
patterns = [...]  # USE IB SDK INSTEAD
```

### 1.3 Required Pattern: SDK-Only Access

```python
# CORRECT: Always use IB SDK
from intelligence_builder_sdk import IBPlatformClient

async with IBPlatformClient(
    base_url=settings.IB_PLATFORM_URL,
    api_key=settings.IB_API_KEY,
    tenant_id=settings.TENANT_ID,
) as ib:
    # Create entities via SDK
    entity = await ib.entities.create(
        entity_type="vulnerability",
        name="CVE-2021-44228",
        domain="security",
    )

    # Traverse graph via SDK
    related = await ib.graph.traverse(
        start_node_id=entity.id,
        max_depth=2,
    )
```

---

## 2. Quality-First Philosophy

### 2.1 Core Principle

> **Quality must be built into code FROM THE MOMENT OF CREATION, not retrofitted afterward**

### 2.2 Mandatory Requirements

**ALL generated code MUST have:**
- Complete type hints on ALL functions
- Structured logging with `logging.getLogger(__name__)`
- Comprehensive docstrings (Google style)
- Error handling with specific exceptions
- Test file created FIRST (TDD approach)

### 2.3 Forbidden Practices

- **NEVER use `--no-verify`** when committing
- **NEVER bypass pre-commit hooks**
- **NEVER exceed 500 lines per file**
- **NEVER exceed 10 cyclomatic complexity per function**
- **NEVER bypass IB SDK** with direct database access

### 2.4 LOC Budget

| Component | Max LOC | Purpose |
|-----------|---------|---------|
| `src/cloud_optimizer/` | 5,000 | Core application |
| `tests/` | 3,000 | Test coverage |
| `docs/` | 2,000 | Documentation |
| **Total** | **10,000** | Hard limit |

---

## 3. Code Generation Standards

### 3.1 Function Template

```python
"""Module description with clear purpose."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from intelligence_builder_sdk import IBPlatformClient
from .config import settings
from .exceptions import ScanError, ValidationError

logger = logging.getLogger(__name__)


async def scan_security_groups(
    ib_client: IBPlatformClient,
    aws_account_id: str,
    region: str = "us-east-1",
) -> List[Dict[str, Any]]:
    """
    Scan AWS security groups and push findings to Intelligence-Builder.

    Args:
        ib_client: Intelligence-Builder SDK client
        aws_account_id: AWS account to scan
        region: AWS region to scan

    Returns:
        List of security findings created in IB

    Raises:
        ScanError: When AWS scan fails
        ValidationError: When findings validation fails

    Example:
        >>> async with IBPlatformClient(...) as ib:
        ...     findings = await scan_security_groups(ib, "123456789", "us-east-1")
        ...     print(f"Found {len(findings)} issues")
    """
    logger.info(
        "Starting security group scan",
        extra={"aws_account": aws_account_id, "region": region}
    )

    try:
        # 1. Scan AWS
        raw_findings = await _scan_aws_security_groups(aws_account_id, region)

        # 2. Transform to IB entities
        entities = [_transform_finding(f) for f in raw_findings]

        # 3. Push to IB via SDK
        created = await ib_client.entities.batch_create(entities)

        logger.info(
            "Security group scan complete",
            extra={"findings_count": len(created)}
        )
        return created

    except Exception as e:
        logger.error(f"Security group scan failed: {e}", exc_info=True)
        raise ScanError(f"Scan failed: {str(e)}")
```

### 3.2 Service Class Template

```python
"""Security scanning service for Cloud Optimizer."""

import logging
from typing import Dict, List, Optional

from intelligence_builder_sdk import IBPlatformClient

from .config import settings

logger = logging.getLogger(__name__)


class SecurityService:
    """
    Security scanning service using Intelligence-Builder platform.

    This service orchestrates AWS security scans and manages findings
    through the IB SDK. It does NOT implement graph operations directly.
    """

    def __init__(self, ib_client: IBPlatformClient):
        """
        Initialize security service.

        Args:
            ib_client: Intelligence-Builder SDK client (injected)
        """
        self.ib = ib_client
        self.logger = logging.getLogger(__name__)

    async def scan_account(
        self,
        aws_account_id: str,
        scan_types: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        Perform comprehensive security scan of AWS account.

        Args:
            aws_account_id: AWS account to scan
            scan_types: Optional list of scan types (default: all)

        Returns:
            Dict with counts by finding type
        """
        scan_types = scan_types or ["security_groups", "iam", "encryption"]
        results = {}

        for scan_type in scan_types:
            findings = await self._run_scan(scan_type, aws_account_id)
            results[scan_type] = len(findings)

        return results
```

### 3.3 API Endpoint Template

```python
"""Security API endpoints for Cloud Optimizer."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_ib_client, get_security_service
from ..schemas.security import ScanRequest, ScanResult, FindingResponse
from ..services.security import SecurityService

router = APIRouter(prefix="/api/v1/security", tags=["security"])


@router.post("/scan", response_model=ScanResult)
async def trigger_security_scan(
    request: ScanRequest,
    security_service: SecurityService = Depends(get_security_service),
):
    """
    Trigger security scan for AWS account.

    Scans the specified AWS account and pushes findings to
    Intelligence-Builder platform via SDK.
    """
    try:
        results = await security_service.scan_account(
            aws_account_id=request.aws_account_id,
            scan_types=request.scan_types,
        )
        return ScanResult(success=True, findings_by_type=results)
    except Exception as e:
        raise HTTPException(500, f"Scan failed: {str(e)}")


@router.get("/findings", response_model=List[FindingResponse])
async def list_findings(
    severity: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    security_service: SecurityService = Depends(get_security_service),
):
    """List security findings from Intelligence-Builder."""
    return await security_service.get_findings(severity=severity, limit=limit)
```

---

## 4. File Structure & Limits

### 4.1 Project Structure

```
cloud-optimizer/
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI pipeline
│       └── release.yml         # Release workflow
├── src/
│   └── cloud_optimizer/
│       ├── __init__.py
│       ├── main.py             # FastAPI app (< 100 lines)
│       ├── config.py           # Settings (< 100 lines)
│       ├── dependencies.py     # DI container (< 100 lines)
│       ├── exceptions.py       # Custom exceptions (< 50 lines)
│       ├── api/
│       │   ├── __init__.py
│       │   ├── health.py       # Health endpoints (< 50 lines)
│       │   └── security.py     # Security endpoints (< 200 lines)
│       ├── schemas/
│       │   ├── __init__.py
│       │   └── security.py     # Pydantic models (< 200 lines)
│       ├── services/
│       │   ├── __init__.py
│       │   └── security.py     # Security service (< 300 lines)
│       └── integrations/
│           └── aws/
│               ├── __init__.py
│               ├── security_groups.py  # SG scanner (< 200 lines)
│               ├── iam.py              # IAM scanner (< 200 lines)
│               └── encryption.py       # Encryption scanner (< 200 lines)
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   └── test_services/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/
│   ├── platform/               # IB platform docs (reference)
│   └── AI_DEVELOPER_GUIDE.md   # This file
├── pyproject.toml
├── requirements.txt
└── README.md
```

### 4.2 File Size Limits

| File Type | Max Lines | Rationale |
|-----------|-----------|-----------|
| Any Python file | 500 | Maintainability |
| API endpoint file | 200 | Single responsibility |
| Service file | 300 | Complexity limit |
| Schema file | 200 | Readability |
| Test file | 400 | Coverage depth |

### 4.3 Complexity Limits

- **Cyclomatic complexity**: < 10 per function
- **Cognitive complexity**: < 15 per function
- **Function arguments**: < 6
- **Nesting depth**: < 4 levels

---

## 5. IB SDK Integration Patterns

### 5.1 Client Initialization

```python
# src/cloud_optimizer/dependencies.py
from contextlib import asynccontextmanager
from functools import lru_cache

from intelligence_builder_sdk import IBPlatformClient

from .config import settings


@lru_cache
def get_ib_client_config():
    """Get IB client configuration (cached)."""
    return {
        "base_url": settings.IB_PLATFORM_URL,
        "api_key": settings.IB_API_KEY,
        "tenant_id": settings.TENANT_ID,
        "timeout": settings.IB_TIMEOUT,
    }


@asynccontextmanager
async def get_ib_client():
    """Dependency injection for IB client."""
    config = get_ib_client_config()
    async with IBPlatformClient(**config) as client:
        yield client
```

### 5.2 Entity Creation Pattern

```python
async def create_security_finding(
    ib: IBPlatformClient,
    finding: SecurityFinding,
) -> Entity:
    """Create security finding entity in IB."""
    return await ib.entities.create(
        entity_type="security_finding",
        name=finding.title,
        domain="security",
        properties={
            "severity": finding.severity,
            "resource": finding.resource_arn,
            "remediation": finding.remediation,
            "aws_account": finding.aws_account_id,
        },
    )
```

### 5.3 Relationship Creation Pattern

```python
async def link_finding_to_control(
    ib: IBPlatformClient,
    finding_id: UUID,
    control_id: UUID,
) -> Relationship:
    """Create relationship between finding and mitigating control."""
    return await ib.relationships.create(
        source_id=finding_id,
        target_id=control_id,
        relationship_type="mitigates",
        domain="security",
        properties={"effectiveness": 0.8},
    )
```

### 5.4 Graph Traversal Pattern

```python
async def get_unmitigated_findings(
    ib: IBPlatformClient,
    severity: str = "critical",
) -> List[Entity]:
    """Find critical findings without mitigating controls."""
    # Get all critical findings
    findings = await ib.entities.search(
        entity_type="security_finding",
        domain="security",
        filters={"severity": severity},
    )

    # Check which have mitigating controls
    unmitigated = []
    for finding in findings:
        neighbors = await ib.graph.get_neighbors(
            node_id=finding.id,
            edge_types=["mitigates"],
            direction="incoming",
        )
        if not neighbors:
            unmitigated.append(finding)

    return unmitigated
```

---

## 6. Testing Methodology

### 6.1 Test-First Development

```python
# tests/test_services/test_security.py
"""Tests for security service - WRITTEN FIRST."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cloud_optimizer.services.security import SecurityService


class TestSecurityService:
    """Security service tests with mocked IB client."""

    @pytest.fixture
    def mock_ib_client(self):
        """Mock IB client for unit tests."""
        client = AsyncMock()
        client.entities.batch_create = AsyncMock(return_value=[])
        client.entities.search = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def security_service(self, mock_ib_client):
        """Security service with mocked dependencies."""
        return SecurityService(ib_client=mock_ib_client)

    @pytest.mark.asyncio
    async def test_scan_account_calls_ib_sdk(
        self,
        security_service,
        mock_ib_client,
    ):
        """Verify scan pushes findings to IB via SDK."""
        result = await security_service.scan_account("123456789")

        # Verify IB SDK was called
        mock_ib_client.entities.batch_create.assert_called()

    @pytest.mark.asyncio
    async def test_scan_account_returns_counts(
        self,
        security_service,
    ):
        """Verify scan returns finding counts by type."""
        result = await security_service.scan_account("123456789")

        assert "security_groups" in result
        assert isinstance(result["security_groups"], int)
```

### 6.2 Integration Test Pattern

```python
# tests/integration/test_ib_integration.py
"""Integration tests with real IB platform."""

import pytest
from intelligence_builder_sdk import IBPlatformClient

from cloud_optimizer.config import settings


@pytest.mark.integration
class TestIBIntegration:
    """Integration tests requiring IB platform."""

    @pytest.fixture
    async def ib_client(self):
        """Real IB client for integration tests."""
        async with IBPlatformClient(
            base_url=settings.IB_PLATFORM_URL,
            api_key=settings.IB_API_KEY,
            tenant_id="test-tenant",
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_create_and_retrieve_finding(self, ib_client):
        """Test full create/retrieve cycle."""
        # Create
        entity = await ib_client.entities.create(
            entity_type="security_finding",
            name="Test Finding",
            domain="security",
        )
        assert entity.id is not None

        # Retrieve
        retrieved = await ib_client.entities.get(entity.id)
        assert retrieved.name == "Test Finding"

        # Cleanup
        await ib_client.entities.delete(entity.id)
```

### 6.3 Coverage Requirements

- **Unit tests**: 80% coverage minimum
- **Integration tests**: Critical paths covered
- **Performance tests**: < 200ms API response time

---

## 7. Quality Assembly Line

### 7.1 Four-Station Process

**Station 1: Quality Inception**
- Use templates from this guide
- Include all required elements from creation
- Never retrofit quality

**Station 2: Continuous Validation**
```bash
# Validate syntax
python -m py_compile src/cloud_optimizer/new_file.py

# Check types
mypy src/cloud_optimizer/new_file.py

# Check style
ruff check src/cloud_optimizer/new_file.py
```

**Station 3: Pre-Save Gate**
```bash
# Run formatter
black src/cloud_optimizer/
isort src/cloud_optimizer/

# Run linter
ruff check --fix src/cloud_optimizer/
```

**Station 4: Pre-Commit**
```bash
# Run all hooks
pre-commit run --all-files

# Only commit when passing
git commit -m "feat: add security scanning"
# NEVER: git commit --no-verify
```

### 7.2 Pre-Commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.3.0
    hooks:
      - id: black
        args: [--line-length=88]

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: local
    hooks:
      - id: file-size-check
        name: Check file size
        entry: python -c "import sys; [exit(1) for f in sys.argv[1:] if len(open(f).readlines()) > 500]"
        language: system
        types: [python]
```

---

## 8. Troubleshooting

### 8.1 Common Issues

**Issue**: "IB SDK connection failed"
```python
# Check configuration
from cloud_optimizer.config import settings
print(f"IB URL: {settings.IB_PLATFORM_URL}")
print(f"Tenant: {settings.TENANT_ID}")

# Test connection
async with IBPlatformClient(...) as ib:
    health = await ib.health()
    print(f"IB Status: {health}")
```

**Issue**: "File exceeds 500 lines"
```bash
# Find large files
find src -name "*.py" -exec wc -l {} + | sort -n | tail -10

# Split into modules
# Move related functions to new files
```

**Issue**: "Pre-commit hooks fail"
```bash
# Run hooks individually to identify issue
pre-commit run black --all-files
pre-commit run isort --all-files
pre-commit run mypy --all-files

# Fix issues, NEVER bypass
```

### 8.2 Reference Documentation

- **IB Platform Design**: `docs/platform/TECHNICAL_DESIGN.md`
- **IB Strategic Design**: `docs/platform/STRATEGIC_DESIGN.md`
- **Smart-Scaffold Integration**: `docs/smart-scaffold/`

---

## Summary

Cloud Optimizer v2 is a **thin client** that:

1. **Consumes IB SDK** for all graph operations
2. **Implements AWS integration** for security scanning
3. **Stays under 10K LOC** with strict file limits
4. **Maintains quality-first** development practices

**Remember**: CO v2 does NOT implement graph operations, pattern detection, or entity management. These are IB platform responsibilities accessed only via SDK.

---

**Last Updated**: 2025-11-28
**Document Owner**: Cloud Optimizer Development Team
