# Cloud Optimizer Documentation

**Version:** 2.2.0
**Last Updated:** 2025-11-30

---

## Overview

Cloud Optimizer is an AWS cost optimization and Well-Architected Framework analysis tool built on the Intelligence-Builder platform. It provides:

- **Cost Analysis** - AWS spending analysis and savings recommendations
- **Security Assessment** - Vulnerability detection and compliance checking
- **Well-Architected Review** - AWS WAF pillar assessments
- **Pattern Detection** - Uses IB Platform for intelligent pattern matching

---

## Glossary of Terms

| Term | Definition |
|------|------------|
| **Cloud Optimizer (CO)** | AWS cost optimization and WAF analysis application |
| **Intelligence-Builder (IB)** | Platform providing graph database, pattern detection, and domain infrastructure |
| **Tenant** | An isolated customer account (replaces legacy term "Organization") |
| **Scan** | Process of analyzing AWS resources for findings |
| **Finding** | A discovered issue (security vulnerability, cost inefficiency, compliance gap) |
| **Scanner** | Component that retrieves and analyzes AWS resource data |
| **Domain** | A pluggable module defining entity types, patterns, and operations |
| **WAF** | AWS Well-Architected Framework |

---

## Documentation Index

### 01-guides/ - Getting Started
| Document | Description |
|----------|-------------|
| [AI_DEVELOPER_GUIDE.md](./01-guides/AI_DEVELOPER_GUIDE.md) | Guide for AI agents working on this project |
| [QUICKSTART.md](./01-guides/QUICKSTART.md) | Quick start for developers |
| [LOCAL_DEVELOPMENT_GUIDE.md](./01-guides/LOCAL_DEVELOPMENT_GUIDE.md) | Local development setup |

### 02-architecture/ - Architecture & Design

**Authoritative Documents (Current):**

| Document | Description | Status |
|----------|-------------|--------|
| [ARCHITECTURE.md](./02-architecture/ARCHITECTURE.md) | **High-level system architecture** | Authoritative |
| [REQUIREMENTS_V2.md](./02-architecture/REQUIREMENTS_V2.md) | **Detailed requirements (221 total)** | Authoritative |
| [REQUIREMENTS_OWNERSHIP.md](./02-architecture/REQUIREMENTS_OWNERSHIP.md) | **CO vs IB requirements split (172 CO / 49 IB)** | Authoritative |
| [PHASED_IMPLEMENTATION_PLAN.md](./02-architecture/PHASED_IMPLEMENTATION_PLAN.md) | **MVP definition & phase breakdown (30 weeks)** | Authoritative |
| [IB_STRATEGIC_DESIGN.md](./02-architecture/IB_STRATEGIC_DESIGN.md) | **Intelligence-Builder platform design (IB requirements)** | Authoritative |
| [STRATEGIC_DESIGN_V2.md](./02-architecture/STRATEGIC_DESIGN_V2.md) | **Cloud Optimizer technical design (CO requirements)** | Authoritative |
| [IMPLEMENTATION_READINESS_MATRIX.md](./02-architecture/IMPLEMENTATION_READINESS_MATRIX.md) | **Migration mapping from legacy systems** | Authoritative |
| [MIGRATION.md](./02-architecture/MIGRATION.md) | **Gap analysis and migration guide** | Authoritative |
| [PROJECT_GOALS.md](./02-architecture/PROJECT_GOALS.md) | Project objectives | Reference |
| [MARKETING_TECHNICAL_GAP_ANALYSIS.md](./02-architecture/MARKETING_TECHNICAL_GAP_ANALYSIS.md) | Marketing vision vs technical requirements | Reference |

**Archived Documents:**
- See `02-architecture/_archive/` for superseded documents (STRATEGIC_DESIGN.md, TECHNICAL_DESIGN.md, etc.)

### 03-development/ - Development
| Document | Description |
|----------|-------------|
| [DEVELOPMENT_STANDARDS.md](./03-development/DEVELOPMENT_STANDARDS.md) | Coding standards and practices |
| [TESTING_GUIDE.md](./03-development/TESTING_GUIDE.md) | Testing strategies and requirements |
| [QUALITY_GATES.md](./03-development/QUALITY_GATES.md) | Quality gate requirements |

### 04-operations/ - Operations
| Document | Description |
|----------|-------------|
| [DOCKER_GUIDE.md](./04-operations/DOCKER_GUIDE.md) | Docker setup and operations |
| [DEPLOYMENT.md](./04-operations/DEPLOYMENT.md) | Deployment procedures |

### 05-integration/ - Platform Integration
| Document | Description |
|----------|-------------|
| [AWS_INTEGRATION_TESTING.md](./05-integration/AWS_INTEGRATION_TESTING.md) | AWS testing (LocalStack & real AWS) |
| [IB_SDK_INTEGRATION.md](./05-integration/IB_SDK_INTEGRATION.md) | Intelligence-Builder SDK usage |
| [SMART_SCAFFOLD_INTEGRATION.md](./05-integration/SMART_SCAFFOLD_INTEGRATION.md) | Smart-Scaffold integration |
| [DOMAIN_PATTERNS.md](./05-integration/DOMAIN_PATTERNS.md) | Domain-specific patterns |

