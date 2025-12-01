# Cloud Optimizer v2 - Strategic Design

**Version:** 2.1
**Date:** 2025-11-30
**Status:** Approved - Ready for Implementation

---

## 1. Design Philosophy

### 1.1 Core Principles

| Principle | Description | Implementation |
|-----------|-------------|----------------|
| **Simplicity** | Prefer simple, obvious solutions | Max 10K LOC, flat module structure |
| **Separation** | Clear boundaries between concerns | Layered architecture, interfaces |
| **Leverage** | Use IB platform, don't rebuild | SDK-first integration |
| **Type Safety** | Catch errors at compile time | 100% type hints, Pydantic models |
| **Testability** | Design for testing | Dependency injection, interfaces |

### 1.2 Anti-Patterns to Avoid

From legacy system lessons learned:

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| God services | 1000+ line service files | Max 300 lines per service |
| SQL in business logic | Injection risk, hard to test | Repository pattern |
| Implicit tenant context | Data leaks between tenants | Explicit tenant_id on all queries |
| Feature flags everywhere | Complex conditionals | Plugin architecture |
| Circular dependencies | Hard to understand, test | Strict layer boundaries |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLOUD OPTIMIZER v2                          │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Frontend  │  │   Mobile    │  │     CLI     │  │   Webhooks  │ │
│  │   (React)   │  │   (Future)  │  │   (Future)  │  │   (AWS MP)  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │                │        │
│  ┌──────┴────────────────┴────────────────┴────────────────┴──────┐ │
│  │                         API GATEWAY                             │ │
│  │              (FastAPI + JWT Auth + Rate Limiting)               │ │
│  └─────────────────────────────┬───────────────────────────────────┘ │
│                                │                                     │
│  ┌─────────────────────────────┴───────────────────────────────────┐ │
│  │                      APPLICATION LAYER                           │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │ │
│  │  │ Security │ │   Cost   │ │Compliance│ │ Tenant   │           │ │
│  │  │ Service  │ │ Service  │ │ Service  │ │ Service  │           │ │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │ │
│  └───────┼────────────┼────────────┼────────────┼──────────────────┘ │
│          │            │            │            │                    │
│  ┌───────┴────────────┴────────────┴────────────┴──────────────────┐ │
│  │                       DOMAIN LAYER                               │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │ │
│  │  │   Scanner    │  │    Domain    │  │  Marketplace │          │ │
│  │  │   Registry   │  │   Registry   │  │   Service    │          │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │ │
│  └─────────────────────────────┬───────────────────────────────────┘ │
│                                │                                     │
│  ┌─────────────────────────────┴───────────────────────────────────┐ │
│  │                    INFRASTRUCTURE LAYER                          │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │ │
│  │  │    IB    │ │   AWS    │ │   Cache  │ │ Database │           │ │
│  │  │   SDK    │ │  Client  │ │  (Redis) │ │  (PG)    │           │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INTELLIGENCE-BUILDER PLATFORM                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   GraphRAG  │  │   Pattern   │  │   Domain    │                 │
│  │   Engine    │  │   Detector  │  │   System    │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Responsibilities

| Layer | Responsibility | Key Components |
|-------|---------------|----------------|
| **API** | HTTP handling, auth, validation | Routers, schemas, middleware |
| **Application** | Business orchestration | Services (thin, <300 LOC each) |
| **Domain** | Business rules, entities | Models, domain services |
| **Infrastructure** | External systems | Repositories, clients, adapters |

### 2.3 Dependency Rules

```
API → Application → Domain → Infrastructure
         ↓
   (Domain Layer is the core - no outward dependencies)
```

**Strict Rules:**
1. API layer can only call Application layer
2. Application layer can call Domain and Infrastructure
3. Domain layer has NO external dependencies
4. Infrastructure layer implements interfaces defined in Domain

---

## 3. Component Design

### 3.1 Module Structure

```
src/cloud_optimizer/
├── api/                    # API Layer
│   ├── routers/           # FastAPI routers (1 per domain)
│   │   ├── security.py
│   │   ├── cost.py
│   │   ├── compliance.py
│   │   ├── dashboard.py
│   │   ├── tenant.py
│   │   └── marketplace.py
│   ├── schemas/           # Pydantic request/response models
│   ├── middleware/        # Auth, tenant context, rate limiting
│   └── dependencies.py    # FastAPI dependency injection
│
├── services/              # Application Layer
│   ├── security.py        # Security orchestration
│   ├── cost.py           # Cost analysis orchestration
│   ├── compliance.py     # Compliance orchestration
│   ├── tenant.py         # Tenant management
│   ├── marketplace.py    # AWS Marketplace integration
│   └── notification.py   # Alert/notification service
│
├── domain/               # Domain Layer
│   ├── models/          # Domain entities (Pydantic)
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── finding.py
│   │   └── recommendation.py
│   ├── interfaces/      # Abstract interfaces (Protocol classes)
│   │   ├── scanner.py
│   │   ├── repository.py
│   │   └── client.py
│   └── exceptions.py    # Domain-specific exceptions
│
├── infrastructure/      # Infrastructure Layer
│   ├── ib/             # Intelligence-Builder integration
│   │   ├── client.py   # IB SDK wrapper
│   │   └── adapter.py  # Domain adapter
│   ├── aws/            # AWS integrations
│   │   ├── scanners/   # AWS scanner implementations
│   │   ├── marketplace.py
│   │   └── client.py   # Boto3 wrapper
│   ├── db/             # Database
│   │   ├── repositories/  # Repository implementations
│   │   ├── models.py   # SQLAlchemy models
│   │   └── session.py  # Session management
│   └── cache/          # Redis caching
│
├── config.py           # Configuration (Pydantic Settings)
├── main.py            # FastAPI app factory
└── exceptions.py      # Global exception handlers
```

### 3.2 File Size Limits

| File Type | Max Lines | Rationale |
|-----------|-----------|-----------|
| Router | 200 | Thin, delegates to services |
| Service | 300 | Orchestration only, no business logic |
| Repository | 200 | Simple CRUD operations |
| Model | 100 | Data structures only |
| Schema | 150 | Request/response definitions |

---

## 4. Core Patterns

### 4.1 Tenant Context Pattern

**Problem:** Every operation must be scoped to a tenant for data isolation.

**Solution:** Inject tenant context via middleware, pass through all layers.

```python
# Domain model (immutable)
@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    tier: TenantTier
    settings: TenantSettings

# Middleware injects context
class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        token = await get_jwt_token(request)
        request.state.tenant = await self.tenant_service.get_context(token.tenant_id)
        return await call_next(request)

# Dependency for routes
def get_tenant(request: Request) -> TenantContext:
    return request.state.tenant

# Usage in router
@router.get("/findings")
async def list_findings(
    tenant: TenantContext = Depends(get_tenant),
    finding_service: FindingService = Depends()
):
    return await finding_service.list_findings(tenant)

# Service always receives tenant
class FindingService:
    async def list_findings(self, tenant: TenantContext) -> List[Finding]:
        return await self.repository.list_by_tenant(tenant.tenant_id)

# Repository enforces tenant filter
class FindingRepository:
    async def list_by_tenant(self, tenant_id: str) -> List[Finding]:
        query = select(FindingModel).where(FindingModel.tenant_id == tenant_id)
        return await self.session.execute(query)
```

### 4.2 Scanner Registry Pattern

**Problem:** Multiple AWS scanners with different capabilities need unified management.

**Solution:** Registry pattern with scanner interface.

