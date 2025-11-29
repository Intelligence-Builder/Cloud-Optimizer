"""Unit tests for SecurityService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cloud_optimizer.services.security import SecurityService


class TestSecurityService:
    """Tests for SecurityService."""

    @pytest.fixture
    def mock_ib_service(self):
        """Create mock IB service."""
        mock_ib = MagicMock()
        mock_ib.is_connected = True
        mock_ib.create_entity = AsyncMock()
        mock_ib.query_entities = AsyncMock(return_value={"entities": []})
        return mock_ib

    @pytest.fixture
    def security_service(self, mock_ib_service):
        """Create SecurityService with mocked dependencies."""
        return SecurityService(ib_service=mock_ib_service)

    def test_service_initialization(self, mock_ib_service):
        """Test service initializes correctly."""
        service = SecurityService(ib_service=mock_ib_service)
        assert service.ib_service is mock_ib_service

    def test_get_scanner_creates_security_group_scanner(self, security_service):
        """Test get_scanner creates SecurityGroupScanner."""
        scanner = security_service._get_scanner("security_groups", "us-east-1")
        assert scanner is not None
        assert scanner.get_scanner_name() == "SecurityGroupScanner"

    def test_get_scanner_creates_iam_scanner(self, security_service):
        """Test get_scanner creates IAMScanner."""
        scanner = security_service._get_scanner("iam", "us-east-1")
        assert scanner is not None
        assert scanner.get_scanner_name() == "IAMScanner"

    def test_get_scanner_creates_encryption_scanner(self, security_service):
        """Test get_scanner creates EncryptionScanner."""
        scanner = security_service._get_scanner("encryption", "us-east-1")
        assert scanner is not None
        assert scanner.get_scanner_name() == "EncryptionScanner"

    def test_get_scanner_raises_for_unknown_type(self, security_service):
        """Test get_scanner raises for unknown scan type."""
        with pytest.raises(ValueError, match="Unknown scan type"):
            security_service._get_scanner("unknown_type", "us-east-1")

    def test_get_scanner_caching(self, security_service):
        """Test scanner instances are cached."""
        scanner1 = security_service._get_scanner("security_groups", "us-east-1")
        scanner2 = security_service._get_scanner("security_groups", "us-east-1")
        assert scanner1 is scanner2

    @pytest.mark.asyncio
    async def test_scan_account_runs_all_scan_types(
        self, security_service, mock_ib_service
    ):
        """Test scan_account runs all scan types by default."""
        with patch.object(security_service, "_run_scan") as mock_run_scan:
            mock_run_scan.return_value = []

            results = await security_service.scan_account("123456789012")

            assert "security_groups" in results
            assert "iam" in results
            assert "encryption" in results
            assert mock_run_scan.call_count == 3

    @pytest.mark.asyncio
    async def test_scan_account_runs_specific_scan_types(
        self, security_service, mock_ib_service
    ):
        """Test scan_account runs only specified scan types."""
        with patch.object(security_service, "_run_scan") as mock_run_scan:
            mock_run_scan.return_value = []

            results = await security_service.scan_account(
                "123456789012", scan_types=["iam"]
            )

            assert "iam" in results
            assert "security_groups" not in results
            assert mock_run_scan.call_count == 1

    @pytest.mark.asyncio
    async def test_scan_account_returns_finding_counts(
        self, security_service, mock_ib_service
    ):
        """Test scan_account returns correct finding counts."""
        with patch.object(security_service, "_run_scan") as mock_run_scan:
            mock_run_scan.return_value = [
                {"finding_type": "test1"},
                {"finding_type": "test2"},
            ]

            results = await security_service.scan_account(
                "123456789012", scan_types=["security_groups"]
            )

            assert results["security_groups"] == 2

    @pytest.mark.asyncio
    async def test_run_scan_executes_scanner(self, security_service):
        """Test _run_scan executes the correct scanner."""
        mock_scanner = MagicMock()
        mock_scanner.scan = AsyncMock(
            return_value=[{"finding_type": "test_finding"}]
        )

        with patch.object(
            security_service, "_get_scanner", return_value=mock_scanner
        ):
            findings = await security_service._run_scan(
                "security_groups", "123456789012", "us-east-1"
            )

            assert len(findings) == 1
            mock_scanner.scan.assert_called_once_with("123456789012")

    @pytest.mark.asyncio
    async def test_persist_findings_creates_entities(
        self, security_service, mock_ib_service
    ):
        """Test _persist_findings creates entities in IB."""
        findings = [
            {
                "title": "Test Finding",
                "finding_type": "test",
                "severity": "high",
                "description": "Test description",
                "resource_arn": "arn:aws:test",
                "resource_type": "test",
                "aws_account_id": "123456789012",
                "region": "us-east-1",
                "remediation": "Fix it",
            }
        ]

        await security_service._persist_findings(findings)

        mock_ib_service.create_entity.assert_called_once()
        call_args = mock_ib_service.create_entity.call_args[0][0]
        assert call_args["entity_type"] == "security_finding"
        assert call_args["name"] == "Test Finding"

    @pytest.mark.asyncio
    async def test_persist_findings_skips_if_no_ib_service(self):
        """Test _persist_findings skips when IB service not available."""
        service = SecurityService(ib_service=None)
        findings = [{"title": "Test"}]

        # Should not raise exception
        await service._persist_findings(findings)

    @pytest.mark.asyncio
    async def test_get_findings_retrieves_from_ib(
        self, security_service, mock_ib_service
    ):
        """Test get_findings retrieves from IB service."""
        mock_ib_service.query_entities.return_value = {
            "entities": [{"id": "1", "name": "Finding 1"}]
        }

        findings = await security_service.get_findings()

        assert len(findings) == 1
        mock_ib_service.query_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_findings_filters_by_severity(
        self, security_service, mock_ib_service
    ):
        """Test get_findings applies severity filter."""
        await security_service.get_findings(severity="critical")

        call_args = mock_ib_service.query_entities.call_args
        assert call_args[1]["filters"]["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_get_findings_returns_empty_if_no_ib_service(self):
        """Test get_findings returns empty list when IB not available."""
        service = SecurityService(ib_service=None)
        findings = await service.get_findings()
        assert findings == []

    @pytest.mark.asyncio
    async def test_get_finding_stats_calculates_statistics(
        self, security_service, mock_ib_service
    ):
        """Test get_finding_stats calculates statistics."""
        mock_ib_service.query_entities.return_value = {
            "entities": [
                {"metadata": {"severity": "high", "finding_type": "sg"}},
                {"metadata": {"severity": "high", "finding_type": "iam"}},
                {"metadata": {"severity": "critical", "finding_type": "sg"}},
            ]
        }

        stats = await security_service.get_finding_stats()

        assert stats["total"] == 3
        assert stats["by_severity"]["high"] == 2
        assert stats["by_severity"]["critical"] == 1
        assert stats["by_type"]["sg"] == 2
        assert stats["by_type"]["iam"] == 1
        assert stats["ib_available"] is True

    @pytest.mark.asyncio
    async def test_get_finding_stats_returns_empty_if_no_ib(self):
        """Test get_finding_stats returns empty stats when IB not available."""
        service = SecurityService(ib_service=None)
        stats = await service.get_finding_stats()

        assert stats["total"] == 0
        assert stats["by_severity"] == {}
        assert stats["by_type"] == {}
        assert stats["ib_available"] is False