### 06-reports/ - Reports & Handoffs
| Document | Description |
|----------|-------------|
| Session handoff documents | Session summaries and context |

### issues/ - Issue Templates
| Document | Description |
|----------|-------------|
| Epic and issue body templates | GitHub issue content |

---

## Quick Links

### For New Developers
1. Start with [QUICKSTART.md](./01-guides/QUICKSTART.md)
2. Read [ARCHITECTURE.md](./02-architecture/ARCHITECTURE.md) for system overview
3. Review [REQUIREMENTS_V2.md](./02-architecture/REQUIREMENTS_V2.md) for detailed requirements
4. Check [DEVELOPMENT_STANDARDS.md](./03-development/DEVELOPMENT_STANDARDS.md)

### For AI Agents
1. Start with [AI_DEVELOPER_GUIDE.md](./01-guides/AI_DEVELOPER_GUIDE.md)
2. Read [ARCHITECTURE.md](./02-architecture/ARCHITECTURE.md) for context
3. Check [REQUIREMENTS_V2.md](./02-architecture/REQUIREMENTS_V2.md) for current phase
4. Review current GitHub issues

### For Architecture Review
1. [ARCHITECTURE.md](./02-architecture/ARCHITECTURE.md) - High-level overview
2. [REQUIREMENTS_V2.md](./02-architecture/REQUIREMENTS_V2.md) - What to build
3. [STRATEGIC_DESIGN_V2.md](./02-architecture/STRATEGIC_DESIGN_V2.md) - How to build it
4. [MIGRATION.md](./02-architecture/MIGRATION.md) - Migration from legacy

### For Integration Work
1. Read [IB_SDK_INTEGRATION.md](./05-integration/IB_SDK_INTEGRATION.md)
2. Review [DOMAIN_PATTERNS.md](./05-integration/DOMAIN_PATTERNS.md)
3. Check IB SDK contract in [STRATEGIC_DESIGN_V2.md](./02-architecture/STRATEGIC_DESIGN_V2.md#13-ib-sdk-contract-specification)

### For AWS Testing
1. Read [AWS_INTEGRATION_TESTING.md](./05-integration/AWS_INTEGRATION_TESTING.md)
2. Configure credentials: `~/.aws/credentials`
3. Run: `USE_REAL_AWS=true PYTHONPATH=src pytest tests/integration/`

---

## Project Structure

```
cloud-optimizer/
├── src/
│   ├── cloud_optimizer/      # Main application code
│   │   ├── api/             # FastAPI app and routers
│   │   ├── services/        # Business logic services
│   │   ├── scanners/        # AWS resource scanners
│   │   ├── models/          # Pydantic models
│   │   └── repositories/    # Data access layer
│   │
│   └── ib_platform/         # Intelligence-Builder platform components
│       ├── graph/           # Graph database abstraction
│       ├── patterns/        # Pattern detection engine
│       └── domains/         # Domain module system
│
├── tests/                   # Test suite (80%+ coverage target)
├── docker/                  # Docker configuration
├── docs/                    # Documentation (you are here)
│   ├── 01-guides/          # Getting started guides
│   ├── 02-architecture/    # Architecture documents
│   ├── 03-development/     # Development standards
│   ├── 04-operations/      # Operations guides
│   ├── 05-integration/     # Integration guides
│   └── 06-reports/         # Reports and handoffs
│
└── evidence/               # Test evidence and reports
```

---

## Development Timeline

| Phase | Scope | Duration | Milestone |
|-------|-------|----------|-----------|
| **Phase 0** | Foundation Setup | 1 week | |
| **Phase 1** | Core Platform (MVP Foundation) | 4 weeks | |
| **Phase 2** | Core Features (MVP Completion) | 7 weeks | **MVP Week 12** |
| **Phase 3** | Frontend Application | 8 weeks | |
| **Phase 4** | Advanced Features (SSO, Analytics, Audit) | 6 weeks | |
| **Phase 5** | Post-MVP (Multi-Cloud, Feedback, Ontology) | 4 weeks | |
| **Total** | | **30 weeks** | |

> **42% timeline reduction** achieved by leveraging existing implementation from legacy Cloud_Optimizer and CloudGuardian codebases.

See [PHASED_IMPLEMENTATION_PLAN.md](./02-architecture/PHASED_IMPLEMENTATION_PLAN.md) for MVP definition and detailed phase breakdown.
See [REQUIREMENTS_V2.md](./02-architecture/REQUIREMENTS_V2.md) for the 221 detailed requirements.

---

## Related Projects

- **Intelligence-Builder** - The platform providing GraphRAG and pattern detection
- **Smart-Scaffold** - AI development framework with knowledge graph

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | 2025-11-30 | Documentation consolidation, added glossary, updated structure |
| 2.0.0 | 2025-11-29 | Clean-slate rebuild on IB Platform |
| 1.x | Prior | Legacy implementation |
