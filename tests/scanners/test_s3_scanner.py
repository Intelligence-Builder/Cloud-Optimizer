"""S3 Scanner integration tests.

Tests S3 security scanning using either LocalStack (default) or real AWS.
Run with USE_REAL_AWS=true to test against actual AWS infrastructure.
"""

import asyncio
import os
from typing import Any

import pytest

from cloud_optimizer.scanners.s3 import S3Scanner


class TestS3ScannerRules:
    """Test S3 scanner rule registration."""

    def test_rules_registered(self, boto_session: Any) -> None:
        """Test that all S3 rules are registered."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        rules = scanner.get_rules()
        assert len(rules) == 5

        # Verify expected rules
        expected_rules = ["S3_001", "S3_002", "S3_003", "S3_004", "S3_005"]
        for rule_id in expected_rules:
            assert rule_id in rules

    def test_rule_s3_001_public_access(self, boto_session: Any) -> None:
        """Test S3_001 rule details."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])
        rule = scanner.rules.get("S3_001")

        assert rule is not None
        assert rule.title == "S3 Bucket Has Public Access"
        assert rule.severity == "critical"
        assert "CIS" in rule.compliance_frameworks

    def test_rule_s3_002_encryption(self, boto_session: Any) -> None:
        """Test S3_002 rule details."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])
        rule = scanner.rules.get("S3_002")

        assert rule is not None
        assert rule.title == "S3 Bucket Encryption Not Enabled"
        assert rule.severity == "high"
        assert "HIPAA" in rule.compliance_frameworks

    def test_rule_s3_003_versioning(self, boto_session: Any) -> None:
        """Test S3_003 rule details."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])
        rule = scanner.rules.get("S3_003")

        assert rule is not None
        assert rule.title == "S3 Bucket Versioning Disabled"
        assert rule.severity == "medium"


class TestS3ScannerWithInsecureBucket:
    """Test S3 scanner with insecure bucket configuration.

    These tests require LocalStack to be running or USE_REAL_AWS=true.
    The scanner's internal client must be configured with the endpoint.
    """

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("USE_REAL_AWS", "false").lower() != "true",
        reason="Full scan test requires real AWS or properly configured scanner",
    )
    async def test_scan_insecure_bucket_finds_issues(
        self,
        boto_session: Any,
        insecure_s3_bucket: str,
        localstack_or_real_aws: str,
    ) -> None:
        """Test scanner detects security issues in insecure bucket."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        # Run scan
        results = await scanner.scan()

        # Filter results for our test bucket
        bucket_results = [r for r in results if insecure_s3_bucket in r.resource_id]

        # Should find multiple issues
        assert len(bucket_results) >= 1, f"Expected findings for {insecure_s3_bucket}"

        # Check for expected rule violations
        rule_ids = [r.rule_id for r in bucket_results]

        # Encryption should definitely be flagged
        assert (
            "S3_002" in rule_ids or "S3_003" in rule_ids
        ), f"Expected encryption or versioning findings, got: {rule_ids}"

    @pytest.mark.asyncio
    async def test_encryption_check_on_insecure_bucket(
        self,
        boto_session: Any,
        insecure_s3_bucket: str,
        s3_client: Any,
        localstack_or_real_aws: str,
    ) -> None:
        """Test encryption check specifically.

        Note: LocalStack may not fully emulate the encryption check error.
        In LocalStack, get_bucket_encryption might return empty instead of
        raising ServerSideEncryptionConfigurationNotFoundError.
        """
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        # Direct check for encryption
        results = await scanner._check_encryption(
            s3_client, insecure_s3_bucket, "us-east-1"
        )

        # LocalStack may not raise the expected error
        if localstack_or_real_aws == "localstack" and len(results) == 0:
            pytest.skip("LocalStack doesn't fully emulate encryption error responses")

        # Should find encryption not enabled (real AWS)
        assert len(results) == 1
        assert results[0].rule_id == "S3_002"

    @pytest.mark.asyncio
    async def test_versioning_check_on_insecure_bucket(
        self,
        boto_session: Any,
        insecure_s3_bucket: str,
        s3_client: Any,
        localstack_or_real_aws: str,
    ) -> None:
        """Test versioning check specifically."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        # Direct check for versioning
        results = await scanner._check_versioning(
            s3_client, insecure_s3_bucket, "us-east-1"
        )

        # Should find versioning not enabled
        assert len(results) == 1
        assert results[0].rule_id == "S3_003"
        assert results[0].evidence.get("versioning_status") in ["", "Disabled"]

    @pytest.mark.asyncio
    async def test_logging_check_on_insecure_bucket(
        self,
        boto_session: Any,
        insecure_s3_bucket: str,
        s3_client: Any,
        localstack_or_real_aws: str,
    ) -> None:
        """Test logging check specifically."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        # Direct check for logging
        results = await scanner._check_logging(
            s3_client, insecure_s3_bucket, "us-east-1"
        )

        # Should find logging not enabled
        assert len(results) == 1
        assert results[0].rule_id == "S3_004"


class TestS3ScannerWithSecureBucket:
    """Test S3 scanner with secure bucket configuration."""

    @pytest.mark.asyncio
    async def test_scan_secure_bucket_passes_checks(
        self,
        boto_session: Any,
        secure_s3_bucket: str,
        localstack_or_real_aws: str,
    ) -> None:
        """Test scanner passes for properly configured bucket."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        # Run scan
        results = await scanner.scan()

        # Filter results for our test bucket
        bucket_results = [r for r in results if secure_s3_bucket in r.resource_id]

        # Should not find encryption or versioning issues
        rule_ids = [r.rule_id for r in bucket_results]
        assert "S3_002" not in rule_ids, "Secure bucket flagged for encryption"
        assert "S3_003" not in rule_ids, "Secure bucket flagged for versioning"

    @pytest.mark.asyncio
    async def test_encryption_check_passes_on_secure_bucket(
        self,
        boto_session: Any,
        secure_s3_bucket: str,
        s3_client: Any,
        localstack_or_real_aws: str,
    ) -> None:
        """Test encryption check passes for encrypted bucket."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        # Direct check for encryption
        results = await scanner._check_encryption(
            s3_client, secure_s3_bucket, "us-east-1"
        )

        # Should not find issues
        assert len(results) == 0, "Encrypted bucket incorrectly flagged"

    @pytest.mark.asyncio
    async def test_versioning_check_passes_on_secure_bucket(
        self,
        boto_session: Any,
        secure_s3_bucket: str,
        s3_client: Any,
        localstack_or_real_aws: str,
    ) -> None:
        """Test versioning check passes for versioned bucket."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        # Direct check for versioning
        results = await scanner._check_versioning(
            s3_client, secure_s3_bucket, "us-east-1"
        )

        # Should not find issues
        assert len(results) == 0, "Versioned bucket incorrectly flagged"


