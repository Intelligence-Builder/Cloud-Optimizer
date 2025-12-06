"""OpsGenie alerting client implementation.

Integrates with OpsGenie Alert API for creating, acknowledging,
and resolving alerts with support for priorities and teams.
"""

import hashlib
from typing import Any, Optional

import httpx

from cloud_optimizer.alerting.client import Alert, AlertClient, AlertResponse
from cloud_optimizer.alerting.config import AlertConfig
from cloud_optimizer.logging import get_logger

logger = get_logger(__name__)


class OpsGenieClient(AlertClient):
    """OpsGenie Alert API client.

    Uses the OpsGenie Alert API v2 for alert management which provides:
    - Alert creation with priorities (P1-P5)
    - Team-based routing
    - Alert tags and custom properties
    - Deduplication via alias
    """

    def __init__(self, config: AlertConfig) -> None:
        """Initialize OpsGenie client.

        Args:
            config: Alert configuration with OpsGenie API key
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
                    "Authorization": f"GenieKey {self.config.api_key}",
                },
            )
        return self._http_client

    @property
    def alerts_url(self) -> str:
        """Get alerts API endpoint."""
        return f"{self.config.base_url}/v2/alerts"

    def _generate_alias(self, alert: Alert) -> str:
        """Generate alias (deduplication key) for an alert.

        Args:
            alert: Alert to generate alias for

        Returns:
            Alias string for deduplication
        """
        if alert.dedup_key:
            return alert.dedup_key

        # Generate based on source and title
        key_source = f"{alert.source}:{alert.title}"
        return hashlib.sha256(key_source.encode()).hexdigest()[:64]

    def _build_alert_payload(self, alert: Alert) -> dict[str, Any]:
        """Build OpsGenie alert creation payload.

        Args:
            alert: Alert data

        Returns:
            OpsGenie API compatible payload
        """
        alias = self._generate_alias(alert)

        payload: dict[str, Any] = {
            "message": alert.title[:130],  # OpsGenie limit
            "alias": alias,
            "description": alert.description[:15000],  # OpsGenie limit
            "priority": alert.severity.to_opsgenie_priority(),
            "source": alert.source,
            "tags": list(set(alert.tags + [self.config.environment])),
            "details": {
                "environment": self.config.environment,
                **alert.custom_details,
            },
        }

        # Add responders (teams/users) if service_id is configured
        if self.config.service_id:
            payload["responders"] = [
                {"type": "team", "id": self.config.service_id}
            ]

        return payload

    async def create_alert(self, alert: Alert) -> AlertResponse:
        """Create a new alert in OpsGenie.

        Args:
            alert: Alert to create

        Returns:
            Response with alert ID and alias
        """
        payload = self._build_alert_payload(alert)
        alias = payload["alias"]

        logger.info(
            "creating_opsgenie_alert",
            message=alert.title,
            priority=payload["priority"],
            alias=alias,
        )

        try:
            response = await self.http_client.post(
                self.alerts_url,
                json=payload,
            )

            if response.status_code in (200, 201, 202):
                data = response.json()
                request_id = data.get("requestId", "")
                logger.info(
                    "opsgenie_alert_created",
                    alias=alias,
                    request_id=request_id,
                )
                return AlertResponse(
                    success=True,
                    alert_id=request_id,
                    message=data.get("result", "Alert created"),
                    dedup_key=alias,
                    status="open",
                )
            else:
                error_msg = response.text
                logger.error(
                    "opsgenie_alert_failed",
                    status_code=response.status_code,
                    error=error_msg,
                )
                return AlertResponse(
                    success=False,
                    message=f"OpsGenie API error: {error_msg}",
                    dedup_key=alias,
                )

        except Exception as e:
            logger.exception("opsgenie_alert_exception", error=str(e))
            return AlertResponse(
                success=False,
                message=f"Exception creating alert: {str(e)}",
                dedup_key=alias,
            )

    async def acknowledge_alert(
        self, alert_id: str, message: Optional[str] = None
    ) -> AlertResponse:
        """Acknowledge an alert in OpsGenie.

        Args:
            alert_id: Alert ID or alias
            message: Optional acknowledgment note

        Returns:
            Response with updated status
        """
        url = f"{self.alerts_url}/{alert_id}/acknowledge"
        params = {"identifierType": "alias"}

        payload: dict[str, Any] = {}
        if message:
            payload["note"] = message

        logger.info("acknowledging_opsgenie_alert", alias=alert_id)

        try:
            response = await self.http_client.post(
                url,
                params=params,
                json=payload,
            )

            if response.status_code in (200, 202):
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
            logger.exception("opsgenie_acknowledge_exception", error=str(e))
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
        """Close/resolve an alert in OpsGenie.

        Args:
            alert_id: Alert ID or alias
            message: Optional resolution note
            dedup_key: Alternative alias (if alert_id not provided)

        Returns:
            Response with updated status
        """
        key = dedup_key or alert_id
        url = f"{self.alerts_url}/{key}/close"
        params = {"identifierType": "alias"}

        payload: dict[str, Any] = {}
        if message:
            payload["note"] = message

        logger.info("resolving_opsgenie_alert", alias=key)

        try:
            response = await self.http_client.post(
                url,
                params=params,
                json=payload,
            )

            if response.status_code in (200, 202):
                return AlertResponse(
                    success=True,
                    alert_id=key,
                    message="Alert closed",
                    dedup_key=key,
                    status="closed",
                )
            else:
                return AlertResponse(
                    success=False,
                    alert_id=key,
                    message=f"Failed to close: {response.text}",
                )

        except Exception as e:
            logger.exception("opsgenie_resolve_exception", error=str(e))
            return AlertResponse(
                success=False,
                alert_id=key,
                message=f"Exception closing alert: {str(e)}",
            )

    async def get_alert(self, alert_id: str) -> Optional[dict[str, Any]]:
        """Get alert details from OpsGenie.

        Args:
            alert_id: Alert ID or alias

        Returns:
            Alert details or None if not found
        """
        url = f"{self.alerts_url}/{alert_id}"
        params = {"identifierType": "alias"}

        try:
            response = await self.http_client.get(url, params=params)
            if response.status_code == 200:
                return response.json().get("data")
            return None
        except Exception as e:
            logger.exception("opsgenie_get_alert_exception", error=str(e))
            return None

    async def add_note(self, alert_id: str, note: str) -> AlertResponse:
        """Add a note to an alert in OpsGenie.

        Args:
            alert_id: Alert ID or alias
            note: Note content

        Returns:
            Response indicating success
        """
        url = f"{self.alerts_url}/{alert_id}/notes"
        params = {"identifierType": "alias"}

        payload = {"note": note}

        try:
            response = await self.http_client.post(
                url,
                params=params,
                json=payload,
            )
            if response.status_code in (200, 202):
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
            logger.exception("opsgenie_add_note_exception", error=str(e))
            return AlertResponse(
                success=False,
                alert_id=alert_id,
                message=f"Exception adding note: {str(e)}",
            )

    async def test_connection(self) -> bool:
        """Test connection to OpsGenie API.

        Returns:
            True if connection is successful
        """
        url = f"{self.config.base_url}/v2/heartbeats"

        try:
            response = await self.http_client.get(url)
            return response.status_code == 200
        except Exception as e:
            logger.exception("opsgenie_connection_test_failed", error=str(e))
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
