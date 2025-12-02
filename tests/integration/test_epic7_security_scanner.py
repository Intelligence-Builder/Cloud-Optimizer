"""
Integration tests for Epic #28 / Issue #30 (Security Scanner Engine).

The test provisions a real AWS security group with an intentionally risky
ingress rule and verifies that SecurityGroupScanner reports the issue.
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import suppress

import boto3
import pytest

from cloud_optimizer.integrations.aws.security_groups import SecurityGroupScanner


def _get_default_vpc_id(ec2_client) -> str:
    response = ec2_client.describe_vpcs(
        Filters=[{"Name": "isDefault", "Values": ["true"]}]
    )
    if not response.get("Vpcs"):
        raise RuntimeError("No default VPC available for creating test security group")
    return response["Vpcs"][0]["VpcId"]


@pytest.mark.integration
@pytest.mark.real_aws
@pytest.mark.asyncio
async def test_security_group_scanner_flags_open_ssh() -> None:
    """Create an insecure security group and ensure the scanner reports it."""
    ec2 = boto3.client("ec2")
    sts = boto3.client("sts")
    account_id = sts.get_caller_identity()["Account"]
    vpc_id = _get_default_vpc_id(ec2)

    sg_name = f"cloud-optimizer-test-{uuid.uuid4().hex[:8]}"
    create_resp = ec2.create_security_group(
        Description="QA test SG for Cloud Optimizer",
        GroupName=sg_name,
        VpcId=vpc_id,
        TagSpecifications=[
            {
                "ResourceType": "security-group",
                "Tags": [{"Key": "Name", "Value": sg_name}],
            }
        ],
    )
    sg_id = create_resp["GroupId"]

    try:
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                }
            ],
        )

        scanner = SecurityGroupScanner()
        findings = await scanner.scan(account_id=account_id)

        matching = [
            f
            for f in findings
            if f["resource_id"] == sg_id and f["severity"] == "critical"
        ]
        assert matching, "Expected scanner to detect open SSH security group"
        assert matching[0]["finding_type"] == "overly_permissive_security_group"
    finally:
        with suppress(Exception):
            ec2.delete_security_group(GroupId=sg_id)
