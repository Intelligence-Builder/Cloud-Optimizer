# Cloud Optimizer - Legacy Architecture & Design Summary

**Compiled From**: Legacy Cloud_Optimizer Documentation (v1/v2)
**Purpose**: Inform new system design (Cloud Optimizer v2 Clean-Slate Rebuild)
**Date**: 2025-11-30

---

## Executive Overview

Cloud Optimizer is an **enterprise-grade cloud security, compliance, and cost optimization platform** designed as a multi-tenant, production-ready system. The legacy system achieved significant architectural maturity before being rebuilt as a clean-slate system in 2025-07-17.

### Key Achievement Metrics
- **Database Coverage**: 100% contract coverage across 67+ tables
- **Authentication Security**: Production-ready JWT + RBAC with audit trails
- **Type Safety**: Complete elimination of SQL injection through database contracts
- **API Stability**: 234 protected endpoints with comprehensive security
- **AWS Integration**: AWS Marketplace integration readiness framework
- **Testing Target**: 80%+ test coverage required for production

---

## 1. SYSTEM ARCHITECTURE

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   CLOUD OPTIMIZER PLATFORM                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  User Layer  │  │  API Layer   │  │  Smart Scaffold  │  │
│  │              │  │  (FastAPI)   │  │  Integration     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                  │
│                    ┌──────────────┐                          │
│                    │  Auth Layer  │                          │
│                    │  (JWT/RBAC)  │                          │
│                    └──────────────┘                          │
│                            │                                  │
│    ┌───────────────────────┼───────────────────────┐         │
│    ▼                       ▼                       ▼         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Database Contract Layer                     │    │
│  │  • Type-safe operations                            │    │
│  │  • Schema abstraction (ag_catalog)                 │    │
│  │  • Validation framework                            │    │
│  └─────────────────────────────────────────────────────┘    │
│         │                       │              │             │
│         ▼                       ▼              ▼             │
│    ┌──────────┐          ┌───────────┐   ┌──────────┐      │
│    │PostgreSQL│          │ GraphRAG  │   │  Redis   │      │
│    │Database  │          │  Knowledge│   │  Cache   │      │
│    │(ag_catalog)         │  Graph    │   │          │      │
│    └──────────┘          └───────────┘   └──────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Core Components

#### **Authentication & Authorization Layer**
- **JWT-based Authentication**: Multi-provider support (OAuth2, SAML)
- **RBAC System**: Role-based access control with hierarchical permissions
- **Multi-tenant Isolation**: Strict tenant boundary enforcement
- **Audit Logging**: Comprehensive audit trail for all access decisions
- **API Key Management**: Service-to-service authentication
- **Status**: Production-ready with comprehensive security implementation

#### **API Layer (FastAPI)**
- **RESTful Architecture**: Standard REST patterns with proper HTTP methods
- **234 Endpoints**: Comprehensive endpoint coverage
- **OpenAPI Documentation**: Full Swagger/OpenAPI specification
- **Rate Limiting**: Endpoint-level rate limit protection
- **CORS Support**: Proper cross-origin resource sharing
- **Security Headers**: Standard security headers on all responses
- **Health Checks**: Comprehensive system health endpoints
- **Versioning**: API versioning for backward compatibility

#### **Database Contract System**
- **67+ Tables**: Complete type-safe coverage
- **Zero Hardcoded Schemas**: All references through contract abstraction
- **SQL Injection Prevention**: Eliminated through parameterized queries
- **Type Safety**: 100% type coverage for all database operations
- **Built-in Validation**: Comprehensive validation framework
- **Performance Optimization**: Optimized query patterns

#### **Data Layer (PostgreSQL)**
- **Schema**: ag_catalog (from Apache AGE, now primary schema)
- **Multi-tenancy**: Tenant isolation at database level
- **Connection Pooling**: Optimized connection management
- **Indexes**: Performance indexes on critical paths
- **Transactions**: ACID compliance for data integrity

#### **Caching Layer (Redis)**
- **Session Management**: User session storage
- **Query Caching**: Frequent query result caching
- **Rate Limiting**: Rate limit tracking
- **Task Queue**: Background job processing

#### **Smart Scaffold Integration (Optional)**
- **API Client**: HTTP client with circuit breaker pattern
- **Feature Flags**: Runtime control of collaboration features
- **Graceful Degradation**: Continues without Smart Scaffold if unavailable
- **Async Integration**: Asynchronous collaboration workflows

