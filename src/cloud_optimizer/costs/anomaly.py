"""AWS Cost Anomaly Detection implementation.

Issue #169: Cost monitoring and budgets.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from cloud_optimizer.costs.config import CostConfig
from cloud_optimizer.logging import get_logger

logger = get_logger(__name__)


class AnomalySeverity(str, Enum):
    """Cost anomaly severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CostAnomaly:
    """Cost anomaly information.

    Attributes:
        anomaly_id: Unique anomaly identifier
        service: AWS service with anomaly
        region: AWS region (if applicable)
        start_date: When anomaly started
        end_date: When anomaly ended (or ongoing)
        expected_cost: Expected cost for the period
        actual_cost: Actual cost incurred
        impact: Cost impact in USD
        impact_percentage: Percentage deviation from expected
        severity: Anomaly severity level
        root_causes: Potential root causes
        is_resolved: Whether anomaly has been resolved
    """

    anomaly_id: str
    service: str
    region: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    expected_cost: float = 0.0
    actual_cost: float = 0.0
    impact: float = 0.0
    impact_percentage: float = 0.0
    severity: AnomalySeverity = AnomalySeverity.LOW
    root_causes: list[dict[str, Any]] = field(default_factory=list)
    is_resolved: bool = False


class AnomalyDetector:
    """AWS Cost Anomaly Detection client.

    Provides access to cost anomaly monitors and detected anomalies.
    """

    def __init__(self, config: Optional[CostConfig] = None) -> None:
        """Initialize Anomaly Detector.

        Args:
            config: Cost configuration
        """
        self.config = config or CostConfig()
        self._client: Optional[Any] = None

    @property
    def client(self) -> Any:
        """Get or create boto3 Cost Explorer client."""
        if self._client is None:
            self._client = boto3.client("ce")
        return self._client

    def _determine_severity(
        self, impact: float, impact_percentage: float
    ) -> AnomalySeverity:
        """Determine anomaly severity.

        Args:
            impact: Cost impact in USD
            impact_percentage: Percentage deviation

        Returns:
            Anomaly severity level
        """
        if impact >= 1000 or impact_percentage >= 100:
            return AnomalySeverity.CRITICAL
        if impact >= 500 or impact_percentage >= 50:
            return AnomalySeverity.HIGH
        if impact >= 100 or impact_percentage >= 25:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW

    async def list_monitors(self) -> list[dict[str, Any]]:
        """List all anomaly monitors.

        Returns:
            List of monitor configurations
        """
        logger.info("list_anomaly_monitors")

        try:
            response = self.client.get_anomaly_monitors(MaxResults=100)

            monitors = []
            for monitor in response.get("AnomalyMonitors", []):
                monitors.append({
                    "arn": monitor.get("MonitorArn"),
                    "name": monitor.get("MonitorName"),
                    "type": monitor.get("MonitorType"),
                    "dimension": monitor.get("MonitorDimension"),
                    "creation_date": monitor.get("CreationDate"),
                    "last_updated": monitor.get("LastUpdatedDate"),
                })
            return monitors
        except ClientError as e:
            logger.error("list_monitors_error", error=str(e))
            return []

    async def get_anomalies(
        self,
        days: int = 30,
        monitor_arn: Optional[str] = None,
    ) -> list[CostAnomaly]:
        """Get detected cost anomalies.

        Args:
            days: Number of days to look back
            monitor_arn: Optional monitor ARN to filter by

        Returns:
            List of detected anomalies
        """
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        logger.info("get_anomalies", days=days, monitor_arn=monitor_arn)

        try:
            params: dict[str, Any] = {
                "DateInterval": {
                    "StartDate": start.strftime("%Y-%m-%d"),
                    "EndDate": end.strftime("%Y-%m-%d"),
                },
                "MaxResults": 100,
            }

            if monitor_arn:
                params["MonitorArn"] = monitor_arn

            response = self.client.get_anomalies(**params)
            anomalies = []

            for anomaly_data in response.get("Anomalies", []):
                impact = anomaly_data.get("Impact", {})
                total_impact = float(impact.get("TotalImpact", 0))
                expected = float(impact.get("TotalExpectedSpend", 0))

                impact_pct = (
                    (total_impact / expected * 100) if expected > 0 else 0
                )

                # Parse root causes
                root_causes = []
                for rc in anomaly_data.get("RootCauses", []):
                    root_causes.append({
                        "service": rc.get("Service"),
                        "region": rc.get("Region"),
                        "linked_account": rc.get("LinkedAccount"),
                        "usage_type": rc.get("UsageType"),
                    })

                anomaly = CostAnomaly(
                    anomaly_id=anomaly_data.get("AnomalyId", ""),
                    service=root_causes[0].get("service", "Unknown")
                    if root_causes else "Unknown",
                    region=root_causes[0].get("region")
                    if root_causes else None,
                    start_date=datetime.fromisoformat(
                        anomaly_data.get("AnomalyStartDate", "").replace("Z", "+00:00")
                    ) if anomaly_data.get("AnomalyStartDate") else None,
                    end_date=datetime.fromisoformat(
                        anomaly_data.get("AnomalyEndDate", "").replace("Z", "+00:00")
                    ) if anomaly_data.get("AnomalyEndDate") else None,
                    expected_cost=expected,
                    actual_cost=float(impact.get("TotalActualSpend", 0)),
                    impact=total_impact,
                    impact_percentage=round(impact_pct, 1),
                    severity=self._determine_severity(total_impact, impact_pct),
                    root_causes=root_causes,
                    is_resolved=anomaly_data.get("AnomalyEndDate") is not None,
                )
                anomalies.append(anomaly)

            return anomalies
        except ClientError as e:
            logger.error("get_anomalies_error", error=str(e))
            return []

    async def create_monitor(
        self,
        name: str,
        monitor_type: str = "DIMENSIONAL",
        dimension: str = "SERVICE",
        tags: Optional[dict[str, str]] = None,
    ) -> Optional[str]:
        """Create a new anomaly monitor.

        Args:
            name: Monitor name
            monitor_type: Type (DIMENSIONAL or CUSTOM)
            dimension: Dimension to monitor (SERVICE, LINKED_ACCOUNT)
            tags: Optional tags

        Returns:
            Monitor ARN if created successfully
        """
        logger.info(
            "create_anomaly_monitor",
            name=name,
            type=monitor_type,
            dimension=dimension,
        )

        try:
            params: dict[str, Any] = {
                "MonitorName": name,
                "MonitorType": monitor_type,
            }

            if monitor_type == "DIMENSIONAL":
                params["MonitorDimension"] = dimension

            if tags:
                params["ResourceTags"] = [
                    {"Key": k, "Value": v} for k, v in tags.items()
                ]

            response = self.client.create_anomaly_monitor(
                AnomalyMonitor=params
            )

            arn = response.get("MonitorArn")
            logger.info("anomaly_monitor_created", arn=arn)
            return arn
        except ClientError as e:
            logger.error("create_monitor_error", error=str(e))
            return None

    async def create_subscription(
        self,
        name: str,
        monitor_arns: list[str],
        threshold: float,
        email_addresses: list[str],
        frequency: str = "DAILY",
    ) -> Optional[str]:
        """Create an anomaly subscription for alerts.

        Args:
            name: Subscription name
            monitor_arns: List of monitor ARNs to subscribe to
            threshold: Cost threshold for alerts (USD)
            email_addresses: Email addresses for notifications
            frequency: Alert frequency (IMMEDIATE, DAILY, WEEKLY)

        Returns:
            Subscription ARN if created successfully
        """
        logger.info(
            "create_anomaly_subscription",
            name=name,
            threshold=threshold,
            frequency=frequency,
        )

        try:
            response = self.client.create_anomaly_subscription(
                AnomalySubscription={
                    "SubscriptionName": name,
                    "MonitorArnList": monitor_arns,
                    "Threshold": threshold,
                    "Frequency": frequency,
                    "Subscribers": [
                        {"Type": "EMAIL", "Address": email}
                        for email in email_addresses
                    ],
                }
            )

            arn = response.get("SubscriptionArn")
            logger.info("anomaly_subscription_created", arn=arn)
            return arn
        except ClientError as e:
            logger.error("create_subscription_error", error=str(e))
            return None

    async def delete_monitor(self, monitor_arn: str) -> bool:
        """Delete an anomaly monitor.

        Args:
            monitor_arn: ARN of monitor to delete

        Returns:
            True if deleted successfully
        """
        logger.info("delete_anomaly_monitor", arn=monitor_arn)

        try:
            self.client.delete_anomaly_monitor(MonitorArn=monitor_arn)
            logger.info("anomaly_monitor_deleted", arn=monitor_arn)
            return True
        except ClientError as e:
            logger.error("delete_monitor_error", error=str(e))
            return False

    async def get_summary(self, days: int = 30) -> dict[str, Any]:
        """Get anomaly summary for the account.

        Args:
            days: Number of days to analyze

        Returns:
            Summary of anomaly activity
        """
        anomalies = await self.get_anomalies(days=days)

        if not anomalies:
            return {
                "total_anomalies": 0,
                "total_impact": 0,
                "resolved": 0,
                "active": 0,
                "by_severity": {},
                "by_service": {},
            }

        by_severity: dict[str, int] = {}
        by_service: dict[str, float] = {}
        total_impact = 0.0
        resolved = 0
        active = 0

        for anomaly in anomalies:
            severity = anomaly.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

            by_service[anomaly.service] = (
                by_service.get(anomaly.service, 0) + anomaly.impact
            )

            total_impact += anomaly.impact

            if anomaly.is_resolved:
                resolved += 1
            else:
                active += 1

        return {
            "total_anomalies": len(anomalies),
            "total_impact": round(total_impact, 2),
            "resolved": resolved,
            "active": active,
            "by_severity": by_severity,
            "by_service": {
                k: round(v, 2)
                for k, v in sorted(
                    by_service.items(), key=lambda x: x[1], reverse=True
                )
            },
        }
