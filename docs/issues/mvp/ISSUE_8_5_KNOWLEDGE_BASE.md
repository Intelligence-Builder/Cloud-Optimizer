# 8.5 Knowledge Base Integration

## Parent Epic
Epic 8: MVP Phase 2 - Expert System (Intelligence-Builder)

## Overview

Implement the compliance knowledge base that provides expert-level security guidance for answer generation. The KB contains compliance framework requirements, AWS security best practices, and remediation patterns baked into the container.

## Background

The knowledge base enables expert-level responses without real-time web searches:
- Compliance requirements (HIPAA, SOC2, PCI-DSS, GDPR, CIS, NIST)
- AWS service security best practices
- Common misconfiguration patterns
- Remediation code templates
- All baked into container at build time

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| KB-001 | KB structure | Organize by framework, service, pattern type |
| KB-002 | KB loading | Load from YAML files at startup, cache in memory |
| KB-003 | KB queries | Query by framework, service, or pattern |

## Technical Specification

### Knowledge Base Structure

```
data/compliance/
├── frameworks/
│   ├── hipaa/
│   │   ├── controls.yaml       # All HIPAA controls
│   │   ├── aws_mappings.yaml   # AWS services to controls
│   │   └── requirements.yaml   # Detailed requirements
│   ├── soc2/
│   ├── pci-dss/
│   ├── gdpr/
│   ├── cis/
│   └── nist/
├── services/
│   ├── s3.yaml                 # S3 security best practices
│   ├── ec2.yaml
│   ├── rds.yaml
│   ├── iam.yaml
│   └── ...
├── patterns/
│   ├── encryption.yaml         # Encryption patterns
│   ├── access_control.yaml
│   ├── logging.yaml
│   └── network_security.yaml
└── remediation/
    ├── terraform/
    │   ├── s3_encryption.tf
    │   └── ...
    └── cli/
        ├── s3_encryption.sh
        └── ...
```

### KB Data Models

```python
# src/ib_platform/kb/models.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ComplianceControl:
    framework: str
    control_id: str
    name: str
    description: str
    requirements: list[str]
    aws_services: list[str]
    implementation_guidance: str


@dataclass
class ServiceBestPractice:
    service: str
    category: str  # encryption, access_control, logging, etc.
    title: str
    description: str
    compliance_frameworks: list[str]
    implementation: str
    terraform_example: Optional[str] = None
    cli_example: Optional[str] = None
    console_steps: Optional[list[str]] = None


@dataclass
class SecurityPattern:
    pattern_id: str
    name: str
    category: str
    description: str
    applicable_services: list[str]
    compliance_frameworks: list[str]
    implementation_steps: list[str]
    code_examples: dict[str, str]  # language -> code


@dataclass
class RemediationTemplate:
    template_id: str
    rule_id: str  # Maps to scanner rule
    title: str
    description: str
    terraform: Optional[str] = None
    cli: Optional[str] = None
    console_steps: Optional[list[str]] = None
```

### Sample KB Content

```yaml
# data/compliance/frameworks/hipaa/controls.yaml
framework: HIPAA
version: "2013"
controls:
  - control_id: "164.312(a)(1)"
    name: Access Control
    description: |
      Implement technical policies and procedures for electronic information
      systems that maintain ePHI to allow access only to authorized persons.
    requirements:
      - Unique User Identification
      - Emergency Access Procedure
      - Automatic Logoff
      - Encryption and Decryption
    aws_services:
      - IAM
      - KMS
      - S3
      - RDS
    implementation_guidance: |
      1. Use IAM for user authentication and authorization
      2. Implement MFA for all users with ePHI access
      3. Enable CloudTrail for access logging
      4. Use KMS for encryption key management
      5. Enable default encryption on S3 and RDS

  - control_id: "164.312(a)(2)(iv)"
    name: Encryption and Decryption
    description: |
      Implement a mechanism to encrypt and decrypt electronic protected
      health information.
    requirements:
      - Data at rest encryption
      - Data in transit encryption
    aws_services:
      - KMS
      - S3
      - RDS
      - EBS
    implementation_guidance: |
      1. Use SSE-KMS for S3 bucket encryption
      2. Enable RDS encryption with KMS CMK
      3. Enable EBS volume encryption
      4. Use TLS 1.2+ for all data in transit


# data/compliance/services/s3.yaml
service: S3
best_practices:
  - category: encryption
    title: Enable Default Encryption
    description: |
      All S3 buckets should have default encryption enabled to ensure
      data at rest is protected.
    compliance_frameworks:
      - HIPAA
      - SOC2
      - PCI-DSS
    implementation: |
      Enable SSE-S3 (AES-256) or SSE-KMS (customer managed keys) as
      default encryption for all buckets.
    terraform_example: |
      resource "aws_s3_bucket_server_side_encryption_configuration" "example" {
        bucket = aws_s3_bucket.example.id
        rule {
          apply_server_side_encryption_by_default {
            sse_algorithm     = "aws:kms"
            kms_master_key_id = aws_kms_key.example.arn
          }
        }
      }
    cli_example: |
      aws s3api put-bucket-encryption \
        --bucket my-bucket \
        --server-side-encryption-configuration '{
          "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
              "SSEAlgorithm": "aws:kms",
              "KMSMasterKeyID": "alias/my-key"
            }
          }]
        }'
    console_steps:
      - Navigate to S3 console
      - Select the bucket
      - Go to Properties tab
      - Under Default encryption, click Edit
      - Select SSE-KMS and choose your KMS key
      - Save changes

  - category: access_control
    title: Block Public Access
    description: |
      Enable S3 Block Public Access at account and bucket level to
      prevent accidental public exposure.
    compliance_frameworks:
      - HIPAA
      - SOC2
      - PCI-DSS
      - GDPR
    implementation: |
      Enable all four Block Public Access settings at both account
      and bucket levels.
```

