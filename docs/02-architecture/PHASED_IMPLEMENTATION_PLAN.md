# Cloud Optimizer v2 - Phased Implementation Plan

**Version:** 1.2
**Date:** 2025-11-30
**Status:** Ready for Execution

---

## Executive Summary

Based on comprehensive analysis of legacy Cloud_Optimizer (~125K LOC) and CloudGuardian (~45K LOC) codebases, this plan leverages existing implementation to reduce the overall timeline from 52 weeks to **30 weeks (42% reduction)**.

### Deployment Model: AWS Marketplace Container Product

Cloud Optimizer will be offered as an **AWS Marketplace Container Product** with a trial-first strategy to gather real-world feedback.

**Critical Constraint:** Intelligence-Builder (IB) and Cloud Optimizer (CO) must be deployed together and kept in sync.

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Customer's AWS Account                          │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      ECS/EKS Cluster                           │  │
│  │                                                                 │  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │           Cloud Optimizer + IB Platform Bundle           │   │  │
│  │  │  ┌─────────────────┐  ┌─────────────────────────────┐   │   │  │
│  │  │  │  CO API Server  │  │  Intelligence-Builder Core   │   │   │  │
│  │  │  │  - FastAPI      │  │  - Graph Backend (CTE)       │   │   │  │
│  │  │  │  - Scanners     │  │  - Pattern Engine            │   │   │  │
│  │  │  │  - Auth         │  │  - Domain System             │   │   │  │
│  │  │  └────────┬────────┘  └─────────────┬───────────────┘   │   │  │
│  │  │           │                         │                    │   │  │
│  │  │           └───────────┬─────────────┘                    │   │  │
│  │  │                       │ Shared Process                   │   │  │
│  │  └───────────────────────┼─────────────────────────────────┘   │  │
│  │                          │                                      │  │
│  │  ┌─────────────────┐     │     ┌─────────────────┐             │  │
│  │  │   Job Worker    │◄────┴────►│   Redis Cache   │             │  │
│  │  │  (CO + IB)      │           │   (Optional)    │             │  │
│  │  └────────┬────────┘           └─────────────────┘             │  │
│  │           │                                                     │  │
│  └───────────┼─────────────────────────────────────────────────────┘  │
│              │                                                        │
│              ▼                                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    PostgreSQL RDS                               │  │
│  │  ┌──────────────────┐  ┌──────────────────────────────────┐   │  │
│  │  │ CO Schema        │  │ IB Schema                         │   │  │
│  │  │ - users          │  │ - graph_nodes                     │   │  │
│  │  │ - findings       │  │ - graph_edges                     │   │  │
│  │  │ - scans          │  │ - patterns                        │   │  │
│  │  │ - usage_records  │  │ - domains                         │   │  │
│  │  └──────────────────┘  └──────────────────────────────────┘   │  │
│  │                    Coordinated Migrations                       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                              │                                        │
│                              ▼                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │              AWS Marketplace Metering API                       │  │
│  │  - License validation at startup                                │  │
│  │  - Usage metering (scans, findings, API calls)                  │  │
│  │  - Trial expiration enforcement                                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### CO + IB Synchronization Strategy

| Aspect | Strategy |
|--------|----------|
| **Packaging** | Single Docker image with both CO and IB |
| **Versioning** | Semantic versioning: `CO-vX.Y.Z-IB-vA.B.C` |
| **Database** | Shared PostgreSQL, separate schemas, coordinated migrations |
| **Startup** | IB initializes first, then CO (dependency order) |
| **Health Checks** | Combined health endpoint checking both systems |
| **Upgrades** | Atomic container replacement, rollback if either fails |

### Version Compatibility Matrix

```yaml
# Managed in: version-matrix.yaml
compatibility:
  cloud-optimizer: "2.0.0"
  intelligence-builder: "1.0.0"
  postgresql: ">=15.0"
  redis: ">=7.0"

# Tested combinations
tested_versions:
  - co: "2.0.0"
    ib: "1.0.0"
    status: "stable"
  - co: "2.1.0"
    ib: "1.0.0"
    status: "compatible"
```

### IB Platform Components in Bundle

The container includes these Intelligence-Builder components:

| Component | Purpose | Source |
|-----------|---------|--------|
| **Graph Backend** | PostgreSQL CTE-based graph storage | `ib_platform/graph/` |
| **Pattern Engine** | Pattern detection and matching | `ib_platform/patterns/` |
| **Domain System** | Pluggable domain modules | `ib_platform/domains/` |
| **Security Domain** | AWS security patterns | `ib_platform/domains/security/` |
| **Cost Domain** | AWS cost patterns | `ib_platform/domains/cost/` |
| **GraphRAG** | Graph-enhanced retrieval | `ib_platform/graphrag/` |

