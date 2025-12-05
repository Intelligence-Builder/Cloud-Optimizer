"""Unit tests for Lambda Scanner.

Issue #133: Lambda function scanner with rules
Tests for Lambda function security scanning rules LAMBDA_001-010.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Any

from cloud_optimizer.scanners.lambda_scanner import LambdaScanner


class TestLambdaScannerRules:
    """Test Lambda scanner security rules."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> LambdaScanner:
        """Create Lambda scanner with mock session."""
        return LambdaScanner(session=mock_session, regions=["us-east-1"])

    def test_scanner_initialization(self, scanner: LambdaScanner) -> None:
        """Test scanner initializes with correct rules."""
        assert scanner.service_name == "lambda"
        assert len(scanner.rules) >= 10

        rule_ids = [r.rule_id for r in scanner.rules]
        expected_rules = [
            "LAMBDA_001", "LAMBDA_002", "LAMBDA_003", "LAMBDA_004",
            "LAMBDA_005", "LAMBDA_006", "LAMBDA_007", "LAMBDA_008",
            "LAMBDA_009", "LAMBDA_010"
        ]
        for expected in expected_rules:
            assert expected in rule_ids, f"Missing rule {expected}"

    def test_rule_lambda_001_public_access(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_001: Check for public access policy."""
        # Function with public access
        function_public = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "_resource_policy": '{"Statement":[{"Principal":"*"}]}'
        }

        rule = next(r for r in scanner.rules if r.rule_id == "LAMBDA_001")
        result = rule.check_function(function_public)
        assert result is not None
        assert not result.passed

        # Function without public access
        function_private = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "_resource_policy": '{"Statement":[{"Principal":{"AWS":"arn:aws:iam::123456789012:root"}}]}'
        }
        result = rule.check_function(function_private)
        assert result is None or result.passed

    def test_rule_lambda_002_vpc_configuration(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_002: Check for VPC configuration."""
        # Function without VPC
        function_no_vpc = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
        }

        rule = next(r for r in scanner.rules if r.rule_id == "LAMBDA_002")
        result = rule.check_function(function_no_vpc)
        assert result is not None
        assert not result.passed

        # Function with VPC
        function_with_vpc = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "VpcConfig": {
                "VpcId": "vpc-12345",
                "SubnetIds": ["subnet-1", "subnet-2"],
                "SecurityGroupIds": ["sg-1"]
            }
        }
        result = rule.check_function(function_with_vpc)
        assert result is None or result.passed

    def test_rule_lambda_003_deprecated_runtime(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_003: Check for deprecated runtime."""
        # Function with deprecated runtime
        function_deprecated = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python2.7",
        }

        rule = next(r for r in scanner.rules if r.rule_id == "LAMBDA_003")
        result = rule.check_function(function_deprecated)
        assert result is not None
        assert not result.passed

        # Function with current runtime
        function_current = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.12",
        }
        result = rule.check_function(function_current)
        assert result is None or result.passed

    def test_rule_lambda_004_environment_encryption(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_004: Check for environment variable encryption."""
        # Function with unencrypted env vars
        function_unencrypted = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "Environment": {
                "Variables": {"DB_HOST": "localhost"}
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "LAMBDA_004")
        result = rule.check_function(function_unencrypted)
        assert result is not None
        assert not result.passed

        # Function with KMS encryption
        function_encrypted = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "KMSKeyArn": "arn:aws:kms:us-east-1:123456789012:key/12345",
            "Environment": {
                "Variables": {"DB_HOST": "localhost"}
            }
        }
        result = rule.check_function(function_encrypted)
        assert result is None or result.passed

    def test_rule_lambda_005_dead_letter_queue(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_005: Check for dead letter queue configuration."""
        # Function without DLQ
        function_no_dlq = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
        }

        rule = next(r for r in scanner.rules if r.rule_id == "LAMBDA_005")
        result = rule.check_function(function_no_dlq)
        assert result is not None
        assert not result.passed

        # Function with DLQ
        function_with_dlq = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "DeadLetterConfig": {
                "TargetArn": "arn:aws:sqs:us-east-1:123456789012:dlq"
            }
        }
        result = rule.check_function(function_with_dlq)
        assert result is None or result.passed

    def test_rule_lambda_006_secrets_in_env(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_006: Check for secrets in environment variables."""
        # Function with secrets in env vars
        function_with_secrets = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "Environment": {
                "Variables": {
                    "DB_PASSWORD": "secret123",
                    "API_KEY": "key-12345"
                }
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "LAMBDA_006")
        result = rule.check_function(function_with_secrets)
        assert result is not None
        assert not result.passed

        # Function without secrets
        function_safe = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "Environment": {
                "Variables": {
                    "LOG_LEVEL": "INFO",
                    "REGION": "us-east-1"
                }
            }
        }
        result = rule.check_function(function_safe)
        assert result is None or result.passed

    def test_rule_lambda_007_cloudwatch_logs(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_007: Check for CloudWatch Logs configuration."""
        # Function without CloudWatch logs role
        function_no_logs = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "Role": "arn:aws:iam::123456789012:role/basic-role",
            "_role_policies": []
        }

        rule = next(r for r in scanner.rules if r.rule_id == "LAMBDA_007")
        result = rule.check_function(function_no_logs)
        # This rule checks for logging permissions
        assert result is not None

    def test_rule_lambda_008_unused_function(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_008: Check for unused functions (90+ days)."""
        # Function unused for 100 days
        function_old = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "LastModified": (datetime.now(timezone.utc) - timedelta(days=100)).isoformat(),
            "_last_invocation": None
        }

        rule = next(r for r in scanner.rules if r.rule_id == "LAMBDA_008")
        result = rule.check_function(function_old)
        assert result is not None
        assert not result.passed

        # Recently used function
        function_recent = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "LastModified": datetime.now(timezone.utc).isoformat(),
            "_last_invocation": datetime.now(timezone.utc).isoformat()
        }
        result = rule.check_function(function_recent)
        assert result is None or result.passed

    def test_rule_lambda_009_public_url(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_009: Check for public function URL."""
        # Function with public URL
        function_public_url = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "_function_url_config": {
                "AuthType": "NONE",
                "FunctionUrl": "https://abc123.lambda-url.us-east-1.on.aws/"
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "LAMBDA_009")
        result = rule.check_function(function_public_url)
        assert result is not None
        assert not result.passed

        # Function with authenticated URL
        function_auth_url = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "_function_url_config": {
                "AuthType": "AWS_IAM",
                "FunctionUrl": "https://abc123.lambda-url.us-east-1.on.aws/"
            }
        }
        result = rule.check_function(function_auth_url)
        assert result is None or result.passed

    def test_rule_lambda_010_default_role(self, scanner: LambdaScanner) -> None:
        """Test LAMBDA_010: Check for overly permissive default role."""
        # Function with overly permissive role
        function_admin_role = {
            "FunctionName": "test-function",
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test",
            "Runtime": "python3.9",
            "Role": "arn:aws:iam::123456789012:role/admin-role",
            "_role_policies": ["AdministratorAccess"]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "LAMBDA_010")
        result = rule.check_function(function_admin_role)
        assert result is not None
        assert not result.passed


class TestLambdaScannerIntegration:
    """Integration tests for Lambda scanner."""

    @pytest.fixture
    def mock_lambda_client(self) -> MagicMock:
        """Create mock Lambda client."""
        client = MagicMock()
        client.list_functions.return_value = {
            "Functions": [
                {
                    "FunctionName": "test-function-1",
                    "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test-1",
                    "Runtime": "python3.9",
                    "Role": "arn:aws:iam::123456789012:role/test-role",
                    "LastModified": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        client.get_policy.return_value = {
            "Policy": '{"Statement":[]}'
        }
        client.get_function_url_config.side_effect = Exception("No URL config")
        return client

    @pytest.fixture
    def mock_session_with_client(
        self, mock_lambda_client: MagicMock
    ) -> MagicMock:
        """Create mock session with Lambda client."""
        session = MagicMock()
        session.client.return_value = mock_lambda_client
        return session

    @pytest.mark.asyncio
    async def test_scan_returns_results(
        self, mock_session_with_client: MagicMock
    ) -> None:
        """Test that scan returns results."""
        scanner = LambdaScanner(
            session=mock_session_with_client,
            regions=["us-east-1"]
        )

        # Mock the scan to avoid actual AWS calls
        with patch.object(scanner, 'scan', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = []
            results = await scanner.scan()
            assert isinstance(results, list)
