"""
Epic 3 Integration Tests - Cloud Optimizer v2 Clean Rebuild

Tests E3-INT-01 through E3-INT-06 as specified in Epic 3 issue.
Uses real FastAPI test client with mocked AWS services.

Requirements:
    docker-compose -f docker/docker-compose.test.yml up -d

Test IDs:
    E3-INT-01: App Startup
    E3-INT-02: IB SDK Connection
    E3-INT-03: AWS SG Scan
    E3-INT-04: AWS IAM Scan
    E3-INT-05: Full Security Scan
    E3-INT-06: Dashboard Metrics
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from cloud_optimizer.main import create_app
from cloud_optimizer.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        app_name="Cloud Optimizer Test",
        app_version="2.0.0-test",
        debug=True,
        log_level="DEBUG",
        ib_platform_url="http://localhost:8000",
        ib_api_key="test-api-key",
        ib_tenant_id="test-tenant",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        aws_default_region="us-east-1",
    )


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestE3INT01AppStartup:
    """
    E3-INT-01: App Startup

    Verify application starts and health endpoint returns 200.
    """

    @pytest.mark.integration
    def test_app_starts_successfully(self, client):
        """App starts and responds to requests."""
        response = client.get("/health")
        assert response.status_code == 200

    @pytest.mark.integration
    def test_health_returns_healthy_status(self, client):
        """Health endpoint returns healthy status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    @pytest.mark.integration
    def test_openapi_docs_available(self, client):
        """OpenAPI documentation is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert data["info"]["title"] == "Cloud Optimizer"


class TestE3INT02IBConnection:
    """
    E3-INT-02: IB SDK Connection

    Verify application connects to Intelligence-Builder platform.
    """

    @pytest.mark.integration
    def test_ready_endpoint_exists(self, client):
        """Ready endpoint exists and responds."""
        response = client.get("/ready")
        assert response.status_code == 200

    @pytest.mark.integration
    def test_ready_reports_ib_status(self, client):
        """Ready endpoint reports IB connection status."""
        response = client.get("/ready")
        data = response.json()
        assert "status" in data
        assert "intelligence_builder" in data

    @pytest.mark.integration
    def test_ready_without_ib_connection(self, client):
        """App handles missing IB connection gracefully."""
        response = client.get("/ready")
        data = response.json()
        # Should still be ready even without IB
        assert data["status"] == "ready"


class TestE3INT03SecurityGroupScan:
    """
    E3-INT-03: AWS SG Scan

    Verify security group scanning works correctly.
    """

    @pytest.fixture
    def mock_ec2_client(self):
        """Create mock EC2 client with test security groups."""
        mock = MagicMock()
        mock.describe_security_groups.return_value = {
            "SecurityGroups": [
                {
                    "GroupId": "sg-12345",
                    "GroupName": "risky-sg",
                    "Description": "Test risky SG",
                    "VpcId": "vpc-12345",
                    "IpPermissions": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 22,
                            "ToPort": 22,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                },
                {
                    "GroupId": "sg-67890",
                    "GroupName": "safe-sg",
                    "Description": "Test safe SG",
                    "VpcId": "vpc-12345",
                    "IpPermissions": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 443,
                            "ToPort": 443,
                            "IpRanges": [{"CidrIp": "10.0.0.0/8"}],
                        }
                    ],
                },
            ]
        }
        return mock

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_sg_scanner_detects_open_ssh(self, mock_ec2_client):
        """Security group scanner detects open SSH port."""
        from cloud_optimizer.integrations.aws.security_groups import (
            SecurityGroupScanner,
        )

        scanner = SecurityGroupScanner()

        with patch.object(scanner, "get_client", return_value=mock_ec2_client):
            findings = await scanner.scan("123456789012")

        # Should find the risky SG with open SSH
        assert len(findings) >= 1
        # Check for SSH-related finding (port 22 or SSH in title)
        ssh_findings = [
            f for f in findings
            if "22" in str(f.get("metadata", {})) or "SSH" in f.get("title", "")
        ]
        assert len(ssh_findings) >= 1
        assert ssh_findings[0]["severity"] == "critical"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_sg_scanner_ignores_safe_rules(self, mock_ec2_client):
        """Security group scanner ignores properly scoped rules."""
        from cloud_optimizer.integrations.aws.security_groups import (
            SecurityGroupScanner,
        )

        scanner = SecurityGroupScanner()

        with patch.object(scanner, "get_client", return_value=mock_ec2_client):
            findings = await scanner.scan("123456789012")

        # Should not flag the safe SG (10.0.0.0/8 is internal)
        safe_findings = [f for f in findings if "safe-sg" in f.get("resource", "")]
        assert len(safe_findings) == 0


class TestE3INT04IAMScan:
    """
    E3-INT-04: AWS IAM Scan

    Verify IAM scanning works correctly.
    """

    @pytest.fixture
    def mock_iam_client(self):
        """Create mock IAM client with test resources."""
        mock = MagicMock()

        # Mock paginators - the scanner uses get_paginator().paginate()
        # User paginator
        mock_user_paginator = MagicMock()
        mock_user_paginator.paginate.return_value = [
            {
                "Users": [
                    {"UserName": "admin-user", "UserId": "AIDA123", "Arn": "arn:aws:iam::123:user/admin"},
                    {"UserName": "no-mfa-user", "UserId": "AIDA456", "Arn": "arn:aws:iam::123:user/no-mfa"},
                ]
            }
        ]

        # Policy paginator
        mock_policy_paginator = MagicMock()
        mock_policy_paginator.paginate.return_value = [
            {
                "Policies": [
                    {
                        "PolicyName": "AdminPolicy",
                        "PolicyId": "ANPA123",
                        "Arn": "arn:aws:iam::123:policy/AdminPolicy",
                        "DefaultVersionId": "v1",
                    }
                ]
            }
        ]

        def get_paginator(name):
            if name == "list_users":
                return mock_user_paginator
            elif name == "list_policies":
                return mock_policy_paginator
            return MagicMock()

        mock.get_paginator = get_paginator

        # MFA devices - no-mfa-user has no MFA
        mock.list_mfa_devices.side_effect = lambda UserName: {
            "MFADevices": [{"SerialNumber": "arn:aws:iam::123:mfa/device"}] if UserName == "admin-user" else []
        }

        # Policy version with wildcard permissions
        mock.get_policy_version.return_value = {
            "PolicyVersion": {
                "Document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {"Effect": "Allow", "Action": "*", "Resource": "*"}
                    ],
                }
            }
        }

        # get_user for last used check
        mock.get_user.return_value = {"User": {"UserName": "test-user"}}

        return mock

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_iam_scanner_detects_no_mfa(self, mock_iam_client):
        """IAM scanner detects users without MFA."""
        from cloud_optimizer.integrations.aws.iam import IAMScanner

        scanner = IAMScanner()

        with patch.object(scanner, "get_client", return_value=mock_iam_client):
            findings = await scanner.scan("123456789012")

        # Check for MFA-related findings (case insensitive)
        mfa_findings = [
            f for f in findings
            if "mfa" in f.get("title", "").lower() or "mfa" in str(f).lower()
        ]
        assert len(mfa_findings) >= 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_iam_scanner_detects_wildcard_permissions(self, mock_iam_client):
        """IAM scanner detects wildcard permissions."""
        from cloud_optimizer.integrations.aws.iam import IAMScanner

        scanner = IAMScanner()

        with patch.object(scanner, "get_client", return_value=mock_iam_client):
            findings = await scanner.scan("123456789012")

        # Check for wildcard-related findings
        wildcard_findings = [
            f for f in findings
            if "wildcard" in f.get("title", "").lower()
            or "overly permissive" in f.get("title", "").lower()
            or "*" in str(f.get("metadata", {}))
        ]
        assert len(wildcard_findings) >= 1


class TestE3INT05FullSecurityScan:
    """
    E3-INT-05: Full Security Scan

    Verify complete security scan orchestration.
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_security_service_runs_all_scanners(self):
        """Security service runs all scanner types."""
        from cloud_optimizer.services.security import SecurityService

        service = SecurityService()

        # Mock all scanners
        with patch.object(service, "_run_scan", new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = [{"finding": "test"}]

            results = await service.scan_account(
                aws_account_id="123456789012",
                scan_types=["security_groups", "iam", "encryption"],
            )

        assert mock_scan.call_count == 3
        assert "security_groups" in results
        assert "iam" in results
        assert "encryption" in results

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_security_service_aggregates_findings(self):
        """Security service correctly aggregates findings from all scanners."""
        from cloud_optimizer.services.security import SecurityService

        service = SecurityService()

        with patch.object(service, "_run_scan", new_callable=AsyncMock) as mock_scan:
            mock_scan.side_effect = [
                [{"type": "sg", "severity": "high"}] * 3,
                [{"type": "iam", "severity": "medium"}] * 2,
                [{"type": "encryption", "severity": "critical"}] * 1,
            ]

            results = await service.scan_account(aws_account_id="123456789012")

        assert results["security_groups"] == 3
        assert results["iam"] == 2
        assert results["encryption"] == 1


class TestE3INT06DashboardMetrics:
    """
    E3-INT-06: Dashboard Metrics

    Verify dashboard metrics aggregation.
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_finding_stats_calculation(self):
        """Finding stats are calculated correctly."""
        from cloud_optimizer.services.security import SecurityService

        # Mock IB service with correct method (query_entities, not entities.search)
        mock_ib = AsyncMock()
        mock_ib.is_connected = True
        mock_ib.query_entities = AsyncMock(return_value={
            "entities": [
                {"id": "1", "metadata": {"severity": "critical", "finding_type": "sg"}},
                {"id": "2", "metadata": {"severity": "critical", "finding_type": "sg"}},
                {"id": "3", "metadata": {"severity": "high", "finding_type": "iam"}},
                {"id": "4", "metadata": {"severity": "medium", "finding_type": "encryption"}},
            ]
        })

        service = SecurityService(ib_service=mock_ib)
        stats = await service.get_finding_stats()

        assert stats["total"] == 4
        assert stats["by_severity"]["critical"] == 2
        assert stats["by_severity"]["high"] == 1
        assert stats["by_severity"]["medium"] == 1

    @pytest.mark.integration
    def test_security_schema_endpoint(self, app, client):
        """Security schema endpoint returns domain schema when IB is configured."""
        # Create mock IB service
        mock_ib = AsyncMock()
        mock_ib.is_connected = True
        mock_ib.get_security_schema = AsyncMock(return_value={
            "domain": "security",
            "entity_types": [
                {"name": "vulnerability", "description": "Security vulnerability"},
                {"name": "security_control", "description": "Security control"},
            ],
            "relationship_types": [
                {"name": "mitigates", "description": "Control mitigates vulnerability"},
            ],
        })

        # Set up app state with mock IB service
        app.state.ib_service = mock_ib

        response = client.get("/api/v1/security/schema")
        assert response.status_code == 200
        data = response.json()
        assert "entity_types" in data
        assert "relationship_types" in data
        assert data["domain"] == "security"
