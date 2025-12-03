"""
E2E Test Fixtures for Cloud Optimizer.

Provides fixtures for end-to-end testing with real docker-compose stack:
- Docker Compose orchestration
- Service health checking
- API client configuration
- Test data setup/teardown

These tests use REAL services - no mocks!
"""

import asyncio
import subprocess
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator

import docker
import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKER_COMPOSE_E2E = PROJECT_ROOT / "docker" / "docker-compose.e2e.yml"
DOCKER_COMPOSE_TEST = PROJECT_ROOT / "docker" / "docker-compose.test.yml"

# Test configuration
API_BASE_URL = "http://localhost:18080"
API_TIMEOUT = 120  # seconds to wait for services to be healthy
POSTGRES_TEST_URL = "postgresql+asyncpg://test:test@localhost:5434/test_intelligence"


# ============================================================================
# Docker Availability Check
# ============================================================================


def is_docker_available() -> bool:
    """Check if Docker is available and running."""
    try:
        client = docker.from_env()
        client.ping()
        client.close()
        return True
    except Exception:
        return False


def skip_if_no_docker() -> pytest.MarkDecorator:
    """Skip test if Docker is not available."""
    return pytest.mark.skipif(
        not is_docker_available(),
        reason="Docker not available - install Docker to run E2E tests",
    )


# ============================================================================
# Docker Compose Management
# ============================================================================


class DockerComposeManager:
    """Manage docker-compose lifecycle for E2E tests."""

    def __init__(self, compose_file: Path, project_name: str = "co-e2e") -> None:
        """Initialize docker-compose manager.

        Args:
            compose_file: Path to docker-compose.yml file
            project_name: Docker compose project name
        """
        self.compose_file = compose_file
        self.project_name = project_name
        self.client = docker.from_env()

    def up(self, services: list[str] | None = None) -> None:
        """Start docker-compose services.

        Args:
            services: Optional list of specific services to start
        """
        cmd = [
            "docker-compose",
            "-f",
            str(self.compose_file),
            "-p",
            self.project_name,
            "up",
            "-d",
        ]
        if services:
            cmd.extend(services)

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to start docker-compose: {result.stderr or result.stdout}"
            )

    def down(self, volumes: bool = True) -> None:
        """Stop and remove docker-compose services.

        Args:
            volumes: Whether to remove volumes
        """
        cmd = [
            "docker-compose",
            "-f",
            str(self.compose_file),
            "-p",
            self.project_name,
            "down",
        ]
        if volumes:
            cmd.append("-v")

        subprocess.run(cmd, capture_output=True, check=False)

    def get_service_logs(self, service: str, tail: int = 50) -> str:
        """Get logs from a service.

        Args:
            service: Service name
            tail: Number of lines to retrieve

        Returns:
            Service logs as string
        """
        try:
            container_name = f"{self.project_name}-{service}-1"
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=tail).decode("utf-8")
            return logs
        except Exception as e:
            return f"Failed to get logs: {e}"

    def is_service_healthy(self, service: str) -> bool:
        """Check if a service is healthy.

        Args:
            service: Service name

        Returns:
            True if service is healthy
        """
        try:
            container_name = f"{self.project_name}-{service}-1"
            container = self.client.containers.get(container_name)
            container.reload()

            # Check container is running
            if container.status != "running":
                return False

            # Check health status if healthcheck is defined
            health = container.attrs.get("State", {}).get("Health", {})
            if health:
                return health.get("Status") == "healthy"

            # If no healthcheck, running status is sufficient
            return True
        except Exception:
            return False


async def wait_for_api_health(
    base_url: str = API_BASE_URL,
    timeout: int = API_TIMEOUT,
    interval: int = 2,
) -> bool:
    """Wait for API to become healthy.

    Args:
        base_url: API base URL
        timeout: Maximum time to wait (seconds)
        interval: Check interval (seconds)

    Returns:
        True if API is healthy, False if timeout

    Raises:
        RuntimeError: If API never becomes healthy
    """
    deadline = time.time() + timeout
    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=10.0) as client:
        while time.time() < deadline:
            try:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    # API is healthy if status is "healthy" or "degraded"
                    # (degraded means IB service might not be connected, which is OK)
                    if data.get("status") in ["healthy", "degraded"]:
                        return True
            except Exception as e:
                last_error = e

            await asyncio.sleep(interval)

    # Timeout reached
    error_msg = f"API health check timeout after {timeout}s"
    if last_error:
        error_msg += f". Last error: {last_error}"
    raise RuntimeError(error_msg)


