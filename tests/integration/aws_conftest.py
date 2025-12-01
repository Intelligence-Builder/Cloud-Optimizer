"""
AWS Integration Test Fixtures - LocalStack or Real AWS.

Supports two modes:
1. LocalStack (default) - Free, local, safe for development
2. Real AWS - Set USE_REAL_AWS=true to test against actual AWS

Usage:
    # LocalStack (default)
    pytest tests/integration/

    # Real AWS
    USE_REAL_AWS=true pytest tests/integration/

    # Or use pytest marker
    pytest tests/integration/ -m real_aws

Requirements:
    LocalStack: docker-compose -f docker/docker-compose.test.yml up -d
    Real AWS: AWS credentials configured (AWS_PROFILE or env vars)
"""

import json
import os
import uuid
from typing import Any, Dict, Generator

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

# ============================================================================
# Configuration
# ============================================================================

# Check if we should use real AWS
USE_REAL_AWS = os.getenv("USE_REAL_AWS", "false").lower() in ("true", "1", "yes")

# LocalStack configuration
LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Test resource prefix - helps identify and cleanup test resources
TEST_PREFIX = f"cloud-opt-test-{uuid.uuid4().hex[:8]}"

# Boto3 config
AWS_CONFIG = Config(
    region_name=AWS_REGION,
    signature_version="v4",
    retries={"max_attempts": 3, "mode": "standard"},
)


# ============================================================================
# Helper Functions
# ============================================================================


def is_localstack_available() -> bool:
    """Check if LocalStack is available."""
    if USE_REAL_AWS:
        return False
    try:
        client = boto3.client(
            "ec2",
            endpoint_url=LOCALSTACK_ENDPOINT,
            aws_access_key_id="test",
            aws_secret_access_key="test",
            config=AWS_CONFIG,
        )
        client.describe_regions()
        return True
    except Exception:
        return False


def is_real_aws_available() -> bool:
    """Check if real AWS credentials are available."""
    try:
        sts = boto3.client("sts", config=AWS_CONFIG)
        sts.get_caller_identity()
        return True
    except (NoCredentialsError, ClientError):
        return False


def get_aws_mode() -> str:
    """Get current AWS mode."""
    if USE_REAL_AWS:
        return "real_aws"
    return "localstack"


def create_client(service_name: str) -> Any:
    """Create a boto3 client for the appropriate environment."""
    if USE_REAL_AWS:
        if not is_real_aws_available():
            pytest.skip("Real AWS credentials not available")
        return boto3.client(service_name, config=AWS_CONFIG)
    else:
        if not is_localstack_available():
            pytest.skip(
                "LocalStack not available - run: "
                "docker-compose -f docker/docker-compose.test.yml up -d"
            )
        return boto3.client(
            service_name,
            endpoint_url=LOCALSTACK_ENDPOINT,
            aws_access_key_id="test",
            aws_secret_access_key="test",
            config=AWS_CONFIG,
        )


def create_resource(service_name: str) -> Any:
    """Create a boto3 resource for the appropriate environment."""
    if USE_REAL_AWS:
        if not is_real_aws_available():
            pytest.skip("Real AWS credentials not available")
        return boto3.resource(service_name, config=AWS_CONFIG)
    else:
        if not is_localstack_available():
            pytest.skip("LocalStack not available")
        return boto3.resource(
            service_name,
            endpoint_url=LOCALSTACK_ENDPOINT,
            aws_access_key_id="test",
            aws_secret_access_key="test",
            config=AWS_CONFIG,
        )


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "real_aws: mark test to run only with real AWS")
    config.addinivalue_line(
        "markers", "localstack_only: mark test to run only with LocalStack"
    )


@pytest.fixture(scope="session")
def aws_mode() -> str:
    """Return current AWS testing mode."""
    mode = get_aws_mode()
    print(f"\n{'='*60}")
    print(f"AWS Testing Mode: {mode.upper()}")
    if mode == "real_aws":
        print("WARNING: Tests will create REAL AWS resources!")
        print(f"Resource prefix: {TEST_PREFIX}")
    print(f"{'='*60}\n")
    return mode


@pytest.fixture(scope="session")
def test_prefix() -> str:
    """Return unique test prefix for resource naming."""
    return TEST_PREFIX