#### **GraphRAG Knowledge Graph**
- **PostgreSQL CTE Backend**: Default implementation using SQL CTEs
- **Memgraph Optional**: Alternative graph backend option
- **Q&A Engine**: Intelligent question-answering system
- **Knowledge Organization**: Structured knowledge representation
- **Query Interface**: GraphQL-like query capabilities

---

## 2. AUTHENTICATION & AUTHORIZATION ARCHITECTURE

### 2.1 Production Authentication Design

**Status**: Production-ready with comprehensive security

#### Authentication Flow
```
User Login
   ↓
Username/Password Validation (bcrypt)
   ↓
Account Status Check (locked, inactive, etc.)
   ↓
JWT Token Generation (Access + Refresh)
   ↓
Last Login Update
   ↓
Audit Logging
   ↓
Return Tokens
```

#### Database Schema for Authentication
```sql
-- Users table with secure authentication
ag_catalog.users (
    id UUID,
    username VARCHAR(255),
    email VARCHAR(255),
    password_hash VARCHAR(255),  -- bcrypt/argon2
    is_active BOOLEAN,
    is_verified BOOLEAN,
    last_login TIMESTAMP,
    failed_login_attempts INTEGER,
    locked_until TIMESTAMP
)

-- Roles with hierarchical permissions
ag_catalog.roles (
    id UUID,
    name VARCHAR(100),
    description TEXT,
    level INTEGER,  -- Role hierarchy
    is_system BOOLEAN
)

-- User-Role assignments with audit trail
ag_catalog.user_roles (
    id UUID,
    user_id UUID,
    role_id UUID,
    assigned_by UUID,
    assigned_at TIMESTAMP,
    expires_at TIMESTAMP,  -- Temporary role assignments
    is_active BOOLEAN
)

-- Granular permissions system
ag_catalog.permissions (
    id UUID,
    name VARCHAR(100),
    resource VARCHAR(100),
    action VARCHAR(50),
    description TEXT
)

-- Role-Permission assignments
ag_catalog.role_permissions (
    id UUID,
    role_id UUID,
    permission_id UUID
)

-- Comprehensive audit log
ag_catalog.audit_log (
    id UUID,
    user_id UUID,
    session_id VARCHAR(255),
    action VARCHAR(100),
    resource VARCHAR(100),
    resource_id UUID,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN,
    error_message TEXT,
    request_data JSONB,
    response_data JSONB,
    timestamp TIMESTAMP
)

-- JWT token blacklist for logout
ag_catalog.token_blacklist (
    id UUID,
    token_jti VARCHAR(255),
    user_id UUID,
    blacklisted_at TIMESTAMP,
    expires_at TIMESTAMP
)
```

### 2.2 Authorization & RBAC

#### Permission Model
- **Resource-Based**: Permissions organized by resource type
- **Action-Based**: Actions like read, write, delete
- **Conditional**: Support for JSONB-based conditional permissions
- **Inherited**: Permission inheritance through role hierarchy
- **Cached**: Redis-based permission caching with TTL

#### RBAC Flow
```
User Request
   ↓
Extract User Token
   ↓
Validate Token & Get User Info
   ↓
Extract Resource & Action from Request
   ↓
Check Permission Cache (Redis)
   ↓
If Cache Miss: Query Database
   ↓
Perform RBAC Check via Role Hierarchy
   ↓
Log Authorization Decision
   ↓
Cache Result (with TTL)
   ↓
Grant/Deny Access
```

### 2.3 Security Features

**Critical Security Achievements**:
- All mock authentication implementations eliminated
- Real password hashing (bcrypt/argon2)
- JWT tokens with proper expiration and blacklisting
- Complete audit logging for all access decisions
- Rate limiting on authentication endpoints
- Account lockout after failed attempts
- Temporary role assignments with expiration

---

## 3. DATABASE ARCHITECTURE

### 3.1 Core Design Principles

- **100% Contract Coverage**: All operations through type-safe contracts
- **Schema Abstraction**: No hardcoded schema names
- **Type Safety**: Complete type hints for all operations
- **Validation Framework**: Built-in validation for all database changes
- **Multi-tenancy**: Proper tenant isolation at database level
- **Performance**: Optimized queries with connection pooling

### 3.2 Database Contracts System

