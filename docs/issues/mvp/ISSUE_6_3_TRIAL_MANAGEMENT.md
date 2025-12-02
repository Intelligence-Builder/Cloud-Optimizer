# 6.3 Trial Management System

## Parent Epic
Epic 6: MVP Phase 1 - Container Product Foundation

## Overview

Implement trial management system that enforces usage limits during the 14-day trial period, provides clear messaging about trial status, and enables smooth conversion to paid subscription.

## Background

Trial customers need to experience Cloud Optimizer's value quickly while staying within defined limits. The trial system must:
- Track usage against limits (scans, chat questions, documents)
- Provide clear UI messaging about remaining trial quota
- Gracefully handle trial expiration
- Enable easy upgrade path to paid subscription

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| TRL-001 | Trial creation | Auto-create trial on first access, record start date in DB |
| TRL-002 | Trial limits | Enforce: 50 scans, 500 chat questions, 20 documents, 1 AWS account |
| TRL-003 | Trial expiration | Graceful degradation after 14 days, read-only access to existing data |
| TRL-004 | Trial conversion | Clear upgrade CTA, one-click to AWS Marketplace |
| TRL-005 | Trial extension | Admin can extend trial by 7 days (one-time) |
| TRL-006 | Trial notifications | Email/UI notifications at 75%, 90%, 100% of limits and 3 days before expiry |

## Technical Specification

### Trial Configuration

```yaml
trial:
  duration_days: 14
  extension_days: 7  # One-time extension allowed
  limits:
    aws_accounts: 1
    scans_per_day: 5
    total_scans: 50
    chat_questions_per_day: 50
    total_chat_questions: 500
    document_uploads: 20
    findings_stored: 500
    users: 1

  features_enabled:
    - security_chat_qa
    - document_analysis
    - security_scanning
    - cost_analysis_basic
    - compliance_recommendations

  features_disabled:
    - advanced_analytics
    - custom_reports
    - api_access
    - multi_account
    - scheduled_scans
```

### Database Schema

```sql
-- Trial tracking table
CREATE TABLE trials (
    trial_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    extended_at TIMESTAMPTZ,  -- NULL if not extended
    converted_at TIMESTAMPTZ,  -- NULL if not converted
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, expired, converted
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Usage tracking table
CREATE TABLE trial_usage (
    usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trial_id UUID NOT NULL REFERENCES trials(trial_id),
    dimension VARCHAR(50) NOT NULL,  -- scans, chat_questions, documents
    count INTEGER NOT NULL DEFAULT 0,
    last_reset_at TIMESTAMPTZ,  -- For daily limits
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(trial_id, dimension)
);

-- Indexes
CREATE INDEX idx_trials_tenant ON trials(tenant_id);
CREATE INDEX idx_trials_status ON trials(status);
CREATE INDEX idx_trial_usage_trial ON trial_usage(trial_id);
```

### Trial Service

```python
# src/cloud_optimizer/services/trial.py
class TrialService:
    def __init__(self, db: AsyncSession, config: TrialConfig):
        self.db = db
        self.config = config

    async def get_or_create_trial(self, tenant_id: UUID) -> Trial:
        """Get existing trial or create new one."""
        trial = await self._get_trial(tenant_id)
        if trial:
            return trial

        # Create new trial
        trial = Trial(
            tenant_id=tenant_id,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=self.config.duration_days),
            status=TrialStatus.ACTIVE,
        )
        self.db.add(trial)
        await self.db.commit()

        # Initialize usage counters
        for dimension in ["scans", "chat_questions", "documents"]:
            usage = TrialUsage(trial_id=trial.trial_id, dimension=dimension, count=0)
            self.db.add(usage)
        await self.db.commit()

        return trial

    async def check_limit(self, tenant_id: UUID, dimension: str) -> TrialLimitCheck:
        """Check if action is allowed within trial limits."""
        trial = await self.get_or_create_trial(tenant_id)

        # Check if trial is active
        if trial.status == TrialStatus.EXPIRED:
            return TrialLimitCheck(allowed=False, reason="trial_expired")

        if trial.status == TrialStatus.CONVERTED:
            return TrialLimitCheck(allowed=True, reason="paid_subscription")

        # Check usage against limit
        usage = await self._get_usage(trial.trial_id, dimension)
        limit = self.config.limits.get(f"total_{dimension}")

        if usage.count >= limit:
            return TrialLimitCheck(
                allowed=False,
                reason="limit_reached",
                current=usage.count,
                limit=limit,
            )

        return TrialLimitCheck(
            allowed=True,
            current=usage.count,
            limit=limit,
            remaining=limit - usage.count,
        )

    async def record_usage(self, tenant_id: UUID, dimension: str, count: int = 1):
        """Record usage of a trial resource."""
        trial = await self.get_or_create_trial(tenant_id)

        await self.db.execute(
            update(TrialUsage)
            .where(TrialUsage.trial_id == trial.trial_id)
            .where(TrialUsage.dimension == dimension)
            .values(count=TrialUsage.count + count, updated_at=datetime.utcnow())
        )
        await self.db.commit()

        # Check for notification thresholds
        await self._check_notification_thresholds(trial, dimension)

    async def extend_trial(self, tenant_id: UUID) -> Trial:
        """Extend trial by configured days (one-time)."""
        trial = await self._get_trial(tenant_id)

        if trial.extended_at is not None:
            raise TrialAlreadyExtendedException()

        trial.expires_at += timedelta(days=self.config.extension_days)
        trial.extended_at = datetime.utcnow()
        await self.db.commit()

        return trial

    async def get_trial_status(self, tenant_id: UUID) -> TrialStatusResponse:
        """Get comprehensive trial status for UI."""
        trial = await self.get_or_create_trial(tenant_id)
        usage = await self._get_all_usage(trial.trial_id)

        days_remaining = (trial.expires_at - datetime.utcnow()).days
        days_remaining = max(0, days_remaining)

        return TrialStatusResponse(
            status=trial.status,
            started_at=trial.started_at,
            expires_at=trial.expires_at,
            days_remaining=days_remaining,
            can_extend=trial.extended_at is None and trial.status == TrialStatus.ACTIVE,
            usage={
                "scans": UsageInfo(
                    current=usage.get("scans", 0),
                    limit=self.config.limits.total_scans,
                ),
                "chat_questions": UsageInfo(
                    current=usage.get("chat_questions", 0),
                    limit=self.config.limits.total_chat_questions,
                ),
                "documents": UsageInfo(
                    current=usage.get("documents", 0),
                    limit=self.config.limits.document_uploads,
                ),
            },
            upgrade_url="https://aws.amazon.com/marketplace/pp/xxx",
        )
```

