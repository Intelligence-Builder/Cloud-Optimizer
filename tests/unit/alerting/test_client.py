"""Tests for alert client base classes."""

from datetime import datetime

import pytest

from cloud_optimizer.alerting.client import Alert, AlertResponse, get_alert_client
from cloud_optimizer.alerting.config import AlertConfig, AlertPlatform, AlertSeverity
from cloud_optimizer.alerting.pagerduty import PagerDutyClient
from cloud_optimizer.alerting.opsgenie import OpsGenieClient


class TestAlert:
    """Tests for Alert dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        alert = Alert(title="Test", description="Test description")

        assert alert.title == "Test"
        assert alert.description == "Test description"
        assert alert.severity == AlertSeverity.MEDIUM
        assert alert.source == "cloud-optimizer"
        assert alert.dedup_key is None
        assert alert.timestamp is not None
        assert alert.custom_details == {}
        assert alert.links == []
        assert alert.tags == []

    def test_custom_values(self) -> None:
        """Test custom values."""
        timestamp = datetime(2025, 12, 4, 16, 0, 0)
        alert = Alert(
            title="Critical Alert",
            description="Something is wrong",
            severity=AlertSeverity.CRITICAL,
            source="cloudwatch",
            dedup_key="unique-key",
            timestamp=timestamp,
            custom_details={"region": "us-east-1"},
            links=[{"href": "https://example.com", "text": "Link"}],
            tags=["prod", "critical"],
        )

        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.source == "cloudwatch"
        assert alert.dedup_key == "unique-key"
        assert alert.timestamp == timestamp
        assert alert.custom_details["region"] == "us-east-1"
        assert len(alert.links) == 1
        assert "prod" in alert.tags


class TestAlertResponse:
    """Tests for AlertResponse dataclass."""

    def test_success_response(self) -> None:
        """Test successful response."""
        response = AlertResponse(
            success=True,
            alert_id="incident-123",
            message="Alert created",
            dedup_key="dedup-key",
            status="triggered",
        )

        assert response.success
        assert response.alert_id == "incident-123"
        assert response.message == "Alert created"
        assert response.dedup_key == "dedup-key"
        assert response.status == "triggered"

    def test_failure_response(self) -> None:
        """Test failure response."""
        response = AlertResponse(
            success=False,
            message="API error",
        )

        assert not response.success
        assert response.alert_id is None
        assert response.message == "API error"


class TestGetAlertClient:
    """Tests for get_alert_client factory function."""

    def test_get_pagerduty_client(self) -> None:
        """Test creating PagerDuty client."""
        config = AlertConfig(
            platform=AlertPlatform.PAGERDUTY,
            api_key="test-key",
            routing_key="routing-key",
        )

        client = get_alert_client(config)

        assert isinstance(client, PagerDutyClient)
        assert client.config == config

    def test_get_opsgenie_client(self) -> None:
        """Test creating OpsGenie client."""
        config = AlertConfig(
            platform=AlertPlatform.OPSGENIE,
            api_key="test-key",
            service_id="service-123",
        )

        client = get_alert_client(config)

        assert isinstance(client, OpsGenieClient)
        assert client.config == config


class TestPagerDutyClient:
    """Tests for PagerDutyClient."""

    @pytest.fixture
    def client(self) -> PagerDutyClient:
        """Create PagerDuty client for testing."""
        config = AlertConfig(
            platform=AlertPlatform.PAGERDUTY,
            api_key="test-api-key",
            routing_key="test-routing-key",
            environment="test",
        )
        return PagerDutyClient(config)

    def test_generate_dedup_key_from_alert(self, client: PagerDutyClient) -> None:
        """Test dedup key generation from alert."""
        alert = Alert(
            title="Test Alert",
            description="Test",
            source="test-source",
            dedup_key="custom-key",
        )

        key = client._generate_dedup_key(alert)

        assert key == "custom-key"

    def test_generate_dedup_key_automatic(self, client: PagerDutyClient) -> None:
        """Test automatic dedup key generation."""
        alert = Alert(
            title="Test Alert",
            description="Test",
            source="test-source",
        )

        key = client._generate_dedup_key(alert)

        assert len(key) == 32  # SHA256 truncated to 32 chars

    def test_build_trigger_payload(self, client: PagerDutyClient) -> None:
        """Test building trigger event payload."""
        alert = Alert(
            title="Critical Alert",
            description="Service is down",
            severity=AlertSeverity.CRITICAL,
            source="cloudwatch",
            custom_details={"region": "us-east-1"},
        )

        payload = client._build_event_payload(alert, "trigger")

        assert payload["routing_key"] == "test-routing-key"
        assert payload["event_action"] == "trigger"
        assert "dedup_key" in payload
        assert payload["payload"]["summary"] == "Critical Alert"
        assert payload["payload"]["severity"] == "critical"
        assert payload["payload"]["source"] == "cloudwatch"

    def test_build_acknowledge_payload(self, client: PagerDutyClient) -> None:
        """Test building acknowledge event payload."""
        alert = Alert(
            title="Test",
            description="Test",
            dedup_key="test-dedup",
        )

        payload = client._build_event_payload(alert, "acknowledge")

        assert payload["event_action"] == "acknowledge"
        assert payload["dedup_key"] == "test-dedup"
        assert "payload" not in payload  # No payload for acknowledge

    def test_build_resolve_payload(self, client: PagerDutyClient) -> None:
        """Test building resolve event payload."""
        alert = Alert(
            title="Test",
            description="Test",
            dedup_key="test-dedup",
        )

        payload = client._build_event_payload(alert, "resolve")

        assert payload["event_action"] == "resolve"
        assert payload["dedup_key"] == "test-dedup"


class TestOpsGenieClient:
    """Tests for OpsGenieClient."""

    @pytest.fixture
    def client(self) -> OpsGenieClient:
        """Create OpsGenie client for testing."""
        config = AlertConfig(
            platform=AlertPlatform.OPSGENIE,
            api_key="test-api-key",
            service_id="test-service",
            environment="test",
        )
        return OpsGenieClient(config)

    def test_generate_alias_from_alert(self, client: OpsGenieClient) -> None:
        """Test alias generation from alert."""
        alert = Alert(
            title="Test Alert",
            description="Test",
            dedup_key="custom-alias",
        )

        alias = client._generate_alias(alert)

        assert alias == "custom-alias"

    def test_generate_alias_automatic(self, client: OpsGenieClient) -> None:
        """Test automatic alias generation."""
        alert = Alert(
            title="Test Alert",
            description="Test",
            source="test-source",
        )

        alias = client._generate_alias(alert)

        assert len(alias) == 64  # SHA256 truncated to 64 chars

    def test_build_alert_payload(self, client: OpsGenieClient) -> None:
        """Test building alert creation payload."""
        alert = Alert(
            title="Critical Alert",
            description="Service is down",
            severity=AlertSeverity.CRITICAL,
            source="cloudwatch",
            tags=["prod"],
            custom_details={"region": "us-east-1"},
        )

        payload = client._build_alert_payload(alert)

        assert payload["message"] == "Critical Alert"
        assert payload["priority"] == "P1"
        assert payload["source"] == "cloudwatch"
        assert "alias" in payload
        assert "test" in payload["tags"]  # Environment added to tags
        assert "prod" in payload["tags"]
        assert payload["details"]["region"] == "us-east-1"

    def test_build_alert_payload_with_team(self, client: OpsGenieClient) -> None:
        """Test payload includes responders when service_id set."""
        alert = Alert(
            title="Test",
            description="Test",
        )

        payload = client._build_alert_payload(alert)

        assert "responders" in payload
        assert payload["responders"][0]["type"] == "team"
        assert payload["responders"][0]["id"] == "test-service"

    def test_alerts_url(self, client: OpsGenieClient) -> None:
        """Test alerts URL property."""
        assert client.alerts_url == "https://api.opsgenie.com/v2/alerts"
