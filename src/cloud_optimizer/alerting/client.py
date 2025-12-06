"""Base alert client and factory.

Provides abstract interface for alerting platforms and factory function
to create appropriate client based on configuration.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from cloud_optimizer.alerting.config import (
    AlertConfig,
    AlertPlatform,
    AlertSeverity,
)


@dataclass
class Alert:
    """Represents an alert to be sent to an alerting platform.

    Attributes:
        title: Short summary of the alert
        description: Detailed description of the issue
        severity: Alert severity level
        source: Source of the alert (e.g., "cloudwatch", "application")
        dedup_key: Deduplication key for grouping related alerts
        timestamp: When the alert occurred
        custom_details: Additional context as key-value pairs
        links: Related links (documentation, runbooks, etc.)
        tags: Tags for categorization
    """

    title: str
    description: str
    severity: AlertSeverity = AlertSeverity.MEDIUM
    source: str = "cloud-optimizer"
    dedup_key: Optional[str] = None
    timestamp: Optional[datetime] = None
    custom_details: dict[str, Any] = None
    links: list[dict[str, str]] = None
    tags: list[str] = None

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.custom_details is None:
            self.custom_details = {}
        if self.links is None:
            self.links = []
        if self.tags is None:
            self.tags = []
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class AlertResponse:
    """Response from alerting platform after creating/updating an alert.

    Attributes:
        success: Whether the operation succeeded
        alert_id: Platform-specific alert/incident ID
        message: Human-readable response message
        dedup_key: Deduplication key used
        status: Current status of the alert
    """

    success: bool
    alert_id: Optional[str] = None
    message: str = ""
    dedup_key: Optional[str] = None
    status: str = "triggered"


class AlertClient(ABC):
    """Abstract base class for alerting platform clients.

    Implementations must provide methods for creating, updating,
    acknowledging, and resolving alerts.
    """

    def __init__(self, config: AlertConfig) -> None:
        """Initialize the client with configuration.

        Args:
            config: Alerting configuration
        """
        self.config = config

    @abstractmethod
    async def create_alert(self, alert: Alert) -> AlertResponse:
        """Create a new alert in the platform.

        Args:
            alert: Alert to create

        Returns:
            Response with alert ID and status
        """
        pass

    @abstractmethod
    async def acknowledge_alert(
        self, alert_id: str, message: Optional[str] = None
    ) -> AlertResponse:
        """Acknowledge an existing alert.

        Args:
            alert_id: Platform-specific alert ID
            message: Optional acknowledgment message

        Returns:
            Response with updated status
        """
        pass

    @abstractmethod
    async def resolve_alert(
        self,
        alert_id: str,
        message: Optional[str] = None,
        dedup_key: Optional[str] = None,
    ) -> AlertResponse:
        """Resolve an existing alert.

        Args:
            alert_id: Platform-specific alert ID (can be empty if using dedup_key)
            message: Optional resolution message
            dedup_key: Deduplication key to resolve by

        Returns:
            Response with updated status
        """
        pass

    @abstractmethod
    async def get_alert(self, alert_id: str) -> Optional[dict[str, Any]]:
        """Get details of an existing alert.

        Args:
            alert_id: Platform-specific alert ID

        Returns:
            Alert details or None if not found
        """
        pass

    @abstractmethod
    async def add_note(self, alert_id: str, note: str) -> AlertResponse:
        """Add a note/comment to an existing alert.

        Args:
            alert_id: Platform-specific alert ID
            note: Note content to add

        Returns:
            Response indicating success
        """
        pass

    async def test_connection(self) -> bool:
        """Test the connection to the alerting platform.

        Returns:
            True if connection is successful
        """
        # Default implementation - subclasses should override
        return True


def get_alert_client(config: AlertConfig) -> AlertClient:
    """Factory function to create appropriate alert client.

    Args:
        config: Alerting configuration specifying platform

    Returns:
        Configured alert client for the specified platform

    Raises:
        ValueError: If platform is not supported
    """
    from cloud_optimizer.alerting.pagerduty import PagerDutyClient
    from cloud_optimizer.alerting.opsgenie import OpsGenieClient

    if config.platform == AlertPlatform.PAGERDUTY:
        return PagerDutyClient(config)
    elif config.platform == AlertPlatform.OPSGENIE:
        return OpsGenieClient(config)
    else:
        raise ValueError(f"Unsupported alerting platform: {config.platform}")