# ============================================================================
# EC2 Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def ec2_client(aws_mode: str) -> Generator[Any, None, None]:
    """Create EC2 client for current environment."""
    client = create_client("ec2")
    yield client

    # Cleanup: Delete test security groups
    try:
        response = client.describe_security_groups(
            Filters=[{"Name": "group-name", "Values": [f"{TEST_PREFIX}-*"]}]
        )
        for sg in response.get("SecurityGroups", []):
            if sg["GroupName"] != "default":
                try:
                    client.delete_security_group(GroupId=sg["GroupId"])
                except Exception:
                    pass
    except Exception:
        pass


@pytest.fixture(scope="function")
def vpc_id(ec2_client: Any) -> Generator[str, None, None]:
    """Create a VPC for testing."""
    response = ec2_client.create_vpc(
        CidrBlock="10.0.0.0/16",
        TagSpecifications=[
            {
                "ResourceType": "vpc",
                "Tags": [{"Key": "Name", "Value": f"{TEST_PREFIX}-vpc"}],
            }
        ],
    )
    vpc_id = response["Vpc"]["VpcId"]

    # Wait for VPC to be available
    waiter = ec2_client.get_waiter("vpc_available")
    waiter.wait(VpcIds=[vpc_id])

    yield vpc_id

    # Cleanup
    try:
        # Delete subnets first
        subnets = ec2_client.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )
        for subnet in subnets.get("Subnets", []):
            try:
                ec2_client.delete_subnet(SubnetId=subnet["SubnetId"])
            except Exception:
                pass

        # Delete internet gateways
        igws = ec2_client.describe_internet_gateways(
            Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
        )
        for igw in igws.get("InternetGateways", []):
            try:
                ec2_client.detach_internet_gateway(
                    InternetGatewayId=igw["InternetGatewayId"], VpcId=vpc_id
                )
                ec2_client.delete_internet_gateway(
                    InternetGatewayId=igw["InternetGatewayId"]
                )
            except Exception:
                pass

        # Delete security groups (non-default)
        sgs = ec2_client.describe_security_groups(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )
        for sg in sgs.get("SecurityGroups", []):
            if sg["GroupName"] != "default":
                try:
                    ec2_client.delete_security_group(GroupId=sg["GroupId"])
                except Exception:
                    pass

        ec2_client.delete_vpc(VpcId=vpc_id)
    except Exception:
        pass


@pytest.fixture(scope="function")
def risky_security_group(
    ec2_client: Any, vpc_id: str, test_prefix: str
) -> Generator[Dict[str, Any], None, None]:
    """Create a security group with risky rules (0.0.0.0/0 on SSH)."""
    sg_name = f"{test_prefix}-risky-sg"

    response = ec2_client.create_security_group(
        GroupName=sg_name,
        Description="Test SG with risky rules",
        VpcId=vpc_id,
        TagSpecifications=[
            {
                "ResourceType": "security-group",
                "Tags": [{"Key": "Name", "Value": sg_name}],
            }
        ],
    )
    sg_id = response["GroupId"]

    # Add risky ingress rules
    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [
                    {"CidrIp": "0.0.0.0/0", "Description": "SSH from anywhere"}
                ],
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 3389,
                "ToPort": 3389,
                "IpRanges": [
                    {"CidrIp": "0.0.0.0/0", "Description": "RDP from anywhere"}
                ],
            },
        ],
    )

    yield {"GroupId": sg_id, "GroupName": sg_name, "VpcId": vpc_id}


@pytest.fixture(scope="function")
def safe_security_group(
    ec2_client: Any, vpc_id: str, test_prefix: str
) -> Generator[Dict[str, Any], None, None]:
    """Create a security group with safe rules (internal CIDR only)."""
    sg_name = f"{test_prefix}-safe-sg"

    response = ec2_client.create_security_group(
        GroupName=sg_name,
        Description="Test SG with safe rules",
        VpcId=vpc_id,
        TagSpecifications=[
            {
                "ResourceType": "security-group",
                "Tags": [{"Key": "Name", "Value": sg_name}],
            }
        ],
    )
    sg_id = response["GroupId"]

    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 443,
                "ToPort": 443,
                "IpRanges": [
                    {"CidrIp": "10.0.0.0/8", "Description": "HTTPS from internal"}
                ],
            }
        ],
    )

    yield {"GroupId": sg_id, "GroupName": sg_name, "VpcId": vpc_id}


