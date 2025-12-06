"""Alert deduplication and grouping module.

Provides mechanisms to prevent alert fatigue through:
- Deduplication of identical alerts within a time window
- Grouping of related alerts
- Rate limiting of alerts
"""

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from cloud_optimizer.alerting.client import Alert
from cloud_optimizer.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DeduplicationKey:
    """Key for alert deduplication.

    Attributes:
        source: Alert source (e.g., "cloudwatch", "application")
        category: Alert category (e.g., "cpu", "memory", "error")
        identifier: Unique identifier within category
        dimensions: Additional dimensions for granularity
    """

    source: str
    category: str
    identifier: str
    dimensions: dict[str, str] = field(default_factory=dict)

    def to_string(self) -> str:
        """Convert to string representation."""
        parts = [self.source, self.category, self.identifier]
        if self.dimensions:
            sorted_dims = sorted(self.dimensions.items())
            dims_str = ",".join(f"{k}={v}" for k, v in sorted_dims)
            parts.append(dims_str)
        return ":".join(parts)

    def to_hash(self) -> str:
        """Generate hash of the key."""
        return hashlib.sha256(self.to_string().encode()).hexdigest()[:32]


@dataclass
class AlertGroup:
    """Group of related alerts.

    Attributes:
        group_key: Unique key for this group
        alerts: List of alerts in this group
        first_seen: When the first alert in group was seen
        last_seen: When the most recent alert was seen
        count: Total number of alerts in group
        suppressed_count: Number of alerts suppressed (not sent)
        severity: Highest severity among grouped alerts
    """

    group_key: str
    alerts: list[Alert] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    count: int = 0
    suppressed_count: int = 0
    severity: str = "info"

    def add_alert(self, alert: Alert) -> None:
        """Add an alert to this group."""
        now = datetime.utcnow()
        if self.first_seen is None:
            self.first_seen = now
        self.last_seen = now
        self.count += 1
        self.alerts.append(alert)

        # Track highest severity
        severity_order = ["info", "low", "medium", "high", "critical"]
        current_idx = severity_order.index(self.severity) if self.severity in severity_order else 0
        alert_idx = severity_order.index(alert.severity.value) if alert.severity.value in severity_order else 0
        if alert_idx > current_idx:
            self.severity = alert.severity.value


