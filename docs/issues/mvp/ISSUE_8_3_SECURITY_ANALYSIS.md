# 8.3 Security Analysis Integration

## Parent Epic
Epic 8: MVP Phase 2 - Expert System (Intelligence-Builder)

## Overview

Implement the integration between Intelligence-Builder (IB) and Cloud Optimizer (CO) security findings. IB analyzes findings to provide expert explanations, prioritization recommendations, and remediation guidance through the chat interface.

## Background

The security analysis integration bridges scanning results with expert advice:
- Explain findings in business context
- Prioritize remediation based on risk
- Provide compliance-aware recommendations
- Generate actionable remediation plans

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| IB-SEC-001 | Finding explanation | Explain any finding in plain language with business impact |
| IB-SEC-002 | Risk prioritization | Rank findings by risk considering compliance, exploitability |
| IB-SEC-003 | Remediation planning | Generate step-by-step remediation with code examples |
| IB-SEC-004 | Compliance correlation | Map findings to specific compliance controls |

## Technical Specification

### Security Analysis Service

```python
# src/ib_platform/security/analysis_service.py
from anthropic import Anthropic

class SecurityAnalysisService:
    """Analyze security findings and provide expert guidance."""

    ANALYSIS_PROMPT = """You are a senior cloud security engineer analyzing AWS security findings.

For each finding, provide:
1. Plain language explanation of the risk
2. Business impact if exploited
3. Likelihood of exploitation
4. Compliance implications
5. Prioritized remediation steps
6. Example code to fix (Terraform, AWS CLI, or Console steps)

Be specific and actionable. Reference the exact resource and configuration."""

    def __init__(
        self,
        anthropic_client: Anthropic,
        findings_service: FindingsService,
        compliance_service: ComplianceService,
    ):
        self.client = anthropic_client
        self.findings_service = findings_service
        self.compliance_service = compliance_service

    async def explain_finding(
        self,
        tenant_id: UUID,
        finding_id: UUID,
    ) -> FindingExplanation:
        """Generate detailed explanation for a finding."""
        finding = await self.findings_service.get_finding(tenant_id, finding_id)

        # Get compliance context
        compliance_controls = await self.compliance_service.get_controls_for_rule(
            finding.rule_id
        )

        prompt = f"""Analyze this security finding:

**Finding:** {finding.title}
**Severity:** {finding.severity}
**Resource:** {finding.resource_type} - {finding.resource_id}
**Region:** {finding.region}
**Description:** {finding.description}

**Compliance Frameworks Affected:** {', '.join(finding.compliance_frameworks)}
**Specific Controls:**
{self._format_controls(compliance_controls)}

Provide a comprehensive analysis following the structure above."""

        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            system=self.ANALYSIS_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        return FindingExplanation(
            finding_id=finding_id,
            explanation=response.content[0].text,
            compliance_controls=compliance_controls,
            generated_at=datetime.utcnow(),
        )

    async def prioritize_findings(
        self,
        tenant_id: UUID,
        limit: int = 10,
    ) -> PrioritizedFindings:
        """Prioritize open findings by risk."""
        # Get all open findings
        findings = await self.findings_service.get_findings(
            tenant_id,
            filters=FindingFilters(status=["open"]),
            pagination=Pagination(limit=100),
        )

        # Score each finding
        scored_findings = []
        for finding in findings.items:
            score = self._calculate_risk_score(finding)
            scored_findings.append((finding, score))

        # Sort by score descending
        scored_findings.sort(key=lambda x: x[1], reverse=True)

        # Get top N
        top_findings = scored_findings[:limit]

        # Generate prioritization rationale
        rationale = await self._generate_prioritization_rationale(
            [f for f, _ in top_findings]
        )

        return PrioritizedFindings(
            findings=[
                PrioritizedFinding(
                    finding=f,
                    risk_score=s,
                    rank=i + 1,
                )
                for i, (f, s) in enumerate(top_findings)
            ],
            rationale=rationale,
        )

    def _calculate_risk_score(self, finding: Finding) -> float:
        """Calculate risk score for prioritization."""
        score = 0.0

        # Severity weight (0-40 points)
        severity_weights = {
            "critical": 40,
            "high": 30,
            "medium": 15,
            "low": 5,
        }
        score += severity_weights.get(finding.severity, 0)

        # Compliance weight (0-30 points)
        high_value_frameworks = ["HIPAA", "PCI-DSS"]
        if any(f in finding.compliance_frameworks for f in high_value_frameworks):
            score += 30
        elif finding.compliance_frameworks:
            score += 15

        # Resource type weight (0-20 points)
        high_risk_resources = ["iam", "s3", "rds"]
        if any(r in finding.resource_type.lower() for r in high_risk_resources):
            score += 20

        # Public exposure weight (0-10 points)
        if "public" in finding.title.lower() or "public" in finding.description.lower():
            score += 10

        return score

    async def _generate_prioritization_rationale(
        self,
        findings: list[Finding],
    ) -> str:
        """Generate explanation for prioritization."""
        prompt = f"""Given these top priority security findings, explain why they should be addressed in this order:

{self._format_findings_for_prompt(findings)}

Provide a brief (2-3 paragraph) rationale focusing on:
1. Why the top issues are most critical
2. What the overall security posture indicates
3. Quick wins that could be addressed first"""

        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    async def generate_remediation_plan(
        self,
        tenant_id: UUID,
        finding_ids: list[UUID],
    ) -> RemediationPlan:
        """Generate comprehensive remediation plan for findings."""
        findings = []
        for fid in finding_ids:
            finding = await self.findings_service.get_finding(tenant_id, fid)
            findings.append(finding)

        prompt = f"""Generate a remediation plan for these security findings:

{self._format_findings_for_prompt(findings)}

For each finding provide:
1. Step-by-step remediation instructions
2. Terraform code to fix (if applicable)
3. AWS CLI commands (if applicable)
4. AWS Console steps
5. Verification steps to confirm remediation

Group related findings if they can be fixed together."""

        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000,
            system="You are a cloud security engineer creating remediation plans.",
            messages=[{"role": "user", "content": prompt}],
        )

        return RemediationPlan(
            findings=findings,
            plan=response.content[0].text,
            generated_at=datetime.utcnow(),
        )

    def _format_findings_for_prompt(self, findings: list[Finding]) -> str:
        """Format findings for LLM prompt."""
        lines = []
        for i, f in enumerate(findings, 1):
            lines.append(f"{i}. **{f.title}** ({f.severity})")
            lines.append(f"   Resource: {f.resource_id}")
            lines.append(f"   Compliance: {', '.join(f.compliance_frameworks)}")
            lines.append(f"   Description: {f.description[:200]}")
            lines.append("")
        return "\n".join(lines)

    def _format_controls(self, controls: list[ComplianceControl]) -> str:
        """Format compliance controls for prompt."""
        lines = []
        for c in controls:
            lines.append(f"- {c.control_code}: {c.name}")
        return "\n".join(lines)
```

