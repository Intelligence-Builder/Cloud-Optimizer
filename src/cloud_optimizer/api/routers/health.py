"""
Health check endpoint for Cloud Optimizer.

Provides detailed health status for all system components.
"""

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from cloud_optimizer.config import get_settings
from cloud_optimizer.database import get_engine

logger = structlog.get_logger(__name__)

router = APIRouter()


class ComponentStatus(BaseModel):
    """Status of a single component."""

    name: str = Field(..., description="Component name")
    status: str = Field(
        ..., description="Component status: healthy, degraded, unhealthy"
    )
    message: str | None = Field(None, description="Additional status information")
    response_time_ms: float | None = Field(
        None, description="Response time in milliseconds"
    )


class HealthResponse(BaseModel):
    """Overall health check response."""

    status: str = Field(..., description="Overall status: healthy, degraded, unhealthy")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Health check timestamp")
    components: list[ComponentStatus] = Field(..., description="Component statuses")


async def check_database() -> ComponentStatus:
    """
    Check database connectivity and health.

    Returns:
        ComponentStatus: Database health status.
    """
    import time

    start_time = time.time()

    try:
        engine = get_engine()  # type: ignore[no-untyped-call]
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            response_time = (time.time() - start_time) * 1000

            return ComponentStatus(
                name="database",
                status="healthy",
                message="PostgreSQL connection successful",
                response_time_ms=round(response_time, 2),
            )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error("database_health_check_failed", error=str(e))
        return ComponentStatus(
            name="database",
            status="unhealthy",
            message=f"Database connection failed: {str(e)}",
            response_time_ms=round(response_time, 2),
        )


async def check_intelligence_builder(request: Request) -> ComponentStatus:
    """
    Check Intelligence-Builder platform connectivity.

    Args:
        request: FastAPI request object with app state.

    Returns:
        ComponentStatus: Intelligence-Builder health status.
    """
    import time

    start_time = time.time()

    try:
        # Check if IB service is available in app state
        if not hasattr(request.app.state, "ib_service"):
            return ComponentStatus(
                name="intelligence_builder",
                status="degraded",
                message="Intelligence-Builder service not initialized",
                response_time_ms=0.0,
            )

        ib_service = request.app.state.ib_service

        if ib_service is None:
            return ComponentStatus(
                name="intelligence_builder",
                status="degraded",
                message="Intelligence-Builder not configured",
                response_time_ms=0.0,
            )

        # Check connection status
        if not ib_service.is_connected:
            return ComponentStatus(
                name="intelligence_builder",
                status="degraded",
                message="Intelligence-Builder not connected",
                response_time_ms=0.0,
            )

        response_time = (time.time() - start_time) * 1000

        return ComponentStatus(
            name="intelligence_builder",
            status="healthy",
            message="Intelligence-Builder platform connected",
            response_time_ms=round(response_time, 2),
        )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error("intelligence_builder_health_check_failed", error=str(e))
        return ComponentStatus(
            name="intelligence_builder",
            status="unhealthy",
            message=f"Health check failed: {str(e)}",
            response_time_ms=round(response_time, 2),
        )


# Note: Redis health check removed - Redis not used in MVP
# When Redis is added, implement check_redis() function here


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of all system components",
    responses={
        200: {"description": "All components healthy"},
        503: {"description": "One or more components unhealthy"},
    },
)
async def health_check(request: Request, response: Response) -> HealthResponse:
    """
    Perform comprehensive health check of all components.

    Args:
        request: FastAPI request object.
        response: FastAPI response object.

    Returns:
        HealthResponse: Detailed health status of all components.
    """
    settings = get_settings()

    # Check all components (Redis not included - not used in MVP)
    components = [
        await check_database(),
        await check_intelligence_builder(request),
    ]

    # Determine overall status
    component_statuses = [c.status for c in components]

    if all(s == "healthy" for s in component_statuses):
        overall_status = "healthy"
        response.status_code = status.HTTP_200_OK
    elif any(s == "unhealthy" for s in component_statuses):
        overall_status = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        overall_status = "degraded"
        response.status_code = status.HTTP_200_OK

    logger.info(
        "health_check_performed",
        overall_status=overall_status,
        components={c.name: c.status for c in components},
    )

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        components=components,
    )


@router.get(
    "/ready",
    summary="Readiness Check",
    description="Check if the application is ready to accept traffic",
    responses={
        200: {"description": "Application ready"},
        503: {"description": "Application not ready"},
    },
)
async def readiness_check(request: Request, response: Response) -> dict[str, Any]:
    """
    Perform readiness check for Kubernetes/container orchestration.

    Args:
        request: FastAPI request object.
        response: FastAPI response object.

    Returns:
        dict: Readiness status.
    """
    # Check critical dependencies only (database)
    db_status = await check_database()

    if db_status.status == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"ready": False, "reason": db_status.message}

    response.status_code = status.HTTP_200_OK
    return {"ready": True}


@router.get(
    "/live",
    summary="Liveness Check",
    description="Check if the application is alive (for Kubernetes)",
    responses={
        200: {"description": "Application is alive"},
    },
)
async def liveness_check() -> dict[str, bool]:
    """
    Perform liveness check for Kubernetes/container orchestration.

    Returns:
        dict: Simple alive status.
    """
    return {"alive": True}
