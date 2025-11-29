## Parent Epic
Part of #3 (Epic 3: Cloud Optimizer v2 Clean Rebuild)

## Reference Documentation
- **See `docs/platform/TECHNICAL_DESIGN.md` Section 5 for Security domain**
- **See `docs/AI_DEVELOPER_GUIDE.md` for SDK integration patterns**

## Objective
Implement Security domain features with AWS integration.

## File Structure
```
src/cloud_optimizer/
├── api/
│   └── security.py          # Security endpoints (< 200 lines)
├── schemas/
│   └── security.py          # Pydantic models (< 200 lines)
├── services/
│   └── security.py          # Security service (< 300 lines)
└── integrations/
    └── aws/
        ├── __init__.py
        ├── base.py           # Base AWS scanner (< 100 lines)
        ├── security_groups.py # SG scanner (< 200 lines)
        ├── iam.py            # IAM scanner (< 200 lines)
        └── encryption.py     # Encryption scanner (< 200 lines)
```

## SecurityService Implementation
```python
"""Security scanning service for Cloud Optimizer."""

import logging
from typing import Dict, List, Optional

from intelligence_builder_sdk import IBPlatformClient

from ..integrations.aws import SecurityGroupScanner, IAMScanner, EncryptionScanner

logger = logging.getLogger(__name__)


class SecurityService:
    """Orchestrates security scans and pushes findings to IB."""

    def __init__(self, ib_client: IBPlatformClient):
        self.ib = ib_client
        self.scanners = {
            "security_groups": SecurityGroupScanner(),
            "iam": IAMScanner(),
            "encryption": EncryptionScanner(),
        }

    async def scan_account(
        self,
        aws_account_id: str,
        scan_types: Optional[List[str]] = None,
        region: str = "us-east-1",
    ) -> Dict[str, int]:
        """Run security scans and push findings to IB."""
        scan_types = scan_types or list(self.scanners.keys())
        results = {}

        for scan_type in scan_types:
            scanner = self.scanners.get(scan_type)
            if not scanner:
                continue

            # 1. Run AWS scan
            findings = await scanner.scan(aws_account_id, region)

            # 2. Transform to IB entities
            entities = [self._to_entity(f) for f in findings]

            # 3. Push to IB via SDK
            created = await self.ib.entities.batch_create(entities)
            results[scan_type] = len(created)

        return results

    def _to_entity(self, finding: dict) -> dict:
        """Transform AWS finding to IB entity format."""
        return {
            "entity_type": "security_finding",
            "name": finding["title"],
            "domain": "security",
            "properties": {
                "severity": finding["severity"],
                "resource": finding["resource_arn"],
                "remediation": finding.get("remediation"),
                "aws_account": finding["aws_account_id"],
                "region": finding["region"],
            },
        }
```

## AWS Scanner Base
```python
"""Base class for AWS security scanners."""

from abc import ABC, abstractmethod
from typing import List
import boto3


class BaseAWSScanner(ABC):
    """Abstract base for AWS security scanners."""

    @abstractmethod
    async def scan(self, account_id: str, region: str) -> List[dict]:
        """Scan AWS resources and return findings."""
        pass

    def _get_client(self, service: str, region: str):
        """Get boto3 client for AWS service."""
        return boto3.client(service, region_name=region)
```

## Security Group Scanner
```python
"""Security group scanner for open ports and risky rules."""

from typing import List
from .base import BaseAWSScanner


class SecurityGroupScanner(BaseAWSScanner):
    """Scans security groups for risky configurations."""

    RISKY_PORTS = [22, 3389, 3306, 5432, 27017]

    async def scan(self, account_id: str, region: str) -> List[dict]:
        """Find security groups with risky ingress rules."""
        ec2 = self._get_client("ec2", region)
        findings = []

        sgs = ec2.describe_security_groups()["SecurityGroups"]
        for sg in sgs:
            for rule in sg.get("IpPermissions", []):
                finding = self._check_rule(sg, rule, account_id, region)
                if finding:
                    findings.append(finding)

        return findings

    def _check_rule(self, sg: dict, rule: dict, account_id: str, region: str):
        """Check if rule is risky (open to world on sensitive port)."""
        for ip_range in rule.get("IpRanges", []):
            if ip_range.get("CidrIp") == "0.0.0.0/0":
                port = rule.get("FromPort")
                if port in self.RISKY_PORTS:
                    return {
                        "title": f"Security group {sg['GroupId']} open on port {port}",
                        "severity": "high",
                        "resource_arn": f"arn:aws:ec2:{region}:{account_id}:security-group/{sg['GroupId']}",
                        "aws_account_id": account_id,
                        "region": region,
                        "remediation": f"Restrict port {port} to specific IP ranges",
                    }
        return None
```

## API Endpoints
```python
# api/security.py
from fastapi import APIRouter, Depends
from ..dependencies import get_security_service
from ..schemas.security import ScanRequest, ScanResult

router = APIRouter(prefix="/api/v1/security", tags=["security"])


@router.post("/scan", response_model=ScanResult)
async def trigger_scan(
    request: ScanRequest,
    service=Depends(get_security_service),
):
    """Trigger security scan for AWS account."""
    results = await service.scan_account(
        aws_account_id=request.aws_account_id,
        scan_types=request.scan_types,
        region=request.region,
    )
    return ScanResult(success=True, findings_by_type=results)
```

## Test Scenarios
```python
class TestSecurityService:
    async def test_scan_account_all_types()
    async def test_scan_pushes_to_ib()
    async def test_finding_transformation()

class TestSecurityGroupScanner:
    async def test_detects_open_ssh()
    async def test_detects_open_rdp()
    async def test_ignores_safe_rules()

class TestSecurityAPI:
    async def test_scan_endpoint()
    async def test_scan_with_region()
```

## Acceptance Criteria
- [ ] SecurityService orchestrates scans correctly
- [ ] Findings pushed to IB via SDK
- [ ] Security group scanner detects risky rules
- [ ] IAM scanner implemented (similar pattern)
- [ ] Encryption scanner implemented (similar pattern)
- [ ] API endpoint triggers scans
- [ ] Dashboard endpoint returns metrics
- [ ] No file exceeds 500 lines
- [ ] Test coverage > 80%
- [ ] All code has type hints
