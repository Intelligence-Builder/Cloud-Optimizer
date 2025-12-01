# Cloud Optimizer v2 - Requirements Ownership Matrix

**Version:** 1.0
**Date:** 2025-11-30
**Purpose:** Define which requirements are owned by Intelligence-Builder (IB) vs Cloud Optimizer (CO)

---

## Executive Summary

The 221 requirements are split between two systems that are deployed together:

| Owner | Requirements | Count | Percentage |
|-------|--------------|-------|------------|
| **Intelligence-Builder (IB)** | Knowledge, Search, NLU, Answers, Feedback, Ontology | 49 | 22% |
| **Cloud Optimizer (CO)** | Application, AWS, UI, Operations | 172 | 78% |

---

## Intelligence-Builder (IB) Requirements

IB provides the **intelligence platform** capabilities. These requirements must be implemented in the IB codebase.

### IB-KNG: Knowledge Ingestion System (14 requirements)

| ID | Requirement | IB Component |
|----|-------------|--------------|
| KNG-001 | Source registry | `ib_platform/ingestion/registry.py` |
| KNG-002 | Document ingestion | `ib_platform/ingestion/document_processor.py` |
| KNG-003 | CVE ingestion | `ib_platform/ingestion/sources/cve.py` |
| KNG-004 | CIS benchmark ingestion | `ib_platform/ingestion/sources/cis.py` |
| KNG-005 | Pricing data ingestion | `ib_platform/ingestion/sources/aws_pricing.py` |
| KNG-006 | Incremental updates | `ib_platform/ingestion/delta_processor.py` |
| KNG-007 | Entity extraction | `ib_platform/patterns/entity_extractor.py` |
| KNG-008 | Relationship mapping | `ib_platform/graph/relationship_mapper.py` |
| KNG-009 | Embedding generation | `ib_platform/embeddings/generator.py` |
| KNG-010 | Deduplication | `ib_platform/graph/deduplication.py` |
| KNG-011 | Quality scoring | `ib_platform/scoring/quality_scorer.py` |
| KNG-012 | Versioning | `ib_platform/graph/versioning.py` |
| KNG-013 | Staleness detection | `ib_platform/monitoring/staleness.py` |
| KNG-014 | Manual curation | `ib_platform/api/curation.py` |

**Migration Source:** Legacy `src/services/graphrag/`, `src/services/semantic/`

---

### IB-SRH: Hybrid Search System (6 requirements)

| ID | Requirement | IB Component |
|----|-------------|--------------|
| SRH-001 | Vector similarity search | `ib_platform/search/vector_search.py` |
| SRH-002 | Graph-enhanced retrieval | `ib_platform/search/graph_retrieval.py` |
| SRH-003 | Hybrid ranking algorithm | `ib_platform/search/hybrid_ranker.py` |
| SRH-004 | Search mode selection | `ib_platform/search/mode_selector.py` |
| SRH-005 | Context assembly | `ib_platform/search/context_builder.py` |
| SRH-006 | Search performance | `ib_platform/search/cache.py` |

**Migration Source:** Legacy `src/services/graphrag/orchestrator.py`, `src/services/graphrag/knowledge_graph_adapter.py`

---

### IB-NLU: Natural Language Understanding (6 requirements)

| ID | Requirement | IB Component |
|----|-------------|--------------|
| NLU-001 | Query intent parsing | `ib_platform/nlu/intent_classifier.py` |
| NLU-002 | Domain classification | `ib_platform/nlu/domain_classifier.py` |
| NLU-003 | Entity extraction from queries | `ib_platform/nlu/query_ner.py` |
| NLU-004 | Query reformulation | `ib_platform/nlu/reformulator.py` |
| NLU-005 | Temporal understanding | `ib_platform/nlu/temporal_parser.py` |
| NLU-006 | Query decomposition | `ib_platform/nlu/decomposer.py` |

**Migration Source:** Legacy `src/services/graphrag/intent_analyzer.py`, `src/services/graphrag/domain/classifier.py`

---

### IB-ANS: Answer Generation Engine (8 requirements)

