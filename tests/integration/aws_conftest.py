"""
AWS Integration Test Fixtures using LocalStack.

These fixtures connect to REAL LocalStack services - NO MOCKS.
All tests run against actual AWS API-compatible infrastructure.

Requirements:
    docker-compose -f docker/docker-compose.test.yml up -d
"""

import os
from typing import Any, AsyncGenerator, Dict, Generator, List

import boto3
import pytest
import pytest_asyncio
from botocore.config import Config

# LocalStack configuration
LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Boto3 config for LocalStack
LOCALSTACK_CONFIG = Config(
    region_name=AWS_REGION,
    signature_version="v4",
    retries={"max_attempts": 3, "mode": "standard"},
)


def is_localstack_available() -> bool:
    """Check if LocalStack is available."""
    try:
        client = boto3.client(
            "sts",
            endpoint_url=LOCALSTACK_ENDPOINT,
            aws_access_key_id="test",
            aws_secret_access_key="test",
            config=LOCALSTACK_CONFIG,
        )
        client.get_caller_identity()
        return True
    except Exception:
        return False


# ============================================================================
# EC2 Fixtures (Security Groups)
# ============================================================================


@pytest.fixture(scope="function")
def ec2_client() -> Generator[Any, None, None]:
    """
    Create a REAL EC2 client connected to LocalStack.

    Cleans up all security groups after each test.
    """
    if not is_localstack_available():
        pytest.skip("LocalStack not available - run: docker-compose -f docker/docker-compose.test.yml up -d")

    client = boto3.client(
        "ec2",
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=LOCALSTACK_CONFIG,
    )

    yield client

    # Cleanup: Delete all non-default security groups
    try:
        response = client.describe_security_groups()
        for sg in response.get("SecurityGroups", []):
            if sg["GroupName"] != "default":
                try:
                    client.delete_security_group(GroupId=sg["GroupId"])
                except Exception:
                    pass  # Ignore cleanup errors
    except Exception:
        pass


@pytest.fixture(scope="function")
def vpc_id(ec2_client: Any) -> Generator[str, None, None]:
    """Create a VPC for testing and return its ID."""
    response = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = response["Vpc"]["VpcId"]

    yield vpc_id

    # Cleanup
    try:
        ec2_client.delete_vpc(VpcId=vpc_id)
    except Exception:
        pass


@pytest.fixture(scope="function")
def risky_security_group(ec2_client: Any, vpc_id: str) -> Generator[Dict[str, Any], None, None]:
    """
    Create a security group with risky rules (0.0.0.0/0 on SSH).

    This is REAL infrastructure for testing scanner detection.
    """
    # Create security group
    response = ec2_client.create_security_group(
        GroupName="risky-test-sg",
        Description="Test SG with risky rules",
        VpcId=vpc_id,
    )
    sg_id = response["GroupId"]

    # Add risky ingress rule - SSH open to world
    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "SSH from anywhere"}],
            }
        ],
    )

    # Add another risky rule - RDP open to world
    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 3389,
                "ToPort": 3389,
                "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "RDP from anywhere"}],
            }
        ],
    )

    yield {
        "GroupId": sg_id,
        "GroupName": "risky-test-sg",
        "VpcId": vpc_id,
    }


@pytest.fixture(scope="function")
def safe_security_group(ec2_client: Any, vpc_id: str) -> Generator[Dict[str, Any], None, None]:
    """
    Create a security group with safe rules (internal CIDR only).

    This is REAL infrastructure for testing scanner ignores safe rules.
    """
    response = ec2_client.create_security_group(
        GroupName="safe-test-sg",
        Description="Test SG with safe rules",
        VpcId=vpc_id,
    )
    sg_id = response["GroupId"]

    # Add safe ingress rule - internal network only
    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 443,
                "ToPort": 443,
                "IpRanges": [{"CidrIp": "10.0.0.0/8", "Description": "HTTPS from internal"}],
            }
        ],
    )

    yield {
        "GroupId": sg_id,
        "GroupName": "safe-test-sg",
        "VpcId": vpc_id,
    }


# ============================================================================
# IAM Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def iam_client() -> Generator[Any, None, None]:
    """
    Create a REAL IAM client connected to LocalStack.

    Cleans up all test users and policies after each test.
    """
    if not is_localstack_available():
        pytest.skip("LocalStack not available")

    client = boto3.client(
        "iam",
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=LOCALSTACK_CONFIG,
    )

    yield client

    # Cleanup: Delete test users and policies
    try:
        # Delete users
        for user in client.list_users().get("Users", []):
            if user["UserName"].startswith("test-"):
                # Delete MFA devices first
                for mfa in client.list_mfa_devices(UserName=user["UserName"]).get("MFADevices", []):
                    client.deactivate_mfa_device(
                        UserName=user["UserName"],
                        SerialNumber=mfa["SerialNumber"],
                    )
                    client.delete_virtual_mfa_device(SerialNumber=mfa["SerialNumber"])
                # Detach policies
                for policy in client.list_attached_user_policies(UserName=user["UserName"]).get("AttachedPolicies", []):
                    client.detach_user_policy(UserName=user["UserName"], PolicyArn=policy["PolicyArn"])
                client.delete_user(UserName=user["UserName"])

        # Delete policies
        for policy in client.list_policies(Scope="Local").get("Policies", []):
            if policy["PolicyName"].startswith("test-"):
                client.delete_policy(PolicyArn=policy["Arn"])
    except Exception:
        pass