**IB Platform Database Schema:**
```sql
-- IB Schema (initialized first)
CREATE SCHEMA IF NOT EXISTS ib_platform;

-- Graph tables
CREATE TABLE ib_platform.graph_nodes (...);
CREATE TABLE ib_platform.graph_edges (...);

-- Pattern tables
CREATE TABLE ib_platform.patterns (...);
CREATE TABLE ib_platform.pattern_matches (...);

-- Domain tables
CREATE TABLE ib_platform.domains (...);
CREATE TABLE ib_platform.domain_entities (...);
```

### Container Product Advantages

| Advantage | Description |
|-----------|-------------|
| **Customer Data Stays in Customer Account** | Security-conscious customers keep their AWS data in their own VPC |
| **Trial-First Approach** | Free trial enables real-world feedback before full commitment |
| **Simpler Initial Architecture** | Single-tenant per container (no RLS complexity initially) |
| **AWS Marketplace Trust** | Customers trust AWS Marketplace billing and compliance |
| **Faster Time-to-Market** | Container packaging vs full SaaS infrastructure |

### Key Findings

| Metric | Value |
|--------|-------|
| **Total Requirements** | 221 |
| **Cloud Optimizer (CO) Owned** | 172 (78%) |
| **Intelligence-Builder (IB) Owned** | 49 (22%) |
| **Can Migrate Directly** | 45% (99 requirements) |
| **Needs Adaptation** | 44% (97 requirements) |
| **Needs New Development** | 11% (25 requirements) |
| **Original Timeline** | 52 weeks |
| **Revised Timeline** | 30 weeks |
| **Reduction** | 42% |

> See [REQUIREMENTS_OWNERSHIP.md](./REQUIREMENTS_OWNERSHIP.md) for detailed CO vs IB split.

---

## MVP Definition

### MVP Scope (Weeks 1-12)

The Minimum Viable Product focuses on **AWS Marketplace Container Product** with trial capability to gather real-world feedback:

#### MVP Must-Have Requirements (55 requirements)

| Category | Count | Priority | Migration Effort | Notes |
|----------|-------|----------|------------------|-------|
| Container Packaging (CNT-*) | 6 | P0 | NEW | Docker, Helm, CloudFormation |
| AWS Marketplace Container (MKT-*) | 5 | P0 | ADAPT | Container-specific metering |
| Trial Management (TRL-*) | 6 | P0 | ADAPT | Container license enforcement |
| User Management (USR-*) | 5 | P1 | LOW - Migrate | Single-tenant simplified |
| Security Scanning (SEC-*) | 12 | P0 | LOW - Migrate | Core value proposition |
| Cost Optimization (CST-*) | 9 | P0 | LOW - Migrate | Core value proposition |
| Monitoring (MON-*) | 7 | P1 | LOW - Migrate | Container health checks |
| Feature Flags (FLG-*) | 5 | P1 | LOW - Migrate | Tier-based features |

#### New Container-Specific Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| CNT-001 | Docker image packaging | Multi-stage Dockerfile, <500MB image, security scanning |
| CNT-002 | Helm chart | Configurable values, EKS/ECS deployment templates |
| CNT-003 | CloudFormation template | One-click deployment with RDS, VPC configuration |
| CNT-004 | Container health checks | Liveness/readiness probes, dependency checks |
| CNT-005 | Environment configuration | Secrets via AWS Secrets Manager, configmaps |
| CNT-006 | Upgrade mechanism | Zero-downtime updates, database migrations |

#### AWS Marketplace Container Integration

| ID | Requirement | Container-Specific Implementation |
|----|-------------|-----------------------------------|
| MKT-001 | License validation | `RegisterUsage` API call at container startup |
| MKT-002 | Usage metering | `MeterUsage` API with dimensions (scans, findings) |
| MKT-003 | Trial enforcement | 14-day trial, feature limits, expiration handling |
| MKT-004 | Entitlement check | Periodic entitlement validation (hourly) |
| MKT-005 | Subscription handling | Graceful degradation on subscription issues |

#### Trial-First Strategy

```yaml
Trial Configuration:
  duration: 14 days
  limits:
    aws_accounts: 1
    scans_per_day: 10
    findings_stored: 500
    users: 3
  features_enabled:
    - security_scanning
    - cost_analysis
    - basic_dashboard
  features_disabled:
    - advanced_analytics
    - custom_reports
    - api_access
    - multi-account

Conversion Path:
  1. Trial user discovers value
  2. AWS Marketplace subscription
  3. License key applied to container
  4. Full features unlocked
  5. Usage metering begins
```

#### MVP Success Criteria

1. **Container Deployment**
   - One-click deployment via CloudFormation
   - <10 minute setup time
   - Automated database initialization

