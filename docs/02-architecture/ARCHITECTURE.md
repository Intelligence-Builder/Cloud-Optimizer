# Cloud Optimizer v2 Architecture

**Version:** 2.1.0
**Last Updated:** 2025-11-30
**Status:** Authoritative High-Level Overview

---

## Document Purpose

This is the **single authoritative high-level architecture document** for Cloud Optimizer v2. For detailed specifications, see:

| Document | Purpose |
|----------|---------|
| [REQUIREMENTS_V2.md](./REQUIREMENTS_V2.md) | Detailed requirements by phase |
| [STRATEGIC_DESIGN_V2.md](./STRATEGIC_DESIGN_V2.md) | Technical design, patterns, decisions |
| [MIGRATION.md](./MIGRATION.md) | Gap analysis and migration from legacy |
| [PROJECT_GOALS.md](./PROJECT_GOALS.md) | Project objectives and success metrics |

Archived documents are in `./_archive/` for historical reference.

---

## Glossary of Terms

| Term | Definition |
|------|------------|
| **Cloud Optimizer (CO)** | AWS cost optimization and Well-Architected Framework analysis application |
| **Intelligence-Builder (IB)** | Platform providing graph database, pattern detection, and domain infrastructure |
| **IB SDK** | Software development kit for calling IB Platform services |
| **Tenant** | An isolated customer account (replaces legacy term "Organization") |
| **Scan** | Process of analyzing AWS resources for findings |
| **Finding** | A discovered issue (security vulnerability, cost inefficiency, compliance gap) |
| **Recommendation** | Suggested action to address a finding |
| **Scanner** | Component that retrieves and analyzes AWS resource data |
| **Domain** | A pluggable module defining entity types, patterns, and operations (e.g., Security, Cost) |
| **Pattern** | A regex-based rule for detecting entities or relationships in data |
| **WAF** | AWS Well-Architected Framework |
| **CTE** | Common Table Expression - PostgreSQL feature for graph traversal |
| **Knowledge Base** | Repository of ingested technical knowledge (CVEs, best practices, benchmarks) |
| **Expert System** | AI-driven recommendation engine using knowledge base + scan findings |
| **Ingestion** | Process of importing and normalizing knowledge from external sources |

---

## System Overview

Cloud Optimizer v2 is a **multi-tenant SaaS application** for AWS cloud optimization that leverages the Intelligence-Builder Platform for knowledge graph and pattern detection capabilities.

### Core Capabilities

