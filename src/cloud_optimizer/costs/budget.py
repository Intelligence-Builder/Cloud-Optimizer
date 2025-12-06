"""AWS Budgets client implementation.

Issue #169: Cost monitoring and budgets.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from cloud_optimizer.costs.config import BudgetConfig
from cloud_optimizer.logging import get_logger

logger = get_logger(__name__)


class BudgetStatus(str, Enum):
    """Budget status levels."""

    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


@dataclass
class BudgetAlert:
    """Budget alert information.

    Attributes:
        threshold: Alert threshold percentage
        threshold_type: Type of threshold (PERCENTAGE or ABSOLUTE)
        notification_state: Current notification state
        triggered: Whether alert has been triggered
        triggered_at: When alert was triggered
    """

    threshold: float
    threshold_type: str = "PERCENTAGE"
    notification_state: str = "OK"
    triggered: bool = False
    triggered_at: Optional[datetime] = None


@dataclass
class Budget:
    """Budget information.

    Attributes:
        name: Budget name
        budget_type: Type of budget (COST, USAGE, etc.)
        time_unit: Time period (MONTHLY, QUARTERLY, ANNUALLY)
        limit_amount: Budget limit in USD
        actual_spend: Current actual spend
        forecasted_spend: Forecasted spend for the period
        status: Current budget status
        percent_used: Percentage of budget used
        alerts: List of configured alerts
        last_updated: When budget data was last updated
    """

    name: str
    budget_type: str = "COST"
    time_unit: str = "MONTHLY"
    limit_amount: float = 0.0
    actual_spend: float = 0.0
    forecasted_spend: float = 0.0
    status: BudgetStatus = BudgetStatus.OK
    percent_used: float = 0.0
    alerts: list[BudgetAlert] = field(default_factory=list)
    last_updated: Optional[datetime] = None


class BudgetClient:
    """AWS Budgets API client.

    Provides access to budget creation, monitoring, and alerts.
    """

    def __init__(self, account_id: Optional[str] = None) -> None:
        """Initialize Budgets client.

        Args:
            account_id: AWS account ID (auto-detected if not provided)
        """
        self._client: Optional[Any] = None
        self._sts_client: Optional[Any] = None
        self._account_id = account_id

    @property
    def client(self) -> Any:
        """Get or create boto3 Budgets client."""
        if self._client is None:
            self._client = boto3.client("budgets")
        return self._client

    @property
    def account_id(self) -> str:
        """Get AWS account ID."""
        if self._account_id is None:
            if self._sts_client is None:
                self._sts_client = boto3.client("sts")
            self._account_id = self._sts_client.get_caller_identity()["Account"]
        return self._account_id

    def _determine_status(self, percent_used: float, forecasted_percent: float) -> BudgetStatus:
        """Determine budget status based on usage.

        Args:
            percent_used: Actual percentage used
            forecasted_percent: Forecasted percentage

        Returns:
            Budget status
        """
        if percent_used >= 100:
            return BudgetStatus.EXCEEDED
        if percent_used >= 80 or forecasted_percent >= 100:
            return BudgetStatus.CRITICAL
        if percent_used >= 50 or forecasted_percent >= 80:
            return BudgetStatus.WARNING
        return BudgetStatus.OK

    async def list_budgets(self) -> list[Budget]:
        """List all budgets for the account.

        Returns:
            List of Budget objects
        """
        logger.info("listing_budgets", account_id=self.account_id)

        try:
            response = self.client.describe_budgets(AccountId=self.account_id)
            budgets = []

            for budget_data in response.get("Budgets", []):
                limit = float(
                    budget_data.get("BudgetLimit", {}).get("Amount", 0)
                )
                actual = float(
                    budget_data.get("CalculatedSpend", {})
                    .get("ActualSpend", {})
                    .get("Amount", 0)
                )
                forecasted = float(
                    budget_data.get("CalculatedSpend", {})
                    .get("ForecastedSpend", {})
                    .get("Amount", 0)
                )

                percent_used = (actual / limit * 100) if limit > 0 else 0
                forecasted_percent = (forecasted / limit * 100) if limit > 0 else 0

                budget = Budget(
                    name=budget_data.get("BudgetName", ""),
                    budget_type=budget_data.get("BudgetType", "COST"),
                    time_unit=budget_data.get("TimeUnit", "MONTHLY"),
                    limit_amount=limit,
                    actual_spend=actual,
                    forecasted_spend=forecasted,
                    percent_used=round(percent_used, 1),
                    status=self._determine_status(percent_used, forecasted_percent),
                    last_updated=datetime.now(timezone.utc),
                )
                budgets.append(budget)

            return budgets
        except ClientError as e:
            logger.error("list_budgets_error", error=str(e))
            return []

    async def get_budget(self, budget_name: str) -> Optional[Budget]:
        """Get a specific budget by name.

        Args:
            budget_name: Name of the budget

        Returns:
            Budget object or None if not found
        """
        logger.info("get_budget", budget_name=budget_name)

        try:
            response = self.client.describe_budget(
                AccountId=self.account_id,
                BudgetName=budget_name,
            )

            budget_data = response.get("Budget", {})
            limit = float(budget_data.get("BudgetLimit", {}).get("Amount", 0))
            actual = float(
                budget_data.get("CalculatedSpend", {})
                .get("ActualSpend", {})
                .get("Amount", 0)
            )
            forecasted = float(
                budget_data.get("CalculatedSpend", {})
                .get("ForecastedSpend", {})
                .get("Amount", 0)
            )

            percent_used = (actual / limit * 100) if limit > 0 else 0
            forecasted_percent = (forecasted / limit * 100) if limit > 0 else 0

            return Budget(
                name=budget_data.get("BudgetName", ""),
                budget_type=budget_data.get("BudgetType", "COST"),
                time_unit=budget_data.get("TimeUnit", "MONTHLY"),
                limit_amount=limit,
                actual_spend=actual,
                forecasted_spend=forecasted,
                percent_used=round(percent_used, 1),
                status=self._determine_status(percent_used, forecasted_percent),
                last_updated=datetime.now(timezone.utc),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "NotFoundException":
                return None
            logger.error("get_budget_error", error=str(e))
            return None

    async def create_budget(self, config: BudgetConfig) -> bool:
        """Create a new budget.

        Args:
            config: Budget configuration

        Returns:
            True if created successfully
        """
        errors = config.validate()
        if errors:
            logger.error("budget_config_invalid", errors=errors)
            return False

        logger.info("create_budget", name=config.name, amount=config.amount)

        try:
            budget = {
                "BudgetName": config.name,
                "BudgetType": "COST",
                "BudgetLimit": {
                    "Amount": str(config.amount),
                    "Unit": "USD",
                },
                "TimeUnit": config.time_unit,
                "CostTypes": {
                    "IncludeTax": config.include_tax,
                    "IncludeSubscription": config.include_subscription,
                    "UseBlended": False,
                    "IncludeRefund": False,
                    "IncludeCredit": False,
                    "IncludeUpfront": True,
                    "IncludeRecurring": True,
                    "IncludeOtherSubscription": True,
                    "IncludeSupport": True,
                    "IncludeDiscount": True,
                    "UseAmortized": False,
                },
            }

            if config.cost_filters:
                budget["CostFilters"] = config.cost_filters

            notifications = []
            for threshold in config.alert_thresholds:
                notification = {
                    "Notification": {
                        "NotificationType": "ACTUAL",
                        "ComparisonOperator": "GREATER_THAN",
                        "Threshold": threshold,
                        "ThresholdType": "PERCENTAGE",
                    },
                    "Subscribers": [
                        {"SubscriptionType": "EMAIL", "Address": email}
                        for email in config.notification_emails
                    ],
                }
                notifications.append(notification)

            self.client.create_budget(
                AccountId=self.account_id,
                Budget=budget,
                NotificationsWithSubscribers=notifications,
            )

            logger.info("budget_created", name=config.name)
            return True
        except ClientError as e:
            logger.error("create_budget_error", error=str(e))
            return False

    async def delete_budget(self, budget_name: str) -> bool:
        """Delete a budget.

        Args:
            budget_name: Name of the budget to delete

        Returns:
            True if deleted successfully
        """
        logger.info("delete_budget", name=budget_name)

        try:
            self.client.delete_budget(
                AccountId=self.account_id,
                BudgetName=budget_name,
            )
            logger.info("budget_deleted", name=budget_name)
            return True
        except ClientError as e:
            logger.error("delete_budget_error", error=str(e))
            return False

    async def get_budget_performance(
        self,
        budget_name: str,
        periods: int = 12,
    ) -> list[dict[str, Any]]:
        """Get budget performance history.

        Args:
            budget_name: Budget name
            periods: Number of periods to retrieve

        Returns:
            List of performance data points
        """
        logger.info("get_budget_performance", name=budget_name, periods=periods)

        try:
            response = self.client.describe_budget_performance_history(
                AccountId=self.account_id,
                BudgetName=budget_name,
                MaxResults=periods,
            )

            return [
                {
                    "start": item["TimePeriod"]["Start"],
                    "end": item["TimePeriod"]["End"],
                    "budgeted": float(item["BudgetedAmount"]["Amount"]),
                    "actual": float(item["ActualAmount"]["Amount"]),
                }
                for item in response.get("BudgetPerformanceHistory", {}).get(
                    "BudgetedAndActualAmountsList", []
                )
            ]
        except ClientError as e:
            logger.error("budget_performance_error", error=str(e))
            return []