| ID | Requirement | IB Component |
|----|-------------|--------------|
| ANS-001 | Multi-source synthesis | `ib_platform/generation/synthesizer.py` |
| ANS-002 | Confidence scoring | `ib_platform/generation/confidence.py` |
| ANS-003 | Alternative interpretations | `ib_platform/generation/alternatives.py` |
| ANS-004 | Ranked recommendations | `ib_platform/generation/ranker.py` |
| ANS-005 | Remediation steps | `ib_platform/generation/remediation.py` |
| ANS-006 | Evidence chains | `ib_platform/generation/evidence.py` |
| ANS-007 | Answer formatting | `ib_platform/generation/formatter.py` |
| ANS-008 | Cross-domain insights | `ib_platform/generation/cross_domain.py` |

**Migration Source:** Legacy `src/services/graphrag/answer_generator.py`, `src/services/recommendation_service.py`

---

### IB-FBK: User Feedback Loop (7 requirements)

| ID | Requirement | IB Component |
|----|-------------|--------------|
| FBK-001 | Feedback capture | `ib_platform/feedback/capture.py` |
| FBK-002 | Feedback classification | `ib_platform/feedback/classifier.py` |
| FBK-003 | Expert routing | `ib_platform/feedback/routing.py` |
| FBK-004 | Feedback-to-knowledge pipeline | `ib_platform/feedback/pipeline.py` |
| FBK-005 | Conflict resolution | `ib_platform/feedback/resolution.py` |
| FBK-006 | Learning metrics | `ib_platform/feedback/metrics.py` |
| FBK-007 | Feedback analytics | `ib_platform/feedback/analytics.py` |

**Migration Source:** Legacy `src/api/routers/knowledge_sharing.py` (partial)

---

### IB-ONT: Ontology Management System (8 requirements)

| ID | Requirement | IB Component |
|----|-------------|--------------|
| ONT-001 | Ontology schema storage | `ib_platform/ontology/schema.py` |
| ONT-002 | Entity type management | `ib_platform/ontology/entity_types.py` |
| ONT-003 | Relationship type management | `ib_platform/ontology/relationship_types.py` |
| ONT-004 | Synonym/alias management | `ib_platform/ontology/synonyms.py` |
| ONT-005 | Entity resolution engine | `ib_platform/ontology/resolution.py` |
| ONT-006 | Ontology versioning | `ib_platform/ontology/versioning.py` |
| ONT-007 | Ontology validation | `ib_platform/ontology/validation.py` |
| ONT-008 | Ontology import/export | `ib_platform/ontology/io.py` |

**Migration Source:** Legacy `src/models/knowledge_base.py` (partial), new development required

---

## IB Requirements Summary

| Category | Count | Migration Status | Effort |
|----------|-------|------------------|--------|
| KNG-* Knowledge Ingestion | 14 | 85% exists | 1 week |
| SRH-* Hybrid Search | 6 | 95% exists | 0.5 weeks |
| NLU-* Natural Language | 6 | 70% exists | 1.5 weeks |
| ANS-* Answer Generation | 8 | 75% exists | 1 week |
| FBK-* Feedback Loop | 7 | 55% exists | 2.5 weeks |
| ONT-* Ontology Management | 8 | 50% exists | 3 weeks |
| **Total IB** | **49** | **72% avg** | **9.5 weeks** |

---

## Cloud Optimizer (CO) Requirements

CO provides the **application layer** that uses IB. These requirements are implemented in the CO codebase.

### CO-MKT: AWS Marketplace Integration (5 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| MKT-001 | Entitlement verification | `cloud_optimizer/marketplace/entitlements.py` |
| MKT-002 | Usage metering | `cloud_optimizer/marketplace/metering.py` |
| MKT-003 | Customer registration | `cloud_optimizer/marketplace/registration.py` |
| MKT-004 | Subscription management | `cloud_optimizer/marketplace/subscriptions.py` |
| MKT-005 | Billing portal | `cloud_optimizer/marketplace/billing.py` |

---

