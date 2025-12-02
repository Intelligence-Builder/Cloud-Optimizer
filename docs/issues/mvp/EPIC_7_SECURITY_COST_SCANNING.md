# Epic 7: MVP Phase 2 - Security & Cost Scanning

## Overview

Implement AWS account scanning capabilities for security misconfiguration detection and cost optimization opportunities. This epic enables trial customers to connect their AWS account and receive actionable findings through the chat interface.

## Business Value

- **Immediate Value Demonstration**: Trial customers see real findings from their actual AWS environment
- **Differentiation**: AI-powered analysis goes beyond simple checklist scanning
- **Conversion Driver**: Findings create urgency to upgrade and remediate
- **Trust Building**: Data stays in customer's account (scans run locally)

## MVP Use Cases Enabled

1. **AWS Account Connection** - User provides IAM credentials, CO validates and connects
2. **Security Scanning** - Automated scan identifies misconfigurations against compliance frameworks
3. **Cost Analysis** - Identify unused resources, rightsizing opportunities, savings recommendations
4. **Findings Chat** - User asks about specific findings, gets remediation guidance

## Requirements Summary

| Sub-Issue | Requirements | Count | Priority |
|-----------|--------------|-------|----------|
| 7.1 AWS Account Connection | AWS-001 to AWS-004 | 4 | P0 |
| 7.2 Security Scanner | SEC-001 to SEC-006 | 6 | P0 |
| 7.3 Cost Scanner | CST-001 to CST-005 | 5 | P0 |
| 7.4 Findings Management | FND-001 to FND-005 | 5 | P0 |
| 7.5 Compliance Mapping | CMP-001 to CMP-004 | 4 | P0 |
| **Total** | | **24** | |

## Architecture Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Cloud Optimizer                              │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      Scanner Engine                              ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  ││
│  │  │ AWS Connector│  │ Security     │  │ Cost Scanner         │  ││
│  │  │ - STS        │  │ Scanner      │  │ - Cost Explorer      │  ││
│  │  │ - IAM        │  │ - S3, EC2    │  │ - Trusted Advisor    │  ││
│  │  │ - Validation │  │ - RDS, IAM   │  │ - Resource Inventory │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                              │                                       │
│                    ┌─────────▼─────────┐                            │
│                    │ Findings Store     │                            │
│                    │ (PostgreSQL)       │                            │
│                    └───────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
         Customer AWS    Compliance KB    IB Platform
         Account         (frameworks)     (analysis)
```

## Timeline

- **Phase 2**: Weeks 7-12
- **Milestone**: Working scanner with findings displayed in chat

## Sub-Issues

- [ ] #XX 7.1 AWS Account Connection (AWS-*)
- [ ] #XX 7.2 Security Scanner Engine (SEC-*)
- [ ] #XX 7.3 Cost Analysis Scanner (CST-*)
- [ ] #XX 7.4 Findings Management System (FND-*)
- [ ] #XX 7.5 Compliance Framework Mapping (CMP-*)

## Dependencies

- Epic 6: Container Product Foundation (requires running backend)

## Success Criteria

1. [ ] User can connect AWS account with read-only IAM role
2. [ ] Security scan completes in <5 minutes for typical account
3. [ ] Findings mapped to compliance frameworks (HIPAA, SOC2, etc.)
4. [ ] Cost savings identified with estimated $ impact
5. [ ] Findings accessible via chat ("What did you find?")
6. [ ] 80%+ test coverage on scanner code

## Reference Documents

- [REQUIREMENTS_V2.md](../02-architecture/REQUIREMENTS_V2.md) - AWS-*, SEC-*, CST-* requirements
- [STRATEGIC_DESIGN_V2.md](../02-architecture/STRATEGIC_DESIGN_V2.md) - Scanner architecture
- [DEPLOYMENT.md](../04-operations/DEPLOYMENT.md) - AWS permissions model

## Labels

`epic`, `mvp`, `phase-2`, `scanning`, `P0`
