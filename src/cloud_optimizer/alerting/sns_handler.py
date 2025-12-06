"""SNS message handler for CloudWatch Alarms.

Processes SNS notifications from CloudWatch Alarms and converts them
to platform-specific alerts for PagerDuty or OpsGenie.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from cloud_optimizer.alerting.client import Alert, AlertClient, AlertResponse
from cloud_optimizer.alerting.config import AlertSeverity
from cloud_optimizer.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CloudWatchAlarmMessage:
    """Parsed CloudWatch Alarm SNS message.

    Attributes:
        alarm_name: Name of the CloudWatch alarm
        alarm_description: Description of the alarm
        aws_account_id: AWS account ID where alarm triggered
        region: AWS region
        new_state: Current state (ALARM, OK, INSUFFICIENT_DATA)
        old_state: Previous state
        new_state_reason: Reason for state change
        state_change_time: When the state changed
        metric_name: Name of the metric
        namespace: CloudWatch namespace
        dimensions: Metric dimensions
        threshold: Alarm threshold value
        comparison_operator: Comparison operator used
        evaluation_periods: Number of evaluation periods
        period: Period in seconds
        statistic: Statistic used (Average, Sum, etc.)
        treat_missing_data: How missing data is treated
    """

    alarm_name: str
    alarm_description: str = ""
    aws_account_id: str = ""
    region: str = ""
    new_state: str = ""
    old_state: str = ""
    new_state_reason: str = ""
    state_change_time: Optional[datetime] = None
    metric_name: str = ""
    namespace: str = ""
    dimensions: dict[str, str] = None
    threshold: Optional[float] = None
    comparison_operator: str = ""
    evaluation_periods: int = 1
    period: int = 60
    statistic: str = ""
    treat_missing_data: str = ""

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.dimensions is None:
            self.dimensions = {}


def parse_cloudwatch_alarm(message_body: str | dict) -> CloudWatchAlarmMessage:
    """Parse a CloudWatch Alarm SNS message.

    Args:
        message_body: Raw SNS message body (JSON string or dict)

    Returns:
        Parsed CloudWatchAlarmMessage

    Raises:
        ValueError: If message cannot be parsed
    """
    if isinstance(message_body, str):
        try:
            data = json.loads(message_body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in message: {e}") from e
    else:
        data = message_body

    # Handle nested Message field from SNS
    if "Message" in data and isinstance(data["Message"], str):
        try:
            data = json.loads(data["Message"])
        except json.JSONDecodeError:
            pass

    # Parse state change time
    state_change_time = None
    if "StateChangeTime" in data:
        try:
            state_change_time = datetime.fromisoformat(
                data["StateChangeTime"].replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            pass

    # Parse trigger details
    trigger = data.get("Trigger", {})
    dimensions = {}
    for dim in trigger.get("Dimensions", []):
        dimensions[dim.get("name", "")] = dim.get("value", "")

    return CloudWatchAlarmMessage(
        alarm_name=data.get("AlarmName", ""),
        alarm_description=data.get("AlarmDescription", ""),
        aws_account_id=data.get("AWSAccountId", ""),
        region=data.get("Region", ""),
        new_state=data.get("NewStateValue", ""),
        old_state=data.get("OldStateValue", ""),
        new_state_reason=data.get("NewStateReason", ""),
        state_change_time=state_change_time,
        metric_name=trigger.get("MetricName", ""),
        namespace=trigger.get("Namespace", ""),
        dimensions=dimensions,
        threshold=trigger.get("Threshold"),
        comparison_operator=trigger.get("ComparisonOperator", ""),
        evaluation_periods=trigger.get("EvaluationPeriods", 1),
        period=trigger.get("Period", 60),
        statistic=trigger.get("Statistic", ""),
        treat_missing_data=trigger.get("TreatMissingData", ""),
    )


def _determine_severity(alarm: CloudWatchAlarmMessage) -> AlertSeverity:
    """Determine alert severity from alarm name and state.

    Uses naming conventions and alarm characteristics to determine severity:
    - *-critical-* or *-p1-* -> CRITICAL
    - *-high-* or *-p2-* -> HIGH
    - *-warning-* or *-p3-* -> MEDIUM
    - *-info-* or *-p4-* -> LOW

    Args:
        alarm: Parsed CloudWatch alarm

    Returns:
        Appropriate alert severity
    """
    name_lower = alarm.alarm_name.lower()

    if any(x in name_lower for x in ["critical", "-p1-", "_p1_"]):
        return AlertSeverity.CRITICAL
    elif any(x in name_lower for x in ["high", "error", "-p2-", "_p2_"]):
        return AlertSeverity.HIGH
    elif any(x in name_lower for x in ["warning", "warn", "-p3-", "_p3_"]):
        return AlertSeverity.MEDIUM
    elif any(x in name_lower for x in ["info", "low", "-p4-", "_p4_", "-p5-"]):
        return AlertSeverity.LOW

    # Default based on namespace
    if "error" in alarm.namespace.lower():
        return AlertSeverity.HIGH

    return AlertSeverity.MEDIUM


class SNSAlertHandler:
    """Handler for SNS messages from CloudWatch Alarms.

    Converts CloudWatch Alarm notifications to platform-specific alerts
    and manages alert lifecycle (trigger, acknowledge, resolve).
    """

    def __init__(
        self,
        client: AlertClient,
        environment: str = "production",
        auto_resolve: bool = True,
    ) -> None:
        """Initialize the SNS handler.

        Args:
            client: Alert client for the target platform
            environment: Environment name for context
            auto_resolve: Whether to auto-resolve alerts when alarm clears
        """
        self.client = client
        self.environment = environment
        self.auto_resolve = auto_resolve

    def _create_dedup_key(self, alarm: CloudWatchAlarmMessage) -> str:
        """Create deduplication key for an alarm.

        Args:
            alarm: Parsed CloudWatch alarm

        Returns:
            Deduplication key string
        """
        # Include account, region, and alarm name for uniqueness
        parts = [
            alarm.aws_account_id or "unknown",
            alarm.region or "unknown",
            alarm.alarm_name,
        ]
        return ":".join(parts)

    def _alarm_to_alert(self, alarm: CloudWatchAlarmMessage) -> Alert:
        """Convert CloudWatch alarm to Alert.

        Args:
            alarm: Parsed CloudWatch alarm

        Returns:
            Alert ready for sending to platform
        """
        severity = _determine_severity(alarm)
        dedup_key = self._create_dedup_key(alarm)

        # Build description
        description_parts = [
            alarm.alarm_description or "No description provided",
            "",
            f"State: {alarm.old_state} → {alarm.new_state}",
            f"Reason: {alarm.new_state_reason}",
            "",
            f"Metric: {alarm.namespace}/{alarm.metric_name}",
            f"Threshold: {alarm.comparison_operator} {alarm.threshold}",
            f"Evaluation: {alarm.evaluation_periods} periods of {alarm.period}s",
        ]

        if alarm.dimensions:
            description_parts.append("")
            description_parts.append("Dimensions:")
            for key, value in alarm.dimensions.items():
                description_parts.append(f"  {key}: {value}")

        custom_details = {
            "aws_account_id": alarm.aws_account_id,
            "region": alarm.region,
            "namespace": alarm.namespace,
            "metric_name": alarm.metric_name,
            "threshold": alarm.threshold,
            "comparison_operator": alarm.comparison_operator,
            "evaluation_periods": alarm.evaluation_periods,
            "period": alarm.period,
            "statistic": alarm.statistic,
            "dimensions": alarm.dimensions,
        }

        # Build CloudWatch console link
        links = []
        if alarm.region and alarm.alarm_name:
            cw_url = (
                f"https://{alarm.region}.console.aws.amazon.com/cloudwatch/home"
                f"?region={alarm.region}#alarmsV2:alarm/{alarm.alarm_name}"
            )
            links.append({"href": cw_url, "text": "View in CloudWatch"})

        tags = [
            f"aws:{alarm.aws_account_id}",
            f"region:{alarm.region}",
            f"namespace:{alarm.namespace}",
            self.environment,
        ]

        return Alert(
            title=f"[{alarm.new_state}] {alarm.alarm_name}",
            description="\n".join(description_parts),
            severity=severity,
            source="cloudwatch",
            dedup_key=dedup_key,
            timestamp=alarm.state_change_time,
            custom_details=custom_details,
            links=links,
            tags=tags,
        )

    async def handle_message(self, message_body: str | dict) -> AlertResponse:
        """Handle an SNS message from CloudWatch.

        Args:
            message_body: Raw SNS message body

        Returns:
            Response from the alerting platform
        """
        try:
            alarm = parse_cloudwatch_alarm(message_body)
        except ValueError as e:
            logger.error("failed_to_parse_cloudwatch_alarm", error=str(e))
            return AlertResponse(
                success=False,
                message=f"Failed to parse alarm: {str(e)}",
            )

        logger.info(
            "processing_cloudwatch_alarm",
            alarm_name=alarm.alarm_name,
            new_state=alarm.new_state,
            old_state=alarm.old_state,
        )

        # Handle state transitions
        if alarm.new_state == "ALARM":
            alert = self._alarm_to_alert(alarm)
            return await self.client.create_alert(alert)

        elif alarm.new_state == "OK" and self.auto_resolve:
            dedup_key = self._create_dedup_key(alarm)
            return await self.client.resolve_alert(
                alert_id="",
                message=f"Alarm cleared: {alarm.new_state_reason}",
                dedup_key=dedup_key,
            )

        elif alarm.new_state == "INSUFFICIENT_DATA":
            # Log but don't create alert for insufficient data
            logger.info(
                "cloudwatch_alarm_insufficient_data",
                alarm_name=alarm.alarm_name,
                reason=alarm.new_state_reason,
            )
            return AlertResponse(
                success=True,
                message="Insufficient data state - no action taken",
            )

        return AlertResponse(
            success=True,
            message=f"Unhandled state: {alarm.new_state}",
        )

    async def handle_sns_notification(
        self,
        sns_message: dict[str, Any],
    ) -> AlertResponse:
        """Handle a full SNS notification envelope.

        Args:
            sns_message: Full SNS notification with Message field

        Returns:
            Response from the alerting platform
        """
        # Extract the actual message from SNS envelope
        message = sns_message.get("Message", sns_message)

        # Handle subscription confirmation
        if sns_message.get("Type") == "SubscriptionConfirmation":
            logger.info(
                "sns_subscription_confirmation",
                topic_arn=sns_message.get("TopicArn"),
                subscribe_url=sns_message.get("SubscribeURL"),
            )
            return AlertResponse(
                success=True,
                message="Subscription confirmation received",
            )

        return await self.handle_message(message)
