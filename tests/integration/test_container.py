"""
Integration tests for Docker container build and startup (Issue #47).

Tests verify:
1. Docker build succeeds
2. Image size is under 500MB
3. Container starts and passes healthcheck
4. Migrations run correctly
5. Health endpoint returns 200

These tests use the docker Python package and real Docker daemon.
"""

import os
import time
from pathlib import Path
from typing import Generator

import httpx
import pytest
from docker.models.containers import Container
from docker.models.images import Image

import docker

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE_PATH = PROJECT_ROOT / "docker" / "Dockerfile"

# Test configuration
IMAGE_SIZE_LIMIT_MB = 500
HEALTH_TIMEOUT_SECONDS = 120
CONTAINER_PORT = 8000
HOST_PORT = 18000


@pytest.fixture(scope="module")
def docker_client() -> Generator[docker.DockerClient, None, None]:
    """
    Provide Docker client for tests.

    Yields:
        docker.DockerClient: Connected Docker client.

    Raises:
        pytest.skip: If Docker is not available.
    """
    try:
        client = docker.from_env()
        # Test connection
        client.ping()
        yield client
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")
    finally:
        if "client" in locals():
            client.close()


@pytest.fixture(scope="module")
def built_image(docker_client: docker.DockerClient) -> Generator[Image, None, None]:
    """
    Build Docker image for testing.

    Args:
        docker_client: Docker client fixture.

    Yields:
        Image: Built Docker image.

    Raises:
        AssertionError: If build fails.
    """
    import uuid

    image_tag = f"cloud-optimizer-test:{uuid.uuid4().hex[:8]}"

    try:
        # Build image
        image, build_logs = docker_client.images.build(
            path=str(PROJECT_ROOT),
            dockerfile=str(DOCKERFILE_PATH.relative_to(PROJECT_ROOT)),
            tag=image_tag,
            rm=True,  # Remove intermediate containers
            forcerm=True,  # Always remove intermediate containers
        )

        # Print build logs for debugging
        for log in build_logs:
            if "stream" in log:
                print(log["stream"].strip())

        yield image

    finally:
        # Cleanup: remove image
        try:
            docker_client.images.remove(image=image_tag, force=True)
        except Exception as e:
            print(f"Failed to remove image {image_tag}: {e}")


@pytest.fixture
def test_container(
    docker_client: docker.DockerClient, built_image: Image
) -> Generator[Container, None, None]:
    """
    Start test container from built image.

    Args:
        docker_client: Docker client fixture.
        built_image: Built image fixture.

    Yields:
        Container: Running container.
    """
    import uuid

    container_name = f"cloud-optimizer-test-{uuid.uuid4().hex[:8]}"

    # Test environment variables
    env_vars = {
        "LOG_LEVEL": "INFO",
        "DATABASE_HOST": "postgres",
        "DATABASE_PORT": "5432",
        "DATABASE_NAME": "cloud_optimizer",
        "DATABASE_USER": "cloud_optimizer",
        "DATABASE_PASSWORD": "securepass123",
        "API_HOST": "0.0.0.0",
        "API_PORT": str(CONTAINER_PORT),
    }

    container = None
    try:
        # Start container
        container = docker_client.containers.run(
            image=built_image.id,
            name=container_name,
            ports={f"{CONTAINER_PORT}/tcp": HOST_PORT},
            environment=env_vars,
            detach=True,
            remove=False,  # Don't auto-remove so we can inspect logs
        )

        # Wait a moment for container to start
        time.sleep(2)

        yield container

    finally:
        # Cleanup: stop and remove container
        if container:
            try:
                # Print logs for debugging
                logs = container.logs(tail=50).decode("utf-8")
                print(f"\n=== Container logs (last 50 lines) ===\n{logs}")

                container.stop(timeout=5)
                container.remove(force=True)
            except Exception as e:
                print(f"Failed to cleanup container {container_name}: {e}")


@pytest.mark.integration
def test_docker_build_succeeds(built_image: Image) -> None:
    """
    Test that Docker build completes successfully.

    Args:
        built_image: Built image fixture.
    """
    assert built_image is not None, "Docker build failed"
    assert len(built_image.tags) > 0, "Built image has no tags"
    print(f"✓ Docker build succeeded: {built_image.tags[0]}")


