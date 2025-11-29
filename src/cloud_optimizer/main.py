"""
Cloud Optimizer v2 - FastAPI Application.

Main entry point for the Cloud Optimizer application.
Built on Intelligence-Builder platform for knowledge graph operations.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cloud_optimizer.config import get_settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup/shutdown."""
    from cloud_optimizer.services.intelligence_builder import get_ib_service

    settings = get_settings()

    # Startup
    logger.info(
        "starting_cloud_optimizer",
        version=settings.app_version,
        debug=settings.debug,
        enabled_domains=settings.enabled_domains,
    )

    # Initialize Intelligence-Builder service
    ib_service = get_ib_service()
    try:
        if ib_service.is_available and settings.ib_api_key:
            await ib_service.connect()
            app.state.ib_service = ib_service
            logger.info("ib_service_connected", platform_url=settings.ib_platform_url)
        else:
            logger.warning(
                "ib_service_not_connected",
                sdk_available=ib_service.is_available,
                api_key_set=bool(settings.ib_api_key),
            )
            app.state.ib_service = None
    except Exception as e:
        logger.error("ib_service_connection_failed", error=str(e))
        app.state.ib_service = None

    yield

    # Shutdown
    logger.info("shutting_down_cloud_optimizer")
    if hasattr(app.state, "ib_service") and app.state.ib_service:
        await app.state.ib_service.disconnect()
        logger.info("ib_service_disconnected")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Cloud cost optimization and Well-Architected Framework analysis. "
            "Built on Intelligence-Builder GraphRAG platform."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Basic health check endpoint."""
        return {"status": "healthy", "version": settings.app_version}

    @app.get("/ready")
    async def readiness_check() -> dict[str, str]:
        """Readiness check - verifies dependencies are available."""
        ib_status = "not_configured"
        if hasattr(app.state, "ib_service") and app.state.ib_service:
            if app.state.ib_service.is_connected:
                ib_status = "connected"
            else:
                ib_status = "disconnected"

        return {
            "status": "ready",
            "intelligence_builder": ib_status,
        }

    # Register security analysis router
    from cloud_optimizer.api.routers import security

    app.include_router(
        security.router,
        prefix="/api/v1/security",
        tags=["Security Analysis"],
    )

    return app


# Application instance
app = create_app()


def cli() -> None:
    """CLI entry point for running the application."""
    import uvicorn

    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level))

    uvicorn.run(
        "cloud_optimizer.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    cli()
