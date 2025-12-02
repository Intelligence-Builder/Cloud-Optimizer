# 6.2 AWS Marketplace Integration

## Parent Epic
Epic 6: MVP Phase 1 - Container Product Foundation

## Overview

Integrate Cloud Optimizer with AWS Marketplace for container product distribution. This enables license validation, usage metering, and trial management through AWS Marketplace APIs.

## Background

Cloud Optimizer is distributed as an **AWS Marketplace Container Product** with:
- 14-day free trial period
- Usage-based pricing (scans, chat questions, document analysis)
- Automatic license validation on container startup
- Usage metering for billing

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| MKT-001 | License validation | `RegisterUsage` API call on startup, handles VALID/TRIAL/EXPIRED states |
| MKT-002 | Usage metering | `MeterUsage` API reports dimensions: SecurityScans, ChatQuestions, DocumentAnalysis |
| MKT-003 | Trial enforcement | 14-day trial with limits, graceful expiration handling |
| MKT-004 | Entitlement check | Hourly entitlement validation, handles subscription changes |
| MKT-005 | Subscription handling | Graceful degradation on subscription issues, clear error messages |

## Technical Specification

### Marketplace Product Configuration

```yaml
Product:
  Type: Container
  DeliveryMethod: AWS Marketplace Container
  PricingModel: Usage-Based

  Dimensions:
    - Name: SecurityScans
      Description: Number of AWS account scans performed
      Unit: Scans
      PricePerUnit: $0.50

    - Name: ChatQuestions
      Description: Security Q&A questions asked
      Unit: Questions
      PricePerUnit: $0.02

    - Name: DocumentAnalysis
      Description: Architecture documents analyzed
      Unit: Documents
      PricePerUnit: $0.25

  Trial:
    Duration: 14 days
    Limits:
      SecurityScans: 50
      ChatQuestions: 500
      DocumentAnalysis: 20
```

### License Validation Service

```python
# src/cloud_optimizer/marketplace/license.py
from enum import Enum
import boto3

class LicenseStatus(Enum):
    VALID = "valid"           # Paid subscription active
    TRIAL = "trial"           # In trial period
    TRIAL_EXPIRED = "trial_expired"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    INVALID = "invalid"

class MarketplaceLicenseValidator:
    def __init__(self, product_code: str):
        self.product_code = product_code
        self.client = boto3.client('meteringmarketplace')

    async def validate_on_startup(self) -> LicenseStatus:
        """Called when container starts."""
        try:
            response = self.client.register_usage(
                ProductCode=self.product_code,
                PublicKeyVersion=1,
            )
            logger.info(
                "License validated",
                customer_id=response.get("CustomerIdentifier"),
                product_code=self.product_code,
            )
            return LicenseStatus.VALID

        except self.client.exceptions.CustomerNotEntitledException:
            # No paid subscription - check for trial
            return await self._check_trial_status()

        except self.client.exceptions.CustomerNotSubscribedException:
            logger.warning("Subscription expired or cancelled")
            return LicenseStatus.SUBSCRIPTION_EXPIRED

        except Exception as e:
            logger.error("License validation failed", error=str(e))
            return LicenseStatus.INVALID

    async def _check_trial_status(self) -> LicenseStatus:
        """Check if trial is active or expired."""
        trial_start = await self._get_trial_start_date()
        if trial_start is None:
            # First run - start trial
            await self._start_trial()
            return LicenseStatus.TRIAL

        days_elapsed = (datetime.utcnow() - trial_start).days
        if days_elapsed > 14:
            return LicenseStatus.TRIAL_EXPIRED

        return LicenseStatus.TRIAL
```

### Usage Metering Service

```python
# src/cloud_optimizer/marketplace/metering.py
class UsageMeteringService:
    DIMENSIONS = {
        "scan": "SecurityScans",
        "chat": "ChatQuestions",
        "document": "DocumentAnalysis",
    }

    def __init__(self, product_code: str, enabled: bool = True):
        self.product_code = product_code
        self.enabled = enabled
        self.client = boto3.client('meteringmarketplace')
        self._buffer: List[UsageRecord] = []
        self._buffer_lock = asyncio.Lock()

    async def record_usage(self, dimension: str, quantity: int = 1):
        """Record usage for billing."""
        if not self.enabled:
            return

        if dimension not in self.DIMENSIONS:
            raise ValueError(f"Invalid dimension: {dimension}")

        async with self._buffer_lock:
            self._buffer.append(UsageRecord(
                dimension=self.DIMENSIONS[dimension],
                quantity=quantity,
                timestamp=datetime.utcnow(),
            ))

        # Flush if buffer exceeds threshold
        if len(self._buffer) >= 10:
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Send buffered usage to Marketplace."""
        async with self._buffer_lock:
            if not self._buffer:
                return

            records = self._buffer.copy()
            self._buffer.clear()

        # Aggregate by dimension
        aggregated = self._aggregate_records(records)

        for dimension, quantity in aggregated.items():
            try:
                self.client.meter_usage(
                    ProductCode=self.product_code,
                    Timestamp=datetime.utcnow(),
                    UsageDimension=dimension,
                    UsageQuantity=quantity,
                )
                logger.info("Usage metered", dimension=dimension, quantity=quantity)
            except Exception as e:
                logger.error("Metering failed", dimension=dimension, error=str(e))
                # Re-add to buffer for retry
                self._buffer.extend([
                    UsageRecord(dimension=dimension, quantity=quantity, timestamp=datetime.utcnow())
                ])
```

