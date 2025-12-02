# 7.5 Compliance Framework Mapping

## Parent Epic
Epic 7: MVP Phase 2 - Security & Cost Scanning

## Overview

Implement compliance framework mapping that associates security findings with relevant compliance requirements (HIPAA, SOC2, PCI-DSS, GDPR, CIS Benchmarks, NIST). Enables compliance-focused reporting and chat queries.

## Background

Trial customers often have compliance requirements driving their security initiatives. Mapping findings to compliance frameworks:
- Provides business context for findings
- Enables compliance-focused filtering
- Supports audit preparation
- Differentiates from basic scanning tools

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| CMP-001 | Framework data model | Store frameworks, controls, requirements with hierarchy |
| CMP-002 | Finding mapping | Map security rules to compliance controls |
| CMP-003 | Coverage reporting | Show % of framework controls covered by scans |
| CMP-004 | Compliance queries | Filter findings by framework, get compliance summary |

## Technical Specification

### Compliance Data Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Compliance Framework                              │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  Framework (e.g., HIPAA)                                        ││
│  │    └── Domain (e.g., Technical Safeguards)                      ││
│  │         └── Control (e.g., Access Control)                      ││
│  │              └── Requirement (e.g., Unique User ID)             ││
│  └─────────────────────────────────────────────────────────────────┘│
│                              │                                       │
│                    ┌─────────▼─────────┐                            │
│                    │ Rule Mappings     │                            │
│                    │ SEC_001 → HIPAA   │                            │
│                    │          SOC2     │                            │
│                    └───────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Database Schema

```sql
-- Compliance frameworks
CREATE TABLE compliance_frameworks (
    framework_id VARCHAR(20) PRIMARY KEY,  -- 'HIPAA', 'SOC2', etc.
    name VARCHAR(100) NOT NULL,
    description TEXT,
    version VARCHAR(20),
    effective_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Compliance domains (top-level grouping)
CREATE TABLE compliance_domains (
    domain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    framework_id VARCHAR(20) NOT NULL REFERENCES compliance_frameworks(framework_id),
    domain_code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sort_order INTEGER,
    UNIQUE(framework_id, domain_code)
);

-- Compliance controls
CREATE TABLE compliance_controls (
    control_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES compliance_domains(domain_id),
    control_code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sort_order INTEGER
);

-- Security rule to compliance mappings
CREATE TABLE rule_compliance_mappings (
    mapping_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id VARCHAR(50) NOT NULL,        -- 'S3_001', 'EC2_001', etc.
    control_id UUID NOT NULL REFERENCES compliance_controls(control_id),
    relevance VARCHAR(20) NOT NULL,      -- 'direct', 'supporting'
    notes TEXT,
    UNIQUE(rule_id, control_id)
);

CREATE INDEX idx_mappings_rule ON rule_compliance_mappings(rule_id);
CREATE INDEX idx_mappings_control ON rule_compliance_mappings(control_id);
```

### Compliance Data (Seeded)

```yaml
# data/compliance/hipaa.yaml
framework:
  id: HIPAA
  name: Health Insurance Portability and Accountability Act
  version: "2013"
  description: US healthcare data privacy regulation

domains:
  - code: "164.312"
    name: Technical Safeguards
    controls:
      - code: "164.312(a)(1)"
        name: Access Control
        description: Implement technical policies to allow access only to authorized persons
        requirements:
          - "Unique User Identification"
          - "Emergency Access Procedure"
          - "Automatic Logoff"
          - "Encryption and Decryption"

      - code: "164.312(a)(2)(iv)"
        name: Encryption and Decryption
        description: Implement mechanism to encrypt/decrypt ePHI

      - code: "164.312(b)"
        name: Audit Controls
        description: Implement mechanisms to record and examine access

      - code: "164.312(c)(1)"
        name: Integrity
        description: Implement policies to protect ePHI from improper alteration

      - code: "164.312(d)"
        name: Person or Entity Authentication
        description: Implement procedures to verify identity

      - code: "164.312(e)(1)"
        name: Transmission Security
        description: Implement security measures for electronic transmission

# Rule mappings
mappings:
  - rule_id: S3_001  # Public Access
    control: "164.312(a)(1)"
    relevance: direct

  - rule_id: S3_002  # Encryption
    control: "164.312(a)(2)(iv)"
    relevance: direct

  - rule_id: S3_004  # Logging
    control: "164.312(b)"
    relevance: direct

  - rule_id: IAM_002  # MFA
    control: "164.312(d)"
    relevance: direct
```