```python
# Interface in domain layer
class ScannerProtocol(Protocol):
    def get_scanner_name(self) -> str: ...
    def get_supported_checks(self) -> List[str]: ...
    async def scan(self, tenant: TenantContext, config: ScanConfig) -> ScanResult: ...

# Registry for managing scanners
class ScannerRegistry:
    _scanners: Dict[str, ScannerProtocol] = {}

    @classmethod
    def register(cls, name: str, scanner: ScannerProtocol):
        cls._scanners[name] = scanner

    @classmethod
    def get(cls, name: str) -> ScannerProtocol:
        if name not in cls._scanners:
            raise ScannerNotFoundError(name)
        return cls._scanners[name]

    @classmethod
    def list_all(cls) -> List[str]:
        return list(cls._scanners.keys())

# Scanner implementation in infrastructure
class SecurityGroupScanner(ScannerProtocol):
    def __init__(self, aws_client: AWSClient, ib_client: IBClient):
        self.aws = aws_client
        self.ib = ib_client

    def get_scanner_name(self) -> str:
        return "security_groups"

    async def scan(self, tenant: TenantContext, config: ScanConfig) -> ScanResult:
        # 1. Scan AWS resources
        findings = await self.aws.describe_security_groups()

        # 2. Analyze with IB
        analysis = await self.ib.analyze(findings, tenant.tenant_id)

        # 3. Return unified result
        return ScanResult(findings=analysis.findings)

# Auto-registration at startup
def register_scanners():
    ScannerRegistry.register("security_groups", SecurityGroupScanner(...))
    ScannerRegistry.register("iam", IAMScanner(...))
    ScannerRegistry.register("cost", CostScanner(...))
```

### 4.3 Repository Pattern

**Problem:** Data access scattered, hard to test, SQL injection risk.

**Solution:** Repository interface with implementation in infrastructure.

```python
# Interface in domain layer
class TenantRepositoryProtocol(Protocol):
    async def get(self, tenant_id: str) -> Optional[Tenant]: ...
    async def create(self, tenant: TenantCreate) -> Tenant: ...
    async def update(self, tenant_id: str, data: TenantUpdate) -> Tenant: ...
    async def delete(self, tenant_id: str) -> None: ...

# Implementation in infrastructure
class PostgresTenantRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, tenant_id: str) -> Optional[Tenant]:
        result = await self.session.execute(
            select(TenantModel).where(TenantModel.tenant_id == tenant_id)
        )
        row = result.scalar_one_or_none()
        return Tenant.from_orm(row) if row else None

    async def create(self, tenant: TenantCreate) -> Tenant:
        model = TenantModel(**tenant.model_dump())
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return Tenant.from_orm(model)

# Dependency injection
def get_tenant_repository(session: AsyncSession = Depends(get_session)):
    return PostgresTenantRepository(session)
```

### 4.4 Service Pattern

**Problem:** Business logic spread across routers, hard to test and reuse.

**Solution:** Thin services that orchestrate domain logic and infrastructure.

```python
class SecurityService:
    """Orchestrates security scanning operations."""

    def __init__(
        self,
        scanner_registry: ScannerRegistry,
        finding_repository: FindingRepositoryProtocol,
        ib_client: IBClientProtocol,
    ):
        self.scanners = scanner_registry
        self.findings = finding_repository
        self.ib = ib_client

    async def run_scan(
        self,
        tenant: TenantContext,
        scan_type: str,
        config: Optional[ScanConfig] = None,
    ) -> ScanResult:
        """Run a security scan for a tenant."""
        # 1. Get scanner
        scanner = self.scanners.get(scan_type)

        # 2. Execute scan
        result = await scanner.scan(tenant, config or ScanConfig())

        # 3. Persist findings
        for finding in result.findings:
            await self.findings.create(tenant.tenant_id, finding)

        # 4. Notify IB for graph update
        await self.ib.persist_findings(tenant.tenant_id, result.findings)

        return result

    async def list_findings(
        self,
        tenant: TenantContext,
        filters: Optional[FindingFilters] = None,
    ) -> List[Finding]:
        """List findings for a tenant."""
        return await self.findings.list(tenant.tenant_id, filters)
```

---

## 5. Data Architecture

### 5.1 Database Design

**Principle:** Minimal local storage, IB is the source of truth for intelligence data.

```
Cloud Optimizer Database (PostgreSQL)
├── Tenant Management
│   ├── tenants
│   ├── tenant_settings
│   └── tenant_quotas
│
├── User Management
│   ├── users
│   ├── user_sessions
│   └── user_roles
│
├── AWS Marketplace
│   ├── marketplace_customers
│   ├── marketplace_subscriptions
│   └── usage_records
│
├── Trials
│   ├── trials
│   └── trial_usage
│
├── Audit
│   └── audit_logs
│
└── Cache (optional, prefer Redis)
    └── scan_cache

Intelligence-Builder Database (via SDK)
├── Entities (vulnerabilities, controls, etc.)
├── Relationships (mitigates, affects, etc.)
├── Embeddings (vector search)
└── Query cache
```

### 5.2 Schema Design

```sql
-- Tenants
CREATE TABLE tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    tier VARCHAR(50) NOT NULL DEFAULT 'free',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    email_verified BOOLEAN DEFAULT FALSE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Tenant Members (many-to-many)
CREATE TABLE tenant_members (
    tenant_id UUID REFERENCES tenants(tenant_id),
    user_id UUID REFERENCES users(user_id),
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    PRIMARY KEY (tenant_id, user_id)
);

-- Marketplace Customers
CREATE TABLE marketplace_customers (
    customer_id VARCHAR(255) PRIMARY KEY,  -- AWS Marketplace ID
    tenant_id UUID REFERENCES tenants(tenant_id),
    product_code VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    subscription_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage Records (for metering)
CREATE TABLE usage_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(255) REFERENCES marketplace_customers(customer_id),
    dimension VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    submitted BOOLEAN DEFAULT FALSE,
    submission_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Logs
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    user_id UUID REFERENCES users(user_id),
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_tenant_members_user ON tenant_members(user_id);
CREATE INDEX idx_marketplace_tenant ON marketplace_customers(tenant_id);
CREATE INDEX idx_usage_customer_time ON usage_records(customer_id, timestamp);
CREATE INDEX idx_audit_tenant_time ON audit_logs(tenant_id, created_at);
```

---

## 6. API Design

### 6.1 URL Structure

```yaml
Base: /api/v1

Authentication:
  POST /auth/login          # Login
  POST /auth/register       # Register
  POST /auth/refresh        # Refresh token
  POST /auth/logout         # Logout

Tenant Management:
  GET  /tenant              # Get current tenant
  PUT  /tenant              # Update tenant settings
  GET  /tenant/members      # List members
  POST /tenant/members      # Invite member

Security:
  POST /security/scan       # Run security scan
  GET  /security/findings   # List findings
  GET  /security/findings/{id}
  POST /security/findings/{id}/remediate

Cost:
  GET  /cost/analysis       # Get cost analysis
  GET  /cost/recommendations
  GET  /cost/forecast
  GET  /cost/anomalies

Compliance:
  GET  /compliance/status   # Overall status
  GET  /compliance/frameworks
  GET  /compliance/frameworks/{id}
  GET  /compliance/gaps

Dashboard:
  GET  /dashboard/overview
  GET  /dashboard/security
  GET  /dashboard/cost
  GET  /dashboard/compliance

Marketplace:
  POST /marketplace/register     # From AWS Marketplace
  POST /marketplace/webhook      # Subscription events
  GET  /marketplace/entitlement  # Check entitlement
  GET  /marketplace/usage        # Usage summary

Admin:
  GET  /admin/tenants       # List all tenants (super-admin)
  GET  /admin/metrics       # System metrics
```

### 6.2 Response Format

**Success Response:**
```json
{
    "data": { ... },
    "meta": {
        "request_id": "req_abc123",
        "timestamp": "2025-11-30T12:00:00Z"
    }
}
```

**List Response:**
```json
{
    "data": [ ... ],
    "meta": {
        "request_id": "req_abc123",
        "timestamp": "2025-11-30T12:00:00Z",
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total_items": 150,
            "total_pages": 8
        }
    }
}
```

**Error Response:**
```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input",
        "details": [
            {"field": "email", "message": "Invalid email format"}
        ]
    },
    "meta": {
        "request_id": "req_abc123",
        "timestamp": "2025-11-30T12:00:00Z"
    }
}
```

### 6.3 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Invalid request data |
| AUTHENTICATION_ERROR | 401 | Invalid or expired token |
| AUTHORIZATION_ERROR | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMIT_ERROR | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |
| SERVICE_UNAVAILABLE | 503 | IB or AWS unavailable |

