# Cloud Optimizer v2 - Phased Implementation Plan

**Version:** 2.0
**Date:** 2025-12-01
**Status:** MVP Scope Finalized

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
| **MVP Requirements** | 99 (45%) |
| **MVP - Cloud Optimizer (CO)** | 65 |
| **MVP - Intelligence-Builder (IB)** | 34 |
| **Post-MVP Requirements** | 122 (55%) |
| **Timeline** | 30 weeks |
| **MVP Delivery** | Week 12 |

### MVP Core Capabilities

| Capability | Requirements | Priority |
|------------|--------------|----------|
| **Security Chat Q&A** | NLU-*, ANS-*, UI-002 | P0 - Differentiator |
| **Document Analysis** | DOC-*, UI-003 | P0 - Differentiator |
| **AWS Scanning** | SEC-* | P0 - Core Value |
| **Compliance KB** | KNG-*, SRH-* | P0 - Foundation |
| **Container Deployment** | CNT-*, MKT-*, TRL-* | P0 - Delivery |

> See [REQUIREMENTS_OWNERSHIP.md](./REQUIREMENTS_OWNERSHIP.md) for detailed CO vs IB split.

---

## MVP Definition

### MVP Value Proposition

**"AI-powered security advisor that understands your AWS architecture"**

Cloud Optimizer MVP delivers an intelligent security assistant that:
1. Answers natural language questions about AWS security
2. Analyzes uploaded architecture documents
3. Scans AWS accounts for real vulnerabilities
4. Provides compliance-aware recommendations (HIPAA, SOC2, PCI-DSS, GDPR, CIS)

### MVP Use Cases

#### Use Case 1: Security Q&A Chat

```
User: "I have patient data loaded to S3 then ingested via Glue into
       Redshift and use Power BI for reporting, what should I be
       concerned about security-wise?"

System: Based on your architecture involving PHI data, here are the
        key security concerns:

        🔴 HIGH PRIORITY - HIPAA Compliance:
        1. S3 Bucket Encryption - Ensure SSE-KMS for PHI at rest
        2. Glue Job IAM Roles - Principle of least privilege
        3. Redshift encryption - Enable cluster encryption
        4. Data in transit - Verify TLS everywhere

        🟡 MEDIUM PRIORITY:
        5. Power BI connection - Use private endpoints
        6. VPC configuration - Isolate data pipeline
        7. CloudTrail logging - Audit all PHI access

        📋 Compliance Mapping:
        - HIPAA §164.312(a)(1): Access controls
        - HIPAA §164.312(e)(1): Transmission security

        Would you like me to scan your AWS account to verify these?
```

#### Use Case 2: Architecture Document Analysis

```
User: [Uploads architecture-diagram.pdf]
      "What security improvements do you recommend?"

System: I've analyzed your architecture document. Found:
        - 3 S3 buckets (2 public-facing)
        - 1 RDS instance (MySQL)
        - 2 Lambda functions
        - 1 API Gateway

        🔴 Critical Findings:
        1. Public S3 bucket "data-exports" - should be private
        2. RDS not in private subnet
        3. API Gateway missing WAF

        📄 Full report: [Download PDF]
```

### MVP Scope (Weeks 1-12)

The Minimum Viable Product focuses on **AWS Marketplace Container Product** with AI-powered security Q&A:

#### MVP Requirements Summary (99 requirements)

| Owner | Category | Count | Priority | Notes |
|-------|----------|-------|----------|-------|
| **CO** | Container Packaging (CNT-*) | 6 | P0 | Docker, Helm, CloudFormation |
| **CO** | AWS Marketplace (MKT-*) | 5 | P0 | License, metering |
| **CO** | Trial Management (TRL-*) | 6 | P0 | 14-day trial |
| **CO** | Basic Auth (USR-*) | 3 | P0 | Single admin, email/password |
| **CO** | Chat + Dashboard UI (UI-*) | 10 | P0 | **Chat interface + dashboard** |
| **CO** | Security Scanning (SEC-*) | 12 | P0 | AWS account scanning |
| **CO** | Cost Optimization (CST-*) | 5 | P1 | Basic cost analysis |
| **CO** | Document Processing (DOC-*) | 5 | P0 | **PDF upload + parsing** |
| **CO** | Job Management (JOB-*) | 5 | P1 | Background processing |
| **CO** | Minimal Monitoring (MON-*) | 2 | P1 | Health endpoints only |
| **CO** | Feature Flags (FLG-*) | 6 | P1 | Tier-based features |
| **IB** | Knowledge Ingestion (KNG-*) | 14 | P0 | **Compliance frameworks** |
| **IB** | Hybrid Search (SRH-*) | 6 | P0 | Vector + graph search |
| **IB** | NLU Pipeline (NLU-*) | 6 | P0 | **Question understanding** |
| **IB** | Answer Generation (ANS-*) | 8 | P0 | **Recommendations** |
| | **CO Total** | **65** | | |
| | **IB Total** | **34** | | |
| | **MVP Total** | **99** | | |

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

