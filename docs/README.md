# Cloud Optimizer Documentation

**Version:** 2.0.0
**Last Updated:** 2025-11-29

---

## Overview

Cloud Optimizer is an AWS cost optimization and Well-Architected Framework analysis tool built on the Intelligence-Builder platform. It provides:

- **Cost Analysis** - AWS spending analysis and savings recommendations
- **Security Assessment** - Vulnerability detection and compliance checking
- **Well-Architected Review** - AWS WAF pillar assessments
- **Pattern Detection** - Uses IB Platform for intelligent pattern matching

---

## Documentation Index

### 01-guides/ - Getting Started
| Document | Description |
|----------|-------------|
| [AI_DEVELOPER_GUIDE.md](./01-guides/AI_DEVELOPER_GUIDE.md) | Guide for AI agents working on this project |
| [QUICKSTART.md](./01-guides/QUICKSTART.md) | Quick start for developers |
| [LOCAL_DEVELOPMENT_GUIDE.md](./01-guides/LOCAL_DEVELOPMENT_GUIDE.md) | Local development setup |

### 02-architecture/ - Architecture & Design
| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./02-architecture/ARCHITECTURE.md) | System architecture overview |
| [PROJECT_GOALS.md](./02-architecture/PROJECT_GOALS.md) | Project goals and objectives |
| [STRATEGIC_DESIGN.md](./02-architecture/STRATEGIC_DESIGN.md) | Strategic design decisions |
| [TECHNICAL_DESIGN.md](./02-architecture/TECHNICAL_DESIGN.md) | Technical implementation details |

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
2. Read [ARCHITECTURE.md](./02-architecture/ARCHITECTURE.md)
3. Review [DEVELOPMENT_STANDARDS.md](./03-development/DEVELOPMENT_STANDARDS.md)

### For AI Agents
1. Start with [AI_DEVELOPER_GUIDE.md](./01-guides/AI_DEVELOPER_GUIDE.md)
2. Check latest session handoff in [06-reports/](./06-reports/)
3. Review current GitHub issues

### For Integration Work
1. Read [IB_SDK_INTEGRATION.md](./05-integration/IB_SDK_INTEGRATION.md)
2. Review [DOMAIN_PATTERNS.md](./05-integration/DOMAIN_PATTERNS.md)

---

## Project Structure

```
cloud-optimizer/
├── src/
│   ├── cloud_optimizer/      # Main application code
│   │   ├── services/         # Business logic services
│   │   ├── routers/          # API endpoints
│   │   └── models/           # Data models
│   └── ib_platform/          # Intelligence-Builder platform components
│       ├── graph/            # Graph database abstraction
│       ├── patterns/         # Pattern detection engine
│       └── domains/          # Domain module system
├── tests/                    # Test suite
├── docker/                   # Docker configuration
├── docs/                     # Documentation (you are here)
└── evidence/                 # Test evidence and reports
```

---

## Related Projects

- **Intelligence-Builder** - The platform providing GraphRAG and pattern detection
- **Smart-Scaffold** - AI development framework with knowledge graph

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-11-29 | Clean-slate rebuild on IB Platform |
| 1.x | Prior | Legacy implementation |