---

## 7. Intelligence-Builder Integration

### 7.1 Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Cloud Optimizer                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    IB Integration Layer                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │  IBClient   │  │ IBAdapter   │  │ IBCache     │       │  │
│  │  │  (SDK)      │  │ (Domain)    │  │ (Redis)     │       │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │  │
│  └─────────┼────────────────┼────────────────┼───────────────┘  │
│            │                │                │                   │
└────────────┼────────────────┼────────────────┼───────────────────┘
             │                │                │
             ▼                │                │
┌────────────────────────────────────────────────────────────────┐
│                  Intelligence-Builder Platform                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  REST API   │  │  GraphRAG   │  │  Pattern    │            │
│  │  (FastAPI)  │  │  Engine     │  │  Detection  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└────────────────────────────────────────────────────────────────┘
```

### 7.2 IBClient Wrapper

```python
class IBClient:
    """Wrapper around IB SDK with tenant context and caching."""

    def __init__(self, config: IBConfig, cache: CacheProtocol):
        self._sdk = IntelligenceBuilderClient(
            ClientConfig(
                base_url=config.base_url,
                api_key=config.api_key,
                timeout=config.timeout,
                enable_circuit_breaker=True,
                enable_caching=False,  # We handle caching
            )
        )
        self._cache = cache

    async def query(
        self,
        tenant_id: str,
        query: str,
        domain: Optional[str] = None,
    ) -> QueryResult:
        """Execute a query with tenant context."""
        cache_key = f"query:{tenant_id}:{hash(query)}"

        # Check cache
        cached = await self._cache.get(cache_key)
        if cached:
            return QueryResult.parse_raw(cached)

        # Execute query
        result = await self._sdk.query(
            query=query,
            context={"tenant_id": tenant_id, "domain": domain}
        )

        # Cache result
        await self._cache.set(cache_key, result.json(), ttl=300)

        return result

    async def analyze_security(
        self,
        tenant_id: str,
        text: str,
    ) -> AnalysisResult:
        """Analyze text for security patterns."""
        return await self._sdk.detect_patterns(
            text=text,
            domain="security",
            context={"tenant_id": tenant_id}
        )

    async def persist_findings(
        self,
        tenant_id: str,
        findings: List[Finding],
    ) -> None:
        """Persist findings to IB knowledge graph."""
        entities = [finding.to_entity() for finding in findings]
        await self._sdk.create_entities(
            entities=entities,
            context={"tenant_id": tenant_id}
        )
```

### 7.3 Domain Adapter

```python
class CloudOptimizerDomainAdapter:
    """Adapts Cloud Optimizer domains to IB domain system."""

    DOMAIN_MAPPING = {
        "security": "security",
        "cost": "cost_optimization",
        "performance": "performance",
        "reliability": "reliability",
        "operations": "operational_excellence",
    }

    def __init__(self, ib_client: IBClient):
        self.ib = ib_client

    async def analyze(
        self,
        tenant_id: str,
        domain: str,
        content: str,
    ) -> DomainAnalysis:
        """Analyze content using IB domain system."""
        ib_domain = self.DOMAIN_MAPPING.get(domain, domain)

        result = await self.ib.query(
            tenant_id=tenant_id,
            query=f"Analyze this for {domain} issues: {content}",
            domain=ib_domain,
        )

        return DomainAnalysis(
            domain=domain,
            findings=result.entities,
            recommendations=result.recommendations,
            confidence=result.confidence,
        )
```

---

## 8. Security Architecture

### 8.1 Authentication Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │     │   API    │     │  Auth    │     │    DB    │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │  POST /login   │                │                │
     │───────────────>│                │                │
     │                │  verify_user   │                │
     │                │───────────────>│                │
     │                │                │  get_user      │
     │                │                │───────────────>│
     │                │                │<───────────────│
     │                │                │                │
     │                │  create_token  │                │
     │                │───────────────>│                │
     │                │<───────────────│                │
     │  JWT Token     │                │                │
     │<───────────────│                │                │
     │                │                │                │
     │  GET /data     │                │                │
     │  + Bearer JWT  │                │                │
     │───────────────>│                │                │
     │                │  verify_token  │                │
     │                │───────────────>│                │
     │                │<───────────────│                │
     │                │                │                │
     │                │  get_tenant    │                │
     │                │───────────────>│                │
     │                │<───────────────│                │
     │  Response      │                │                │
     │<───────────────│                │                │
```

### 8.2 Authorization Model

```python
# Role definitions
class Role(Enum):
    OWNER = "owner"       # Full access, can delete tenant
    ADMIN = "admin"       # Full access except delete tenant
    MEMBER = "member"     # Read/write findings, run scans
    VIEWER = "viewer"     # Read-only access

# Permission mapping
ROLE_PERMISSIONS = {
    Role.OWNER: ["*"],
    Role.ADMIN: [
        "tenant:read", "tenant:update",
        "users:*",
        "security:*",
        "cost:*",
        "compliance:*",
    ],
    Role.MEMBER: [
        "tenant:read",
        "security:read", "security:scan",
        "cost:read",
        "compliance:read",
    ],
    Role.VIEWER: [
        "tenant:read",
        "security:read",
        "cost:read",
        "compliance:read",
    ],
}

# Permission check
def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, tenant: TenantContext, user: User, **kwargs):
            if not has_permission(user.role, permission):
                raise AuthorizationError(f"Permission denied: {permission}")
            return await func(*args, tenant=tenant, user=user, **kwargs)
        return wrapper
    return decorator
```

### 8.3 Security Measures

| Measure | Implementation |
|---------|---------------|
| SQL Injection | Parameterized queries via SQLAlchemy |
| XSS | Response escaping, CSP headers |
| CSRF | SameSite cookies, CSRF tokens |
| Rate Limiting | Per-tenant/user limits via Redis |
| Secrets | AWS Secrets Manager, never in code |
| Audit | All state changes logged |
| Encryption | TLS 1.3, AES-256 at rest |

---

## 9. Performance Architecture

### 9.1 Caching Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                      Cache Layers                            │
├─────────────────────────────────────────────────────────────┤
│  L1: Request Cache (in-memory)                              │
│      - Per-request deduplication                            │
│      - TTL: Request lifetime                                │
├─────────────────────────────────────────────────────────────┤
│  L2: Application Cache (Redis)                              │
│      - IB query results (5 min TTL)                         │
│      - AWS scan results (15 min TTL)                        │
│      - Dashboard aggregates (1 min TTL)                     │
├─────────────────────────────────────────────────────────────┤
│  L3: Database Cache (PostgreSQL)                            │
│      - Query plan cache                                     │
│      - Connection pooling                                   │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Connection Pooling

```python
# Database connection pool
DATABASE_POOL_CONFIG = {
    "min_size": 5,
    "max_size": 20,
    "max_inactive_connection_lifetime": 300,
}

# Redis connection pool
REDIS_POOL_CONFIG = {
    "max_connections": 50,
}

# IB SDK connection pool (via httpx)
IB_CLIENT_CONFIG = {
    "max_keepalive_connections": 20,
    "max_connections": 100,
}
```

### 9.3 Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Health check | <50ms | p95 |
| List endpoints | <100ms | p95 |
| Detail endpoints | <200ms | p95 |
| Scan operations | <30s | p95 |
| Dashboard load | <500ms | p95 |
| IB queries | <300ms | p95 (cached) |

---

## 10. Deployment Architecture

### 10.1 Container Architecture

```yaml
services:
  api:
    build: .
    replicas: 2
    resources:
      limits:
        memory: 512M
        cpus: "0.5"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    depends_on:
      - db
      - redis
      - ib

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: cloud_optimizer
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  ib:
    image: intelligence-builder:latest
    environment:
      DATABASE_URL: postgresql://...
      JWT_SECRET: ${JWT_SECRET}
```

### 10.2 Environment Configuration