### Knowledge Base Service

```python
# src/ib_platform/kb/service.py
import yaml
from pathlib import Path
from functools import lru_cache

class KnowledgeBaseService:
    DATA_DIR = Path("data/compliance")

    def __init__(self):
        self._frameworks: dict[str, list[ComplianceControl]] = {}
        self._services: dict[str, list[ServiceBestPractice]] = {}
        self._patterns: dict[str, SecurityPattern] = {}
        self._remediation: dict[str, RemediationTemplate] = {}

    async def load(self):
        """Load all KB data at startup."""
        await self._load_frameworks()
        await self._load_services()
        await self._load_patterns()
        await self._load_remediation()

    async def _load_frameworks(self):
        """Load compliance frameworks."""
        frameworks_dir = self.DATA_DIR / "frameworks"
        for framework_dir in frameworks_dir.iterdir():
            if framework_dir.is_dir():
                controls_file = framework_dir / "controls.yaml"
                if controls_file.exists():
                    data = yaml.safe_load(controls_file.read_text())
                    framework = data["framework"]
                    self._frameworks[framework] = [
                        ComplianceControl(
                            framework=framework,
                            **control
                        )
                        for control in data.get("controls", [])
                    ]

    async def _load_services(self):
        """Load service best practices."""
        services_dir = self.DATA_DIR / "services"
        for service_file in services_dir.glob("*.yaml"):
            data = yaml.safe_load(service_file.read_text())
            service = data["service"]
            self._services[service] = [
                ServiceBestPractice(service=service, **bp)
                for bp in data.get("best_practices", [])
            ]

    async def _load_patterns(self):
        """Load security patterns."""
        patterns_dir = self.DATA_DIR / "patterns"
        for pattern_file in patterns_dir.glob("*.yaml"):
            data = yaml.safe_load(pattern_file.read_text())
            for pattern in data.get("patterns", []):
                p = SecurityPattern(**pattern)
                self._patterns[p.pattern_id] = p

    async def _load_remediation(self):
        """Load remediation templates."""
        remediation_dir = self.DATA_DIR / "remediation"
        # Load from index file
        index_file = remediation_dir / "index.yaml"
        if index_file.exists():
            data = yaml.safe_load(index_file.read_text())
            for template in data.get("templates", []):
                t = RemediationTemplate(**template)
                self._remediation[t.rule_id] = t

    # Query methods

    def get_framework_controls(
        self,
        framework: str,
    ) -> list[ComplianceControl]:
        """Get all controls for a framework."""
        return self._frameworks.get(framework.upper(), [])

    def get_control(
        self,
        framework: str,
        control_id: str,
    ) -> ComplianceControl | None:
        """Get specific control."""
        for control in self._frameworks.get(framework.upper(), []):
            if control.control_id == control_id:
                return control
        return None

    def get_service_best_practices(
        self,
        service: str,
        category: str = None,
    ) -> list[ServiceBestPractice]:
        """Get best practices for a service."""
        practices = self._services.get(service.upper(), [])
        if category:
            practices = [p for p in practices if p.category == category]
        return practices

    def get_for_framework(
        self,
        framework: str,
    ) -> list[KBEntry]:
        """Get KB entries relevant to a framework."""
        entries = []

        # Add controls
        for control in self.get_framework_controls(framework):
            entries.append(
                KBEntry(
                    entry_type="control",
                    framework=framework,
                    control_name=control.name,
                    description=control.description,
                    guidance=control.implementation_guidance,
                )
            )

        # Add service practices that reference this framework
        for service, practices in self._services.items():
            for practice in practices:
                if framework in practice.compliance_frameworks:
                    entries.append(
                        KBEntry(
                            entry_type="best_practice",
                            framework=framework,
                            service=service,
                            control_name=practice.title,
                            description=practice.description,
                            guidance=practice.implementation,
                        )
                    )

        return entries[:20]  # Limit for context

    def get_for_service(
        self,
        service: str,
    ) -> list[KBEntry]:
        """Get KB entries for a service."""
        entries = []

        for practice in self.get_service_best_practices(service):
            entries.append(
                KBEntry(
                    entry_type="best_practice",
                    service=service,
                    control_name=practice.title,
                    description=practice.description,
                    guidance=practice.implementation,
                    terraform=practice.terraform_example,
                    cli=practice.cli_example,
                )
            )

        return entries

    def get_remediation(
        self,
        rule_id: str,
    ) -> RemediationTemplate | None:
        """Get remediation template for a rule."""
        return self._remediation.get(rule_id)

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[KBEntry]:
        """Search KB entries by keyword."""
        query_lower = query.lower()
        results = []

        # Search controls
        for framework, controls in self._frameworks.items():
            for control in controls:
                if (
                    query_lower in control.name.lower()
                    or query_lower in control.description.lower()
                ):
                    results.append(
                        KBEntry(
                            entry_type="control",
                            framework=framework,
                            control_name=control.name,
                            description=control.description,
                            guidance=control.implementation_guidance,
                        )
                    )

        # Search practices
        for service, practices in self._services.items():
            for practice in practices:
                if (
                    query_lower in practice.title.lower()
                    or query_lower in practice.description.lower()
                ):
                    results.append(
                        KBEntry(
                            entry_type="best_practice",
                            service=service,
                            control_name=practice.title,
                            description=practice.description,
                            guidance=practice.implementation,
                        )
                    )

        return results[:limit]


@dataclass
class KBEntry:
    entry_type: str  # control, best_practice, pattern
    control_name: str
    description: str
    guidance: str
    framework: str = None
    service: str = None
    terraform: str = None
    cli: str = None
```