### Compliance Service

```python
# src/cloud_optimizer/services/compliance.py
class ComplianceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_frameworks(self) -> list[ComplianceFramework]:
        """Get all compliance frameworks."""
        result = await self.db.execute(select(ComplianceFramework))
        return result.scalars().all()

    async def get_framework_details(
        self, framework_id: str
    ) -> ComplianceFrameworkDetails:
        """Get framework with domains and controls."""
        framework = await self.db.execute(
            select(ComplianceFramework)
            .where(ComplianceFramework.framework_id == framework_id)
        )
        framework = framework.scalar_one_or_none()
        if not framework:
            raise FrameworkNotFoundException()

        domains = await self.db.execute(
            select(ComplianceDomain)
            .where(ComplianceDomain.framework_id == framework_id)
            .order_by(ComplianceDomain.sort_order)
        )

        return ComplianceFrameworkDetails(
            framework=framework,
            domains=domains.scalars().all(),
        )

    async def get_compliance_status(
        self,
        tenant_id: UUID,
        framework_id: str,
    ) -> ComplianceStatus:
        """Get compliance status for a framework based on findings."""
        # Get all controls for framework
        controls_query = select(ComplianceControl).join(
            ComplianceDomain
        ).where(ComplianceDomain.framework_id == framework_id)

        controls = (await self.db.execute(controls_query)).scalars().all()

        # Get findings mapped to this framework
        findings_query = select(SecurityFinding).where(
            SecurityFinding.tenant_id == tenant_id,
            SecurityFinding.compliance_frameworks.contains([framework_id]),
            SecurityFinding.status == "open",
        )

        findings = (await self.db.execute(findings_query)).scalars().all()

        # Calculate status per control
        control_status = []
        for control in controls:
            # Get rules mapped to this control
            mappings = await self._get_control_mappings(control.control_id)
            rule_ids = [m.rule_id for m in mappings]

            # Find violations for these rules
            violations = [f for f in findings if f.rule_id in rule_ids]

            status = "compliant" if not violations else "non_compliant"
            if not rule_ids:
                status = "not_assessed"

            control_status.append(
                ControlStatus(
                    control=control,
                    status=status,
                    violation_count=len(violations),
                    findings=violations[:3],  # Top 3 for preview
                )
            )

        # Calculate overall compliance percentage
        assessed = [c for c in control_status if c.status != "not_assessed"]
        compliant = [c for c in assessed if c.status == "compliant"]

        compliance_pct = (
            len(compliant) / len(assessed) * 100 if assessed else 0
        )

        return ComplianceStatus(
            framework_id=framework_id,
            compliance_percentage=compliance_pct,
            total_controls=len(controls),
            compliant_controls=len(compliant),
            non_compliant_controls=len(assessed) - len(compliant),
            not_assessed_controls=len(controls) - len(assessed),
            controls=control_status,
        )

    async def get_findings_by_framework(
        self,
        tenant_id: UUID,
        framework_id: str,
    ) -> list[SecurityFinding]:
        """Get all findings for a compliance framework."""
        result = await self.db.execute(
            select(SecurityFinding)
            .where(
                SecurityFinding.tenant_id == tenant_id,
                SecurityFinding.compliance_frameworks.contains([framework_id]),
            )
            .order_by(
                case(
                    (SecurityFinding.severity == "critical", 1),
                    (SecurityFinding.severity == "high", 2),
                    (SecurityFinding.severity == "medium", 3),
                    (SecurityFinding.severity == "low", 4),
                )
            )
        )
        return result.scalars().all()

    async def map_finding_to_frameworks(
        self, rule_id: str
    ) -> list[str]:
        """Get frameworks a rule maps to."""
        result = await self.db.execute(
            select(ComplianceFramework.framework_id)
            .join(ComplianceDomain)
            .join(ComplianceControl)
            .join(RuleComplianceMapping)
            .where(RuleComplianceMapping.rule_id == rule_id)
            .distinct()
        )
        return result.scalars().all()
```

### Data Loader