### CO-TNT: Multi-Tenant Architecture (9 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| TNT-001 | Tenant isolation | `cloud_optimizer/middleware/tenant_isolation.py` |
| TNT-002 | Tenant provisioning | `cloud_optimizer/services/tenant_service.py` |
| TNT-003 | Tenant configuration | `cloud_optimizer/models/tenant_config.py` |
| TNT-004 | Tenant quotas | `cloud_optimizer/services/quota_service.py` |
| TNT-005 | Tenant context | `cloud_optimizer/middleware/tenant_context.py` |
| TNT-006 | Tenant suspension | `cloud_optimizer/services/tenant_service.py` |
| TNT-007 | Tenant deletion | `cloud_optimizer/services/tenant_service.py` |
| TNT-008 | Tenant data export | `cloud_optimizer/services/export_service.py` |
| TNT-009 | Cross-tenant admin | `cloud_optimizer/api/admin/tenants.py` |

---

### CO-TRL: Trial Management (6 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| TRL-001 | Trial creation | `cloud_optimizer/services/trial_service.py` |
| TRL-002 | Trial limits | `cloud_optimizer/middleware/trial_limits.py` |
| TRL-003 | Trial expiration | `cloud_optimizer/services/trial_service.py` |
| TRL-004 | Trial conversion | `cloud_optimizer/marketplace/conversion.py` |
| TRL-005 | Trial extension | `cloud_optimizer/services/trial_service.py` |
| TRL-006 | Trial notifications | `cloud_optimizer/services/notification_service.py` |

---

### CO-USR: User Management (7 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| USR-001 | User registration | `cloud_optimizer/api/auth/registration.py` |
| USR-002 | User invitation | `cloud_optimizer/services/invitation_service.py` |
| USR-003 | User roles | `cloud_optimizer/middleware/rbac.py` |
| USR-004 | Profile management | `cloud_optimizer/api/users/profile.py` |
| USR-005 | MFA support | `cloud_optimizer/services/mfa_service.py` |
| USR-006 | Session management | `cloud_optimizer/services/session_service.py` |
| USR-007 | Password policies | `cloud_optimizer/services/password_policy.py` |

---

### CO-SEC: Security Scanning & Analysis (12 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| SEC-001 | Resource discovery | `cloud_optimizer/scanners/resource_scanner.py` |
| SEC-002 | Vulnerability detection | `cloud_optimizer/scanners/vulnerability_scanner.py` |
| SEC-003 | Configuration assessment | `cloud_optimizer/scanners/config_scanner.py` |
| SEC-004 | Compliance mapping | `cloud_optimizer/services/compliance_service.py` |
| SEC-005 | Security posture scoring | `cloud_optimizer/services/scoring_service.py` |
| SEC-006 | Remediation guidance | `cloud_optimizer/services/remediation_service.py` |
| SEC-007 | Finding lifecycle | `cloud_optimizer/services/finding_service.py` |
| SEC-008 | Finding SLA | `cloud_optimizer/services/sla_service.py` |
| SEC-009 | Bulk finding operations | `cloud_optimizer/api/findings/bulk.py` |
| SEC-010 | Finding export | `cloud_optimizer/services/export_service.py` |
| SEC-011 | Scheduled scans | `cloud_optimizer/services/scheduler_service.py` |
| SEC-012 | Scan scope configuration | `cloud_optimizer/models/scan_config.py` |

---

### CO-CST: Cost Optimization Engine (5 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| CST-001 | Cost analysis | `cloud_optimizer/scanners/cost_scanner.py` |
| CST-002 | Savings recommendations | `cloud_optimizer/services/savings_service.py` |
| CST-003 | Cost forecasting | `cloud_optimizer/services/forecast_service.py` |
| CST-004 | Cost anomaly detection | `cloud_optimizer/services/anomaly_service.py` |
| CST-005 | Cost allocation | `cloud_optimizer/services/allocation_service.py` |

---

### CO-DSH: Dashboard APIs (5 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| DSH-001 | Overview dashboard | `cloud_optimizer/api/dashboards/overview.py` |
| DSH-002 | Security dashboard | `cloud_optimizer/api/dashboards/security.py` |
| DSH-003 | Cost dashboard | `cloud_optimizer/api/dashboards/cost.py` |
| DSH-004 | Compliance dashboard | `cloud_optimizer/api/dashboards/compliance.py` |
| DSH-005 | Trend analytics | `cloud_optimizer/api/dashboards/trends.py` |

---

