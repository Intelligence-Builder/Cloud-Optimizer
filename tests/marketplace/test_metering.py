"""
Tests for UsageMeteringService.

TESTING STRATEGY:
Since AWS Marketplace Metering API is NOT supported by LocalStack, we use:
1. Unit tests for internal logic (buffering, aggregation)
2. Integration tests with mocked AWS client for API calls
3. Real tests marked with @pytest.mark.real_aws
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cloud_optimizer.marketplace.metering import UsageMeteringService, UsageRecord


# ============================================================================
# Unit Tests - Internal Logic (No AWS Dependencies)
# ============================================================================


@pytest.mark.unit
def test_service_initialization() -> None:
    """Test service can be initialized."""
    service = UsageMeteringService("test-product", enabled=True)

    assert service.product_code == "test-product"
    assert service.enabled is True
    assert len(service._buffer) == 0
    assert service._client is None


@pytest.mark.unit
def test_service_disabled() -> None:
    """Test disabled service doesn't create client."""
    service = UsageMeteringService("test-product", enabled=False)

    assert service.enabled is False
    assert service._client is None


@pytest.mark.unit
def test_dimension_mapping() -> None:
    """Test dimension keys map to AWS dimension names."""
    assert UsageMeteringService.DIMENSIONS["scan"] == "SecurityScans"
    assert UsageMeteringService.DIMENSIONS["chat"] == "ChatQuestions"
    assert UsageMeteringService.DIMENSIONS["document"] == "DocumentAnalysis"


@pytest.mark.unit
def test_aggregation_single_dimension() -> None:
    """Test record aggregation with single dimension."""
    service = UsageMeteringService("test-product", enabled=True)

    records = [
        UsageRecord("SecurityScans", 1, datetime.now(timezone.utc)),
        UsageRecord("SecurityScans", 2, datetime.now(timezone.utc)),
        UsageRecord("SecurityScans", 3, datetime.now(timezone.utc)),
    ]

    aggregated = service._aggregate_records(records)

    assert len(aggregated) == 1
    assert aggregated["SecurityScans"] == 6


@pytest.mark.unit
def test_aggregation_multiple_dimensions() -> None:
    """Test record aggregation with multiple dimensions."""
    service = UsageMeteringService("test-product", enabled=True)

    records = [
        UsageRecord("SecurityScans", 1, datetime.now(timezone.utc)),
        UsageRecord("SecurityScans", 2, datetime.now(timezone.utc)),
        UsageRecord("ChatQuestions", 5, datetime.now(timezone.utc)),
        UsageRecord("DocumentAnalysis", 3, datetime.now(timezone.utc)),
        UsageRecord("ChatQuestions", 10, datetime.now(timezone.utc)),
    ]

    aggregated = service._aggregate_records(records)

    assert len(aggregated) == 3
    assert aggregated["SecurityScans"] == 3
    assert aggregated["ChatQuestions"] == 15
    assert aggregated["DocumentAnalysis"] == 3


@pytest.mark.unit
def test_aggregation_empty_records() -> None:
    """Test record aggregation with empty list."""
    service = UsageMeteringService("test-product", enabled=True)

    aggregated = service._aggregate_records([])

    assert len(aggregated) == 0


