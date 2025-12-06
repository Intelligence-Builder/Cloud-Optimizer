"""PagerDuty alerting client implementation.

Integrates with PagerDuty Events API v2 for creating, acknowledging,
and resolving incidents.
"""

import hashlib
import json
from typing import Any, Optional

import httpx

from cloud_optimizer.alerting.client import Alert, AlertClient, AlertResponse
from cloud_optimizer.alerting.config import AlertConfig
from cloud_optimizer.logging import get_logger

logger = get_logger(__name__)


class PagerDutyClient(AlertClient):
    """PagerDuty Events API v2 client.

    Uses the Events API for incident management which provides:
    - Event deduplication via dedup_key
    - Automatic incident grouping
    - Integration with PagerDuty's escalation and notification systems
    """

    EVENTS_API_URL = "https://events.pagerduty.com/v2/enqueue"

    def __init__(self, config: AlertConfig) -> None:
        """Initialize PagerDuty client.

        Args:
            config: Alert configuration with PagerDuty routing key
        """
        super().__init__(config)
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Token token={self.config.api_key}",
                },
            )
        return self._http_client

    def _generate_dedup_key(self, alert: Alert) -> str:
        """Generate deduplication key for an alert.

        Args:
            alert: Alert to generate key for

        Returns:
            Deduplication key string
        """
        if alert.dedup_key:
            return alert.dedup_key

        # Generate based on source and title
        key_source = f"{alert.source}:{alert.title}"
        return hashlib.sha256(key_source.encode()).hexdigest()[:32]

    def _build_event_payload(
        self,
        alert: Alert,
        event_action: str = "trigger",
    ) -> dict[str, Any]:
        """Build PagerDuty Events API v2 payload.

        Args:
            alert: Alert data
            event_action: One of "trigger", "acknowledge", "resolve"

        Returns:
            Events API v2 compatible payload
        """
        dedup_key = self._generate_dedup_key(alert)

        payload: dict[str, Any] = {
            "routing_key": self.config.routing_key,
            "event_action": event_action,
            "dedup_key": dedup_key,
        }

        if event_action == "trigger":
            payload["payload"] = {
                "summary": alert.title[:1024],  # PagerDuty limit
                "severity": alert.severity.to_pagerduty_severity(),
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat() if alert.timestamp else None,
                "custom_details": {
                    "description": alert.description,
                    "environment": self.config.environment,
                    **alert.custom_details,
                },
            }

            if alert.links:
                payload["links"] = [
                    {"href": link.get("href", ""), "text": link.get("text", "")}
                    for link in alert.links[:5]  # PagerDuty limit
                ]

            # Add images if any (for dashboards, graphs)
            payload["images"] = []

        return payload

    async def create_alert(self, alert: Alert) -> AlertResponse:
        """Create a new incident in PagerDuty.

        Args:
            alert: Alert to create

        Returns:
            Response with incident ID and dedup key
        """
        payload = self._build_event_payload(alert, "trigger")
        dedup_key = payload["dedup_key"]

        logger.info(
            "creating_pagerduty_alert",
            title=alert.title,
            severity=alert.severity.value,
            dedup_key=dedup_key,
        )

        try:
            response = await self.http_client.post(
                self.EVENTS_API_URL,
                json=payload,
            )

            if response.status_code == 202:
                data = response.json()
                logger.info(
                    "pagerduty_alert_created",
                    dedup_key=dedup_key,
                    status=data.get("status"),
                )
                return AlertResponse(
                    success=True,
                    alert_id=data.get("dedup_key", dedup_key),
                    message=data.get("message", "Event accepted"),
                    dedup_key=dedup_key,
                    status="triggered",
                )
            else:
                error_msg = response.text
                logger.error(
                    "pagerduty_alert_failed",
                    status_code=response.status_code,
                    error=error_msg,
                )
                return AlertResponse(
                    success=False,
                    message=f"PagerDuty API error: {error_msg}",
                    dedup_key=dedup_key,
                )

        except Exception as e:
            logger.exception("pagerduty_alert_exception", error=str(e))
            return AlertResponse(
                success=False,
                message=f"Exception creating alert: {str(e)}",
                dedup_key=dedup_key,
            )

    async def acknowledge_alert(
        self, alert_id: str, message: Optional[str] = None
    ) -> AlertResponse:
        """Acknowledge an incident in PagerDuty.

        Args:
            alert_id: Deduplication key of the incident
            message: Optional acknowledgment message

        Returns:
            Response with updated status
        """
        payload = {
            "routing_key": self.config.routing_key,
            "event_action": "acknowledge",
            "dedup_key": alert_id,
        }

        logger.info("acknowledging_pagerduty_alert", dedup_key=alert_id)

        try:
            response = await self.http_client.post(
                self.EVENTS_API_URL,
                json=payload,
            )

            if response.status_code == 202:
                return AlertResponse(
                    success=True,
                    alert_id=alert_id,
                    message="Alert acknowledged",
                    dedup_key=alert_id,
                    status="acknowledged",
                )
            else:
                return AlertResponse(
                    success=False,
                    alert_id=alert_id,
                    message=f"Failed to acknowledge: {response.text}",
                )

        except Exception as e:
            logger.exception("pagerduty_acknowledge_exception", error=str(e))
            return AlertResponse(
                success=False,
                alert_id=alert_id,
                message=f"Exception acknowledging alert: {str(e)}",
            )

    async def resolve_alert(
        self,
        alert_id: str,
        message: Optional[str] = None,
        dedup_key: Optional[str] = None,
    ) -> AlertResponse:
        """Resolve an incident in PagerDuty.

        Args:
            alert_id: Deduplication key of the incident
            message: Optional resolution message
            dedup_key: Alternative dedup key (if alert_id not provided)

        Returns:
            Response with updated status
        """
        key = dedup_key or alert_id

        payload = {
            "routing_key": self.config.routing_key,
            "event_action": "resolve",
            "dedup_key": key,
        }

        logger.info("resolving_pagerduty_alert", dedup_key=key)

        try:
            response = await self.http_client.post(
                self.EVENTS_API_URL,
                json=payload,
            )

            if response.status_code == 202:
                return AlertResponse(
                    success=True,
                    alert_id=key,
                    message="Alert resolved",
                    dedup_key=key,
                    status="resolved",
                )
            else:
                return AlertResponse(
                    success=False,
                    alert_id=key,
                    message=f"Failed to resolve: {response.text}",
                )

        except Exception as e:
            logger.exception("pagerduty_resolve_exception", error=str(e))
            return AlertResponse(
                success=False,
                alert_id=key,
                message=f"Exception resolving alert: {str(e)}",
            )

    async def get_alert(self, alert_id: str) -> Optional[dict[str, Any]]:
        """Get incident details from PagerDuty REST API.

        Args:
            alert_id: Incident ID

        Returns:
            Incident details or None if not found
        """
        url = f"{self.config.base_url}/incidents/{alert_id}"

        try:
            response = await self.http_client.get(url)
            if response.status_code == 200:
                return response.json().get("incident")
            return None
        except Exception as e:
            logger.exception("pagerduty_get_alert_exception", error=str(e))
            return None

    async def add_note(self, alert_id: str, note: str) -> AlertResponse:
        """Add a note to an incident in PagerDuty.

        Args:
            alert_id: Incident ID
            note: Note content

        Returns:
            Response indicating success
        """
        url = f"{self.config.base_url}/incidents/{alert_id}/notes"

        payload = {
            "note": {
                "content": note,
            }
        }

        try:
            response = await self.http_client.post(url, json=payload)
            if response.status_code in (200, 201):
                return AlertResponse(
                    success=True,
                    alert_id=alert_id,
                    message="Note added successfully",
                )
            else:
                return AlertResponse(
                    success=False,
                    alert_id=alert_id,
                    message=f"Failed to add note: {response.text}",
                )
        except Exception as e:
            logger.exception("pagerduty_add_note_exception", error=str(e))
            return AlertResponse(
                success=False,
                alert_id=alert_id,
                message=f"Exception adding note: {str(e)}",
            )

    async def test_connection(self) -> bool:
        """Test connection to PagerDuty API.

        Returns:
            True if connection is successful
        """
        url = f"{self.config.base_url}/abilities"

        try:
            response = await self.http_client.get(url)
            return response.status_code == 200
        except Exception as e:
            logger.exception("pagerduty_connection_test_failed", error=str(e))
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