### Trial Enforcement Middleware

```python
# src/cloud_optimizer/middleware/trial.py
class TrialEnforcementMiddleware:
    """Enforce trial limits on protected endpoints."""

    # Map endpoints to usage dimensions
    METERED_ENDPOINTS = {
        "/api/v1/security/scan": "scans",
        "/api/v1/chat/message": "chat_questions",
        "/api/v1/documents/upload": "documents",
    }

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]

        # Check if endpoint is metered
        dimension = self._get_dimension(path)
        if dimension:
            tenant_id = scope["state"].get("tenant_id")
            check = await self.trial_service.check_limit(tenant_id, dimension)

            if not check.allowed:
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "trial_limit_exceeded",
                        "dimension": dimension,
                        "current": check.current,
                        "limit": check.limit,
                        "message": f"Trial limit reached for {dimension}. Please upgrade.",
                        "upgrade_url": "https://aws.amazon.com/marketplace/pp/xxx",
                    },
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
```

## Files to Create

```
src/cloud_optimizer/services/
└── trial.py                 # Trial management service

src/cloud_optimizer/models/
└── trial.py                 # Trial SQLAlchemy models

src/cloud_optimizer/middleware/
└── trial.py                 # Trial enforcement middleware

src/cloud_optimizer/api/routers/
└── trial.py                 # Trial status API endpoints

alembic/versions/
└── xxx_create_trial_tables.py  # Migration

tests/services/
└── test_trial.py            # Trial service tests
```

## API Endpoints

```
GET  /api/v1/trial/status     # Get trial status and usage
POST /api/v1/trial/extend     # Extend trial (one-time)
```

## Testing Requirements

### Unit Tests
- [ ] `test_trial_creation.py` - New trial created correctly
- [ ] `test_trial_limits.py` - Limits enforced correctly
- [ ] `test_trial_expiration.py` - Expired trials handled
- [ ] `test_trial_extension.py` - Extension works once only
- [ ] `test_usage_recording.py` - Usage tracked correctly

### Integration Tests
- [ ] `test_trial_flow.py` - Full trial lifecycle
- [ ] `test_limit_enforcement.py` - API returns 429 at limit

## Acceptance Criteria Checklist

- [ ] Trial auto-created on first access
- [ ] Usage tracked for scans, chat questions, documents
- [ ] API returns 429 when limit reached
- [ ] Trial expires after 14 days
- [ ] Expired trial allows read-only access
- [ ] Extension adds 7 days (one-time only)
- [ ] Trial status endpoint returns accurate data
- [ ] UI can display trial status from endpoint
- [ ] 80%+ test coverage

## Dependencies

- 6.2 AWS Marketplace Integration (license status)

## Blocked By

- 6.2 AWS Marketplace Integration

## Blocks

- 6.5 Chat Interface UI (needs trial status API)

## Estimated Effort

0.5 weeks

## Labels

`trial`, `billing`, `mvp`, `phase-1`, `P0`
