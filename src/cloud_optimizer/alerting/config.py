"""Alerting configuration module.

Defines configuration dataclasses for alerting platforms, severity levels,
escalation policies, and on-call schedules.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AlertPlatform(str, Enum):
    """Supported alerting platforms."""

    PAGERDUTY = "pagerduty"
    OPSGENIE = "opsgenie"


class AlertSeverity(str, Enum):
    """Alert severity levels mapped to platform-specific values.

    Mapping to PagerDuty:
        CRITICAL -> critical
        HIGH -> error
        MEDIUM -> warning
        LOW -> info

    Mapping to OpsGenie:
        CRITICAL -> P1
        HIGH -> P2
        MEDIUM -> P3
        LOW -> P4/P5
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    def to_pagerduty_severity(self) -> str:
        """Convert to PagerDuty severity string."""
        mapping = {
            AlertSeverity.CRITICAL: "critical",
            AlertSeverity.HIGH: "error",
            AlertSeverity.MEDIUM: "warning",
            AlertSeverity.LOW: "info",
            AlertSeverity.INFO: "info",
        }
        return mapping[self]

    def to_opsgenie_priority(self) -> str:
        """Convert to OpsGenie priority string."""
        mapping = {
            AlertSeverity.CRITICAL: "P1",
            AlertSeverity.HIGH: "P2",
            AlertSeverity.MEDIUM: "P3",
            AlertSeverity.LOW: "P4",
            AlertSeverity.INFO: "P5",
        }
        return mapping[self]


@dataclass
class EscalationLevel:
    """Single level in an escalation policy.

    Attributes:
        level: The escalation level number (1-based)
        targets: List of target IDs (user IDs, schedule IDs, or team IDs)
        delay_minutes: Minutes to wait before escalating to next level
        notify_type: How to notify ("user", "schedule", "team")
    """

    level: int
    targets: list[str]
    delay_minutes: int = 30
    notify_type: str = "user"


@dataclass
class EscalationPolicy:
    """Escalation policy configuration.

    Attributes:
        name: Policy name for identification
        description: Human-readable description
        levels: Ordered list of escalation levels
        repeat_enabled: Whether to repeat the escalation after all levels
        repeat_count: Number of times to repeat (0 for infinite until ack)
    """

    name: str
    description: str = ""
    levels: list[EscalationLevel] = field(default_factory=list)
    repeat_enabled: bool = True
    repeat_count: int = 3


@dataclass
class OnCallSchedule:
    """On-call schedule configuration.

    Attributes:
        name: Schedule name
        description: Human-readable description
        timezone: Timezone for the schedule (e.g., "America/New_York")
        rotation_type: Type of rotation ("daily", "weekly", "custom")
        handoff_time: Time of day for handoffs (24h format, e.g., "09:00")
        users: List of user IDs in rotation order
    """

    name: str
    description: str = ""
    timezone: str = "UTC"
    rotation_type: str = "weekly"
    handoff_time: str = "09:00"
    users: list[str] = field(default_factory=list)


@dataclass
class AlertConfig:
    """Main alerting configuration.

    Attributes:
        platform: Which alerting platform to use
        api_key: API key for the platform
        api_url: Base URL for API calls (optional, uses default if not set)
        service_id: Service/integration ID in the platform
        routing_key: Routing key for PagerDuty Events API
        default_severity: Default severity for alerts without explicit severity
        environment: Environment name for alert context
        deduplication_enabled: Whether to deduplicate alerts
        deduplication_window_minutes: Time window for deduplication
        auto_resolve_enabled: Whether to auto-resolve alerts when alarm clears
        slack_webhook_url: Optional Slack webhook for notifications
        escalation_policy: Default escalation policy
    """

    platform: AlertPlatform = AlertPlatform.PAGERDUTY
    api_key: str = ""
    api_url: Optional[str] = None
    service_id: str = ""
    routing_key: str = ""
    default_severity: AlertSeverity = AlertSeverity.MEDIUM
    environment: str = "production"
    deduplication_enabled: bool = True
    deduplication_window_minutes: int = 60
    auto_resolve_enabled: bool = True
    slack_webhook_url: Optional[str] = None
    escalation_policy: Optional[EscalationPolicy] = None

    @property
    def base_url(self) -> str:
        """Get the base API URL for the platform."""
        if self.api_url:
            return self.api_url
        if self.platform == AlertPlatform.PAGERDUTY:
            return "https://api.pagerduty.com"
        return "https://api.opsgenie.com"

    def validate(self) -> list[str]:
        """Validate the configuration and return list of errors."""
        errors = []
        if not self.api_key:
            errors.append("API key is required")
        if self.platform == AlertPlatform.PAGERDUTY:
            if not self.routing_key:
                errors.append("Routing key is required for PagerDuty")
        if self.platform == AlertPlatform.OPSGENIE:
            if not self.service_id:
                errors.append("Service ID is required for OpsGenie")
        return errors
