# Intelligence-Builder Platform: Strategic Design

**Document Version**: 1.0
**Created**: 2025-11-28
**Status**: Active

---

## Overview

This document describes the strategic architecture decisions for the Intelligence-Builder platform. It focuses on the "why" behind architectural choices and how components relate at a high level.

---

## Strategic Context: Clean-Slate Rebuild

> **This initiative is not simply about consolidating knowledge graphs across three systems. It is a strategic opportunity to rebuild Cloud Optimizer from scratch on top of a proper platform foundation.**

### The Problem

Cloud Optimizer v1 has accumulated significant technical debt:
- **50K+ lines of code** that should be <10K for an application of this scope
- **Messy, inconsistent architecture** - no clear separation between platform and application concerns
- **Tightly coupled components** - difficult to modify or extend
- **Documentation sprawl** - too many files, inconsistent, outdated

### The Opportunity

Rather than refactor CO in place (which would perpetuate existing problems), we are:

1. **Building the platform right** - IB becomes the core GraphRAG platform with:
   - Graph DB abstraction (PostgreSQL CTE + Memgraph)
   - Pattern detection engine
   - Domain module system
   - Core orchestration

2. **Rebuilding CO as a thin application** - CO v2 will be:
   - A new, clean repository
   - Pure application logic consuming IB services via SDK
   - Target: **< 10K LOC** (down from 50K+)
   - Enterprise-grade code quality

3. **Migrating carefully, part by part** - Not a big-bang migration:
   - Security domain first (priority)
   - Validate each piece works before moving on
   - Optimize and clean as we port
   - Result: Clean, maintainable, extensible

### Design Implications

This clean-slate approach influences every architectural decision:

| Aspect | Implication |
|--------|-------------|
| **What lives in IB** | All knowledge graph infrastructure, pattern detection, domains |
| **What lives in CO v2** | Only AWS integration, UI, CO-specific business rules |
| **Code quality bar** | No 500+ line files, no complex orchestrators, no tight coupling |
| **Domain boundaries** | Strict - CO v2 ONLY calls IB APIs, never bypasses to database |

---

## Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION LAYER                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐   │
│  │ Cloud Optimizer │  │  Smart-Scaffold │  │  Legal Advisor  │  │ Future Apps  │   │
│  │   v2 (Clean)    │  │                 │  │    (Future)     │  │              │   │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤  ├──────────────┤   │
│  │ • Own UI        │  │ • Context Sys   │  │ • Own UI        │  │              │   │
│  │ • Business Logic│  │ • Workflow Coord│  │ • Business Logic│  │              │   │
│  │ • 5 Domains     │  │ • Agent Orch    │  │ • Legal Domain  │  │              │   │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘   │
│           │                    │                    │                  │            │
│           └────────────────────┴────────────────────┴──────────────────┘            │
│                                        │                                            │
│                          IB Platform SDK (Python Client)                            │
│                                        │                                            │
├────────────────────────────────────────┴────────────────────────────────────────────┤
│                     INTELLIGENCE-BUILDER PLATFORM (CORE)                            │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                          PLATFORM API GATEWAY                                 │  │
│  │  /api/v1/                                                                    │  │
│  │    ├── entities/           - Entity CRUD                                     │  │
│  │    ├── relationships/      - Relationship CRUD                               │  │
│  │    ├── graph/              - Traversal, paths, subgraphs                     │  │
│  │    ├── search/             - Vector, hybrid, semantic                        │  │
│  │    ├── patterns/           - Pattern registry & detection                    │  │
│  │    ├── domains/            - Domain registry & operations                    │  │
│  │    ├── ontology/           - Schema definitions                              │  │
│  │    └── orchestrate/        - Query orchestration                             │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                       CORE SERVICES LAYER                                     │  │
│  │                                                                               │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │  │
│  │  │ Pattern Engine  │  │ Core Orchestrator│  │ Domain Registry │               │  │
│  │  │ • Detection     │  │ • Query Intake   │  │ • Registration  │               │  │
│  │  │ • Scoring       │  │ • Strategy Select│  │ • Validation    │               │  │
│  │  │ • Discovery     │  │ • Execution      │  │ • Lifecycle     │               │  │
│  │  │ • Registry      │  │ • Synthesis      │  │ • Versioning    │               │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘               │  │
│  │                                                                               │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │  │
│  │  │ Ontology Service│  │ Embedding Service│  │  Cache Service  │               │  │
│  │  │ • Schemas       │  │ • Generation    │  │ • L1 (Memory)   │               │  │
│  │  │ • Validation    │  │ • Storage       │  │ • L2 (Redis)    │               │  │
│  │  │ • Evolution     │  │ • Search        │  │ • Invalidation  │               │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘               │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                     GRAPH DATABASE ABSTRACTION LAYER                          │  │
│  │                                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                     GraphBackendProtocol                                │ │  │
│  │  │  • traverse()           • find_path()         • get_subgraph()          │ │  │
│  │  │  • batch_create_nodes() • batch_create_edges() • execute_query()        │ │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │  │
│  │                          │                           │                        │  │
│  │           ┌──────────────┴──────────────┐ ┌─────────┴──────────────┐         │  │
│  │           │   PostgreSQL CTE Backend    │ │   Memgraph Backend     │         │  │
│  │           │   (Default)                 │ │   (Optional)           │         │  │
│  │           │                             │ │                        │         │  │
│  │           │   • Recursive CTEs          │ │   • Native Cypher      │         │  │
│  │           │   • No extra infrastructure │ │   • Complex patterns   │         │  │
│  │           │   • ACID transactions       │ │   • High performance   │         │  │
│  │           └─────────────────────────────┘ └────────────────────────┘         │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │                       INFRASTRUCTURE LAYER                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │ PostgreSQL  │  │  pgvector   │  │    Redis    │  │  Memgraph   │          │  │
│  │  │ (Entities,  │  │ (Semantic   │  │  (Caching)  │  │ (Optional   │          │  │
│  │  │  Relations, │  │  Embeddings)│  │             │  │  Graph DB)  │          │  │
│  │  │  Ontology)  │  │             │  │             │  │             │          │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘          │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Architectural Principles