class AlertDeduplicator:
    """Manages alert deduplication and grouping.

    Provides mechanisms to:
    - Deduplicate alerts within a configurable time window
    - Group related alerts together
    - Rate limit alerts per source/category
    """

    def __init__(
        self,
        window_minutes: int = 60,
        max_alerts_per_window: int = 10,
        grouping_enabled: bool = True,
    ) -> None:
        """Initialize the deduplicator.

        Args:
            window_minutes: Time window for deduplication (default 60 min)
            max_alerts_per_window: Max alerts per key before suppression
            grouping_enabled: Whether to group related alerts
        """
        self.window_minutes = window_minutes
        self.max_alerts_per_window = max_alerts_per_window
        self.grouping_enabled = grouping_enabled

        # In-memory storage (would use Redis in production)
        self._seen_alerts: dict[str, datetime] = {}
        self._alert_counts: dict[str, int] = defaultdict(int)
        self._alert_groups: dict[str, AlertGroup] = {}
        self._last_cleanup = datetime.utcnow()

    def _cleanup_expired(self) -> None:
        """Remove expired entries from tracking."""
        now = datetime.utcnow()

        # Only cleanup every 5 minutes
        if (now - self._last_cleanup).total_seconds() < 300:
            return

        cutoff = now - timedelta(minutes=self.window_minutes)

        # Clean seen alerts
        expired_keys = [
            key for key, timestamp in self._seen_alerts.items()
            if timestamp < cutoff
        ]
        for key in expired_keys:
            del self._seen_alerts[key]
            self._alert_counts.pop(key, None)

        # Clean groups
        expired_groups = [
            key for key, group in self._alert_groups.items()
            if group.last_seen and group.last_seen < cutoff
        ]
        for key in expired_groups:
            del self._alert_groups[key]

        self._last_cleanup = now

        if expired_keys or expired_groups:
            logger.debug(
                "deduplication_cleanup",
                expired_alerts=len(expired_keys),
                expired_groups=len(expired_groups),
            )

    def generate_key(self, alert: Alert) -> DeduplicationKey:
        """Generate deduplication key for an alert.

        Args:
            alert: Alert to generate key for

        Returns:
            DeduplicationKey for the alert
        """
        # Extract category from alert tags or custom_details
        category = "general"
        if "namespace" in alert.custom_details:
            category = alert.custom_details["namespace"]
        elif alert.tags:
            for tag in alert.tags:
                if tag.startswith("namespace:"):
                    category = tag.split(":")[1]
                    break

        # Extract dimensions
        dimensions = alert.custom_details.get("dimensions", {})
        if isinstance(dimensions, dict):
            dims = {k: v for k, v in dimensions.items() if v}
        else:
            dims = {}

        return DeduplicationKey(
            source=alert.source,
            category=category,
            identifier=alert.title,
            dimensions=dims,
        )

    def should_send(self, alert: Alert) -> tuple[bool, str]:
        """Check if an alert should be sent or suppressed.

        Args:
            alert: Alert to check

        Returns:
            Tuple of (should_send, reason)
        """
        self._cleanup_expired()

        key = self.generate_key(alert)
        key_hash = key.to_hash()
        now = datetime.utcnow()

        # Check if we've seen this exact alert recently
        if key_hash in self._seen_alerts:
            last_seen = self._seen_alerts[key_hash]
            elapsed = (now - last_seen).total_seconds()
            if elapsed < (self.window_minutes * 60):
                # Check if we've hit the rate limit
                count = self._alert_counts[key_hash]
                if count >= self.max_alerts_per_window:
                    # Update group suppression count
                    if self.grouping_enabled and key_hash in self._alert_groups:
                        self._alert_groups[key_hash].suppressed_count += 1
                    return False, f"Rate limited ({count} alerts in window)"

        # Update tracking
        self._seen_alerts[key_hash] = now
        self._alert_counts[key_hash] += 1

        # Add to group if grouping enabled
        if self.grouping_enabled:
            if key_hash not in self._alert_groups:
                self._alert_groups[key_hash] = AlertGroup(group_key=key_hash)
            self._alert_groups[key_hash].add_alert(alert)

        return True, "OK"

    def get_group(self, alert: Alert) -> Optional[AlertGroup]:
        """Get the alert group for an alert.

        Args:
            alert: Alert to get group for

        Returns:
            AlertGroup if grouping enabled and group exists
        """
        if not self.grouping_enabled:
            return None

        key = self.generate_key(alert)
        return self._alert_groups.get(key.to_hash())

    def get_stats(self) -> dict[str, Any]:
        """Get deduplication statistics.

        Returns:
            Dictionary with stats about deduplication
        """
        self._cleanup_expired()

        total_groups = len(self._alert_groups)
        total_suppressed = sum(g.suppressed_count for g in self._alert_groups.values())
        total_alerts = sum(g.count for g in self._alert_groups.values())

        return {
            "active_keys": len(self._seen_alerts),
            "active_groups": total_groups,
            "total_alerts_processed": total_alerts,
            "total_suppressed": total_suppressed,
            "suppression_rate": (
                total_suppressed / total_alerts if total_alerts > 0 else 0
            ),
            "window_minutes": self.window_minutes,
            "max_per_window": self.max_alerts_per_window,
        }

    def reset(self) -> None:
        """Reset all tracking state."""
        self._seen_alerts.clear()
        self._alert_counts.clear()
        self._alert_groups.clear()
        self._last_cleanup = datetime.utcnow()
        logger.info("deduplication_state_reset")