```yaml
Development:
  DEBUG: true
  LOG_LEVEL: DEBUG
  DATABASE_URL: postgresql://localhost:5432/cloud_optimizer_dev
  REDIS_URL: redis://localhost:6379/0
  IB_URL: http://localhost:8100

Staging:
  DEBUG: false
  LOG_LEVEL: INFO
  DATABASE_URL: ${DATABASE_URL}
  REDIS_URL: ${REDIS_URL}
  IB_URL: ${IB_URL}

Production:
  DEBUG: false
  LOG_LEVEL: WARNING
  DATABASE_URL: ${DATABASE_URL}  # From Secrets Manager
  REDIS_URL: ${REDIS_URL}
  IB_URL: ${IB_URL}
```

---

## 11. Testing Strategy

### 11.1 Test Pyramid

```
                    ┌───────────┐
                    │   E2E     │  5%
                    │   Tests   │
                ┌───┴───────────┴───┐
                │   Integration     │  25%
                │   Tests           │
            ┌───┴───────────────────┴───┐
            │       Unit Tests          │  70%
            │                           │
            └───────────────────────────┘
```

### 11.2 Test Categories

```python
# Unit tests (fast, isolated)
@pytest.mark.unit
async def test_finding_severity_calculation():
    finding = Finding(cvss_score=9.5)
    assert finding.severity == Severity.CRITICAL

# Integration tests (with real DB/Redis)
@pytest.mark.integration
async def test_create_tenant():
    repo = PostgresTenantRepository(session)
    tenant = await repo.create(TenantCreate(name="Test"))
    assert tenant.tenant_id is not None

# E2E tests (full API flow)
@pytest.mark.e2e
async def test_security_scan_flow():
    # Login
    response = await client.post("/auth/login", ...)
    token = response.json()["access_token"]

    # Start scan
    response = await client.post(
        "/security/scan",
        headers={"Authorization": f"Bearer {token}"},
        json={"scan_type": "security_groups"}
    )
    assert response.status_code == 200
```

### 11.3 Test Infrastructure

```yaml
# docker-compose.test.yml
services:
  test-db:
    image: postgres:15-alpine
    ports:
      - "5433:5432"
    tmpfs:
      - /var/lib/postgresql/data  # RAM for speed

  test-redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"

  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"
```

---

## 12. Migration Path

### 12.1 From Legacy

| Component | Migration Strategy |
|-----------|-------------------|
| User data | Export/import script |
| Tenant data | Export/import script |
| Findings | Re-scan (fresher data) |
| Audit logs | Archive, don't migrate |
| Documents | Migrate to IB |

### 12.2 Feature Flags

```python
class FeatureFlags(BaseSettings):
    """Control feature rollout."""

    enable_marketplace: bool = False
    enable_sso: bool = False
    enable_advanced_analytics: bool = False
    enable_notifications: bool = False

    # Percentage rollout
    cost_forecasting_rollout: int = 0  # 0-100
```

---

## 13. IB SDK Contract Specification

### 13.1 SDK Interface Definition

Before implementation, the following contract must be established with Intelligence-Builder:

```python
from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class IBClientProtocol(Protocol):
    """Contract for Intelligence-Builder SDK integration."""

    async def health_check(self) -> HealthStatus:
        """Check IB platform availability."""
        ...

    async def query(
        self,
        query: str,
        context: IBContext,
        options: Optional[QueryOptions] = None,
    ) -> QueryResult:
        """Execute a GraphRAG query."""
        ...

    async def detect_patterns(
        self,
        text: str,
        domain: str,
        context: IBContext,
    ) -> PatternDetectionResult:
        """Detect patterns in text using domain-specific rules."""
        ...

    async def create_entities(
        self,
        entities: List[Entity],
        context: IBContext,
    ) -> CreateEntitiesResult:
        """Persist entities to the knowledge graph."""
        ...

    async def create_relationships(
        self,
        relationships: List[Relationship],
        context: IBContext,
    ) -> CreateRelationshipsResult:
        """Create relationships between entities."""
        ...

    async def search_similar(
        self,
        query: str,
        context: IBContext,
        limit: int = 10,
    ) -> List[SimilarityResult]:
        """Vector similarity search."""
        ...

@dataclass
class IBContext:
    """Context passed to all IB operations."""
    tenant_id: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    domain: Optional[str] = None

@dataclass
class QueryOptions:
    """Options for query execution."""
    timeout_ms: int = 5000
    max_results: int = 100
    include_sources: bool = True
    confidence_threshold: float = 0.7

@dataclass
class QueryResult:
    """Result from a query operation."""
    answer: str
    confidence: float
    sources: List[str]
    entities: List[Entity]
    processing_time_ms: int

@dataclass
class HealthStatus:
    """IB platform health status."""
    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: int
    graph_backend: str
    pattern_engine: str
    last_check: str
```

### 13.2 Circuit Breaker Configuration

```python
@dataclass
class CircuitBreakerConfig:
    """Configuration for IB SDK circuit breaker."""

    # Failure threshold before opening circuit
    failure_threshold: int = 5

    # Time window for counting failures (seconds)
    failure_window: int = 60

    # Time to wait before testing recovery (seconds)
    recovery_timeout: int = 30

    # Success threshold to close circuit
    success_threshold: int = 3

    # Timeout for individual requests (ms)
    request_timeout: int = 5000

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery
```

### 13.3 Fallback Behavior

When IB is unavailable:

| Operation | Fallback Behavior |
|-----------|-------------------|
| `query()` | Return cached result if available, else error |
| `detect_patterns()` | Use local regex patterns (degraded accuracy) |
| `create_entities()` | Queue for retry, continue operation |
| `search_similar()` | Return empty results with warning |

```python
class IBFallbackHandler:
    """Handle IB unavailability gracefully."""

    async def handle_query_fallback(
        self,
        query: str,
        context: IBContext,
        cache: CacheProtocol,
    ) -> QueryResult:
        # Try cache first
        cached = await cache.get(f"query:{context.tenant_id}:{hash(query)}")
        if cached:
            return QueryResult.parse_raw(cached).with_warning("Cached result")

        # No fallback available
        raise IBUnavailableError(
            "IB platform unavailable, no cached result",
            retry_after=30,
        )

    async def handle_pattern_fallback(
        self,
        text: str,
        domain: str,
        local_patterns: PatternRegistry,
    ) -> PatternDetectionResult:
        # Use local pattern matching (reduced accuracy)
        matches = local_patterns.match(text, domain)
        return PatternDetectionResult(
            patterns=matches,
            confidence=0.6,  # Lower confidence for local matching
            warning="Using local pattern matching (IB unavailable)",
        )
```

---

## 14. Error Handling Matrix

### 14.1 Error Categories

| Category | HTTP Status | Retry | User Message |
|----------|-------------|-------|--------------|
| Validation | 400 | No | Show field errors |
| Authentication | 401 | No | Redirect to login |
| Authorization | 403 | No | Show permission error |
| Not Found | 404 | No | Show not found |
| Rate Limit | 429 | Yes (after delay) | Show retry message |
| IB Unavailable | 503 | Yes (exponential) | Show degraded mode |
| AWS Error | 502 | Yes (limited) | Show AWS status |
| Internal | 500 | No | Show generic error |

### 14.2 Error Handling by Scenario

#### AWS Credential Expiration During Scan

```python
async def handle_aws_credential_error(
    error: CredentialError,
    tenant: TenantContext,
    scan_id: str,
) -> None:
    """Handle expired AWS credentials mid-scan."""
    # 1. Mark scan as failed
    await scan_repository.update(
        scan_id,
        status=ScanStatus.FAILED,
        error_code="AWS_CREDENTIALS_EXPIRED",
        error_message="AWS credentials expired during scan",
    )

    # 2. Notify tenant owner
    await notification_service.send(
        tenant_id=tenant.tenant_id,
        template="aws_credentials_expired",
        data={"scan_id": scan_id},
    )

    # 3. Mark AWS account for re-authentication
    await aws_account_repository.update(
        tenant_id=tenant.tenant_id,
        status=AWSAccountStatus.NEEDS_REAUTH,
    )
```

#### IB Returns Malformed Data