### 1. Platform-First Design

**Principle**: IB is a platform, not a library or shared service.

**Implications**:
- Well-defined APIs with versioning and deprecation policies
- SDK for client applications (not direct database access)
- Multi-tenant by design
- Self-service domain registration

**Rationale**: Enables multiple applications to build on IB independently, evolving at their own pace while sharing core infrastructure.

### 2. Domain-Driven Extensibility

**Principle**: Domains are first-class citizens with isolated schemas, patterns, and logic.

**Implications**:
- Each domain defines its own entity types, relationships, and patterns
- Domains can depend on other domains
- Domain logic is isolated but shares platform infrastructure
- New domains can be added without platform changes

**Rationale**: Supports the core value proposition of unlimited domain expansion (security, cost, legal, compliance, etc.).

### 3. Pattern Detection as Foundation

**Principle**: Automatic pattern detection during graph construction is a core platform capability.

**Implications**:
- Pattern engine is domain-agnostic
- Domains register patterns; platform executes them
- Confidence scoring is multi-factor and extensible
- Pattern discovery learns new patterns from data

**Rationale**: Every domain benefits from structured knowledge extraction. Centralizing this avoids duplication and ensures consistency.

### 4. Graph Backend Abstraction

**Principle**: Applications don't know or care which graph backend is used.

**Implications**:
- Clean protocol/interface for graph operations
- PostgreSQL CTE as default (no extra infrastructure)
- Memgraph as option for complex graph patterns
- Backend selection is configuration, not code change

**Rationale**: Flexibility to optimize for different workloads without application changes. Start simple, scale when needed.

### 5. Clean Application Architecture

**Principle**: Applications built on IB are thin layers with minimal code.

**Implications**:
- Applications use IB SDK, not direct database access
- Business logic is application-specific, not platform
- Applications can have extended orchestrators
- Strict code quality enforcement

**Rationale**: Keeps applications maintainable and ensures platform is doing the heavy lifting.

---

## Component Responsibilities

### Platform Components (IB Core)

| Component | Responsibility | Does NOT Handle |
|-----------|----------------|-----------------|
| **Pattern Engine** | Detection, scoring, discovery, registry | Domain-specific pattern definitions |
| **Core Orchestrator** | Query intake, strategy selection, execution | Domain-specific strategies |
| **Domain Registry** | Registration, validation, lifecycle | Domain business logic |
| **Ontology Service** | Schema management, validation | Domain schema definitions |
| **Graph Abstraction** | Unified graph operations | Backend-specific optimizations |
| **Embedding Service** | Generation, storage, search | Model training |
| **Cache Service** | L1/L2 caching, invalidation | Application-specific caching |