# ============================================================================
# Integration Tests - With Mocked AWS Client
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_usage_adds_to_buffer() -> None:
    """Test recording usage adds to buffer."""
    service = UsageMeteringService("test-product", enabled=True)

    await service.record_usage("scan", 1)

    assert len(service._buffer) == 1
    assert service._buffer[0].dimension == "SecurityScans"
    assert service._buffer[0].quantity == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_multiple_usage() -> None:
    """Test recording multiple usage events."""
    service = UsageMeteringService("test-product", enabled=True)

    await service.record_usage("scan", 1)
    await service.record_usage("chat", 5)
    await service.record_usage("document", 2)

    assert len(service._buffer) == 3
    assert service._buffer[0].dimension == "SecurityScans"
    assert service._buffer[1].dimension == "ChatQuestions"
    assert service._buffer[2].dimension == "DocumentAnalysis"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_disabled_metering_no_buffer() -> None:
    """Test disabled metering doesn't record."""
    service = UsageMeteringService("test-product", enabled=False)

    await service.record_usage("scan", 1)

    assert len(service._buffer) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unknown_dimension_ignored() -> None:
    """Test unknown dimension is ignored."""
    service = UsageMeteringService("test-product", enabled=True)

    await service.record_usage("unknown_dimension", 1)

    assert len(service._buffer) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_buffer_flush_at_threshold() -> None:
    """Test buffer flushes when reaching threshold."""
    service = UsageMeteringService("test-product", enabled=True)

    # Mock the client
    mock_client = MagicMock()
    mock_client.meter_usage.return_value = {}
    service._client = mock_client

    # Record exactly threshold number of events
    threshold = UsageMeteringService.BUFFER_THRESHOLD
    for i in range(threshold):
        await service.record_usage("scan", 1)

    # Buffer should be empty after automatic flush
    assert len(service._buffer) == 0

    # Client should have been called
    assert mock_client.meter_usage.called


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_flush() -> None:
    """Test manual buffer flush."""
    service = UsageMeteringService("test-product", enabled=True)

    # Mock the client
    mock_client = MagicMock()
    mock_client.meter_usage.return_value = {}
    service._client = mock_client

    # Add records below threshold
    await service.record_usage("scan", 1)
    await service.record_usage("chat", 2)

    assert len(service._buffer) == 2

    # Manual flush
    await service._flush_buffer()

    assert len(service._buffer) == 0
    assert mock_client.meter_usage.call_count == 2  # One call per dimension


@pytest.mark.integration
@pytest.mark.asyncio
async def test_flush_aggregates_same_dimension() -> None:
    """Test flush aggregates records with same dimension."""
    service = UsageMeteringService("test-product", enabled=True)

    # Mock the client
    mock_client = MagicMock()
    mock_client.meter_usage.return_value = {}
    service._client = mock_client

    # Add multiple records of same dimension
    await service.record_usage("scan", 1)
    await service.record_usage("scan", 2)
    await service.record_usage("scan", 3)

    await service._flush_buffer()

    # Should be called once with aggregated quantity
    assert mock_client.meter_usage.call_count == 1
    call_args = mock_client.meter_usage.call_args
    assert call_args[1]["UsageQuantity"] == 6
    assert call_args[1]["UsageDimension"] == "SecurityScans"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_send_metering_record_success() -> None:
    """Test successful metering record send."""
    service = UsageMeteringService("test-product", enabled=True)

    # Mock successful response
    mock_client = MagicMock()
    mock_client.meter_usage.return_value = {"MeteringRecordId": "test-123"}
    service._client = mock_client

    result = await service._send_metering_record("SecurityScans", 5)

    assert result is True
    mock_client.meter_usage.assert_called_once()
    call_kwargs = mock_client.meter_usage.call_args[1]
    assert call_kwargs["ProductCode"] == "test-product"
    assert call_kwargs["UsageDimension"] == "SecurityScans"
    assert call_kwargs["UsageQuantity"] == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_send_metering_record_failure_requeues() -> None:
    """Test failed metering record is requeued."""
    from botocore.exceptions import ClientError

    service = UsageMeteringService("test-product", enabled=True)

    # Mock client error
    mock_client = MagicMock()
    error_response = {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}}
    mock_client.meter_usage.side_effect = ClientError(error_response, "MeterUsage")
    service._client = mock_client

    initial_buffer_length = len(service._buffer)
    result = await service._send_metering_record("SecurityScans", 5)

    assert result is False
    # Record should be re-added to buffer
    assert len(service._buffer) == initial_buffer_length + 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_flush_empty_buffer_no_api_call() -> None:
    """Test flushing empty buffer doesn't call API."""
    service = UsageMeteringService("test-product", enabled=True)

    # Mock the client
    mock_client = MagicMock()
    service._client = mock_client

    await service._flush_buffer()

    # Should not call meter_usage
    mock_client.meter_usage.assert_not_called()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_client_lazy_initialization() -> None:
    """Test boto3 client is created lazily."""
    service = UsageMeteringService("test-product", enabled=True)

    # Client should not exist yet
    assert service._client is None

    # Accessing client property creates it
    with patch("cloud_optimizer.marketplace.metering.boto3.client") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client

        client = service.client

        assert client is mock_client
        mock_boto3.assert_called_once_with("meteringmarketplace")


