"""
Integration tests for AWS Marketplace functionality.

Tests the complete marketplace integration including:
- License validation and entitlement checking
- Usage metering and reporting
- Trial period management
- Subscription lifecycle
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from cloud_optimizer.marketplace.exceptions import (
    LicenseExpiredError,
    LicenseInvalidError,
    MarketplaceError,
)
from cloud_optimizer.marketplace.license import (
    LicenseStatus,
    MarketplaceLicenseValidator,
)
from cloud_optimizer.marketplace.metering import (
    UsageMeteringService,
    UsageRecord,
)
from cloud_optimizer.marketplace.models import (
    LicenseStatusResponse,
    MarketplaceConfig,
)


class TestMarketplaceLicenseValidation:
    """Test suite for license validation functionality."""

    @pytest.fixture
    def product_code(self) -> str:
        """Return test product code."""
        return "test-product-code-123"

    @pytest.fixture
    def mock_marketplace_client(self) -> MagicMock:
        """Create mock boto3 marketplace client."""
        client = MagicMock()
        client.register_usage = MagicMock()
        client.get_entitlements = MagicMock()
        return client

    @pytest.fixture
    def license_validator(
        self, product_code: str, mock_marketplace_client: MagicMock
    ) -> MarketplaceLicenseValidator:
        """Create license validator with mocked client."""
        with patch("boto3.client", return_value=mock_marketplace_client):
            validator = MarketplaceLicenseValidator(product_code=product_code)
            validator._client = mock_marketplace_client
            return validator

    @pytest.mark.asyncio
    async def test_valid_subscription_license(
        self,
        license_validator: MarketplaceLicenseValidator,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test license validation with valid paid subscription."""
        # Arrange
        customer_id = "customer-123456"
        mock_marketplace_client.register_usage.return_value = {
            "CustomerIdentifier": customer_id,
            "PublicKeyRotationTimestamp": datetime.now(timezone.utc),
            "Signature": "mock-signature",
        }

        # Act
        status = await license_validator.validate_on_startup()

        # Assert
        assert status == LicenseStatus.VALID
        mock_marketplace_client.register_usage.assert_called_once()
        call_args = mock_marketplace_client.register_usage.call_args
        assert call_args.kwargs["ProductCode"] == "test-product-code-123"
        assert call_args.kwargs["PublicKeyVersion"] == 1

    @pytest.mark.asyncio
    async def test_trial_period_active(
        self,
        license_validator: MarketplaceLicenseValidator,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test license validation during active trial period."""
        # Arrange - No entitlement (triggers trial check)
        error = ClientError(
            error_response={
                "Error": {
                    "Code": "CustomerNotEntitledException",
                    "Message": "Customer not entitled",
                }
            },
            operation_name="RegisterUsage",
        )
        mock_marketplace_client.register_usage.side_effect = error

        # Mock trial start date (5 days ago)
        trial_start = datetime.now(timezone.utc) - timedelta(days=5)
        with patch.object(
            license_validator, "_get_trial_start_date", return_value=trial_start
        ):
            # Act
            status = await license_validator.validate_on_startup()

            # Assert
            assert status == LicenseStatus.TRIAL

    @pytest.mark.asyncio
    async def test_trial_period_expired(
        self,
        license_validator: MarketplaceLicenseValidator,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test license validation when trial has expired."""
        # Arrange
        error = ClientError(
            error_response={
                "Error": {
                    "Code": "CustomerNotEntitledException",
                    "Message": "Customer not entitled",
                }
            },
            operation_name="RegisterUsage",
        )
        mock_marketplace_client.register_usage.side_effect = error

        # Mock trial start date (20 days ago - expired)
        trial_start = datetime.now(timezone.utc) - timedelta(days=20)
        with patch.object(
            license_validator, "_get_trial_start_date", return_value=trial_start
        ):
            # Act
            status = await license_validator.validate_on_startup()

            # Assert
            assert status == LicenseStatus.TRIAL_EXPIRED

    @pytest.mark.asyncio
    async def test_subscription_expired(
        self,
        license_validator: MarketplaceLicenseValidator,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test license validation when subscription is cancelled/expired."""
        # Arrange
        error = ClientError(
            error_response={
                "Error": {
                    "Code": "CustomerNotSubscribedException",
                    "Message": "Customer not subscribed",
                }
            },
            operation_name="RegisterUsage",
        )
        mock_marketplace_client.register_usage.side_effect = error

        # Act
        status = await license_validator.validate_on_startup()

        # Assert
        assert status == LicenseStatus.SUBSCRIPTION_EXPIRED

    @pytest.mark.asyncio
    async def test_invalid_license(
        self,
        license_validator: MarketplaceLicenseValidator,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test license validation with unexpected error."""
        # Arrange
        error = ClientError(
            error_response={
                "Error": {"Code": "InvalidParameterException", "Message": "Invalid"}
            },
            operation_name="RegisterUsage",
        )
        mock_marketplace_client.register_usage.side_effect = error

        # Act
        status = await license_validator.validate_on_startup()

        # Assert
        assert status == LicenseStatus.INVALID

    @pytest.mark.asyncio
    async def test_entitlement_check_valid(
        self,
        license_validator: MarketplaceLicenseValidator,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test periodic entitlement checking for active subscription."""
        # Arrange
        mock_marketplace_client.get_entitlements.return_value = {
            "Entitlements": [
                {
                    "ProductCode": "test-product-code-123",
                    "Dimension": "Professional",
                    "Value": {"IntegerValue": 1},
                    "ExpirationDate": datetime.now(timezone.utc)
                    + timedelta(days=30),
                }
            ]
        }

        # Act
        has_entitlement = await license_validator.check_entitlement()

        # Assert
        assert has_entitlement is True
        mock_marketplace_client.get_entitlements.assert_called_once()

    @pytest.mark.asyncio
    async def test_entitlement_check_no_entitlement(
        self,
        license_validator: MarketplaceLicenseValidator,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test entitlement check when customer has no active entitlement."""
        # Arrange
        mock_marketplace_client.get_entitlements.return_value = {"Entitlements": []}

        # Act
        has_entitlement = await license_validator.check_entitlement()

        # Assert
        assert has_entitlement is False

    @pytest.mark.asyncio
    async def test_cached_license_status(
        self,
        license_validator: MarketplaceLicenseValidator,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test that license status is cached to avoid excessive API calls."""
        # Arrange
        mock_marketplace_client.register_usage.return_value = {
            "CustomerIdentifier": "customer-123",
            "PublicKeyRotationTimestamp": datetime.now(timezone.utc),
            "Signature": "signature",
        }

        # Act - Validate twice
        status1 = await license_validator.validate_on_startup()
        await asyncio.sleep(0.1)  # Small delay
        status2 = await license_validator.get_cached_status()

        # Assert
        assert status1 == LicenseStatus.VALID
        assert status2 == LicenseStatus.VALID
        # Should only call API once (second call uses cache)
        assert mock_marketplace_client.register_usage.call_count == 1


class TestUsageMetering:
    """Test suite for usage metering functionality."""

    @pytest.fixture
    def product_code(self) -> str:
        """Return test product code."""
        return "test-product-code-123"

    @pytest.fixture
    def mock_marketplace_client(self) -> MagicMock:
        """Create mock boto3 marketplace client."""
        client = MagicMock()
        client.meter_usage = MagicMock(return_value={"MeteringRecordId": "record-123"})
        return client

    @pytest.fixture
    def metering_service(
        self, product_code: str, mock_marketplace_client: MagicMock
    ) -> UsageMeteringService:
        """Create metering service with mocked client."""
        service = UsageMeteringService(product_code=product_code, enabled=True)
        service._client = mock_marketplace_client
        return service

    @pytest.mark.asyncio
    async def test_record_single_scan(
        self,
        metering_service: UsageMeteringService,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test recording a single security scan."""
        # Act
        await metering_service.record_usage(dimension="scan", quantity=1)

        # Assert - Should be buffered, not sent yet
        assert len(metering_service._buffer) == 1
        assert metering_service._buffer[0].dimension == "SecurityScans"
        assert metering_service._buffer[0].quantity == 1
        mock_marketplace_client.meter_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_chat_question(
        self,
        metering_service: UsageMeteringService,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test recording a chat question."""
        # Act
        await metering_service.record_usage(dimension="chat", quantity=1)

        # Assert
        assert len(metering_service._buffer) == 1
        assert metering_service._buffer[0].dimension == "ChatQuestions"

    @pytest.mark.asyncio
    async def test_record_document_analysis(
        self,
        metering_service: UsageMeteringService,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test recording a document analysis."""
        # Act
        await metering_service.record_usage(dimension="document", quantity=1)

        # Assert
        assert len(metering_service._buffer) == 1
        assert metering_service._buffer[0].dimension == "DocumentAnalysis"

    @pytest.mark.asyncio
    async def test_buffer_flush_on_threshold(
        self,
        metering_service: UsageMeteringService,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test that buffer flushes when threshold is reached."""
        # Arrange - Buffer threshold is 10
        assert metering_service.BUFFER_THRESHOLD == 10

        # Act - Record 10 scans to trigger flush
        for i in range(10):
            await metering_service.record_usage(dimension="scan", quantity=1)

        # Wait for flush to complete
        await asyncio.sleep(0.1)

        # Assert
        assert len(metering_service._buffer) == 0  # Buffer cleared
        mock_marketplace_client.meter_usage.assert_called_once()
        call_args = mock_marketplace_client.meter_usage.call_args
        assert call_args.kwargs["ProductCode"] == "test-product-code-123"
        assert call_args.kwargs["UsageDimension"] == "SecurityScans"
        assert call_args.kwargs["UsageQuantity"] == 10

    @pytest.mark.asyncio
    async def test_aggregation_of_same_dimension(
        self,
        metering_service: UsageMeteringService,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test that multiple records of same dimension are aggregated."""
        # Act - Record multiple scans
        for i in range(5):
            await metering_service.record_usage(dimension="scan", quantity=1)

        # Manually flush
        await metering_service._flush_buffer()

        # Assert - Should aggregate to single metering call
        mock_marketplace_client.meter_usage.assert_called_once()
        call_args = mock_marketplace_client.meter_usage.call_args
        assert call_args.kwargs["UsageQuantity"] == 5

    @pytest.mark.asyncio
    async def test_separate_metering_per_dimension(
        self,
        metering_service: UsageMeteringService,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test that different dimensions are metered separately."""
        # Act - Record different dimension types
        await metering_service.record_usage(dimension="scan", quantity=3)
        await metering_service.record_usage(dimension="chat", quantity=5)
        await metering_service.record_usage(dimension="document", quantity=2)

        # Flush
        await metering_service._flush_buffer()

        # Assert - Should make 3 separate metering calls
        assert mock_marketplace_client.meter_usage.call_count == 3

        # Verify each dimension was metered correctly
        calls = mock_marketplace_client.meter_usage.call_args_list
        dimensions_metered = {call.kwargs["UsageDimension"] for call in calls}
        assert dimensions_metered == {
            "SecurityScans",
            "ChatQuestions",
            "DocumentAnalysis",
        }

    @pytest.mark.asyncio
    async def test_metering_retry_on_failure(
        self,
        metering_service: UsageMeteringService,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test that failed metering is retried."""
        # Arrange - First call fails, second succeeds
        mock_marketplace_client.meter_usage.side_effect = [
            ClientError(
                error_response={
                    "Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}
                },
                operation_name="MeterUsage",
            ),
            {"MeteringRecordId": "record-123"},
        ]

        # Act
        await metering_service.record_usage(dimension="scan", quantity=1)
        await metering_service._flush_buffer()  # First attempt - fails

        # Assert - Record should be back in buffer for retry
        assert len(metering_service._buffer) > 0

        # Act - Retry
        await metering_service._flush_buffer()  # Second attempt - succeeds

        # Assert
        assert mock_marketplace_client.meter_usage.call_count == 2
        # Buffer should be empty after successful retry
        assert len(metering_service._buffer) == 0

    @pytest.mark.asyncio
    async def test_metering_disabled(
        self, product_code: str, mock_marketplace_client: MagicMock
    ) -> None:
        """Test that metering is skipped when disabled."""
        # Arrange
        service = UsageMeteringService(product_code=product_code, enabled=False)
        service._client = mock_marketplace_client

        # Act
        await service.record_usage(dimension="scan", quantity=1)
        await service._flush_buffer()

        # Assert - No API calls made
        mock_marketplace_client.meter_usage.assert_not_called()
        assert len(service._buffer) == 0

    @pytest.mark.asyncio
    async def test_periodic_flush(
        self,
        metering_service: UsageMeteringService,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test that buffer flushes periodically."""
        # Arrange - Start periodic flush task
        await metering_service.start()

        # Act - Record usage below threshold
        await metering_service.record_usage(dimension="scan", quantity=1)

        # Wait for periodic flush (FLUSH_INTERVAL_SECONDS = 60)
        # Use shorter timeout for test
        original_interval = metering_service.FLUSH_INTERVAL_SECONDS
        metering_service.FLUSH_INTERVAL_SECONDS = 0.5
        await asyncio.sleep(0.6)

        # Assert - Should have flushed via periodic task
        mock_marketplace_client.meter_usage.assert_called()

        # Cleanup
        await metering_service.stop()
        metering_service.FLUSH_INTERVAL_SECONDS = original_interval

    @pytest.mark.asyncio
    async def test_flush_on_shutdown(
        self,
        metering_service: UsageMeteringService,
        mock_marketplace_client: MagicMock,
    ) -> None:
        """Test that buffer flushes on service shutdown."""
        # Act - Record usage and immediately stop
        await metering_service.record_usage(dimension="scan", quantity=3)
        await metering_service.stop()

        # Assert - Should flush remaining records
        mock_marketplace_client.meter_usage.assert_called_once()
        call_args = mock_marketplace_client.meter_usage.call_args
        assert call_args.kwargs["UsageQuantity"] == 3


class TestMarketplaceIntegration:
    """Integration tests combining license and metering."""

    @pytest.fixture
    def marketplace_config(self) -> MarketplaceConfig:
        """Create marketplace configuration."""
        return MarketplaceConfig(
            enabled=True,
            product_code="test-product-123",
            trial_duration_days=14,
            trial_limits={"scans": 50, "chat_questions": 500, "documents": 20},
        )

    @pytest.mark.asyncio
    async def test_trial_user_workflow(
        self, marketplace_config: MarketplaceConfig
    ) -> None:
        """Test complete workflow for trial user."""
        # This would test:
        # 1. User subscribes (trial)
        # 2. License validates as TRIAL
        # 3. User performs actions (scans, questions)
        # 4. Usage is tracked (but not metered during trial)
        # 5. Trial expires
        # 6. License validates as TRIAL_EXPIRED
        # 7. User is blocked from further actions

        # Note: This is a placeholder for full integration test
        # that would involve actual database and service orchestration
        assert marketplace_config.enabled is True
        assert marketplace_config.trial_duration_days == 14
        assert marketplace_config.trial_limits["scans"] == 50

    @pytest.mark.asyncio
    async def test_paid_user_workflow(
        self, marketplace_config: MarketplaceConfig
    ) -> None:
        """Test complete workflow for paid subscriber."""
        # This would test:
        # 1. User subscribes (paid)
        # 2. License validates as VALID
        # 3. User performs actions
        # 4. Usage is metered to AWS Marketplace
        # 5. User is billed monthly

        # Note: This is a placeholder for full integration test
        assert marketplace_config.enabled is True

    @pytest.mark.asyncio
    async def test_subscription_upgrade(
        self, marketplace_config: MarketplaceConfig
    ) -> None:
        """Test workflow when user upgrades from trial to paid."""
        # This would test:
        # 1. User starts trial
        # 2. Trial usage tracked
        # 3. User upgrades to paid
        # 4. License status changes to VALID
        # 5. Future usage is metered

        # Note: This is a placeholder for full integration test
        assert marketplace_config.enabled is True


class TestMarketplaceMockResponses:
    """Test AWS Marketplace API mock responses for various scenarios."""

    @pytest.mark.asyncio
    async def test_mock_register_usage_success(self) -> None:
        """Test successful RegisterUsage API response."""
        # Arrange
        mock_response = {
            "CustomerIdentifier": "AWSMarketplace:customer-123456789",
            "PublicKeyRotationTimestamp": datetime.now(timezone.utc),
            "Signature": "base64-encoded-signature==",
        }

        # Assert structure
        assert "CustomerIdentifier" in mock_response
        assert mock_response["CustomerIdentifier"].startswith("AWSMarketplace:")
        assert isinstance(mock_response["PublicKeyRotationTimestamp"], datetime)

    @pytest.mark.asyncio
    async def test_mock_meter_usage_success(self) -> None:
        """Test successful MeterUsage API response."""
        # Arrange
        mock_response = {"MeteringRecordId": str(uuid4())}

        # Assert structure
        assert "MeteringRecordId" in mock_response
        assert len(mock_response["MeteringRecordId"]) > 0

    @pytest.mark.asyncio
    async def test_mock_get_entitlements_success(self) -> None:
        """Test successful GetEntitlements API response."""
        # Arrange
        mock_response = {
            "Entitlements": [
                {
                    "ProductCode": "test-product-123",
                    "Dimension": "Professional",
                    "CustomerIdentifier": "customer-123",
                    "Value": {"IntegerValue": 1},
                    "ExpirationDate": datetime.now(timezone.utc) + timedelta(days=30),
                }
            ]
        }

        # Assert structure
        assert "Entitlements" in mock_response
        assert len(mock_response["Entitlements"]) > 0
        entitlement = mock_response["Entitlements"][0]
        assert "ProductCode" in entitlement
        assert "Dimension" in entitlement
        assert "Value" in entitlement


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