```python
async def handle_ib_malformed_response(
    response: Any,
    operation: str,
    context: IBContext,
) -> None:
    """Handle malformed IB response."""
    # 1. Log for debugging
    logger.error(
        "IB returned malformed data",
        extra={
            "operation": operation,
            "tenant_id": context.tenant_id,
            "response_type": type(response).__name__,
            "response_sample": str(response)[:500],
        },
    )

    # 2. Increment error counter for circuit breaker
    circuit_breaker.record_failure()

    # 3. Return safe default or raise
    raise IBMalformedResponseError(
        f"IB returned invalid data for {operation}",
        operation=operation,
    )
```

#### Partial Scan Failure

```python
async def handle_partial_scan_failure(
    scan_id: str,
    completed_scanners: List[str],
    failed_scanners: Dict[str, str],  # scanner -> error
) -> ScanResult:
    """Handle scan where some scanners failed."""
    # 1. Store partial results
    await scan_repository.update(
        scan_id,
        status=ScanStatus.PARTIAL,
        completed_scanners=completed_scanners,
        failed_scanners=list(failed_scanners.keys()),
        errors=failed_scanners,
    )

    # 2. Return partial results with warnings
    return ScanResult(
        scan_id=scan_id,
        status="partial",
        findings=collected_findings,
        warnings=[
            f"Scanner '{name}' failed: {error}"
            for name, error in failed_scanners.items()
        ],
        completed_scanners=completed_scanners,
    )
```

#### Trial Expires During Active Scan

```python
async def handle_trial_expiry_during_scan(
    tenant: TenantContext,
    scan_id: str,
) -> None:
    """Handle trial expiration during active scan."""
    # 1. Allow scan to complete (grace period)
    logger.info(
        "Trial expired during scan, allowing completion",
        extra={"tenant_id": tenant.tenant_id, "scan_id": scan_id},
    )

    # 2. Mark results as final trial results
    await scan_repository.update(
        scan_id,
        metadata={"trial_expired_during_scan": True},
    )

    # 3. Block subsequent operations
    await tenant_service.suspend(
        tenant.tenant_id,
        reason="trial_expired",
        allow_read_access=True,  # Can view results but not run new scans
    )
```

### 14.3 Error Response Format

```python
@dataclass
class ErrorResponse:
    """Standardized error response."""
    code: str              # Machine-readable error code
    message: str           # Human-readable message
    details: List[ErrorDetail] = field(default_factory=list)
    retry_after: Optional[int] = None  # Seconds until retry
    documentation_url: Optional[str] = None

@dataclass
class ErrorDetail:
    """Field-level error detail."""
    field: Optional[str]
    code: str
    message: str

# Example usage
ErrorResponse(
    code="SCAN_PARTIAL_FAILURE",
    message="Scan completed with some errors",
    details=[
        ErrorDetail(
            field=None,
            code="SCANNER_FAILED",
            message="IAM scanner failed: Access denied",
        ),
    ],
    documentation_url="https://docs.example.com/errors/scan-partial-failure",
)
```

---

## 15. Enhanced Security Architecture

### 15.1 Multi-Factor Authentication (MFA)

#### TOTP Implementation

```python
@dataclass
class MFAConfig:
    """MFA configuration."""
    issuer: str = "Cloud Optimizer"
    algorithm: str = "SHA1"
    digits: int = 6
    period: int = 30
    backup_codes_count: int = 10

class MFAService:
    """Manage MFA for users."""

    async def enable_mfa(self, user_id: str) -> MFASetupResult:
        """Generate MFA secret and QR code."""
        # 1. Generate secret
        secret = pyotp.random_base32()

        # 2. Create TOTP URI
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=self.config.issuer,
        )

        # 3. Generate backup codes
        backup_codes = [
            secrets.token_hex(4).upper()
            for _ in range(self.config.backup_codes_count)
        ]

        # 4. Store encrypted (not active yet)
        await self.user_repository.store_mfa_pending(
            user_id,
            encrypted_secret=self.encrypt(secret),
            backup_codes_hash=[hash_code(c) for c in backup_codes],
        )

        return MFASetupResult(
            secret=secret,
            qr_code_uri=uri,
            backup_codes=backup_codes,
        )

    async def verify_and_activate(
        self, user_id: str, code: str
    ) -> bool:
        """Verify code and activate MFA."""
        pending = await self.user_repository.get_mfa_pending(user_id)
        secret = self.decrypt(pending.encrypted_secret)

        totp = pyotp.TOTP(secret)
        if totp.verify(code, valid_window=1):
            await self.user_repository.activate_mfa(user_id)
            return True
        return False

    async def verify_code(
        self, user_id: str, code: str
    ) -> MFAVerifyResult:
        """Verify MFA code during login."""
        user = await self.user_repository.get(user_id)

        # Try TOTP first
        totp = pyotp.TOTP(self.decrypt(user.mfa_secret))
        if totp.verify(code, valid_window=1):
            return MFAVerifyResult(success=True, method="totp")

        # Try backup code
        for i, hashed in enumerate(user.backup_codes_hash):
            if verify_hash(code.upper(), hashed):
                # Invalidate used backup code
                await self.user_repository.invalidate_backup_code(
                    user_id, index=i
                )
                return MFAVerifyResult(
                    success=True,
                    method="backup_code",
                    remaining_backup_codes=len(user.backup_codes_hash) - 1,
                )

        return MFAVerifyResult(success=False)
```

### 15.2 Session Management

```python
@dataclass
class SessionConfig:
    """Session configuration."""
    access_token_ttl: int = 900  # 15 minutes
    refresh_token_ttl: int = 604800  # 7 days
    max_concurrent_sessions: int = 5
    session_idle_timeout: int = 3600  # 1 hour

class SessionService:
    """Manage user sessions."""

    async def create_session(
        self,
        user: User,
        tenant: Tenant,
        ip_address: str,
        user_agent: str,
    ) -> SessionTokens:
        """Create new session with tokens."""
        # 1. Check concurrent session limit
        active_sessions = await self.session_repository.count_active(user.user_id)
        if active_sessions >= self.config.max_concurrent_sessions:
            # Revoke oldest session
            oldest = await self.session_repository.get_oldest(user.user_id)
            await self.revoke_session(oldest.session_id)

        # 2. Create session record
        session = await self.session_repository.create(
            user_id=user.user_id,
            tenant_id=tenant.tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(seconds=self.config.refresh_token_ttl),
        )

        # 3. Generate tokens
        access_token = self.create_access_token(user, tenant, session)
        refresh_token = self.create_refresh_token(session)

        # 4. Store refresh token hash
        await self.session_repository.update(
            session.session_id,
            refresh_token_hash=hash_token(refresh_token),
        )

        return SessionTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.config.access_token_ttl,
        )

    async def list_sessions(self, user_id: str) -> List[SessionInfo]:
        """List all active sessions for a user."""
        sessions = await self.session_repository.list_active(user_id)
        return [
            SessionInfo(
                session_id=s.session_id,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                created_at=s.created_at,
                last_activity_at=s.last_activity_at,
                is_current=s.session_id == current_session_id,
            )
            for s in sessions
        ]

    async def revoke_session(self, session_id: str) -> None:
        """Revoke a specific session."""
        await self.session_repository.revoke(session_id)
        # Add refresh token to blacklist
        await self.token_blacklist.add(session_id)

    async def revoke_all_sessions(
        self, user_id: str, except_current: bool = True
    ) -> int:
        """Revoke all sessions for a user."""
        sessions = await self.session_repository.list_active(user_id)
        revoked = 0
        for session in sessions:
            if except_current and session.session_id == current_session_id:
                continue
            await self.revoke_session(session.session_id)
            revoked += 1
        return revoked
```

### 15.3 API Key Management