#### Contract Architecture
```python
class BaseDatabaseContract:
    """Base class for all database contracts"""

    async def create_record(self, conn, **kwargs) -> Dict
    async def get_record_by_id(self, conn, record_id) -> Optional[Dict]
    async def update_record(self, conn, record_id, **kwargs) -> Optional[Dict]
    async def delete_record(self, conn, record_id) -> bool
    async def list_records(self, conn, limit=100, offset=0, **filters) -> List[Dict]
    async def count_records(self, conn, **filters) -> int
```

#### Implemented Contracts (67+ tables)
1. **Organizations** - Organization management and hierarchy
2. **Settings** - Configuration and key-value storage
3. **Audit Logs** - System activity tracking
4. **Permissions** - Access control management
5. **Roles** - Role definitions with inheritance
6. **Users** - User management
7. **API Keys** - Service authentication
8. **Assessment** - Cost assessments
9. **Recommendations** - Optimization recommendations
10. Plus 57+ additional domain-specific contracts

#### Contract Usage Pattern
```python
# All database operations through contracts
from src.contracts.organizations_contract import organizations_contract

# Create
org = await organizations_contract.create_organization(
    conn,
    name="Acme Corp",
    domain="acme.com",
    settings={"timezone": "UTC"}
)

# Read
org = await organizations_contract.get_organization_by_name(conn, "Acme Corp")

# Update
updated = await organizations_contract.update_record(
    conn,
    org["id"],
    settings={"timezone": "EST"}
)

# Delete
deleted = await organizations_contract.delete_record(conn, org["id"])
```

### 3.3 Schema Organization

**Primary Schema**: ag_catalog
- Historical from Apache AGE integration
- Contains all business tables
- Proper indexing on critical paths
- ACID compliance enforced

**Key Tables by Domain**:
```yaml
Authentication & Authorization:
  - users
  - roles
  - user_roles
  - permissions
  - role_permissions
  - api_keys
  - audit_log
  - token_blacklist

Core Business:
  - organizations
  - assessments
  - recommendations
  - documents
  - settings

Optional Smart Scaffold:
  - smart_scaffold_sessions
  - smart_scaffold_approval_requests
  - smart_scaffold_quality_feedback
```

### 3.4 Database Security Features

- **No SQL Injection**: Eliminated through contract system
- **Parameter Binding**: All queries use parameterized statements
- **Type Checking**: Complete type validation
- **Access Control**: RBAC enforced at database level
- **Audit Trail**: Complete audit logging
- **Encryption**: Password hashing with bcrypt
- **Token Security**: JWT with proper expiration and blacklisting

---

## 4. API ARCHITECTURE

### 4.1 API Structure

**Base URL**: `/api/v1/`
**Documentation**: OpenAPI/Swagger at `/docs`
**Format**: JSON request/response

#### Endpoint Categories

```yaml
Authentication:
  POST /auth/login              # User login
  POST /auth/logout             # User logout
  POST /auth/refresh            # Token refresh
  POST /auth/register           # User registration
  GET  /auth/me                 # Current user info
  POST /auth/password-reset     # Password reset

Authorization & RBAC:
  GET  /admin/users             # List users
  POST /admin/users             # Create user
  GET  /admin/users/{id}        # Get user
  PUT  /admin/users/{id}        # Update user
  DELETE /admin/users/{id}      # Delete user
  POST /admin/users/{id}/roles  # Assign role
  DELETE /admin/users/{id}/roles/{role_id}  # Revoke role

Assessments:
  GET  /assessments             # List assessments
  POST /assessments             # Create assessment
  GET  /assessments/{id}        # Get assessment
  PUT  /assessments/{id}        # Update assessment

Recommendations:
  GET  /recommendations         # List recommendations
  POST /recommendations         # Create recommendation
  GET  /recommendations/{id}    # Get recommendation

Knowledge Graph:
  POST /knowledge-graph/query   # Query knowledge graph
  GET  /knowledge-graph/status  # Graph status
  POST /knowledge-graph/documents  # Upload documents

Dashboard:
  GET  /dashboard/summary       # Dashboard summary
  GET  /dashboard/metrics       # System metrics
  GET  /dashboard/analytics     # Analytics data

Health & Monitoring:
  GET  /health                  # Health check
  GET  /health/ready            # Readiness check
  GET  /metrics                 # Prometheus metrics
```

