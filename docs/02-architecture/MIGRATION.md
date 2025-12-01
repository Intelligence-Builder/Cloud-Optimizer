# Cloud Optimizer v2 Migration Guide

**Version:** 1.0
**Date:** 2025-11-30
**Purpose:** Guide migration from legacy Cloud_Optimizer to new cloud-optimizer + Intelligence-Builder

---

## Document Purpose

This document consolidates:
1. Gap analysis between legacy and new systems
2. Migration strategies and data mapping
3. Legacy system context for reference
4. Deprecation timeline and cut-over plan

---

## 1. Executive Summary

| Metric | Legacy | New (CO + IB) | Gap Status |
|--------|--------|---------------|------------|
| **API Endpoints** | 162+ | ~25 | 🔴 Significant gap |
| **Services** | 125+ | ~10 | 🔴 Significant gap |
| **Database Tables** | 67 | ~10 | 🔴 Significant gap |
| **AWS Scanners** | Implied | 7 implemented | 🟢 Good coverage |
| **Test Coverage** | Extensive | 54 files, 80%+ target | 🟢 On track |
| **Documentation** | Extensive | Comprehensive | 🟢 Good |

**Overall Assessment:** The new architecture provides a cleaner, more maintainable foundation with Intelligence-Builder as a powerful backend. Significant functionality needs migration, but the new system offers better separation of concerns and extensibility.

---

## 2. Architecture Comparison

### Legacy System Architecture

```
Legacy Cloud_Optimizer (Monolithic)
├── FastAPI Application
│   ├── 162+ API endpoints
│   ├── 125+ service classes
│   └── Direct DB access
├── PostgreSQL (67 tables)
│   ├── Multi-tenant data
│   ├── Knowledge graph
│   └── All business data
└── AWS Integrations
    └── Marketplace, S3, etc.
```

### New System Architecture

```
Cloud Optimizer v2 (Layered) + Intelligence-Builder (Platform)
├── Cloud Optimizer (Application)
│   ├── FastAPI (~25 endpoints)
│   ├── ~10 services (orchestration)
│   └── Scanner implementations
├── Intelligence-Builder (Platform)
│   ├── Graph backends (Postgres CTE, Memgraph)
│   ├── Pattern detection engine
│   ├── Domain system
│   └── Ingestion pipeline
└── Infrastructure
    ├── PostgreSQL (app data)
    ├── Redis (cache, sessions)
    └── AWS Integrations
```

### Key Differences

| Aspect | Legacy | New |
|--------|--------|-----|
| **Architecture** | Monolithic | Layered + Platform |
| **Graph Database** | Apache AGE | PostgresCTE / Memgraph |
| **Intelligence** | Embedded | IB Platform (reusable) |
| **Multi-Tenancy** | Built-in | To be implemented |
| **Testing** | Mixed | 80%+ coverage target |

---

## 3. Gap Analysis by Category

### 3.1 Authentication & Authorization

| Feature | Legacy | New | Gap |
|---------|--------|-----|-----|
| JWT Authentication | ✅ | ✅ (via IB) | None |
| OAuth2/OIDC | ✅ | ❌ | Phase 4 |
| RBAC | ✅ | ✅ (via IB) | None |
| API Key Management | ✅ | ✅ (via IB) | None |
| User Registration | ✅ | ❌ | Phase 1 |
| Multi-Tenant Auth | ✅ | ❌ | Phase 1 |

### 3.2 Security Analysis

| Feature | Legacy | New | Gap |
|---------|--------|-----|-----|
| Vulnerability Detection | ✅ | ✅ | None |
| Compliance Assessment | ✅ | ✅ | None |
| Security Recommendations | ✅ | ✅ | None |
| Threat Analysis | ✅ | ✅ | None |
| Security Posture Scoring | ✅ | ⚠️ | Enhancement needed |
| Auth Attack Detection | ✅ | ❌ | Optional |

### 3.3 Cost Optimization

| Feature | Legacy | New | Gap |
|---------|--------|-----|-----|
| Spending Analysis | ✅ | ✅ | None |
| Right-sizing | ✅ | ✅ | None |
| RI/Savings Plans | ✅ | ✅ | None |
| Cost Forecasting | ✅ | ❌ | Phase 2 |
| AWS Marketplace | ✅ | ❌ | Phase 1 (P0) |

### 3.4 Multi-Tenant Support

| Feature | Legacy | New | Gap |
|---------|--------|-----|-----|
| Tenant Isolation | ✅ | ❌ | Phase 1 (P0) |
| Tenant Quotas | ✅ | ⚠️ | Phase 1 |
| Trial Management | ✅ | ❌ | Phase 1 (P0) |
| Cross-tenant Admin | ✅ | ❌ | Phase 1 |

### 3.5 Frontend / UI

| Feature | Legacy | New | Gap |
|---------|--------|-----|-----|
| React Dashboard | ✅ | ❌ | Phase 3 (P0) |
| Security UI | ✅ | ❌ | Phase 3 |
| Cost UI | ✅ | ❌ | Phase 3 |
| Admin Panel | ✅ | ❌ | Phase 3 |

