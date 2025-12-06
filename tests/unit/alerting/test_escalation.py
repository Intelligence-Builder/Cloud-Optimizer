"""Tests for escalation policy configuration."""

import os
import tempfile

import pytest
import yaml

from cloud_optimizer.alerting.config import EscalationLevel, EscalationPolicy
from cloud_optimizer.alerting.escalation import (
    DEFAULT_ESCALATION_POLICIES,
    EscalationConfig,
    NotifyType,
    OnCallRotation,
    dict_to_policy,
    get_policy_for_severity,
    load_escalation_config,
    policy_to_dict,
    save_escalation_config,
)


class TestNotifyType:
    """Tests for NotifyType enum."""

    def test_notify_type_values(self) -> None:
        """Test notify type enum values."""
        assert NotifyType.USER.value == "user"
        assert NotifyType.TEAM.value == "team"
        assert NotifyType.SCHEDULE.value == "schedule"
        assert NotifyType.EMAIL.value == "email"
        assert NotifyType.WEBHOOK.value == "webhook"


class TestOnCallRotation:
    """Tests for OnCallRotation dataclass."""

    def test_default_values(self) -> None:
        """Test default rotation values."""
        rotation = OnCallRotation(name="primary")

        assert rotation.name == "primary"
        assert rotation.users == []
        assert rotation.rotation_type == "weekly"
        assert rotation.start_time == "09:00"
        assert rotation.timezone == "UTC"
        assert rotation.restrictions == []

    def test_custom_values(self) -> None:
        """Test custom rotation values."""
        rotation = OnCallRotation(
            name="weekend",
            users=["user-1", "user-2"],
            rotation_type="daily",
            start_time="18:00",
            timezone="America/New_York",
            restrictions=[{"type": "weekend"}],
        )

        assert rotation.name == "weekend"
        assert len(rotation.users) == 2
        assert rotation.rotation_type == "daily"
        assert rotation.start_time == "18:00"
        assert rotation.timezone == "America/New_York"
        assert len(rotation.restrictions) == 1


class TestEscalationConfig:
    """Tests for EscalationConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default config values."""
        config = EscalationConfig()

        assert config.policies == {}
        assert config.schedules == {}
        assert config.default_policy == "default"
        assert config.notification_timeout_minutes == 5
        assert config.ack_timeout_minutes == 30


class TestDefaultPolicies:
    """Tests for DEFAULT_ESCALATION_POLICIES."""

    def test_critical_policy_exists(self) -> None:
        """Test critical policy is defined."""
        assert "critical" in DEFAULT_ESCALATION_POLICIES
        policy = DEFAULT_ESCALATION_POLICIES["critical"]
        assert policy.name == "critical"
        assert len(policy.levels) >= 3
        assert policy.repeat_count == 5

    def test_high_policy_exists(self) -> None:
        """Test high policy is defined."""
        assert "high" in DEFAULT_ESCALATION_POLICIES
        policy = DEFAULT_ESCALATION_POLICIES["high"]
        assert policy.name == "high"
        assert len(policy.levels) >= 2

    def test_medium_policy_exists(self) -> None:
        """Test medium policy is defined."""
        assert "medium" in DEFAULT_ESCALATION_POLICIES
        policy = DEFAULT_ESCALATION_POLICIES["medium"]
        assert policy.name == "medium"

    def test_low_policy_exists(self) -> None:
        """Test low policy is defined."""
        assert "low" in DEFAULT_ESCALATION_POLICIES
        policy = DEFAULT_ESCALATION_POLICIES["low"]
        assert policy.name == "low"
        assert policy.repeat_enabled is False

    def test_default_policy_exists(self) -> None:
        """Test default policy is defined."""
        assert "default" in DEFAULT_ESCALATION_POLICIES


