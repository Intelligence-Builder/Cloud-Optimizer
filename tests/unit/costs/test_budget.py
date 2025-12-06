"""Unit tests for budget management.

Issue #169: Cost monitoring and budgets.
"""

import pytest

from cloud_optimizer.costs.budget import Budget, BudgetAlert, BudgetStatus


class TestBudgetStatus:
    """Test BudgetStatus enum."""

    def test_ok_status(self) -> None:
        """Test OK status value."""
        assert BudgetStatus.OK.value == "ok"

    def test_warning_status(self) -> None:
        """Test WARNING status value."""
        assert BudgetStatus.WARNING.value == "warning"

    def test_critical_status(self) -> None:
        """Test CRITICAL status value."""
        assert BudgetStatus.CRITICAL.value == "critical"

    def test_exceeded_status(self) -> None:
        """Test EXCEEDED status value."""
        assert BudgetStatus.EXCEEDED.value == "exceeded"


class TestBudgetAlert:
    """Test BudgetAlert dataclass."""

    def test_default_values(self) -> None:
        """Test default alert values."""
        alert = BudgetAlert(threshold=80)
        assert alert.threshold == 80
        assert alert.threshold_type == "PERCENTAGE"
        assert alert.notification_state == "OK"
        assert alert.triggered is False
        assert alert.triggered_at is None

    def test_custom_threshold_type(self) -> None:
        """Test custom threshold type."""
        alert = BudgetAlert(threshold=100, threshold_type="ABSOLUTE")
        assert alert.threshold_type == "ABSOLUTE"

    def test_triggered_alert(self) -> None:
        """Test triggered alert."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        alert = BudgetAlert(
            threshold=80,
            triggered=True,
            triggered_at=now,
            notification_state="ALARM",
        )
        assert alert.triggered is True
        assert alert.triggered_at == now
        assert alert.notification_state == "ALARM"


class TestBudget:
    """Test Budget dataclass."""

    def test_default_values(self) -> None:
        """Test default budget values."""
        budget = Budget(name="test-budget")
        assert budget.name == "test-budget"
        assert budget.budget_type == "COST"
        assert budget.time_unit == "MONTHLY"
        assert budget.limit_amount == 0.0
        assert budget.actual_spend == 0.0
        assert budget.forecasted_spend == 0.0
        assert budget.status == BudgetStatus.OK
        assert budget.percent_used == 0.0
        assert budget.alerts == []
        assert budget.last_updated is None

    def test_custom_values(self) -> None:
        """Test custom budget values."""
        budget = Budget(
            name="production-budget",
            budget_type="COST",
            time_unit="MONTHLY",
            limit_amount=10000.0,
            actual_spend=5000.0,
            forecasted_spend=12000.0,
            status=BudgetStatus.WARNING,
            percent_used=50.0,
        )
        assert budget.name == "production-budget"
        assert budget.limit_amount == 10000.0
        assert budget.actual_spend == 5000.0
        assert budget.forecasted_spend == 12000.0
        assert budget.status == BudgetStatus.WARNING
        assert budget.percent_used == 50.0

    def test_budget_with_alerts(self) -> None:
        """Test budget with configured alerts."""
        alerts = [
            BudgetAlert(threshold=50),
            BudgetAlert(threshold=80),
            BudgetAlert(threshold=100, triggered=True),
        ]
        budget = Budget(name="test", alerts=alerts)
        assert len(budget.alerts) == 3
        assert budget.alerts[2].triggered is True

    def test_budget_exceeded_status(self) -> None:
        """Test budget with exceeded status."""
        budget = Budget(
            name="exceeded-budget",
            limit_amount=1000.0,
            actual_spend=1200.0,
            percent_used=120.0,
            status=BudgetStatus.EXCEEDED,
        )
        assert budget.status == BudgetStatus.EXCEEDED
        assert budget.percent_used == 120.0

    def test_budget_with_last_updated(self) -> None:
        """Test budget with last_updated timestamp."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        budget = Budget(name="test", last_updated=now)
        assert budget.last_updated == now

    def test_quarterly_budget(self) -> None:
        """Test quarterly budget configuration."""
        budget = Budget(name="quarterly", time_unit="QUARTERLY")
        assert budget.time_unit == "QUARTERLY"

    def test_annual_budget(self) -> None:
        """Test annual budget configuration."""
        budget = Budget(name="annual", time_unit="ANNUALLY")
        assert budget.time_unit == "ANNUALLY"