### CO-MTR: Prometheus Metrics (4 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| MTR-001 | Request metrics | `cloud_optimizer/middleware/metrics.py` |
| MTR-002 | Business metrics | `cloud_optimizer/services/metrics_service.py` |
| MTR-003 | IB integration metrics | `cloud_optimizer/services/ib_metrics.py` |
| MTR-004 | System metrics | `cloud_optimizer/middleware/system_metrics.py` |

---

### CO-NTF: Notification System (5 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| NTF-001 | Email notifications | `cloud_optimizer/notifications/email.py` |
| NTF-002 | Slack integration | `cloud_optimizer/notifications/slack.py` |
| NTF-003 | Webhook support | `cloud_optimizer/notifications/webhook.py` |
| NTF-004 | Notification preferences | `cloud_optimizer/models/notification_prefs.py` |
| NTF-005 | Alert rules | `cloud_optimizer/services/alert_service.py` |

---

### CO-DOC: Document Management (8 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| DOC-001 | Document upload | `cloud_optimizer/api/documents/upload.py` |
| DOC-002 | Storage abstraction | `cloud_optimizer/storage/backend.py` |
| DOC-003 | Document versioning | `cloud_optimizer/services/document_service.py` |
| DOC-004 | Document categories | `cloud_optimizer/models/document.py` |
| DOC-005 | Access control | `cloud_optimizer/middleware/document_acl.py` |
| DOC-006 | Document search | `cloud_optimizer/services/document_search.py` |
| DOC-007 | Bulk operations | `cloud_optimizer/api/documents/bulk.py` |
| DOC-008 | Retention policies | `cloud_optimizer/services/retention_service.py` |

---

### CO-API: API Key Management (7 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| API-001 | Key generation | `cloud_optimizer/services/api_key_service.py` |
| API-002 | Key scoping | `cloud_optimizer/middleware/api_key_scope.py` |
| API-003 | Key expiration | `cloud_optimizer/services/api_key_service.py` |
| API-004 | Key rotation | `cloud_optimizer/services/api_key_service.py` |
| API-005 | Key revocation | `cloud_optimizer/services/api_key_service.py` |
| API-006 | Usage tracking | `cloud_optimizer/services/usage_service.py` |
| API-007 | Rate limits | `cloud_optimizer/middleware/rate_limit.py` |

---

### CO-JOB: Job Management & Background Processing (10 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| JOB-001 | Job queue | `cloud_optimizer/jobs/queue.py` |
| JOB-002 | Job types | `cloud_optimizer/jobs/types.py` |
| JOB-003 | Job scheduling | `cloud_optimizer/jobs/scheduler.py` |
| JOB-004 | Job progress | `cloud_optimizer/jobs/progress.py` |
| JOB-005 | Job retry | `cloud_optimizer/jobs/retry.py` |
| JOB-006 | Dead letter queue | `cloud_optimizer/jobs/dlq.py` |
| JOB-007 | Job cancellation | `cloud_optimizer/jobs/manager.py` |
| JOB-008 | Job dependencies | `cloud_optimizer/jobs/dependencies.py` |
| JOB-009 | Job results | `cloud_optimizer/jobs/results.py` |
| JOB-010 | Job monitoring | `cloud_optimizer/api/jobs/monitoring.py` |

---

### CO-MON: Advanced Monitoring & Health (7 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| MON-001 | Health endpoints | `cloud_optimizer/api/health.py` |
| MON-002 | Dependency health | `cloud_optimizer/health/dependencies.py` |
| MON-003 | SLO monitoring | `cloud_optimizer/health/slo.py` |
| MON-004 | Circuit breaker | `cloud_optimizer/middleware/circuit_breaker.py` |
| MON-005 | Alerting rules | `cloud_optimizer/services/alert_service.py` |
| MON-006 | Status page | `cloud_optimizer/api/status.py` |
| MON-007 | Incident tracking | `cloud_optimizer/services/incident_service.py` |

---

### CO-FLG: Feature Flags (6 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| FLG-001 | Flag definition | `cloud_optimizer/services/feature_flag_service.py` |
| FLG-002 | Flag evaluation | `cloud_optimizer/middleware/feature_flags.py` |
| FLG-003 | Tenant overrides | `cloud_optimizer/services/feature_flag_service.py` |
| FLG-004 | User targeting | `cloud_optimizer/services/feature_flag_service.py` |
| FLG-005 | Flag audit | `cloud_optimizer/services/audit_service.py` |
| FLG-006 | Client SDK | `cloud_optimizer/api/flags/sdk.py` |

