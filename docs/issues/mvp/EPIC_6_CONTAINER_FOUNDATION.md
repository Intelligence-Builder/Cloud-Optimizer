# Epic 6: MVP Phase 1 - Container Product Foundation

## Overview

Build the foundational container product that enables trial customers to deploy Cloud Optimizer in their AWS account with one-click setup. This epic delivers the deployment infrastructure, AWS Marketplace integration, trial management, basic authentication, and chat-first UI.

## Business Value

- **Trial-First Launch**: Enable potential customers to experience value immediately
- **AWS Marketplace Revenue**: Unlock AWS Marketplace as distribution channel
- **Customer Data Security**: Data stays in customer's AWS account
- **Reduced Time-to-Value**: One-click deployment in <10 minutes

## MVP Use Cases Enabled

1. **Security Q&A Chat** - User asks security questions, gets expert answers
2. **Document Analysis** - User uploads architecture PDF, gets recommendations
3. **AWS Scanning** - User connects AWS account, sees real findings

## Requirements Summary

| Sub-Issue | Requirements | Count | Priority |
|-----------|--------------|-------|----------|
| 6.1 Container Packaging | CNT-001 to CNT-006 | 6 | P0 |
| 6.2 AWS Marketplace | MKT-001 to MKT-005 | 5 | P0 |
| 6.3 Trial Management | TRL-001 to TRL-006 | 6 | P0 |
| 6.4 Basic Authentication | USR-001, USR-004, USR-007 | 3 | P0 |
| 6.5 Chat Interface UI | UI-001 to UI-010 | 10 | P0 |
| **Total** | | **30** | |

## Architecture Context

```
┌─────────────────────────────────────────────────────────────────┐
│                 cloud-optimizer:v2.0.0-ib1.0.0                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  CO API Server  │──│  IB Platform (embedded)                ││
│  │  - FastAPI      │  │  - Graph Backend                       ││
│  │  - Chat API     │  │  - Pattern Engine                      ││
│  │  - Scanners     │  │  - NLU + Answer Gen                    ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
         │                    │                    │
    PostgreSQL            Redis             AWS Marketplace
       (RDS)           (Optional)           Metering API
```

## Timeline

- **Phase 1**: Weeks 1-6
- **Milestone**: Deployable container with chat UI and trial capability

## Sub-Issues

- [ ] #XX 6.1 Container Packaging (CNT-*)
- [ ] #XX 6.2 AWS Marketplace Integration (MKT-*)
- [ ] #XX 6.3 Trial Management System (TRL-*)
- [ ] #XX 6.4 Basic Authentication (USR-*)
- [ ] #XX 6.5 Chat Interface + Dashboard UI (UI-*)

## Dependencies

- None (foundation epic)

## Success Criteria

1. [ ] One-click CloudFormation deploys working system in <10 minutes
2. [ ] Trial user can ask security questions and get expert answers
3. [ ] AWS Marketplace FTR (Fulfillment Technical Review) ready
4. [ ] Chat response time <3 seconds
5. [ ] 80%+ test coverage on all new code

## Reference Documents

- [PHASED_IMPLEMENTATION_PLAN.md](../02-architecture/PHASED_IMPLEMENTATION_PLAN.md) - MVP definition
- [REQUIREMENTS_V2.md](../02-architecture/REQUIREMENTS_V2.md) - Detailed requirements
- [DEPLOYMENT.md](../04-operations/DEPLOYMENT.md) - Deployment architecture
- [STRATEGIC_DESIGN_V2.md](../02-architecture/STRATEGIC_DESIGN_V2.md) - Technical design

## Labels

`epic`, `mvp`, `phase-1`, `P0`