1. **Security Analysis** - Vulnerability detection, threat identification, compliance checking
2. **Cost Optimization** - Spending analysis, savings recommendations, forecasting
3. **Well-Architected Review** - AWS WAF pillar assessments and remediation guidance
4. **Pattern Detection** - Intelligent pattern matching via IB Platform
5. **Expert System** - Knowledge-driven recommendations based on curated CVEs, best practices, and benchmarks

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Clean & Simple** | Target 10K LOC application code (business logic only) |
| **IB-First** | All intelligence operations through IB Platform |
| **Multi-Tenant Native** | Tenant isolation from day one via row-level security |
| **Contract-Driven** | Type-safe interfaces between all components |
| **Extensible** | Plugin architecture for domains and scanners |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLOUD OPTIMIZER V2                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        API Layer (FastAPI)                            │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌────────┐  │   │
│  │  │  /auth    │ │ /security │ │   /cost   │ │   /waf    │ │/dashboard│ │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      Middleware Layer                                 │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │   │
│  │  │   Auth/JWT  │ │Tenant Context│ │ Rate Limit  │ │  Audit Logger   │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       Service Layer                                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │   │
│  │  │ SecurityService │  │   CostService   │  │    WAFService       │   │   │
│  │  │ - Vuln scanning │  │ - Cost analysis │  │ - Pillar assessment │   │   │
│  │  │ - Compliance    │  │ - Forecasting   │  │ - Recommendations   │   │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    IB Platform Layer (Local)                          │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │   │
│  │  │  Graph Backends │  │  Pattern Engine │  │   Domain System     │   │   │
│  │  │ - PostgresCTE   │  │ - Detector      │  │ - SecurityDomain    │   │   │
│  │  │ - Memgraph      │  │ - Matcher       │  │ - CostDomain        │   │   │
│  │  │ - Factory       │  │ - Scorer        │  │ - WAFDomain         │   │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │   │
│  │  │                    Expert System                                 │  │   │
│  │  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │  │   │
│  │  │  │ Knowledge Base│  │  Reasoning    │  │  Recommendation   │   │  │   │
│  │  │  │ - CVEs        │  │  Engine       │  │  Generator        │   │  │   │
│  │  │  │ - Best pracs  │  │ - Graph query │  │ - Prioritization  │   │  │   │
│  │  │  │ - Benchmarks  │  │ - Inference   │  │ - Remediation     │   │  │   │
│  │  │  └───────────────┘  └───────────────┘  └───────────────────────┘   │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Infrastructure Layer                              │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │   │
│  │  │   PostgreSQL    │  │     Redis       │  │    AWS Services     │   │   │
│  │  │ - App data      │  │ - Sessions      │  │ - Cost Explorer     │   │   │
│  │  │ - Graph (CTE)   │  │ - Cache         │  │ - CloudWatch        │   │   │
│  │  │ - Knowledge     │  │ - Rate limits   │  │ - IAM, EC2, RDS...  │   │   │
│  │  │ - Audit logs    │  │                 │  │                     │   │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘   │
│  │                                                                       │   │
│  │  ┌──────────────────────────────────────────────────────────────┐     │   │
│  │  │              External Knowledge Sources                       │     │   │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐  │     │   │
│  │  │  │  NVD/  │ │  AWS   │ │  CIS   │ │  AWS   │ │   NIST/    │  │     │   │
│  │  │  │  CVE   │ │Security│ │Benchmrk│ │Pricing │ │   OWASP    │  │     │   │
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────────┘  │     │   │
│  │  └──────────────────────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### 1. API Layer (FastAPI)

| Endpoint Group | Responsibility |
|----------------|----------------|
| `/api/v1/auth` | Authentication, token management, user registration |
| `/api/v1/security` | Security scans, findings, vulnerabilities |
| `/api/v1/cost` | Cost analysis, recommendations, forecasts |
| `/api/v1/waf` | Well-Architected Framework assessments |
| `/api/v1/dashboard` | Aggregated metrics and visualizations |
| `/api/v1/admin` | Tenant management, user management |

### 2. Middleware Layer

| Middleware | Function |
|------------|----------|
| **Auth/JWT** | Validate JWT tokens, extract user context |
| **Tenant Context** | Inject tenant_id into request state, set RLS context |
| **Rate Limit** | Enforce per-tenant API quotas |
| **Audit Logger** | Log all API calls for compliance |

### 3. Service Layer

Business logic services that:
- Coordinate between API and platform layers
- Implement cloud-specific analysis logic
- Handle AWS SDK integration (via Scanners)
- Manage domain-specific workflows

### 4. IB Platform Layer

| Component | Purpose |
|-----------|---------|
| **Graph Backends** | PostgresCTE and Memgraph implementations of GraphBackendProtocol |
| **Pattern Engine** | Detection, matching, and confidence scoring |
| **Domain System** | Pluggable domain modules (Security, Cost, WAF) |
| **Expert System** | Knowledge-driven recommendation engine (see below) |

### 4.1 Expert System Architecture

The Expert System is the intelligence core that transforms raw scan findings into actionable recommendations. It consists of three components:

| Component | Function |
|-----------|----------|
| **Knowledge Base** | Repository of curated knowledge (CVEs, best practices, CIS benchmarks, AWS pricing) |
| **Reasoning Engine** | Queries knowledge graph to find relevant context for findings |
| **Recommendation Generator** | Produces prioritized, actionable recommendations with remediation steps |

#### How Recommendations are Generated

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Scan Finding   │────▶│ Reasoning Engine│────▶│ Recommendation  │
│ (from Scanner)  │     │ (graph queries) │     │   (output)      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Knowledge Base │
                        │ (CVEs, controls,│
                        │  best practices)│
                        └─────────────────┘
