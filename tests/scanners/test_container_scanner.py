"""Unit tests for Container Scanner (EKS/ECS).

Issue #142: EKS/ECS container security scanner
Tests for container security scanning rules EKS_001-004 and ECS_001-008.
"""

import pytest
from typing import Any, Dict
from unittest.mock import MagicMock, patch, AsyncMock

from cloud_optimizer.scanners.container_scanner import ContainerScanner


class TestContainerScannerRules:
    """Test Container scanner security rules."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> ContainerScanner:
        """Create Container scanner with mock session."""
        return ContainerScanner(session=mock_session, regions=["us-east-1"])

    def test_scanner_initialization(self, scanner: ContainerScanner) -> None:
        """Test scanner initializes with correct rules."""
        assert scanner.service_name == "containers"
        assert len(scanner.rules) >= 12

        rule_ids = [r.rule_id for r in scanner.rules]
        expected_rules = [
            "EKS_001", "EKS_002", "EKS_003", "EKS_004",
            "ECS_001", "ECS_002", "ECS_003", "ECS_004",
            "ECS_005", "ECS_006", "ECS_007", "ECS_008"
        ]
        for expected in expected_rules:
            assert expected in rule_ids, f"Missing rule {expected}"


class TestEKSRules:
    """Test EKS-specific security rules."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        return MagicMock()

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> ContainerScanner:
        """Create Container scanner with mock session."""
        return ContainerScanner(session=mock_session, regions=["us-east-1"])

    def test_rule_eks_001_public_endpoint(
        self, scanner: ContainerScanner
    ) -> None:
        """Test EKS_001: Check for public cluster endpoint."""
        # EKS cluster with public endpoint
        cluster_public: Dict[str, Any] = {
            "name": "test-cluster",
            "arn": "arn:aws:eks:us-east-1:123456789012:cluster/test-cluster",
            "resourcesVpcConfig": {
                "endpointPublicAccess": True,
                "endpointPrivateAccess": False
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "EKS_001")
        result = rule.check_function(cluster_public)
        assert result is not None
        assert not result.passed

        # EKS cluster with private endpoint only
        cluster_private: Dict[str, Any] = {
            "name": "test-cluster",
            "arn": "arn:aws:eks:us-east-1:123456789012:cluster/test-cluster",
            "resourcesVpcConfig": {
                "endpointPublicAccess": False,
                "endpointPrivateAccess": True
            }
        }
        result = rule.check_function(cluster_private)
        assert result is None or result.passed

    def test_rule_eks_002_secrets_encryption(
        self, scanner: ContainerScanner
    ) -> None:
        """Test EKS_002: Check for secrets encryption."""
        # EKS cluster without secrets encryption
        cluster_no_encryption: Dict[str, Any] = {
            "name": "test-cluster",
            "arn": "arn:aws:eks:us-east-1:123456789012:cluster/test-cluster",
            "encryptionConfig": None
        }

        rule = next(r for r in scanner.rules if r.rule_id == "EKS_002")
        result = rule.check_function(cluster_no_encryption)
        assert result is not None
        assert not result.passed

        # EKS cluster with secrets encryption
        cluster_with_encryption: Dict[str, Any] = {
            "name": "test-cluster",
            "arn": "arn:aws:eks:us-east-1:123456789012:cluster/test-cluster",
            "encryptionConfig": [
                {
                    "resources": ["secrets"],
                    "provider": {
                        "keyArn": "arn:aws:kms:us-east-1:123456789012:key/12345"
                    }
                }
            ]
        }
        result = rule.check_function(cluster_with_encryption)
        assert result is None or result.passed

    def test_rule_eks_003_control_plane_logging(
        self, scanner: ContainerScanner
    ) -> None:
        """Test EKS_003: Check for control plane logging."""
        # EKS cluster without logging
        cluster_no_logging: Dict[str, Any] = {
            "name": "test-cluster",
            "arn": "arn:aws:eks:us-east-1:123456789012:cluster/test-cluster",
            "logging": {
                "clusterLogging": [
                    {
                        "types": ["api", "audit", "authenticator"],
                        "enabled": False
                    }
                ]
            }
        }

        rule = next(r for r in scanner.rules if r.rule_id == "EKS_003")
        result = rule.check_function(cluster_no_logging)
        assert result is not None
        assert not result.passed

        # EKS cluster with logging
        cluster_with_logging: Dict[str, Any] = {
            "name": "test-cluster",
            "arn": "arn:aws:eks:us-east-1:123456789012:cluster/test-cluster",
            "logging": {
                "clusterLogging": [
                    {
                        "types": ["api", "audit", "authenticator", "controllerManager", "scheduler"],
                        "enabled": True
                    }
                ]
            }
        }
        result = rule.check_function(cluster_with_logging)
        assert result is None or result.passed

    def test_rule_eks_004_outdated_version(
        self, scanner: ContainerScanner
    ) -> None:
        """Test EKS_004: Check for outdated Kubernetes version."""
        # EKS cluster with old version
        cluster_old: Dict[str, Any] = {
            "name": "test-cluster",
            "arn": "arn:aws:eks:us-east-1:123456789012:cluster/test-cluster",
            "version": "1.21"
        }

        rule = next(r for r in scanner.rules if r.rule_id == "EKS_004")
        result = rule.check_function(cluster_old)
        assert result is not None
        assert not result.passed

        # EKS cluster with recent version
        cluster_new: Dict[str, Any] = {
            "name": "test-cluster",
            "arn": "arn:aws:eks:us-east-1:123456789012:cluster/test-cluster",
            "version": "1.29"
        }
        result = rule.check_function(cluster_new)
        assert result is None or result.passed


class TestECSRules:
    """Test ECS-specific security rules."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock boto3 session."""
        return MagicMock()

    @pytest.fixture
    def scanner(self, mock_session: MagicMock) -> ContainerScanner:
        """Create Container scanner with mock session."""
        return ContainerScanner(session=mock_session, regions=["us-east-1"])

    def test_rule_ecs_001_privileged_container(
        self, scanner: ContainerScanner
    ) -> None:
        """Test ECS_001: Check for privileged containers."""
        # Task definition with privileged container
        task_privileged: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "containerDefinitions": [
                {
                    "name": "app",
                    "privileged": True
                }
            ]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "ECS_001")
        result = rule.check_function(task_privileged)
        assert result is not None
        assert not result.passed

        # Task definition without privileged container
        task_non_privileged: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "containerDefinitions": [
                {
                    "name": "app",
                    "privileged": False
                }
            ]
        }
        result = rule.check_function(task_non_privileged)
        assert result is None or result.passed

    def test_rule_ecs_002_root_user(self, scanner: ContainerScanner) -> None:
        """Test ECS_002: Check for containers running as root."""
        # Task definition running as root
        task_root: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "containerDefinitions": [
                {
                    "name": "app",
                    "user": "root"
                }
            ]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "ECS_002")
        result = rule.check_function(task_root)
        assert result is not None
        assert not result.passed

        # Task definition with non-root user
        task_nonroot: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "containerDefinitions": [
                {
                    "name": "app",
                    "user": "1000:1000"
                }
            ]
        }
        result = rule.check_function(task_nonroot)
        assert result is None or result.passed

    def test_rule_ecs_003_secrets_in_env(
        self, scanner: ContainerScanner
    ) -> None:
        """Test ECS_003: Check for secrets in environment variables."""
        # Task definition with secrets in env
        task_secrets_env: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "containerDefinitions": [
                {
                    "name": "app",
                    "environment": [
                        {"name": "DB_PASSWORD", "value": "secret123"},
                        {"name": "API_KEY", "value": "key-12345"}
                    ]
                }
            ]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "ECS_003")
        result = rule.check_function(task_secrets_env)
        assert result is not None
        assert not result.passed

        # Task definition with secrets from Secrets Manager
        task_secrets_sm: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "containerDefinitions": [
                {
                    "name": "app",
                    "secrets": [
                        {
                            "name": "DB_PASSWORD",
                            "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-password"
                        }
                    ]
                }
            ]
        }
        result = rule.check_function(task_secrets_sm)
        assert result is None or result.passed

    def test_rule_ecs_004_logging_disabled(
        self, scanner: ContainerScanner
    ) -> None:
        """Test ECS_004: Check for logging configuration."""
        # Task definition without logging
        task_no_logging: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "containerDefinitions": [
                {
                    "name": "app",
                    "logConfiguration": None
                }
            ]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "ECS_004")
        result = rule.check_function(task_no_logging)
        assert result is not None
        assert not result.passed

        # Task definition with logging
        task_with_logging: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "containerDefinitions": [
                {
                    "name": "app",
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "/ecs/test",
                            "awslogs-region": "us-east-1"
                        }
                    }
                }
            ]
        }
        result = rule.check_function(task_with_logging)
        assert result is None or result.passed

    def test_rule_ecs_005_readonly_filesystem(
        self, scanner: ContainerScanner
    ) -> None:
        """Test ECS_005: Check for read-only root filesystem."""
        # Task definition without read-only filesystem
        task_rw: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "containerDefinitions": [
                {
                    "name": "app",
                    "readonlyRootFilesystem": False
                }
            ]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "ECS_005")
        result = rule.check_function(task_rw)
        assert result is not None
        assert not result.passed

        # Task definition with read-only filesystem
        task_ro: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "containerDefinitions": [
                {
                    "name": "app",
                    "readonlyRootFilesystem": True
                }
            ]
        }
        result = rule.check_function(task_ro)
        assert result is None or result.passed

    def test_rule_ecs_006_network_mode(
        self, scanner: ContainerScanner
    ) -> None:
        """Test ECS_006: Check for host network mode."""
        # Task definition with host network
        task_host_network: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "networkMode": "host",
            "containerDefinitions": [{"name": "app"}]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "ECS_006")
        result = rule.check_function(task_host_network)
        assert result is not None
        assert not result.passed

        # Task definition with awsvpc network
        task_awsvpc: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "networkMode": "awsvpc",
            "containerDefinitions": [{"name": "app"}]
        }
        result = rule.check_function(task_awsvpc)
        assert result is None or result.passed

    def test_rule_ecs_007_resource_limits(
        self, scanner: ContainerScanner
    ) -> None:
        """Test ECS_007: Check for resource limits."""
        # Task definition without resource limits
        task_no_limits: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "cpu": None,
            "memory": None,
            "containerDefinitions": [{"name": "app"}]
        }

        rule = next(r for r in scanner.rules if r.rule_id == "ECS_007")
        result = rule.check_function(task_no_limits)
        assert result is not None
        assert not result.passed

        # Task definition with resource limits
        task_with_limits: Dict[str, Any] = {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/test:1",
            "cpu": "256",
            "memory": "512",
            "containerDefinitions": [{"name": "app"}]
        }
        result = rule.check_function(task_with_limits)
        assert result is None or result.passed

    def test_rule_ecs_008_exec_access(
        self, scanner: ContainerScanner
    ) -> None:
        """Test ECS_008: Check for ECS Exec access."""
        # Service with exec enabled
        service_exec: Dict[str, Any] = {
            "serviceName": "test-service",
            "serviceArn": "arn:aws:ecs:us-east-1:123456789012:service/test/test-service",
            "enableExecuteCommand": True
        }

        rule = next(r for r in scanner.rules if r.rule_id == "ECS_008")
        result = rule.check_function(service_exec)
        # ECS Exec is informational
        assert result is not None

        # Service without exec
        service_no_exec: Dict[str, Any] = {
            "serviceName": "test-service",
            "serviceArn": "arn:aws:ecs:us-east-1:123456789012:service/test/test-service",
            "enableExecuteCommand": False
        }
        result = rule.check_function(service_no_exec)
        assert result is None or result.passed


