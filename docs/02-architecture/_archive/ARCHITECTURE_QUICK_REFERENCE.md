# Cloud Optimizer - Architecture Quick Reference

**Purpose**: Quick lookup for key architecture decisions and patterns
**Audience**: New developers and architects
**Reference**: Detailed info in `LEGACY_ARCHITECTURE_SUMMARY.md`

---

## Core System Architecture

### Layers (Top to Bottom)
1. **User/API Layer** - FastAPI REST API (234 endpoints)
2. **Auth Layer** - JWT + RBAC middleware  
3. **Contract Layer** - Database contracts (100% type-safe)
4. **Data Layer** - PostgreSQL ag_catalog schema + Redis cache

### Key Components
- **API**: FastAPI with OpenAPI/Swagger documentation
- **Database**: PostgreSQL with ag_catalog schema
- **Cache**: Redis for sessions, queries, rate limiting
- **Knowledge Graph**: GraphRAG (PostgreSQL CTE or Memgraph)
- **Integration**: Smart Scaffold (optional, feature-flagged)

---

## Authentication & Authorization

### Strategy
- **Auth**: JWT with access + refresh tokens
- **Hashing**: bcrypt for passwords
- **RBAC**: Role-based with hierarchical permissions
- **Audit**: Complete audit logging of all access decisions
- **Session**: Redis-based session storage

### Database Tables
```
users → roles ← role_permissions ← permissions
  ↓
user_roles
  ↓
audit_log
```

### Security Features
- Account lockout after failed attempts
- Token blacklisting for logout
- Temporary role assignments (expiration support)
- Comprehensive audit trail

---

## Database Architecture

### Core Principle
**All database operations through contracts - never direct SQL**

### Schema
- **Primary**: ag_catalog (from Apache AGE)
- **Tables**: 67+ with 100% contract coverage
- **No Hardcoding**: All schema references abstracted

### Contract Pattern
```python
from src.contracts.organizations_contract import organizations_contract

# Create
org = await organizations_contract.create_organization(conn, name="...", ...)

# Read
org = await organizations_contract.get_organization_by_name(conn, "...")

# Update
await organizations_contract.update_record(conn, id, **kwargs)

# Delete
await organizations_contract.delete_record(conn, id)

# List
items = await organizations_contract.list_records(conn, limit=10, offset=0)

# Count
count = await organizations_contract.count_records(conn, filters)
```

### Security
- **SQL Injection Prevention**: Eliminated through contracts
- **Parameter Binding**: All queries parameterized
- **Type Safety**: 100% type coverage
- **Validation**: Built-in validation framework

---

## API Architecture

### Structure
- **Base URL**: `/api/v1/`
- **Format**: JSON request/response
- **Docs**: OpenAPI/Swagger at `/docs`
- **Endpoints**: 234 protected endpoints

### Response Format
```json
{
  "status": "success|error",
  "data": { /* payload */ },
  "error": null,
  "timestamp": "ISO8601",
  "request_id": "uuid"
}
```

### Security
- JWT authentication required
- Rate limiting on all endpoints
- Pydantic input validation
- Security headers (Content-Type, Frame-Options, XSS-Protection, HSTS)
- CORS properly configured

---

## Multi-Tenancy

### Model
- **Type**: Single database with row-level isolation
- **Isolation**: Tenant ID in JWT + database RLS policies
- **Cost**: Optimal (single database instance)
- **Scalability**: Easy horizontal scaling

### Implementation
```python
# From JWT token
current_tenant_id = request.state.user["tenant_id"]

# Set database context
await conn.execute("SET app.current_tenant_id = $1", current_tenant_id)

# Query automatically filtered by RLS policy
results = await conn.fetch("SELECT * FROM ag_catalog.assessments")
```

---

## Smart Scaffold Integration

### Design
- **Optional**: Feature-flagged integration
- **Type**: API client with circuit breaker
- **Graceful Degradation**: Continues without Smart Scaffold
- **Async**: Asynchronous collaboration workflows

### Usage
```python
if get_feature_flag("smart_scaffold_integration", default=False):
    async with SmartScaffoldAPIClient() as client:
        result = await client.create_session(...)
else:
    # Continue without Smart Scaffold
    result = create_local_session(...)
```

### Three-Layer Reality System
1. **Build-Time**: Contract compilation and validation
2. **Deploy-Time**: Schema compatibility validation
3. **Runtime**: Continuous drift detection and monitoring

---

## Performance Optimization

### Caching Layers
1. **Redis**: Sessions, query results, permissions
2. **Application**: In-memory TTL cache for config
3. **Database**: Strategic indexes on critical paths

### Performance Targets
```
API Response Times:
  - Health check: <10ms
  - Simple auth: <100ms
  - Complex query: <500ms
  - GraphRAG query: <1000ms

Database:
  - Index lookup: <10ms
  - Simple query: <50ms
  - Complex join: <200ms
```

### Cache Invalidation
- Time-based (TTL)
- Event-based (on changes)
- Manual (admin clear)

---

## AWS Marketplace Integration

### Status
Framework designed, awaiting implementation

### Key Requirements
1. Trial management (14-day default)
2. Customer registration (AWS customer ID capture)
3. Usage metering (API calls, documents, assessments)
4. Subscription handling (starter, pro, enterprise)
5. Feature tiering (different features per tier)