### License Middleware

```python
# src/cloud_optimizer/middleware/license.py
class LicenseMiddleware:
    """Enforce license status on API requests."""

    ALWAYS_ALLOWED = ["/health", "/docs", "/openapi.json"]

    def __init__(self, app: ASGIApp, license_service: MarketplaceLicenseValidator):
        self.app = app
        self.license_service = license_service

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]

        # Always allow health checks
        if any(path.startswith(p) for p in self.ALWAYS_ALLOWED):
            await self.app(scope, receive, send)
            return

        # Check license status
        status = await self.license_service.get_cached_status()

        if status in [LicenseStatus.TRIAL_EXPIRED, LicenseStatus.SUBSCRIPTION_EXPIRED]:
            response = JSONResponse(
                status_code=402,
                content={
                    "error": "subscription_required",
                    "message": "Your trial has expired. Please subscribe via AWS Marketplace.",
                    "marketplace_url": "https://aws.amazon.com/marketplace/pp/xxx",
                },
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
```

## Files to Create

```
src/cloud_optimizer/marketplace/
├── __init__.py
├── license.py              # License validation
├── metering.py             # Usage metering
├── models.py               # Pydantic models
└── exceptions.py           # Custom exceptions

src/cloud_optimizer/middleware/
├── __init__.py
└── license.py              # License enforcement middleware

tests/marketplace/
├── __init__.py
├── test_license.py
├── test_metering.py
└── conftest.py             # Mocked AWS clients
```

## Files to Modify

```
src/cloud_optimizer/main.py          # Add license middleware
src/cloud_optimizer/config.py        # Add MARKETPLACE_* settings
src/cloud_optimizer/entrypoint.py    # License validation on startup
```

## Environment Variables

```bash
# Required for Marketplace integration
MARKETPLACE_ENABLED=true
MARKETPLACE_PRODUCT_CODE=abc123xyz
AWS_REGION=us-east-1

# Trial mode (when no Marketplace)
TRIAL_MODE=false
```

## Testing Requirements

### Unit Tests
- [ ] `test_license_valid.py` - Valid subscription returns VALID
- [ ] `test_license_trial.py` - No subscription starts trial
- [ ] `test_license_expired.py` - Expired trial returns TRIAL_EXPIRED
- [ ] `test_metering_record.py` - Usage records buffered correctly
- [ ] `test_metering_flush.py` - Buffer flushed to Marketplace API
- [ ] `test_middleware_expired.py` - 402 returned when expired

### Integration Tests
- [ ] `test_marketplace_integration.py` - Full flow with mocked AWS
- [ ] `test_trial_enforcement.py` - Trial limits enforced

### Mocking Strategy

```python
# tests/marketplace/conftest.py
@pytest.fixture
def mock_marketplace_client():
    with patch('boto3.client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def valid_subscription(mock_marketplace_client):
    mock_marketplace_client.register_usage.return_value = {
        "CustomerIdentifier": "customer-123",
    }
    return mock_marketplace_client
```

## Acceptance Criteria Checklist

- [ ] License validation runs on container startup
- [ ] Valid subscription allows full access
- [ ] Trial mode starts when no subscription exists
- [ ] Trial expires after 14 days
- [ ] API returns 402 when trial/subscription expired
- [ ] Usage metering records all billable actions
- [ ] Metering buffer flushes every 10 records or 60 seconds
- [ ] Metering failures are logged and retried
- [ ] All tests pass with mocked AWS clients
- [ ] Works with LocalStack for local development
- [ ] 80%+ test coverage

## Dependencies

- 6.1 Container Packaging (needs Docker image)

## Blocked By

- 6.1 Container Packaging

## Blocks

- 6.3 Trial Management (uses license status)

## Estimated Effort

1 week

## Labels

`marketplace`, `aws`, `billing`, `mvp`, `phase-1`, `P0`

## Reference Documents

- [DEPLOYMENT.md](../04-operations/DEPLOYMENT.md) - Section 8: AWS Marketplace
- [AWS Marketplace Metering API](https://docs.aws.amazon.com/marketplace/latest/userguide/metering-service.html)