#### Compliance Knowledge Base (MVP)

The Expert System requires comprehensive compliance knowledge:

| Framework | Content | Ingestion Source | Priority |
|-----------|---------|------------------|----------|
| **HIPAA** | PHI handling, encryption, access controls, audit | HHS Guidelines | P0 |
| **SOC 2** | Trust service criteria (security, availability) | AICPA | P0 |
| **PCI-DSS** | Cardholder data, network security, monitoring | PCI Council | P0 |
| **GDPR** | Data privacy, consent, retention, DPO | EU Regulations | P0 |
| **CIS Benchmarks** | AWS hardening (200+ controls) | CIS Downloads | P0 |
| **NIST 800-53** | Security controls catalog | NIST CSF | P1 |
| **AWS Well-Architected** | Security pillar best practices | AWS Docs | P0 |
| **AWS Security Best Practices** | Service-specific guidance | AWS Docs | P0 |

#### Trial-First Strategy

```yaml
Trial Configuration:
  duration: 14 days
  limits:
    aws_accounts: 1
    chat_questions_per_day: 50
    document_uploads: 10
    scans_per_day: 5
    findings_stored: 500
    users: 1  # Single admin for trial
  features_enabled:
    - security_chat_qa           # Core differentiator
    - document_analysis          # Core differentiator
    - security_scanning
    - cost_analysis_basic
    - compliance_recommendations
  features_disabled:
    - advanced_analytics
    - custom_reports
    - api_access
    - multi-account
    - scheduled_scans

Conversion Path:
  1. Trial user asks security questions (immediate value)
  2. Uploads architecture doc for analysis
  3. Connects AWS account for real findings
  4. Sees value in recommendations
  5. AWS Marketplace subscription
  6. Full features unlocked
```

#### MVP Success Criteria

1. **Container Deployment**
   - One-click deployment via CloudFormation
   - <10 minute setup time
   - Automated database initialization

2. **Security Q&A Experience** (Primary Differentiator)
   - User asks security question, gets expert-level answer in <3 seconds
   - Answers include compliance mapping (HIPAA, SOC2, etc.)
   - Recommendations are actionable with specific AWS guidance

3. **Document Analysis**
   - Upload PDF architecture document
   - Extract entities (S3, RDS, Lambda, etc.)
   - Generate security recommendations within 30 seconds

4. **AWS Scanning Integration**
   - Connect AWS account via IAM role
   - Scan completes in <60 seconds for typical account
   - Findings linked to knowledge base recommendations

5. **Trial Experience**
   - Immediate value in first 5 minutes (ask a question, get an answer)
   - Clear trial limits and upgrade path
   - Smooth conversion to paid

6. **AWS Marketplace Compliance**
   - Container FTR (Fulfillment Technical Review) passed
   - Proper license validation
   - Accurate usage metering

7. **Quality Gates**
   - 80%+ test coverage
   - <500ms p95 API latency (chat responses <3s)
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

#### 1.5 Chat Interface + Dashboard UI (Week 4-5)

**MVP requires a chat-first UI that delivers immediate value to trial users.**

| Requirement | Action | Deliverable |
|-------------|--------|-------------|
| UI-001 | NEW | Login/registration page |
| UI-002 | NEW | **Security Chat Interface** (primary experience) |
| UI-003 | NEW | Document upload with analysis results |
| UI-004 | NEW | AWS account connection wizard |
| UI-005 | NEW | Dashboard overview (findings, compliance status) |
| UI-006 | NEW | Security findings list with severity |
| UI-007 | NEW | Cost recommendations list |
| UI-008 | NEW | Compliance status by framework (HIPAA, SOC2, etc.) |
| UI-009 | NEW | Trial status and upgrade prompt |
| UI-010 | NEW | Basic settings page |