```

1. **Scanner** detects a finding (e.g., "S3 bucket has public access")
2. **Reasoning Engine** queries knowledge graph:
   - Find related CVEs/vulnerabilities
   - Find applicable CIS benchmark controls
   - Find remediation best practices
3. **Recommendation Generator** produces output:
   - Severity based on CVE/finding impact
   - Remediation steps from best practices
   - Compliance impact (CIS, SOC2, etc.)
   - Cost impact (if applicable)

#### Knowledge Sources (Ingested via Pipeline)

| Source | Content | Update Frequency |
|--------|---------|------------------|
| NVD/CVE Database | Known vulnerabilities | Daily |
| AWS Security Bulletins | AWS-specific advisories | Daily |
| CIS Benchmarks | Security control frameworks | Monthly |
| AWS Pricing API | Service pricing for cost analysis | Weekly |
| NIST Guidelines | Security frameworks | Quarterly |
| OWASP | Application security guidance | Yearly |

See [STRATEGIC_DESIGN_V2.md](./STRATEGIC_DESIGN_V2.md#17-knowledge-base--expert-system-architecture) for implementation details.
See [REQUIREMENTS_V2.md](./REQUIREMENTS_V2.md#45-knowledge-ingestion-system) for KNG-* requirements.

### 5. Infrastructure Layer

| System | Role |
|--------|------|
| **PostgreSQL** | Application data, graph storage (CTE), knowledge base, audit logs |
| **Redis** | Session storage, query cache, rate limit counters |
| **AWS Services** | Source data for scans (Cost Explorer, CloudWatch, IAM, etc.) |
| **External Sources** | Knowledge ingestion (NVD, AWS Security, CIS, NIST, OWASP) |

---

## Multi-Tenancy Architecture

### Tenant Isolation Model

```
┌─────────────────────────────────────────────────────────────┐
│                     Single Database                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │   Tenant A      │  │   Tenant B      │  ... (RLS)        │
│  │   tenant_id=A   │  │   tenant_id=B   │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Isolation Mechanism

1. **JWT Token** contains `tenant_id` claim
2. **Middleware** extracts tenant_id and sets PostgreSQL session variable
3. **Row-Level Security (RLS)** policies filter all queries automatically
4. **Application code** never needs to add tenant filters manually

```python
# Middleware sets context
await conn.execute("SET app.current_tenant_id = $1", tenant_id)

# RLS policy handles filtering
CREATE POLICY tenant_isolation ON findings
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

---

## Data Flow Examples

### Security Scan Flow

```
1. POST /api/v1/security/scan
         │
         ▼
2. Auth Middleware validates JWT, extracts tenant_id
         │
         ▼
3. SecurityService.start_scan(tenant_id, aws_account)
         │
         ▼
4. IAMScanner → AWS IAM API → Raw findings
   SecurityGroupScanner → AWS EC2 API → Raw findings
         │
         ▼
5. Pattern Engine detects patterns, scores confidence
         │
         ▼
6. SecurityDomain validates entities
         │
         ▼
7. Graph Backend stores entities and relationships
         │
         ▼
8. Response: { scan_id, status, finding_count }
```

### Cost Analysis Flow

```
1. POST /api/v1/cost/analyze
         │
         ▼
2. Auth Middleware validates JWT, extracts tenant_id
         │
         ▼
3. CostService.analyze(tenant_id, date_range)
         │
         ▼
4. CostExplorerScanner → AWS Cost Explorer API
         │
         ▼
5. Pattern Engine identifies cost patterns (idle resources, RI opportunities)
         │
         ▼
6. CostDomain generates recommendations
         │
         ▼
7. Response: { total_cost, savings_potential, recommendations[] }
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Graph Backend** | PostgresCTE (default), Memgraph (optional) | PostgresCTE requires no extra infrastructure; Memgraph for complex traversals |
| **Multi-Tenancy** | Single DB with RLS | Cost-effective, strong isolation, easy to scale |
| **IB Integration** | Embedded locally | Lower latency, simpler deployment, no network dependency |
| **Authentication** | JWT with refresh tokens | Stateless, scalable, industry standard |
| **API Framework** | FastAPI | Type-safe, async, auto-docs, high performance |
| **Caching** | Redis | Sessions, rate limits, query cache in one system |

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Health check | < 10ms | Simple DB ping |
| Auth validation | < 50ms | JWT decode + cache lookup |
| Simple query | < 100ms | Single table with index |
| Security scan | < 60s | Full account scan |
| Graph traversal (1K nodes) | < 100ms | PostgresCTE optimized |
| API p95 latency | < 500ms | Across all endpoints |