2. **Trial Experience**
   - Immediate value demonstration
   - Clear trial limits and messaging
   - Smooth conversion to paid

3. **Core Value Delivery**
   - Security scanning with actionable findings
   - Cost optimization recommendations
   - Real-world customer feedback collection

4. **AWS Marketplace Compliance**
   - Container FTR (Fulfillment Technical Review) passed
   - Proper license validation
   - Accurate usage metering

5. **Quality Gates**
   - 80%+ test coverage
   - <500ms p95 API latency
   - Zero critical security vulnerabilities

### MVP Simplifications (Container Model)

| Original Requirement | MVP Approach | Deferred To |
|---------------------|--------------|-------------|
| Multi-Tenant RLS | Single-tenant per container | SaaS Phase |
| Cross-tenant admin | Not needed for container | SaaS Phase |
| Tenant provisioning | Container deployment = tenant | SaaS Phase |
| Complex RBAC | Owner/Admin/Viewer only | Phase 4 |
| API key management | Basic API keys | Phase 2 |

### MVP Exclusions (Deferred to Later Phases)

- **SaaS multi-tenant platform** (container-first approach)
- Frontend application (API + basic UI first)
- Multi-cloud support (AWS only for MVP)
- Advanced analytics and reporting
- SSO/SAML integration
- Knowledge graph UI
- Ontology builder
- Feedback loop system (manual collection initially)

---

## Phase Structure

### Phase 0: Foundation Setup (Week 1)

**Goal:** Container infrastructure and project setup

**Deliverables:**
- [ ] Development environment setup
- [ ] CI/CD pipeline for container builds (ECR, GitHub Actions)
- [ ] Base Docker image with Python/FastAPI
- [ ] Database schema migration scripts
- [ ] Test infrastructure (LocalStack, test containers)
- [ ] AWS Marketplace seller account setup

**Effort:** 1 week

---

### Phase 1: Container Product - MVP Foundation (Weeks 2-5)

**Goal:** Deployable container product with trial capability

**Focus:** Container packaging + core scanning capabilities

#### 1.1 Container Packaging - CO + IB Bundle (Week 2)

| Requirement | Action | Deliverable |
|-------------|--------|-------------|
| CNT-001 | NEW | Multi-stage Dockerfile bundling CO + IB |
| CNT-002 | NEW | Helm chart with configurable values |
| CNT-003 | NEW | CloudFormation template for one-click deploy |
| CNT-004 | ADAPT | Combined health checks (CO + IB) |
| CNT-005 | NEW | AWS Secrets Manager integration |
| CNT-006 | NEW | Coordinated database migrations (CO + IB schemas) |
| CNT-007 | NEW | Version compatibility validation on startup |

**Bundled Container Architecture:**
```python
# entrypoint.py - Coordinated startup
async def startup():
    # 1. Validate version compatibility
    validate_co_ib_compatibility()

    # 2. Run IB migrations first (graph schema)
    await run_ib_migrations()

    # 3. Run CO migrations (app schema)
    await run_co_migrations()

    # 4. Initialize IB Platform
    ib_platform = await initialize_ib_platform()

    # 5. Initialize CO with IB dependency
    co_app = create_co_app(ib_platform=ib_platform)

    # 6. Start combined health check
    start_health_monitor(co_app, ib_platform)

    return co_app
```

**New Files to Create:**
```
docker/
├── Dockerfile                    # Multi-stage: IB + CO bundle
├── Dockerfile.dev               # Development with hot reload
├── docker-compose.yml           # Local development (CO + IB + DB)
├── docker-compose.prod.yml      # Production-like testing
├── entrypoint.py                # Coordinated startup script
├── version-matrix.yaml          # CO + IB version compatibility
└── .dockerignore

helm/cloud-optimizer/
├── Chart.yaml                   # Includes IB as dependency
├── values.yaml
├── templates/
│   ├── deployment.yaml          # Single pod with CO + IB
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── migrations-job.yaml      # Init container for migrations
│   └── ingress.yaml
└── README.md

cloudformation/
├── cloud-optimizer-ecs.yaml     # ECS Fargate (CO + IB bundle)
├── cloud-optimizer-eks.yaml     # EKS deployment
├── cloud-optimizer-rds.yaml     # PostgreSQL RDS (both schemas)
└── parameters/
    ├── dev.json
    └── prod.json
```

**Dockerfile Structure:**
```dockerfile
# Stage 1: IB Platform build
FROM python:3.11-slim as ib-builder
COPY intelligence-builder/ /ib/
RUN pip install --no-cache-dir /ib/

# Stage 2: CO Application build
FROM python:3.11-slim as co-builder
COPY cloud-optimizer/ /co/
RUN pip install --no-cache-dir /co/

# Stage 3: Combined runtime
FROM python:3.11-slim as runtime
COPY --from=ib-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=co-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY entrypoint.py /app/
EXPOSE 8000
CMD ["python", "/app/entrypoint.py"]
```