**Technology Stack:**
- React 18 with TypeScript
- Tailwind CSS for styling
- React Query for API integration
- Streaming responses for chat (SSE or WebSocket)
- PDF.js for document preview

**Chat Interface Design:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Cloud Optimizer                    [Trial: 12 days left] [⚙️]  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Ask me about AWS security...                            │    │
│  │                                                          │    │
│  │  💬 "I have patient data in S3, what should I check?"   │    │
│  │                                                          │    │
│  │  🤖 Based on your description involving PHI data:       │    │
│  │                                                          │    │
│  │     🔴 HIGH PRIORITY - HIPAA Compliance:                │    │
│  │     1. S3 Bucket Encryption - Ensure SSE-KMS            │    │
│  │     2. Access Logging - Enable CloudTrail               │    │
│  │                                                          │    │
│  │     📋 Compliance: HIPAA §164.312(a)(1)                 │    │
│  │                                                          │    │
│  │     [Connect AWS Account to Verify]                      │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Type your question...                    [📎] [Send]   │    │
│  └─────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│  [💬 Chat] [📄 Documents] [🔍 Scan Results] [💰 Cost] [⚡ Quick]│
└─────────────────────────────────────────────────────────────────┘
```

**Files to Create:**
```
frontend/
├── src/
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Chat.tsx              # Primary experience
│   │   ├── Documents.tsx         # Upload + analysis
│   │   ├── AWSConnect.tsx        # Account connection
│   │   ├── Dashboard.tsx         # Overview
│   │   ├── Findings.tsx
│   │   ├── Compliance.tsx        # Framework status
│   │   ├── CostAnalysis.tsx
│   │   └── Settings.tsx
│   ├── components/
│   │   ├── ChatMessage.tsx
│   │   ├── ChatInput.tsx
│   │   ├── DocumentUpload.tsx
│   │   ├── ComplianceBadge.tsx
│   │   ├── TrialBanner.tsx
│   │   ├── FindingsTable.tsx
│   │   └── CostSavingsCard.tsx
│   └── api/
│       ├── client.ts
│       └── streaming.ts          # SSE for chat
├── Dockerfile
└── nginx.conf
```

**Effort:** 1.5 weeks (chat interface adds complexity)

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

#### 2.5 Knowledge Graph + Compliance KB (Week 9-10)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| KNG-001 to KNG-014 | `graphrag/` directory | Direct migrate + extend |

**Compliance Knowledge Ingestion (NEW):**
```python
# Compliance frameworks to ingest for MVP
COMPLIANCE_SOURCES = {
    "hipaa": {
        "source": "HHS Guidelines",
        "entities": ["PHI", "BAA", "encryption", "access_control"],
        "controls": 45,
    },
    "soc2": {
        "source": "AICPA Trust Services",
        "entities": ["security", "availability", "confidentiality"],
        "controls": 64,
    },
    "pci_dss": {
        "source": "PCI Security Council",
        "entities": ["cardholder_data", "network_security"],
        "controls": 250,
    },
    "gdpr": {
        "source": "EU Regulations",
        "entities": ["personal_data", "consent", "dpo"],
        "controls": 99,
    },
    "cis_aws": {
        "source": "CIS Benchmark v2.0",
        "entities": ["iam", "logging", "monitoring", "networking"],
        "controls": 200,
    },
}
```

**Files to Migrate + Create:**
```
src/services/graphrag/ (35+ files)
src/api/routers/knowledge_graph.py
src/models/knowledge_base.py
src/services/semantic/ (entire directory)
NEW: src/ib_platform/ingestion/sources/hipaa.py
NEW: src/ib_platform/ingestion/sources/soc2.py
NEW: src/ib_platform/ingestion/sources/pci_dss.py
NEW: src/ib_platform/ingestion/sources/gdpr.py
NEW: src/ib_platform/ingestion/sources/cis_aws.py
tests/test_graphrag*.py (25 files)
```

**Effort:** 1.5 weeks (existing: 95% + compliance ingestion)

#### 2.6 Hybrid Search (Week 10)

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

#### 2.7 NLU Pipeline (Week 10-11) - **NEW IN MVP**

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| NLU-001 | Intent classification | Direct migrate from `intent_analyzer.py` |
| NLU-002 | Domain classification | Direct migrate |
| NLU-003 | Entity extraction | Direct migrate |
| NLU-004 | Query reformulation | Adapt |
| NLU-005 | Temporal understanding | Adapt |
| NLU-006 | Query decomposition | Adapt |

**NLU for Security Q&A:**
```python
# Example query parsing
query = "I have patient data in S3, what should I check for HIPAA?"