@pytest.fixture(scope="function")
def user_without_mfa(iam_client: Any) -> Generator[Dict[str, Any], None, None]:
    """Create an IAM user without MFA enabled."""
    user_name = "test-user-no-mfa"

    iam_client.create_user(UserName=user_name)

    user = iam_client.get_user(UserName=user_name)["User"]

    yield {
        "UserName": user_name,
        "Arn": user["Arn"],
        "UserId": user["UserId"],
    }


@pytest.fixture(scope="function")
def user_with_mfa(iam_client: Any) -> Generator[Dict[str, Any], None, None]:
    """Create an IAM user with MFA enabled."""
    user_name = "test-user-with-mfa"

    iam_client.create_user(UserName=user_name)

    # Create virtual MFA device
    mfa_response = iam_client.create_virtual_mfa_device(
        VirtualMFADeviceName=f"{user_name}-mfa"
    )
    mfa_serial = mfa_response["VirtualMFADevice"]["SerialNumber"]

    # Enable MFA (LocalStack accepts any codes)
    iam_client.enable_mfa_device(
        UserName=user_name,
        SerialNumber=mfa_serial,
        AuthenticationCode1="123456",
        AuthenticationCode2="654321",
    )

    user = iam_client.get_user(UserName=user_name)["User"]

    yield {
        "UserName": user_name,
        "Arn": user["Arn"],
        "UserId": user["UserId"],
        "MFASerial": mfa_serial,
    }


@pytest.fixture(scope="function")
def wildcard_policy(iam_client: Any) -> Generator[Dict[str, Any], None, None]:
    """Create an IAM policy with wildcard permissions."""
    policy_name = "test-wildcard-policy"

    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "*",
                "Resource": "*",
            }
        ],
    }

    import json
    response = iam_client.create_policy(
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document),
        Description="Test policy with wildcard permissions",
    )

    yield {
        "PolicyName": policy_name,
        "PolicyArn": response["Policy"]["Arn"],
        "PolicyId": response["Policy"]["PolicyId"],
    }


@pytest.fixture(scope="function")
def least_privilege_policy(iam_client: Any) -> Generator[Dict[str, Any], None, None]:
    """Create an IAM policy following least privilege."""
    policy_name = "test-least-privilege-policy"

    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": [
                    "arn:aws:s3:::specific-bucket",
                    "arn:aws:s3:::specific-bucket/*",
                ],
            }
        ],
    }

    import json
    response = iam_client.create_policy(
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document),
        Description="Test policy following least privilege",
    )

    yield {
        "PolicyName": policy_name,
        "PolicyArn": response["Policy"]["Arn"],
        "PolicyId": response["Policy"]["PolicyId"],
    }


# ============================================================================
# S3 Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def s3_client() -> Generator[Any, None, None]:
    """Create a REAL S3 client connected to LocalStack."""
    if not is_localstack_available():
        pytest.skip("LocalStack not available")

    client = boto3.client(
        "s3",
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=LOCALSTACK_CONFIG,
    )

    yield client

    # Cleanup: Delete all test buckets
    try:
        for bucket in client.list_buckets().get("Buckets", []):
            if bucket["Name"].startswith("test-"):
                # Delete all objects first
                try:
                    objects = client.list_objects_v2(Bucket=bucket["Name"])
                    for obj in objects.get("Contents", []):
                        client.delete_object(Bucket=bucket["Name"], Key=obj["Key"])
                except Exception:
                    pass
                client.delete_bucket(Bucket=bucket["Name"])
    except Exception:
        pass


@pytest.fixture(scope="function")
def unencrypted_bucket(s3_client: Any) -> Generator[str, None, None]:
    """Create an S3 bucket without encryption."""
    bucket_name = "test-unencrypted-bucket"

    s3_client.create_bucket(Bucket=bucket_name)

    yield bucket_name


@pytest.fixture(scope="function")
def encrypted_bucket(s3_client: Any) -> Generator[str, None, None]:
    """Create an S3 bucket with SSE-S3 encryption."""
    bucket_name = "test-encrypted-bucket"

    s3_client.create_bucket(Bucket=bucket_name)

    # Enable encryption
    s3_client.put_bucket_encryption(
        Bucket=bucket_name,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }
            ]
        },
    )

    yield bucket_name


# ============================================================================
# Test Account Fixture
# ============================================================================


@pytest.fixture(scope="function")
def aws_account_id() -> str:
    """Return test AWS account ID."""
    return "000000000000"  # LocalStack default account ID