### 4.2 API Design Patterns

#### Request/Response Format
```json
{
  "status": "success|error",
  "data": { /* response payload */ },
  "error": null,
  "timestamp": "2025-11-30T12:00:00Z",
  "request_id": "uuid"
}
```

#### Error Handling
```json
{
  "status": "error",
  "error": {
    "code": "UNAUTHORIZED|FORBIDDEN|NOT_FOUND|VALIDATION_ERROR",
    "message": "Human-readable error message",
    "details": [ /* field-level errors */ ]
  }
}
```

#### Pagination
```json
{
  "data": [ /* items */ ],
  "pagination": {
    "total": 100,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

### 4.3 API Security

- **Authentication**: JWT tokens required on protected endpoints
- **Rate Limiting**: 234 endpoints with configured rate limits
- **Input Validation**: Pydantic models for all request validation
- **CORS**: Properly configured for allowed origins
- **Security Headers**:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security`

### 4.4 API Documentation

**OpenAPI Spec**: Full Swagger/OpenAPI 3.0 specification
**Available at**: `/docs` (Swagger UI), `/redoc` (ReDoc)
**Includes**:
- All endpoints with parameters
- Request/response schemas
- Authentication requirements
- Rate limiting information
- Error codes

---

## 5. AWS MARKETPLACE INTEGRATION ARCHITECTURE

### 5.1 Marketplace Integration Goals

**Status**: Framework designed, awaiting implementation

#### Key Marketplace Requirements
1. **Trial Management**: Free trial period with conversion path
2. **Customer Registration**: AWS customer ID capture and validation
3. **Usage Metering**: Track usage for billing
4. **Subscription Handling**: Subscription state management
5. **Feature Tiering**: Different features for different pricing tiers
6. **Billing Integration**: AWS Marketplace metering API integration

### 5.2 Trial Management System

#### Proposed Design
```yaml
Trial Flow:
  1. AWS customer registers from marketplace
  2. System captures AWS customer ID
  3. Create trial account (14-day default)
  4. Customer gets full access during trial
  5. Trial expiration triggers conversion prompt
  6. Pay customer converts to subscription
  7. Account transitions to paid tier

Database Tables Needed:
  aws_customer_registrations:
    - aws_customer_id
    - email
    - registration_date
    - trial_start_date
    - trial_expiration_date
    - status (trial, active, expired, converted)

  aws_usage_metrics:
    - aws_customer_id
    - metric_type (api_calls, documents, assessments)
    - quantity
    - timestamp
    - billing_dimension

  aws_subscriptions:
    - aws_customer_id
    - subscription_id
    - product_code
    - pricing_tier (starter, pro, enterprise)
    - activation_date
    - renewal_date
    - status
```

### 5.3 Feature Tiering System

```python
# Feature access based on subscription tier
FEATURE_TIERS = {
    "trial": {
        "api_calls_per_month": 10000,
        "documents": 100,
        "assessments": 10,
        "knowledge_graph": False,
        "advanced_analytics": False,
        "support_level": "community"
    },
    "starter": {
        "api_calls_per_month": 50000,
        "documents": 1000,
        "assessments": 100,
        "knowledge_graph": True,
        "advanced_analytics": False,
        "support_level": "email"
    },
    "pro": {
        "api_calls_per_month": 500000,
        "documents": 10000,
        "assessments": 1000,
        "knowledge_graph": True,
        "advanced_analytics": True,
        "support_level": "phone"
    },
    "enterprise": {
        "api_calls_per_month": -1,  # Unlimited
        "documents": -1,
        "assessments": -1,
        "knowledge_graph": True,
        "advanced_analytics": True,
        "support_level": "dedicated"
    }
}
```

### 5.4 AWS Marketplace Readiness Assessment

**Current Status**: NOT READY
**Estimated Ready Date**: Based on 7-day sprint (historical plan)

#### Critical Gaps
1. **Test Coverage**: 5.91% (need 80%+)
   - 5,729 tests exist but infrastructure broken
   - Need to rebuild test framework
   - Focus on critical paths: auth, billing, core API

2. **AWS Integration**: MISSING
   - No trial management system
   - No metering integration
   - No subscription handling
   - No AWS customer ID capture

3. **Performance**: UNKNOWN
   - No performance benchmarks
   - Response time SLA: <500ms (target)
   - Database query: <50ms (target)