### Finding Correlation

```python
# src/ib_platform/security/correlation.py
class FindingCorrelator:
    """Correlate related findings for holistic analysis."""

    async def find_related(
        self,
        finding: Finding,
        all_findings: list[Finding],
    ) -> list[Finding]:
        """Find findings related to a given finding."""
        related = []

        for f in all_findings:
            if f.finding_id == finding.finding_id:
                continue

            # Same resource
            if f.resource_id == finding.resource_id:
                related.append(f)
                continue

            # Same resource type in same region
            if (
                f.resource_type == finding.resource_type
                and f.region == finding.region
            ):
                related.append(f)
                continue

            # Same compliance framework
            if set(f.compliance_frameworks) & set(finding.compliance_frameworks):
                related.append(f)

        return related[:5]  # Top 5 related

    async def cluster_findings(
        self,
        findings: list[Finding],
    ) -> list[FindingCluster]:
        """Group findings into clusters for batch remediation."""
        clusters = {}

        for finding in findings:
            # Cluster by resource type + severity
            key = (finding.resource_type, finding.severity)
            if key not in clusters:
                clusters[key] = FindingCluster(
                    resource_type=finding.resource_type,
                    severity=finding.severity,
                    findings=[],
                )
            clusters[key].findings.append(finding)

        return list(clusters.values())
```

### Models

```python
# src/ib_platform/security/models.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FindingExplanation:
    finding_id: UUID
    explanation: str
    compliance_controls: list[ComplianceControl]
    generated_at: datetime


@dataclass
class PrioritizedFinding:
    finding: Finding
    risk_score: float
    rank: int


@dataclass
class PrioritizedFindings:
    findings: list[PrioritizedFinding]
    rationale: str


@dataclass
class RemediationPlan:
    findings: list[Finding]
    plan: str
    generated_at: datetime


@dataclass
class FindingCluster:
    resource_type: str
    severity: str
    findings: list[Finding]

    @property
    def count(self) -> int:
        return len(self.findings)
```

## API Endpoints

```
GET  /api/v1/analysis/findings/:id/explain     # Explain finding
GET  /api/v1/analysis/findings/prioritize      # Get prioritized findings
POST /api/v1/analysis/remediation-plan         # Generate remediation plan
GET  /api/v1/analysis/findings/:id/related     # Get related findings
GET  /api/v1/analysis/clusters                 # Get finding clusters
```

## Files to Create

```
src/ib_platform/security/
├── __init__.py
├── analysis_service.py      # Main analysis service
├── correlation.py           # Finding correlation
├── scoring.py               # Risk scoring
└── models.py                # Data models

src/cloud_optimizer/api/routers/
└── analysis.py              # API endpoints

tests/ib_platform/security/
├── test_analysis_service.py
├── test_correlation.py
├── test_scoring.py
└── test_api.py
```

## Testing Requirements

### Unit Tests
- [ ] `test_risk_scoring.py` - Risk score calculation
- [ ] `test_correlation.py` - Finding correlation logic
- [ ] `test_clustering.py` - Finding clustering

### Integration Tests
- [ ] `test_analysis_service.py` - Full analysis with mocked LLM
- [ ] `test_remediation_plan.py` - Plan generation

## Acceptance Criteria Checklist

- [ ] Finding explanations are clear and actionable
- [ ] Risk score considers severity, compliance, exposure
- [ ] Prioritization includes rationale
- [ ] Remediation plans include code examples
- [ ] Related findings identified correctly
- [ ] Clusters group similar findings
- [ ] Compliance controls mapped to findings
- [ ] API endpoints return correct data
- [ ] 80%+ test coverage

## Dependencies

- 7.2 Security Scanner (generates findings)
- 7.4 Findings Management (finding queries)
- 7.5 Compliance Mapping (compliance context)

## Blocked By

- 7.4 Findings Management

## Blocks

- 8.2 Answer Generation (uses analysis for responses)

## Estimated Effort

1 week

## Labels

`security`, `analysis`, `ib`, `mvp`, `phase-2`, `P0`