---

## 4. Migration Strategy

### 4.1 Data Migration

#### Users Table

```sql
-- Legacy Schema
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    name VARCHAR(255),
    organization_id INTEGER,  -- Legacy term
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- New Schema
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    name VARCHAR(255),
    status VARCHAR(50),
    email_verified BOOLEAN,
    mfa_enabled BOOLEAN,
    created_at TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ
);

-- Migration Script
INSERT INTO new_users (user_id, email, password_hash, name, status, email_verified, created_at)
SELECT
    gen_random_uuid(),
    email,
    password_hash,
    name,
    'active',
    true,  -- Assume legacy users are verified
    created_at
FROM legacy_users;
```

#### Tenants Table

```sql
-- Legacy Schema (organizations)
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    slug VARCHAR(100),
    tier VARCHAR(50),
    settings JSONB,
    created_at TIMESTAMP
);

-- New Schema (tenants)
CREATE TABLE tenants (
    tenant_id UUID PRIMARY KEY,
    name VARCHAR(255),
    slug VARCHAR(100) UNIQUE,
    tier VARCHAR(50),
    status VARCHAR(50),
    settings JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- Migration Script
INSERT INTO tenants (tenant_id, name, slug, tier, status, settings, created_at, updated_at)
SELECT
    gen_random_uuid(),
    name,
    slug,
    COALESCE(tier, 'starter'),
    'active',
    COALESCE(settings, '{}'),
    created_at,
    NOW()
FROM organizations;
```

#### Tenant-User Association

```sql
-- Legacy: users.organization_id
-- New: tenant_members table

INSERT INTO tenant_members (tenant_id, user_id, role, invited_at, accepted_at)
SELECT
    t.tenant_id,
    u.user_id,
    CASE
        WHEN lu.is_admin THEN 'admin'
        ELSE 'member'
    END,
    u.created_at,
    u.created_at
FROM legacy_users lu
JOIN users u ON u.email = lu.email
JOIN organizations o ON o.id = lu.organization_id
JOIN tenants t ON t.slug = o.slug;
```

### 4.2 API Migration

#### Endpoint Mapping

| Legacy Endpoint | New Endpoint | Notes |
|-----------------|--------------|-------|
| `POST /auth/login` | `POST /api/v1/auth/login` | Same contract |
| `POST /auth/register` | `POST /api/v1/auth/register` | Add tenant context |
| `GET /organization` | `GET /api/v1/tenant` | Renamed |
| `GET /security/scan` | `POST /api/v1/security/scan` | Changed to POST |
| `GET /costs/analysis` | `GET /api/v1/cost/analysis` | Singular naming |
| `POST /marketplace/webhook` | `POST /api/v1/marketplace/webhook` | Same contract |

#### Deprecated Endpoints (Will Not Migrate)

| Endpoint | Reason | Alternative |
|----------|--------|-------------|
| `/expert-workbench/*` | Not needed in v2 | Manual GitHub integration |
| `/backup/*` | Use PostgreSQL native | `pg_dump` |
| `/replication/*` | Use PostgreSQL native | Streaming replication |

### 4.3 Feature Flags for Migration

```python
class MigrationFlags(BaseSettings):
    """Control gradual migration rollout."""

    # Phase 1
    enable_new_auth: bool = False
    enable_tenant_isolation: bool = False
    enable_marketplace_v2: bool = False

    # Phase 2
    enable_new_dashboard_api: bool = False
    enable_cost_forecasting: bool = False

    # Phase 3
    enable_new_frontend: bool = False

    # Percentage rollout
    new_system_rollout_percent: int = 0  # 0-100
```

### 4.4 Parallel Running Strategy

During migration, both systems run in parallel:

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │  Legacy System  │◄─────────►│   New System    │
    │                 │  Data Sync │                 │
    └─────────────────┘           └─────────────────┘