---

## Security Architecture (Summary)

| Aspect | Implementation |
|--------|----------------|
| **Authentication** | JWT tokens (15m access, 7d refresh) |
| **Authorization** | RBAC with tenant isolation |
| **Data Protection** | TLS 1.3 in transit, AES-256 at rest |
| **Secrets** | AWS Secrets Manager, no hardcoded credentials |
| **Audit** | All API calls logged with user, tenant, action |
| **Input Validation** | Pydantic models on all endpoints |

See [STRATEGIC_DESIGN_V2.md](./STRATEGIC_DESIGN_V2.md) for detailed security architecture.

---

## Module Structure

```
cloud-optimizer/
├── src/
│   ├── cloud_optimizer/        # Application code
│   │   ├── api/               # FastAPI app and routers
│   │   │   ├── main.py        # App factory
│   │   │   └── routers/       # Endpoint definitions
│   │   ├── services/          # Business logic (< 300 LOC each)
│   │   ├── scanners/          # AWS resource scanners
│   │   ├── models/            # Pydantic models
│   │   └── repositories/      # Data access layer
│   │
│   └── ib_platform/           # Intelligence-Builder platform
│       ├── graph/             # Graph database abstraction
│       ├── patterns/          # Pattern detection engine
│       └── domains/           # Domain module system
│
├── tests/                     # Test suite (80%+ coverage target)
├── docker/                    # Docker configuration
├── docs/                      # Documentation
└── evidence/                  # Test evidence and reports
```

---

## Deployment Architecture

### Local Development

```yaml
docker-compose.yml:
  - api: FastAPI app (port 8000)
  - postgres: PostgreSQL (port 5432)
  - redis: Redis (port 6379)
  - localstack: AWS mock (port 4566) [optional]
```

### Production (AWS)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Route 53  │────▶│  CloudFront │────▶│     ALB     │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          ▼                          │
                    │  ┌─────────────────────────────────────────────┐   │
                    │  │              ECS Fargate                     │   │
                    │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐      │   │
                    │  │  │  API    │  │  API    │  │  API    │      │   │
                    │  │  │ Task 1  │  │ Task 2  │  │ Task N  │      │   │
                    │  │  └─────────┘  └─────────┘  └─────────┘      │   │
                    │  └─────────────────────────────────────────────┘   │
                    │                          │                          │
                    │         ┌────────────────┼────────────────┐         │
                    │         ▼                ▼                ▼         │
                    │  ┌───────────┐    ┌───────────┐    ┌───────────┐   │
                    │  │    RDS    │    │ElastiCache│    │  Secrets  │   │
                    │  │ PostgreSQL│    │   Redis   │    │  Manager  │   │
                    │  └───────────┘    └───────────┘    └───────────┘   │
                    │                                                     │
                    └─────────────────────────────────────────────────────┘
```

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [REQUIREMENTS_V2.md](./REQUIREMENTS_V2.md) | Detailed requirements organized by phase |
| [STRATEGIC_DESIGN_V2.md](./STRATEGIC_DESIGN_V2.md) | Technical design, patterns, IB SDK contract |
| [MIGRATION.md](./MIGRATION.md) | Gap analysis and migration guidance |
| [PROJECT_GOALS.md](./PROJECT_GOALS.md) | Project objectives and success metrics |
| [../03-development/](../03-development/) | Development standards and testing guides |
| [../05-integration/](../05-integration/) | AWS and platform integration guides |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.2.0 | 2025-11-30 | Added Expert System architecture, knowledge base, external sources |
| 2.1.0 | 2025-11-30 | Consolidated from multiple docs, added glossary, updated references |
| 2.0.0 | 2025-11-29 | Initial v2 architecture |