```python
@dataclass
class APIKeyConfig:
    """API key configuration."""
    prefix: str = "co_"  # cloud_optimizer_
    key_length: int = 32
    default_ttl_days: int = 365
    max_keys_per_tenant: int = 10

class APIKeyService:
    """Manage API keys for programmatic access."""

    async def create_api_key(
        self,
        tenant: TenantContext,
        user: User,
        name: str,
        scopes: List[str],
        expires_in_days: Optional[int] = None,
    ) -> APIKeyCreateResult:
        """Create new API key."""
        # 1. Check limit
        existing = await self.api_key_repository.count(tenant.tenant_id)
        if existing >= self.config.max_keys_per_tenant:
            raise APIKeyLimitExceededError()

        # 2. Generate key
        key_id = str(uuid.uuid4())[:8]
        secret = secrets.token_urlsafe(self.config.key_length)
        full_key = f"{self.config.prefix}{key_id}_{secret}"

        # 3. Calculate expiry
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        elif self.config.default_ttl_days:
            expires_at = datetime.utcnow() + timedelta(
                days=self.config.default_ttl_days
            )

        # 4. Store (only hash of secret)
        await self.api_key_repository.create(
            key_id=key_id,
            tenant_id=tenant.tenant_id,
            created_by=user.user_id,
            name=name,
            scopes=scopes,
            secret_hash=hash_secret(secret),
            expires_at=expires_at,
        )

        # 5. Return full key (only time it's visible)
        return APIKeyCreateResult(
            key_id=key_id,
            api_key=full_key,  # Show once!
            name=name,
            scopes=scopes,
            expires_at=expires_at,
        )

    async def rotate_api_key(
        self, key_id: str, tenant: TenantContext
    ) -> APIKeyCreateResult:
        """Rotate an existing API key."""
        # 1. Get existing key
        existing = await self.api_key_repository.get(key_id, tenant.tenant_id)
        if not existing:
            raise APIKeyNotFoundError()

        # 2. Create new key with same settings
        new_key = await self.create_api_key(
            tenant=tenant,
            user=User(user_id=existing.created_by),
            name=f"{existing.name} (rotated)",
            scopes=existing.scopes,
            expires_in_days=None,  # Use default
        )

        # 3. Revoke old key (with grace period)
        await self.api_key_repository.schedule_revocation(
            key_id,
            revoke_at=datetime.utcnow() + timedelta(hours=24),
        )

        return new_key

    async def verify_api_key(self, api_key: str) -> APIKeyVerifyResult:
        """Verify API key and return context."""
        # 1. Parse key
        if not api_key.startswith(self.config.prefix):
            return APIKeyVerifyResult(valid=False)

        parts = api_key[len(self.config.prefix):].split("_", 1)
        if len(parts) != 2:
            return APIKeyVerifyResult(valid=False)

        key_id, secret = parts

        # 2. Lookup key
        key_record = await self.api_key_repository.get(key_id)
        if not key_record:
            return APIKeyVerifyResult(valid=False)

        # 3. Verify secret
        if not verify_hash(secret, key_record.secret_hash):
            return APIKeyVerifyResult(valid=False)

        # 4. Check expiry
        if key_record.expires_at and key_record.expires_at < datetime.utcnow():
            return APIKeyVerifyResult(valid=False, reason="expired")

        # 5. Check if revoked
        if key_record.revoked_at:
            return APIKeyVerifyResult(valid=False, reason="revoked")

        # 6. Update last used
        await self.api_key_repository.update_last_used(key_id)

        return APIKeyVerifyResult(
            valid=True,
            tenant_id=key_record.tenant_id,
            scopes=key_record.scopes,
        )
```

### 15.4 Secrets Rotation

```python
@dataclass
class SecretsRotationConfig:
    """Configuration for secrets rotation."""
    jwt_secret_rotation_days: int = 90
    db_password_rotation_days: int = 30
    api_key_warning_days: int = 30
    encryption_key_rotation_days: int = 180

class SecretsRotationService:
    """Manage automatic secrets rotation."""

    async def check_rotation_needed(self) -> List[RotationNeeded]:
        """Check which secrets need rotation."""
        needed = []

        # JWT signing key
        jwt_age = await self.get_secret_age("jwt_signing_key")
        if jwt_age > self.config.jwt_secret_rotation_days:
            needed.append(RotationNeeded(
                secret_type="jwt_signing_key",
                age_days=jwt_age,
                action="rotate",
            ))

        # Database password
        db_age = await self.get_secret_age("database_password")
        if db_age > self.config.db_password_rotation_days:
            needed.append(RotationNeeded(
                secret_type="database_password",
                age_days=db_age,
                action="rotate",
            ))

        return needed

    async def rotate_jwt_secret(self) -> None:
        """Rotate JWT signing key with overlap period."""
        # 1. Generate new key
        new_key = secrets.token_urlsafe(64)

        # 2. Store with version
        version = await self.secrets_manager.create_version(
            secret_id="jwt_signing_key",
            secret_value=new_key,
        )

        # 3. Update config to use both keys during transition
        await self.config_service.update(
            "jwt_signing_keys",
            [version, version - 1],  # Accept both for 24 hours
        )

        # 4. Schedule old key removal
        await self.scheduler.schedule(
            task="remove_old_jwt_key",
            run_at=datetime.utcnow() + timedelta(hours=24),
            args={"version": version - 1},
        )
```

---

## 16. Observability Architecture

### 16.1 Metrics Taxonomy

```yaml
# Prometheus metrics naming convention
# Format: cloud_optimizer_{component}_{metric}_{unit}

# Request Metrics
cloud_optimizer_http_requests_total:
  type: counter
  labels: [method, endpoint, status_code]
  description: Total HTTP requests

cloud_optimizer_http_request_duration_seconds:
  type: histogram
  labels: [method, endpoint]
  buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
  description: HTTP request duration

# Authentication Metrics
cloud_optimizer_auth_attempts_total:
  type: counter
  labels: [result, method]  # result: success/failure, method: password/mfa/api_key
  description: Authentication attempts

cloud_optimizer_active_sessions_total:
  type: gauge
  labels: [tenant_id]
  description: Active user sessions

# Business Metrics
cloud_optimizer_scans_total:
  type: counter
  labels: [tenant_id, scan_type, status]
  description: Security/cost scans executed

cloud_optimizer_findings_total:
  type: gauge
  labels: [tenant_id, severity]
  description: Active findings by severity

cloud_optimizer_savings_identified_dollars:
  type: gauge
  labels: [tenant_id]
  description: Identified cost savings

# IB Integration Metrics
cloud_optimizer_ib_requests_total:
  type: counter
  labels: [operation, status]
  description: IB SDK requests

cloud_optimizer_ib_request_duration_seconds:
  type: histogram
  labels: [operation]
  buckets: [0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
  description: IB request duration

cloud_optimizer_ib_circuit_breaker_state:
  type: gauge
  labels: []  # 0=closed, 1=open, 2=half_open
  description: IB circuit breaker state

# Database Metrics
cloud_optimizer_db_connections_active:
  type: gauge
  description: Active database connections

cloud_optimizer_db_query_duration_seconds:
  type: histogram
  labels: [query_type]  # select, insert, update, delete
  buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
  description: Database query duration

# Cache Metrics
cloud_optimizer_cache_hits_total:
  type: counter
  labels: [cache_type]  # redis, local
  description: Cache hits

cloud_optimizer_cache_misses_total:
  type: counter
  labels: [cache_type]
  description: Cache misses
```

### 16.2 Structured Logging

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Log format
{
    "timestamp": "2025-11-30T12:00:00.000Z",
    "level": "info",
    "event": "scan_completed",
    "request_id": "req_abc123",
    "tenant_id": "tenant_xyz",
    "user_id": "user_123",
    "scan_id": "scan_456",
    "scan_type": "security",
    "findings_count": 42,
    "duration_ms": 15234,
    "scanners_completed": ["iam", "security_groups", "s3"],
    "scanners_failed": []
}