4. **Stability**: INCOMPLETE
   - Only 37.2% endpoints verified working
   - No load testing
   - No SLA metrics

#### Go/No-Go Criteria (MVP)
- [x] 80% test coverage on critical paths
- [x] All security vulnerabilities fixed
- [ ] Trial management working
- [ ] Performance SLA met
- [ ] AWS customer registration flow

---

## 6. SMART SCAFFOLD INTEGRATION ARCHITECTURE

### 6.1 Smart Scaffold v4.0 Overview

**Purpose**: GitHub-native framework for orchestrating AI developers through async collaboration

**Key Features**:
- Async-first collaboration (eliminates synchronous bottlenecks)
- Confidence-based routing (≥0.85 vs <0.85)
- Critical issue detection (security, data-migration, breaking-change)
- Automated evidence generation
- 97.2% validation success rate target

### 6.2 Integration Pattern

#### Optional Integration (Feature-Flagged)
```python
# Runtime configuration
from src.features.feature_flags import get_feature_flag

def is_smart_scaffold_enabled():
    return get_feature_flag("smart_scaffold_integration", default=False)

# Graceful degradation
async def create_collaboration_session(issue_data):
    if SMART_SCAFFOLD_ENABLED:
        async with SmartScaffoldAPIClient() as client:
            return await client.create_collaboration_session(issue_data)
    else:
        # Continue without collaboration
        return create_local_session(issue_data)
```

### 6.3 Three-Layer Reality System

#### 1. Build-Time Validation
- Compile contracts into native adapters
- Syntax checking, type validation
- Output: Static adapter code with <1ms overhead

#### 2. Deploy-Time Validation
- Validate schema compatibility
- Generate zero-downtime migrations
- Output: Migration plans with rollback

#### 3. Runtime Monitoring
- Continuous schema drift detection
- Performance monitoring
- Alert generation for anomalies

### 6.4 Enhanced Smart Scaffold Components

#### Context Manifest System
- Gherkin requirement parsing
- Component dependency analysis
- Pattern similarity matching
- Focused context bundling for AI operators

#### Pre-Mortem Risk Analysis
- Learn from past failures
- Identify risk patterns
- Generate mitigation strategies
- Calculate confidence scores

#### Automated ADR Generation
- Detect novel architectural patterns
- Document decisions with context
- Track consequences and alternatives
- Update pattern library automatically

---

## 7. MULTI-TENANT ARCHITECTURE

### 7.1 Multi-Tenancy Model

**Type**: Database-per-schema within single database
**Isolation Level**: Row-level + schema-level

### 7.2 Tenant Isolation Strategy

```sql
-- Tenant identification
-- Option 1: Row-level security policies
ALTER TABLE ag_catalog.organizations
ENABLE ROW LEVEL SECURITY;

CREATE POLICY organization_isolation ON ag_catalog.organizations
USING (id = current_setting('app.current_tenant_id')::uuid);

-- Option 2: Tenant ID in where clause
SELECT * FROM ag_catalog.assessments
WHERE tenant_id = current_tenant_id;
```

### 7.3 Multi-Tenant Data Flow

```
Request with JWT
   ↓
Extract user from token
   ↓
Load user's assigned tenants
   ↓
Validate tenant_id in request
   ↓
Set tenant context (Postgres app.current_tenant_id)
   ↓
Enable RLS policies
   ↓
Execute query (only see own tenant data)
```

### 7.4 Tenant-Related Tables

```yaml
Organizations:
  - id (UUID)
  - name
  - domain
  - settings (JSONB)
  - parent_org_id (for hierarchy)

Organization Members:
  - id
  - user_id
  - organization_id
  - role
  - added_at

Tenant Settings:
  - tenant_id
  - key
  - value (JSONB)
  - updated_at
```

---

## 8. GRAPHRAG KNOWLEDGE GRAPH ARCHITECTURE

### 8.1 GraphRAG System Overview

**Purpose**: Intelligent question-answering system using graph-based reasoning

**Default Backend**: PostgreSQL with CTE (Common Table Expressions)
**Optional Backend**: Memgraph (graph database)

### 8.2 GraphRAG API Client SDK

#### Core Features
- Async and sync support
- Configuration management with Pydantic
- Automatic retry logic with exponential backoff
- Context managers for resource cleanup
- Full type hints and type safety