**Effort:** 1.5 weeks (new development, critical path)

#### 1.2 AWS Marketplace Container Integration (Week 2-3)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| MKT-001 | `aws_marketplace_*.py` | Adapt for container `RegisterUsage` |
| MKT-002 | `aws_metering.py` | Adapt for container `MeterUsage` |
| MKT-003 | Trial enforcement | NEW - License file validation |
| MKT-004 | Entitlement check | Adapt for container context |
| MKT-005 | Subscription handling | Adapt for graceful degradation |

**Container-Specific Implementation:**
```python
# Startup license validation
class ContainerLicenseValidator:
    async def validate_on_startup(self):
        """Called when container starts."""
        try:
            response = await self.marketplace_client.register_usage(
                ProductCode=self.product_code,
                PublicKeyVersion=1
            )
            return LicenseStatus.VALID
        except CustomerNotEntitledException:
            return LicenseStatus.TRIAL
        except Exception:
            return LicenseStatus.EXPIRED
```

**Files to Migrate/Adapt:**
```
src/services/aws_metering.py → src/services/container_metering.py
src/services/license_validator.py (NEW)
src/api/middleware/license_check.py (NEW)
tests/test_container_license*.py (NEW)
```

**Effort:** 1 week (adaptation required)

#### 1.3 Trial Management - Container Edition (Week 3)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| TRL-001 | Trial service | Adapt for container |
| TRL-002 | Quota enforcement | Adapt - local enforcement |
| TRL-003 | Expiration handling | Adapt - graceful degradation |
| TRL-004 | Feature limits | Direct migrate |
| TRL-005 | Trial-to-paid | Adapt for Marketplace |
| TRL-006 | Trial UI messaging | NEW |

**Container Trial Implementation:**
```python
class ContainerTrialManager:
    """Manages trial state within container."""

    TRIAL_DURATION_DAYS = 14
    TRIAL_LIMITS = {
        "scans_per_day": 10,
        "findings_stored": 500,
        "users": 3,
        "aws_accounts": 1
    }

    async def check_trial_status(self) -> TrialStatus:
        """Check if container is in trial mode."""
        license_status = await self.license_validator.get_status()
        if license_status == LicenseStatus.VALID:
            return TrialStatus.CONVERTED

        # Check trial expiration
        trial_start = await self.get_trial_start_date()
        if (datetime.now() - trial_start).days > self.TRIAL_DURATION_DAYS:
            return TrialStatus.EXPIRED

        return TrialStatus.ACTIVE
```

**Files to Migrate/Adapt:**
```
src/services/trial_management.py → src/services/container_trial.py
src/api/middleware/trial_limits.py (NEW)
tests/test_container_trial*.py (NEW)
```

**Effort:** 0.5 weeks (adaptation required)

#### 1.4 User Management - Simplified (Week 3-4)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| USR-001 | `auth_abstraction/` | Migrate - simplified |
| USR-002 | User invitation | Migrate - local only |
| USR-003 | Basic roles | Migrate - Owner/Admin/Viewer |
| USR-004 | Profile management | Direct migrate |
| USR-005 | Password policies | Direct migrate |

**Simplified for Single-Tenant Container:**
- No cross-tenant user management
- Local user storage in PostgreSQL
- Basic role model (Owner, Admin, Viewer)
- Optional: LDAP/AD integration (Phase 4)

**Files to Migrate:**
```
src/api/routers/auth*.py (subset)
src/services/auth_abstraction/ (simplified)
src/models/user*.py (simplified)
tests/test_auth*.py (subset)
```

**Effort:** 0.5 weeks (existing: 95% complete, simplified)

#### 1.5 Basic UI Dashboard (Week 4-5)

**MVP requires a basic UI for trial users to see value immediately.**

| Requirement | Action | Deliverable |
|-------------|--------|-------------|
| UI-001 | NEW | Login/registration page |
| UI-002 | NEW | Dashboard overview (findings count, cost savings) |
| UI-003 | NEW | Security findings list with severity |
| UI-004 | NEW | Cost recommendations list |
| UI-005 | NEW | Trial status and upgrade prompt |
| UI-006 | NEW | Basic settings page |

**Technology Stack:**
- React 18 with TypeScript
- Tailwind CSS for styling
- React Query for API integration
- Minimal dependencies for fast load

**Files to Create:**
```
frontend/
├── src/
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Findings.tsx
│   │   ├── CostRecommendations.tsx
│   │   └── Settings.tsx
│   ├── components/
│   │   ├── TrialBanner.tsx
│   │   ├── FindingsTable.tsx
│   │   └── CostSavingsCard.tsx
│   └── api/
│       └── client.ts
├── Dockerfile
└── nginx.conf
```

