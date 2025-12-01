# Cloud Optimizer v2 - Detailed Requirements

**Version:** 2.6
**Date:** 2025-11-30
**Status:** Approved - Ready for Implementation (MVP Week 12)

---

## 1. Executive Summary

Cloud Optimizer v2 is a clean-slate rebuild that leverages Intelligence-Builder (IB) as its intelligence platform while implementing business-critical features for AWS cloud optimization and SaaS monetization.

### Design Principles
1. **Clean & Simple** - Maximum 10K lines of application code
2. **IB-First** - All intelligence operations through IB SDK
3. **Contract-Driven** - Type-safe interfaces between all components
4. **Multi-Tenant Native** - Tenant isolation from day one
5. **Extensible** - Plugin architecture for domains and scanners

### Success Metrics
- 80%+ test coverage
- <500ms p95 API latency
- Zero SQL injection vulnerabilities
- 100% type hint coverage

---

## 2. Timeline & Risk Assessment

### Revised Timeline (Based on Implementation Readiness)

Based on comprehensive analysis of legacy Cloud_Optimizer (~125K LOC) and CloudGuardian (~45K LOC), the timeline has been **reduced by 42%** due to existing implementation that can be migrated.

| Phase | Scope | Duration | Start | End |
|-------|-------|----------|-------|-----|
| **Phase 0** | Foundation Setup | 1 week | Week 1 | Week 1 |
| **Phase 1** | Core Platform (MVP Foundation) | 4 weeks | Week 2 | Week 5 |
| **Phase 2** | Core Features (MVP Completion) | 7 weeks | Week 6 | Week 12 |
| **MVP Delivery** | | | **Week 12** | |
| **Phase 3** | Frontend Application | 8 weeks | Week 13 | Week 20 |
| **Phase 4** | Advanced Features (SSO, Analytics, Audit) | 6 weeks | Week 21 | Week 26 |
| **Phase 5** | Post-MVP (Multi-Cloud, Feedback, Ontology) | 4 weeks | Week 27 | Week 30 |

**Total: 30 weeks (7.5 months)** - Reduced from 52 weeks (42% savings)

> **Note:** Timeline reduction achieved because 70%+ of requirements have existing implementation:
> - 45% can be migrated directly (99 requirements)
> - 44% need minimal adaptation (97 requirements)
> - 11% require new development (25 requirements)
>
> See [PHASED_IMPLEMENTATION_PLAN.md](./PHASED_IMPLEMENTATION_PLAN.md) for detailed breakdown.
> See [IMPLEMENTATION_READINESS_MATRIX.md](./IMPLEMENTATION_READINESS_MATRIX.md) for migration mapping.

### Phase Dependencies

```
Phase 1: Core Platform
    ├── IB Platform components (prerequisite - already complete)
    ├── PostgreSQL + Redis infrastructure
    └── AWS credentials for testing

Phase 2: Feature Parity
    ├── Phase 1 complete (auth, tenant context)
    ├── AWS Cost Explorer API access
    └── IB Domain modules

Phase 3: Frontend
    ├── Phase 2 APIs complete and stable
    ├── Design mockups approved
    └── API documentation finalized

Phase 4: Advanced
    ├── Phase 3 complete
    ├── SSO provider sandbox accounts
    └── Compliance requirements clarified
```

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| IB SDK integration delays | MEDIUM | HIGH | Define contract upfront, build mock SDK |
| AWS Marketplace FTR rejection | MEDIUM | CRITICAL | Follow FTR checklist, test early with AWS |
| Multi-tenant data leak | LOW | CRITICAL | RLS policies, integration tests, security audit |
| Frontend scope creep | HIGH | MEDIUM | Lock mockups before Phase 3, define MVP |
| Performance issues at scale | MEDIUM | HIGH | Load test early, establish baselines |
| Team unavailability | MEDIUM | MEDIUM | Document thoroughly, pair programming |

---

## 3. Phase 1: Core Platform (Weeks 1-8)

### 3.1 AWS Marketplace Integration

**Priority:** P0 (Business-Critical)
**Effort:** 3 weeks
**Dependencies:** AWS Marketplace seller account, SNS topic for notifications

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| MKT-001 | Entitlement verification | Verify customer entitlements via AWS Marketplace API on every authenticated request |
| MKT-002 | Usage metering | Submit hourly usage records to AWS Marketplace Metering API |
| MKT-003 | Customer registration | Auto-create tenant on first Marketplace customer login |
| MKT-004 | Subscription management | Handle subscription create, update, cancel webhooks |
| MKT-005 | Billing portal | Redirect to AWS Marketplace billing management |

#### AWS Marketplace Technical Specification

##### Fulfillment Technical Review (FTR) Checklist

| Requirement | Implementation |
|-------------|----------------|
| **Registration Flow** | POST to registration URL with `x-amzn-marketplace-token` |
| **Token Resolution** | Call `ResolveCustomer` API with registration token |
| **Entitlement Check** | Call `GetEntitlements` API on each authenticated request |
| **Usage Metering** | `BatchMeterUsage` API with dimension records |
| **SNS Notifications** | Subscribe to `aws-mp-subscription-notification` topic |

##### SNS Notification Handling

```yaml
Notification Types:
  subscribe-success:
    action: Create tenant, activate subscription
    data: customerId, productCode, entitlements

  subscribe-fail:
    action: Log error, notify admin
    data: customerId, errorMessage

  unsubscribe-pending:
    action: Mark subscription for cancellation
    data: customerId, effectiveDate

  unsubscribe-success:
    action: Deactivate tenant, archive data
    data: customerId
```

##### Usage Metering Dimensions

| Dimension | Unit | Description | Metering Frequency |
|-----------|------|-------------|-------------------|
| `api_calls` | Count | API requests (excluding health checks) | Hourly |
| `scans` | Count | Security/cost scan executions | Hourly |
| `active_users` | Count | Unique users in billing period | Daily |
| `findings` | Count | Active findings in system | Daily |

##### Metering Error Handling

```yaml
Retry Policy:
  max_retries: 3
  backoff: exponential (1s, 2s, 4s)
  dead_letter: Store in DB, retry in next batch

Grace Period:
  metering_delay: 15 minutes (aggregate before submit)
  late_submission: Up to 6 hours allowed by AWS

Reconciliation:
  daily_job: Compare local usage with AWS records
  alert_threshold: >5% discrepancy
```

#### Data Model

```yaml
MarketplaceCustomer:
  customer_id: str (AWS Marketplace customer ID)
  tenant_id: str (FK to Tenant)
  product_code: str
  entitlement_status: enum (ACTIVE, EXPIRED, CANCELLED)
  subscription_type: enum (MONTHLY, ANNUAL, METERED)
  entitlements: jsonb  # {"tier": "professional", "features": [...]}
  created_at: datetime
  updated_at: datetime

UsageRecord:
  record_id: str (UUID)
  customer_id: str (FK)
  dimension: str (e.g., "api_calls", "scans", "users")
  quantity: int
  timestamp: datetime
  submitted: bool
  submission_id: str (optional, AWS response)
  submission_error: str (optional)
  retry_count: int (default 0)

UsageBatch:
  batch_id: str (UUID)
  customer_id: str (FK)
  records: list[UsageRecord IDs]
  status: enum (PENDING, SUBMITTED, CONFIRMED, FAILED)
  submitted_at: datetime (nullable)
  aws_response: jsonb (nullable)
```

#### API Endpoints

```yaml
POST /api/v1/marketplace/register:
  description: Register new Marketplace customer (called by AWS)
  headers:
    x-amzn-marketplace-token: string (required)
  response:
    redirect_url: string (to application dashboard)
  errors:
    400: Invalid token
    409: Customer already registered

POST /api/v1/marketplace/webhook:
  description: Handle Marketplace SNS notifications
  auth: AWS signature verification (HMAC-SHA256)
  body:
    Type: "Notification"
    Message: JSON string with subscription event
  response: 200 OK (always, to acknowledge receipt)

GET /api/v1/marketplace/entitlement:
  description: Check current entitlement status
  auth: JWT (tenant context)
  response:
    customer_id: string
    product_code: string
    entitlements: object
    status: "ACTIVE" | "EXPIRED" | "GRACE_PERIOD"
    features: list[string]

GET /api/v1/marketplace/usage:
  description: Get usage summary for current billing period
  auth: JWT (tenant context)
  query:
    period: "current" | "previous" | ISO date range
  response:
    period_start: datetime
    period_end: datetime
    usage_by_dimension: object
    estimated_charges: float (optional, if available)
```

---

### 3.2 Multi-Tenant Architecture

**Priority:** P0 (Business-Critical)
**Effort:** 3 weeks
**Dependencies:** PostgreSQL with RLS support

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| TNT-001 | Tenant isolation | All data queries filtered by tenant_id via RLS |
| TNT-002 | Tenant provisioning | Create tenant with default configuration on registration |
| TNT-003 | Tenant configuration | Per-tenant feature flags and settings |
| TNT-004 | Tenant quotas | Enforce API rate limits and resource quotas per tenant |
| TNT-005 | Tenant context | Inject tenant_id into all IB SDK calls |
| TNT-006 | Tenant suspension | Suspend tenant access while preserving data |
| TNT-007 | Tenant deletion | Soft delete with 30-day recovery period |
| TNT-008 | Tenant data export | Export all tenant data in standard format |
| TNT-009 | Cross-tenant admin | Platform admins can view/manage all tenants |

