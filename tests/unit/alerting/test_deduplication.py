"""Tests for alert deduplication."""

from datetime import datetime, timedelta

import pytest

from cloud_optimizer.alerting.client import Alert
from cloud_optimizer.alerting.config import AlertSeverity
from cloud_optimizer.alerting.deduplication import (
    AlertDeduplicator,
    AlertGroup,
    DeduplicationKey,
)


class TestDeduplicationKey:
    """Tests for DeduplicationKey dataclass."""

    def test_to_string_basic(self) -> None:
        """Test basic string conversion."""
        key = DeduplicationKey(
            source="cloudwatch",
            category="AWS/EC2",
            identifier="cpu-alarm",
        )
        result = key.to_string()
        assert result == "cloudwatch:AWS/EC2:cpu-alarm"

    def test_to_string_with_dimensions(self) -> None:
        """Test string conversion with dimensions."""
        key = DeduplicationKey(
            source="cloudwatch",
            category="AWS/EC2",
            identifier="cpu-alarm",
            dimensions={"InstanceId": "i-1234", "env": "prod"},
        )
        result = key.to_string()
        # Dimensions should be sorted
        assert "InstanceId=i-1234" in result
        assert "env=prod" in result

    def test_to_hash_consistent(self) -> None:
        """Test hash is consistent for same key."""
        key1 = DeduplicationKey(
            source="cloudwatch",
            category="test",
            identifier="alarm",
        )
        key2 = DeduplicationKey(
            source="cloudwatch",
            category="test",
            identifier="alarm",
        )
        assert key1.to_hash() == key2.to_hash()

    def test_to_hash_different_for_different_keys(self) -> None:
        """Test hash is different for different keys."""
        key1 = DeduplicationKey(
            source="cloudwatch",
            category="test",
            identifier="alarm1",
        )
        key2 = DeduplicationKey(
            source="cloudwatch",
            category="test",
            identifier="alarm2",
        )
        assert key1.to_hash() != key2.to_hash()


class TestAlertGroup:
    """Tests for AlertGroup dataclass."""

    def test_add_alert_first(self) -> None:
        """Test adding first alert to group."""
        group = AlertGroup(group_key="test")
        alert = Alert(title="Test Alert", description="Test", severity=AlertSeverity.MEDIUM)

        group.add_alert(alert)

        assert group.count == 1
        assert group.first_seen is not None
        assert group.last_seen is not None
        assert len(group.alerts) == 1

    def test_add_multiple_alerts(self) -> None:
        """Test adding multiple alerts to group."""
        group = AlertGroup(group_key="test")

        for i in range(3):
            alert = Alert(title=f"Alert {i}", description="Test", severity=AlertSeverity.MEDIUM)
            group.add_alert(alert)

        assert group.count == 3
        assert len(group.alerts) == 3

    def test_severity_tracking(self) -> None:
        """Test highest severity is tracked."""
        group = AlertGroup(group_key="test")

        alert1 = Alert(title="Low", description="Test", severity=AlertSeverity.LOW)
        group.add_alert(alert1)
        assert group.severity == "low"

        alert2 = Alert(title="High", description="Test", severity=AlertSeverity.HIGH)
        group.add_alert(alert2)
        assert group.severity == "high"

        alert3 = Alert(title="Medium", description="Test", severity=AlertSeverity.MEDIUM)
        group.add_alert(alert3)
        # Should still be high
        assert group.severity == "high"