**Effort:** 1 week (new development, minimal viable UI)

#### Phase 1 Summary

| Week | Deliverables | Effort |
|------|--------------|--------|
| 2 | Container packaging, Marketplace integration (start) | 1 week |
| 3 | Marketplace (complete), Trial management, User (start) | 1 week |
| 4 | User (complete), Basic UI (start) | 1 week |
| 5 | Basic UI (complete), Integration testing | 1 week |

**Phase 1 Total: 4 weeks**

**Key Milestone:** Deployable container with trial capability and basic UI

---

### Phase 2: Core Features - MVP Completion (Weeks 6-12)

**Goal:** Deliver core value proposition (security + cost optimization)

#### 2.1 Security Scanning (Weeks 6-7)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| SEC-001 | `security_analytics_orchestrator.py` | Direct migrate |
| SEC-002 | `security_anomaly_detector.py` | Direct migrate |
| SEC-003 | `compliance_service.py` | Direct migrate |
| SEC-004 | `compliance_reporting.py` | Direct migrate |
| SEC-005 | `behavioral_analytics_engine.py` | Direct migrate |
| SEC-006 | `recommendation_service.py` | Direct migrate |
| SEC-007 | `assessment_service.py` | Direct migrate |
| SEC-008 | `threshold_config_v2.py` | Direct migrate |
| SEC-009 | `batch_operations.py` | Direct migrate |
| SEC-010 | `document_service.py` | Direct migrate |
| SEC-011 | `batch_processing_service.py` | Direct migrate |
| SEC-012 | `tenant_configuration.py` | Direct migrate |

**Files to Migrate:**
```
src/services/security_analytics_orchestrator.py
src/services/behavioral_analytics_engine.py
src/services/security_anomaly_detector.py
src/services/compliance_service.py
src/api/routers/security_analysis.py
src/api/routers/compliance_reporting.py
src/services/recommendation_service.py
tests/test_security*.py (20 files)
```

**Effort:** 1.5 weeks (existing: 95% complete)

#### 2.2 Cost Optimization (Week 7-8)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| CST-001 | `cost_analytics.py` | Direct migrate |
| CST-002 | Cost service | Direct migrate |
| CST-003 | Recommendation engine | Direct migrate |
| CST-004 | RI analysis | Direct migrate |
| CST-005 | Savings plans | Direct migrate |
| CST-006 | Cost allocation | Direct migrate |
| CST-007 | Budget alerts | Direct migrate |
| CST-008 | Cost forecasting | Adapt |
| CST-009 | Cost reports | Direct migrate |

**Files to Migrate:**
```
src/services/cost_analytics.py
src/services/cost_optimization_service.py
src/api/routers/cost*.py (4 files)
src/services/recommendation_engine.py
tests/test_cost*.py (10 files)
```

**Effort:** 1.5 weeks (existing: 85% complete)

#### 2.3 Monitoring & Health (Week 8)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| MON-001 | `health.py` | Direct migrate |
| MON-002 | `health_failover_management.py` | Direct migrate |
| MON-003 | `monitoring.py` | Direct migrate |
| MON-004 | `automated_failover.py` | Adapt |
| MON-005 | `quota_alerts.py` | Direct migrate |
| MON-006 | `dashboard.py` | Direct migrate |
| MON-007 | `audit_log.py` | Direct migrate |

**Files to Migrate:**
```
src/api/routers/health*.py (4 files)
src/api/routers/monitoring*.py (6 files)
src/services/automated_failover.py
src/utils/monitoring.py
tests/test_health*.py (8 files)
```

**Effort:** 0.5 weeks (existing: 90% complete)

#### 2.4 Job Management (Week 9)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| JOB-001 | `batch_processing_service.py` | Direct migrate |
| JOB-002 | `job_models.py` | Direct migrate |
| JOB-003 | `job_manager.py` | Direct migrate |
| JOB-004 | `progress_tracker.py` | Direct migrate |
| JOB-005 | Retry logic | Direct migrate |
| JOB-006 | `dlq_monitoring.py` | Direct migrate |
| JOB-007 | `batch_operations.py` | Direct migrate |
| JOB-008 | `cross_epic_orchestrator.py` | Adapt |
| JOB-009 | Job models | Direct migrate |
| JOB-010 | Monitoring integration | Direct migrate |

**Files to Migrate:**
```
src/services/batch_processing_service.py
src/services/bulk_upload/job_manager.py
src/services/bulk_upload/progress_tracker.py
src/api/routers/dlq_monitoring.py
src/api/models/job_models.py
tests/test_job*.py (12 files)
```