class TestPolicyConversion:
    """Tests for policy conversion functions."""

    def test_policy_to_dict(self) -> None:
        """Test converting policy to dictionary."""
        policy = EscalationPolicy(
            name="test",
            description="Test policy",
            levels=[
                EscalationLevel(level=1, targets=["user-1"], delay_minutes=5),
                EscalationLevel(level=2, targets=["team-1"], delay_minutes=15, notify_type="team"),
            ],
            repeat_enabled=True,
            repeat_count=3,
        )

        result = policy_to_dict(policy)

        assert result["name"] == "test"
        assert result["description"] == "Test policy"
        assert len(result["levels"]) == 2
        assert result["levels"][0]["delay_minutes"] == 5
        assert result["levels"][1]["notify_type"] == "team"
        assert result["repeat_enabled"] is True
        assert result["repeat_count"] == 3

    def test_dict_to_policy(self) -> None:
        """Test converting dictionary to policy."""
        data = {
            "name": "test",
            "description": "Test policy",
            "levels": [
                {"level": 1, "targets": ["user-1"], "delay_minutes": 5, "notify_type": "user"},
                {"level": 2, "targets": ["team-1"], "delay_minutes": 15, "notify_type": "team"},
            ],
            "repeat_enabled": True,
            "repeat_count": 3,
        }

        result = dict_to_policy(data)

        assert result.name == "test"
        assert result.description == "Test policy"
        assert len(result.levels) == 2
        assert result.levels[0].targets == ["user-1"]
        assert result.levels[1].notify_type == "team"

    def test_roundtrip_conversion(self) -> None:
        """Test converting policy to dict and back."""
        original = DEFAULT_ESCALATION_POLICIES["critical"]

        as_dict = policy_to_dict(original)
        restored = dict_to_policy(as_dict)

        assert restored.name == original.name
        assert restored.description == original.description
        assert len(restored.levels) == len(original.levels)
        assert restored.repeat_enabled == original.repeat_enabled
        assert restored.repeat_count == original.repeat_count


class TestLoadSaveConfig:
    """Tests for loading and saving escalation config."""

    def test_load_config(self) -> None:
        """Test loading config from YAML file."""
        config_content = """
default_policy: medium
notification_timeout_minutes: 10
ack_timeout_minutes: 60

policies:
  test:
    description: Test policy
    levels:
      - level: 1
        targets:
          - user-1
        delay_minutes: 5
        notify_type: user
    repeat_enabled: true
    repeat_count: 2

schedules:
  primary:
    users:
      - user-1
      - user-2
    rotation_type: weekly
    start_time: "09:00"
    timezone: UTC
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            config = load_escalation_config(f.name)

        os.unlink(f.name)

        assert config.default_policy == "medium"
        assert config.notification_timeout_minutes == 10
        assert "test" in config.policies
        assert config.policies["test"].description == "Test policy"
        assert "primary" in config.schedules
        assert len(config.schedules["primary"].users) == 2

    def test_save_config(self) -> None:
        """Test saving config to YAML file."""
        config = EscalationConfig(
            default_policy="high",
            notification_timeout_minutes=15,
            policies={
                "test": EscalationPolicy(
                    name="test",
                    description="Test",
                    levels=[EscalationLevel(level=1, targets=["user-1"])],
                )
            },
            schedules={
                "primary": OnCallRotation(name="primary", users=["user-1"])
            },
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            save_escalation_config(config, f.name)

            with open(f.name) as read_f:
                saved_data = yaml.safe_load(read_f)

        os.unlink(f.name)

        assert saved_data["default_policy"] == "high"
        assert "test" in saved_data["policies"]
        assert "primary" in saved_data["schedules"]


class TestGetPolicyForSeverity:
    """Tests for get_policy_for_severity function."""

    def test_get_critical_policy(self) -> None:
        """Test getting critical policy."""
        policy = get_policy_for_severity("critical")
        assert policy.name == "critical"

    def test_get_high_policy(self) -> None:
        """Test getting high policy."""
        policy = get_policy_for_severity("high")
        assert policy.name == "high"

    def test_get_medium_policy(self) -> None:
        """Test getting medium policy."""
        policy = get_policy_for_severity("medium")
        assert policy.name == "medium"

    def test_get_low_policy(self) -> None:
        """Test getting low policy."""
        policy = get_policy_for_severity("low")
        assert policy.name == "low"

    def test_get_default_for_unknown(self) -> None:
        """Test getting default policy for unknown severity."""
        policy = get_policy_for_severity("unknown")
        assert policy.name == "default"

    def test_get_policy_from_custom_config(self) -> None:
        """Test getting policy from custom config."""
        custom_policy = EscalationPolicy(
            name="custom-critical",
            description="Custom critical",
            levels=[],
        )
        config = EscalationConfig(
            policies={"critical": custom_policy},
            default_policy="critical",
        )

        policy = get_policy_for_severity("critical", config)

        assert policy.name == "custom-critical"