---

### CO-SSO: OAuth2/OIDC Integration (4 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| SSO-001 | OIDC provider support | `cloud_optimizer/auth/oidc.py` |
| SSO-002 | SAML support | `cloud_optimizer/auth/saml.py` |
| SSO-003 | JIT provisioning | `cloud_optimizer/auth/jit.py` |
| SSO-004 | Role mapping | `cloud_optimizer/auth/role_mapping.py` |

---

### CO-ANL: Advanced Analytics (4 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| ANL-001 | Custom reports | `cloud_optimizer/services/report_service.py` |
| ANL-002 | Scheduled reports | `cloud_optimizer/services/scheduled_reports.py` |
| ANL-003 | Data export | `cloud_optimizer/services/export_service.py` |
| ANL-004 | API usage analytics | `cloud_optimizer/services/usage_analytics.py` |

---

### CO-AUD: Audit & Compliance (4 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| AUD-001 | Audit logging | `cloud_optimizer/middleware/audit.py` |
| AUD-002 | Audit search | `cloud_optimizer/api/audit/search.py` |
| AUD-003 | Audit export | `cloud_optimizer/services/audit_export.py` |
| AUD-004 | Retention policy | `cloud_optimizer/services/audit_retention.py` |

---

### CO-BCK: Backup & Disaster Recovery (8 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| BCK-001 | Automated backups | `cloud_optimizer/ops/backup.py` |
| BCK-002 | Point-in-time recovery | `cloud_optimizer/ops/pitr.py` |
| BCK-003 | Backup encryption | `cloud_optimizer/ops/encryption.py` |
| BCK-004 | Cross-region replication | `cloud_optimizer/ops/replication.py` |
| BCK-005 | Backup verification | `cloud_optimizer/ops/verification.py` |
| BCK-006 | Manual backup | `cloud_optimizer/api/ops/backup.py` |
| BCK-007 | Restore testing | `cloud_optimizer/ops/restore_test.py` |
| BCK-008 | DR runbook | Documentation |

---

### CO-CLD: Multi-Cloud Support (6 requirements)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| CLD-001 | Cloud provider abstraction | `cloud_optimizer/providers/base.py` |
| CLD-002 | Azure integration | `cloud_optimizer/providers/azure/` |
| CLD-003 | GCP integration | `cloud_optimizer/providers/gcp/` |
| CLD-004 | Unified findings | `cloud_optimizer/services/finding_normalizer.py` |
| CLD-005 | Cross-cloud dashboard | `cloud_optimizer/api/dashboards/multi_cloud.py` |
| CLD-006 | Cloud comparison | `cloud_optimizer/services/cloud_comparison.py` |

---

### CO-FE: Frontend Application (Implied from Phase 3)

| ID | Requirement | CO Component |
|----|-------------|--------------|
| FE-001 | React application | `frontend/` |
| FE-002 | Login/registration | `frontend/src/pages/Login.tsx` |
| FE-003 | Dashboard | `frontend/src/pages/Dashboard.tsx` |
| FE-004 | Security findings UI | `frontend/src/pages/Findings.tsx` |
| FE-005 | Cost analysis UI | `frontend/src/pages/CostAnalysis.tsx` |
| FE-006 | Settings UI | `frontend/src/pages/Settings.tsx` |

---

## CO Requirements Summary