# ============================================================================
# IAM Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def iam_client(aws_mode: str) -> Generator[Any, None, None]:
    """Create IAM client for current environment."""
    client = create_client("iam")
    yield client

    # Cleanup: Delete test users and policies
    try:
        for user in client.list_users().get("Users", []):
            if user["UserName"].startswith(TEST_PREFIX):
                # Delete MFA devices
                for mfa in client.list_mfa_devices(UserName=user["UserName"]).get(
                    "MFADevices", []
                ):
                    try:
                        client.deactivate_mfa_device(
                            UserName=user["UserName"],
                            SerialNumber=mfa["SerialNumber"],
                        )
                        client.delete_virtual_mfa_device(
                            SerialNumber=mfa["SerialNumber"]
                        )
                    except Exception:
                        pass
                # Detach policies
                for policy in client.list_attached_user_policies(
                    UserName=user["UserName"]
                ).get("AttachedPolicies", []):
                    try:
                        client.detach_user_policy(
                            UserName=user["UserName"], PolicyArn=policy["PolicyArn"]
                        )
                    except Exception:
                        pass
                # Delete inline policies
                for policy_name in client.list_user_policies(
                    UserName=user["UserName"]
                ).get("PolicyNames", []):
                    try:
                        client.delete_user_policy(
                            UserName=user["UserName"], PolicyName=policy_name
                        )
                    except Exception:
                        pass
                # Delete access keys
                for key in client.list_access_keys(UserName=user["UserName"]).get(
                    "AccessKeyMetadata", []
                ):
                    try:
                        client.delete_access_key(
                            UserName=user["UserName"], AccessKeyId=key["AccessKeyId"]
                        )
                    except Exception:
                        pass
                client.delete_user(UserName=user["UserName"])

        # Delete test policies
        for policy in client.list_policies(Scope="Local").get("Policies", []):
            if policy["PolicyName"].startswith(TEST_PREFIX):
                try:
                    client.delete_policy(PolicyArn=policy["Arn"])
                except Exception:
                    pass
    except Exception:
        pass


@pytest.fixture(scope="function")
def user_without_mfa(
    iam_client: Any, test_prefix: str
) -> Generator[Dict[str, Any], None, None]:
    """Create an IAM user without MFA enabled."""
    user_name = f"{test_prefix}-user-no-mfa"

    iam_client.create_user(UserName=user_name)
    user = iam_client.get_user(UserName=user_name)["User"]

    yield {
        "UserName": user_name,
        "Arn": user["Arn"],
        "UserId": user["UserId"],
    }


@pytest.fixture(scope="function")
def user_with_mfa(
    iam_client: Any, test_prefix: str
) -> Generator[Dict[str, Any], None, None]:
    """Create an IAM user with MFA enabled."""
    user_name = f"{test_prefix}-user-with-mfa"

    iam_client.create_user(UserName=user_name)

    # Create virtual MFA device
    mfa_response = iam_client.create_virtual_mfa_device(
        VirtualMFADeviceName=f"{user_name}-mfa"
    )
    mfa_serial = mfa_response["VirtualMFADevice"]["SerialNumber"]

    # Enable MFA (LocalStack accepts any codes, real AWS needs TOTP)
    if not USE_REAL_AWS:
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
def wildcard_policy(
    iam_client: Any, test_prefix: str
) -> Generator[Dict[str, Any], None, None]:
    """Create an IAM policy with wildcard permissions."""
    policy_name = f"{test_prefix}-wildcard-policy"

    policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
    }

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
def least_privilege_policy(
    iam_client: Any, test_prefix: str
) -> Generator[Dict[str, Any], None, None]:
    """Create an IAM policy following least privilege."""
    policy_name = f"{test_prefix}-least-privilege-policy"

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
def s3_client(aws_mode: str) -> Generator[Any, None, None]:
    """Create S3 client for current environment."""
    client = create_client("s3")
    yield client

    # Cleanup: Delete test buckets
    try:
        for bucket in client.list_buckets().get("Buckets", []):
            if bucket["Name"].startswith(TEST_PREFIX.replace("-", "")):
                try:
                    # Delete all objects
                    paginator = client.get_paginator("list_objects_v2")
                    for page in paginator.paginate(Bucket=bucket["Name"]):
                        for obj in page.get("Contents", []):
                            client.delete_object(Bucket=bucket["Name"], Key=obj["Key"])
                    # Delete all versions (if versioning enabled)
                    try:
                        paginator = client.get_paginator("list_object_versions")
                        for page in paginator.paginate(Bucket=bucket["Name"]):
                            for version in page.get("Versions", []):
                                client.delete_object(
                                    Bucket=bucket["Name"],
                                    Key=version["Key"],
                                    VersionId=version["VersionId"],
                                )
                            for marker in page.get("DeleteMarkers", []):
                                client.delete_object(
                                    Bucket=bucket["Name"],
                                    Key=marker["Key"],
                                    VersionId=marker["VersionId"],
                                )
                    except Exception:
                        pass
                    client.delete_bucket(Bucket=bucket["Name"])
                except Exception:
                    pass
    except Exception:
        pass