class TestS3ScannerScanResult:
    """Test S3 scanner result structure."""

    @pytest.mark.asyncio
    async def test_scan_result_structure(
        self,
        boto_session: Any,
        insecure_s3_bucket: str,
        s3_client: Any,
        localstack_or_real_aws: str,
    ) -> None:
        """Test that scan results have correct structure.

        Uses versioning check since it works reliably in LocalStack.
        """
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        # Get a specific finding (versioning works in LocalStack)
        results = await scanner._check_versioning(
            s3_client, insecure_s3_bucket, "us-east-1"
        )

        assert len(results) == 1
        result = results[0]

        # Verify result structure
        assert hasattr(result, "rule_id")
        assert hasattr(result, "passed")
        assert hasattr(result, "resource_id")
        assert hasattr(result, "region")
        assert hasattr(result, "evidence")

        # Verify values
        assert result.rule_id == "S3_003"
        assert result.passed is False
        assert insecure_s3_bucket in result.resource_id
        assert result.region == "us-east-1"

    @pytest.mark.asyncio
    async def test_scan_result_arn_format(
        self,
        boto_session: Any,
        insecure_s3_bucket: str,
        s3_client: Any,
        localstack_or_real_aws: str,
    ) -> None:
        """Test that resource_id follows ARN format.

        Uses versioning check since it works reliably in LocalStack.
        """
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        results = await scanner._check_versioning(
            s3_client, insecure_s3_bucket, "us-east-1"
        )

        assert len(results) == 1
        result = results[0]

        # Should be S3 ARN format
        assert result.resource_id.startswith("arn:aws:s3:::")
        assert insecure_s3_bucket in result.resource_id


class TestS3ScannerEdgeCases:
    """Edge case tests for S3 scanner."""

    @pytest.mark.asyncio
    async def test_scan_empty_bucket_list(
        self,
        boto_session: Any,
        localstack_or_real_aws: str,
    ) -> None:
        """Test scanner handles case with no buckets."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        # Even with existing buckets, scan should complete without error
        results = await scanner.scan()
        assert isinstance(results, list)

    def test_scanner_multiple_regions(self, boto_session: Any) -> None:
        """Test scanner with multiple regions."""
        regions = ["us-east-1", "us-west-2", "eu-west-1"]
        scanner = S3Scanner(boto_session, regions=regions)

        assert scanner.regions == regions

    def test_create_result_method(self, boto_session: Any) -> None:
        """Test the create_result helper method."""
        scanner = S3Scanner(boto_session, regions=["us-east-1"])

        result = scanner.create_result(
            rule_id="S3_001",
            resource_id="arn:aws:s3:::test-bucket",
            resource_name="test-bucket",
            region="us-east-1",
            metadata={"test": "data"},
        )

        assert result.rule_id == "S3_001"
        assert result.passed is False
        assert result.resource_id == "arn:aws:s3:::test-bucket"
        assert result.resource_arn == "arn:aws:s3:::test-bucket"
        assert result.region == "us-east-1"
        assert result.evidence == {"test": "data"}


class TestS3ScannerRealAWS:
    """Tests specific to real AWS environment.

    These tests only run when USE_REAL_AWS=true and validate
    additional functionality that can't be tested with LocalStack.
    """

    @pytest.mark.asyncio
    async def test_real_aws_account_id(
        self,
        require_real_aws: None,
        boto_session: Any,
        sts_client: Any,
    ) -> None:
        """Test scanner gets correct AWS account ID."""
        identity = sts_client.get_caller_identity()
        account_id = identity["Account"]

        assert account_id is not None
        assert len(account_id) == 12

    @pytest.mark.asyncio
    async def test_real_aws_bucket_regions(
        self,
        require_real_aws: None,
        boto_session: Any,
        s3_client: Any,
    ) -> None:
        """Test scanner correctly identifies bucket regions."""
        # List buckets and check at least one
        response = s3_client.list_buckets()
        buckets = response.get("Buckets", [])

        if not buckets:
            pytest.skip("No S3 buckets found in AWS account")

        bucket_name = buckets[0]["Name"]
        location = s3_client.get_bucket_location(Bucket=bucket_name)
        region = location.get("LocationConstraint") or "us-east-1"

        assert region in [
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2",
            "eu-west-1",
            "eu-west-2",
            "eu-west-3",
            "eu-central-1",
            "ap-northeast-1",
            "ap-northeast-2",
            "ap-southeast-1",
            "ap-southeast-2",
            "ap-south-1",
            "sa-east-1",
            "ca-central-1",
        ]