async def wait_for_postgres_ready(
    connection_url: str = POSTGRES_TEST_URL,
    timeout: int = 60,
    interval: int = 2,
) -> bool:
    """Wait for PostgreSQL to be ready.

    Args:
        connection_url: Database connection URL
        timeout: Maximum time to wait (seconds)
        interval: Check interval (seconds)

    Returns:
        True if database is ready

    Raises:
        RuntimeError: If database never becomes ready
    """
    deadline = time.time() + timeout
    last_error: Exception | None = None

    engine = create_async_engine(connection_url, echo=False)

    while time.time() < deadline:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                await engine.dispose()
                return True
        except Exception as e:
            last_error = e
            await asyncio.sleep(interval)

    await engine.dispose()

    # Timeout reached
    error_msg = f"PostgreSQL readiness check timeout after {timeout}s"
    if last_error:
        error_msg += f". Last error: {last_error}"
    raise RuntimeError(error_msg)


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def docker_compose_manager() -> Generator[DockerComposeManager, None, None]:
    """Provide docker-compose manager for E2E tests."""
    if not is_docker_available():
        pytest.skip("Docker not available")

    # Check if compose file exists
    if not DOCKER_COMPOSE_E2E.exists():
        pytest.skip(f"E2E compose file not found: {DOCKER_COMPOSE_E2E}")

    manager = DockerComposeManager(DOCKER_COMPOSE_E2E, project_name="co-e2e-test")
    yield manager
    manager.client.close()


@pytest.fixture(scope="session")
def docker_compose_up(
    docker_compose_manager: DockerComposeManager,
) -> Generator[DockerComposeManager, None, None]:
    """Start docker-compose stack for E2E tests.

    This fixture:
    1. Starts all services defined in docker-compose.e2e.yml
    2. Waits for services to become healthy
    3. Tears down services after tests complete
    """
    print("\n" + "=" * 60)
    print("Starting E2E Test Environment")
    print("=" * 60)

    # Start services
    try:
        docker_compose_manager.up()
        print("✓ Docker Compose services started")
    except RuntimeError as e:
        pytest.fail(f"Failed to start services: {e}")

    # Wait for critical services to be healthy
    services_to_check = ["postgres-test", "localstack", "app"]
    deadline = time.time() + API_TIMEOUT

    for service in services_to_check:
        print(f"Waiting for {service} to be healthy...")
        while time.time() < deadline:
            if docker_compose_manager.is_service_healthy(service):
                print(f"✓ {service} is healthy")
                break
            time.sleep(2)
        else:
            # Service never became healthy
            logs = docker_compose_manager.get_service_logs(service)
            docker_compose_manager.down()
            pytest.fail(
                f"Service {service} never became healthy.\n"
                f"Last logs:\n{logs}"
            )

    # Additional check: wait for API to respond
    print("Waiting for API to respond...")
    try:
        asyncio.run(wait_for_api_health())
        print("✓ API is healthy and responding")
    except RuntimeError as e:
        logs = docker_compose_manager.get_service_logs("app")
        docker_compose_manager.down()
        pytest.fail(f"API never became healthy: {e}\nLast logs:\n{logs}")

    print("=" * 60)
    print("E2E Environment Ready")
    print("=" * 60 + "\n")

    yield docker_compose_manager

    # Teardown
    print("\n" + "=" * 60)
    print("Tearing Down E2E Test Environment")
    print("=" * 60)
    docker_compose_manager.down(volumes=True)
    print("✓ Services stopped and cleaned up")