### KB Statistics

```
Total KB Entities: ~5,500
- Compliance controls: ~400 (across 6 frameworks)
- Service best practices: ~300 (20 AWS services × 15 avg)
- Security patterns: ~100
- Remediation templates: ~50

Data Size: ~20MB (YAML files baked into container)
```

## API Endpoints

```
GET /api/v1/kb/frameworks              # List frameworks
GET /api/v1/kb/frameworks/:id/controls # Get framework controls
GET /api/v1/kb/services                # List services
GET /api/v1/kb/services/:id/practices  # Get service practices
GET /api/v1/kb/search                  # Search KB
GET /api/v1/kb/remediation/:rule_id    # Get remediation template
```

## Files to Create

```
src/ib_platform/kb/
├── __init__.py
├── service.py               # KB service
├── models.py                # Data models
└── loader.py                # YAML loading

data/compliance/
├── frameworks/
│   ├── hipaa/
│   │   └── controls.yaml
│   ├── soc2/
│   │   └── controls.yaml
│   ├── pci-dss/
│   │   └── controls.yaml
│   ├── gdpr/
│   │   └── controls.yaml
│   ├── cis/
│   │   └── controls.yaml
│   └── nist/
│       └── controls.yaml
├── services/
│   ├── s3.yaml
│   ├── ec2.yaml
│   ├── rds.yaml
│   ├── iam.yaml
│   ├── lambda.yaml
│   ├── vpc.yaml
│   ├── kms.yaml
│   └── ... (20 total)
├── patterns/
│   └── *.yaml
└── remediation/
    └── index.yaml

tests/ib_platform/kb/
├── test_loader.py
├── test_service.py
└── test_queries.py
```

## Testing Requirements

### Unit Tests
- [ ] `test_loader.py` - YAML loading
- [ ] `test_framework_queries.py` - Framework queries
- [ ] `test_service_queries.py` - Service queries
- [ ] `test_search.py` - KB search

### Integration Tests
- [ ] `test_kb_service.py` - Full KB with real data
- [ ] `test_kb_api.py` - API endpoints

## Acceptance Criteria Checklist

- [ ] 6 compliance frameworks loaded
- [ ] 20 AWS services with best practices
- [ ] Security patterns documented
- [ ] Remediation templates for scanner rules
- [ ] KB loads at container startup
- [ ] Query by framework returns controls
- [ ] Query by service returns practices
- [ ] Search returns relevant entries
- [ ] KB size < 25MB
- [ ] Load time < 5 seconds
- [ ] 80%+ test coverage

## KB Content Creation

The KB content should be created by:
1. Extracting from official compliance documentation
2. AWS documentation for best practices
3. CIS Benchmarks for specific checks
4. Security research for remediation templates

Content should be reviewed for accuracy.

## Dependencies

- None (standalone data)

## Blocked By

- None (first IB component)

## Blocks

- 8.2 Answer Generation (uses KB for context)
- 7.5 Compliance Mapping (uses KB structure)

## Estimated Effort

2 weeks (1 week code + 1 week content)

## Labels

`kb`, `compliance`, `ib`, `data`, `mvp`, `phase-2`, `P0`