| Category | Count | Migration Status | Effort |
|----------|-------|------------------|--------|
| MKT-* Marketplace | 5 | 95% exists | 0.5 weeks |
| TNT-* Multi-Tenant | 9 | 95% exists | 0.5 weeks |
| TRL-* Trial | 6 | 95% exists | 0.5 weeks |
| USR-* User Management | 7 | 95% exists | 0.5 weeks |
| SEC-* Security Scanning | 12 | 95% exists | 1.5 weeks |
| CST-* Cost Optimization | 5 | 85% exists | 1 week |
| DSH-* Dashboards | 5 | 90% exists | 1 week |
| MTR-* Metrics | 4 | 90% exists | 0.5 weeks |
| NTF-* Notifications | 5 | 70% exists | 1 week |
| DOC-* Documents | 8 | 95% exists | 0.5 weeks |
| API-* API Keys | 7 | 90% exists | 0.5 weeks |
| JOB-* Job Management | 10 | 85% exists | 1 week |
| MON-* Monitoring | 7 | 90% exists | 0.5 weeks |
| FLG-* Feature Flags | 6 | 80% exists | 1 week |
| SSO-* SSO | 4 | 80% exists | 1 week |
| ANL-* Analytics | 4 | 85% exists | 1 week |
| AUD-* Audit | 4 | 95% exists | 0.5 weeks |
| BCK-* Backup/DR | 8 | 70% exists | 2 weeks |
| CLD-* Multi-Cloud | 6 | 60% exists | 3 weeks |
| FE-* Frontend | 6 | 60% exists | 8 weeks |
| **Total CO** | **128+** | **85% avg** | **~26 weeks** |

---

## Interface: CO → IB SDK

Cloud Optimizer calls Intelligence-Builder through a defined SDK interface:

```python
# cloud_optimizer/ib_sdk/client.py

class IBPlatformClient:
    """SDK for Cloud Optimizer to interact with Intelligence-Builder."""

    # Knowledge Operations
    async def ingest_document(self, doc: Document) -> EntityList: ...
    async def query_knowledge(self, query: str) -> SearchResults: ...
    async def get_entity(self, entity_id: str) -> Entity: ...

    # Search Operations
    async def hybrid_search(self, query: str, mode: SearchMode) -> SearchResults: ...
    async def vector_search(self, embedding: List[float], top_k: int) -> List[Entity]: ...
    async def graph_traverse(self, start: str, hops: int) -> SubGraph: ...

    # NLU Operations
    async def parse_intent(self, query: str) -> Intent: ...
    async def classify_domain(self, query: str) -> DomainClassification: ...
    async def extract_entities(self, text: str) -> List[EntityMention]: ...

    # Answer Generation
    async def generate_answer(self, query: str, context: SearchResults) -> Answer: ...
    async def get_recommendations(self, finding: Finding) -> List[Recommendation]: ...
    async def get_remediation(self, vulnerability: str) -> RemediationSteps: ...

    # Feedback Operations
    async def submit_feedback(self, feedback: Feedback) -> None: ...
    async def get_feedback_status(self, feedback_id: str) -> FeedbackStatus: ...

    # Ontology Operations
    async def resolve_entity(self, mention: str) -> Entity: ...
    async def get_entity_type(self, type_name: str) -> EntityType: ...
```

---

## Phased Development by Owner

### Phase 1: MVP Foundation (Weeks 2-5)

| Owner | Requirements | Focus |
|-------|--------------|-------|
| **CO** | CNT-*, MKT-*, TRL-*, USR-* | Container, Marketplace, Trial, Users |
| **IB** | (existing) | Use existing IB Platform components |

### Phase 2: Core Features (Weeks 6-12)

| Owner | Requirements | Focus |
|-------|--------------|-------|
| **CO** | SEC-*, CST-*, MON-*, JOB-*, DOC-* | Scanning, Cost, Monitoring, Jobs |
| **IB** | KNG-*, SRH-* | Knowledge ingestion, Hybrid search |

### Phase 3: Frontend (Weeks 13-20)

| Owner | Requirements | Focus |
|-------|--------------|-------|
| **CO** | FE-*, DSH-* | React app, Dashboard APIs |
| **IB** | (maintenance) | Bug fixes, performance |

### Phase 4: Advanced (Weeks 21-26)

| Owner | Requirements | Focus |
|-------|--------------|-------|
| **CO** | SSO-*, ANL-*, AUD-*, API-*, FLG-* | SSO, Analytics, Audit |
| **IB** | NLU-*, ANS-* | NLU enhancements, Answer generation |

### Phase 5: Post-MVP (Weeks 27-30)

| Owner | Requirements | Focus |
|-------|--------------|-------|
| **CO** | CLD-*, BCK-* | Multi-cloud, Backup/DR |
| **IB** | FBK-*, ONT-* | Feedback loop, Ontology |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-30 | Initial requirements ownership matrix |