parsed = {
    "intent": "security_assessment",
    "domain": "compliance",
    "entities": [
        {"type": "data_type", "value": "patient_data", "compliance": "hipaa"},
        {"type": "aws_service", "value": "S3"},
        {"type": "framework", "value": "HIPAA"},
    ],
    "focus": "data_protection",
}
```

**Files to Migrate:**
```
src/services/graphrag/intent_analyzer.py
src/services/graphrag/domain/classifier.py
NEW: src/ib_platform/nlu/security_intent.py
NEW: src/ib_platform/nlu/compliance_extractor.py
tests/test_nlu*.py
```

**Effort:** 1 week (existing: 70% + security-specific)

#### 2.8 Answer Generation (Week 11) - **NEW IN MVP**

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| ANS-001 | Multi-source synthesis | Direct migrate |
| ANS-002 | Confidence scoring | Direct migrate |
| ANS-003 | Alternative interpretations | Adapt |
| ANS-004 | Ranked recommendations | Direct migrate |
| ANS-005 | Remediation steps | Direct migrate |
| ANS-006 | Evidence chains | Adapt |
| ANS-007 | Answer formatting | Direct migrate |
| ANS-008 | Cross-domain insights | Adapt |

**Answer Format for Security Q&A:**
```python
# Example generated answer
answer = {
    "summary": "Based on your architecture with PHI in S3...",
    "findings": [
        {
            "severity": "high",
            "category": "encryption",
            "title": "S3 Bucket Encryption",
            "description": "Ensure SSE-KMS for PHI at rest",
            "compliance": ["HIPAA §164.312(a)(2)(iv)"],
            "remediation": "aws s3api put-bucket-encryption...",
        },
    ],
    "compliance_mapping": {
        "HIPAA": {"covered": 3, "gaps": 2},
        "SOC2": {"covered": 5, "gaps": 1},
    },
    "confidence": 0.92,
    "sources": ["CIS AWS Benchmark", "AWS Security Best Practices"],
}
```

**Files to Migrate:**
```
src/services/graphrag/answer_generator.py
src/services/recommendation_service.py
NEW: src/ib_platform/generation/compliance_formatter.py
NEW: src/ib_platform/generation/remediation_generator.py
tests/test_answer*.py
```

**Effort:** 1 week (existing: 75% + compliance formatting)

#### 2.9 Document Processing (Week 11-12) - **ADDED BACK**

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| DOC-001 | Document upload | Direct migrate |
| DOC-002 | PDF extraction | Adapt - add PDF parsing |
| DOC-003 | Entity extraction from docs | NEW |
| DOC-004 | Architecture analysis | NEW |
| DOC-005 | Document storage | Direct migrate |

**PDF Architecture Analysis:**
```python
# Example document processing
async def analyze_architecture_document(pdf_file: UploadFile) -> AnalysisResult:
    # 1. Extract text from PDF
    text = await extract_pdf_text(pdf_file)

    # 2. Extract AWS entities
    entities = await nlu.extract_entities(text)
    # Found: ["S3:data-bucket", "RDS:mysql", "Lambda:processor"]

    # 3. Infer relationships
    relationships = await infer_architecture(entities)
    # Found: S3 -> Lambda -> RDS data flow

    # 4. Generate security recommendations
    recommendations = await answer_gen.analyze_architecture(
        entities=entities,
        relationships=relationships,
        compliance_frameworks=["HIPAA", "SOC2"],
    )

    return AnalysisResult(
        entities=entities,
        recommendations=recommendations,
        compliance_gaps=recommendations.gaps,
    )
