"""Pytest fixtures for AWS scanner tests.

Supports both LocalStack (default) and real AWS (USE_REAL_AWS=true).
"""

import os
import subprocess
import time
from typing import Any, Generator

import boto3
import pytest
from botocore.config import Config

# Test configuration
USE_REAL_AWS = os.getenv("USE_REAL_AWS", "false").lower() == "true"
LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


def is_localstack_running() -> bool:
    """Check if LocalStack is running."""
    try:
        result = subprocess.run(
            ["curl", "-s", f"{LOCALSTACK_ENDPOINT}/_localstack/health"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def aws_credentials() -> dict[str, str]:
    """Get AWS credentials for testing.

    Returns LocalStack dummy credentials or real credentials.
    """
    if USE_REAL_AWS:
        # Use real credentials from environment or AWS config
        return {}  # boto3 will use default credential chain
    else:
        return {
            "aws_access_key_id": "test",
            "aws_secret_access_key": "test",
            "region_name": AWS_REGION,
        }


@pytest.fixture(scope="session")
def boto_session(aws_credentials: dict[str, str]) -> boto3.Session:
    """Create boto3 session for testing."""
    if USE_REAL_AWS:
        return boto3.Session(region_name=AWS_REGION)
    else:
        return boto3.Session(**aws_credentials)


@pytest.fixture(scope="session")
def aws_config() -> Config:
    """Get boto3 config for testing."""
    if USE_REAL_AWS:
        return Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            region_name=AWS_REGION,
        )
    else:
        return Config(
            retries={"max_attempts": 1, "mode": "standard"},
            region_name=AWS_REGION,
        )


def get_client(
    session: boto3.Session,
    service: str,
    config: Config,
    region: str | None = None,
) -> Any:
    """Get boto3 client for service.

    Args:
        session: Boto3 session
        service: AWS service name
        config: Boto3 config
        region: Optional region override

    Returns:
        Configured boto3 client
    """
    kwargs: dict[str, Any] = {"config": config}
    if region:
        kwargs["region_name"] = region

    if not USE_REAL_AWS:
        kwargs["endpoint_url"] = LOCALSTACK_ENDPOINT

    return session.client(service, **kwargs)


@pytest.fixture(scope="session")
def s3_client(
    boto_session: boto3.Session,
    aws_config: Config,
) -> Generator[Any, None, None]:
    """Create S3 client for testing."""
    client = get_client(boto_session, "s3", aws_config)
    yield client


@pytest.fixture(scope="session")
def ec2_client(
    boto_session: boto3.Session,
    aws_config: Config,
) -> Generator[Any, None, None]:
    """Create EC2 client for testing."""
    client = get_client(boto_session, "ec2", aws_config)
    yield client


@pytest.fixture(scope="session")
def iam_client(
    boto_session: boto3.Session,
    aws_config: Config,
) -> Generator[Any, None, None]:
    """Create IAM client for testing."""
    client = get_client(boto_session, "iam", aws_config)
    yield client


@pytest.fixture(scope="session")
def rds_client(
    boto_session: boto3.Session,
    aws_config: Config,
) -> Generator[Any, None, None]:
    """Create RDS client for testing."""
    client = get_client(boto_session, "rds", aws_config)
    yield client


@pytest.fixture(scope="session")
def ce_client(
    boto_session: boto3.Session,
    aws_config: Config,
) -> Generator[Any, None, None]:
    """Create Cost Explorer client for testing.

    Note: Cost Explorer is not available in LocalStack Community.
    """
    if not USE_REAL_AWS:
        pytest.skip("Cost Explorer requires real AWS or LocalStack Pro")
    client = get_client(boto_session, "ce", aws_config)
    yield client


@pytest.fixture(scope="session")
def cloudwatch_client(
    boto_session: boto3.Session,
    aws_config: Config,
) -> Generator[Any, None, None]:
    """Create CloudWatch client for testing."""
    client = get_client(boto_session, "cloudwatch", aws_config)
    yield client


@pytest.fixture(scope="session")
def sts_client(
    boto_session: boto3.Session,
    aws_config: Config,
) -> Generator[Any, None, None]:
    """Create STS client for testing."""
    client = get_client(boto_session, "sts", aws_config)
    yield client


@pytest.fixture
def test_bucket_name() -> str:
    """Generate unique test bucket name."""
    import uuid

    return f"cloud-optimizer-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_s3_bucket(
    s3_client: Any,
    test_bucket_name: str,
) -> Generator[str, None, None]:
    """Create test S3 bucket and cleanup after test.

    Yields:
        Bucket name
    """
    # Create bucket
    if AWS_REGION == "us-east-1":
        s3_client.create_bucket(Bucket=test_bucket_name)
    else:
        s3_client.create_bucket(
            Bucket=test_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
        )

    yield test_bucket_name

    # Cleanup
    try:
        # Delete all objects
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=test_bucket_name):
            objects = page.get("Contents", [])
            if objects:
                delete_keys = [{"Key": obj["Key"]} for obj in objects]
                s3_client.delete_objects(
                    Bucket=test_bucket_name,
                    Delete={"Objects": delete_keys},
                )
        # Delete bucket
        s3_client.delete_bucket(Bucket=test_bucket_name)
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
def insecure_s3_bucket(
    s3_client: Any,
    test_bucket_name: str,
) -> Generator[str, None, None]:
    """Create insecure S3 bucket for security testing.

    Creates bucket with:
    - No encryption
    - No versioning
    - Public access block disabled (LocalStack only)

    Yields:
        Bucket name
    """
    # Create bucket
    if AWS_REGION == "us-east-1":
        s3_client.create_bucket(Bucket=test_bucket_name)
    else:
        s3_client.create_bucket(
            Bucket=test_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
        )

    # Disable public access block (LocalStack only - don't do this in real AWS)
    if not USE_REAL_AWS:
        try:
            s3_client.delete_public_access_block(Bucket=test_bucket_name)
        except Exception:
            pass

    yield test_bucket_name

    # Cleanup
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=test_bucket_name):
            objects = page.get("Contents", [])
            if objects:
                delete_keys = [{"Key": obj["Key"]} for obj in objects]
                s3_client.delete_objects(
                    Bucket=test_bucket_name,
                    Delete={"Objects": delete_keys},
                )
        s3_client.delete_bucket(Bucket=test_bucket_name)
    except Exception:
        pass