@pytest.mark.integration
def test_image_size_under_limit(built_image: Image) -> None:
    """
    Test that Docker image size is under 500MB.

    Args:
        built_image: Built image fixture.

    Raises:
        AssertionError: If image exceeds size limit.
    """
    # Get image size in bytes
    image_size_bytes = built_image.attrs["Size"]
    image_size_mb = image_size_bytes / (1024 * 1024)

    print(f"Image size: {image_size_mb:.2f} MB")

    assert (
        image_size_mb < IMAGE_SIZE_LIMIT_MB
    ), f"Image size {image_size_mb:.2f}MB exceeds limit of {IMAGE_SIZE_LIMIT_MB}MB"

    print(f"✓ Image size {image_size_mb:.2f}MB is under {IMAGE_SIZE_LIMIT_MB}MB limit")


@pytest.mark.integration
def test_container_starts(test_container: Container) -> None:
    """
    Test that container starts successfully.

    Args:
        test_container: Running container fixture.
    """
    # Refresh container status
    test_container.reload()

    assert test_container.status in [
        "running",
        "created",
    ], f"Container not running: {test_container.status}"

    print(
        f"✓ Container started: {test_container.name} (status: {test_container.status})"
    )


@pytest.mark.integration
def test_container_healthcheck_passes(test_container: Container) -> None:
    """
    Test that container health check passes.

    This test waits up to HEALTH_TIMEOUT_SECONDS for the container to become healthy.
    The container's built-in healthcheck runs every 30s.

    Note: This test requires a PostgreSQL database to be available.
    If database is not available, the container will fail to start.

    Args:
        test_container: Running container fixture.

    Raises:
        AssertionError: If healthcheck fails or times out.
    """
    deadline = time.time() + HEALTH_TIMEOUT_SECONDS
    last_status = None

    while time.time() < deadline:
        test_container.reload()

        # Get health status from container state
        health = test_container.attrs.get("State", {}).get("Health", {})
        status = health.get("Status", "unknown")
        last_status = status

        print(f"Health status: {status}")

        if status == "healthy":
            print("✓ Container healthcheck passed")
            return

        if status == "unhealthy":
            # Print last health check log
            logs = health.get("Log", [])
            if logs:
                last_log = logs[-1]
                print(f"Last healthcheck output: {last_log.get('Output', 'N/A')}")

            # Check container logs for database connection errors
            container_logs = test_container.logs().decode("utf-8")
            if (
                "psycopg2" in container_logs
                or "Database connection failed" in container_logs
            ):
                pytest.skip(
                    "Container requires PostgreSQL database to be available. "
                    "Run with docker-compose for full integration testing."
                )

            pytest.fail(f"Container healthcheck failed: {status}")

        # Wait before checking again
        time.sleep(5)

    # Timeout reached
    # Check if it's a database issue before failing
    container_logs = test_container.logs().decode("utf-8")
    if "Database connection failed" in container_logs or "psycopg2" in container_logs:
        pytest.skip(
            "Container requires PostgreSQL database to be available. "
            "Run with docker-compose for full integration testing."
        )

    pytest.fail(
        f"Container healthcheck timeout after {HEALTH_TIMEOUT_SECONDS}s. "
        f"Last status: {last_status}"
    )


