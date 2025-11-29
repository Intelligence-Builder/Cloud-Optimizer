# Cloud Optimizer Architecture

**Version:** 2.0.0
**Last Updated:** 2025-11-29

---

## Overview

Cloud Optimizer v2 is a thin client application that leverages the Intelligence-Builder (IB) Platform for all knowledge graph and pattern detection capabilities. This architecture provides:

- **Separation of Concerns** - Cloud Optimizer focuses on AWS/cloud domain logic
- **Platform Reuse** - IB Platform provides graph, patterns, and domain infrastructure
- **Extensibility** - New cloud providers or analysis types are easy to add

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLOUD OPTIMIZER V2                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        API Layer (FastAPI)                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │   /health   │  │  /security  │  │    /cost    │  │    /waf     │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       Service Layer                                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │   │
│  │  │ SecurityService │  │   CostService   │  │    WAFService       │   │   │
│  │  │ - Vuln detection│  │ - Cost analysis │  │ - Pillar assessment │   │   │
│  │  │ - Compliance    │  │ - Trends        │  │ - Recommendations   │   │   │
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
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                  │
            ┌───────▼───────┐                 ┌───────▼───────┐
            │  PostgreSQL   │                 │   Memgraph    │
            │  (CTE Graph)  │                 │ (Native Graph)│
            │  Port: 5434   │                 │  Port: 7688   │
            └───────────────┘                 └───────────────┘
```

---

## Component Overview

### 1. API Layer
FastAPI-based REST API providing endpoints for:
- **Health** - Service health and readiness checks
- **Security** - Vulnerability analysis, threat detection, compliance
- **Cost** - AWS cost analysis and optimization recommendations
- **WAF** - Well-Architected Framework assessments

### 2. Service Layer
Business logic services that:
- Coordinate between API and platform layers
- Implement cloud-specific analysis logic
- Handle AWS SDK integration
- Manage domain-specific workflows

### 3. IB Platform Layer
Embedded platform components providing:
- **Graph Backends** - PostgresCTE and Memgraph implementations
- **Pattern Engine** - Detection, matching, and scoring
- **Domain System** - Pluggable domain modules (Security, Cost, WAF)

### 4. Data Layer
Dual-backend graph storage:
- **PostgresCTE** - PostgreSQL with recursive CTEs for graph traversal
- **Memgraph** - Native graph database with Cypher queries

---

## Data Flow

### Security Analysis Flow
```
1. Request → /api/v1/security/analyze
2. SecurityService receives request
3. Pattern Engine detects security patterns
4. SecurityDomain validates entities
5. Graph backend stores/retrieves entities
6. Response with findings and recommendations
```

### Cost Analysis Flow
```
1. Request → /api/v1/cost/analyze
2. CostService receives request
3. AWS SDK fetches cost data
4. Pattern Engine identifies cost patterns
5. Graph backend stores cost entities
6. Response with cost insights
```

---

## Key Design Decisions

### 1. Embedded Platform vs SDK
**Decision:** Embed IB Platform components locally rather than using remote SDK calls.

**Rationale:**
- Lower latency for graph operations
- Simpler deployment (single application)
- Full control over database backends
- No network dependency for core operations

### 2. Dual Graph Backends
**Decision:** Support both PostgresCTE and Memgraph backends.

**Rationale:**
- PostgresCTE: Works with existing PostgreSQL, no additional infrastructure
- Memgraph: Better performance for complex graph traversals
- Factory pattern allows runtime switching

### 3. Domain Module System
**Decision:** Implement domains as pluggable modules.

**Rationale:**
- Easy to add new cloud providers
- Separation of domain logic from infrastructure
- Testable domain implementations
- Reusable validation patterns

---

## Module Boundaries

### ib_platform/ (Platform Infrastructure)
```
ib_platform/
├── graph/           # Graph database abstraction
│   ├── protocol.py  # GraphBackendProtocol
│   ├── factory.py   # Backend factory
│   └── backends/    # PostgresCTE, Memgraph
├── patterns/        # Pattern detection
│   ├── detector.py  # Pattern orchestrator
│   ├── matcher.py   # Graph-based matching
│   └── scorer.py    # Confidence scoring
└── domains/         # Domain modules
    ├── base.py      # BaseDomain abstract class
    ├── registry.py  # Domain registry
    └── security/    # Security domain
```

### cloud_optimizer/ (Application)
```
cloud_optimizer/
├── services/        # Business logic
│   ├── security.py  # Security analysis
│   ├── cost.py      # Cost analysis
│   └── waf.py       # WAF assessment
├── routers/         # API endpoints
│   ├── security.py
│   ├── cost.py
│   └── waf.py
└── models/          # Data models
```

---

## Integration Points

### With Intelligence-Builder (Future)
When full IB SDK integration is needed:
- Remote GraphRAG queries
- Shared knowledge graphs
- Cross-application pattern sharing

### With AWS
- AWS SDK (boto3) for resource scanning
- CloudWatch for metrics
- Cost Explorer for cost data
- Config for compliance rules

### With Smart-Scaffold
- Knowledge graph context during development
- Issue tracking and automation
- Quality gate enforcement

---

## Performance Considerations

### Graph Operations
- PostgresCTE: Optimized for 1000-node traversals < 100ms
- Memgraph: Native graph for complex path finding
- Batch operations: 1000+ nodes efficiently

### Pattern Detection
- In-memory caching for frequent patterns
- Async detection for parallel processing
- Confidence scoring < 10ms per pattern

### API Response Times
- Health check: < 10ms
- Simple queries: < 100ms
- Complex analysis: < 2s

---

## Security Architecture

### Authentication
- JWT tokens for API access
- API keys for service-to-service

### Data Protection
- Soft deletes for audit trail
- Encrypted sensitive properties
- Tenant isolation in multi-tenant mode

### Access Control
- Role-based access (admin, analyst, viewer)
- Domain-level permissions
- Resource-level authorization

---

## Related Documentation

- [TECHNICAL_DESIGN.md](./TECHNICAL_DESIGN.md) - Detailed technical specifications
- [STRATEGIC_DESIGN.md](./STRATEGIC_DESIGN.md) - Strategic decisions and rationale
- [PROJECT_GOALS.md](./PROJECT_GOALS.md) - Project objectives