#### Tenant Lifecycle Management

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PENDING    │────▶│    ACTIVE    │────▶│  SUSPENDED   │
│  (created)   │     │  (verified)  │     │ (grace period│
└──────────────┘     └──────────────┘     └──────────────┘
                            │                    │
                            │                    ▼
                            │            ┌──────────────┐
                            │            │   DELETED    │
                            └───────────▶│ (30-day hold)│
                                         └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │   PURGED     │
                                         │ (data removed)│
                                         └──────────────┘
```

##### Lifecycle Operations

| Operation | Trigger | Actions |
|-----------|---------|---------|
| **Create** | Marketplace registration, admin action | Create tenant record, default settings, owner user |
| **Activate** | Email verification, payment | Enable API access, start trial/subscription |
| **Suspend** | Payment failure, admin action, trial expiry | Disable API access, send notification, preserve data |
| **Reactivate** | Payment received, admin action | Enable API access, clear suspension flags |
| **Delete** | User request, admin action | Soft delete, schedule purge in 30 days |
| **Purge** | 30 days after deletion | Hard delete all tenant data, anonymize audit logs |
| **Export** | User request (GDPR), admin action | Generate ZIP with all tenant data in JSON format |

#### Data Model

```yaml
Tenant:
  tenant_id: str (UUID)
  name: str
  slug: str (unique, URL-safe)
  status: enum (PENDING, ACTIVE, SUSPENDED, DELETED)
  tier: enum (FREE, STARTER, PROFESSIONAL, ENTERPRISE)
  settings: jsonb
  metadata: jsonb  # {"company_size": "...", "industry": "..."}
  created_at: datetime
  updated_at: datetime
  suspended_at: datetime (nullable)
  deleted_at: datetime (nullable)
  purge_scheduled_at: datetime (nullable)

TenantQuota:
  quota_id: str (UUID)
  tenant_id: str (FK)
  quota_type: str (e.g., "api_calls_per_hour", "scans_per_day")
  limit: int (-1 for unlimited)
  current_usage: int
  reset_at: datetime
  last_exceeded_at: datetime (nullable)

TenantMember:
  member_id: str (UUID)
  tenant_id: str (FK)
  user_id: str (FK)
  role: enum (OWNER, ADMIN, MEMBER, VIEWER)
  invited_at: datetime
  invited_by: str (FK to User)
  accepted_at: datetime (nullable)
  removed_at: datetime (nullable)

TenantAWSAccount:
  account_id: str (UUID)
  tenant_id: str (FK)
  aws_account_id: str (12-digit)
  role_arn: str (IAM role for scanning)
  external_id: str (for assume role)
  regions: list[str]
  status: enum (PENDING, ACTIVE, ERROR)
  last_scan_at: datetime (nullable)
  error_message: str (nullable)
```

#### Row-Level Security Implementation

```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
-- ... repeat for all tenant-scoped tables

-- Create policies
CREATE POLICY tenant_isolation ON findings
  FOR ALL
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Platform admin bypass
CREATE POLICY admin_bypass ON findings
  FOR ALL
  TO platform_admin
  USING (true);

-- Tenant context is set in middleware
SET app.current_tenant_id = 'tenant-uuid-here';
```

#### Tenant Context Pattern

```python
# Every request must establish tenant context
@dataclass
class TenantContext:
    tenant_id: str
    tenant_name: str
    tier: TenantTier
    status: TenantStatus
    quotas: Dict[str, TenantQuota]
    settings: TenantSettings
    features: List[str]  # Enabled features for this tier

# Middleware injects context from JWT
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/v1/"):
        token = get_jwt_token(request)
        if token and token.tenant_id:
            tenant_ctx = await get_tenant_context(token.tenant_id)
            if tenant_ctx.status != TenantStatus.ACTIVE:
                raise HTTPException(403, "Tenant suspended")
            request.state.tenant = tenant_ctx
            # Set PostgreSQL session variable for RLS
            await set_db_tenant_context(token.tenant_id)
    return await call_next(request)
```

---

### 3.3 Trial Management

**Priority:** P0 (Business-Critical)
**Effort:** 1 week
**Dependencies:** Tenant system complete

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| TRL-001 | Trial creation | Create 14-day trial on new tenant registration |
| TRL-002 | Trial limits | Enforce trial-specific quotas (e.g., 100 scans, 5 users) |
| TRL-003 | Trial expiration | Automatically suspend access after trial ends |
| TRL-004 | Trial conversion | Convert trial to paid via Marketplace |
| TRL-005 | Trial extension | Admin can extend trial period |
| TRL-006 | Trial notifications | Email at 7 days, 3 days, 1 day, expiry |

#### Trial Configuration

```yaml
Default Trial:
  duration_days: 14
  limits:
    scans: 100
    users: 5
    api_calls_per_day: 1000
    findings_stored: 500
    aws_accounts: 1
  features:
    - security_scanning
    - cost_analysis
    - dashboard_basic
  disabled_features:
    - advanced_analytics
    - custom_reports
    - api_access
    - sso_integration

Notification Schedule:
  - days_remaining: 7
    template: trial_reminder_7d
  - days_remaining: 3
    template: trial_reminder_3d
  - days_remaining: 1
    template: trial_final_reminder
  - days_remaining: 0
    template: trial_expired
```

#### Data Model

```yaml
Trial:
  trial_id: str (UUID)
  tenant_id: str (FK)
  status: enum (ACTIVE, EXPIRED, CONVERTED, CANCELLED)
  started_at: datetime
  expires_at: datetime
  extended_count: int (default 0)
  extended_by: str (FK to User, nullable)
  converted_at: datetime (nullable)
  converted_to: str (subscription ID, nullable)
  limits: jsonb  # {"scans": 100, "users": 5, ...}
  usage: jsonb   # {"scans": 45, "users": 3, ...}
  notification_sent: jsonb  # {"7d": true, "3d": false, ...}
```

---

### 3.4 User Management

**Priority:** P1 (High)
**Effort:** 1 week
**Dependencies:** Tenant system complete

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| USR-001 | User registration | Email + password registration with verification |
| USR-002 | User invitation | Invite users to tenant via email |
| USR-003 | User roles | Assign roles (Owner, Admin, Member, Viewer) |
| USR-004 | Profile management | Update name, email, password |
| USR-005 | MFA support | TOTP-based MFA (Google Authenticator compatible) |
| USR-006 | Session management | View active sessions, force logout |
| USR-007 | Password policies | Minimum strength, expiry, history |

#### Role Permissions

| Permission | Owner | Admin | Member | Viewer |
|------------|-------|-------|--------|--------|
| View dashboard | ✓ | ✓ | ✓ | ✓ |
| View findings | ✓ | ✓ | ✓ | ✓ |
| Run scans | ✓ | ✓ | ✓ | - |
| Manage findings | ✓ | ✓ | ✓ | - |
| Invite users | ✓ | ✓ | - | - |
| Manage users | ✓ | ✓ | - | - |
| Tenant settings | ✓ | ✓ | - | - |
| Billing management | ✓ | - | - | - |
| Delete tenant | ✓ | - | - | - |
| Transfer ownership | ✓ | - | - | - |

#### Data Model

```yaml
User:
  user_id: str (UUID)
  email: str (unique)
  password_hash: str (bcrypt)
  name: str
  status: enum (PENDING, ACTIVE, SUSPENDED)
  email_verified: bool
  email_verified_at: datetime (nullable)
  mfa_enabled: bool
  mfa_secret: str (encrypted, nullable)
  mfa_backup_codes: list[str] (encrypted, nullable)
  password_changed_at: datetime
  failed_login_attempts: int (default 0)
  locked_until: datetime (nullable)
  created_at: datetime
  last_login_at: datetime (nullable)

UserSession:
  session_id: str (UUID)
  user_id: str (FK)
  tenant_id: str (FK)  # Active tenant context
  refresh_token_hash: str
  created_at: datetime
  expires_at: datetime
  last_activity_at: datetime
  ip_address: str
  user_agent: str
  is_revoked: bool (default false)
```

---

## 4. Phase 2: Feature Parity (Weeks 9-14)

### 4.1 Cost Optimization Engine

**Priority:** P1 (High)
**Effort:** 2 weeks
**Dependencies:** AWS Cost Explorer access, Scanners framework

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| CST-001 | Cost analysis | Analyze AWS Cost Explorer data for spending patterns |
| CST-002 | Savings recommendations | Generate RI, Savings Plan, rightsizing recommendations |
| CST-003 | Cost forecasting | 30/60/90-day cost projections |
| CST-004 | Cost anomaly detection | Alert on unusual spending patterns |
| CST-005 | Cost allocation | Tag-based cost breakdown by team/project |

---

### 4.2 Dashboard APIs

**Priority:** P1 (High)
**Effort:** 2 weeks
**Dependencies:** Cost and Security services complete

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| DSH-001 | Overview dashboard | Summary metrics for security, cost, compliance |
| DSH-002 | Security dashboard | Vulnerability counts, severity breakdown, trends |
| DSH-003 | Cost dashboard | Spending summary, savings opportunities, forecasts |
| DSH-004 | Compliance dashboard | Framework status, gaps, remediation progress |
| DSH-005 | Trend analytics | Historical data with time-series charts |

---

### 4.3 Prometheus Metrics

**Priority:** P1 (High)
**Effort:** 1 week
**Dependencies:** API layer complete

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| MTR-001 | Request metrics | Count, latency, status by endpoint |
| MTR-002 | Business metrics | Scans, findings, recommendations by tenant |
| MTR-003 | IB integration metrics | IB API latency, errors, cache hits |
| MTR-004 | System metrics | Memory, CPU, connection pool stats |

---

### 4.4 Notification System

**Priority:** P2 (Medium)
**Effort:** 1 week
**Dependencies:** SES access, user preferences

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| NTF-001 | Email notifications | Send alerts via email (SES) |
| NTF-002 | Slack integration | Post alerts to Slack channels |
| NTF-003 | Webhook support | Send alerts to custom webhook URLs |
| NTF-004 | Notification preferences | Per-user notification settings |
| NTF-005 | Alert rules | Configurable alert triggers |

---

### 4.5 Knowledge Ingestion System

**Priority:** P1 (High)
**Effort:** 2 weeks
**Dependencies:** IB Platform graph backend, pattern engine

> **Note:** The Knowledge Base is the foundation of the Expert System. Recommendations quality depends directly on the knowledge ingested. Initial setup should begin in Phase 1 with continuous updates throughout.

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| KNG-001 | Source registry | Maintain registry of knowledge sources with metadata, credentials, update schedules |
| KNG-002 | Document ingestion | Parse and extract entities from AWS docs, security bulletins, best practices |
| KNG-003 | CVE ingestion | Daily sync from NVD/CVE database with severity scoring |
| KNG-004 | CIS benchmark ingestion | Import CIS Benchmarks with control mappings |
| KNG-005 | Pricing data ingestion | Weekly sync of AWS pricing data for cost recommendations |
| KNG-006 | Incremental updates | Support delta updates to avoid full re-ingestion |
| KNG-007 | Entity extraction | Extract entities (vulnerabilities, controls, remediations) using pattern engine |
| KNG-008 | Relationship mapping | Identify and store relationships between knowledge entities |
| KNG-009 | Embedding generation | Generate vector embeddings for semantic search |
| KNG-010 | Deduplication | Detect and merge duplicate entities across sources |
| KNG-011 | Quality scoring | Score knowledge entities by source authority, recency, verification |
| KNG-012 | Versioning | Track entity versions for audit and rollback |
| KNG-013 | Staleness detection | Flag stale entities that haven't been updated |
| KNG-014 | Manual curation | Admin interface for reviewing and correcting extracted entities |

#### Knowledge Sources

| Source | Type | Update Frequency | Priority |
|--------|------|------------------|----------|
| AWS Documentation | Best practices, service guides | Weekly | P0 |
| AWS Security Bulletins | Vulnerability advisories | Daily | P0 |
| CVE/NVD Database | Vulnerability database | Daily | P0 |
| CIS Benchmarks | Security controls | Monthly | P1 |
| AWS Pricing API | Service pricing | Weekly | P1 |
| NIST Guidelines | Security frameworks | Quarterly | P2 |
| OWASP Top 10 | Application security | Yearly | P2 |

#### Data Model

```yaml
KnowledgeSource:
  source_id: str (UUID)
  name: str (e.g., "AWS Security Bulletins")
  type: enum (DOCUMENTATION, CVE, BENCHMARK, PRICING, GUIDELINE)
  url: str (base URL)
  auth_type: enum (NONE, API_KEY, OAUTH, BASIC)
  auth_credentials: str (encrypted reference to secrets manager)
  parser_type: str (e.g., "html", "json", "xml", "rss")
  update_schedule: str (cron expression)
  last_sync_at: datetime (nullable)
  last_sync_status: enum (SUCCESS, PARTIAL, FAILED)
  entity_count: int
  is_active: bool
  priority: int (ordering for sync jobs)
  metadata: jsonb

KnowledgeEntity:
  entity_id: str (UUID)
  source_id: str (FK)
  entity_type: enum (VULNERABILITY, THREAT, CONTROL, REMEDIATION, PRICING_MODEL, BEST_PRACTICE, COMPLIANCE_REQUIREMENT)
  external_id: str (e.g., CVE-2024-12345)
  title: str
  description: text
  severity: enum (CRITICAL, HIGH, MEDIUM, LOW, INFO) - nullable
  confidence_score: float (0.0 - 1.0)
  quality_score: float (0.0 - 1.0)
  embedding: vector(1536) - nullable
  metadata: jsonb
  tags: list[str]
  source_url: str (specific page URL)
  version: int
  created_at: datetime
  updated_at: datetime
  stale_at: datetime (nullable, based on source type)
  verified_by: str (FK to User, nullable)
  verified_at: datetime (nullable)

KnowledgeRelationship:
  relationship_id: str (UUID)
  source_entity_id: str (FK)
  target_entity_id: str (FK)
  relationship_type: enum (MITIGATES, EXPLOITS, REFERENCES, SUPERSEDES, RELATED_TO)
  confidence_score: float (0.0 - 1.0)
  metadata: jsonb
  created_at: datetime

IngestionJob:
  job_id: str (UUID)
  source_id: str (FK)
  status: enum (PENDING, RUNNING, COMPLETED, FAILED)
  started_at: datetime
  completed_at: datetime (nullable)
  entities_created: int
  entities_updated: int
  entities_skipped: int
  relationships_created: int
  errors: jsonb (list of error messages)
  metadata: jsonb
```

#### Ingestion Pipeline Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Fetcher    │────▶│    Parser    │────▶│  Extractor   │────▶│   Embedder   │
│ (HTTP/API)   │     │ (HTML/JSON)  │     │  (Entities)  │     │  (Vectors)   │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                       │
                                                                       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Store     │◀────│   Deduper    │◀────│  Validator   │◀────│ Relationship │
│   (Graph)    │     │  (Merge)     │     │  (Quality)   │     │  Detector    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

#### API Endpoints

```yaml
POST /api/v1/knowledge/sources:
  description: Register new knowledge source
  auth: JWT (admin only)
  body:
    name: string
    type: enum
    url: string
    parser_type: string
    update_schedule: string (cron)
  response:
    source_id: string
    status: string

POST /api/v1/knowledge/sources/{source_id}/sync:
  description: Trigger immediate sync for source
  auth: JWT (admin only)
  query:
    full: bool (default false, true for full re-ingestion)
  response:
    job_id: string
    status: "PENDING"

GET /api/v1/knowledge/entities:
  description: Search knowledge entities
  auth: JWT
  query:
    q: string (search query)
    type: enum (filter by entity type)
    source_id: string (filter by source)
    min_quality: float (default 0.5)
    limit: int (default 20, max 100)
  response:
    entities: list[KnowledgeEntity]
    total: int

GET /api/v1/knowledge/entities/{entity_id}/related:
  description: Get related entities
  auth: JWT
  query:
    relationship_type: enum (optional filter)
    depth: int (default 1, max 3)
  response:
    entities: list[KnowledgeEntity]
    relationships: list[KnowledgeRelationship]

GET /api/v1/knowledge/stats:
  description: Knowledge base statistics
  auth: JWT (admin only)
  response:
    total_entities: int
    entities_by_type: object
    entities_by_source: object
    stale_entities: int
    last_sync: datetime
    quality_distribution: object
```

#### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Entity coverage | 95%+ of known CVEs | Compare with NVD count |
| Freshness | <24h for critical sources | Time since last sync |
| Quality score avg | >0.7 | Average quality_score |
| Deduplication rate | <5% duplicates | Duplicate detection ratio |
| Relationship coverage | >80% entities linked | Entities with relationships |
| Embedding coverage | 100% | Entities with embeddings |

---

### 4.6 Hybrid Search System

**Priority:** P1 (High)
**Effort:** 2 weeks
**Dependencies:** Knowledge Ingestion (KNG-009 embeddings), Graph backends

> **Note:** Hybrid search combining vector similarity with graph traversal is a key differentiator prominently featured in marketing materials. This enables "finding connections that are impossible to find with conventional tools."

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| SRH-001 | Vector similarity search | Query knowledge base using semantic embeddings with cosine similarity, returning top-k results |
| SRH-002 | Graph-enhanced retrieval | Expand vector search results by traversing graph relationships (1-3 hops) |
| SRH-003 | Hybrid ranking algorithm | Combine vector similarity score + graph relevance score + recency for final ranking |
| SRH-004 | Search mode selection | Support vector-only, graph-only, or hybrid search modes via API parameter |
| SRH-005 | Context assembly | Build rich context from search results including related entities, temporal history, and cross-domain relationships |
| SRH-006 | Search performance | Hybrid search returns results in <2 seconds for 3-hop traversals |

#### Search Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Hybrid Search Pipeline                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Query ──▶ ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐   │
│            │  Embedding  │───▶│   Vector    │───▶│  Initial        │   │
│            │  Generator  │    │   Search    │    │  Results (k=50) │   │
│            └─────────────┘    └─────────────┘    └────────┬────────┘   │
│                                                           │             │
│                                                           ▼             │
│                                                  ┌─────────────────┐   │
│                                                  │  Graph Expand   │   │
│                                                  │  (1-3 hops)     │   │
│                                                  └────────┬────────┘   │
│                                                           │             │
│                                                           ▼             │
│            ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐   │
│  Results ◀─│   Context   │◀───│   Hybrid    │◀───│  Expanded       │   │
│            │   Builder   │    │   Ranker    │    │  Result Set     │   │
│            └─────────────┘    └─────────────┘    └─────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Ranking Algorithm

```python
def hybrid_score(result: SearchResult) -> float:
    """
    Combine multiple signals for final ranking.

    Weights are configurable per domain.
    """
    return (
        weights.vector * result.vector_similarity +      # Semantic relevance (0-1)
        weights.graph * result.graph_relevance +         # Graph proximity (0-1)
        weights.recency * result.recency_score +         # Time decay (0-1)
        weights.quality * result.source_quality +        # Source authority (0-1)
        weights.confidence * result.confidence_score     # Pattern confidence (0-1)
    )

# Default weights
DEFAULT_WEIGHTS = HybridWeights(
    vector=0.35,
    graph=0.30,
    recency=0.15,
    quality=0.10,
    confidence=0.10
)
```

#### Data Model

```yaml
SearchQuery:
  query_id: str (UUID)
  query_text: str
  query_embedding: vector(1536) - generated
  mode: enum (VECTOR_ONLY, GRAPH_ONLY, HYBRID)
  filters:
    domains: list[str] (optional)
    entity_types: list[str] (optional)
    date_range: DateRange (optional)
    min_quality: float (default 0.5)
  options:
    max_results: int (default 20)
    graph_depth: int (default 2, max 3)
    include_context: bool (default true)
  tenant_id: str (FK)
  user_id: str (FK)
  created_at: datetime

SearchResult:
  result_id: str (UUID)
  query_id: str (FK)
  entity_id: str (FK to KnowledgeEntity)
  vector_similarity: float (0-1)
  graph_relevance: float (0-1)
  hybrid_score: float (0-1)
  context: SearchContext
  rank: int

SearchContext:
  primary_entity: KnowledgeEntity
  related_entities: list[KnowledgeEntity] (from graph traversal)
  relationships: list[KnowledgeRelationship]
  temporal_context: list[EntityVersion] (history)
  cross_domain_links: list[CrossDomainLink]
```

#### API Endpoints

```yaml
POST /api/v1/search:
  description: Execute hybrid search query
  auth: JWT
  body:
    query: string (required)
    mode: "vector" | "graph" | "hybrid" (default "hybrid")
    domains: list[string] (optional filter)
    entity_types: list[string] (optional filter)
    max_results: int (default 20, max 100)
    graph_depth: int (default 2, max 3)
    include_context: bool (default true)
  response:
    query_id: string
    results: list[SearchResult]
    total_found: int
    search_time_ms: int
    mode_used: string

GET /api/v1/search/{query_id}/explain:
  description: Explain ranking for a search result
  auth: JWT
  response:
    query: string
    result_id: string
    ranking_factors:
      vector_similarity: float
      graph_relevance: float
      recency_score: float
      quality_score: float
      confidence_score: float
    graph_path: list[Entity] (how result was reached)
    evidence_chain: list[Source]
```

#### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Vector search latency | <200ms | For k=50 initial results |
| Graph expansion latency | <500ms | For 2-hop, <1000ms for 3-hop |
| Hybrid search total | <2000ms | End-to-end for 3-hop |
| Context assembly | <300ms | Including related entities |

---

### 4.7 Natural Language Understanding (NLU)

**Priority:** P1 (High)
**Effort:** 2 weeks
**Dependencies:** Hybrid Search system, Knowledge Graph

> **Note:** NLU is the entry point to the GraphRAG engine. It transforms natural language questions into structured queries that can be executed against the knowledge graph.

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| NLU-001 | Query intent parsing | Classify query intent into categories: FIND (retrieve entities), COMPARE (contrast entities), ANALYZE (identify patterns), PREDICT (forecast), EXPLAIN (provide reasoning) |
| NLU-002 | Domain classification | Auto-detect query domain (security, cost, compliance, performance) with confidence score; support multi-domain queries |
| NLU-003 | Entity extraction from queries | Extract entity mentions from natural language using ontology-guided NER; link to canonical entities |
| NLU-004 | Query reformulation | When query is ambiguous (confidence <0.7), suggest clarified alternatives; track which reformulations users select |
| NLU-005 | Temporal understanding | Parse temporal references ("last month", "Q3 2024", "since the audit") into date ranges |
| NLU-006 | Query decomposition | Break complex multi-part queries into sub-queries that can be executed independently and combined |

#### NLU Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NLU Processing Pipeline                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  "Which security controls failed in our last SOC2 audit?"                   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Intent Classification                         │    │
│  │  Intent: FIND (0.92) | Domain: compliance (0.88), security (0.75)   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Entity Extraction                             │    │
│  │  "security controls" → EntityType:Control, Domain:Security          │    │
│  │  "SOC2 audit" → EntityType:Audit, Framework:SOC2                    │    │
│  │  "last" → Temporal:most_recent                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Query Structure                               │    │
│  │  {                                                                   │    │
│  │    intent: "FIND",                                                   │    │
│  │    targets: [{type: "Control", filters: {status: "failed"}}],       │    │
│  │    context: [{type: "Audit", filters: {framework: "SOC2"}}],        │    │
│  │    temporal: {reference: "most_recent"},                            │    │
│  │    relationships: ["EVALUATED_BY"]                                   │    │
│  │  }                                                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Data Model

```yaml
ParsedQuery:
  query_id: str (UUID)
  original_text: str
  intent:
    primary: enum (FIND, COMPARE, ANALYZE, PREDICT, EXPLAIN)
    confidence: float (0-1)
    alternatives: list[{intent, confidence}]
  domains:
    - domain: str
      confidence: float
  entities:
    - mention: str (text span)
      start_pos: int
      end_pos: int
      entity_type: str
      canonical_id: str (nullable, if resolved)
      confidence: float
  temporal:
    reference: enum (ABSOLUTE, RELATIVE, RANGE, MOST_RECENT)
    start_date: datetime (nullable)
    end_date: datetime (nullable)
    raw_text: str
  relationships:
    - type: str
      direction: enum (OUTBOUND, INBOUND, ANY)
  sub_queries: list[ParsedQuery] (for decomposed queries)
  reformulations: list[str] (suggested alternatives)
  created_at: datetime

QueryFeedback:
  feedback_id: str (UUID)
  query_id: str (FK)
  feedback_type: enum (REFORMULATION_SELECTED, INTENT_CORRECTED, ENTITY_CORRECTED)
  original_value: str
  corrected_value: str
  user_id: str (FK)
  created_at: datetime
```

#### API Endpoints

```yaml
POST /api/v1/nlu/parse:
  description: Parse natural language query into structured form
  auth: JWT
  body:
    query: string (required)
    context:
      previous_queries: list[string] (optional, for context)
      domain_hint: string (optional)
  response:
    parsed_query: ParsedQuery
    needs_clarification: bool
    reformulations: list[string] (if ambiguous)

POST /api/v1/nlu/reformulate:
  description: User selects a reformulation
  auth: JWT
  body:
    query_id: string
    selected_reformulation: string
  response:
    parsed_query: ParsedQuery (re-parsed with selected reformulation)

POST /api/v1/nlu/correct:
  description: User corrects NLU interpretation
  auth: JWT
  body:
    query_id: string
    correction_type: enum
    original_value: string
    corrected_value: string
  response:
    acknowledged: bool
    updated_query: ParsedQuery
```

#### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Query parsing latency | <100ms | Full NLU pipeline |
| Intent classification accuracy | >90% | Measured on test set |
| Entity extraction F1 | >85% | With ontology guidance |
| Domain classification accuracy | >92% | Top-1 accuracy |

---

### 4.8 Answer Generation Engine

**Priority:** P1 (High)
**Effort:** 2 weeks
**Dependencies:** NLU, Hybrid Search, Knowledge Graph

> **Note:** The Answer Generation Engine synthesizes information from multiple graph sources into coherent, evidence-backed responses. This is the "intelligence" that makes GraphRAG superior to traditional RAG.

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| ANS-001 | Multi-source synthesis | Aggregate information from multiple knowledge entities into a coherent answer; cite all sources |
| ANS-002 | Confidence scoring | Calculate overall answer confidence from source quality, relationship strength, and evidence coverage |
| ANS-003 | Alternative interpretations | When confidence <0.8, provide alternative answers with different assumptions |
| ANS-004 | Ranked recommendations | Order recommendations by configurable criteria: risk severity, savings potential, implementation ease, compliance impact |
| ANS-005 | Remediation steps | For security/compliance findings, include actionable remediation steps from knowledge base |
| ANS-006 | Evidence chains | Provide complete evidence trail from answer back to source documents |
| ANS-007 | Answer formatting | Structure answers appropriately for query type (list, table, narrative, comparison) |
| ANS-008 | Cross-domain insights | Identify and include relevant insights from related domains (e.g., cost implications of security findings) |

#### Answer Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Answer Generation Pipeline                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Search Results ──▶ ┌───────────────┐    ┌───────────────┐                  │
│  (from Hybrid       │   Aggregator  │───▶│   Synthesizer │                  │
│   Search)           │ (group by     │    │ (merge info,  │                  │
│                     │  entity)      │    │  resolve      │                  │
│                     └───────────────┘    │  conflicts)   │                  │
│                                          └───────┬───────┘                  │
│                                                  │                          │
│                                                  ▼                          │
│                     ┌───────────────┐    ┌───────────────┐                  │
│                     │   Confidence  │◀───│   Evidence    │                  │
│                     │   Calculator  │    │   Linker      │                  │
│                     └───────┬───────┘    └───────────────┘                  │
│                             │                                               │
│                             ▼                                               │
│       ┌─────────────────────┴─────────────────────┐                        │
│       │              Confidence >= 0.8?            │                        │
│       └─────────────────────┬─────────────────────┘                        │
│                   Yes │           │ No                                      │
│                       ▼           ▼                                         │
│               ┌───────────┐  ┌───────────────┐                             │
│               │  Primary  │  │  Alternatives │                             │
│               │  Answer   │  │  Generator    │                             │
│               └─────┬─────┘  └───────┬───────┘                             │
│                     │                │                                      │
│                     └────────┬───────┘                                      │
│                              ▼                                              │
│                     ┌───────────────┐    ┌───────────────┐                  │
│                     │   Formatter   │───▶│   Output      │──▶ Final Answer │
│                     │ (structure by │    │ (with evidence│                  │
│                     │  query type)  │    │  & confidence)│                  │
│                     └───────────────┘    └───────────────┘                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Data Model

```yaml
GeneratedAnswer:
  answer_id: str (UUID)
  query_id: str (FK to ParsedQuery)
  search_id: str (FK to SearchQuery)

  # Primary answer
  content:
    summary: str (concise answer)
    details: list[AnswerSection]
    format: enum (NARRATIVE, LIST, TABLE, COMPARISON, TIMELINE)

  # Confidence and evidence
  confidence:
    overall: float (0-1)
    factors:
      source_quality: float
      evidence_coverage: float
      relationship_strength: float
      temporal_relevance: float
    explanation: str (why this confidence level)

  evidence_chain:
    - entity_id: str
      entity_type: str
      source_url: str
      relevance: float
      excerpt: str

  # Alternatives (if confidence < 0.8)
  alternatives:
    - content: AnswerContent
      confidence: float
      assumption: str (what differs from primary)

  # Cross-domain insights
  related_insights:
    - domain: str
      insight: str
      relevance: float
      entities: list[str]

  # Recommendations (if applicable)
  recommendations:
    - title: str
      priority: enum (CRITICAL, HIGH, MEDIUM, LOW)
      impact: str
      effort: enum (LOW, MEDIUM, HIGH)
      remediation_steps: list[str]
      evidence: list[str] (entity IDs)
      savings_potential: float (nullable, for cost recommendations)

  # Metadata
  generation_time_ms: int
  created_at: datetime
  user_id: str (FK)
  tenant_id: str (FK)

AnswerSection:
  title: str
  content: str
  entities: list[str] (entity IDs referenced)
  evidence: list[EvidenceLink]
  sub_sections: list[AnswerSection] (nullable)

EvidenceLink:
  entity_id: str
  entity_type: str
  title: str
  source_url: str
  excerpt: str
  confidence: float
```

#### Recommendation Ranking Algorithm

```python
def rank_recommendations(
    recommendations: list[Recommendation],
    criteria: RankingCriteria
) -> list[Recommendation]:
    """
    Rank recommendations by configurable criteria.

    Default weights prioritize risk, then savings, then ease.
    """
    for rec in recommendations:
        rec.score = (
            criteria.risk_weight * risk_score(rec) +
            criteria.savings_weight * savings_score(rec) +
            criteria.ease_weight * ease_score(rec) +
            criteria.compliance_weight * compliance_score(rec)
        )

    return sorted(recommendations, key=lambda r: r.score, reverse=True)

# Default ranking criteria
DEFAULT_CRITERIA = RankingCriteria(
    risk_weight=0.40,      # Prioritize high-risk items
    savings_weight=0.30,   # Then potential savings
    ease_weight=0.20,      # Then implementation ease
    compliance_weight=0.10 # Then compliance impact
)

def risk_score(rec: Recommendation) -> float:
    """Map priority to score: CRITICAL=1.0, HIGH=0.75, MEDIUM=0.5, LOW=0.25"""
    return {"CRITICAL": 1.0, "HIGH": 0.75, "MEDIUM": 0.5, "LOW": 0.25}[rec.priority]

def savings_score(rec: Recommendation) -> float:
    """Normalize savings to 0-1 range based on tenant's total spend"""
    if not rec.savings_potential:
        return 0.0
    return min(rec.savings_potential / tenant_monthly_spend, 1.0)

def ease_score(rec: Recommendation) -> float:
    """Inverse of effort: LOW effort = 1.0, HIGH effort = 0.33"""
    return {"LOW": 1.0, "MEDIUM": 0.66, "HIGH": 0.33}[rec.effort]
```

#### API Endpoints

```yaml
POST /api/v1/answer/generate:
  description: Generate answer from search results
  auth: JWT
  body:
    query_id: string (from NLU parse)
    search_id: string (from hybrid search)
    options:
      include_alternatives: bool (default true if confidence < 0.8)
      include_cross_domain: bool (default true)
      recommendation_criteria: RankingCriteria (optional)
      format_preference: enum (optional)
  response:
    answer: GeneratedAnswer

GET /api/v1/answer/{answer_id}:
  description: Retrieve a generated answer
  auth: JWT
  response:
    answer: GeneratedAnswer

GET /api/v1/answer/{answer_id}/evidence:
  description: Get detailed evidence chain for an answer
  auth: JWT
  response:
    evidence_chain: list[EvidenceDetail]
    graph_visualization: GraphData (for UI rendering)

POST /api/v1/answer/{answer_id}/feedback:
  description: Provide feedback on answer quality
  auth: JWT
  body:
    rating: enum (HELPFUL, NOT_HELPFUL, PARTIALLY_HELPFUL)
    feedback_type: enum (MISSING_INFO, INCORRECT, OUTDATED, GOOD)
    details: string (optional)
  response:
    acknowledged: bool
```

#### Answer Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Answer accuracy | 95%+ | Human evaluation sample (monthly) |
| Evidence relevance | 90%+ | % of cited evidence supports answer |
| Confidence calibration | ±10% | Predicted vs actual accuracy |
| User satisfaction | 90%+ | Thumbs up ratio |
| Cross-domain discovery | 70%+ | % of answers with relevant cross-domain insights |

#### Example Generated Answer

```json
{
  "answer_id": "ans-123",
  "content": {
    "summary": "3 security controls failed in the Q3 2024 SOC2 audit.",
    "format": "LIST",
    "details": [
      {
        "title": "Access Control (CC6.1)",
        "content": "Failed due to missing MFA on 12 privileged accounts.",
        "entities": ["ctrl-456", "audit-789"],
        "evidence": [
          {"source_url": "/audits/2024-q3/report.pdf#page=23", "excerpt": "..."}
        ],
        "sub_sections": [
          {"title": "Status", "content": "In Progress (70% complete)"},
          {"title": "Owner", "content": "Security Team (John Smith)"},
          {"title": "Target", "content": "January 15, 2025"}
        ]
      }
    ]
  },
  "confidence": {
    "overall": 0.94,
    "factors": {
      "source_quality": 0.98,
      "evidence_coverage": 0.92,
      "relationship_strength": 0.95,
      "temporal_relevance": 0.90
    }
  },
  "recommendations": [
    {
      "title": "Enable MFA for remaining privileged accounts",
      "priority": "CRITICAL",
      "impact": "Resolves CC6.1 finding, reduces unauthorized access risk",
      "effort": "LOW",
      "remediation_steps": [
        "Identify 12 accounts without MFA (see finding detail)",
        "Enable MFA via AWS IAM console or CLI",
        "Notify account owners of new requirement",
        "Update access policy documentation"
      ],
      "evidence": ["ctrl-456", "finding-321"]
    }
  ],
  "related_insights": [
    {
      "domain": "cost",
      "insight": "MFA tokens cost ~$50/user/year; total: $600",
      "relevance": 0.72
    }
  ]
}
```

---

## 5. Phase 3: Frontend (Weeks 15-22)

### 5.1 Frontend Application

**Priority:** P0 (Business-Critical)
**Effort:** 8 weeks
**Dependencies:** All Phase 2 APIs complete, design mockups approved

#### Requirements (Broken Down)

##### Authentication UI (FE-001) - 1 week
| Sub-ID | Feature | Acceptance Criteria |
|--------|---------|---------------------|
| FE-001a | Login page | Email/password form, error handling, "remember me" |
| FE-001b | Registration page | Form with validation, email verification flow |
| FE-001c | Forgot password | Email input, reset link, new password form |
| FE-001d | MFA setup | QR code display, backup codes, verification |
| FE-001e | MFA challenge | 6-digit code input on login when enabled |

##### Dashboard (FE-002) - 1 week
| Sub-ID | Feature | Acceptance Criteria |
|--------|---------|---------------------|
| FE-002a | Overview cards | Security score, cost savings, compliance status |
| FE-002b | Trend charts | 7-day/30-day trends for key metrics |
| FE-002c | Recent activity | Latest scans, findings, recommendations |
| FE-002d | Quick actions | Start scan, view findings, go to settings |

##### Security View (FE-003) - 2 weeks
| Sub-ID | Feature | Acceptance Criteria |
|--------|---------|---------------------|
| FE-003a | Findings list | Table with sort, filter, search, pagination |
| FE-003b | Finding detail | Full finding info, affected resources, remediation |
| FE-003c | Severity breakdown | Chart of findings by severity |
| FE-003d | Bulk actions | Select multiple, mark as resolved, export |
| FE-003e | Scan management | Start scan, view history, schedule scans |

##### Cost View (FE-004) - 1.5 weeks
| Sub-ID | Feature | Acceptance Criteria |
|--------|---------|---------------------|
| FE-004a | Spending overview | Current month, forecast, YoY comparison |
| FE-004b | Service breakdown | Cost by AWS service with drill-down |
| FE-004c | Recommendations | Savings opportunities with potential amount |
| FE-004d | Cost trends | 12-month trend chart |

##### Compliance View (FE-005) - 1 week
| Sub-ID | Feature | Acceptance Criteria |
|--------|---------|---------------------|
| FE-005a | Framework list | Supported frameworks with status |
| FE-005b | Framework detail | Controls, compliance percentage, gaps |
| FE-005c | Evidence management | Upload/view compliance evidence |

##### Settings (FE-006) - 1 week
| Sub-ID | Feature | Acceptance Criteria |
|--------|---------|---------------------|
| FE-006a | Tenant settings | Name, slug, timezone, defaults |
| FE-006b | User profile | Name, email, password change |
| FE-006c | Security settings | MFA, sessions, API keys |
| FE-006d | Integrations | AWS accounts, Slack, webhooks |
| FE-006e | Notifications | Email preferences, alert rules |

##### Admin Panel (FE-007) - 0.5 week
| Sub-ID | Feature | Acceptance Criteria |
|--------|---------|---------------------|
| FE-007a | User management | List, invite, edit roles, remove users |
| FE-007b | Billing | Current plan, usage, upgrade link |
| FE-007c | Audit logs | Searchable audit log viewer |

##### User Feedback & Answer Validation (FE-008) - 1 week
| Sub-ID | Feature | Acceptance Criteria |
|--------|---------|---------------------|
| FE-008a | Answer feedback buttons | Thumbs up/down on every AI-generated answer and recommendation |
| FE-008b | Answer correction form | Modal to submit corrections with evidence/reasoning |
| FE-008c | Evidence validation | Allow users to confirm or reject cited evidence sources |
| FE-008d | Feedback history | View user's past feedback submissions and their status |
| FE-008e | Expert badge system | Visual indicators for domain expert contributors |

> **Note:** User feedback is critical for the "continuous learning" marketing claim. Every answer must have a feedback mechanism.

#### Technology Stack

```yaml
Framework: React 18 + TypeScript
Build: Vite
State: TanStack Query (server state) + Zustand (client state)
Routing: React Router v6
UI: Tailwind CSS + Headless UI
Charts: Recharts
Tables: TanStack Table
Forms: React Hook Form + Zod validation
Testing: Vitest + Testing Library + Playwright (E2E)
```

---

### 5.2 User Feedback Loop (Backend)

**Priority:** P1 (High)
**Effort:** 2 weeks
**Dependencies:** Knowledge Ingestion system, Frontend feedback UI

> **Note:** The feedback loop enables "continuous learning from experts" - a key marketing differentiator. User feedback flows back into the knowledge base to improve answer quality over time.

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FBK-001 | Feedback capture | Store all user feedback (thumbs, corrections, evidence validation) with context |
| FBK-002 | Feedback classification | Auto-classify feedback by type (factual error, outdated info, wrong evidence, etc.) |
| FBK-003 | Expert routing | Route feedback to domain experts based on entity type and confidence threshold |
| FBK-004 | Feedback-to-knowledge pipeline | Convert validated corrections into knowledge graph updates |
| FBK-005 | Conflict resolution | Handle conflicting feedback from multiple users with voting/authority weights |
| FBK-006 | Learning metrics | Track improvement in answer quality from feedback (correction rate over time) |
| FBK-007 | Feedback analytics | Dashboard showing feedback volume, categories, resolution rate, expert activity |

#### Feedback Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Continuous Learning Pipeline                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User ──▶ ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐    │
│ Feedback  │  Capture &  │───▶│  Classify   │───▶│  Expert Review      │    │
│           │  Store      │    │  & Route    │    │  Queue              │    │
│           └─────────────┘    └─────────────┘    └──────────┬──────────┘    │
│                                                             │               │
│                                                             ▼               │
│                                                    ┌─────────────────┐      │
│                                                    │ Expert Reviews  │      │
│                                                    │ & Validates     │      │
│                                                    └────────┬────────┘      │
│                                                             │               │
│           ┌─────────────┐    ┌─────────────┐               │               │
│ Knowledge │   Update    │◀───│  Convert to │◀──────────────┘               │
│   Graph   │   Graph     │    │  Entities   │                               │
│           └─────────────┘    └─────────────┘                               │
│                 │                                                           │
│                 ▼                                                           │
│           ┌─────────────┐                                                   │
│           │  Learning   │  Track: correction_rate, accuracy_trend,         │
│           │  Metrics    │  expert_contributions, resolution_time           │
│           └─────────────┘                                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Data Model

```yaml
UserFeedback:
  feedback_id: str (UUID)
  user_id: str (FK)
  tenant_id: str (FK)
  feedback_type: enum (THUMBS_UP, THUMBS_DOWN, CORRECTION, EVIDENCE_REJECT, EVIDENCE_CONFIRM)
  target_type: enum (ANSWER, RECOMMENDATION, EVIDENCE, ENTITY)
  target_id: str (reference to target)
  context:
    query: str (original question)
    answer: str (AI response)
    evidence_cited: list[str] (entity IDs)
  correction:
    original_value: str (nullable)
    corrected_value: str (nullable)
    reasoning: str (nullable)
    evidence_links: list[str] (URLs or entity IDs)
  status: enum (PENDING, UNDER_REVIEW, VALIDATED, REJECTED, APPLIED)
  assigned_expert: str (FK to User, nullable)
  resolution:
    resolved_by: str (FK to User)
    resolved_at: datetime
    resolution_notes: str
    knowledge_updates: list[str] (entity IDs updated)
  created_at: datetime
  updated_at: datetime

ExpertAssignment:
  assignment_id: str (UUID)
  user_id: str (FK)
  tenant_id: str (FK)
  domains: list[str] (e.g., ["security", "cost"])
  entity_types: list[str] (e.g., ["VULNERABILITY", "CONTROL"])
  authority_level: int (1-5, affects vote weight)
  is_active: bool
  feedback_reviewed: int (count)
  accuracy_score: float (0-1, based on community validation)
  created_at: datetime

LearningMetric:
  metric_id: str (UUID)
  tenant_id: str (FK)
  period: enum (DAILY, WEEKLY, MONTHLY)
  period_start: datetime
  metrics:
    total_answers: int
    thumbs_up: int
    thumbs_down: int
    corrections_submitted: int
    corrections_validated: int
    corrections_applied: int
    average_resolution_time_hours: float
  trends:
    correction_rate: float (corrections / answers)
    satisfaction_rate: float (thumbs_up / total_feedback)
    correction_rate_change: float (vs previous period)
  created_at: datetime
```

#### API Endpoints

```yaml
POST /api/v1/feedback:
  description: Submit feedback on an answer or recommendation
  auth: JWT
  body:
    feedback_type: enum
    target_type: enum
    target_id: string
    context: object (query, answer, evidence)
    correction: object (optional - for corrections)
  response:
    feedback_id: string
    status: "PENDING"

GET /api/v1/feedback/queue:
  description: Get pending feedback for expert review
  auth: JWT (expert role required)
  query:
    domains: list[string] (filter by domain)
    status: enum (default PENDING)
    limit: int (default 20)
  response:
    items: list[UserFeedback]
    total: int

POST /api/v1/feedback/{feedback_id}/review:
  description: Expert reviews and resolves feedback
  auth: JWT (expert role required)
  body:
    action: enum (VALIDATE, REJECT, REQUEST_MORE_INFO)
    resolution_notes: string
    apply_to_knowledge: bool (default false)
  response:
    feedback_id: string
    status: string
    knowledge_updates: list[string] (if applied)

GET /api/v1/feedback/metrics:
  description: Get learning metrics and trends
  auth: JWT
  query:
    period: enum (DAILY, WEEKLY, MONTHLY)
    range: int (number of periods, default 12)
  response:
    metrics: list[LearningMetric]
    trends:
      correction_rate_trend: list[float]
      satisfaction_trend: list[float]
```

---

## 6. Phase 4: Advanced Features (Weeks 23-28)

### 6.1 OAuth2/OIDC Integration

**Priority:** P2 (Medium)
**Effort:** 2 weeks

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| SSO-001 | OIDC provider support | Support Okta, Auth0, Azure AD |
| SSO-002 | SAML support | Enterprise SAML integration |
| SSO-003 | JIT provisioning | Auto-create users on first SSO login |
| SSO-004 | Role mapping | Map SSO groups to tenant roles |

---

### 6.2 Advanced Analytics

**Priority:** P2 (Medium)
**Effort:** 2 weeks

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| ANL-001 | Custom reports | Build custom reports with filters |
| ANL-002 | Scheduled reports | Email reports on schedule |
| ANL-003 | Data export | Export findings/costs as CSV/PDF |
| ANL-004 | API usage analytics | Track API usage patterns per tenant |

---

### 6.3 Audit & Compliance

**Priority:** P1 (High)
**Effort:** 2 weeks

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| AUD-001 | Audit logging | Log all user actions with context |
| AUD-002 | Audit search | Search/filter audit logs |
| AUD-003 | Audit export | Export audit logs for compliance |
| AUD-004 | Retention policy | Configurable log retention |

---

### 6.4 Ontology Management System

**Priority:** P2 (Medium)
**Effort:** 3 weeks
**Dependencies:** Knowledge Ingestion system, Domain System

> **Note:** The "No-Code Ontology Builder" is a major UX differentiator in marketing. It allows domain experts to "visually teach the system new concepts" without requiring data scientists.

#### Backend Requirements (ONT-*)

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| ONT-001 | Ontology schema storage | Store entity types, attributes, and relationships in machine-readable format (JSON-LD/OWL compatible) |
| ONT-002 | Entity type management | CRUD operations for entity types with attributes, constraints, and inheritance |
| ONT-003 | Relationship type management | Define relationship types with source/target entity constraints and cardinality |
| ONT-004 | Synonym/alias management | Maintain synonym lists for entity resolution (e.g., "AWS" = "Amazon Web Services") |
| ONT-005 | Entity resolution engine | Resolve text mentions to canonical entities using synonyms and context |
| ONT-006 | Ontology versioning | Track ontology changes with version history and rollback capability |
| ONT-007 | Ontology validation | Validate knowledge entities against ontology schema on ingestion |
| ONT-008 | Ontology import/export | Import/export ontology in standard formats (JSON-LD, OWL, CSV) |

#### Frontend Requirements (FE-009) - 2 weeks

| Sub-ID | Feature | Acceptance Criteria |
|--------|---------|---------------------|
| FE-009a | Ontology graph viewer | Interactive visualization of entity types and relationships |
| FE-009b | Entity type editor | Create/edit entity types with attributes, no code required |
| FE-009c | Relationship type editor | Define relationships between entity types with visual drag-and-drop |
| FE-009d | Synonym manager | Add/edit/delete synonyms for entities with bulk import |
| FE-009e | Ontology version history | View change history, compare versions, restore previous |
| FE-009f | Ontology import wizard | Step-by-step wizard to import from JSON/OWL/CSV |
| FE-009g | Validation dashboard | Show entities failing ontology validation with fix suggestions |

#### Data Model

```yaml
Ontology:
  ontology_id: str (UUID)
  tenant_id: str (FK)
  name: str
  version: int
  description: str
  base_uri: str (e.g., "https://cloud-optimizer.io/ontology/")
  status: enum (DRAFT, ACTIVE, ARCHIVED)
  created_at: datetime
  updated_at: datetime
  created_by: str (FK to User)

EntityType:
  type_id: str (UUID)
  ontology_id: str (FK)
  name: str (e.g., "Vulnerability", "Control", "AWSService")
  parent_type_id: str (FK, nullable - for inheritance)
  description: str
  attributes: list[AttributeDefinition]
  constraints: jsonb
  icon: str (icon name for UI)
  color: str (hex color for UI)
  created_at: datetime

AttributeDefinition:
  name: str
  data_type: enum (STRING, INTEGER, FLOAT, BOOLEAN, DATE, ENUM, REFERENCE)
  required: bool
  default_value: any (nullable)
  enum_values: list[str] (if data_type is ENUM)
  reference_type_id: str (if data_type is REFERENCE)
  validation_pattern: str (regex, nullable)

RelationshipType:
  rel_type_id: str (UUID)
  ontology_id: str (FK)
  name: str (e.g., "MITIGATES", "EXPLOITS", "CONTAINS")
  source_type_id: str (FK to EntityType)
  target_type_id: str (FK to EntityType)
  cardinality: enum (ONE_TO_ONE, ONE_TO_MANY, MANY_TO_MANY)
  inverse_name: str (nullable, e.g., "MITIGATED_BY")
  description: str
  attributes: list[AttributeDefinition] (for relationship properties)

EntitySynonym:
  synonym_id: str (UUID)
  ontology_id: str (FK)
  canonical_name: str (the standard name)
  synonym: str (the alias)
  entity_type_id: str (FK to EntityType)
  case_sensitive: bool (default false)
  context_hint: str (nullable, helps disambiguation)
  source: enum (MANUAL, AUTO_DETECTED, IMPORTED)
  confidence: float (0-1, for auto-detected)
  created_at: datetime

OntologyVersion:
  version_id: str (UUID)
  ontology_id: str (FK)
  version_number: int
  change_summary: str
  changes: jsonb (diff from previous version)
  created_by: str (FK to User)
  created_at: datetime
```

#### API Endpoints

```yaml
# Ontology Management
GET /api/v1/ontology:
  description: Get active ontology for tenant
  auth: JWT
  response:
    ontology: Ontology
    entity_types: list[EntityType]
    relationship_types: list[RelationshipType]

PUT /api/v1/ontology:
  description: Update ontology (creates new version)
  auth: JWT (admin only)
  body:
    entity_types: list[EntityType]
    relationship_types: list[RelationshipType]
    change_summary: string
  response:
    ontology_id: string
    version: int

# Entity Type Management
POST /api/v1/ontology/entity-types:
  description: Create new entity type
  auth: JWT (admin only)
  body: EntityType
  response: EntityType

PUT /api/v1/ontology/entity-types/{type_id}:
  description: Update entity type
  auth: JWT (admin only)
  body: EntityType
  response: EntityType

# Synonym Management
GET /api/v1/ontology/synonyms:
  description: List all synonyms
  auth: JWT
  query:
    entity_type: string (optional filter)
    search: string (optional search)
  response:
    synonyms: list[EntitySynonym]

POST /api/v1/ontology/synonyms/bulk:
  description: Bulk import synonyms
  auth: JWT (admin only)
  body:
    synonyms: list[{canonical_name, synonym, entity_type}]
  response:
    created: int
    updated: int
    errors: list[string]

# Entity Resolution
POST /api/v1/ontology/resolve:
  description: Resolve text to canonical entities
  auth: JWT
  body:
    text: string
    context: string (optional, helps disambiguation)
  response:
    entities: list[{mention, canonical, type, confidence}]

# Version Management
GET /api/v1/ontology/versions:
  description: List ontology versions
  auth: JWT (admin only)
  response:
    versions: list[OntologyVersion]

POST /api/v1/ontology/versions/{version_id}/restore:
  description: Restore previous ontology version
  auth: JWT (admin only)
  response:
    ontology_id: string
    restored_version: int
    new_version: int
```

#### Entity Resolution Algorithm

```python
async def resolve_entity(
    text: str,
    context: str | None,
    ontology: Ontology
) -> list[ResolvedEntity]:
    """
    Resolve text mentions to canonical entities.

    1. Exact match against synonyms (case-insensitive)
    2. Fuzzy match with confidence threshold
    3. Context-based disambiguation
    4. Return top candidates with confidence scores
    """
    candidates = []

    # Step 1: Exact synonym match
    exact_matches = await synonym_store.find_exact(text, ontology.id)
    for match in exact_matches:
        candidates.append(ResolvedEntity(
            mention=text,
            canonical=match.canonical_name,
            entity_type=match.entity_type_id,
            confidence=1.0,
            match_type="EXACT"
        ))

    # Step 2: Fuzzy match (if no exact)
    if not candidates:
        fuzzy_matches = await synonym_store.find_fuzzy(
            text, ontology.id, threshold=0.85
        )
        candidates.extend(fuzzy_matches)

    # Step 3: Context disambiguation
    if len(candidates) > 1 and context:
        candidates = await disambiguate_by_context(
            candidates, context, ontology
        )

    # Return sorted by confidence
    return sorted(candidates, key=lambda x: x.confidence, reverse=True)
```

---

## 5. Core Platform Extensions (Phase 1-2)

> **Note:** These requirements were identified from the legacy Cloud_Optimizer and CloudGuardian codebases. They represent proven functionality that should be migrated to the new platform.

### 5.3 Security Scanning & Analysis

**Priority:** P0 (Business-Critical)
**Effort:** 3 weeks
**Dependencies:** AWS credentials, IB Platform pattern engine

> **Source:** Legacy Cloud_Optimizer security module (125+ services), CloudGuardian skills framework

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| SEC-001 | Resource discovery | Discover and inventory AWS resources across all enabled regions |
| SEC-002 | Vulnerability detection | Identify security vulnerabilities using CVE database and AWS security findings |
| SEC-003 | Configuration assessment | Assess resource configurations against security best practices |
| SEC-004 | Compliance mapping | Map findings to compliance frameworks (SOC2, HIPAA, PCI-DSS, NIST, ISO27001, CIS) |
| SEC-005 | Security posture scoring | Calculate aggregate security score (0-100) with breakdown by category |
| SEC-006 | Remediation guidance | Provide actionable remediation steps for each finding |
| SEC-007 | Finding lifecycle | Track finding status (NEW, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, FALSE_POSITIVE) |
| SEC-008 | Finding SLA | Set severity-based resolution SLAs with alerts |
| SEC-009 | Bulk finding operations | Bulk update status, assign owner, add tags |
| SEC-010 | Finding export | Export findings to CSV, JSON, PDF formats |
| SEC-011 | Scheduled scans | Configure recurring scan schedules (daily, weekly, monthly) |
| SEC-012 | Scan scope configuration | Define scan scope by region, resource type, tags |

#### AWS Resource Scanners

| Scanner | Resources | Security Checks |
|---------|-----------|-----------------|
| IAM Scanner | Users, Roles, Policies, Access Keys | MFA status, key rotation, overly permissive policies, unused credentials |
| S3 Scanner | Buckets, Objects, Policies | Public access, encryption, versioning, logging, CORS |
| EC2 Scanner | Instances, Security Groups, EBS | Public exposure, encryption, IMDSv2, unused volumes |
| RDS Scanner | Instances, Snapshots, Clusters | Encryption, public access, backup retention, minor version updates |
| Lambda Scanner | Functions, Layers | Runtime versions, VPC config, environment variables |
| VPC Scanner | VPCs, Subnets, NACLs, Flow Logs | Default VPC usage, flow logging, NACL rules |
| CloudTrail Scanner | Trails, Events | Multi-region, log validation, encryption |
| KMS Scanner | Keys, Policies | Key rotation, usage, cross-account access |
| Secrets Scanner | Secrets Manager, Parameter Store | Rotation, encryption, access patterns |
| EKS Scanner | Clusters, Node Groups | Public endpoint, logging, secrets encryption |

#### Data Model

```yaml
SecurityScan:
  scan_id: str (UUID)
  tenant_id: str (FK)
  aws_account_id: str
  status: enum (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
  scan_type: enum (FULL, INCREMENTAL, TARGETED)
  scope:
    regions: list[str]
    resource_types: list[str]
    tags: dict[str, str]
  started_at: datetime
  completed_at: datetime (nullable)
  resources_scanned: int
  findings_created: int
  findings_updated: int
  error_message: str (nullable)
  triggered_by: enum (SCHEDULED, MANUAL, WEBHOOK)
  triggered_by_user: str (FK, nullable)

SecurityFinding:
  finding_id: str (UUID)
  tenant_id: str (FK)
  scan_id: str (FK)
  aws_account_id: str
  region: str
  resource_type: str (e.g., "aws_s3_bucket")
  resource_id: str (ARN)
  resource_name: str
  finding_type: str (e.g., "S3_PUBLIC_ACCESS")
  severity: enum (CRITICAL, HIGH, MEDIUM, LOW, INFO)
  status: enum (NEW, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, FALSE_POSITIVE, SUPPRESSED)
  title: str
  description: text
  remediation: text
  evidence: jsonb  # {"actual": "...", "expected": "...", "diff": "..."}
  compliance_mappings: list[ComplianceMapping]
  first_seen_at: datetime
  last_seen_at: datetime
  resolved_at: datetime (nullable)
  resolved_by: str (FK, nullable)
  sla_due_at: datetime (nullable)
  assigned_to: str (FK, nullable)
  tags: list[str]
  risk_score: float (0-100)

ComplianceMapping:
  framework: str (e.g., "SOC2", "PCI-DSS")
  control_id: str (e.g., "CC6.1", "1.2.3")
  control_name: str
  status: enum (PASS, FAIL, NOT_APPLICABLE)

SecurityPosture:
  posture_id: str (UUID)
  tenant_id: str (FK)
  aws_account_id: str
  calculated_at: datetime
  overall_score: int (0-100)
  category_scores:
    identity: int
    data_protection: int
    network: int
    logging: int
    incident_response: int
  finding_summary:
    critical: int
    high: int
    medium: int
    low: int
    info: int
  compliance_scores:
    - framework: str
      score: int
      passed: int
      failed: int
      not_applicable: int
  trend: enum (IMPROVING, STABLE, DECLINING)
  trend_percentage: float
```

#### API Endpoints

```yaml
POST /api/v1/security/scans:
  description: Start a new security scan
  auth: JWT
  body:
    aws_account_id: string
    scan_type: enum (default FULL)
    scope:
      regions: list[string] (optional, default all)
      resource_types: list[string] (optional, default all)
      tags: object (optional)
  response:
    scan_id: string
    status: "PENDING"

GET /api/v1/security/scans:
  description: List security scans
  auth: JWT
  query:
    aws_account_id: string (optional)
    status: enum (optional)
    limit: int (default 20)
    offset: int (default 0)
  response:
    scans: list[SecurityScan]
    total: int

GET /api/v1/security/scans/{scan_id}:
  description: Get scan details and progress
  auth: JWT
  response:
    scan: SecurityScan
    progress: ScanProgress

GET /api/v1/security/findings:
  description: List findings with filters
  auth: JWT
  query:
    aws_account_id: string (optional)
    severity: list[enum] (optional)
    status: list[enum] (optional)
    resource_type: string (optional)
    compliance_framework: string (optional)
    search: string (optional, full-text)
    sort_by: string (default "-severity,-first_seen_at")
    limit: int (default 50)
    offset: int (default 0)
  response:
    findings: list[SecurityFinding]
    total: int
    summary:
      by_severity: object
      by_status: object

PATCH /api/v1/security/findings/{finding_id}:
  description: Update finding status or assignment
  auth: JWT
  body:
    status: enum (optional)
    assigned_to: string (optional)
    tags: list[string] (optional)
    notes: string (optional)
  response:
    finding: SecurityFinding

POST /api/v1/security/findings/bulk:
  description: Bulk update findings
  auth: JWT
  body:
    finding_ids: list[string]
    update:
      status: enum (optional)
      assigned_to: string (optional)
      tags: list[string] (optional)
  response:
    updated: int
    failed: list[{id, error}]

GET /api/v1/security/posture:
  description: Get security posture summary
  auth: JWT
  query:
    aws_account_id: string (optional, default all)
  response:
    posture: SecurityPosture
    recommendations: list[Recommendation]

GET /api/v1/security/compliance/{framework}:
  description: Get compliance status for a framework
  auth: JWT
  query:
    aws_account_id: string (optional)
  response:
    framework: string
    overall_score: int
    controls: list[ControlStatus]
    gaps: list[ComplianceGap]
```

---

### 5.4 Document Management

**Priority:** P2 (Medium)
**Effort:** 1 week
**Dependencies:** S3 or local storage, tenant context

> **Source:** Legacy Cloud_Optimizer document management module (20 routers, 121 endpoints)

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| DOC-001 | Document upload | Upload documents with metadata (compliance evidence, reports, policies) |
| DOC-002 | Storage abstraction | Support S3 and local filesystem backends |
| DOC-003 | Document versioning | Track document versions with diff capability |
| DOC-004 | Document categories | Organize documents by type (EVIDENCE, REPORT, POLICY, PROCEDURE) |
| DOC-005 | Access control | Document-level permissions (tenant-wide, role-based, user-specific) |
| DOC-006 | Document search | Full-text search across document metadata and content |
| DOC-007 | Bulk operations | Bulk upload, download, delete operations |
| DOC-008 | Retention policies | Configurable retention periods with auto-archive/delete |

#### Data Model

```yaml
Document:
  document_id: str (UUID)
  tenant_id: str (FK)
  filename: str
  display_name: str
  mime_type: str
  size_bytes: int
  category: enum (EVIDENCE, REPORT, POLICY, PROCEDURE, OTHER)
  storage_backend: enum (S3, LOCAL)
  storage_path: str
  checksum: str (SHA-256)
  metadata: jsonb
  tags: list[str]
  version: int
  parent_version_id: str (FK, nullable)
  uploaded_by: str (FK)
  uploaded_at: datetime
  retention_until: datetime (nullable)
  is_archived: bool (default false)
  archived_at: datetime (nullable)

DocumentAccess:
  access_id: str (UUID)
  document_id: str (FK)
  access_type: enum (TENANT, ROLE, USER)
  access_target: str (role name or user_id)
  permission: enum (READ, WRITE, DELETE)
  granted_by: str (FK)
  granted_at: datetime
  expires_at: datetime (nullable)
```

#### API Endpoints

```yaml
POST /api/v1/documents:
  description: Upload a document
  auth: JWT
  content-type: multipart/form-data
  body:
    file: binary
    display_name: string (optional)
    category: enum
    metadata: object (optional)
    tags: list[string] (optional)
  response:
    document: Document

GET /api/v1/documents:
  description: List documents
  auth: JWT
  query:
    category: enum (optional)
    tags: list[string] (optional)
    search: string (optional)
    limit: int (default 20)
  response:
    documents: list[Document]
    total: int

GET /api/v1/documents/{document_id}/download:
  description: Download document
  auth: JWT
  response: binary stream with Content-Disposition

DELETE /api/v1/documents/{document_id}:
  description: Delete document (soft delete with retention)
  auth: JWT
  response:
    deleted: bool
    retention_until: datetime
```

---

### 5.5 API Key Management

**Priority:** P1 (High)
**Effort:** 1 week
**Dependencies:** User management, tenant context

> **Source:** Legacy Cloud_Optimizer API key management

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| API-001 | Key generation | Generate secure API keys with configurable prefix |
| API-002 | Key scoping | Scope keys to specific permissions/resources |
| API-003 | Key expiration | Set expiration dates with auto-disable |
| API-004 | Key rotation | Support key rotation with grace period |
| API-005 | Key revocation | Immediate key revocation with audit trail |
| API-006 | Usage tracking | Track API key usage (requests, last used, endpoints) |
| API-007 | Rate limits | Per-key rate limit configuration |

#### Data Model

```yaml
APIKey:
  key_id: str (UUID)
  tenant_id: str (FK)
  user_id: str (FK, creator)
  name: str (human-readable identifier)
  key_prefix: str (first 8 chars, for identification)
  key_hash: str (SHA-256 hash of full key)
  scopes: list[str] (e.g., ["security:read", "cost:read", "scans:write"])
  status: enum (ACTIVE, EXPIRED, REVOKED, ROTATED)
  rate_limit: int (requests per minute, -1 for unlimited)
  expires_at: datetime (nullable)
  last_used_at: datetime (nullable)
  last_used_ip: str (nullable)
  usage_count: int (total requests)
  rotated_from: str (FK to previous key, nullable)
  revoked_at: datetime (nullable)
  revoked_by: str (FK, nullable)
  revocation_reason: str (nullable)
  created_at: datetime
  updated_at: datetime

APIKeyUsage:
  usage_id: str (UUID)
  key_id: str (FK)
  endpoint: str
  method: str
  status_code: int
  response_time_ms: int
  ip_address: str
  user_agent: str
  timestamp: datetime
```

#### API Endpoints

```yaml
POST /api/v1/api-keys:
  description: Generate new API key
  auth: JWT
  body:
    name: string
    scopes: list[string]
    expires_in_days: int (optional)
    rate_limit: int (optional, default tenant limit)
  response:
    key_id: string
    key: string (ONLY returned once, on creation)
    key_prefix: string
    expires_at: datetime

GET /api/v1/api-keys:
  description: List API keys
  auth: JWT
  response:
    keys: list[APIKey] (key field not included)

DELETE /api/v1/api-keys/{key_id}:
  description: Revoke API key
  auth: JWT
  body:
    reason: string (optional)
  response:
    revoked: bool

POST /api/v1/api-keys/{key_id}/rotate:
  description: Rotate API key
  auth: JWT
  body:
    grace_period_hours: int (default 24)
  response:
    old_key_id: string
    new_key_id: string
    new_key: string
    grace_period_ends: datetime

GET /api/v1/api-keys/{key_id}/usage:
  description: Get API key usage statistics
  auth: JWT
  query:
    period: enum (HOUR, DAY, WEEK, MONTH)
  response:
    total_requests: int
    requests_by_endpoint: object
    requests_by_status: object
    last_used: datetime
```

---

### 5.6 Job Management & Background Processing

**Priority:** P1 (High)
**Effort:** 2 weeks
**Dependencies:** Redis/message queue, PostgreSQL

> **Source:** Legacy Cloud_Optimizer job orchestration (26 routers, 175 endpoints for monitoring)

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| JOB-001 | Job queue | Submit jobs to background queue with priority |
| JOB-002 | Job types | Support scan, export, report generation, ingestion jobs |
| JOB-003 | Job scheduling | Schedule jobs for future execution or recurring |
| JOB-004 | Job progress | Track job progress with percentage and status updates |
| JOB-005 | Job retry | Automatic retry with exponential backoff |
| JOB-006 | Dead letter queue | Move failed jobs to DLQ after max retries |
| JOB-007 | Job cancellation | Cancel pending or running jobs |
| JOB-008 | Job dependencies | Define job dependencies (run after X completes) |
| JOB-009 | Job results | Store and retrieve job results/artifacts |
| JOB-010 | Job monitoring | Dashboard for job queue health and throughput |

#### Data Model

```yaml
BackgroundJob:
  job_id: str (UUID)
  tenant_id: str (FK)
  job_type: enum (SCAN, EXPORT, REPORT, INGESTION, NOTIFICATION, CLEANUP)
  status: enum (PENDING, QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED, DEAD_LETTER)
  priority: int (1-10, higher = more urgent)
  payload: jsonb
  result: jsonb (nullable)
  result_artifact_path: str (nullable, for large results)
  progress_percent: int (0-100)
  progress_message: str (nullable)
  scheduled_at: datetime (nullable, for future jobs)
  started_at: datetime (nullable)
  completed_at: datetime (nullable)
  retry_count: int (default 0)
  max_retries: int (default 3)
  next_retry_at: datetime (nullable)
  error_message: str (nullable)
  error_stack: text (nullable)
  depends_on: list[str] (job IDs)
  created_by: str (FK)
  created_at: datetime
  updated_at: datetime

JobSchedule:
  schedule_id: str (UUID)
  tenant_id: str (FK)
  job_type: enum
  name: str
  description: str
  payload_template: jsonb
  cron_expression: str
  timezone: str
  is_active: bool
  last_run_at: datetime (nullable)
  next_run_at: datetime
  created_by: str (FK)
  created_at: datetime

DeadLetterEntry:
  entry_id: str (UUID)
  job_id: str (FK)
  tenant_id: str (FK)
  failure_reason: str
  failure_count: int
  last_attempt_at: datetime
  payload_snapshot: jsonb
  error_history: list[{timestamp, error, stack}]
  requeued_at: datetime (nullable)
  requeued_by: str (FK, nullable)
  discarded_at: datetime (nullable)
  discarded_by: str (FK, nullable)
  created_at: datetime
```

#### API Endpoints

```yaml
POST /api/v1/jobs:
  description: Submit a background job
  auth: JWT
  body:
    job_type: enum
    payload: object
    priority: int (optional, default 5)
    scheduled_at: datetime (optional)
    depends_on: list[string] (optional)
  response:
    job_id: string
    status: string
    estimated_start: datetime

GET /api/v1/jobs:
  description: List jobs
  auth: JWT
  query:
    job_type: enum (optional)
    status: list[enum] (optional)
    limit: int (default 20)
  response:
    jobs: list[BackgroundJob]
    total: int

GET /api/v1/jobs/{job_id}:
  description: Get job details and progress
  auth: JWT
  response:
    job: BackgroundJob

POST /api/v1/jobs/{job_id}/cancel:
  description: Cancel a job
  auth: JWT
  response:
    cancelled: bool

GET /api/v1/jobs/dead-letter:
  description: List dead letter queue entries
  auth: JWT (admin)
  response:
    entries: list[DeadLetterEntry]
    total: int

POST /api/v1/jobs/dead-letter/{entry_id}/requeue:
  description: Requeue a dead letter entry
  auth: JWT (admin)
  response:
    new_job_id: string

POST /api/v1/jobs/schedules:
  description: Create a job schedule
  auth: JWT
  body:
    job_type: enum
    name: string
    cron_expression: string
    timezone: string
    payload_template: object
  response:
    schedule: JobSchedule

GET /api/v1/jobs/stats:
  description: Get job queue statistics
  auth: JWT
  response:
    pending: int
    running: int
    completed_today: int
    failed_today: int
    dead_letter_count: int
    average_duration_ms: int
    throughput_per_hour: int
```

---

### 5.7 Advanced Monitoring & Health

**Priority:** P1 (High)
**Effort:** 1 week
**Dependencies:** Prometheus metrics, job system

> **Source:** Legacy Cloud_Optimizer monitoring module (26 routers, 175 endpoints)

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| MON-001 | Health endpoints | Kubernetes-compatible liveness, readiness, startup probes |
| MON-002 | Dependency health | Check health of all dependencies (DB, Redis, AWS, IB) |
| MON-003 | SLO monitoring | Track SLO metrics (availability, latency, error rate) |
| MON-004 | Circuit breaker | Automatic circuit breaker for failing dependencies |
| MON-005 | Alerting rules | Configurable alerting thresholds and channels |
| MON-006 | Status page | Public status page with component health |
| MON-007 | Incident tracking | Log incidents with duration and impact |

#### API Endpoints

```yaml
GET /health/live:
  description: Liveness probe (is process running)
  auth: None
  response:
    status: "ok"

GET /health/ready:
  description: Readiness probe (can serve traffic)
  auth: None
  response:
    status: "ok" | "degraded" | "unhealthy"
    checks:
      database: "ok" | "unhealthy"
      redis: "ok" | "unhealthy"
      aws: "ok" | "unhealthy"

GET /health/startup:
  description: Startup probe (has initialization completed)
  auth: None
  response:
    status: "ok" | "initializing"

GET /api/v1/monitoring/status:
  description: Detailed system status
  auth: JWT (admin)
  response:
    overall: enum (OPERATIONAL, DEGRADED, PARTIAL_OUTAGE, MAJOR_OUTAGE)
    components:
      - name: string
        status: enum
        latency_ms: int
        last_check: datetime
    incidents: list[Incident]

GET /api/v1/monitoring/slo:
  description: SLO dashboard data
  auth: JWT (admin)
  query:
    period: enum (DAY, WEEK, MONTH)
  response:
    availability:
      target: float (e.g., 99.9)
      actual: float
      budget_remaining: float
    latency_p95:
      target_ms: int
      actual_ms: int
    error_rate:
      target: float
      actual: float
```

---

### 5.8 Feature Flags

**Priority:** P2 (Medium)
**Effort:** 1 week
**Dependencies:** Tenant system

> **Source:** Legacy Cloud_Optimizer feature flag system

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FLG-001 | Flag definition | Define feature flags with name, description, default state |
| FLG-002 | Flag evaluation | Evaluate flags for current tenant/user context |
| FLG-003 | Tenant overrides | Override flag values per tenant |
| FLG-004 | User targeting | Enable flags for specific users or percentage rollout |
| FLG-005 | Flag audit | Track flag changes with audit trail |
| FLG-006 | Client SDK | Frontend SDK for flag evaluation with caching |

#### Data Model

```yaml
FeatureFlag:
  flag_id: str (UUID)
  key: str (unique, e.g., "enable_dark_mode")
  name: str
  description: str
  flag_type: enum (BOOLEAN, STRING, NUMBER, JSON)
  default_value: any
  is_active: bool
  created_at: datetime
  updated_at: datetime
  created_by: str (FK)

FlagOverride:
  override_id: str (UUID)
  flag_id: str (FK)
  target_type: enum (TENANT, USER, PERCENTAGE)
  target_id: str (tenant_id or user_id, nullable for percentage)
  target_percentage: int (nullable, 0-100 for percentage rollout)
  value: any
  is_active: bool
  created_at: datetime
  created_by: str (FK)
```

#### API Endpoints

```yaml
GET /api/v1/flags:
  description: Get all flags for current context
  auth: JWT
  response:
    flags: object (key -> value map)

GET /api/v1/flags/{flag_key}:
  description: Evaluate a specific flag
  auth: JWT
  response:
    key: string
    value: any
    source: enum (DEFAULT, TENANT_OVERRIDE, USER_OVERRIDE, PERCENTAGE)

POST /api/v1/admin/flags:
  description: Create a feature flag
  auth: JWT (admin)
  body:
    key: string
    name: string
    description: string
    flag_type: enum
    default_value: any
  response:
    flag: FeatureFlag

PUT /api/v1/admin/flags/{flag_id}/overrides:
  description: Set flag override
  auth: JWT (admin)
  body:
    target_type: enum
    target_id: string (optional)
    target_percentage: int (optional)
    value: any
  response:
    override: FlagOverride
```

---

## 6. Phase 4 Extensions

### 6.5 Backup & Disaster Recovery

**Priority:** P1 (High)
**Effort:** 2 weeks
**Dependencies:** S3, PostgreSQL

> **Source:** Legacy Cloud_Optimizer backup module (5 routers, 46 endpoints)

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| BCK-001 | Automated backups | Daily automated database backups with retention |
| BCK-002 | Point-in-time recovery | Support PITR for PostgreSQL |
| BCK-003 | Backup encryption | Encrypt backups at rest using KMS |
| BCK-004 | Cross-region replication | Replicate backups to secondary region |
| BCK-005 | Backup verification | Automated backup integrity verification |
| BCK-006 | Manual backup | On-demand backup creation |
| BCK-007 | Restore testing | Quarterly automated restore testing |
| BCK-008 | DR runbook | Documented disaster recovery procedures |

#### Data Model

```yaml
Backup:
  backup_id: str (UUID)
  backup_type: enum (FULL, INCREMENTAL, WAL)
  status: enum (PENDING, IN_PROGRESS, COMPLETED, FAILED, VERIFYING, VERIFIED)
  source: enum (AUTOMATED, MANUAL)
  storage_location: str (S3 path)
  storage_region: str
  size_bytes: int
  encryption_key_id: str
  started_at: datetime
  completed_at: datetime (nullable)
  retention_until: datetime
  verified_at: datetime (nullable)
  verification_status: enum (PENDING, PASSED, FAILED)
  metadata: jsonb

RestoreOperation:
  restore_id: str (UUID)
  backup_id: str (FK)
  target_environment: str
  status: enum (PENDING, IN_PROGRESS, COMPLETED, FAILED)
  restore_point: datetime (for PITR)
  started_at: datetime
  completed_at: datetime (nullable)
  initiated_by: str (FK)
```

#### API Endpoints

```yaml
POST /api/v1/admin/backups:
  description: Create manual backup
  auth: JWT (admin)
  body:
    backup_type: enum (default FULL)
    retention_days: int (default 30)
  response:
    backup: Backup

GET /api/v1/admin/backups:
  description: List backups
  auth: JWT (admin)
  query:
    status: enum (optional)
    limit: int (default 20)
  response:
    backups: list[Backup]

POST /api/v1/admin/backups/{backup_id}/restore:
  description: Initiate restore from backup
  auth: JWT (admin)
  body:
    target_environment: string
    restore_point: datetime (optional, for PITR)
  response:
    restore: RestoreOperation
```

---

### 6.6 Multi-Cloud Support

**Priority:** P3 (Future)
**Effort:** 4 weeks per cloud provider
**Dependencies:** Security scanning framework

> **Source:** CloudGuardian multi-cloud module (Azure, AWS, GCP integrations)

#### Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| CLD-001 | Cloud provider abstraction | Abstract interface for multi-cloud resource discovery |
| CLD-002 | Azure integration | Support Azure resource scanning (VMs, Storage, Networks) |
| CLD-003 | GCP integration | Support GCP resource scanning (Compute, Storage, VPC) |
| CLD-004 | Unified findings | Normalize findings across cloud providers |
| CLD-005 | Cross-cloud dashboard | Aggregate view across all connected cloud accounts |
| CLD-006 | Cloud comparison | Compare security posture across clouds |

#### Data Model

```yaml
CloudAccount:
  account_id: str (UUID)
  tenant_id: str (FK)
  cloud_provider: enum (AWS, AZURE, GCP)
  account_identifier: str (AWS account ID, Azure subscription, GCP project)
  display_name: str
  credentials_ref: str (reference to secrets manager)
  status: enum (PENDING, ACTIVE, ERROR, DISABLED)
  regions: list[str]
  last_scan_at: datetime (nullable)
  error_message: str (nullable)
  created_at: datetime
```

> **Note:** Detailed Azure and GCP scanner specifications will be added when these features are prioritized.

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Metric | Target |
|--------|--------|
| API p50 latency | <100ms |
| API p95 latency | <500ms |
| API p99 latency | <1000ms |
| Dashboard load time | <2s |
| Scan completion | <60s for standard scan |

### 7.2 Scalability

| Metric | Target |
|--------|--------|
| Concurrent users | 1,000+ |
| Tenants | 10,000+ |
| API requests/sec | 1,000+ |
| Data retention | 2 years |

### 7.3 Availability

| Metric | Target |
|--------|--------|
| Uptime | 99.9% |
| RTO | 4 hours |
| RPO | 1 hour |

### 7.4 Security

| Requirement | Implementation |
|-------------|----------------|
| Authentication | JWT with refresh tokens (15m/7d expiry) |
| Authorization | RBAC with tenant isolation via RLS |
| Data encryption | TLS 1.3 in transit, AES-256 at rest |
| Secrets | AWS Secrets Manager, no hardcoded credentials |
| Audit | Complete audit trail for all operations |
| Compliance | SOC 2 Type II ready |

---

## 8. Quality Requirements

### 8.1 Code Quality

| Metric | Target |
|--------|--------|
| Test coverage | 80%+ |
| Type coverage | 100% |
| Cyclomatic complexity | <10 |
| Max file length | 500 lines |
| Documentation | All public APIs |

### 8.2 Testing Strategy

| Test Type | Coverage Target |
|-----------|-----------------|
| Unit tests | 80%+ |
| Integration tests | Critical paths (auth, billing, tenant) |
| E2E tests | Happy paths + critical error paths |
| Performance tests | Key endpoints (dashboard, scan) |
| Security tests | Auth, injection, tenant isolation |

---

## 9. Appendix: Requirement Traceability

| Phase | Requirements | Business Value | Duration |
|-------|--------------|----------------|----------|
| Phase 1 | MKT-*, TNT-*, TRL-*, USR-*, API-*, FLG-* | Monetization, SaaS operation, API access | 10 weeks |
| Phase 2 | CST-*, DSH-*, MTR-*, NTF-*, KNG-*, SRH-*, NLU-*, ANS-*, SEC-*, JOB-*, MON-*, DOC-* | Feature parity, security scanning, GraphRAG | 16 weeks |
| Phase 3 | FE-*, FBK-* | User experience, continuous learning | 10 weeks |
| Phase 4 | SSO-*, ANL-*, AUD-*, ONT-*, BCK-*, CLD-* | Enterprise features, DR, multi-cloud | 12 weeks |
| Buffer | Integration, hardening | Quality and stability | 4 weeks |
| **Total** | | | **52 weeks** |

> **Note:** Timeline increased from 43 to 52 weeks to include legacy Cloud_Optimizer and CloudGuardian functionality (security scanning, backup/DR, job management, document management, API keys, feature flags, monitoring, multi-cloud support).

### Requirement Prefixes

| Prefix | Category | Count | Source |
|--------|----------|-------|--------|
| MKT-* | AWS Marketplace | 5 | Original |
| TNT-* | Multi-Tenant | 9 | Original |
| TRL-* | Trial Management | 6 | Original |
| USR-* | User Management | 7 | Original |
| CST-* | Cost Optimization | 5 | Original |
| DSH-* | Dashboard APIs | 5 | Original |
| MTR-* | Prometheus Metrics | 4 | Original |
| NTF-* | Notification System | 5 | Original |
| KNG-* | Knowledge Ingestion | 14 | Original |
| SRH-* | Hybrid Search | 6 | Marketing Alignment |
| NLU-* | Natural Language Understanding | 6 | Marketing Alignment |
| ANS-* | Answer Generation | 8 | Marketing Alignment |
| FE-* | Frontend | 50+ (sub-requirements) | Original |
| FBK-* | User Feedback Loop | 7 | Marketing Alignment |
| SSO-* | OAuth/OIDC | 4 | Original |
| ANL-* | Advanced Analytics | 4 | Original |
| AUD-* | Audit & Compliance | 4 | Original |
| ONT-* | Ontology Management | 8 | Marketing Alignment |
| **SEC-*** | **Security Scanning** | **12** | **Legacy CO** |
| **DOC-*** | **Document Management** | **8** | **Legacy CO** |
| **API-*** | **API Key Management** | **7** | **Legacy CO** |
| **JOB-*** | **Job Management & DLQ** | **10** | **Legacy CO** |
| **MON-*** | **Advanced Monitoring** | **7** | **Legacy CO** |
| **FLG-*** | **Feature Flags** | **6** | **Legacy CO** |
| **BCK-*** | **Backup & Recovery** | **8** | **Legacy CO** |
| **CLD-*** | **Multi-Cloud Support** | **6** | **CloudGuardian** |
| **Total** | | **~221** | |

### Legacy System Coverage

Requirements migrated from legacy systems:

| Source | Components | Requirements Added |
|--------|------------|-------------------|
| **Cloud_Optimizer** | 159 routers, 116 services | SEC-*, DOC-*, API-*, JOB-*, MON-*, FLG-*, BCK-* |
| **CloudGuardian** | 13 components, 34 features | CLD-*, multi-cloud abstractions |

#### AWS Security Scanners (SEC-*)

| Scanner | Coverage |
|---------|----------|
| IAM Scanner | Users, Roles, Policies, Access Keys |
| S3 Scanner | Buckets, Objects, Policies |
| EC2 Scanner | Instances, Security Groups, EBS |
| RDS Scanner | Instances, Snapshots, Clusters |
| Lambda Scanner | Functions, Layers |
| VPC Scanner | VPCs, Subnets, NACLs, Flow Logs |
| CloudTrail Scanner | Trails, Events |
| KMS Scanner | Keys, Policies |
| Secrets Scanner | Secrets Manager, Parameter Store |
| EKS Scanner | Clusters, Node Groups |

#### Compliance Frameworks (SEC-004)

| Framework | Coverage |
|-----------|----------|
| SOC 2 | Type I, Type II controls |
| HIPAA | PHI protection requirements |
| PCI-DSS | Payment card security |
| NIST | 800-53 security controls |
| ISO 27001 | Information security |
| CIS Benchmarks | AWS hardening guides |

### Marketing Alignment

The following requirements directly support key marketing claims:

| Marketing Claim | Requirement IDs |
|-----------------|-----------------|
| "Vector + Graph + Pattern Matching" | SRH-001 to SRH-006 |
| "Natural Language Understanding" | NLU-001 to NLU-006 |
| "Evidence-Based Answers" | ANS-001 to ANS-008, KNG-* |
| "95%+ Answer Accuracy" | ANS-002 (confidence scoring), quality metrics |
| "<2 Second Response Time" | SRH-006, NLU performance targets |
| "No-Code Ontology Builder" | ONT-001 to ONT-008, FE-009a to FE-009g |
| "Continuous Learning from Experts" | FBK-001 to FBK-007, FE-008a to FE-008e |
| "Cross-Domain Intelligence" | ANS-008, SRH-005 |
| "Ranked Recommendations" | ANS-004, recommendation algorithm |
| "Comprehensive Security Scanning" | SEC-001 to SEC-012, 10 AWS scanners |
| "Compliance Framework Support" | SEC-004, 6 frameworks |
| "Enterprise-Grade Reliability" | BCK-001 to BCK-008, MON-* |
| "Multi-Cloud Support" | CLD-001 to CLD-006 |

### GraphRAG Query Pipeline

The full GraphRAG query pipeline is now specified:

```
User Query → NLU Parse → Hybrid Search → Answer Generation → Response
    │            │              │                │
    │            │              │                └── ANS-001 to ANS-008
    │            │              └── SRH-001 to SRH-006
    │            └── NLU-001 to NLU-006
    └── Natural Language Input

Feedback Loop: FBK-001 to FBK-007 (continuous improvement)
```

### Security Scanning Pipeline

```
AWS Account → Resource Discovery → Configuration Analysis → Finding Generation
      │              │                    │                      │
      │              │                    │                      └── SEC-007 (lifecycle)
      │              │                    └── SEC-002, SEC-003 (detection)
      │              └── SEC-001 (discovery)
      └── TenantAWSAccount

Compliance Mapping: SEC-004 (6 frameworks)
Posture Scoring: SEC-005 (0-100 with categories)
```

### Background Job Pipeline

```
Job Submission → Queue → Worker → Result Storage
      │           │        │            │
      │           │        │            └── JOB-009
      │           │        └── JOB-004 (progress), JOB-005 (retry)
      │           └── JOB-001 (priority queue)
      └── JOB-002 (job types)

Dead Letter: JOB-006 (failed jobs)
Scheduling: JOB-003 (cron-based)
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.5 | 2025-11-30 | **Major update:** Added legacy Cloud_Optimizer and CloudGuardian requirements: Security Scanning (SEC-001 to SEC-012, 10 scanners, 6 compliance frameworks), Document Management (DOC-001 to DOC-008), API Key Management (API-001 to API-007), Job Management & DLQ (JOB-001 to JOB-010), Advanced Monitoring (MON-001 to MON-007), Feature Flags (FLG-001 to FLG-006), Backup & Recovery (BCK-001 to BCK-008), Multi-Cloud Support (CLD-001 to CLD-006). Total requirements increased from ~157 to ~221. Timeline extended to 52 weeks. |
| 2.4 | 2025-11-30 | Added NLU (NLU-001 to 006) and Answer Generation (ANS-001 to 008) for complete GraphRAG pipeline |
| 2.3 | 2025-11-30 | Added Hybrid Search (SRH-*), User Feedback Loop (FBK-*, FE-008), Ontology Management (ONT-*, FE-009) for marketing alignment |
| 2.2 | 2025-11-30 | Added Knowledge Ingestion System (KNG-*) requirements for expert system foundation |
| 2.1 | 2025-11-30 | Doubled timelines, added tenant lifecycle, AWS Marketplace tech spec, risk assessment |
| 2.0 | 2025-11-30 | Initial v2 requirements |
