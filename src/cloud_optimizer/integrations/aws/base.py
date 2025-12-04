"""Base AWS scanner for Cloud Optimizer."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config

from cloud_optimizer.config import get_settings

logger = logging.getLogger(__name__)


class BaseAWSScanner(ABC):
    """Abstract base class for AWS resource scanners."""

    def __init__(
        self,
        region: Optional[str] = None,
        session: Optional[boto3.Session] = None,
    ) -> None:
        """
        Initialize AWS scanner.

        Args:
            region: AWS region to scan (defaults to settings.aws_default_region)
            session: Optional boto3 session (useful for per-account scans)
        """
        settings = get_settings()
        self.region = region or settings.aws_default_region
        self._session: Optional[boto3.Session] = session

    @property
    def session(self) -> boto3.Session:
        """
        Get or create boto3 session.

        Returns:
            Boto3 session configured with credentials from settings
        """
        if self._session is None:
            settings = get_settings()
            self._session = boto3.Session(
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                aws_session_token=settings.aws_session_token,
                region_name=self.region,
            )
        return self._session

    def get_client(self, service_name: str) -> Any:
        """
        Get boto3 client for a service.

        Args:
            service_name: AWS service name (e.g., 'ec2', 'iam', 's3')

        Returns:
            Configured boto3 client for the service
        """
        config = Config(retries={"max_attempts": 3, "mode": "adaptive"})
        return self.session.client(service_name, config=config)

    @abstractmethod
    async def scan(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan AWS resources and return findings.

        Args:
            account_id: AWS account ID to scan

        Returns:
            List of security findings as dictionaries
        """
        pass

    @abstractmethod
    def get_scanner_name(self) -> str:
        """
        Return scanner name for logging.

        Returns:
            Human-readable scanner name
        """
        pass
