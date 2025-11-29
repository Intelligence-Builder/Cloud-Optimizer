"""Unit tests for AWS scanners."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cloud_optimizer.integrations.aws.base import BaseAWSScanner
from cloud_optimizer.integrations.aws.encryption import EncryptionScanner
from cloud_optimizer.integrations.aws.iam import IAMScanner
from cloud_optimizer.integrations.aws.security_groups import SecurityGroupScanner


class TestBaseAWSScanner:
    """Tests for BaseAWSScanner."""

    def test_scanner_initialization(self):
        """Test scanner initializes with correct region."""

        class TestScanner(BaseAWSScanner):
            async def scan(self, account_id: str):
                return []

            def get_scanner_name(self) -> str:
                return "TestScanner"

        scanner = TestScanner(region="us-west-2")
        assert scanner.region == "us-west-2"

    @patch("cloud_optimizer.integrations.aws.base.boto3.Session")
    def test_get_client(self, mock_session_class):
        """Test get_client returns boto3 client."""

        class TestScanner(BaseAWSScanner):
            async def scan(self, account_id: str):
                return []

            def get_scanner_name(self) -> str:
                return "TestScanner"

        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session

        scanner = TestScanner()
        client = scanner.get_client("ec2")

        assert client is not None
        mock_session.client.assert_called_once()


class TestSecurityGroupScanner:
    """Tests for SecurityGroupScanner."""

    def test_scanner_name(self):
        """Test scanner returns correct name."""
        scanner = SecurityGroupScanner()
        assert scanner.get_scanner_name() == "SecurityGroupScanner"

    @pytest.mark.asyncio
    async def test_scan_with_no_security_groups(self):
        """Test scan with no security groups."""
        scanner = SecurityGroupScanner()

        with patch.object(scanner, "get_client") as mock_get_client:
            mock_ec2 = MagicMock()
            mock_ec2.describe_security_groups.return_value = {"SecurityGroups": []}
            mock_get_client.return_value = mock_ec2

            findings = await scanner.scan("123456789012")
            assert findings == []

    @pytest.mark.asyncio
    async def test_scan_detects_unrestricted_ingress(self):
        """Test scanner detects 0.0.0.0/0 ingress rules."""
        scanner = SecurityGroupScanner()

        mock_sg = {
            "GroupId": "sg-123456",
            "GroupName": "test-sg",
            "IpPermissions": [
                {
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpProtocol": "tcp",
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                }
            ],
        }

        with patch.object(scanner, "get_client") as mock_get_client:
            mock_ec2 = MagicMock()
            mock_ec2.describe_security_groups.return_value = {
                "SecurityGroups": [mock_sg]
            }
            mock_get_client.return_value = mock_ec2

            findings = await scanner.scan("123456789012")

            assert len(findings) == 1
            assert findings[0]["finding_type"] == "overly_permissive_security_group"
            assert findings[0]["severity"] == "critical"
            assert "SSH" in findings[0]["title"]

    def test_calculate_severity_for_risky_port(self):
        """Test severity calculation for risky ports."""
        scanner = SecurityGroupScanner()
        severity = scanner._calculate_severity(22, 22)
        assert severity == "critical"

    def test_calculate_severity_for_wide_range(self):
        """Test severity calculation for wide port ranges."""
        scanner = SecurityGroupScanner()
        # Port range 1000-2000 includes 1433 (SQL Server), a risky port
        severity = scanner._calculate_severity(1000, 2000)
        assert severity == "critical"

    def test_get_port_description(self):
        """Test port description generation."""
        scanner = SecurityGroupScanner()

        # Single port
        desc = scanner._get_port_description(22, 22)
        assert desc == "SSH (22)"

        # Port range
        desc = scanner._get_port_description(80, 443)
        assert desc == "ports 80-443"


class TestIAMScanner:
    """Tests for IAMScanner."""

    def test_scanner_name(self):
        """Test scanner returns correct name."""
        scanner = IAMScanner()
        assert scanner.get_scanner_name() == "IAMScanner"

    @pytest.mark.asyncio
    async def test_scan_empty_account(self):
        """Test scan with no IAM resources."""
        scanner = IAMScanner()

        with patch.object(scanner, "get_client") as mock_get_client:
            mock_iam = MagicMock()
            mock_iam.get_paginator.return_value.paginate.return_value = []
            mock_get_client.return_value = mock_iam

            findings = await scanner.scan("123456789012")
            assert findings == []

    def test_has_wildcard_permissions_detects_wildcard(self):
        """Test wildcard detection in policies."""
        scanner = IAMScanner()

        policy_doc = {
            "Statement": [
                {"Effect": "Allow", "Action": "*", "Resource": "arn:aws:s3:::bucket"}
            ]
        }

        assert scanner._has_wildcard_permissions(policy_doc) is True

    def test_has_wildcard_permissions_no_wildcard(self):
        """Test no wildcard in specific policy."""
        scanner = IAMScanner()

        policy_doc = {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::bucket/*",
                }
            ]
        }

        assert scanner._has_wildcard_permissions(policy_doc) is False


class TestEncryptionScanner:
    """Tests for EncryptionScanner."""

    def test_scanner_name(self):
        """Test scanner returns correct name."""
        scanner = EncryptionScanner()
        assert scanner.get_scanner_name() == "EncryptionScanner"

    @pytest.mark.asyncio
    async def test_scan_detects_unencrypted_ebs(self):
        """Test scanner detects unencrypted EBS volumes."""
        scanner = EncryptionScanner()

        mock_volume = {
            "VolumeId": "vol-123456",
            "Encrypted": False,
            "Size": 100,
            "State": "in-use",
        }

        with patch.object(scanner, "get_client") as mock_get_client:
            mock_ec2 = MagicMock()
            mock_ec2.describe_volumes.return_value = {"Volumes": [mock_volume]}
            mock_get_client.return_value = mock_ec2

            findings = scanner._scan_ebs_volumes("123456789012")

            assert len(findings) == 1
            assert findings[0]["finding_type"] == "unencrypted_ebs_volume"
            assert findings[0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_scan_ignores_encrypted_ebs(self):
        """Test scanner ignores encrypted EBS volumes."""
        scanner = EncryptionScanner()

        mock_volume = {
            "VolumeId": "vol-123456",
            "Encrypted": True,
            "Size": 100,
            "State": "in-use",
        }

        with patch.object(scanner, "get_client") as mock_get_client:
            mock_ec2 = MagicMock()
            mock_ec2.describe_volumes.return_value = {"Volumes": [mock_volume]}
            mock_get_client.return_value = mock_ec2

            findings = scanner._scan_ebs_volumes("123456789012")

            assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_scan_detects_unencrypted_s3(self):
        """Test scanner detects unencrypted S3 buckets."""
        scanner = EncryptionScanner()

        with patch.object(scanner, "get_client") as mock_get_client:
            mock_s3 = MagicMock()
            mock_s3.list_buckets.return_value = {
                "Buckets": [{"Name": "test-bucket"}]
            }
            mock_s3.exceptions.ServerSideEncryptionConfigurationNotFoundError = (
                type("ServerSideEncryptionConfigurationNotFoundError", (Exception,), {})
            )
            mock_s3.get_bucket_encryption.side_effect = (
                mock_s3.exceptions.ServerSideEncryptionConfigurationNotFoundError()
            )
            mock_get_client.return_value = mock_s3

            findings = scanner._scan_s3_buckets("123456789012")

            assert len(findings) == 1
            assert findings[0]["finding_type"] == "unencrypted_s3_bucket"
            assert findings[0]["severity"] == "high"
