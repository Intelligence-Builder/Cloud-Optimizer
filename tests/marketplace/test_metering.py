"""Tests for UsageMeteringService."""

import pytest
from unittest.mock import patch, MagicMock

from cloud_optimizer.marketplace.metering import (
    UsageMeteringService,
    UsageRecord,
)


@pytest.mark.asyncio
async def test_record_usage(mock_boto3_client):
    """Test recording usage adds to buffer."""
    service = UsageMeteringService("test-product", enabled=True)
    service._client = mock_boto3_client

    await service.record_usage("scan", 1)

    assert len(service._buffer) == 1
    assert service._buffer[0].dimension == "SecurityScans"


@pytest.mark.asyncio
async def test_buffer_flush_at_threshold(mock_boto3_client):
    """Test buffer flushes at threshold."""
    service = UsageMeteringService("test-product", enabled=True)
    service._client = mock_boto3_client

    # Record 10 events (threshold)
    for _ in range(10):
        await service.record_usage("scan", 1)

    # Buffer should be empty after flush
    assert len(service._buffer) == 0
    mock_boto3_client.meter_usage.assert_called()


@pytest.mark.asyncio
async def test_disabled_metering():
    """Test disabled metering doesn't record."""
    service = UsageMeteringService("test-product", enabled=False)

    await service.record_usage("scan", 1)

    assert len(service._buffer) == 0


@pytest.mark.asyncio
async def test_unknown_dimension():
    """Test unknown dimension is ignored."""
    service = UsageMeteringService("test-product", enabled=True)

    await service.record_usage("unknown", 1)

    assert len(service._buffer) == 0


@pytest.mark.asyncio
async def test_aggregation():
    """Test records are aggregated correctly."""
    service = UsageMeteringService("test-product", enabled=True)

    records = [
        UsageRecord("SecurityScans", 1, None),
        UsageRecord("SecurityScans", 2, None),
        UsageRecord("ChatQuestions", 5, None),
    ]

    aggregated = service._aggregate_records(records)

    assert aggregated["SecurityScans"] == 3
    assert aggregated["ChatQuestions"] == 5
