"""Cost monitoring configuration module.

Issue #169: Cost monitoring and budgets.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class CostGranularity(str, Enum):
    """Cost data granularity levels."""

    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    HOURLY = "HOURLY"


class CostMetric(str, Enum):
    """Cost metrics available from Cost Explorer."""

    UNBLENDED_COST = "UnblendedCost"
    BLENDED_COST = "BlendedCost"
    AMORTIZED_COST = "AmortizedCost"
    NET_AMORTIZED_COST = "NetAmortizedCost"
    NET_UNBLENDED_COST = "NetUnblendedCost"
    USAGE_QUANTITY = "UsageQuantity"
    NORMALIZED_USAGE_AMOUNT = "NormalizedUsageAmount"


class CostDimension(str, Enum):
    """Dimensions for grouping cost data."""

    SERVICE = "SERVICE"
    LINKED_ACCOUNT = "LINKED_ACCOUNT"
    REGION = "REGION"
    USAGE_TYPE = "USAGE_TYPE"
    INSTANCE_TYPE = "INSTANCE_TYPE"
    OPERATION = "OPERATION"
    RESOURCE_ID = "RESOURCE_ID"
    PURCHASE_TYPE = "PURCHASE_TYPE"


@dataclass
class BudgetConfig:
    """Configuration for a budget.

    Attributes:
        name: Budget name
        amount: Budget amount in USD
        time_unit: Time period (MONTHLY, QUARTERLY, ANNUALLY)
        alert_thresholds: List of thresholds (percentages) for alerts
        notification_emails: Email addresses for alerts
        include_tax: Whether to include tax in budget
        include_subscription: Whether to include subscriptions
        cost_filters: Optional cost filters (tags, services, etc.)
    """

    name: str
    amount: float
    time_unit: str = "MONTHLY"
    alert_thresholds: list[int] = field(default_factory=lambda: [50, 80, 100, 120])
    notification_emails: list[str] = field(default_factory=list)
    include_tax: bool = True
    include_subscription: bool = True
    cost_filters: dict[str, list[str]] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate budget configuration."""
        errors = []
        if self.amount <= 0:
            errors.append("Budget amount must be positive")
        if not self.name:
            errors.append("Budget name is required")
        if self.time_unit not in ("MONTHLY", "QUARTERLY", "ANNUALLY"):
            errors.append(f"Invalid time unit: {self.time_unit}")
        for threshold in self.alert_thresholds:
            if threshold < 0 or threshold > 200:
                errors.append(f"Invalid threshold: {threshold}")
        return errors


@dataclass
class CostConfig:
    """Main cost monitoring configuration.

    Attributes:
        project_name: Project name for filtering costs
        environment: Environment (development, staging, production)
        default_granularity: Default time granularity for cost queries
        default_metric: Default cost metric to use
        lookback_days: Number of days to look back for cost analysis
        forecast_days: Number of days to forecast
        anomaly_threshold: Minimum cost change (USD) to flag as anomaly
        anomaly_percentage_threshold: Percentage change to flag as anomaly
        budget: Budget configuration
        cost_allocation_tags: Tags to use for cost allocation
        excluded_services: Services to exclude from analysis
    """

    project_name: str = "cloud-optimizer"
    environment: str = "production"
    default_granularity: CostGranularity = CostGranularity.DAILY
    default_metric: CostMetric = CostMetric.UNBLENDED_COST
    lookback_days: int = 30
    forecast_days: int = 30
    anomaly_threshold: float = 50.0
    anomaly_percentage_threshold: float = 25.0
    budget: Optional[BudgetConfig] = None
    cost_allocation_tags: list[str] = field(
        default_factory=lambda: ["Project", "Environment", "Service"]
    )
    excluded_services: list[str] = field(default_factory=list)

    @staticmethod
    def get_current_month_start() -> datetime:
        """Get start of current month."""
        now = datetime.now(timezone.utc)
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def get_current_month_end() -> datetime:
        """Get end of current month."""
        now = datetime.now(timezone.utc)
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        return next_month.replace(hour=0, minute=0, second=0, microsecond=0)

    def validate(self) -> list[str]:
        """Validate cost configuration."""
        errors = []
        if self.lookback_days < 1 or self.lookback_days > 365:
            errors.append("Lookback days must be between 1 and 365")
        if self.forecast_days < 1 or self.forecast_days > 365:
            errors.append("Forecast days must be between 1 and 365")
        if self.anomaly_threshold < 0:
            errors.append("Anomaly threshold must be non-negative")
        if self.anomaly_percentage_threshold < 0:
            errors.append("Anomaly percentage threshold must be non-negative")
        if self.budget:
            errors.extend(self.budget.validate())
        return errors