class TestAlertDeduplicator:
    """Tests for AlertDeduplicator class."""

    @pytest.fixture
    def deduplicator(self) -> AlertDeduplicator:
        """Create deduplicator instance."""
        return AlertDeduplicator(
            window_minutes=60,
            max_alerts_per_window=5,
            grouping_enabled=True,
        )

    def test_first_alert_should_send(self, deduplicator: AlertDeduplicator) -> None:
        """Test first alert should always be sent."""
        alert = Alert(
            title="Test Alert",
            description="Test",
            source="cloudwatch",
            custom_details={"namespace": "AWS/EC2"},
        )

        should_send, reason = deduplicator.should_send(alert)

        assert should_send
        assert reason == "OK"

    def test_duplicate_alert_within_window(self, deduplicator: AlertDeduplicator) -> None:
        """Test duplicate alerts are allowed within limit."""
        alert = Alert(
            title="Test Alert",
            description="Test",
            source="cloudwatch",
            custom_details={"namespace": "AWS/EC2"},
        )

        # First 5 should be allowed
        for _ in range(5):
            should_send, _ = deduplicator.should_send(alert)
            assert should_send

        # 6th should be rate limited
        should_send, reason = deduplicator.should_send(alert)
        assert not should_send
        assert "Rate limited" in reason

    def test_different_alerts_not_deduplicated(self, deduplicator: AlertDeduplicator) -> None:
        """Test different alerts are not deduplicated."""
        alert1 = Alert(
            title="Alert 1",
            description="Test",
            source="cloudwatch",
            custom_details={"namespace": "AWS/EC2"},
        )
        alert2 = Alert(
            title="Alert 2",
            description="Test",
            source="cloudwatch",
            custom_details={"namespace": "AWS/RDS"},
        )

        should_send1, _ = deduplicator.should_send(alert1)
        should_send2, _ = deduplicator.should_send(alert2)

        assert should_send1
        assert should_send2

    def test_generate_key_from_namespace(self, deduplicator: AlertDeduplicator) -> None:
        """Test key generation uses namespace from custom_details."""
        alert = Alert(
            title="Test Alert",
            description="Test",
            source="cloudwatch",
            custom_details={"namespace": "AWS/EC2"},
        )

        key = deduplicator.generate_key(alert)

        assert key.source == "cloudwatch"
        assert key.category == "AWS/EC2"

    def test_generate_key_from_tags(self, deduplicator: AlertDeduplicator) -> None:
        """Test key generation uses namespace from tags."""
        alert = Alert(
            title="Test Alert",
            description="Test",
            source="cloudwatch",
            tags=["namespace:AWS/RDS", "env:prod"],
        )

        key = deduplicator.generate_key(alert)

        assert key.category == "AWS/RDS"

    def test_get_group(self, deduplicator: AlertDeduplicator) -> None:
        """Test getting alert group after sending."""
        alert = Alert(
            title="Test Alert",
            description="Test",
            source="cloudwatch",
            custom_details={"namespace": "AWS/EC2"},
        )

        deduplicator.should_send(alert)
        group = deduplicator.get_group(alert)

        assert group is not None
        assert group.count == 1

    def test_get_group_grouping_disabled(self) -> None:
        """Test get_group returns None when grouping disabled."""
        deduplicator = AlertDeduplicator(grouping_enabled=False)
        alert = Alert(title="Test", description="Test")

        deduplicator.should_send(alert)
        group = deduplicator.get_group(alert)

        assert group is None

    def test_get_stats(self, deduplicator: AlertDeduplicator) -> None:
        """Test statistics collection."""
        alert = Alert(
            title="Test Alert",
            description="Test",
            source="cloudwatch",
            custom_details={"namespace": "AWS/EC2"},
        )

        # Send 7 alerts (5 sent, 2 suppressed)
        for _ in range(7):
            deduplicator.should_send(alert)

        stats = deduplicator.get_stats()

        assert stats["active_keys"] == 1
        assert stats["active_groups"] == 1
        # Group count tracks only alerts that were added (sent), not suppressed ones
        # Total = 5 sent + 2 suppressed = 5 in group (suppressed don't add to group)
        assert stats["total_alerts_processed"] == 5
        assert stats["total_suppressed"] == 2
        assert stats["suppression_rate"] > 0

    def test_reset(self, deduplicator: AlertDeduplicator) -> None:
        """Test reset clears all state."""
        alert = Alert(title="Test", description="Test")
        deduplicator.should_send(alert)

        deduplicator.reset()
        stats = deduplicator.get_stats()

        assert stats["active_keys"] == 0
        assert stats["active_groups"] == 0

    def test_dimensions_in_key(self, deduplicator: AlertDeduplicator) -> None:
        """Test dimensions are included in dedup key."""
        alert1 = Alert(
            title="Test Alert",
            description="Test",
            source="cloudwatch",
            custom_details={
                "namespace": "AWS/EC2",
                "dimensions": {"InstanceId": "i-1111"},
            },
        )
        alert2 = Alert(
            title="Test Alert",
            description="Test",
            source="cloudwatch",
            custom_details={
                "namespace": "AWS/EC2",
                "dimensions": {"InstanceId": "i-2222"},
            },
        )

        key1 = deduplicator.generate_key(alert1)
        key2 = deduplicator.generate_key(alert2)

        # Different dimensions should produce different keys
        assert key1.to_hash() != key2.to_hash()
