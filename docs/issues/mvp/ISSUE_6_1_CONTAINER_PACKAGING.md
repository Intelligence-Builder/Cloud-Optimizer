# 6.1 Container Packaging

## Parent Epic
Epic 6: MVP Phase 1 - Container Product Foundation

## Overview

Create a production-ready Docker container that bundles Cloud Optimizer (CO) and Intelligence-Builder (IB) into a single deployable image. The container must support one-click deployment via CloudFormation and work with AWS Marketplace.

## Background

Cloud Optimizer is deployed as an **AWS Marketplace Container Product**. CO and IB are bundled together because:
1. Simplified deployment (one container vs. orchestrating multiple)
2. Version synchronization guaranteed
3. Reduced network latency (IB is embedded library)
4. Easier for trial customers to deploy

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| CNT-001 | Docker image packaging | Multi-stage Dockerfile, <500MB image, passes Trivy security scan |
| CNT-002 | Helm chart | Configurable values.yaml, works on EKS, documented |
| CNT-003 | CloudFormation template | One-click deploy with RDS, VPC auto-configuration, <10min setup |
| CNT-004 | Container health checks | Liveness probe at /health, readiness probe, checks DB + IB |
| CNT-005 | Environment configuration | All secrets via AWS Secrets Manager, configmaps for non-secrets |
| CNT-006 | Upgrade mechanism | Zero-downtime updates, automatic DB migrations, rollback capability |

## Technical Specification

### Dockerfile Structure

```dockerfile
# Stage 1: Build
FROM python:3.11-slim as builder
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry export -f requirements.txt > requirements.txt
COPY src/ ./src/
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim as runtime
RUN useradd -m -u 1000 appuser
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY data/compliance/ ./data/compliance/  # Baked-in compliance KB
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
  CMD curl -f http://localhost:8000/health || exit 1
ENTRYPOINT ["python", "-m", "cloud_optimizer.entrypoint"]
```

### Entrypoint Script

```python
# src/cloud_optimizer/entrypoint.py
async def main():
    # 1. Validate environment
    validate_required_env_vars()

    # 2. Wait for database
    await wait_for_database(timeout=60)

    # 3. Run migrations (IB schema first, then CO)
    await run_migrations()

    # 4. Initialize IB Platform
    ib_platform = await initialize_ib_platform()

    # 5. Load compliance knowledge base
    await load_compliance_kb()

    # 6. Validate Marketplace license (if enabled)
    license_status = await validate_marketplace_license()

    # 7. Start FastAPI app
    app = create_app(ib_platform=ib_platform, license_status=license_status)

    # 8. Run with uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()
```

### Health Check Endpoint

```python
@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    components = {
        "database": await check_database(db),
        "ib_platform": await check_ib_platform(),
        "redis": await check_redis() if settings.REDIS_URL else "disabled",
    }

    status = "healthy" if all(v == "ok" for v in components.values() if v != "disabled") else "unhealthy"

    return {
        "status": status,
        "version": settings.VERSION,
        "components": components,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

## Files to Create

```
docker/
├── Dockerfile                    # Multi-stage production build
├── Dockerfile.dev               # Development with hot reload
├── docker-compose.yml           # Local development stack
├── docker-compose.test.yml      # Integration test stack
├── .dockerignore
└── README.md                    # Container documentation

helm/cloud-optimizer/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-prod.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   └── _helpers.tpl
└── README.md

cloudformation/
├── cloud-optimizer-quickstart.yaml    # One-click trial deploy
├── cloud-optimizer-production.yaml    # Production deploy
├── nested/
│   ├── vpc.yaml
│   ├── ecs.yaml
│   ├── rds.yaml
│   └── alb.yaml
└── parameters/
    ├── trial.json
    └── production.json

src/cloud_optimizer/
├── entrypoint.py                # Application entrypoint
└── health.py                    # Health check endpoints
```

## Files to Modify

```
pyproject.toml                   # Add Docker-related dependencies
src/cloud_optimizer/config.py    # Environment variable handling
alembic/env.py                   # Migration configuration
```

## Testing Requirements

### Unit Tests
- [ ] `test_entrypoint.py` - Startup sequence, error handling
- [ ] `test_health.py` - Health check responses, component status

### Integration Tests
- [ ] `test_container_build.py` - Docker build succeeds, image size <500MB
- [ ] `test_container_startup.py` - Container starts, health check passes
- [ ] `test_migrations.py` - Migrations run successfully on fresh DB

### E2E Tests
- [ ] `test_cloudformation_deploy.py` - Template deploys successfully (LocalStack)
- [ ] `test_helm_install.py` - Helm chart installs on kind cluster

## Acceptance Criteria Checklist

- [ ] Docker image builds successfully with `docker build`
- [ ] Image size is <500MB
- [ ] Trivy security scan passes with no HIGH/CRITICAL vulnerabilities
- [ ] Container starts and `/health` returns 200 within 60 seconds
- [ ] CloudFormation template validates (`aws cloudformation validate-template`)
- [ ] CloudFormation creates stack successfully in test account
- [ ] Helm chart installs on local kind cluster
- [ ] Database migrations run automatically on first startup
- [ ] Container restarts cleanly after crash (migrations are idempotent)
- [ ] All secrets loaded from AWS Secrets Manager (no hardcoded values)
- [ ] 80%+ test coverage on new code

## Dependencies

- None (first issue in epic)

## Blocked By

- None

## Blocks

- 6.2 AWS Marketplace Integration (needs container image)
- 6.5 Chat Interface UI (needs running backend)

## Estimated Effort

1.5 weeks

## Labels

`container`, `infrastructure`, `mvp`, `phase-1`, `P0`

## Reference Documents

- [DEPLOYMENT.md](../04-operations/DEPLOYMENT.md) - Container architecture details
- [PHASED_IMPLEMENTATION_PLAN.md](../02-architecture/PHASED_IMPLEMENTATION_PLAN.md) - Dockerfile example
