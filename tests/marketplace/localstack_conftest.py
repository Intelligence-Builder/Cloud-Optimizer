"""
LocalStack configuration and fixtures for marketplace tests.

IMPORTANT: AWS Marketplace Metering API is NOT supported by LocalStack Community or Pro.
These fixtures provide the infrastructure for integration testing, but marketplace-specific
tests must use alternative approaches (mock servers, real AWS with IAM policies, etc.).

LocalStack Limitations:
- meteringmarketplace service: NOT SUPPORTED
- marketplace-entitlement service: NOT SUPPORTED

For true integration testing of marketplace features, consider:
1. Use AWS IAM policies with minimal permissions for safe testing
2. Create a test product in AWS Marketplace (Seller account)
3. Use test customer accounts with controlled subscriptions
"""

import time
from typing import AsyncGenerator, Generator

import boto3
import pytest
import requests
from botocore.config import Config


@pytest.fixture(scope="session")
def localstack_endpoint() -> str:
    """Get LocalStack endpoint URL."""
    return "http://localhost:4566"


@pytest.fixture(scope="session")
def wait_for_localstack(localstack_endpoint: str) -> None:
    """Wait for LocalStack to be ready."""
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{localstack_endpoint}/_localstack/health")
            if response.status_code == 200:
                health = response.json()
                # Check if required services are running
                services = health.get("services", {})
                if all(
                    services.get(svc) in ["available", "running"]
                    for svc in ["s3", "iam"]
                ):
                    return
        except requests.exceptions.RequestException:
            pass

        if attempt < max_attempts - 1:
            time.sleep(1)

    raise RuntimeError(
        "LocalStack not ready after 30 seconds. "
        "Start with: docker-compose -f docker/docker-compose.test.yml up -d localstack"
    )


@pytest.fixture
def aws_credentials() -> None:
    """Set dummy AWS credentials for LocalStack."""
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = "test"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def localstack_boto3_config(localstack_endpoint: str) -> Config:
    """Create boto3 config for LocalStack."""
    return Config(
        region_name="us-east-1",
        signature_version="s3v4",
        retries={"max_attempts": 3, "mode": "standard"},
    )


@pytest.fixture
def s3_client(
    wait_for_localstack: None,
    aws_credentials: None,
    localstack_endpoint: str,
    localstack_boto3_config: Config,
) -> Generator[boto3.client, None, None]:
    """Create S3 client connected to LocalStack."""
    client = boto3.client(
        "s3",
        endpoint_url=localstack_endpoint,
        config=localstack_boto3_config,
    )
    yield client
    # Cleanup: delete all buckets created during test
    try:
        buckets = client.list_buckets()
        for bucket in buckets.get("Buckets", []):
            bucket_name = bucket["Name"]
            # Delete all objects first
            try:
                objects = client.list_objects_v2(Bucket=bucket_name)
                if "Contents" in objects:
                    for obj in objects["Contents"]:
                        client.delete_object(Bucket=bucket_name, Key=obj["Key"])
                client.delete_bucket(Bucket=bucket_name)
            except Exception:
                pass  # Best effort cleanup
    except Exception:
        pass


@pytest.fixture
def iam_client(
    wait_for_localstack: None,
    aws_credentials: None,
    localstack_endpoint: str,
    localstack_boto3_config: Config,
) -> Generator[boto3.client, None, None]:
    """Create IAM client connected to LocalStack."""
    client = boto3.client(
        "iam",
        endpoint_url=localstack_endpoint,
        config=localstack_boto3_config,
    )
    yield client
    # Cleanup: best effort to remove created resources
    # Note: IAM cleanup can be complex, doing basic cleanup only


@pytest.fixture
def cloudwatch_client(
    wait_for_localstack: None,
    aws_credentials: None,
    localstack_endpoint: str,
    localstack_boto3_config: Config,
) -> Generator[boto3.client, None, None]:
    """Create CloudWatch client connected to LocalStack."""
    client = boto3.client(
        "cloudwatch",
        endpoint_url=localstack_endpoint,
        config=localstack_boto3_config,
    )
    yield client


def create_mock_marketplace_server() -> str:
    """
    Create a mock HTTP server that simulates AWS Marketplace Metering API.

    This is a placeholder for a more comprehensive mock server implementation.
    Consider using moto, localstack extensions, or a custom Flask/FastAPI server.

    Returns:
        str: URL of the mock server
    """
    # TODO: Implement actual mock server
    # Options:
    # 1. Use moto with custom responses
    # 2. Create a FastAPI app that mimics marketplace API
    # 3. Use responses library for HTTP mocking
    raise NotImplementedError(
        "Mock Marketplace server not implemented. "
        "See tests/marketplace/README.md for alternative testing approaches."
    )


@pytest.fixture
async def mock_marketplace_client(
    localstack_endpoint: str,
) -> AsyncGenerator[boto3.client, None]:
    """
    Create a mock marketplace metering client.

    NOTE: This fixture demonstrates the pattern but marketplace API is not
    supported by LocalStack. Use this as a template for implementing a custom
    mock server or use real AWS for integration testing.
    """
    # This would need a custom mock server implementation
    # For now, we'll create a regular boto3 client that will fail
    # when trying to use marketplace features
    pytest.skip(
        "AWS Marketplace Metering API not supported by LocalStack. "
        "Use real AWS with test IAM policies or implement custom mock server."
    )
    yield  # type: ignore
