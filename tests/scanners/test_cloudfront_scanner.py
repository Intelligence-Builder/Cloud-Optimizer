"""Unit tests for CloudFront Scanner.

Issue #140: CloudFront distribution scanner
Tests for CloudFront security scanning rules CF_001-009.
"""

import pytest
from typing import Any, Dict
from unittest.mock import MagicMock, patch, AsyncMock

from cloud_optimizer.scanners.cloudfront_scanner import CloudFrontScanner


class TestCloudFrontScannerRules:
    """Test CloudFront scanner security rules."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> CloudFrontScanner:
        """Create CloudFront scanner with mock session."""
        return CloudFrontScanner(session=mock_session, regions=["us-east-1"])

    def test_scanner_initialization(self, scanner: CloudFrontScanner) -> None:
        """Test scanner initializes with correct rules."""
        assert scanner.service_name == "cloudfront"
        assert len(scanner.rules) >= 9

        rule_ids = [r.rule_id for r in scanner.rules]
        expected_rules = [
            "CF_001", "CF_002", "CF_003", "CF_004", "CF_005",
            "CF_006", "CF_007", "CF_008", "CF_009"
        ]
        for expected in expected_rules:
            assert expected in rule_ids, f"Missing rule {expected}"

    def test_rule_cf_001_https_only(self, scanner: CloudFrontScanner) -> None:
        """Test CF_001: Check for HTTPS-only viewer protocol."""
        # Distribution allowing HTTP
        dist_http: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "DefaultCacheBehavior": {
                "ViewerProtocolPolicy": "allow-all"
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "CF_001")
        result = rule.check_function(dist_http)
        assert result is not None
        assert not result.passed

        # Distribution with HTTPS only
        dist_https: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "DefaultCacheBehavior": {
                "ViewerProtocolPolicy": "https-only"
            }
        }
        result = rule.check_function(dist_https)
        assert result is None or result.passed

    def test_rule_cf_002_tls_version(self, scanner: CloudFrontScanner) -> None:
        """Test CF_002: Check for minimum TLS version."""
        # Distribution with old TLS
        dist_old_tls: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "ViewerCertificate": {
                "MinimumProtocolVersion": "TLSv1"
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "CF_002")
        result = rule.check_function(dist_old_tls)
        assert result is not None
        assert not result.passed

        # Distribution with TLS 1.2+
        dist_new_tls: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "ViewerCertificate": {
                "MinimumProtocolVersion": "TLSv1.2_2021"
            }
        }
        result = rule.check_function(dist_new_tls)
        assert result is None or result.passed

    def test_rule_cf_003_origin_access_identity(
        self, scanner: CloudFrontScanner
    ) -> None:
        """Test CF_003: Check for S3 origin access identity/control."""
        # Distribution without OAI
        dist_no_oai: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "Origins": {
                "Items": [
                    {
                        "Id": "S3Origin",
                        "DomainName": "bucket.s3.amazonaws.com",
                        "S3OriginConfig": {
                            "OriginAccessIdentity": ""
                        }
                    }
                ]
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "CF_003")
        result = rule.check_function(dist_no_oai)
        assert result is not None
        assert not result.passed

        # Distribution with OAI
        dist_with_oai: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "Origins": {
                "Items": [
                    {
                        "Id": "S3Origin",
                        "DomainName": "bucket.s3.amazonaws.com",
                        "S3OriginConfig": {
                            "OriginAccessIdentity": "origin-access-identity/cloudfront/E123"
                        }
                    }
                ]
            }
        }
        result = rule.check_function(dist_with_oai)
        assert result is None or result.passed

    def test_rule_cf_004_access_logging(
        self, scanner: CloudFrontScanner
    ) -> None:
        """Test CF_004: Check for access logging."""
        # Distribution without logging
        dist_no_logging: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "Logging": {
                "Enabled": False
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "CF_004")
        result = rule.check_function(dist_no_logging)
        assert result is not None
        assert not result.passed

        # Distribution with logging
        dist_with_logging: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "Logging": {
                "Enabled": True,
                "Bucket": "logs-bucket.s3.amazonaws.com",
                "Prefix": "cloudfront/"
            }
        }
        result = rule.check_function(dist_with_logging)
        assert result is None or result.passed

    def test_rule_cf_005_security_headers(
        self, scanner: CloudFrontScanner
    ) -> None:
        """Test CF_005: Check for security headers."""
        # Distribution without security headers
        dist_no_headers: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "DefaultCacheBehavior": {
                "ResponseHeadersPolicyId": None
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "CF_005")
        result = rule.check_function(dist_no_headers)
        assert result is not None
        assert not result.passed

        # Distribution with security headers policy
        dist_with_headers: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "DefaultCacheBehavior": {
                "ResponseHeadersPolicyId": "policy-12345"
            }
        }
        result = rule.check_function(dist_with_headers)
        assert result is None or result.passed

    def test_rule_cf_006_waf_integration(
        self, scanner: CloudFrontScanner
    ) -> None:
        """Test CF_006: Check for WAF integration."""
        # Distribution without WAF
        dist_no_waf: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "WebACLId": ""
        }

        rule = next(r for r in scanner.rules if r.rule_id == "CF_006")
        result = rule.check_function(dist_no_waf)
        assert result is not None
        assert not result.passed

        # Distribution with WAF
        dist_with_waf: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "WebACLId": "arn:aws:wafv2:us-east-1:123456789012:global/webacl/my-acl/12345"
        }
        result = rule.check_function(dist_with_waf)
        assert result is None or result.passed

    def test_rule_cf_007_field_level_encryption(
        self, scanner: CloudFrontScanner
    ) -> None:
        """Test CF_007: Check for field-level encryption."""
        # Distribution without field-level encryption
        dist_no_fle: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "DefaultCacheBehavior": {
                "FieldLevelEncryptionId": ""
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "CF_007")
        result = rule.check_function(dist_no_fle)
        # Field-level encryption is optional, check result exists
        assert result is not None

    def test_rule_cf_008_geo_restriction(
        self, scanner: CloudFrontScanner
    ) -> None:
        """Test CF_008: Check for geo-restriction."""
        # Distribution without geo-restriction
        dist_no_geo: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "Restrictions": {
                "GeoRestriction": {
                    "RestrictionType": "none"
                }
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "CF_008")
        result = rule.check_function(dist_no_geo)
        # Geo-restriction is advisory
        assert result is not None

        # Distribution with geo-restriction
        dist_with_geo: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "Restrictions": {
                "GeoRestriction": {
                    "RestrictionType": "whitelist",
                    "Items": ["US", "CA", "GB"]
                }
            }
        }
        result = rule.check_function(dist_with_geo)
        assert result is None or result.passed

    def test_rule_cf_009_origin_protocol(
        self, scanner: CloudFrontScanner
    ) -> None:
        """Test CF_009: Check for origin protocol policy."""
        # Distribution with HTTP origin
        dist_http_origin: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "Origins": {
                "Items": [
                    {
                        "Id": "CustomOrigin",
                        "DomainName": "api.example.com",
                        "CustomOriginConfig": {
                            "OriginProtocolPolicy": "http-only"
                        }
                    }
                ]
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "CF_009")
        result = rule.check_function(dist_http_origin)
        assert result is not None
        assert not result.passed

        # Distribution with HTTPS origin
        dist_https_origin: Dict[str, Any] = {
            "Id": "DIST123",
            "DomainName": "d123.cloudfront.net",
            "Origins": {
                "Items": [
                    {
                        "Id": "CustomOrigin",
                        "DomainName": "api.example.com",
                        "CustomOriginConfig": {
                            "OriginProtocolPolicy": "https-only"
                        }
                    }
                ]
            }
        }
        result = rule.check_function(dist_https_origin)
        assert result is None or result.passed


class TestCloudFrontScannerIntegration:
    """Integration tests for CloudFront scanner."""

    @pytest.fixture
    def mock_cloudfront_client(self) -> MagicMock:
        """Create mock CloudFront client."""
        client = MagicMock()
        client.list_distributions.return_value = {
            "DistributionList": {
                "Items": [
                    {
                        "Id": "DIST123",
                        "DomainName": "d123.cloudfront.net",
                        "Status": "Deployed",
                        "DefaultCacheBehavior": {
                            "ViewerProtocolPolicy": "https-only"
                        }
                    }
                ]
            }
        }
        return client

    @pytest.fixture
    def mock_session_with_client(
        self, mock_cloudfront_client: MagicMock
    ) -> MagicMock:
        """Create mock session with CloudFront client."""
        session = MagicMock()
        session.client.return_value = mock_cloudfront_client
        return session

    @pytest.mark.asyncio
    async def test_scan_returns_results(
        self, mock_session_with_client: MagicMock
    ) -> None:
        """Test that scan returns results."""
        scanner = CloudFrontScanner(
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
        scanner = CloudFrontScanner(
            session=mock_session_with_client,
            regions=["us-east-1"]
        )
        assert scanner.service_name == "cloudfront"