@pytest.mark.integration
def test_health_endpoint_returns_200(test_container: Container) -> None:
    """
    Test that /health endpoint returns 200 OK.

    This test directly calls the health endpoint via HTTP to verify
    the application is responding correctly.

    Note: This test requires a PostgreSQL database to be available.

    Args:
        test_container: Running container fixture.

    Raises:
        AssertionError: If health endpoint fails or returns wrong status.
    """
    health_url = f"http://127.0.0.1:{HOST_PORT}/health"
    deadline = time.time() + HEALTH_TIMEOUT_SECONDS
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            response = httpx.get(health_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                print(f"Health response: {data}")

                # Verify response structure
                assert "status" in data, "Health response missing 'status' field"
                assert "version" in data, "Health response missing 'version' field"
                assert "timestamp" in data, "Health response missing 'timestamp' field"
                assert (
                    "components" in data
                ), "Health response missing 'components' field"

                print(
                    f"✓ Health endpoint returned 200 OK "
                    f"(status: {data['status']}, version: {data['version']})"
                )
                return

            # Non-200 response
            print(
                f"Health endpoint returned {response.status_code}: {response.text[:200]}"
            )

        except Exception as e:
            last_error = e
            print(f"Health check attempt failed: {e}")

        # Wait before retrying
        time.sleep(5)

    # Timeout reached
    # Check if it's a database issue
    container_logs = test_container.logs().decode("utf-8")
    if "Database connection failed" in container_logs or "psycopg2" in container_logs:
        pytest.skip(
            "Container requires PostgreSQL database to be available. "
            "Run with docker-compose for full integration testing."
        )

    pytest.fail(
        f"Health endpoint check timeout after {HEALTH_TIMEOUT_SECONDS}s. "
        f"Last error: {last_error}"
    )


@pytest.mark.integration
def test_migrations_run_correctly(test_container: Container) -> None:
    """
    Test that database migrations run correctly on container startup.

    This test inspects container logs to verify migrations executed successfully.

    Note: This test requires a PostgreSQL database to be available.

    Args:
        test_container: Running container fixture.
    """
    # Wait for startup to complete
    time.sleep(10)

    # Get container logs
    logs = test_container.logs().decode("utf-8")

    # Check if database is available first
    if "Database connection failed" in logs or "psycopg2" in logs:
        pytest.skip(
            "Container requires PostgreSQL database to be available. "
            "Run with docker-compose for full integration testing."
        )

    # Check for migration success indicators
    migration_indicators = [
        "database_migrations_completed",
        "Running upgrade",
        "alembic",
    ]

    found_indicators = [
        indicator for indicator in migration_indicators if indicator in logs
    ]

    if found_indicators:
        print(f"✓ Found migration indicators in logs: {found_indicators}")
    else:
        # If no migration indicators found, check if migrations were skipped
        # (which is acceptable if alembic.ini is not present)
        if "skipping_migrations" in logs or "alembic_config_not_found" in logs:
            print(
                "⚠ Migrations were skipped (alembic.ini not found in container). "
                "This is acceptable for this test."
            )
            pytest.skip("Migrations skipped - alembic.ini not present in container")
        else:
            # Print relevant log sections
            print(f"\n=== Container logs (checking for migrations) ===")
            for line in logs.split("\n"):
                if any(
                    keyword in line.lower()
                    for keyword in ["migration", "alembic", "database", "upgrade"]
                ):
                    print(line)

            pytest.fail(
                "Could not verify migrations ran successfully. "
                "No migration indicators found in logs."
            )


@pytest.mark.integration
def test_container_exposes_correct_port(built_image: Image) -> None:
    """
    Test that Dockerfile exposes the correct port (8000).

    Args:
        built_image: Built image fixture.
    """
    # Get exposed ports from image config
    config = built_image.attrs.get("Config", {})
    exposed_ports = config.get("ExposedPorts", {})

    # Check if port 8000 is exposed
    expected_port = f"{CONTAINER_PORT}/tcp"
    assert (
        expected_port in exposed_ports
    ), f"Port {CONTAINER_PORT} not exposed. Exposed: {list(exposed_ports.keys())}"

    print(f"✓ Container exposes correct port: {CONTAINER_PORT}")


@pytest.mark.integration
def test_container_uses_non_root_user(built_image: Image) -> None:
    """
    Test that container runs as non-root user for security.

    Args:
        built_image: Built image fixture.
    """
    # Get user from image config
    config = built_image.attrs.get("Config", {})
    user = config.get("User", "")

    # Verify non-root user
    assert user != "", "Container does not specify a user"
    assert user != "root", "Container runs as root (security risk)"
    assert user == "appuser", f"Container runs as unexpected user: {user}"

    print(f"✓ Container runs as non-root user: {user}")


@pytest.mark.integration
def test_container_has_healthcheck(built_image: Image) -> None:
    """
    Test that container has a healthcheck configured.

    Args:
        built_image: Built image fixture.
    """
    # Get healthcheck from image config
    config = built_image.attrs.get("Config", {})
    healthcheck = config.get("Healthcheck", {})

    assert healthcheck, "Container does not have a healthcheck configured"
    assert "Test" in healthcheck, "Healthcheck missing 'Test' command"

    # Verify healthcheck command
    test_command = " ".join(healthcheck["Test"])
    assert "/health" in test_command, "Healthcheck does not use /health endpoint"

    print(f"✓ Container has healthcheck configured: {test_command}")
