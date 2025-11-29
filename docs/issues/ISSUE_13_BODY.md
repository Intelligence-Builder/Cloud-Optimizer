## Parent Epic
Part of #3 (Epic 3: Cloud Optimizer v2 Clean Rebuild)

## Reference Documentation
- **See `docs/platform/TECHNICAL_DESIGN.md` Section 8 for SDK design**
- **See `docs/AI_DEVELOPER_GUIDE.md` for IB SDK integration patterns**

## Objective
Build core application structure with FastAPI and IB SDK integration.

## File Structure
```
src/cloud_optimizer/
├── __init__.py
├── main.py              # FastAPI app with lifespan
├── config.py            # Pydantic settings
├── dependencies.py      # Dependency injection
├── exceptions.py        # Custom exceptions
└── api/
    ├── __init__.py
    └── health.py        # Health check endpoints
```

## main.py Implementation
```python
"""Cloud Optimizer v2 - FastAPI Application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .api import health, security
from .dependencies import init_ib_client, close_ib_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting Cloud Optimizer v2")
    await init_ib_client()
    yield
    await close_ib_client()
    logger.info("Shutting down Cloud Optimizer v2")


app = FastAPI(
    title="Cloud Optimizer v2",
    description="AWS Well-Architected optimization powered by Intelligence-Builder",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(security.router)
```

## config.py Implementation
```python
"""Configuration management using Pydantic settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment."""

    # Application
    APP_NAME: str = "Cloud Optimizer v2"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Intelligence-Builder
    IB_PLATFORM_URL: str
    IB_API_KEY: str
    TENANT_ID: str
    IB_TIMEOUT: float = 30.0

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
```

## dependencies.py Implementation
```python
"""Dependency injection for FastAPI."""

from functools import lru_cache
from typing import AsyncGenerator

from intelligence_builder_sdk import IBPlatformClient

from .config import settings

_ib_client: IBPlatformClient | None = None


async def init_ib_client() -> None:
    """Initialize IB client on startup."""
    global _ib_client
    _ib_client = IBPlatformClient(
        base_url=settings.IB_PLATFORM_URL,
        api_key=settings.IB_API_KEY,
        tenant_id=settings.TENANT_ID,
    )
    await _ib_client.connect()


async def close_ib_client() -> None:
    """Close IB client on shutdown."""
    global _ib_client
    if _ib_client:
        await _ib_client.close()


async def get_ib_client() -> IBPlatformClient:
    """Dependency for IB client."""
    if not _ib_client:
        raise RuntimeError("IB client not initialized")
    return _ib_client
```

## Health Endpoints
```python
# api/health.py
from fastapi import APIRouter, Depends
from ..dependencies import get_ib_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "cloud-optimizer-v2"}


@router.get("/health/ready")
async def readiness_check(ib=Depends(get_ib_client)):
    """Readiness check including IB connection."""
    ib_health = await ib.health()
    return {
        "status": "ready",
        "ib_platform": ib_health.status,
    }
```

## Test Scenarios
```python
class TestApplication:
    def test_app_starts()
    def test_health_endpoint()
    def test_readiness_with_ib()

class TestConfiguration:
    def test_settings_from_env()
    def test_required_settings_error()

class TestDependencies:
    async def test_ib_client_lifecycle()
    async def test_get_ib_client_not_initialized()
```

## Acceptance Criteria
- [ ] FastAPI app starts with lifespan management
- [ ] Settings loaded from environment/.env
- [ ] IB client initializes on startup
- [ ] IB client closes on shutdown
- [ ] /health endpoint returns 200
- [ ] /health/ready checks IB connection
- [ ] Structured logging configured
- [ ] All code has type hints
- [ ] Test coverage > 80%
