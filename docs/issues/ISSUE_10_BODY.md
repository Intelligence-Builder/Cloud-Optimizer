## Parent Epic
Part of #2 (Epic 2: Security Domain Implementation)

## Reference Documentation
**See `docs/platform/TECHNICAL_DESIGN.md` Section 5.1 for pattern specifications**

## Objective
Create security-specific detection patterns for CVEs, compliance, IAM, encryption.

## File Structure
```
src/platform/domains/security/
├── patterns.py      # SECURITY_PATTERNS list
└── factors.py       # SECURITY_CONFIDENCE_FACTORS list
```

## Security Patterns to Implement

| Pattern Name | Category | Regex | Output Type | Confidence |
|--------------|----------|-------|-------------|------------|
| cve_reference | ENTITY | `CVE-\d{4}-\d{4,7}` | vulnerability | 0.95 |
| aws_arn | ENTITY | `arn:aws:[a-z0-9-]+:...` | identity | 0.95 |
| compliance_framework | ENTITY | `SOC\s*2\|HIPAA\|PCI...` | compliance_requirement | 0.90 |
| cvss_score | CONTEXT | `CVSS[:\s]*(\d+\.?\d*)` | cvss_score | 0.90 |
| severity_indicator | CONTEXT | `critical\|high\|medium...` | severity | 0.85 |
| encryption_reference | ENTITY | `AES\|RSA\|TLS\|SSL\|KMS...` | encryption_config | 0.80 |
| security_group | ENTITY | `security\s+group\|sg-...` | security_group | 0.80 |
| iam_policy | ENTITY | `IAM\s+policy\|role...` | access_policy | 0.75 |
| mitigates_relationship | RELATIONSHIP | `X mitigates Y` | mitigates | 0.75 |
| protects_relationship | RELATIONSHIP | `X protects Y` | protects | 0.75 |

## Confidence Factors

| Factor | Weight | Trigger |
|--------|--------|---------|
| severity_context | +0.15 | Nearby severity indicators |
| cve_reference | +0.15 | CVE reference nearby |
| compliance_framework | +0.10 | Compliance framework reference |
| aws_service_context | +0.10 | AWS service mention |

## Test Document
Create `tests/fixtures/security_test_doc.txt`:
```
Security Assessment Report

Critical vulnerability CVE-2021-44228 (CVSS: 10.0) affects our Log4j deployment.
WAF mitigates the Log4j vulnerability by blocking malicious JNDI lookups.

IAM policy AdminAccess grants excessive permissions to arn:aws:iam::123456789:role/DevRole.
Security group sg-0abc123 allows ingress from 0.0.0.0/0 on port 22.

SOC 2 Type II certification requires encryption at rest using AES-256.
Our HIPAA compliance program mandates TLS 1.3 for data in transit.
PCI-DSS requirement 3.4 requires encryption of stored cardholder data.
```

## Test Scenarios

```python
class TestSecurityPatterns:
    def test_cve_pattern_extracts_id()      # CVE-2021-44228 -> vulnerability
    def test_compliance_detects_soc2()       # SOC 2 -> compliance_requirement
    def test_compliance_detects_hipaa()      # HIPAA -> compliance_requirement
    def test_cvss_extracts_score()           # CVSS: 9.8 -> {"score": "9.8"}
    def test_aws_arn_pattern()               # arn:aws:... -> identity
    def test_mitigates_relationship()        # X mitigates Y -> mitigates rel
```

## Acceptance Criteria
- [ ] CVE pattern extracts CVE ID with 95% confidence
- [ ] Compliance patterns detect SOC2, HIPAA, PCI-DSS, GDPR
- [ ] AWS ARN pattern extracts full ARN
- [ ] CVSS pattern extracts numeric score via capture group
- [ ] Relationship patterns extract source and target entities
- [ ] All 4 confidence factors implemented
- [ ] Pattern detection accuracy > 85% on test document
- [ ] Unit tests for each pattern
