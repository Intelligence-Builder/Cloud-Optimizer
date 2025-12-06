"""Escalation policy configuration and management.

Provides configuration structures and utilities for managing
escalation policies across PagerDuty and OpsGenie.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import yaml

from cloud_optimizer.alerting.config import EscalationLevel, EscalationPolicy


class NotifyType(str, Enum):
    """Types of notification targets."""

    USER = "user"
    TEAM = "team"
    SCHEDULE = "schedule"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class OnCallRotation:
    """On-call rotation configuration.

    Attributes:
        name: Rotation name
        users: List of user IDs or emails in rotation order
        rotation_type: Type of rotation (daily, weekly, custom)
        start_time: Daily start time for handoff (HH:MM format)
        timezone: Timezone for the rotation
        restrictions: Time restrictions for the rotation
    """

    name: str
    users: list[str] = field(default_factory=list)
    rotation_type: str = "weekly"
    start_time: str = "09:00"
    timezone: str = "UTC"
    restrictions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class EscalationConfig:
    """Full escalation configuration.

    Attributes:
        policies: Named escalation policies
        schedules: On-call schedules
        default_policy: Name of the default policy
        notification_timeout_minutes: Minutes before escalating
        ack_timeout_minutes: Minutes before re-notifying if not acknowledged
    """

    policies: dict[str, EscalationPolicy] = field(default_factory=dict)
    schedules: dict[str, OnCallRotation] = field(default_factory=dict)
    default_policy: str = "default"
    notification_timeout_minutes: int = 5
    ack_timeout_minutes: int = 30


# Default escalation policies for Cloud Optimizer
DEFAULT_ESCALATION_POLICIES = {
    "critical": EscalationPolicy(
        name="critical",
        description="Critical issues requiring immediate attention",
        levels=[
            EscalationLevel(
                level=1,
                targets=["primary-oncall"],
                delay_minutes=5,
                notify_type="schedule",
            ),
            EscalationLevel(
                level=2,
                targets=["secondary-oncall", "engineering-lead"],
                delay_minutes=15,
                notify_type="schedule",
            ),
            EscalationLevel(
                level=3,
                targets=["engineering-manager", "vp-engineering"],
                delay_minutes=30,
                notify_type="user",
            ),
        ],
        repeat_enabled=True,
        repeat_count=5,
    ),
    "high": EscalationPolicy(
        name="high",
        description="High severity issues",
        levels=[
            EscalationLevel(
                level=1,
                targets=["primary-oncall"],
                delay_minutes=15,
                notify_type="schedule",
            ),
            EscalationLevel(
                level=2,
                targets=["secondary-oncall"],
                delay_minutes=30,
                notify_type="schedule",
            ),
            EscalationLevel(
                level=3,
                targets=["engineering-lead"],
                delay_minutes=60,
                notify_type="user",
            ),
        ],
        repeat_enabled=True,
        repeat_count=3,
    ),
    "medium": EscalationPolicy(
        name="medium",
        description="Medium severity issues",
        levels=[
            EscalationLevel(
                level=1,
                targets=["primary-oncall"],
                delay_minutes=30,
                notify_type="schedule",
            ),
            EscalationLevel(
                level=2,
                targets=["engineering-team"],
                delay_minutes=120,
                notify_type="team",
            ),
        ],
        repeat_enabled=True,
        repeat_count=2,
    ),
    "low": EscalationPolicy(
        name="low",
        description="Low severity issues",
        levels=[
            EscalationLevel(
                level=1,
                targets=["engineering-team"],
                delay_minutes=60,
                notify_type="team",
            ),
        ],
        repeat_enabled=False,
        repeat_count=0,
    ),
    "default": EscalationPolicy(
        name="default",
        description="Default escalation policy",
        levels=[
            EscalationLevel(
                level=1,
                targets=["primary-oncall"],
                delay_minutes=15,
                notify_type="schedule",
            ),
            EscalationLevel(
                level=2,
                targets=["engineering-team"],
                delay_minutes=60,
                notify_type="team",
            ),
        ],
        repeat_enabled=True,
        repeat_count=2,
    ),
}


def policy_to_dict(policy: EscalationPolicy) -> dict[str, Any]:
    """Convert EscalationPolicy to dictionary.

    Args:
        policy: Policy to convert

    Returns:
        Dictionary representation
    """
    return {
        "name": policy.name,
        "description": policy.description,
        "levels": [
            {
                "level": level.level,
                "targets": level.targets,
                "delay_minutes": level.delay_minutes,
                "notify_type": level.notify_type,
            }
            for level in policy.levels
        ],
        "repeat_enabled": policy.repeat_enabled,
        "repeat_count": policy.repeat_count,
    }


def dict_to_policy(data: dict[str, Any]) -> EscalationPolicy:
    """Convert dictionary to EscalationPolicy.

    Args:
        data: Dictionary with policy data

    Returns:
        EscalationPolicy instance
    """
    levels = [
        EscalationLevel(
            level=l["level"],
            targets=l["targets"],
            delay_minutes=l.get("delay_minutes", 30),
            notify_type=l.get("notify_type", "user"),
        )
        for l in data.get("levels", [])
    ]

    return EscalationPolicy(
        name=data["name"],
        description=data.get("description", ""),
        levels=levels,
        repeat_enabled=data.get("repeat_enabled", True),
        repeat_count=data.get("repeat_count", 3),
    )


def load_escalation_config(config_path: str) -> EscalationConfig:
    """Load escalation configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        EscalationConfig instance
    """
    with open(config_path) as f:
        data = yaml.safe_load(f)

    policies = {}
    for name, policy_data in data.get("policies", {}).items():
        policy_data["name"] = name
        policies[name] = dict_to_policy(policy_data)

    schedules = {}
    for name, schedule_data in data.get("schedules", {}).items():
        schedules[name] = OnCallRotation(
            name=name,
            users=schedule_data.get("users", []),
            rotation_type=schedule_data.get("rotation_type", "weekly"),
            start_time=schedule_data.get("start_time", "09:00"),
            timezone=schedule_data.get("timezone", "UTC"),
            restrictions=schedule_data.get("restrictions", []),
        )

    return EscalationConfig(
        policies=policies,
        schedules=schedules,
        default_policy=data.get("default_policy", "default"),
        notification_timeout_minutes=data.get("notification_timeout_minutes", 5),
        ack_timeout_minutes=data.get("ack_timeout_minutes", 30),
    )


def save_escalation_config(config: EscalationConfig, config_path: str) -> None:
    """Save escalation configuration to YAML file.

    Args:
        config: Configuration to save
        config_path: Path to write YAML file
    """
    data: dict[str, Any] = {
        "default_policy": config.default_policy,
        "notification_timeout_minutes": config.notification_timeout_minutes,
        "ack_timeout_minutes": config.ack_timeout_minutes,
        "policies": {},
        "schedules": {},
    }

    for name, policy in config.policies.items():
        data["policies"][name] = policy_to_dict(policy)
        del data["policies"][name]["name"]  # Remove redundant name

    for name, schedule in config.schedules.items():
        data["schedules"][name] = {
            "users": schedule.users,
            "rotation_type": schedule.rotation_type,
            "start_time": schedule.start_time,
            "timezone": schedule.timezone,
            "restrictions": schedule.restrictions,
        }

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_policy_for_severity(
    severity: str,
    config: Optional[EscalationConfig] = None,
) -> EscalationPolicy:
    """Get escalation policy for a given severity.

    Args:
        severity: Alert severity (critical, high, medium, low)
        config: Optional custom configuration

    Returns:
        Appropriate EscalationPolicy
    """
    if config and severity in config.policies:
        return config.policies[severity]

    if severity in DEFAULT_ESCALATION_POLICIES:
        return DEFAULT_ESCALATION_POLICIES[severity]

    # Fall back to default
    if config and config.default_policy in config.policies:
        return config.policies[config.default_policy]

    return DEFAULT_ESCALATION_POLICIES["default"]