```python
# src/cloud_optimizer/compliance/loader.py
import yaml
from pathlib import Path

class ComplianceDataLoader:
    DATA_DIR = Path("data/compliance")

    FRAMEWORKS = ["hipaa", "soc2", "pci-dss", "gdpr", "cis", "nist"]

    async def load_all(self, db: AsyncSession):
        """Load all compliance data from YAML files."""
        for framework in self.FRAMEWORKS:
            await self._load_framework(db, framework)
        await db.commit()

    async def _load_framework(self, db: AsyncSession, name: str):
        """Load single framework from YAML."""
        path = self.DATA_DIR / f"{name}.yaml"
        if not path.exists():
            logger.warning(f"Compliance data not found: {path}")
            return

        with open(path) as f:
            data = yaml.safe_load(f)

        # Create framework
        framework = ComplianceFramework(
            framework_id=data["framework"]["id"],
            name=data["framework"]["name"],
            description=data["framework"].get("description"),
            version=data["framework"].get("version"),
        )
        db.add(framework)

        # Create domains and controls
        for domain_data in data.get("domains", []):
            domain = ComplianceDomain(
                framework_id=framework.framework_id,
                domain_code=domain_data["code"],
                name=domain_data["name"],
                description=domain_data.get("description"),
            )
            db.add(domain)
            await db.flush()  # Get domain_id

            for control_data in domain_data.get("controls", []):
                control = ComplianceControl(
                    domain_id=domain.domain_id,
                    control_code=control_data["code"],
                    name=control_data["name"],
                    description=control_data.get("description"),
                )
                db.add(control)
                await db.flush()

        # Create mappings
        for mapping_data in data.get("mappings", []):
            # Find control by code
            control = await db.execute(
                select(ComplianceControl)
                .join(ComplianceDomain)
                .where(
                    ComplianceDomain.framework_id == framework.framework_id,
                    ComplianceControl.control_code == mapping_data["control"],
                )
            )
            control = control.scalar_one_or_none()

            if control:
                mapping = RuleComplianceMapping(
                    rule_id=mapping_data["rule_id"],
                    control_id=control.control_id,
                    relevance=mapping_data.get("relevance", "direct"),
                )
                db.add(mapping)
```

## Supported Frameworks

| Framework | Version | Controls | Coverage |
|-----------|---------|----------|----------|
| HIPAA | 2013 | 42 | High |
| SOC 2 | 2017 | 64 | High |
| PCI-DSS | 4.0 | 78 | Medium |
| GDPR | 2018 | 35 | Medium |
| CIS Benchmarks | AWS 1.5 | 55 | High |
| NIST 800-53 | Rev 5 | 120 | Medium |

## API Endpoints

```
GET  /api/v1/compliance/frameworks           # List all frameworks
GET  /api/v1/compliance/frameworks/:id       # Get framework details
GET  /api/v1/compliance/status/:framework    # Get compliance status
GET  /api/v1/compliance/findings/:framework  # Get findings by framework
GET  /api/v1/compliance/report/:framework    # Generate compliance report
```

## Files to Create

```
src/cloud_optimizer/services/
└── compliance.py                # Compliance service

src/cloud_optimizer/compliance/
├── __init__.py
└── loader.py                    # YAML data loader

src/cloud_optimizer/models/
├── compliance_framework.py
├── compliance_domain.py
├── compliance_control.py
└── rule_mapping.py

src/cloud_optimizer/api/routers/
└── compliance.py                # API endpoints

data/compliance/
├── hipaa.yaml
├── soc2.yaml
├── pci-dss.yaml
├── gdpr.yaml
├── cis.yaml
└── nist.yaml

alembic/versions/
└── xxx_create_compliance_tables.py

tests/services/
└── test_compliance.py
```

## Testing Requirements

### Unit Tests
- [ ] `test_compliance_loader.py` - YAML parsing and loading
- [ ] `test_compliance_status.py` - Status calculation
- [ ] `test_mapping_lookup.py` - Rule to framework mapping

### Integration Tests
- [ ] `test_compliance_service.py` - Full service with DB
- [ ] `test_compliance_api.py` - API endpoints

## Acceptance Criteria Checklist

- [ ] 6 compliance frameworks loaded from YAML
- [ ] Frameworks have domains and controls hierarchy
- [ ] Security rules mapped to compliance controls
- [ ] Compliance status calculates % correctly
- [ ] Findings filterable by framework
- [ ] Control status shows compliant/non-compliant/not-assessed
- [ ] Compliance report generates correctly
- [ ] Chat can answer "Show HIPAA findings"
- [ ] 80%+ test coverage

## Dependencies

- 7.2 Security Scanner (rule IDs for mapping)
- 7.4 Findings Management (finding queries)

## Blocked By

- 7.4 Findings Management

## Blocks

- 8.3 Security Analysis (compliance-aware responses)

## Estimated Effort

1 week

## Labels

`compliance`, `regulatory`, `data`, `mvp`, `phase-2`, `P0`