### Trial Flow
```
Customer registers from AWS Marketplace
  ↓
System captures AWS customer ID
  ↓
Create trial account (14-day)
  ↓
Full access during trial
  ↓
Trial expiration triggers conversion
  ↓
Subscription transition
```

### Pricing Tiers
```
Trial: 10K API calls, 100 docs, community support
Starter: 50K API calls, 1K docs, email support
Pro: 500K API calls, 10K docs, phone support
Enterprise: Unlimited, dedicated support
```

---

## GraphRAG Knowledge Graph

### Backends
- **Default**: PostgreSQL CTE (Common Table Expressions)
- **Optional**: Memgraph (native graph database)

### Core Operations
```python
# Query the knowledge graph
response = await client.query({
    "query": "What are AWS S3 security best practices?",
    "user_id": "user-123"
})

# Returns structured answer
{
    "answer": "...",
    "confidence": 0.95,
    "sources": ["doc1", "doc2"],
    "entities": ["S3", "Security"],
    "processing_time_ms": 250
}
```

### Knowledge Organization
- **Entities**: Resources, vulnerabilities, controls, practices
- **Relationships**: Configuration, violation, impact, mitigation
- **Documents**: Technical docs, guidelines, frameworks, best practices

---

## Testing Architecture

### Coverage Targets
```
Critical Paths (100%):
  - Authentication/authorization
  - Database contracts
  - API endpoints
  - Error handling

Core Features (80%):
  - Business logic
  - Integration points
  - Data validation

Utilities (60%):
  - Helpers
  - Configuration
```

### Test Levels
1. **Unit Tests**: <1s per test, mocked dependencies
2. **Integration Tests**: 30-60s execution, real services
3. **E2E Tests**: 5-10 min execution, complete workflows

### Quality Gates
- Pre-commit: Syntax, type checking, linting, security
- CI/CD: Tests pass, 80%+ coverage, no vulnerabilities

---

## Deployment

### Docker Services
- API (FastAPI on port 8000)
- PostgreSQL (port 5432)
- Redis (port 6379)
- Ollama (port 11434, optional)
- Grafana (monitoring dashboards)
- Prometheus (metrics collection)

### Configuration
```yaml
Production:
  - TLS/SSL encryption
  - AWS Secrets Manager
  - MFA required
  - Backups + disaster recovery
  - Load balancing

Development:
  - Docker Compose local setup
  - Hot reload enabled
  - Sample test data
  - Local Ollama
```

### CI/CD Pipeline
- Automated testing on PR
- Pre-commit validation
- Quality gates
- Container building/pushing
- Performance benchmarking

---

## Critical Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Schema** | ag_catalog | Clear separation, historical integration, graph support |
| **DB Ops** | Contracts only | Eliminates SQL injection, type safety, consistency |
| **Multi-tenant** | Row-level + tenant ID | Cost-effective, strong isolation, scalable |
| **Integration** | Optional + feature-flagged | Cloud Optimizer autonomous, graceful degradation |
| **Auth** | JWT + refresh tokens | Stateless, scalable, supports mobile apps |
| **Cache** | Redis + in-memory + indexes | Multi-layer optimization, TTL invalidation |
| **API** | FastAPI REST | Type-safe, auto-docs, async-native, performance |

---

## Common Code Patterns

### Database Operation
```python
async def update_organization(conn, org_id: UUID, **updates):
    return await organizations_contract.update_record(conn, org_id, **updates)
```

### API Endpoint
```python
@router.post("/assessments")
async def create_assessment(
    request: AssessmentCreateRequest,
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    org_id = current_user["organization_id"]
    return await assessment_service.create(request, org_id)
```

### Tenant-Safe Query
```python
@router.get("/assessments")
async def list_assessments(
    current_user: Dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
) -> Dict:
    org_id = current_user["organization_id"]
    items = await assessments_contract.list_records(
        conn, 
        limit=limit, 
        offset=offset,
        organization_id=org_id  # Automatic tenant filtering
    )
    return {"data": items}
```

### Error Handling
```python
try:
    result = await operation()
    return {"status": "success", "data": result}
except ValidationError as e:
    return {"status": "error", "error": {"code": "VALIDATION_ERROR", "details": e.details}}
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    return {"status": "error", "error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}
```

---

## Performance Checklist

- [ ] Database indexes on frequently queried columns
- [ ] Query caching with Redis TTL
- [ ] Pagination on list endpoints
- [ ] Connection pooling configured
- [ ] Compression enabled on responses
- [ ] CDN configured if needed
- [ ] Monitoring dashboards set up
- [ ] Performance SLAs established
- [ ] Load testing completed
- [ ] Alert thresholds configured

---

## Security Checklist

- [ ] All authentication mocks removed
- [ ] Passwords hashed with bcrypt
- [ ] JWT tokens with expiration
- [ ] Token blacklisting on logout
- [ ] RBAC properly enforced
- [ ] Audit logging enabled
- [ ] SQL injection prevention via contracts
- [ ] Input validation on all endpoints
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] TLS/SSL enforced in production

---

## References

**Detailed Documentation**
- Full architecture: `LEGACY_ARCHITECTURE_SUMMARY.md`
- Database contracts: `docs/02-architecture/contracts/`
- Security design: `docs/02-architecture/security/`
- API endpoints: `docs/api/openapi.json`
- Database truth: `DATABASE_TRUTH.md`

**Key Files**
- Auth implementation: `src/auth_abstraction/`
- Contract system: `src/contracts/`
- API routers: `src/api/routers/`
- Models/schemas: `src/models/`