**Effort:** 1 week (existing: 85% complete)

#### 2.5 Knowledge Graph (Week 9-10)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| KNG-001 to KNG-014 | `graphrag/` directory | Direct migrate |

**Files to Migrate:**
```
src/services/graphrag/ (35+ files)
src/api/routers/knowledge_graph.py
src/api/routers/knowledge_sharing.py
src/models/knowledge_base.py
src/services/semantic/ (entire directory)
tests/test_graphrag*.py (25 files)
```

**Effort:** 1 week (existing: 95% complete, 97.4% quality score)

#### 2.6 Hybrid Search (Week 10-11)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| SRH-001 to SRH-006 | GraphRAG orchestrator | Direct migrate |

**Files to Migrate:**
```
src/services/graphrag/orchestrator.py
src/services/graphrag/knowledge_graph_adapter.py
src/services/graphrag/cache/embedding_cache.py
src/api/routers/graphrag_query.py
tests/test_hybrid_search*.py (8 files)
```

**Effort:** 0.5 weeks (existing: 100% complete, 850ms response time)

#### 2.7 Document Management (Week 11)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| DOC-001 to DOC-008 | `documents_v2.py`, bulk upload | Direct migrate |

**Files to Migrate:**
```
src/api/routers/documents_v2.py
src/services/document_service.py
src/services/bulk_upload/ (entire directory)
src/contracts/document_contracts.py
tests/test_document*.py (15 files)
```

**Effort:** 0.5 weeks (existing: 95% complete)

#### 2.8 MVP Integration Testing (Week 12)

- End-to-end testing of all MVP features
- Performance testing and optimization
- Security audit
- Documentation finalization

**Effort:** 1 week

#### Phase 2 Summary

| Week | Deliverables | Effort |
|------|--------------|--------|
| 6-7 | Security Scanning | 1.5 weeks |
| 7-8 | Cost Optimization | 1.5 weeks |
| 8 | Monitoring & Health | 0.5 weeks |
| 9 | Job Management | 1 week |
| 9-10 | Knowledge Graph | 1 week |
| 10-11 | Hybrid Search | 0.5 weeks |
| 11 | Document Management | 0.5 weeks |
| 12 | MVP Integration Testing | 1 week |

**Phase 2 Total: 7 weeks** (vs 16 weeks original)
**Reduction: 56%**

---

### MVP Delivery Checkpoint (Week 12)

#### MVP Validation Criteria

- [ ] AWS Marketplace FTR (Fulfillment Technical Review) passed
- [ ] Multi-tenant isolation verified (security audit)
- [ ] Trial-to-paid conversion flow tested
- [ ] Security scanning producing valid findings
- [ ] Cost optimization recommendations accurate
- [ ] API documentation complete
- [ ] 80%+ test coverage achieved
- [ ] <500ms p95 latency verified

#### MVP Artifacts

1. **Deployed Services**
   - Cloud Optimizer API (FastAPI)
   - PostgreSQL with RLS
   - Redis for caching
   - Job queue processor

2. **Documentation**
   - API reference (OpenAPI)
   - Integration guide
   - Operations runbook

3. **Monitoring**
   - Health dashboards
   - Alerting rules
   - SLO tracking

---

### Phase 3: Frontend Application (Weeks 13-20)

**Goal:** User-facing application

#### 3.1 Frontend Foundation (Weeks 13-14)

| Requirement | Migration Action |
|-------------|------------------|
| FE-001 | Build new React app using existing designs |
| FE-002 | Component library setup |
| FE-003 | State management |
| FE-004 | API integration layer |

**Effort:** 2 weeks (designs exist from legacy)

#### 3.2 Core UI Pages (Weeks 15-17)

| Page | Requirements | Effort |
|------|--------------|--------|
| Dashboard | DSH-001 to DSH-006 | 1 week |
| Security Findings | SEC UI | 1 week |
| Cost Analysis | CST UI | 1 week |

**Effort:** 3 weeks

#### 3.3 Admin & Settings (Weeks 18-19)

| Page | Requirements | Effort |
|------|--------------|--------|
| User Management | USR UI | 0.5 weeks |
| Tenant Settings | TNT UI | 0.5 weeks |
| API Key Management | API UI | 0.5 weeks |
| Billing Portal | MKT UI | 0.5 weeks |

**Effort:** 2 weeks

#### 3.4 Frontend Testing & Polish (Week 20)

- E2E testing with Playwright
- Accessibility audit
- Performance optimization
- Cross-browser testing

**Effort:** 1 week

#### Phase 3 Summary

**Phase 3 Total: 8 weeks** (vs 10 weeks original)
**Reduction: 20%**

---

### Phase 4: Advanced Features (Weeks 21-26)

**Goal:** Differentiation and enterprise features