@pytest.fixture(scope="function")
def unencrypted_bucket(
    s3_client: Any, test_prefix: str, aws_mode: str
) -> Generator[str, None, None]:
    """Create an S3 bucket without encryption."""
    # S3 bucket names must be globally unique and lowercase
    bucket_name = f"{test_prefix.replace('-', '')}-unencrypted"[:63]

    # Create bucket (region-specific for non-us-east-1)
    if AWS_REGION == "us-east-1":
        s3_client.create_bucket(Bucket=bucket_name)
    else:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
        )

    # For real AWS, explicitly disable default encryption if it exists
    if aws_mode == "real_aws":
        try:
            s3_client.delete_bucket_encryption(Bucket=bucket_name)
        except ClientError:
            pass  # No encryption config exists

    yield bucket_name


@pytest.fixture(scope="function")
def encrypted_bucket(s3_client: Any, test_prefix: str) -> Generator[str, None, None]:
    """Create an S3 bucket with SSE-S3 encryption."""
    bucket_name = f"{test_prefix.replace('-', '')}-encrypted"[:63]

    if AWS_REGION == "us-east-1":
        s3_client.create_bucket(Bucket=bucket_name)
    else:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
        )

    s3_client.put_bucket_encryption(
        Bucket=bucket_name,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
            ]
        },
    )

    yield bucket_name


# ============================================================================
# Cost Explorer Fixtures (Real AWS only)
# ============================================================================


@pytest.fixture(scope="function")
def ce_client(aws_mode: str) -> Generator[Any, None, None]:
    """Create Cost Explorer client (Real AWS only)."""
    if aws_mode != "real_aws":
        pytest.skip("Cost Explorer requires real AWS")

    client = create_client("ce")
    yield client


# ============================================================================
# RDS Fixtures (Real AWS or LocalStack Pro)
# ============================================================================


@pytest.fixture(scope="function")
def rds_client(aws_mode: str) -> Generator[Any, None, None]:
    """Create RDS client."""
    client = create_client("rds")

    # Test if RDS is available
    try:
        client.describe_db_instances()
    except ClientError as e:
        if "not subscribed" in str(e) or "AccessDenied" in str(e):
            pytest.skip("RDS not available in current environment")
        raise

    yield client


# ============================================================================
# CloudWatch Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def cloudwatch_client(aws_mode: str) -> Generator[Any, None, None]:
    """Create CloudWatch client."""
    client = create_client("cloudwatch")
    yield client


# ============================================================================
# SSM Fixtures (Real AWS or LocalStack Pro)
# ============================================================================


@pytest.fixture(scope="function")
def ssm_client(aws_mode: str) -> Generator[Any, None, None]:
    """Create SSM client."""
    client = create_client("ssm")

    # Test if SSM is available
    try:
        client.describe_instance_information()
    except ClientError as e:
        if "not subscribed" in str(e) or "AccessDenied" in str(e):
            pytest.skip("SSM not available in current environment")
        raise

    yield client


# ============================================================================
# ELB Fixtures (Real AWS or LocalStack Pro)
# ============================================================================


@pytest.fixture(scope="function")
def elb_client(aws_mode: str) -> Generator[Any, None, None]:
    """Create ELB client."""
    client = create_client("elbv2")

    # Test if ELB is available
    try:
        client.describe_load_balancers()
    except ClientError as e:
        if "not subscribed" in str(e) or "AccessDenied" in str(e):
            pytest.skip("ELB not available in current environment")
        raise

    yield client


# ============================================================================
# Account Fixture
# ============================================================================


@pytest.fixture(scope="function")
def aws_account_id(aws_mode: str) -> str:
    """Return AWS account ID."""
    if aws_mode == "real_aws":
        sts = boto3.client("sts", config=AWS_CONFIG)
        return sts.get_caller_identity()["Account"]
    return "000000000000"  # LocalStack default
