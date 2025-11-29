"""
Unit tests for SecurityService.

Testing Strategy:
- Unit tests: Test pure logic without external dependencies
- Tests requiring IB service use stub implementations (not mocks)
- AWS interaction tests are in integration tests using LocalStack

Note: SecurityService depends on IntelligenceBuilderService which is an
external SDK. For unit tests, we use a simple stub that implements the
interface. Integration tests (test_epic3_app.py) test with LocalStack.
"""

import pytest
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from cloud_optimizer.services.security import SecurityService


# ============================================================================
# Stub Implementation for IB Service (NOT a mock - implements interface)
# ============================================================================


@dataclass
class StubIBService:
    """
    Stub implementation of IB service interface for unit testing.

    This is NOT a mock - it's a simple implementation that follows
    the same interface as the real IB service.
    """

    is_connected: bool = True
    _entities: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self._entities is None:
            self._entities = []

    async def create_entity(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store entity in memory."""
        self._entities.append(entity_data)
        return entity_data

    async def query_entities(
        self,
        entity_type: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Return stored entities."""
        return {"entities": self._entities}


# ============================================================================
# Unit Tests - Pure Logic (No External Dependencies)
# ============================================================================


class TestSecurityServiceInitialization:
    """Tests for SecurityService initialization and configuration."""

    def test_service_initializes_without_ib(self):
        """Service can be created without IB service."""
        service = SecurityService(ib_service=None)
        assert service.ib_service is None

    def test_service_initializes_with_ib(self):
        """Service accepts IB service dependency."""
        stub_ib = StubIBService()
        service = SecurityService(ib_service=stub_ib)
        assert service.ib_service is stub_ib


class TestScannerFactory:
    """Tests for scanner creation and caching."""

    def test_creates_security_group_scanner(self):
        """Factory creates SecurityGroupScanner for 'security_groups' type."""
        service = SecurityService()
        scanner = service._get_scanner("security_groups", "us-east-1")

        assert scanner is not None
        assert scanner.get_scanner_name() == "SecurityGroupScanner"
        assert scanner.region == "us-east-1"

    def test_creates_iam_scanner(self):
        """Factory creates IAMScanner for 'iam' type."""
        service = SecurityService()
        scanner = service._get_scanner("iam", "us-east-1")

        assert scanner is not None
        assert scanner.get_scanner_name() == "IAMScanner"

    def test_creates_encryption_scanner(self):
        """Factory creates EncryptionScanner for 'encryption' type."""
        service = SecurityService()
        scanner = service._get_scanner("encryption", "us-east-1")

        assert scanner is not None
        assert scanner.get_scanner_name() == "EncryptionScanner"

    def test_raises_for_unknown_scan_type(self):
        """Factory raises ValueError for unknown scan types."""
        service = SecurityService()

        with pytest.raises(ValueError, match="Unknown scan type"):
            service._get_scanner("unknown_type", "us-east-1")

    def test_caches_scanner_instances(self):
        """Scanner instances are cached by type and region."""
        service = SecurityService()

        scanner1 = service._get_scanner("security_groups", "us-east-1")
        scanner2 = service._get_scanner("security_groups", "us-east-1")

        assert scanner1 is scanner2

    def test_different_regions_have_different_scanners(self):
        """Different regions get different scanner instances."""
        service = SecurityService()

        scanner_east = service._get_scanner("security_groups", "us-east-1")
        scanner_west = service._get_scanner("security_groups", "us-west-2")

        assert scanner_east is not scanner_west
        assert scanner_east.region == "us-east-1"
        assert scanner_west.region == "us-west-2"


class TestFindingsWithoutIB:
    """Tests for finding operations when IB service not available."""

    @pytest.mark.asyncio
    async def test_get_findings_returns_empty_without_ib(self):
        """get_findings returns empty list when IB not connected."""
        service = SecurityService(ib_service=None)

        findings = await service.get_findings()

        assert findings == []

    @pytest.mark.asyncio
    async def test_get_finding_stats_returns_empty_without_ib(self):
        """get_finding_stats returns empty stats when IB not connected."""
        service = SecurityService(ib_service=None)

        stats = await service.get_finding_stats()

        assert stats["total"] == 0
        assert stats["by_severity"] == {}
        assert stats["by_type"] == {}
        assert stats["ib_available"] is False

    @pytest.mark.asyncio
    async def test_persist_findings_skips_without_ib(self):
        """_persist_findings does nothing when IB not available."""
        service = SecurityService(ib_service=None)
        findings = [{"title": "Test Finding"}]

        # Should not raise exception
        await service._persist_findings(findings)


# ============================================================================
# Tests with Stub IB Service (Interface Testing)
# ============================================================================


class TestFindingsWithStubIB:
    """Tests for finding operations using stub IB service."""

    @pytest.fixture
    def service_with_stub_ib(self):
        """Create service with stub IB implementation."""
        stub_ib = StubIBService(is_connected=True)
        return SecurityService(ib_service=stub_ib)

    @pytest.mark.asyncio
    async def test_persist_findings_stores_entities(self, service_with_stub_ib):
        """_persist_findings creates entities through IB service."""
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

        await service_with_stub_ib._persist_findings(findings)

        # Verify entity was stored
        stored = service_with_stub_ib.ib_service._entities
        assert len(stored) == 1
        assert stored[0]["entity_type"] == "security_finding"
        assert stored[0]["name"] == "Test Finding"

    @pytest.mark.asyncio
    async def test_get_findings_retrieves_entities(self, service_with_stub_ib):
        """get_findings retrieves entities from IB service."""
        # Pre-populate stub
        service_with_stub_ib.ib_service._entities = [
            {"id": "1", "name": "Finding 1"},
            {"id": "2", "name": "Finding 2"},
        ]

        findings = await service_with_stub_ib.get_findings()

        assert len(findings) == 2

    @pytest.mark.asyncio
    async def test_get_finding_stats_calculates_statistics(self, service_with_stub_ib):
        """get_finding_stats calculates correct statistics."""
        # Pre-populate stub with findings
        service_with_stub_ib.ib_service._entities = [
            {"metadata": {"severity": "high", "finding_type": "sg"}},
            {"metadata": {"severity": "high", "finding_type": "iam"}},
            {"metadata": {"severity": "critical", "finding_type": "sg"}},
        ]

        stats = await service_with_stub_ib.get_finding_stats()

        assert stats["total"] == 3
        assert stats["by_severity"]["high"] == 2
        assert stats["by_severity"]["critical"] == 1
        assert stats["by_type"]["sg"] == 2
        assert stats["by_type"]["iam"] == 1
        assert stats["ib_available"] is True

    @pytest.mark.asyncio
    async def test_finding_stats_handles_missing_metadata(self, service_with_stub_ib):
        """get_finding_stats handles entities without metadata."""
        service_with_stub_ib.ib_service._entities = [
            {"id": "1"},  # No metadata
            {"metadata": {}},  # Empty metadata
            {"metadata": {"severity": "high"}},  # Partial metadata
        ]

        stats = await service_with_stub_ib.get_finding_stats()

        assert stats["total"] == 3
        # Missing fields default to "unknown"
        assert stats["by_severity"]["unknown"] == 2
        assert stats["by_severity"]["high"] == 1


# ============================================================================
# Scan Account Tests (Orchestration Logic)
# ============================================================================


class TestScanAccountOrchestration:
    """Tests for scan_account orchestration logic.

    Note: These tests verify the orchestration logic.
    Actual AWS scanning is tested in integration tests with LocalStack.
    """

    @pytest.mark.asyncio
    async def test_scan_account_defaults_to_all_scan_types(self):
        """scan_account runs all scan types when none specified."""
        service = SecurityService()

        # Track which scan types were requested
        scanned_types = []
        original_run_scan = service._run_scan

        async def tracking_run_scan(scan_type, account_id, region):
            scanned_types.append(scan_type)
            return []

        service._run_scan = tracking_run_scan

        await service.scan_account("123456789012")

        assert "security_groups" in scanned_types
        assert "iam" in scanned_types
        assert "encryption" in scanned_types

    @pytest.mark.asyncio
    async def test_scan_account_respects_specified_types(self):
        """scan_account only runs specified scan types."""
        service = SecurityService()

        scanned_types = []

        async def tracking_run_scan(scan_type, account_id, region):
            scanned_types.append(scan_type)
            return []

        service._run_scan = tracking_run_scan

        await service.scan_account(
            "123456789012",
            scan_types=["iam"],
        )

        assert scanned_types == ["iam"]

    @pytest.mark.asyncio
    async def test_scan_account_returns_finding_counts(self):
        """scan_account returns correct finding counts per type."""
        service = SecurityService()

        async def fake_run_scan(scan_type, account_id, region):
            if scan_type == "security_groups":
                return [{"f": 1}, {"f": 2}, {"f": 3}]
            elif scan_type == "iam":
                return [{"f": 1}]
            return []

        service._run_scan = fake_run_scan

        results = await service.scan_account(
            "123456789012",
            scan_types=["security_groups", "iam"],
        )

        assert results["security_groups"] == 3
        assert results["iam"] == 1

    @pytest.mark.asyncio
    async def test_scan_account_uses_specified_region(self):
        """scan_account passes region to scanners."""
        service = SecurityService()

        used_regions = []

        async def tracking_run_scan(scan_type, account_id, region):
            used_regions.append(region)
            return []

        service._run_scan = tracking_run_scan

        await service.scan_account(
            "123456789012",
            scan_types=["iam"],
            region="eu-west-1",
        )

        assert used_regions == ["eu-west-1"]