### Application Components

| Component | Responsibility | Depends On |
|-----------|----------------|------------|
| **Domain Modules** | Entity types, relationships, patterns | Platform registry |
| **Extended Orchestrator** | Domain-specific query strategies | Core orchestrator hooks |
| **Business Logic** | Application-specific processing | IB SDK |
| **API Layer** | Application-specific endpoints | IB SDK |
| **UI** | User interface | Application API |

---

## Domain Module Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          DOMAIN MODULE STRUCTURE                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Domain: Security (Priority #1)                                                 │
│  ═══════════════════════════════                                                │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      ENTITY TYPES                                        │   │
│  │                                                                          │   │
│  │  • vulnerability      - Security vulnerabilities (CVE, severity, etc.)   │   │
│  │  • threat             - Threat actors, attack vectors                    │   │
│  │  • control            - Security controls (preventive, detective, etc.)  │   │
│  │  • compliance_req     - Compliance requirements (SOC2, HIPAA, etc.)      │   │
│  │  • encryption_config  - Encryption settings and configurations           │   │
│  │  • access_policy      - IAM policies, access rules                       │   │
│  │  • security_group     - Network security groups                          │   │
│  │  • security_finding   - Security scan findings                           │   │
│  │  • identity           - Users, roles, service accounts                   │   │
│  │  • secret             - Secrets, credentials, API keys                   │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      RELATIONSHIP TYPES                                  │   │
│  │                                                                          │   │
│  │  • mitigates          - Control mitigates vulnerability                  │   │
│  │  • exposes            - Configuration exposes to threat                  │   │
│  │  • requires           - Resource requires compliance requirement         │   │
│  │  • implements         - Control implements compliance requirement        │   │
│  │  • violates           - Finding violates policy                          │   │
│  │  • protects           - Control protects resource                        │   │
│  │  • grants_access      - Policy grants access to identity                 │   │
│  │  • authenticates      - Identity authenticates to resource               │   │
│  │  • encrypts           - Encryption config encrypts resource              │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      PATTERNS                                            │   │
│  │                                                                          │   │
│  │  Entity Patterns:                                                        │   │
│  │  • CVE references: CVE-\d{4}-\d{4,7}                                     │   │
│  │  • IAM policies: \b(IAM|policy|role|permission)\b                        │   │
│  │  • Encryption: \b(encrypt|AES|KMS|TLS|SSL)\b                             │   │
│  │  • Compliance: \b(SOC2|HIPAA|PCI-DSS|GDPR|ISO27001)\b                    │   │
│  │  • Security groups: \b(security group|firewall|ingress|egress)\b         │   │
│  │                                                                          │   │
│  │  Relationship Patterns:                                                  │   │
│  │  • "{control} mitigates {vulnerability}"                                 │   │
│  │  • "{resource} is protected by {control}"                                │   │
│  │  • "{policy} grants {permission} to {identity}"                          │   │
│  │                                                                          │   │
│  │  Context Patterns:                                                       │   │
│  │  • Severity: \b(critical|high|medium|low|informational)\b                │   │
│  │  • CVSS scores: CVSS[:\s]*(\d+\.?\d*)                                    │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      CONFIDENCE FACTORS                                  │   │
│  │                                                                          │   │
│  │  • severity_context     - Nearby severity indicators boost confidence    │   │
│  │  • cve_reference        - CVE number reference boosts confidence         │   │
│  │  • compliance_framework - Framework name nearby boosts confidence        │   │
│  │  • technical_context    - Technical terms boost confidence               │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      CUSTOM OPERATIONS                                   │   │
│  │                                                                          │   │
│  │  • find_unmitigated_vulnerabilities(severity_threshold)                  │   │
│  │  • check_compliance_coverage(framework)                                  │   │
│  │  • trace_access_path(identity, resource)                                 │   │
│  │  • find_encryption_gaps()                                                │   │
│  │                                                                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Architecture