Phase 1: 100% Legacy, 0% New
Phase 2: 80% Legacy, 20% New (select tenants)
Phase 3: 50% Legacy, 50% New
Phase 4: 20% Legacy, 80% New
Phase 5: 0% Legacy, 100% New
```

---

## 5. Priority Gap Resolution

### 5.1 Critical (P0 - Business-Blocking)

| Gap | Phase | Effort | Action |
|-----|-------|--------|--------|
| AWS Marketplace | 1 | 3 weeks | Full implementation required |
| Multi-Tenant Support | 1 | 3 weeks | RLS + tenant context |
| Trial Management | 1 | 1 week | Usage metering |
| Frontend | 3 | 8 weeks | New React application |

### 5.2 High (P1 - Feature Parity)

| Gap | Phase | Effort | Action |
|-----|-------|--------|--------|
| User Registration | 1 | 1 week | New implementation |
| Cost Forecasting | 2 | 2 weeks | Extend cost scanner |
| Prometheus Metrics | 2 | 1 week | Add instrumentator |
| Dashboard APIs | 2 | 2 weeks | New implementation |

### 5.3 Medium (P2 - Nice to Have)

| Gap | Phase | Effort | Action |
|-----|-------|--------|--------|
| OAuth2/OIDC | 4 | 2 weeks | Integrate with IB |
| SNS Notifications | 4 | 1 week | Add notification service |
| Advanced Analytics | 4 | 2 weeks | Custom reports |

---

## 6. Legacy System Context

### 6.1 Module Summary

The legacy Cloud_Optimizer contains the following major modules:

| Module | Purpose | Migration Status |
|--------|---------|------------------|
| `api/` | FastAPI routers (162+ endpoints) | Partially migrated |
| `services/` | Business logic (125+ services) | Selectively migrating |
| `models/` | SQLAlchemy models (67 tables) | New schema design |
| `utils/` | Helper functions | Selective use |
| `scripts/` | Management scripts | New scripts |

### 6.2 Key Legacy Services

| Service | Status | New Location |
|---------|--------|--------------|
| `AuthService` | ✅ Migrated | IB Platform |
| `SecurityService` | ✅ Migrated | cloud-optimizer |
| `CostService` | ✅ Migrated | cloud-optimizer |
| `MarketplaceService` | ❌ Not started | Phase 1 |
| `TenantService` | ❌ Not started | Phase 1 |
| `TrialService` | ❌ Not started | Phase 1 |
| `DashboardService` | ❌ Not started | Phase 2 |
| `NotificationService` | ❌ Not started | Phase 2 |

### 6.3 Database Schema Reference

Legacy tables to migrate:

```
Multi-Tenant Tables:
├── organizations → tenants
├── organization_settings → tenant settings (JSONB)
├── organization_quotas → tenant_quotas
└── organization_members → tenant_members

User Tables:
├── users → users (new schema)
├── user_roles → role column in tenant_members
├── user_sessions → user_sessions
└── api_keys → api_keys

Marketplace Tables:
├── marketplace_customers → marketplace_customers
├── marketplace_subscriptions → merged into marketplace_customers
├── usage_records → usage_records
└── billing_events → audit_logs

Assessment Tables:
├── assessments → stored in IB
├── findings → stored in IB
└── recommendations → stored in IB
```

---

## 7. Deprecation Timeline

### Phase 1: Parallel Operation (Weeks 1-8)
- New system in development
- Legacy continues serving all traffic
- No deprecation yet

### Phase 2: Pilot Migration (Weeks 9-14)
- Select tenants migrated to new system
- Legacy continues for majority
- Feature flag: `new_system_rollout_percent: 10`

### Phase 3: Gradual Rollout (Weeks 15-22)
- 50% traffic to new system
- Legacy in maintenance mode
- Feature flag: `new_system_rollout_percent: 50`

### Phase 4: Legacy Deprecation (Weeks 23-28)
- 90% traffic to new system
- Legacy for fallback only
- Feature flag: `new_system_rollout_percent: 90`

### Phase 5: Legacy Retirement (Week 29+)
- 100% traffic to new system
- Legacy decommissioned
- Data archived

---

## 8. Rollback Plan

### Immediate Rollback (< 1 hour)

```bash
# Switch all traffic back to legacy
./scripts/migration/rollback.sh --immediate

# This does:
# 1. Update load balancer to 100% legacy
# 2. Clear new system cache
# 3. Notify team
```

### Data Rollback (1-4 hours)

```bash
# Restore data from before migration
./scripts/migration/rollback.sh --restore-data

# This does:
# 1. Stop new system writes
# 2. Restore PostgreSQL from snapshot
# 3. Replay missed transactions from audit log
# 4. Verify data integrity
```

### Full Rollback (4-24 hours)

```bash
# Complete rollback to legacy
./scripts/migration/rollback.sh --full

# This does:
# 1. All immediate rollback steps
# 2. Restore legacy database
# 3. Re-enable legacy background jobs
# 4. Update DNS
```

---

## 9. Validation Checklist

### Pre-Migration

- [ ] All legacy data backed up
- [ ] Migration scripts tested on staging
- [ ] Rollback procedures tested
- [ ] Team notified of migration window
- [ ] Monitoring dashboards ready

### During Migration

- [ ] Data integrity checks passing
- [ ] No error rate increase
- [ ] Latency within acceptable range
- [ ] All critical flows tested
- [ ] Rollback trigger defined

### Post-Migration

- [ ] All automated tests passing
- [ ] Manual smoke tests completed
- [ ] User acceptance testing done
- [ ] Performance benchmarks met
- [ ] Documentation updated

---

## 10. New System Advantages

Despite the migration effort, the new architecture provides significant advantages:

1. **Cleaner Separation** - Intelligence-Builder as a standalone platform
2. **Reusable Intelligence** - IB can serve multiple applications
3. **Modern Patterns** - Factory pattern for graph backends, clean SDK
4. **Better Testing** - 80%+ coverage target, comprehensive test suite
5. **Dual AWS Support** - LocalStack + real AWS testing
6. **Extensible Domains** - Pattern-based domain system
7. **Type Safety** - 100% type hints, strict mypy
8. **Simpler Codebase** - Target 10K LOC vs 50K+ legacy

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-30 | Initial migration guide, consolidated from GAP_ANALYSIS.md |