# ============================================================================
# Integration Tests - Lifecycle Management
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_creates_flush_task() -> None:
    """Test start() creates periodic flush task."""
    service = UsageMeteringService("test-product", enabled=True)

    assert service._flush_task is None

    await service.start()

    assert service._flush_task is not None
    assert not service._flush_task.done()

    # Cleanup
    await service.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stop_flushes_remaining_records() -> None:
    """Test stop() flushes remaining buffered records."""
    service = UsageMeteringService("test-product", enabled=True)

    # Mock the client
    mock_client = MagicMock()
    mock_client.meter_usage.return_value = {}
    service._client = mock_client

    # Start service and add records
    await service.start()
    await service.record_usage("scan", 1)
    await service.record_usage("chat", 2)

    assert len(service._buffer) == 2

    # Stop should flush
    await service.stop()

    assert len(service._buffer) == 0
    assert mock_client.meter_usage.called


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


@pytest.mark.unit
def test_get_metering_service_singleton() -> None:
    """Test get_metering_service returns singleton instance."""
    with patch("cloud_optimizer.config.get_settings") as mock_settings:
        mock_settings.return_value.marketplace_product_code = "test-product"
        mock_settings.return_value.marketplace_enabled = True

        # Reset singleton
        import cloud_optimizer.marketplace.metering as metering_module

        metering_module._metering_service = None

        from cloud_optimizer.marketplace.metering import get_metering_service

        service1 = get_metering_service()
        service2 = get_metering_service()

        assert service1 is service2
        assert service1.product_code == "test-product"

        # Cleanup
        metering_module._metering_service = None


# ============================================================================
# LocalStack Integration Tests (Skip if marketplace not available)
# ============================================================================


@pytest.mark.localstack_only
@pytest.mark.skip(
    reason="AWS Marketplace Metering API not supported by LocalStack. "
    "Use real AWS with test accounts or implement custom mock server."
)
def test_localstack_metering_placeholder() -> None:
    """
    Placeholder for LocalStack metering tests.

    When LocalStack adds marketplace support or a custom mock server is implemented:
    1. Remove skip decorator
    2. Use fixtures from localstack_conftest.py
    3. Test against mock metering endpoints
    4. Validate aggregation and retry logic with real HTTP
    """
    pass


# ============================================================================
# Real AWS Integration Tests (Requires AWS Credentials)
# ============================================================================


@pytest.mark.real_aws
@pytest.mark.skip(
    reason="Real AWS tests require valid credentials and test marketplace product. "
    "Enable manually for integration testing."
)
@pytest.mark.asyncio
async def test_real_aws_metering() -> None:
    """
    Real AWS metering test.

    Prerequisites:
    1. AWS credentials configured
    2. Test marketplace product code in environment (TEST_MARKETPLACE_PRODUCT_CODE)
    3. Running in AWS environment with metering permissions

    To run:
        pytest -m real_aws tests/marketplace/test_metering.py::test_real_aws_metering
    """
    import os

    product_code = os.getenv("TEST_MARKETPLACE_PRODUCT_CODE")
    if not product_code:
        pytest.skip("TEST_MARKETPLACE_PRODUCT_CODE not set")

    service = UsageMeteringService(product_code, enabled=True)

    await service.record_usage("scan", 1)
    await service._flush_buffer()

    # If no exception, test passes
    assert True
