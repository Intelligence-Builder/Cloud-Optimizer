"""Unit tests for cost monitoring configuration.

Issue #169: Cost monitoring and budgets.
"""

import pytest

from cloud_optimizer.costs.config import (
    BudgetConfig,
    CostConfig,
    CostDimension,
    CostGranularity,
    CostMetric,
)


class TestCostGranularity:
    """Test CostGranularity enum."""

    def test_daily_value(self) -> None:
        """Test DAILY granularity value."""
        assert CostGranularity.DAILY.value == "DAILY"

    def test_monthly_value(self) -> None:
        """Test MONTHLY granularity value."""
        assert CostGranularity.MONTHLY.value == "MONTHLY"

    def test_hourly_value(self) -> None:
        """Test HOURLY granularity value."""
        assert CostGranularity.HOURLY.value == "HOURLY"


class TestCostMetric:
    """Test CostMetric enum."""

    def test_unblended_cost(self) -> None:
        """Test UnblendedCost metric."""
        assert CostMetric.UNBLENDED_COST.value == "UnblendedCost"

    def test_blended_cost(self) -> None:
        """Test BlendedCost metric."""
        assert CostMetric.BLENDED_COST.value == "BlendedCost"

    def test_amortized_cost(self) -> None:
        """Test AmortizedCost metric."""
        assert CostMetric.AMORTIZED_COST.value == "AmortizedCost"


class TestCostDimension:
    """Test CostDimension enum."""

    def test_service_dimension(self) -> None:
        """Test SERVICE dimension."""
        assert CostDimension.SERVICE.value == "SERVICE"

    def test_region_dimension(self) -> None:
        """Test REGION dimension."""
        assert CostDimension.REGION.value == "REGION"

    def test_instance_type_dimension(self) -> None:
        """Test INSTANCE_TYPE dimension."""
        assert CostDimension.INSTANCE_TYPE.value == "INSTANCE_TYPE"


class TestBudgetConfig:
    """Test BudgetConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default budget configuration values."""
        config = BudgetConfig(name="test-budget", amount=1000)
        assert config.name == "test-budget"
        assert config.amount == 1000
        assert config.time_unit == "MONTHLY"
        assert config.alert_thresholds == [50, 80, 100, 120]
        assert config.include_tax is True
        assert config.include_subscription is True

    def test_custom_values(self) -> None:
        """Test custom budget configuration."""
        config = BudgetConfig(
            name="custom-budget",
            amount=5000,
            time_unit="QUARTERLY",
            alert_thresholds=[25, 50, 75, 100],
            notification_emails=["test@example.com"],
            include_tax=False,
        )
        assert config.amount == 5000
        assert config.time_unit == "QUARTERLY"
        assert config.alert_thresholds == [25, 50, 75, 100]
        assert "test@example.com" in config.notification_emails
        assert config.include_tax is False

    def test_validate_valid_config(self) -> None:
        """Test validation of valid configuration."""
        config = BudgetConfig(name="valid-budget", amount=1000)
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_missing_name(self) -> None:
        """Test validation with missing name."""
        config = BudgetConfig(name="", amount=1000)
        errors = config.validate()
        assert "Budget name is required" in errors

    def test_validate_invalid_amount(self) -> None:
        """Test validation with invalid amount."""
        config = BudgetConfig(name="test", amount=-100)
        errors = config.validate()
        assert "Budget amount must be positive" in errors

    def test_validate_invalid_time_unit(self) -> None:
        """Test validation with invalid time unit."""
        config = BudgetConfig(name="test", amount=1000, time_unit="WEEKLY")
        errors = config.validate()
        assert "Invalid time unit: WEEKLY" in errors

    def test_validate_invalid_threshold(self) -> None:
        """Test validation with invalid threshold."""
        config = BudgetConfig(name="test", amount=1000, alert_thresholds=[50, 250])
        errors = config.validate()
        assert "Invalid threshold: 250" in errors


class TestCostConfig:
    """Test CostConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default cost configuration values."""
        config = CostConfig()
        assert config.project_name == "cloud-optimizer"
        assert config.environment == "production"
        assert config.default_granularity == CostGranularity.DAILY
        assert config.default_metric == CostMetric.UNBLENDED_COST
        assert config.lookback_days == 30
        assert config.forecast_days == 30
        assert config.anomaly_threshold == 50.0
        assert config.anomaly_percentage_threshold == 25.0

    def test_custom_project_name(self) -> None:
        """Test custom project name."""
        config = CostConfig(project_name="my-project")
        assert config.project_name == "my-project"

    def test_custom_environment(self) -> None:
        """Test custom environment."""
        config = CostConfig(environment="development")
        assert config.environment == "development"

    def test_cost_allocation_tags(self) -> None:
        """Test default cost allocation tags."""
        config = CostConfig()
        assert "Project" in config.cost_allocation_tags
        assert "Environment" in config.cost_allocation_tags
        assert "Service" in config.cost_allocation_tags

    def test_validate_valid_config(self) -> None:
        """Test validation of valid configuration."""
        config = CostConfig()
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_invalid_lookback_days(self) -> None:
        """Test validation with invalid lookback days."""
        config = CostConfig(lookback_days=0)
        errors = config.validate()
        assert "Lookback days must be between 1 and 365" in errors

        config = CostConfig(lookback_days=400)
        errors = config.validate()
        assert "Lookback days must be between 1 and 365" in errors

    def test_validate_invalid_forecast_days(self) -> None:
        """Test validation with invalid forecast days."""
        config = CostConfig(forecast_days=-1)
        errors = config.validate()
        assert "Forecast days must be between 1 and 365" in errors

    def test_validate_invalid_anomaly_threshold(self) -> None:
        """Test validation with invalid anomaly threshold."""
        config = CostConfig(anomaly_threshold=-10)
        errors = config.validate()
        assert "Anomaly threshold must be non-negative" in errors

    def test_get_current_month_start(self) -> None:
        """Test getting current month start."""
        start = CostConfig.get_current_month_start()
        assert start.day == 1
        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0

    def test_get_current_month_end(self) -> None:
        """Test getting current month end."""
        end = CostConfig.get_current_month_end()
        assert end.day == 1  # First day of next month
        assert end.hour == 0

    def test_config_with_budget(self) -> None:
        """Test configuration with embedded budget config."""
        budget = BudgetConfig(name="test", amount=1000)
        config = CostConfig(budget=budget)
        assert config.budget is not None
        assert config.budget.name == "test"

    def test_validate_with_invalid_budget(self) -> None:
        """Test validation propagates to budget."""
        budget = BudgetConfig(name="", amount=-100)
        config = CostConfig(budget=budget)
        errors = config.validate()
        assert len(errors) >= 2  # Budget has multiple errors
