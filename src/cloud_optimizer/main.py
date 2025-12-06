"""
Cloud Optimizer v2 - FastAPI Application.

Main entry point for the Cloud Optimizer application.
Built on Intelligence-Builder platform for knowledge graph operations.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cloud_optimizer.config import get_settings
from cloud_optimizer.logging.config import LogConfig, configure_logging, get_logger
from cloud_optimizer.middleware.correlation import CorrelationIdMiddleware
from cloud_optimizer.middleware.license import LicenseMiddleware
from cloud_optimizer.middleware.metrics import MetricsMiddleware
from cloud_optimizer.middleware.security_headers import SecurityHeadersMiddleware
from cloud_optimizer.tracing import XRayMiddleware, TracingConfig

# Configure structured logging with PII redaction and correlation IDs
settings = get_settings()
log_config = LogConfig(
    level=settings.log_level,
    format="json",
    service_name="cloud-optimizer",
    environment="development" if settings.debug else "production",
    version=settings.app_version,
    pii_redaction_enabled=True,
)
configure_logging(log_config)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup/shutdown."""
    from cloud_optimizer.marketplace import get_metering_service
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

    # Initialize Usage Metering service
    metering_service = get_metering_service()
    try:
        await metering_service.start()
        app.state.metering_service = metering_service
        logger.info(
            "metering_service_started",
            enabled=metering_service.enabled,
            product_code=metering_service.product_code,
        )
    except Exception as e:
        logger.error("metering_service_start_failed", error=str(e))
        app.state.metering_service = None

    yield

    # Shutdown
    logger.info("shutting_down_cloud_optimizer")

    # Stop metering service and flush remaining records
    if hasattr(app.state, "metering_service") and app.state.metering_service:
        try:
            await app.state.metering_service.stop()
            logger.info("metering_service_stopped")
        except Exception as e:
            logger.error("metering_service_stop_failed", error=str(e))

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

    # Correlation ID middleware for request tracing
    app.add_middleware(CorrelationIdMiddleware)

    # X-Ray distributed tracing middleware (Issue #167)
    # Added after CorrelationIdMiddleware so correlation IDs are available
    xray_config = TracingConfig(
        enabled=settings.xray_enabled if hasattr(settings, "xray_enabled") else True,
        service_name="cloud-optimizer",
    )
    app.add_middleware(XRayMiddleware, config=xray_config)

    # CloudWatch metrics middleware (Issue #166)
    # Records request count, latency, and errors to CloudWatch
    app.add_middleware(MetricsMiddleware)

    # License enforcement middleware
    app.add_middleware(LicenseMiddleware)

    # Security headers middleware (HSTS, X-Frame-Options, etc.)
    app.add_middleware(SecurityHeadersMiddleware)

    # Register routers
    from cloud_optimizer.api.routers import (
        auth,
        aws_accounts,
        chat,
        documents,
        findings,
        health,
        kb,
        security,
        trial,
    )

    # Health endpoints (no prefix for Kubernetes compatibility)
    app.include_router(
        health.router,
        tags=["Health"],
    )

    app.include_router(
        auth.router,
        prefix="/api/v1/auth",
        tags=["Authentication"],
    )

    app.include_router(
        security.router,
        prefix="/api/v1/security",
        tags=["Security Analysis"],
    )

    app.include_router(
        trial.router,
        prefix="/api/v1/trial",
        tags=["Trial Management"],
    )

    app.include_router(
        kb.router,
        prefix="/api/v1/kb",
        tags=["Knowledge Base"],
    )

    app.include_router(
        aws_accounts.router,
        prefix="/api/v1/aws-accounts",
        tags=["AWS Accounts"],
    )

    app.include_router(
        findings.router,
        prefix="/api/v1/findings",
        tags=["Findings"],
    )

    app.include_router(
        chat.router,
        prefix="/api/v1/chat",
        tags=["Chat"],
    )

    app.include_router(
        documents.router,
        prefix="/api/v1/documents",
        tags=["Documents"],
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
