"""Base scanner classes for AWS security scanning."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ScannerRule:
    """Individual security check rule."""

    rule_id: str
    title: str
    description: str
    severity: str  # "critical", "high", "medium", "low"
    service: str
    resource_type: str
    recommendation: str
    compliance_frameworks: List[str] = field(default_factory=list)
    remediation_steps: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None


@dataclass
class ScanResult:
    """Result of scanning a single resource."""

    rule_id: str
    passed: bool
    resource_id: str
    resource_arn: Optional[str] = None
    region: str = "us-east-1"
    evidence: Dict[str, Any] = field(default_factory=dict)
    potential_savings: Optional[float] = None


class BaseScanner(ABC):
    """Abstract base class for service scanners."""

    SERVICE: str = "unknown"

    def __init__(self, session: boto3.Session, regions: Optional[List[str]] = None) -> None:
        """
        Initialize scanner.

        Args:
            session: Boto3 session with AWS credentials
            regions: List of AWS regions to scan (defaults to ["us-east-1"])
        """
        self.session = session
        self.regions = regions or ["us-east-1"]
        self.rules: Dict[str, ScannerRule] = {}
        self._register_rules()

    @abstractmethod
    def _register_rules(self) -> None:
        """Register all security rules for this scanner."""
        pass

    def register_rule(self, rule: ScannerRule) -> None:
        """
        Register a security rule.

        Args:
            rule: ScannerRule to register
        """
        self.rules[rule.rule_id] = rule
        logger.debug(f"Registered rule {rule.rule_id}: {rule.title}")

    def get_client(self, service_name: str, region: Optional[str] = None) -> Any:
        """
        Get boto3 client for a service.

        Args:
            service_name: AWS service name (e.g., 'ec2', 'iam', 's3')
            region: Optional region override

        Returns:
            Configured boto3 client for the service
        """
        config = Config(retries={"max_attempts": 3, "mode": "adaptive"})
        if region:
            return self.session.client(service_name, region_name=region, config=config)
        return self.session.client(service_name, config=config)

    @abstractmethod
    async def scan(self) -> List[ScanResult]:
        """
        Scan AWS resources and return findings.

        Returns:
            List of scan results (findings)
        """
        pass

    def get_rules(self) -> Dict[str, ScannerRule]:
        """Get all registered rules."""
        return self.rules

    def create_result(
        self,
        rule_id: str,
        resource_id: str,
        resource_name: str,
        region: str = "us-east-1",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScanResult:
        """Create a scan result for a rule violation.

        Args:
            rule_id: ID of the violated rule
            resource_id: ARN or ID of the resource
            resource_name: Human-readable resource name
            region: AWS region
            metadata: Additional metadata about the finding

        Returns:
            ScanResult for the finding
        """
        return ScanResult(
            rule_id=rule_id,
            passed=False,
            resource_id=resource_id,
            resource_arn=resource_id if resource_id.startswith("arn:") else None,
            region=region,
            evidence=metadata or {},
        )