@pytest.fixture
def secure_s3_bucket(
    s3_client: Any,
    test_bucket_name: str,
) -> Generator[str, None, None]:
    """Create secure S3 bucket for security testing.

    Creates bucket with:
    - Default encryption enabled
    - Versioning enabled
    - Public access block enabled

    Yields:
        Bucket name
    """
    # Create bucket
    if AWS_REGION == "us-east-1":
        s3_client.create_bucket(Bucket=test_bucket_name)
    else:
        s3_client.create_bucket(
            Bucket=test_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
        )

    # Enable encryption
    s3_client.put_bucket_encryption(
        Bucket=test_bucket_name,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256",
                    },
                    "BucketKeyEnabled": True,
                }
            ]
        },
    )

    # Enable versioning
    s3_client.put_bucket_versioning(
        Bucket=test_bucket_name,
        VersioningConfiguration={"Status": "Enabled"},
    )

    # Enable public access block
    s3_client.put_public_access_block(
        Bucket=test_bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )

    yield test_bucket_name

    # Cleanup
    try:
        # Delete all object versions
        paginator = s3_client.get_paginator("list_object_versions")
        for page in paginator.paginate(Bucket=test_bucket_name):
            versions = page.get("Versions", [])
            delete_markers = page.get("DeleteMarkers", [])

            objects = [
                {"Key": v["Key"], "VersionId": v["VersionId"]} for v in versions
            ]
            objects.extend(
                {"Key": d["Key"], "VersionId": d["VersionId"]} for d in delete_markers
            )

            if objects:
                s3_client.delete_objects(
                    Bucket=test_bucket_name,
                    Delete={"Objects": objects},
                )

        s3_client.delete_bucket(Bucket=test_bucket_name)
    except Exception:
        pass


@pytest.fixture
def require_localstack() -> None:
    """Skip test if LocalStack is not available."""
    if USE_REAL_AWS:
        pytest.skip("Test requires LocalStack, but USE_REAL_AWS is true")
    if not is_localstack_running():
        pytest.skip("LocalStack is not running")


@pytest.fixture
def require_real_aws() -> None:
    """Skip test if not using real AWS."""
    if not USE_REAL_AWS:
        pytest.skip("Test requires real AWS (set USE_REAL_AWS=true)")


@pytest.fixture
def localstack_or_real_aws() -> str:
    """Get the AWS backend being used.

    Returns:
        'localstack' or 'real_aws'
    """
    if USE_REAL_AWS:
        return "real_aws"
    if not is_localstack_running():
        pytest.skip("Neither LocalStack nor real AWS is available")
    return "localstack"