#### API Operations
```python
# Query operations
await client.query({"query": "...", "user_id": "..."})
await client.get_query_status(query_id)
await client.batch_query([...])

# Health and monitoring
await client.health_check()
await client.get_metrics()

# Cost management
await client.get_cost_metrics(period_hours=24)
await client.get_cost_recommendations()
await client.create_cost_alert(threshold=...)

# Cache operations
await client.clear_cache()
await client.get_cache_stats()

# Dashboard access
await client.get_dashboard_config()
await client.get_prometheus_alerts()
```

### 8.3 Knowledge Organization

```yaml
Document Types:
  - Technical Documentation
  - Security Guidelines
  - Compliance Frameworks
  - AWS Best Practices
  - Cost Optimization Guides

Knowledge Graph Entities:
  - Resources (EC2, S3, RDS, etc.)
  - Vulnerabilities
  - Compliance Controls
  - Cost Factors
  - Best Practices

Relationships:
  - Resource has Configuration
  - Configuration violates Compliance
  - Vulnerability affects Resource
  - Practice reduces Cost
```

### 8.4 Q&A Engine Integration

```python
# Submit question to knowledge graph
response = await graphrag_client.query({
    "query": "What are AWS best practices for S3 security?",
    "context": "S3 configuration analysis",
    "user_id": "user-123"
})

# Returns structured answer
{
    "answer": "...",
    "confidence": 0.95,
    "sources": ["doc1", "doc2"],
    "entities": ["S3", "Security", "Encryption"],
    "processing_time_ms": 250
}
```

---

## 9. PERFORMANCE & OPTIMIZATION ARCHITECTURE

### 9.1 Caching Strategy

**Layers**:
1. **Redis Cache**: Session, query results, permissions
2. **Application Cache**: In-memory TTL cache for config
3. **Database Cache**: Query optimization with indexes

**Cache Invalidation**:
- Time-based (TTL)
- Event-based (on data changes)
- Manual (admin cache clear)

### 9.2 Performance Targets

```yaml
API Response Times:
  - Health check: <10ms
  - Simple auth: <100ms
  - Complex query: <500ms
  - GraphRAG query: <1000ms

Database:
  - Index lookups: <10ms
  - Simple queries: <50ms
  - Complex joins: <200ms

Connection Pooling:
  - Min connections: 5
  - Max connections: 20
  - Connection timeout: 30s
```

### 9.3 Query Optimization

- **Indexes**: Strategic indexes on frequently queried columns
- **Eager Loading**: Prevent N+1 queries
- **Pagination**: Limit result sets
- **Materialized Views**: Pre-computed complex queries

### 9.4 Monitoring & Observability

**Prometheus Metrics**:
- Request count and duration
- Error rates
- Database connection pool stats
- Cache hit/miss ratios

**Logging**:
- Structured logging with correlation IDs
- Request/response logging
- Error stack traces
- Audit logging for security events

**Alerting**:
- Response time p95 > 500ms
- Error rate > 1%
- Memory usage > 80%
- Database connections > 90%

---

## 10. DEPLOYMENT ARCHITECTURE

### 10.1 Docker Containerization

**Components**:
```yaml
Services:
  - API: FastAPI application
  - PostgreSQL: Database
  - Redis: Cache and session store
  - Ollama: Local LLM (optional)
  - Grafana: Monitoring dashboards
  - Prometheus: Metrics collection

Networking:
  - Internal network for service communication
  - API exposed on port 8000
  - Database on port 5432
  - Redis on port 6379
  - Ollama on port 11434
```

### 10.2 Environment Configuration

```yaml
Production:
  - TLS/SSL encryption
  - Secrets management (AWS Secrets Manager)
  - Multi-factor authentication
  - Backup and disaster recovery
  - Load balancing

Staging:
  - Same infrastructure as production
  - Test data isolated
  - Comprehensive logging

Development:
  - Docker Compose for local development
  - Hot reload enabled
  - Test database with sample data
  - Local Ollama instance
```

### 10.3 CI/CD Pipeline

**GitHub Actions**:
- Automated testing on PR
- Pre-commit hook validation
- Quality gates with pre-commit
- Integration testing
- Performance benchmarking
- Container building and pushing

---

## 11. QUALITY & TESTING ARCHITECTURE

### 11.1 Testing Levels

#### Unit Tests
- Individual function/method testing
- Mocked dependencies
- Fast execution (<1s per test)