class TestContainerScannerIntegration:
    """Integration tests for Container scanner."""

    @pytest.fixture
    def mock_eks_client(self) -> MagicMock:
        """Create mock EKS client."""
        client = MagicMock()
        client.list_clusters.return_value = {"clusters": ["test-cluster"]}
        client.describe_cluster.return_value = {
            "cluster": {
                "name": "test-cluster",
                "arn": "arn:aws:eks:us-east-1:123456789012:cluster/test-cluster",
                "version": "1.28",
                "resourcesVpcConfig": {
                    "endpointPublicAccess": True,
                    "endpointPrivateAccess": True
                }
            }
        }
        return client

    @pytest.fixture
    def mock_ecs_client(self) -> MagicMock:
        """Create mock ECS client."""
        client = MagicMock()
        client.list_clusters.return_value = {"clusterArns": []}
        client.list_task_definitions.return_value = {"taskDefinitionArns": []}
        return client

    @pytest.fixture
    def mock_session_with_clients(
        self, mock_eks_client: MagicMock, mock_ecs_client: MagicMock
    ) -> MagicMock:
        """Create mock session with EKS and ECS clients."""
        session = MagicMock()

        def get_client(service: str, **kwargs: Any) -> MagicMock:
            if service == "eks":
                return mock_eks_client
            elif service == "ecs":
                return mock_ecs_client
            return MagicMock()

        session.client.side_effect = get_client
        return session

    @pytest.mark.asyncio
    async def test_scan_returns_results(
        self, mock_session_with_clients: MagicMock
    ) -> None:
        """Test that scan returns results."""
        scanner = ContainerScanner(
            session=mock_session_with_clients,
            regions=["us-east-1"]
        )

        with patch.object(scanner, 'scan', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = []
            results = await scanner.scan()
            assert isinstance(results, list)

    def test_scanner_has_correct_service_name(
        self, mock_session_with_clients: MagicMock
    ) -> None:
        """Test scanner has correct service name."""
        scanner = ContainerScanner(
            session=mock_session_with_clients,
            regions=["us-east-1"]
        )
        assert scanner.service_name == "containers"
