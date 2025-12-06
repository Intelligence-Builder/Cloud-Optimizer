"""Tests for alerting configuration."""

import pytest

from cloud_optimizer.alerting.config import (
    AlertConfig,
    AlertPlatform,
    AlertSeverity,
    EscalationLevel,
    EscalationPolicy,
    OnCallSchedule,
)


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_severity_values(self) -> None:
        """Test severity enum values."""
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.INFO.value == "info"

    def test_to_pagerduty_severity(self) -> None:
        """Test conversion to PagerDuty severity."""
        assert AlertSeverity.CRITICAL.to_pagerduty_severity() == "critical"
        assert AlertSeverity.HIGH.to_pagerduty_severity() == "error"
        assert AlertSeverity.MEDIUM.to_pagerduty_severity() == "warning"
        assert AlertSeverity.LOW.to_pagerduty_severity() == "info"
        assert AlertSeverity.INFO.to_pagerduty_severity() == "info"

    def test_to_opsgenie_priority(self) -> None:
        """Test conversion to OpsGenie priority."""
        assert AlertSeverity.CRITICAL.to_opsgenie_priority() == "P1"
        assert AlertSeverity.HIGH.to_opsgenie_priority() == "P2"
        assert AlertSeverity.MEDIUM.to_opsgenie_priority() == "P3"
        assert AlertSeverity.LOW.to_opsgenie_priority() == "P4"
        assert AlertSeverity.INFO.to_opsgenie_priority() == "P5"


class TestAlertPlatform:
    """Tests for AlertPlatform enum."""

    def test_platform_values(self) -> None:
        """Test platform enum values."""
        assert AlertPlatform.PAGERDUTY.value == "pagerduty"
        assert AlertPlatform.OPSGENIE.value == "opsgenie"


class TestEscalationLevel:
    """Tests for EscalationLevel dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        level = EscalationLevel(level=1, targets=["user-1"])
        assert level.level == 1
        assert level.targets == ["user-1"]
        assert level.delay_minutes == 30
        assert level.notify_type == "user"

    def test_custom_values(self) -> None:
        """Test custom values."""
        level = EscalationLevel(
            level=2,
            targets=["team-1", "team-2"],
            delay_minutes=15,
            notify_type="team",
        )
        assert level.level == 2
        assert level.targets == ["team-1", "team-2"]
        assert level.delay_minutes == 15
        assert level.notify_type == "team"


class TestEscalationPolicy:
    """Tests for EscalationPolicy dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        policy = EscalationPolicy(name="test")
        assert policy.name == "test"
        assert policy.description == ""
        assert policy.levels == []
        assert policy.repeat_enabled is True
        assert policy.repeat_count == 3

    def test_with_levels(self) -> None:
        """Test policy with escalation levels."""
        levels = [
            EscalationLevel(level=1, targets=["oncall"], delay_minutes=5),
            EscalationLevel(level=2, targets=["lead"], delay_minutes=15),
        ]
        policy = EscalationPolicy(
            name="critical",
            description="Critical alerts",
            levels=levels,
            repeat_enabled=True,
            repeat_count=5,
        )
        assert len(policy.levels) == 2
        assert policy.levels[0].delay_minutes == 5
        assert policy.levels[1].targets == ["lead"]


class TestOnCallSchedule:
    """Tests for OnCallSchedule dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        schedule = OnCallSchedule(name="primary")
        assert schedule.name == "primary"
        assert schedule.description == ""
        assert schedule.timezone == "UTC"
        assert schedule.rotation_type == "weekly"
        assert schedule.handoff_time == "09:00"
        assert schedule.users == []

    def test_custom_values(self) -> None:
        """Test custom values."""
        schedule = OnCallSchedule(
            name="weekend",
            description="Weekend on-call",
            timezone="America/New_York",
            rotation_type="daily",
            handoff_time="18:00",
            users=["user-1", "user-2"],
        )
        assert schedule.timezone == "America/New_York"
        assert schedule.rotation_type == "daily"
        assert schedule.handoff_time == "18:00"
        assert len(schedule.users) == 2


class TestAlertConfig:
    """Tests for AlertConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = AlertConfig()
        assert config.platform == AlertPlatform.PAGERDUTY
        assert config.api_key == ""
        assert config.api_url is None
        assert config.default_severity == AlertSeverity.MEDIUM
        assert config.environment == "production"
        assert config.deduplication_enabled is True
        assert config.deduplication_window_minutes == 60
        assert config.auto_resolve_enabled is True

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = AlertConfig(
            platform=AlertPlatform.OPSGENIE,
            api_key="test-key",
            service_id="service-123",
            environment="staging",
            default_severity=AlertSeverity.HIGH,
        )
        assert config.platform == AlertPlatform.OPSGENIE
        assert config.api_key == "test-key"
        assert config.service_id == "service-123"
        assert config.environment == "staging"
        assert config.default_severity == AlertSeverity.HIGH

    def test_base_url_pagerduty(self) -> None:
        """Test base URL for PagerDuty."""
        config = AlertConfig(platform=AlertPlatform.PAGERDUTY)
        assert config.base_url == "https://api.pagerduty.com"

    def test_base_url_opsgenie(self) -> None:
        """Test base URL for OpsGenie."""
        config = AlertConfig(platform=AlertPlatform.OPSGENIE)
        assert config.base_url == "https://api.opsgenie.com"

    def test_base_url_custom(self) -> None:
        """Test custom base URL."""
        config = AlertConfig(api_url="https://custom.api.com")
        assert config.base_url == "https://custom.api.com"

    def test_validate_missing_api_key(self) -> None:
        """Test validation with missing API key."""
        config = AlertConfig()
        errors = config.validate()
        assert "API key is required" in errors

    def test_validate_pagerduty_missing_routing_key(self) -> None:
        """Test validation for PagerDuty without routing key."""
        config = AlertConfig(
            platform=AlertPlatform.PAGERDUTY,
            api_key="test-key",
        )
        errors = config.validate()
        assert "Routing key is required for PagerDuty" in errors

    def test_validate_opsgenie_missing_service_id(self) -> None:
        """Test validation for OpsGenie without service ID."""
        config = AlertConfig(
            platform=AlertPlatform.OPSGENIE,
            api_key="test-key",
        )
        errors = config.validate()
        assert "Service ID is required for OpsGenie" in errors

    def test_validate_valid_pagerduty(self) -> None:
        """Test validation with valid PagerDuty config."""
        config = AlertConfig(
            platform=AlertPlatform.PAGERDUTY,
            api_key="test-key",
            routing_key="routing-key",
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_valid_opsgenie(self) -> None:
        """Test validation with valid OpsGenie config."""
        config = AlertConfig(
            platform=AlertPlatform.OPSGENIE,
            api_key="test-key",
            service_id="service-123",
        )
        errors = config.validate()
        assert len(errors) == 0