#### Integration Tests
- Real service interactions
- Database connections
- API endpoint testing
- 30-60 second execution

#### End-to-End Tests
- Complete workflow testing
- Real external integrations
- Performance testing
- 5-10 minute execution

### 11.2 Test Coverage Targets

```yaml
Critical Paths (100%):
  - Authentication and authorization
  - Database contract operations
  - API endpoints
  - Error handling

Core Features (80%):
  - Business logic
  - Integration points
  - Data validation

Utilities (60%):
  - Helpers
  - Configuration
  - Logging
```

### 11.3 Quality Gates

**Pre-commit Checks**:
- Python syntax validation
- Type checking (mypy)
- Code formatting (black, isort)
- Linting (flake8, pylint)
- Security (bandit)
- Database schema validation

**CI/CD Gates**:
- All tests pass
- Minimum 80% coverage on changed files
- No security vulnerabilities
- Performance benchmarks met

---

## 12. CRITICAL DESIGN DECISIONS

### 12.1 Database Schema Organization

**Decision**: Use ag_catalog schema (from Apache AGE)
**Rationale**:
- Historical integration point
- Proper schema separation
- Support for graph operations if needed
- Clear namespace management

**Alternative Considered**: Public schema
**Why Rejected**: Less clear separation, harder to manage

### 12.2 Contract-Driven Architecture

**Decision**: All database operations through contracts
**Rationale**:
- Eliminates SQL injection
- Type safety
- Consistency enforcement
- Easy to test and validate

**Alternative Considered**: Direct SQL queries
**Why Rejected**: Security vulnerabilities, hard to maintain

### 12.3 Multi-Tenant Model

**Decision**: Database-level row security with tenant ID
**Rationale**:
- Cost-effective (single database)
- Easy to manage
- Strong isolation
- Flexible scaling

**Alternative Considered**: Separate database per tenant
**Why Rejected**: Operational complexity, higher costs

### 12.4 Smart Scaffold Integration

**Decision**: Optional integration via feature flag
**Rationale**:
- Cloud Optimizer works standalone
- Collaboration is enhancement, not requirement
- Graceful degradation
- Independent deployment cycles

**Alternative Considered**: Mandatory tight coupling
**Why Rejected**: Reduces autonomy, complicates deployment

### 12.5 Authentication Strategy

**Decision**: JWT with refresh tokens
**Rationale**:
- Stateless authentication
- Scalable across multiple servers
- Support for mobile apps
- Industry standard

**Alternative Considered**: Session-based auth
**Why Rejected**: Less scalable, harder for distributed systems

---

## 13. LESSONS LEARNED & BEST PRACTICES

### 13.1 What Worked Well

1. **Database Contracts**: 100% contract coverage prevented SQL injection vulnerabilities
2. **RBAC System**: Comprehensive role-based access control provided security foundation
3. **API Documentation**: OpenAPI specification enabled consistent integration
4. **Multi-tenancy Model**: Row-level security provided effective tenant isolation
5. **Modular Architecture**: Clear separation of concerns enabled independent scaling

### 13.2 Areas for Improvement

1. **Test Coverage**: Started at 5.91%, needs to reach 80%+
2. **Performance Benchmarking**: No established SLAs initially
3. **AWS Integration**: Marketplace integration left incomplete
4. **Documentation**: Too much generated documentation, needs consolidation
5. **Development Tooling**: Pre-commit system needed stronger integration

### 13.3 Design Patterns Proven Effective

1. **Contract Pattern**: Database contract system provides type safety
2. **Feature Flags**: Runtime control of features enables gradual rollout
3. **Graceful Degradation**: System continues when optional services unavailable
4. **Audit Logging**: Complete audit trail enables security and compliance
5. **Schema Abstraction**: Eliminates hardcoded references, improves maintainability

### 13.4 Anti-Patterns to Avoid

1. **Mock Authentication**: Never use mock RBAC/auth in production
2. **Hardcoded Schemas**: Always abstract schema references
3. **Direct SQL**: Always use parameterized queries through contracts
4. **Synchronous Bottlenecks**: Use async patterns for I/O operations
5. **Missing Error Handling**: Comprehensive error handling required for stability

---

## 14. FUTURE ARCHITECTURE EVOLUTION

### 14.1 Planned Enhancements

