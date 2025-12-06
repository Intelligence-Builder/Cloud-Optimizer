"""AWS Cost Explorer client implementation.

Issue #169: Cost monitoring and budgets.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from cloud_optimizer.costs.config import (
    CostConfig,
    CostDimension,
    CostGranularity,
    CostMetric,
)
from cloud_optimizer.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ServiceCost:
    """Cost breakdown for a single service.

    Attributes:
        service_name: AWS service name
        cost: Total cost in USD
        usage_quantity: Usage quantity (if available)
        unit: Unit of measurement
        percentage_of_total: Percentage of total cost
    """

    service_name: str
    cost: float
    usage_quantity: Optional[float] = None
    unit: str = "USD"
    percentage_of_total: float = 0.0


@dataclass
class CostTrend:
    """Cost trend over time.

    Attributes:
        date: Date of the cost data point
        cost: Cost for this period
        delta: Change from previous period
        delta_percentage: Percentage change from previous period
    """

    date: datetime
    cost: float
    delta: float = 0.0
    delta_percentage: float = 0.0


@dataclass
class CostReport:
    """Cost analysis report.

    Attributes:
        start_date: Start of analysis period
        end_date: End of analysis period
        total_cost: Total cost for the period
        average_daily_cost: Average daily cost
        service_breakdown: Cost breakdown by service
        trends: Daily/monthly cost trends
        forecast: Cost forecast (if available)
        currency: Currency code
    """

    start_date: datetime
    end_date: datetime
    total_cost: float
    average_daily_cost: float = 0.0
    service_breakdown: list[ServiceCost] = field(default_factory=list)
    trends: list[CostTrend] = field(default_factory=list)
    forecast: Optional[float] = None
    currency: str = "USD"


class CostExplorerClient:
    """AWS Cost Explorer API client.

    Provides access to cost and usage data, forecasts, and recommendations.
    """

    def __init__(self, config: Optional[CostConfig] = None) -> None:
        """Initialize Cost Explorer client.

        Args:
            config: Cost configuration (uses defaults if not provided)
        """
        self.config = config or CostConfig()
        self._client: Optional[Any] = None

    @property
    def client(self) -> Any:
        """Get or create boto3 Cost Explorer client."""
        if self._client is None:
            self._client = boto3.client("ce")
        return self._client

    def _format_date(self, dt: datetime) -> str:
        """Format datetime for Cost Explorer API."""
        return dt.strftime("%Y-%m-%d")

    async def get_cost_and_usage(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: Optional[CostGranularity] = None,
        metrics: Optional[list[CostMetric]] = None,
        group_by: Optional[list[CostDimension]] = None,
        filter_expression: Optional[dict[str, Any]] = None,
    ) -> CostReport:
        """Get cost and usage data.

        Args:
            start_date: Start of period (defaults to 30 days ago)
            end_date: End of period (defaults to today)
            granularity: Time granularity
            metrics: Cost metrics to retrieve
            group_by: Dimensions to group by
            filter_expression: Optional filter expression

        Returns:
            CostReport with cost data
        """
        end = end_date or datetime.now(timezone.utc)
        start = start_date or (end - timedelta(days=self.config.lookback_days))
        gran = granularity or self.config.default_granularity
        metric_list = metrics or [self.config.default_metric]

        params: dict[str, Any] = {
            "TimePeriod": {
                "Start": self._format_date(start),
                "End": self._format_date(end),
            },
            "Granularity": gran.value,
            "Metrics": [m.value for m in metric_list],
        }

        if group_by:
            params["GroupBy"] = [
                {"Type": "DIMENSION", "Key": dim.value} for dim in group_by
            ]

        if filter_expression:
            params["Filter"] = filter_expression

        logger.info(
            "get_cost_and_usage",
            start=self._format_date(start),
            end=self._format_date(end),
            granularity=gran.value,
        )

        try:
            response = self.client.get_cost_and_usage(**params)
            return self._parse_cost_response(response, start, end, metric_list[0])
        except ClientError as e:
            logger.error("cost_explorer_error", error=str(e))
            return CostReport(
                start_date=start,
                end_date=end,
                total_cost=0.0,
            )

    def _parse_cost_response(
        self,
        response: dict[str, Any],
        start: datetime,
        end: datetime,
        metric: CostMetric,
    ) -> CostReport:
        """Parse Cost Explorer response into CostReport."""
        results = response.get("ResultsByTime", [])
        total_cost = 0.0
        service_costs: dict[str, float] = {}
        trends: list[CostTrend] = []
        prev_cost = 0.0

        for result in results:
            period_start = datetime.fromisoformat(result["TimePeriod"]["Start"])
            groups = result.get("Groups", [])

            if groups:
                # Grouped by dimension (e.g., SERVICE)
                for group in groups:
                    key = group["Keys"][0]
                    cost = float(group["Metrics"][metric.value]["Amount"])
                    service_costs[key] = service_costs.get(key, 0) + cost
                    total_cost += cost
            else:
                # No grouping - total cost
                cost = float(result["Total"][metric.value]["Amount"])
                total_cost += cost

            # Build trends
            period_cost = sum(
                float(g["Metrics"][metric.value]["Amount"]) for g in groups
            ) if groups else float(result.get("Total", {}).get(metric.value, {}).get("Amount", 0))

            delta = period_cost - prev_cost if prev_cost > 0 else 0
            delta_pct = (delta / prev_cost * 100) if prev_cost > 0 else 0

            trends.append(CostTrend(
                date=period_start,
                cost=period_cost,
                delta=delta,
                delta_percentage=delta_pct,
            ))
            prev_cost = period_cost

        # Build service breakdown
        service_breakdown = [
            ServiceCost(
                service_name=name,
                cost=cost,
                percentage_of_total=(cost / total_cost * 100) if total_cost > 0 else 0,
            )
            for name, cost in sorted(
                service_costs.items(), key=lambda x: x[1], reverse=True
            )
        ]

        days = (end - start).days or 1
        return CostReport(
            start_date=start,
            end_date=end,
            total_cost=round(total_cost, 2),
            average_daily_cost=round(total_cost / days, 2),
            service_breakdown=service_breakdown,
            trends=trends,
        )

    async def get_cost_forecast(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        metric: Optional[CostMetric] = None,
        granularity: Optional[CostGranularity] = None,
    ) -> dict[str, Any]:
        """Get cost forecast.

        Args:
            start_date: Start of forecast period
            end_date: End of forecast period
            metric: Cost metric to forecast
            granularity: Time granularity

        Returns:
            Forecast data with predicted costs
        """
        now = datetime.now(timezone.utc)
        start = start_date or now
        end = end_date or (now + timedelta(days=self.config.forecast_days))
        met = metric or self.config.default_metric
        gran = granularity or CostGranularity.MONTHLY

        logger.info(
            "get_cost_forecast",
            start=self._format_date(start),
            end=self._format_date(end),
        )

        try:
            response = self.client.get_cost_forecast(
                TimePeriod={
                    "Start": self._format_date(start),
                    "End": self._format_date(end),
                },
                Metric=met.value,
                Granularity=gran.value,
            )

            return {
                "total": float(response.get("Total", {}).get("Amount", 0)),
                "mean": float(response.get("Total", {}).get("Amount", 0)),
                "prediction_interval_lower": float(
                    response.get("Total", {}).get("Amount", 0)
                ) * 0.9,
                "prediction_interval_upper": float(
                    response.get("Total", {}).get("Amount", 0)
                ) * 1.1,
                "by_time": [
                    {
                        "start": item["TimePeriod"]["Start"],
                        "end": item["TimePeriod"]["End"],
                        "mean": float(item["MeanValue"]),
                    }
                    for item in response.get("ForecastResultsByTime", [])
                ],
            }
        except ClientError as e:
            logger.error("cost_forecast_error", error=str(e))
            return {"total": 0, "error": str(e)}

    async def get_top_services(
        self,
        days: int = 30,
        limit: int = 10,
    ) -> list[ServiceCost]:
        """Get top services by cost.

        Args:
            days: Number of days to analyze
            limit: Maximum number of services to return

        Returns:
            List of top services by cost
        """
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        report = await self.get_cost_and_usage(
            start_date=start,
            end_date=end,
            group_by=[CostDimension.SERVICE],
        )

        return report.service_breakdown[:limit]

    async def get_cost_by_tag(
        self,
        tag_key: str,
        days: int = 30,
    ) -> dict[str, float]:
        """Get cost breakdown by tag value.

        Args:
            tag_key: Tag key to group by
            days: Number of days to analyze

        Returns:
            Dictionary mapping tag values to costs
        """
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        try:
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    "Start": self._format_date(start),
                    "End": self._format_date(end),
                },
                Granularity="MONTHLY",
                Metrics=[self.config.default_metric.value],
                GroupBy=[{"Type": "TAG", "Key": tag_key}],
            )

            costs: dict[str, float] = {}
            for result in response.get("ResultsByTime", []):
                for group in result.get("Groups", []):
                    tag_value = group["Keys"][0].replace(f"{tag_key}$", "") or "untagged"
                    cost = float(
                        group["Metrics"][self.config.default_metric.value]["Amount"]
                    )
                    costs[tag_value] = costs.get(tag_value, 0) + cost

            return costs
        except ClientError as e:
            logger.error("cost_by_tag_error", error=str(e))
            return {}

    async def get_recommendations(self) -> list[dict[str, Any]]:
        """Get cost optimization recommendations.

        Returns:
            List of recommendations with potential savings
        """
        recommendations = []

        try:
            # Get Reserved Instance recommendations
            ri_response = self.client.get_reservation_purchase_recommendation(
                Service="Amazon Elastic Compute Cloud - Compute",
                LookbackPeriodInDays="THIRTY_DAYS",
                TermInYears="ONE_YEAR",
                PaymentOption="NO_UPFRONT",
            )

            for rec in ri_response.get("Recommendations", []):
                for detail in rec.get("RecommendationDetails", []):
                    recommendations.append({
                        "type": "reserved_instance",
                        "service": "EC2",
                        "instance_type": detail.get("InstanceDetails", {})
                        .get("EC2InstanceDetails", {})
                        .get("InstanceType"),
                        "estimated_monthly_savings": float(
                            detail.get("EstimatedMonthlySavingsAmount", 0)
                        ),
                        "upfront_cost": float(detail.get("UpfrontCost", 0)),
                    })
        except ClientError:
            pass  # May not have permission or data

        try:
            # Get Savings Plans recommendations
            sp_response = self.client.get_savings_plans_purchase_recommendation(
                SavingsPlansType="COMPUTE_SP",
                LookbackPeriodInDays="THIRTY_DAYS",
                TermInYears="ONE_YEAR",
                PaymentOption="NO_UPFRONT",
            )

            savings_plan = sp_response.get("SavingsPlansPurchaseRecommendation", {})
            for detail in savings_plan.get("SavingsPlansPurchaseRecommendationDetails", []):
                recommendations.append({
                    "type": "savings_plan",
                    "hourly_commitment": float(detail.get("HourlyCommitmentToPurchase", 0)),
                    "estimated_savings_percentage": float(
                        detail.get("EstimatedSavingsPercentage", 0)
                    ),
                    "estimated_monthly_savings": float(
                        detail.get("EstimatedMonthlySavingsAmount", 0)
                    ),
                })
        except ClientError:
            pass

        return recommendations