```

**Files to Migrate + Create:**
```
src/api/routers/documents_v2.py
src/services/document_service.py
NEW: src/services/pdf_extractor.py (PyMuPDF or pdfplumber)
NEW: src/services/architecture_analyzer.py
tests/test_document*.py (15 files)
```

**Effort:** 1 week (existing: 60% + PDF + architecture analysis)

#### 2.10 MVP Integration Testing (Week 12)

- End-to-end testing of Security Q&A flow
- Document upload → analysis → recommendations flow
- AWS scan → findings → compliance mapping flow
- Performance testing (chat <3s response)
- Security audit
- Documentation finalization

**Effort:** 1 week

#### Phase 2 Summary

| Week | Deliverables | Owner | Effort |
|------|--------------|-------|--------|
| 6-7 | Security Scanning | CO | 1.5 weeks |
| 7-8 | Cost Optimization | CO | 1 week |
| 8 | Monitoring & Health | CO | 0.5 weeks |
| 9 | Job Management | CO | 1 week |
| 9-10 | Knowledge Graph + Compliance KB | IB | 1.5 weeks |
| 10 | Hybrid Search | IB | 0.5 weeks |
| 10-11 | **NLU Pipeline** | IB | 1 week |
| 11 | **Answer Generation** | IB | 1 week |
| 11-12 | **Document Processing** | CO | 1 week |
| 12 | MVP Integration Testing | Both | 1 week |

**Phase 2 Total: 7 weeks**
**CO Work: 5 weeks**
**IB Work: 4 weeks** (parallelized with CO)

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

**Goal:** Enterprise features and enhanced user management

> **Note:** NLU-* and ANS-* moved to MVP Phase 2 to support Security Q&A use case.

#### 4.1 Multi-User Support (Week 21)

| Requirement | Source | Migration Action |
|-------------|--------|------------------|
| USR-002 | User invitation | Migrate from auth_abstraction |
| USR-003 | User roles (Owner/Admin/Viewer) | Migrate |
| USR-005 | MFA support | Adapt |
| USR-006 | Session management | Migrate |

**Effort:** 1 week (deferred from MVP for simplicity)

#### 4.2 SSO/SAML Integration (Week 21-22)

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
| Phase 1 | Container + Chat UI (MVP Foundation) | 5 | Weeks 2-6 | Container + Chat Deployable |
| Phase 2 | Expert System (MVP Completion) | 6 | Weeks 7-12 | **MVP: Security Q&A Launch** |
| Phase 3 | Enhanced Frontend | 8 | Weeks 13-20 | Full UI Polish |
| Phase 4 | Enterprise Features | 6 | Weeks 21-26 | Multi-User, SSO, Analytics |
| Phase 5 | Post-MVP Features | 4 | Weeks 27-30 | Multi-Cloud, Feedback |
| **Total** | | **30 weeks** | | |

### MVP Milestone (Week 12)

**Delivered Capabilities:**
- Security Chat Q&A with compliance mapping
- Architecture document analysis (PDF)
- AWS account scanning with recommendations
- Knowledge base: HIPAA, SOC2, PCI-DSS, GDPR, CIS
- Trial-first container deployment

**Key Metrics:**
- 99 requirements (65 CO + 34 IB)
- Chat response time: <3 seconds
- Document analysis: <30 seconds
- AWS scan: <60 seconds

### Timeline Comparison

| Phase | Original | Revised | Notes |
|-------|----------|---------|-------|
| Phase 1 | 4 weeks | 5 weeks | +1 week for Chat UI |
| Phase 2 | 7 weeks | 6 weeks | Optimized with NLU/ANS parallel work |
| Phase 3 | 8 weeks | 8 weeks | Same - UI polish |
| Phase 4 | 6 weeks | 6 weeks | Reduced scope (NLU/ANS moved to MVP) |
| Phase 5 | 4 weeks | 4 weeks | Same |
| **Total** | **30 weeks** | **30 weeks** | Timeline maintained |

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
| 2.0 | 2025-12-01 | **MVP scope finalized** based on use cases: Security Chat Q&A, Document Analysis. Added NLU-*, ANS-* to MVP. Expanded UI for chat interface. Added compliance KB (HIPAA, SOC2, PCI-DSS, GDPR, CIS). |
| 1.2 | 2025-11-30 | Added CO+IB bundle architecture, container deployment model |
| 1.0 | 2025-11-30 | Initial phased implementation plan with MVP definition |