#### 4.1 NLU Enhancement (Week 21)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| NLU-001 to NLU-003 | `intent_analyzer.py` | Direct migrate |
| NLU-004 to NLU-006 | Query enhancement | Adapt |

**Files to Migrate:**
```
src/services/graphrag/intent_analyzer.py
src/services/graphrag/domain/classifier.py
src/services/graphrag/llm_service.py
```

**Effort:** 1.5 weeks (existing: 70%)

#### 4.2 Answer Generation Enhancement (Week 22)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| ANS-001 to ANS-008 | `answer_generator.py` | Adapt |

**Files to Migrate:**
```
src/services/graphrag/answer_generator.py
src/services/recommendation_service.py
src/services/graphrag/llm_router.py
```

**Effort:** 1 week (existing: 75%)

#### 4.3 SSO/SAML Integration (Week 22-23)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| SSO-001 to SSO-006 | Auth abstraction | Adapt |

**Files to Migrate:**
```
src/services/auth_abstraction/ (extend)
src/api/routers/sso*.py (create)
```

**Effort:** 1 week (existing: 80%)

#### 4.4 Advanced Analytics (Week 23-24)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| ANL-001 to ANL-006 | Analytics services | Direct migrate |

**Files to Migrate:**
```
src/services/cost_analytics.py
src/api/routers/cross_tenant_analytics.py
src/services/behavioral_analytics_engine.py
```

**Effort:** 1 week (existing: 85%)

#### 4.5 Audit & Compliance (Week 24)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| AUD-001 to AUD-007 | `audit_log.py` | Direct migrate |

**Files to Migrate:**
```
src/models/audit_log.py
src/api/routers/audit*.py
src/services/audit_service.py
```

**Effort:** 0.5 weeks (existing: 95%)

#### 4.6 Backup & DR (Week 25)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| BCK-001 to BCK-008 | Backup services | Adapt |

**Files to Migrate:**
```
src/api/routers/backup*.py
src/api/routers/replication*.py
src/services/backup_service.py
```

**Effort:** 1.5 weeks (existing: 70%)

#### 4.7 Notifications (Week 26)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| NTF-001 to NTF-005 | Notification services | Adapt |

**Files to Migrate:**
```
src/services/notification_service.py (create)
src/api/routers/notification*.py (create)
```

**Effort:** 0.5 weeks (existing: 70%)

#### Phase 4 Summary

**Phase 4 Total: 6 weeks** (vs 12 weeks original)
**Reduction: 50%**

---

### Phase 5: Post-MVP Features (Weeks 27-30)

**Goal:** Complete feature set and hardening

#### 5.1 Multi-Cloud Support (Weeks 27-28)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| CLD-001 to CLD-006 | CloudGuardian | Adapt |

**Files from CloudGuardian:**
```
CloudGuardian/src/skills/ (69 modules)
CloudGuardian/src/providers/
CloudGuardian/src/intelligence/
```

**Effort:** 2 weeks (existing: 60-85%)

#### 5.2 Feedback Loop (Week 28-29)

| Requirement | Migration Action |
|-------------|------------------|
| FBK-001 to FBK-007 | Build new with partial foundation |

**Effort:** 1.5 weeks (existing: 50-65%)

#### 5.3 Ontology Builder (Week 29-30)

| Requirement | Migration Action |
|-------------|------------------|
| ONT-001 to ONT-008 | Build new with partial foundation |

**Effort:** 1.5 weeks (existing: 40-60%)

#### Phase 5 Summary

**Phase 5 Total: 4 weeks** (buffer absorbed into features)

---

## Timeline Summary

| Phase | Scope | Weeks | Cumulative | Milestone |
|-------|-------|-------|------------|-----------|
| Phase 0 | Foundation Setup | 1 | Week 1 | CI/CD Ready |
| Phase 1 | Container Product (MVP Foundation) | 4 | Weeks 2-5 | Container Deployable |
| Phase 2 | Core Features (MVP Completion) | 7 | Weeks 6-12 | **MVP + Trial Launch** |
| Phase 3 | Enhanced Frontend | 8 | Weeks 13-20 | Full UI |
| Phase 4 | Advanced Features | 6 | Weeks 21-26 | Enterprise Features |
| Phase 5 | Post-MVP Features | 4 | Weeks 27-30 | Multi-Cloud |
| **Total** | | **30 weeks** | | |

### Timeline Comparison

| Phase | Original | Revised | Savings |
|-------|----------|---------|---------|
| Phase 1 | 10 weeks | 4 weeks | 6 weeks (60%) |
| Phase 2 | 16 weeks | 7 weeks | 9 weeks (56%) |
| Phase 3 | 10 weeks | 8 weeks | 2 weeks (20%) |
| Phase 4 | 12 weeks | 6 weeks | 6 weeks (50%) |
| Phase 5/Buffer | 4 weeks | 5 weeks | -1 week |
| **Total** | **52 weeks** | **30 weeks** | **22 weeks (42%)** |