### Document Ingestion Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        DOCUMENT INGESTION PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   DOCUMENT                                                                      │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ 1. TEXT PROCESSING                                                      │  │
│   │    • Chunking (configurable size)                                       │  │
│   │    • Cleaning (normalize whitespace, encoding)                          │  │
│   │    • Language detection                                                 │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ 2. PATTERN DETECTION (Platform Core)                                    │  │
│   │    • Load domain patterns from registry                                 │  │
│   │    • Execute pattern matching (parallel)                                │  │
│   │    • Extract entities, relationships, context                           │  │
│   │    • Apply confidence scoring                                           │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ 3. ONTOLOGY VALIDATION                                                  │  │
│   │    • Validate entity types against domain schema                        │  │
│   │    • Validate relationship types                                        │  │
│   │    • Map unknown types or flag for review                               │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ 4. EMBEDDING GENERATION                                                 │  │
│   │    • Generate embeddings for entities                                   │  │
│   │    • Cache embeddings (L1/L2)                                           │  │
│   │    • Store in pgvector                                                  │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ 5. GRAPH CONSTRUCTION                                                   │  │
│   │    • Create entity nodes (via Graph Backend)                            │  │
│   │    • Create relationship edges (via Graph Backend)                      │  │
│   │    • Detect hierarchy, create parent-child edges                        │  │
│   │    • Apply domain hooks (pre/post create)                               │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ 6. PATTERN DISCOVERY (Feedback Loop)                                    │  │
│   │    • Analyze new graph data                                             │  │
│   │    • Detect naming patterns                                             │  │
│   │    • Detect relationship patterns                                       │  │
│   │    • Suggest new patterns for registry                                  │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   KNOWLEDGE GRAPH                                                               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Query Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           QUERY ORCHESTRATION FLOW                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   USER QUERY                                                                    │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ 1. INTAKE (Core Orchestrator)                                           │  │
│   │    • Parse query                                                        │  │
│   │    • Detect intent (factual, analytical, relational, etc.)              │  │
│   │    • Route to relevant domains                                          │  │
│   │    • Assess complexity                                                  │  │
│   │                                                                         │  │
│   │    Extension Point: on_query_received()                                 │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ 2. STRATEGY SELECTION                                                   │  │
│   │    • Check custom strategies (application-registered)                   │  │
│   │    • Select execution strategy:                                         │  │
│   │      - VECTOR_ONLY: Semantic search only                                │  │
│   │      - GRAPH_ONLY: Graph traversal only                                 │  │
│   │      - VECTOR_FIRST: Semantic then graph expansion                      │  │
│   │      - GRAPH_FIRST: Graph then semantic enrichment                      │  │
│   │      - PARALLEL_HYBRID: Both in parallel, merge results                 │  │
│   │                                                                         │  │
│   │    Extension Point: select_strategy()                                   │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ 3. EXECUTION                                                            │  │
│   │    • Execute via Graph Backend (PostgreSQL CTE or Memgraph)             │  │
│   │    • Execute vector search (pgvector)                                   │  │
│   │    • Merge results based on strategy                                    │  │
│   │    • Apply domain-specific processing                                   │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ 4. SYNTHESIS                                                            │  │
│   │    • Rank results                                                       │  │
│   │    • Generate answer (optional LLM)                                     │  │
│   │    • Extract citations                                                  │  │
│   │    • Calculate confidence                                               │  │
│   │                                                                         │  │
│   │    Extension Point: on_results_ready()                                  │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   RESPONSE                                                                      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Integration Patterns

### Application Integration via SDK

```python
# Application code using IB Platform SDK

from intelligence_builder_sdk import IBPlatformClient
from intelligence_builder_sdk.domains import SecurityDomain

# Initialize client
client = IBPlatformClient(
    base_url="https://ib-platform.example.com",
    api_key=os.environ["IB_API_KEY"],
    tenant_id="cloud-optimizer-v2",
)

# Register domain (typically at startup)
security_domain = SecurityDomain()
await client.domains.register(security_domain)

# Ingest document with pattern detection
result = await client.ingest.process_document(
    document_text=document_content,
    domains=["security"],
    min_confidence=0.7,
)

# Query the graph
query_result = await client.orchestrate.query(
    query="What vulnerabilities affect our S3 buckets?",
    domains=["security"],
)

# Direct graph operations
neighbors = await client.graph.get_neighbors(
    entity_id=entity_uuid,
    relationship_types=["mitigates", "protects"],
    max_depth=2,
)
```