# Correlation IDs
class CorrelationMiddleware:
    async def __call__(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            tenant_id=getattr(request.state, "tenant_id", None),
            user_id=getattr(request.state, "user_id", None),
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### 16.3 Distributed Tracing

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configure tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Trace spans
@tracer.start_as_current_span("security_scan")
async def run_security_scan(tenant: TenantContext, config: ScanConfig):
    span = trace.get_current_span()
    span.set_attribute("tenant_id", tenant.tenant_id)
    span.set_attribute("scan_type", "security")

    # Child span for AWS calls
    with tracer.start_as_current_span("aws_describe_security_groups") as aws_span:
        aws_span.set_attribute("aws_service", "ec2")
        security_groups = await aws_client.describe_security_groups()
        aws_span.set_attribute("sg_count", len(security_groups))

    # Child span for IB analysis
    with tracer.start_as_current_span("ib_pattern_detection") as ib_span:
        ib_span.set_attribute("domain", "security")
        patterns = await ib_client.detect_patterns(...)
        ib_span.set_attribute("patterns_found", len(patterns))

    return ScanResult(...)
```

### 16.4 Alert Rules

```yaml
# Prometheus alerting rules
groups:
  - name: cloud_optimizer_alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(cloud_optimizer_http_requests_total{status_code=~"5.."}[5m]))
          / sum(rate(cloud_optimizer_http_requests_total[5m])) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # Slow response times
      - alert: SlowResponseTime
        expr: |
          histogram_quantile(0.95,
            rate(cloud_optimizer_http_request_duration_seconds_bucket[5m])
          ) > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow API response times"
          description: "P95 latency is {{ $value }}s"

      # IB circuit breaker open
      - alert: IBCircuitBreakerOpen
        expr: cloud_optimizer_ib_circuit_breaker_state == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "IB circuit breaker is open"
          description: "Intelligence-Builder integration is failing"

      # Database connection pool exhaustion
      - alert: DatabaseConnectionPoolExhausted
        expr: |
          cloud_optimizer_db_connections_active
          / cloud_optimizer_db_connections_max > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool near exhaustion"

      # High authentication failure rate
      - alert: HighAuthFailureRate
        expr: |
          sum(rate(cloud_optimizer_auth_attempts_total{result="failure"}[5m]))
          / sum(rate(cloud_optimizer_auth_attempts_total[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High authentication failure rate"
          description: "May indicate brute force attempt"
```

### 16.5 Default Grafana Dashboards

```yaml
Dashboards:
  - name: "Cloud Optimizer Overview"
    panels:
      - Request Rate (requests/second)
      - Error Rate (%)
      - P95 Latency (ms)
      - Active Users (gauge)
      - Active Scans (gauge)

  - name: "Business Metrics"
    panels:
      - Scans by Type (stacked bar)
      - Findings by Severity (pie chart)
      - Savings Identified ($)
      - Top Tenants by Activity

  - name: "IB Integration Health"
    panels:
      - IB Request Rate
      - IB Latency (P50, P95, P99)
      - Circuit Breaker State
      - Cache Hit Rate

  - name: "Infrastructure"
    panels:
      - Database Connections
      - Query Latency by Type
      - Redis Memory Usage
      - Container CPU/Memory
```

---

## 17. Knowledge Base & Expert System Architecture

### 17.1 Conceptual Overview

The knowledge graph is not merely a data store - it is the **foundation of an expert system** that powers intelligent recommendations. The system's value comes from curated expert knowledge ingested from multiple authoritative sources.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXPERT SYSTEM ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    KNOWLEDGE INGESTION LAYER                         │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │  Technical  │ │Best Practice│ │  Security   │ │  Compliance │   │   │
│  │  │    Docs     │ │   Guides    │ │  Bulletins  │ │  Standards  │   │   │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘   │   │
│  │         │               │               │               │           │   │
│  │         ▼               ▼               ▼               ▼           │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              INGESTION PIPELINE (IB Platform)                │   │   │
│  │  │  • Document parsing • Entity extraction • Relationship mapping│   │   │
│  │  │  • Embedding generation • Deduplication • Version tracking   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    KNOWLEDGE GRAPH (IB Platform)                     │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │   Controls  │ │   Threats   │ │Vulnerabilities│ │ Remediations│   │   │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘   │   │
│  │         │               │               │               │           │   │
│  │         └───────────────┴───────────────┴───────────────┘           │   │
│  │                               │                                       │   │
│  │                    RELATIONSHIPS & EMBEDDINGS                        │   │
│  │         mitigates, exploits, affects, remediates, requires           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    REASONING ENGINE                                   │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │   Pattern   │ │   GraphRAG  │ │   Scoring   │ │Recommendation│   │   │
│  │  │  Matching   │ │   Queries   │ │   Engine    │ │  Generator   │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    RECOMMENDATIONS                                    │   │
│  │    "Apply S3 bucket encryption per CIS Benchmark 2.1.1"              │   │
│  │    "Patch CVE-2024-1234 - Critical RCE in OpenSSL"                   │   │
│  │    "Consider Reserved Instances for consistent EC2 usage"            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 17.2 Knowledge Sources

| Source Type | Description | Update Frequency | Priority |
|-------------|-------------|------------------|----------|
| **AWS Documentation** | Service guides, best practices, limits | Weekly | P0 |
| **AWS Security Bulletins** | Vulnerability announcements, patches | Real-time | P0 |
| **CIS Benchmarks** | Security configuration standards | Quarterly | P0 |
| **CVE Database** | Vulnerability definitions | Daily | P0 |
| **AWS Well-Architected** | Framework guidance, lens docs | Monthly | P1 |
| **NIST Guidelines** | Security frameworks (800-53, CSF) | Quarterly | P1 |
| **OWASP Resources** | Security best practices | Monthly | P1 |
| **Cloud Security Alliance** | Cloud control matrix | Quarterly | P2 |
| **Industry Whitepapers** | Vendor best practices | As published | P2 |

### 17.3 Ingestion Pipeline

```python
@dataclass
class KnowledgeSource:
    """Definition of a knowledge source for ingestion."""
    source_id: str
    source_type: SourceType  # DOCUMENTATION, BULLETIN, STANDARD, CVE
    name: str
    url: Optional[str]
    fetch_method: FetchMethod  # RSS, API, SCRAPE, UPLOAD
    update_schedule: str  # Cron expression
    parser: str  # Parser class name
    priority: int  # 0-2
    enabled: bool = True

class KnowledgeIngestionPipeline:
    """Orchestrates knowledge ingestion from multiple sources."""

    async def ingest_source(
        self,
        source: KnowledgeSource,
        incremental: bool = True,
    ) -> IngestionResult:
        """Ingest knowledge from a single source."""
        # 1. Fetch content
        content = await self.fetcher.fetch(source, since=last_ingestion)

        # 2. Parse and extract entities
        entities = await self.parser.parse(content, source.parser)

        # 3. Detect relationships
        relationships = await self.relationship_detector.detect(entities)

        # 4. Generate embeddings for semantic search
        embeddings = await self.embedding_service.generate(entities)

        # 5. Deduplicate against existing knowledge
        unique_entities = await self.deduplicator.dedupe(entities)

        # 6. Persist to knowledge graph
        await self.ib_client.create_entities(unique_entities)
        await self.ib_client.create_relationships(relationships)

        return IngestionResult(
            source_id=source.source_id,
            entities_created=len(unique_entities),
            relationships_created=len(relationships),
            timestamp=datetime.utcnow(),
        )

    async def run_scheduled_ingestion(self) -> None:
        """Run scheduled ingestion for all enabled sources."""
        for source in await self.source_repository.list_enabled():
            if self.scheduler.is_due(source.update_schedule):
                try:
                    result = await self.ingest_source(source)
                    await self.audit_log.log_ingestion(result)
                except IngestionError as e:
                    await self.alert_service.send_alert(
                        severity="warning",
                        message=f"Ingestion failed for {source.name}: {e}",
                    )
```

### 17.4 Entity Types in Knowledge Graph

```yaml
# Core entity types for the expert system
EntityTypes:

  # Security Knowledge
  Vulnerability:
    attributes: [cve_id, cvss_score, description, affected_systems, published_date]
    sources: [CVE Database, AWS Security Bulletins]

  Threat:
    attributes: [threat_id, name, description, tactics, techniques]
    sources: [MITRE ATT&CK, AWS Threat Intelligence]

  Control:
    attributes: [control_id, name, description, framework, implementation_guidance]
    sources: [CIS Benchmarks, NIST 800-53, AWS WAF]

  Remediation:
    attributes: [remediation_id, description, steps, complexity, automation_available]
    sources: [AWS Documentation, CIS Benchmarks, Internal Runbooks]

  # Cost Knowledge
  PricingModel:
    attributes: [service, region, pricing_type, rates, effective_date]
    sources: [AWS Price List API]

  SavingsOpportunity:
    attributes: [opportunity_type, description, typical_savings_percent, requirements]
    sources: [AWS Cost Optimization Hub, Best Practices]

  # Compliance Knowledge
  ComplianceRequirement:
    attributes: [requirement_id, framework, description, evidence_needed]
    sources: [SOC 2, HIPAA, PCI-DSS, GDPR]

  # Operational Knowledge
  BestPractice:
    attributes: [practice_id, category, description, rationale, implementation]
    sources: [AWS Well-Architected, Industry Guides]

# Relationship types
RelationshipTypes:
  - mitigates: Control → Vulnerability
  - exploits: Threat → Vulnerability
  - affects: Vulnerability → Service
  - remediates: Remediation → Vulnerability
  - implements: Control → ComplianceRequirement
  - recommends: BestPractice → Configuration
  - supersedes: Vulnerability → Vulnerability
  - related_to: Any → Any
```

### 17.5 Recommendation Generation

```python
class RecommendationEngine:
    """Generates recommendations from knowledge graph and scan results."""

    async def generate_security_recommendations(
        self,
        tenant: TenantContext,
        findings: List[Finding],
    ) -> List[Recommendation]:
        """Generate security recommendations based on findings and knowledge."""
        recommendations = []

        for finding in findings:
            # 1. Query knowledge graph for related vulnerabilities
            vulnerabilities = await self.ib_client.query(
                query=f"""
                MATCH (v:Vulnerability)-[:affects]->(s:Service)
                WHERE s.name = '{finding.service}'
                AND v.cvss_score >= 7.0
                RETURN v
                """,
                context=IBContext(tenant_id=tenant.tenant_id),
            )

            # 2. Find applicable controls
            controls = await self.ib_client.query(
                query=f"""
                MATCH (c:Control)-[:mitigates]->(v:Vulnerability)
                WHERE v.cve_id IN {[v.cve_id for v in vulnerabilities]}
                RETURN c, v
                """,
                context=IBContext(tenant_id=tenant.tenant_id),
            )

            # 3. Get remediation steps
            remediations = await self.ib_client.query(
                query=f"""
                MATCH (r:Remediation)-[:remediates]->(v:Vulnerability)
                WHERE v.cve_id IN {[v.cve_id for v in vulnerabilities]}
                RETURN r ORDER BY r.complexity ASC
                """,
                context=IBContext(tenant_id=tenant.tenant_id),
            )

            # 4. Build recommendation with full context
            recommendations.append(Recommendation(
                finding_id=finding.finding_id,
                title=f"Remediate {finding.title}",
                description=self._build_description(finding, vulnerabilities, controls),
                priority=self._calculate_priority(finding, vulnerabilities),
                steps=remediations[0].steps if remediations else [],
                references=[
                    Reference(type="CVE", id=v.cve_id) for v in vulnerabilities
                ] + [
                    Reference(type="Control", id=c.control_id) for c in controls
                ],
                estimated_effort=remediations[0].complexity if remediations else "unknown",
                automation_available=any(r.automation_available for r in remediations),
            ))

        return recommendations

    async def generate_cost_recommendations(
        self,
        tenant: TenantContext,
        usage_data: UsageData,
    ) -> List[Recommendation]:
        """Generate cost recommendations based on usage and best practices."""
        recommendations = []

        # Query knowledge graph for applicable savings opportunities
        opportunities = await self.ib_client.query(
            query="""
            MATCH (so:SavingsOpportunity)
            WHERE so.opportunity_type IN ['reserved_instance', 'savings_plan', 'rightsizing']
            RETURN so
            """,
            context=IBContext(tenant_id=tenant.tenant_id),
        )

        # Match opportunities to actual usage patterns
        for opportunity in opportunities:
            if self._opportunity_applies(opportunity, usage_data):
                estimated_savings = self._calculate_savings(opportunity, usage_data)
                recommendations.append(Recommendation(
                    title=opportunity.description,
                    priority=self._priority_from_savings(estimated_savings),
                    estimated_savings_monthly=estimated_savings,
                    steps=opportunity.implementation_steps,
                ))

        return recommendations
```

### 17.6 Continuous Learning & Updates

```yaml
# Scheduled jobs for knowledge maintenance
ScheduledJobs:

  # Real-time priority sources
  security_bulletins:
    schedule: "*/15 * * * *"  # Every 15 minutes
    sources: [AWS Security Bulletins, CVE RSS Feed]
    action: ingest_and_alert

  # Daily updates
  daily_knowledge_sync:
    schedule: "0 2 * * *"  # 2 AM daily
    sources: [AWS Documentation, Pricing API]
    action: incremental_sync

  # Weekly deep refresh
  weekly_full_sync:
    schedule: "0 3 * * 0"  # 3 AM Sunday
    sources: [ALL]
    action: full_sync_with_validation

  # Quarterly standards update
  compliance_standards:
    schedule: "0 4 1 */3 *"  # 4 AM, 1st of quarter
    sources: [CIS Benchmarks, NIST Updates]
    action: update_with_version_tracking

# Alert on critical knowledge updates
AlertRules:
  - name: critical_vulnerability
    condition: "new CVE with CVSS >= 9.0"
    action: immediate_notification

  - name: aws_security_bulletin
    condition: "new AWS security bulletin"
    action: queue_for_review

  - name: compliance_change
    condition: "CIS benchmark version change"
    action: schedule_gap_analysis
```

### 17.7 Knowledge Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Knowledge freshness | < 24h for critical sources | Time since last successful sync |
| Entity coverage | > 95% of AWS services | Services with control mappings |
| Relationship completeness | > 90% | Controls with vulnerability mappings |
| Embedding quality | > 0.85 cosine similarity | Semantic search accuracy |
| Ingestion success rate | > 99% | Successful syncs / total syncs |
| Deduplication accuracy | > 99% | Unique entities / total entities |

---

## 18. Decision Log

| Decision | Options Considered | Choice | Rationale |
|----------|-------------------|--------|-----------|
| Database | PostgreSQL, MySQL | PostgreSQL | pgvector support, IB compatibility |
| Cache | Redis, Memcached | Redis | Pub/sub, data structures |
| Auth | JWT, Sessions | JWT | Stateless, IB compatible |
| ORM | SQLAlchemy, Tortoise | SQLAlchemy | Mature, async support |
| API | FastAPI, Flask | FastAPI | Async, auto-docs, Pydantic |
| Frontend | React, Vue, Svelte | React | Team expertise, ecosystem |

---

## 14. Open Questions

| Question | Options | Decision Needed By |
|----------|---------|-------------------|
| SSO provider priority? | Okta, Auth0, Azure AD | Phase 4 start |
| Multi-region strategy? | Single, Multi-region | Production deployment |
| Backup strategy? | RDS snapshots, custom | Production deployment |
| CDN for frontend? | CloudFront, Cloudflare | Phase 3 start |

---

## 15. Next Steps

1. **Review this design** with stakeholders
2. **Approve requirements** in REQUIREMENTS_V2.md
3. **Create implementation plan** with detailed tasks
4. **Set up project structure** according to module design
5. **Begin Phase 1** implementation

---

## Appendix A: Technology Stack Summary

| Layer | Technology | Version |
|-------|-----------|---------|
| API Framework | FastAPI | 0.104+ |
| Validation | Pydantic | 2.5+ |
| Database | PostgreSQL | 15+ |
| ORM | SQLAlchemy | 2.0+ |
| Cache | Redis | 7+ |
| HTTP Client | httpx | 0.25+ |
| Testing | pytest | 8.0+ |
| Frontend | React | 18+ |
| Build | Vite | 5+ |
| CSS | Tailwind | 3+ |

## Appendix B: File Templates

See `/templates/` directory for:
- Router template
- Service template
- Repository template
- Test template
- Schema template