---

## Future Roadmap: Container to SaaS Evolution

### Container Product First (MVP - Month 3)

```
Current Plan: AWS Marketplace Container Product
├── Customer deploys in their AWS account
├── Single-tenant per container
├── 14-day trial with conversion
├── Usage metering via Marketplace API
└── Real-world feedback collection
```

### SaaS Platform (Post-MVP - Month 6+)

Based on trial feedback and customer demand, evolve to multi-tenant SaaS:

```
Future: Managed SaaS Platform
├── Hosted multi-tenant service
├── Full RLS isolation (existing code ready)
├── Cross-tenant admin portal
├── Centralized billing
└── Higher margin, lower customer ops burden
```

### Evolution Path

| Stage | Model | Timeline | Trigger |
|-------|-------|----------|---------|
| MVP | Container Product | Week 12 | Initial launch |
| Growth | Container + Basic Support | Week 20 | 50+ trial users |
| Scale | Hybrid (Container + SaaS) | Week 30+ | Customer demand |
| Mature | Full SaaS | Month 9+ | 100+ paying customers |

**Key Advantage:** The multi-tenant infrastructure (TNT-*) from legacy Cloud_Optimizer is 95% ready and can be activated when needed for SaaS mode.

---

## Resource Requirements

### Team Composition

| Role | Phase 1-2 | Phase 3 | Phase 4-5 |
|------|-----------|---------|-----------|
| Backend Engineer | 2 | 1 | 2 |
| Frontend Engineer | 0 | 2 | 1 |
| DevOps/SRE | 0.5 | 0.5 | 0.5 |
| QA Engineer | 0.5 | 1 | 0.5 |
| **Total FTE** | **3** | **4.5** | **4** |

### Infrastructure

| Component | MVP | Full |
|-----------|-----|------|
| PostgreSQL | 1 instance | 2 (primary + replica) |
| Redis | 1 instance | 2 (cluster) |
| Application | 2 containers | 4+ (auto-scale) |
| Job Workers | 1 container | 2-4 containers |

---

## Risk Mitigation

### High-Risk Items

| Risk | Phase | Mitigation |
|------|-------|------------|
| Container FTR rejection | 1 | Early AWS engagement, use AWS container FTR guide |
| Trial not converting | 2 | Clear value demo, usage analytics, user interviews |
| Container deployment complexity | 1 | One-click CloudFormation, comprehensive docs |
| Performance issues | 2 | Early load testing, existing 850ms baseline |
| Low trial adoption | 2-3 | Marketing, AWS Marketplace visibility, SEO |
| Multi-cloud complexity | 5 | CloudGuardian abstraction layer |

### Container-Specific Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Customer can't deploy | MEDIUM | HIGH | CloudFormation template, detailed docs, support chat |
| Container resource sizing | LOW | MEDIUM | Documented recommendations, auto-scaling |
| Database configuration | MEDIUM | MEDIUM | RDS defaults, migration scripts |
| License bypass attempts | LOW | MEDIUM | Server-side validation, usage metering |

### Contingency Plans

| Scenario | Action |
|----------|--------|
| Container FTR failure | 2-week buffer, AWS partner escalation |
| Low trial conversion | Extend trial, add features, user research |
| Deployment issues | Managed deployment service option |
| Resource constraints | Reduce Phase 5 scope, focus on core value |

---

## Appendix: Migration File Reference

### Phase 1 Files (45+ files)

```
AWS Marketplace:
  src/api/routers/aws_marketplace_*.py (6)
  src/services/aws_marketplace_*.py (5)
  src/services/aws_metering.py

Multi-Tenant:
  src/api/middleware/tenant*.py (5)
  src/models/tenant*.py (3)
  src/api/routers/tenants_contracts.py

Auth & Users:
  src/api/routers/auth*.py (8)
  src/api/middleware/rbac*.py (4)
  src/services/auth_abstraction/ (all)

API Keys:
  src/api/routers/api_key*.py (2)
  src/api/middleware/rate_limit.py
```

### Phase 2 Files (120+ files)

```
Security:
  src/services/security_*.py (5)
  src/api/routers/security_analysis.py
  src/api/routers/compliance_reporting.py

Cost:
  src/services/cost_*.py (3)
  src/api/routers/cost*.py (4)

Knowledge Graph:
  src/services/graphrag/ (35+)
  src/services/semantic/ (all)

Jobs:
  src/services/batch_processing_service.py
  src/services/bulk_upload/ (all)
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-30 | Initial phased implementation plan with MVP definition |
