"""Alerting integration module for PagerDuty and OpsGenie.

Provides unified alerting capabilities including:
- PagerDuty and OpsGenie client integrations
- CloudWatch Alarm SNS message handling
- Alert deduplication and grouping
- Escalation policy configuration
- Incident management
"""

from cloud_optimizer.alerting.config import (
    AlertConfig,
    AlertPlatform,
    AlertSeverity,
    EscalationPolicy,
    EscalationLevel,
    OnCallSchedule,
)
from cloud_optimizer.alerting.client import (
    AlertClient,
    get_alert_client,
)
from cloud_optimizer.alerting.pagerduty import PagerDutyClient
from cloud_optimizer.alerting.opsgenie import OpsGenieClient
from cloud_optimizer.alerting.sns_handler import (
    SNSAlertHandler,
    parse_cloudwatch_alarm,
    CloudWatchAlarmMessage,
)
from cloud_optimizer.alerting.deduplication import (
    AlertDeduplicator,
    DeduplicationKey,
    AlertGroup,
)

__all__ = [
    # Configuration
    "AlertConfig",
    "AlertPlatform",
    "AlertSeverity",
    "EscalationPolicy",
    "EscalationLevel",
    "OnCallSchedule",
    # Clients
    "AlertClient",
    "get_alert_client",
    "PagerDutyClient",
    "OpsGenieClient",
    # SNS Handler
    "SNSAlertHandler",
    "parse_cloudwatch_alarm",
    "CloudWatchAlarmMessage",
    # Deduplication
    "AlertDeduplicator",
    "DeduplicationKey",
    "AlertGroup",
]
