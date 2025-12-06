"""AWS Marketplace Usage Metering Service."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """A single usage record."""

    dimension: str
    quantity: int
    timestamp: datetime


class UsageMeteringService:
    """Records and reports usage to AWS Marketplace."""

    DIMENSIONS: Dict[str, str] = {
        "scan": "SecurityScans",
        "chat": "ChatQuestions",
        "document": "DocumentAnalysis",
    }

    BUFFER_THRESHOLD: int = 10
    FLUSH_INTERVAL_SECONDS: int = 60

    def __init__(self, product_code: str, enabled: bool = True) -> None:
        """
        Initialize the usage metering service.

        Args:
            product_code: AWS Marketplace product code
            enabled: Whether usage metering is enabled
        """
        self.product_code = product_code
        self.enabled = enabled
        self._client: Optional[boto3.client] = None
        self._buffer: List[UsageRecord] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

    @property
    def client(self) -> boto3.client:
        """Get or create the AWS Marketplace Metering client."""
        if self._client is None:
            self._client = boto3.client("meteringmarketplace")
        return self._client

    async def start(self) -> None:
        """Start the periodic flush task."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._periodic_flush())

    async def stop(self) -> None:
        """Stop the periodic flush and flush remaining records."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush_buffer()

    async def record_usage(self, dimension: str, quantity: int = 1) -> None:
        """
        Record a usage event.

        Args:
            dimension: Usage dimension key (scan, chat, document)
            quantity: Amount of usage to record
        """
        if not self.enabled:
            return

        if dimension not in self.DIMENSIONS:
            logger.warning(f"Unknown dimension: {dimension}")
            return

        async with self._buffer_lock:
            self._buffer.append(
                UsageRecord(
                    dimension=self.DIMENSIONS[dimension],
                    quantity=quantity,
                    timestamp=datetime.now(timezone.utc),
                )
            )

        if len(self._buffer) >= self.BUFFER_THRESHOLD:
            await self._flush_buffer()

    async def _periodic_flush(self) -> None:
        """Periodically flush the buffer."""
        while True:
            await asyncio.sleep(self.FLUSH_INTERVAL_SECONDS)
            await self._flush_buffer()

    async def _flush_buffer(self) -> None:
        """Flush buffered records to AWS Marketplace."""
        async with self._buffer_lock:
            if not self._buffer:
                return
            records = self._buffer.copy()
            self._buffer.clear()

        aggregated = self._aggregate_records(records)
        for dimension, quantity in aggregated.items():
            await self._send_metering_record(dimension, quantity)

    def _aggregate_records(self, records: List[UsageRecord]) -> Dict[str, int]:
        """
        Aggregate records by dimension.

        Args:
            records: List of usage records to aggregate

        Returns:
            Dictionary mapping dimension to total quantity
        """
        aggregated: Dict[str, int] = {}
        for record in records:
            if record.dimension in aggregated:
                aggregated[record.dimension] += record.quantity
            else:
                aggregated[record.dimension] = record.quantity
        return aggregated

    async def _send_metering_record(self, dimension: str, quantity: int) -> bool:
        """
        Send a metering record to AWS Marketplace.

        Args:
            dimension: Usage dimension name
            quantity: Usage quantity

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.meter_usage(
                ProductCode=self.product_code,
                Timestamp=datetime.now(timezone.utc),
                UsageDimension=dimension,
                UsageQuantity=quantity,
            )
            logger.info(f"Metered {quantity} {dimension}")
            return True
        except ClientError as e:
            logger.error(f"Metering failed for {dimension}: {e}")
            # Re-add to buffer for retry
            async with self._buffer_lock:
                self._buffer.append(
                    UsageRecord(dimension, quantity, datetime.now(timezone.utc))
                )
            return False


# Singleton instance
_metering_service: Optional[UsageMeteringService] = None


def get_metering_service() -> UsageMeteringService:
    """Get the singleton metering service instance."""
    global _metering_service
    if _metering_service is None:
        from cloud_optimizer.config import get_settings

        settings = get_settings()
        _metering_service = UsageMeteringService(
            product_code=settings.marketplace_product_code,
            enabled=settings.marketplace_enabled,
        )
    return _metering_service