1. **GraphRAG Memgraph Support**: Optional native graph backend
2. **Performance Optimization**: Caching and query optimization
3. **AWS Marketplace Integration**: Complete trial, metering, billing
4. **Advanced Analytics**: Deep-dive analytics and reporting
5. **AI Agent Integration**: Autonomous optimization agents

### 14.2 Scalability Roadmap

```yaml
Phase 1 (Current):
  - Single database instance
  - Connection pooling
  - Redis caching
  - Load balancer

Phase 2 (Planned):
  - Read replicas for analytics
  - Sharding by tenant
  - Distributed caching
  - Message queue for async jobs

Phase 3 (Future):
  - Global distribution
  - Edge caching
  - Serverless components
  - Event streaming
```

### 14.3 Feature Expansion Vision

1. **Compliance Framework**: Deeper compliance analysis
2. **Cost Forecasting**: Advanced predictive analytics
3. **Security Scanning**: Continuous vulnerability scanning
4. **Optimization Engine**: Autonomous optimization recommendations
5. **Integration Marketplace**: Third-party integrations

---

## 15. ARCHITECTURE SUMMARY & RECOMMENDATIONS

### 15.1 Key Architecture Strengths

1. **Security First**: Production-ready authentication and RBAC
2. **Type Safety**: Database contracts eliminate SQL injection
3. **Scalability**: Multi-tenancy with proper isolation
4. **Flexibility**: Optional Smart Scaffold integration
5. **Maintainability**: Clear separation of concerns

### 15.2 Critical Implementation Requirements

For new system build:

1. **Database Contracts**: Must implement for all tables
   - 100% type coverage required
   - No direct SQL queries
   - Comprehensive validation

2. **Authentication**: Production-ready from day 1
   - Real password hashing
   - JWT with proper expiration
   - Comprehensive audit logging

3. **API Security**: 234 endpoints with protection
   - Rate limiting on all endpoints
   - Input validation with Pydantic
   - Security headers on all responses

4. **Testing**: Target 80%+ coverage
   - Focus on critical paths
   - Integration tests with real services
   - Performance benchmarking

5. **AWS Integration**: For marketplace readiness
   - Trial management system
   - Usage metering
   - Subscription handling

### 15.3 Development Recommendations

1. **Start with Contracts**: Build database contracts first
2. **Then Authentication**: Implement production auth immediately
3. **Then API**: Build API on top of contracts and auth
4. **Then Testing**: Comprehensive test suite for all components
5. **Then AWS Integration**: Add marketplace features last

### 15.4 Quality Standards

**Non-Negotiable**:
- 100% database contract coverage
- Production-ready authentication (no mocks)
- Type hints on all functions
- Pre-commit hooks enforced
- 80%+ test coverage on critical paths
- Comprehensive audit logging

---

## Appendix: Document References

### Core Architecture Documents
- `/docs/architecture/post_separation_architecture_guide.md` - System architecture
- `/docs/02-architecture/README.md` - Architecture overview
- `/docs/02-architecture/security/PRODUCTION_AUTH_ARCHITECTURE_DESIGN.md` - Auth design

### Database Architecture
- `/docs/02-architecture/database/README.md` - Database architecture
- `/docs/02-architecture/contracts/README.md` - Contract system
- `/docs/02-architecture/contracts/DATABASE_CONTRACTS_IMPLEMENTATION_GUIDE.md` - Contract implementation

### Integration Architecture
- `/docs/01-guides/smart-scaffold/SMART_SCAFFOLD_COMPREHENSIVE_DESIGN.md` - Smart Scaffold design
- `/docs/01-guides/smart-scaffold/SMART_SCAFFOLD_INTEGRATION_DESIGN.md` - Integration patterns

### AWS Integration
- `/docs/generated/AWS_MARKETPLACE_READINESS_REPORT.md` - Marketplace readiness
- `/docs/generated/GRAPHRAG_API_CLIENT_SDK_COMPLETE.md` - GraphRAG SDK

### API Architecture
- `/docs/api/openapi_summary.md` - API endpoints
- `/docs/api/openapi.json` - OpenAPI specification

### Development
- `/docs/01-guides/developer-onboarding/Developer_Standards.md` - Development standards
- `/docs/01-guides/testing/` - Testing frameworks

---

**Document Compiled**: 2025-11-30
**For**: Cloud Optimizer v2 Clean-Slate Rebuild
**Status**: Comprehensive architectural and design summary
