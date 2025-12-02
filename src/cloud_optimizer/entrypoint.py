"""
Container entrypoint script for Cloud Optimizer.

Validates environment, waits for dependencies, runs migrations, and starts the application.
"""

import asyncio
import os
import sys
import time
from typing import Optional

import structlog
from sqlalchemy import create_engine, text
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_exponential

from alembic import command
from alembic.config import Config

logger = structlog.get_logger(__name__)


class StartupError(Exception):
    """Raised when startup validation fails."""

    pass


def validate_required_env_vars() -> None:
    """
    Validate that all required environment variables are set.

    Raises:
        StartupError: If any required environment variable is missing.
    """
    required_vars = [
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(
            "missing_required_environment_variables",
            missing_vars=missing_vars,
        )
        raise StartupError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    logger.info("environment_validation_passed", validated_vars=len(required_vars))


@retry(
    stop=stop_after_delay(60),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def wait_for_database() -> None:
    """
    Wait for database to become available.

    Retries connection for up to 60 seconds with exponential backoff.

    Raises:
        Exception: If database is not available after timeout.
    """
    from cloud_optimizer.config import get_settings

    settings = get_settings()
    database_url = settings.database_url_sync

    logger.info(
        "waiting_for_database",
        host=settings.database_host,
        port=settings.database_port,
        database=settings.database_name,
    )

    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("database_connection_successful")
    except Exception as e:
        logger.warning("database_connection_failed", error=str(e), retrying=True)
        raise
    finally:
        engine.dispose()


def run_database_migrations() -> None:
    """
    Run Alembic database migrations.

    Raises:
        Exception: If migrations fail.
    """
    logger.info("running_database_migrations")

    # Get alembic config file path
    alembic_ini_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "alembic.ini",
    )

    if not os.path.exists(alembic_ini_path):
        logger.warning(
            "alembic_config_not_found",
            path=alembic_ini_path,
            skipping_migrations=True,
        )
        return

    try:
        alembic_cfg = Config(alembic_ini_path)
        command.upgrade(alembic_cfg, "head")
        logger.info("database_migrations_completed")
    except Exception as e:
        logger.error("database_migrations_failed", error=str(e))
        raise StartupError(f"Database migrations failed: {e}")


async def initialize_services() -> None:
    """
    Initialize application services.

    Currently validates Intelligence-Builder connectivity if configured.
    """
    from cloud_optimizer.config import get_settings
    from cloud_optimizer.services.intelligence_builder import get_ib_service

    settings = get_settings()

    logger.info("initializing_services")

    # Check Intelligence-Builder service
    ib_service = get_ib_service()
    if ib_service.is_available and settings.ib_api_key:
        try:
            await ib_service.connect()
            logger.info(
                "intelligence_builder_connected",
                platform_url=settings.ib_platform_url,
            )
            await ib_service.disconnect()
        except Exception as e:
            logger.warning(
                "intelligence_builder_connection_failed",
                error=str(e),
                will_retry_on_startup=True,
            )
    else:
        logger.info(
            "intelligence_builder_not_configured",
            sdk_available=ib_service.is_available,
            api_key_set=bool(settings.ib_api_key),
        )

    logger.info("service_initialization_completed")


def start_application() -> None:
    """Start the FastAPI application using uvicorn."""
    import uvicorn

    from cloud_optimizer.config import get_settings

    settings = get_settings()

    logger.info(
        "starting_application",
        host=settings.api_host,
        port=settings.api_port,
        version=settings.app_version,
    )

    # Run uvicorn server
    uvicorn.run(
        "cloud_optimizer.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


async def async_startup() -> None:
    """Run async startup tasks."""
    await initialize_services()


def main() -> int:
    """
    Main entrypoint function.

    Returns:
        int: Exit code (0 for success, 1 for failure).
    """
    try:
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

        logger.info("cloud_optimizer_starting")

        # Step 1: Validate environment variables
        validate_required_env_vars()

        # Step 2: Wait for database
        wait_for_database()

        # Step 3: Run database migrations
        run_database_migrations()

        # Step 4: Initialize services
        asyncio.run(async_startup())

        # Step 5: Start application
        start_application()

        return 0

    except StartupError as e:
        logger.error("startup_failed", error=str(e))
        return 1
    except KeyboardInterrupt:
        logger.info("shutdown_requested")
        return 0
    except Exception as e:
        logger.error("unexpected_error", error=str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
