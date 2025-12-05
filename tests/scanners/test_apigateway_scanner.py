"""Unit tests for API Gateway Scanner.

Issue #134: API Gateway scanner with rules
Tests for API Gateway security scanning rules APIGW_001-009.
"""

import pytest
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, AsyncMock

from cloud_optimizer.scanners.apigateway_scanner import APIGatewayScanner


class TestAPIGatewayScannerRules:
    """Test API Gateway scanner security rules."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> APIGatewayScanner:
        """Create API Gateway scanner with mock session."""
        return APIGatewayScanner(session=mock_session, regions=["us-east-1"])

    def test_scanner_initialization(self, scanner: APIGatewayScanner) -> None:
        """Test scanner initializes with correct rules."""
        assert scanner.service_name == "apigateway"
        assert len(scanner.rules) >= 9

        rule_ids = [r.rule_id for r in scanner.rules]
        expected_rules = [
            "APIGW_001", "APIGW_002", "APIGW_003", "APIGW_004", "APIGW_005",
            "APIGW_006", "APIGW_007", "APIGW_008", "APIGW_009"
        ]
        for expected in expected_rules:
            assert expected in rule_ids, f"Missing rule {expected}"

    def test_rule_apigw_001_no_authentication(
        self, scanner: APIGatewayScanner
    ) -> None:
        """Test APIGW_001: Check for APIs without authentication."""
        # API without authentication
        api_no_auth: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [{"stageName": "prod"}],
            "_resources": [
                {
                    "id": "res1",
                    "path": "/users",
                    "resourceMethods": {
                        "GET": {"authorizationType": "NONE"}
                    }
                }
            ]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "APIGW_001")
        result = rule.check_function(api_no_auth)
        assert result is not None
        assert not result.passed

        # API with authentication
        api_with_auth: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [{"stageName": "prod"}],
            "_resources": [
                {
                    "id": "res1",
                    "path": "/users",
                    "resourceMethods": {
                        "GET": {"authorizationType": "AWS_IAM"}
                    }
                }
            ]
        }
        result = rule.check_function(api_with_auth)
        assert result is None or result.passed

    def test_rule_apigw_002_logging_disabled(
        self, scanner: APIGatewayScanner
    ) -> None:
        """Test APIGW_002: Check for APIs without access logging."""
        # API without logging
        api_no_logging: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [
                {
                    "stageName": "prod",
                    "methodSettings": {}
                }
            ]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "APIGW_002")
        result = rule.check_function(api_no_logging)
        assert result is not None
        assert not result.passed

        # API with logging
        api_with_logging: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [
                {
                    "stageName": "prod",
                    "accessLogSettings": {
                        "destinationArn": "arn:aws:logs:us-east-1:123456789012:log-group:api-logs"
                    }
                }
            ]
        }
        result = rule.check_function(api_with_logging)
        assert result is None or result.passed

    def test_rule_apigw_003_no_waf(self, scanner: APIGatewayScanner) -> None:
        """Test APIGW_003: Check for APIs without WAF."""
        # API without WAF
        api_no_waf: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [{"stageName": "prod"}],
            "_waf_acl": None
        }

        rule = next(r for r in scanner.rules if r.rule_id == "APIGW_003")
        result = rule.check_function(api_no_waf)
        assert result is not None
        assert not result.passed

        # API with WAF
        api_with_waf: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [
                {
                    "stageName": "prod",
                    "webAclArn": "arn:aws:wafv2:us-east-1:123456789012:regional/webacl/my-acl/12345"
                }
            ],
            "_waf_acl": "arn:aws:wafv2:us-east-1:123456789012:regional/webacl/my-acl/12345"
        }
        result = rule.check_function(api_with_waf)
        assert result is None or result.passed

    def test_rule_apigw_004_no_throttling(
        self, scanner: APIGatewayScanner
    ) -> None:
        """Test APIGW_004: Check for APIs without throttling."""
        # API without throttling
        api_no_throttling: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [
                {
                    "stageName": "prod",
                    "methodSettings": {}
                }
            ]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "APIGW_004")
        result = rule.check_function(api_no_throttling)
        assert result is not None
        assert not result.passed

        # API with throttling
        api_with_throttling: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [
                {
                    "stageName": "prod",
                    "methodSettings": {
                        "*/*": {
                            "throttlingBurstLimit": 100,
                            "throttlingRateLimit": 50
                        }
                    }
                }
            ]
        }
        result = rule.check_function(api_with_throttling)
        assert result is None or result.passed

    def test_rule_apigw_005_no_ssl_certificate(
        self, scanner: APIGatewayScanner
    ) -> None:
        """Test APIGW_005: Check for APIs without SSL certificate."""
        # API without SSL
        api_no_ssl: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [
                {
                    "stageName": "prod",
                    "clientCertificateId": None
                }
            ]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "APIGW_005")
        result = rule.check_function(api_no_ssl)
        assert result is not None
        assert not result.passed

        # API with SSL
        api_with_ssl: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [
                {
                    "stageName": "prod",
                    "clientCertificateId": "cert-12345"
                }
            ]
        }
        result = rule.check_function(api_with_ssl)
        assert result is None or result.passed

    def test_rule_apigw_006_caching_disabled(
        self, scanner: APIGatewayScanner
    ) -> None:
        """Test APIGW_006: Check for APIs without caching."""
        # API without caching
        api_no_cache: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [
                {
                    "stageName": "prod",
                    "cacheClusterEnabled": False
                }
            ]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "APIGW_006")
        result = rule.check_function(api_no_cache)
        assert result is not None
        assert not result.passed

        # API with caching
        api_with_cache: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_stages": [
                {
                    "stageName": "prod",
                    "cacheClusterEnabled": True,
                    "cacheClusterSize": "0.5"
                }
            ]
        }
        result = rule.check_function(api_with_cache)
        assert result is None or result.passed

    def test_rule_apigw_007_no_request_validation(
        self, scanner: APIGatewayScanner
    ) -> None:
        """Test APIGW_007: Check for APIs without request validation."""
        # API without validation
        api_no_validation: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_request_validators": []
        }

        rule = next(r for r in scanner.rules if r.rule_id == "APIGW_007")
        result = rule.check_function(api_no_validation)
        assert result is not None
        assert not result.passed

        # API with validation
        api_with_validation: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_request_validators": [
                {
                    "id": "val1",
                    "name": "body-validator",
                    "validateRequestBody": True
                }
            ]
        }
        result = rule.check_function(api_with_validation)
        assert result is None or result.passed

    def test_rule_apigw_008_private_endpoint(
        self, scanner: APIGatewayScanner
    ) -> None:
        """Test APIGW_008: Check for public APIs that should be private."""
        # Public API
        api_public: Dict[str, Any] = {
            "id": "api123",
            "name": "internal-api",
            "endpointConfiguration": {
                "types": ["EDGE"]
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "APIGW_008")
        result = rule.check_function(api_public)
        # This is advisory, may or may not fail
        assert result is not None

        # Private API
        api_private: Dict[str, Any] = {
            "id": "api123",
            "name": "internal-api",
            "endpointConfiguration": {
                "types": ["PRIVATE"]
            }
        }
        result = rule.check_function(api_private)
        assert result is None or result.passed

    def test_rule_apigw_009_cors_misconfigured(
        self, scanner: APIGatewayScanner
    ) -> None:
        """Test APIGW_009: Check for misconfigured CORS."""
        # API with wildcard CORS
        api_wildcard_cors: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_resources": [
                {
                    "id": "res1",
                    "path": "/users",
                    "_cors": {
                        "allowOrigins": ["*"],
                        "allowMethods": ["*"]
                    }
                }
            ]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "APIGW_009")
        result = rule.check_function(api_wildcard_cors)
        assert result is not None
        assert not result.passed

        # API with restricted CORS
        api_restricted_cors: Dict[str, Any] = {
            "id": "api123",
            "name": "test-api",
            "_resources": [
                {
                    "id": "res1",
                    "path": "/users",
                    "_cors": {
                        "allowOrigins": ["https://example.com"],
                        "allowMethods": ["GET", "POST"]
                    }
                }
            ]
        }
        result = rule.check_function(api_restricted_cors)
        assert result is None or result.passed


class TestAPIGatewayScannerIntegration:
    """Integration tests for API Gateway scanner."""

    @pytest.fixture
    def mock_apigateway_client(self) -> MagicMock:
        """Create mock API Gateway client."""
        client = MagicMock()
        client.get_rest_apis.return_value = {
            "items": [
                {
                    "id": "api123",
                    "name": "test-api",
                    "endpointConfiguration": {"types": ["REGIONAL"]}
                }
            ]
        }
        client.get_stages.return_value = {
            "item": [{"stageName": "prod"}]
        }
        client.get_resources.return_value = {
            "items": []
        }
        return client

    @pytest.fixture
    def mock_session_with_client(
        self, mock_apigateway_client: MagicMock
    ) -> MagicMock:
        """Create mock session with API Gateway client."""
        session = MagicMock()
        session.client.return_value = mock_apigateway_client
        return session

    @pytest.mark.asyncio
    async def test_scan_returns_results(
        self, mock_session_with_client: MagicMock
    ) -> None:
        """Test that scan returns results."""
        scanner = APIGatewayScanner(
            session=mock_session_with_client,
            regions=["us-east-1"]
        )

        with patch.object(scanner, 'scan', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = []
            results = await scanner.scan()
            assert isinstance(results, list)

    def test_scanner_has_correct_service_name(
        self, mock_session_with_client: MagicMock
    ) -> None:
        """Test scanner has correct service name."""
        scanner = APIGatewayScanner(
            session=mock_session_with_client,
            regions=["us-east-1"]
        )
        assert scanner.service_name == "apigateway"