@pytest.fixture(scope="session")
async def api_client(
    docker_compose_up: DockerComposeManager,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide async HTTP client configured for E2E API.

    Args:
        docker_compose_up: Ensures services are running

    Yields:
        Configured httpx AsyncClient
    """
    async with httpx.AsyncClient(
        base_url=API_BASE_URL,
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        yield client


@pytest.fixture(scope="session")
async def db_session(
    docker_compose_up: DockerComposeManager,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for E2E tests.

    Args:
        docker_compose_up: Ensures database is running

    Yields:
        SQLAlchemy AsyncSession
    """
    # Wait for database to be ready
    await wait_for_postgres_ready()

    # Create engine and session
    engine = create_async_engine(POSTGRES_TEST_URL, echo=False)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def clean_database(db_session: AsyncSession) -> AsyncGenerator[None, None]:
    """Clean database before and after test.

    This fixture truncates test tables to ensure test isolation.
    """
    # Clean before test
    await _truncate_test_tables(db_session)

    yield

    # Clean after test
    await _truncate_test_tables(db_session)


async def _truncate_test_tables(session: AsyncSession) -> None:
    """Truncate common test tables.

    Args:
        session: Database session
    """
    # List of tables to truncate (add more as needed)
    tables = [
        "security_findings",
        "security_scan_results",
        "aws_accounts",
        "users",
    ]

    try:
        for table in tables:
            # Check if table exists before truncating
            result = await session.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = :table_name
                    )
                """
                ),
                {"table_name": table},
            )
            if result.scalar():
                await session.execute(
                    text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                )
        await session.commit()
    except Exception as e:
        # If truncate fails, it's not critical for E2E tests
        # (tables might not exist yet)
        await session.rollback()
        print(f"Warning: Failed to truncate tables: {e}")


@pytest.fixture
def localstack_endpoint(docker_compose_up: DockerComposeManager) -> str:
    """Provide LocalStack endpoint URL.

    Args:
        docker_compose_up: Ensures LocalStack is running

    Returns:
        LocalStack endpoint URL
    """
    return "http://localhost:4566"


@pytest.fixture
def aws_credentials_for_localstack() -> Dict[str, str]:
    """Provide AWS credentials for LocalStack.

    Returns:
        Dictionary with AWS credentials for LocalStack
    """
    return {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
        "region_name": "us-east-1",
    }


# ============================================================================
# Helper Functions for Tests
# ============================================================================


async def create_test_aws_account(
    api_client: httpx.AsyncClient,
    account_id: str = "123456789012",
    account_name: str = "Test Account",
) -> Dict[str, Any]:
    """Create a test AWS account via API.

    Args:
        api_client: HTTP client
        account_id: AWS account ID
        account_name: Account name

    Returns:
        Created account data

    Raises:
        AssertionError: If account creation fails
    """
    response = await api_client.post(
        "/api/v1/aws-accounts",
        json={
            "account_id": account_id,
            "account_name": account_name,
            "aws_access_key_id": "test_key",
            "aws_secret_access_key": "test_secret",
            "region": "us-east-1",
        },
    )
    assert response.status_code == 201, f"Failed to create account: {response.text}"
    return response.json()


async def trigger_security_scan(
    api_client: httpx.AsyncClient,
    account_id: str,
) -> Dict[str, Any]:
    """Trigger a security scan via API.

    Args:
        api_client: HTTP client
        account_id: AWS account ID to scan

    Returns:
        Scan result data

    Raises:
        AssertionError: If scan fails
    """
    response = await api_client.post(
        f"/api/v1/security/scan/{account_id}",
        json={},
    )
    assert response.status_code in [200, 202], f"Scan failed: {response.text}"
    return response.json()


async def get_findings(
    api_client: httpx.AsyncClient,
    account_id: str | None = None,
    limit: int = 100,
) -> list[Dict[str, Any]]:
    """Get security findings via API.

    Args:
        api_client: HTTP client
        account_id: Optional AWS account ID filter
        limit: Maximum number of findings to return

    Returns:
        List of findings
    """
    params = {"limit": limit}
    if account_id:
        params["account_id"] = account_id

    response = await api_client.get("/api/v1/findings", params=params)
    assert response.status_code == 200, f"Failed to get findings: {response.text}"
    return response.json()