### Smart-Scaffold Integration

Smart-Scaffold uses IB for knowledge but maintains local systems:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    SMART-SCAFFOLD INTEGRATION                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   SMART-SCAFFOLD                                                                │
│   ══════════════                                                                │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │  LOCAL SYSTEMS (PostgreSQL)                                             │  │
│   │  • Context records (revision-controlled, optimistic locking)            │  │
│   │  • Workflow events (temporal, event sourcing)                           │  │
│   │  • Discovered patterns (workflow-specific)                              │  │
│   │  • Session state                                                        │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                              │                                                  │
│                              │ Workflow coordination                            │
│                              ▼                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │  IB PLATFORM CLIENT                                                     │  │
│   │  • Store issues, PRs, commits as entities                               │  │
│   │  • Store relationships (implements, tests, modifies)                    │  │
│   │  • Vector search for similar issues                                     │  │
│   │  • Graph traversal for implementation paths                             │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                              │                                                  │
│                              │ REST API                                         │
│                              ▼                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │  INTELLIGENCE-BUILDER PLATFORM                                          │  │
│   │  • Workflow domain registered                                           │  │
│   │  • Entities: issue, pull_request, commit, file, test                    │  │
│   │  • Shared knowledge graph                                               │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Choices

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Primary Database** | PostgreSQL 15+ | Proven, existing infrastructure, pgvector support |
| **Vector Store** | pgvector | Native PostgreSQL, no separate infrastructure |
| **Cache** | Redis | Fast, proven, L2 cache for embeddings |
| **Graph Backend (Default)** | PostgreSQL CTEs | No extra infrastructure, sufficient for most cases |
| **Graph Backend (Optional)** | Memgraph | Native Cypher, complex traversals, high performance |
| **API Framework** | FastAPI | Async-first, OpenAPI generation, Pydantic |
| **Language** | Python 3.11+ | Async support, type hints, ecosystem |
| **Embedding Models** | sentence-transformers (MiniLM) | Fast, 384-dim, good quality |
| **LLM (Optional)** | Claude/OpenAI | Answer generation, entity extraction |

---

## Security Architecture

### Multi-Tenancy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       MULTI-TENANT DATA ISOLATION                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   API Request                                                                   │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ AUTHENTICATION                                                          │  │
│   │ • API key validation                                                    │  │
│   │ • JWT token validation                                                  │  │
│   │ • Extract tenant_id                                                     │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ TENANT CONTEXT                                                          │  │
│   │ • Inject tenant_id into all queries                                     │  │
│   │ • Row-level security enforced at database                               │  │
│   │ • Cache keys include tenant_id                                          │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │ DATABASE QUERIES                                                        │  │
│   │ • WHERE tenant_id = $current_tenant (automatic)                         │  │
│   │ • No cross-tenant data access possible                                  │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### API Security

| Control | Implementation |
|---------|----------------|
| Authentication | API keys + JWT |
| Authorization | Role-based (admin, write, read) |
| Rate Limiting | Per-tenant, per-endpoint |
| Input Validation | Pydantic models |
| SQL Injection | Parameterized queries only |
| Audit Logging | All mutations logged |

---

## Observability

### Metrics (Prometheus)

| Metric | Type | Description |
|--------|------|-------------|
| `ib_api_request_duration_seconds` | Histogram | API response time |
| `ib_api_requests_total` | Counter | Total API requests |
| `ib_pattern_matches_total` | Counter | Pattern matches by domain |
| `ib_graph_operations_total` | Counter | Graph operations by type |
| `ib_cache_hits_total` | Counter | Cache hits by layer |
| `ib_embedding_generation_seconds` | Histogram | Embedding generation time |

### Logging

- Structured JSON logs
- Correlation IDs for request tracing
- Log levels: DEBUG, INFO, WARN, ERROR
- Sensitive data redaction

### Health Checks

- `/health/live` - Kubernetes liveness
- `/health/ready` - Kubernetes readiness
- `/health/detailed` - Component-level health

---

## References

- [Project Goals](./PROJECT_GOALS.md)
- [Technical Design](./TECHNICAL_DESIGN.md)
- [Implementation Plan](./IMPLEMENTATION_PLAN.md)
