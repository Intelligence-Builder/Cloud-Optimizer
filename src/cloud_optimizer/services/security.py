"""Security scanning service for Cloud Optimizer."""

import logging
from typing import Any, Dict, List, Optional

from cloud_optimizer.integrations.aws.encryption import EncryptionScanner
from cloud_optimizer.integrations.aws.iam import IAMScanner
from cloud_optimizer.integrations.aws.security_groups import SecurityGroupScanner
from cloud_optimizer.services.intelligence_builder import IntelligenceBuilderService

logger = logging.getLogger(__name__)


class SecurityService:
    """
    Security scanning service using Intelligence-Builder platform.

    This service orchestrates AWS security scans and manages findings
    through the IB SDK. It does NOT implement graph operations directly.
    """

    def __init__(self, ib_service: Optional[IntelligenceBuilderService] = None) -> None:
        """
        Initialize security service.

        Args:
            ib_service: Intelligence-Builder service (injected dependency)
        """
        self.ib_service = ib_service
        self._scanners: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)

    def _get_scanner(self, scan_type: str, region: str) -> Any:
        """
        Get or create a scanner instance.

        Args:
            scan_type: Type of scan (security_groups, iam, encryption)
            region: AWS region

        Returns:
            Scanner instance
        """
        cache_key = f"{scan_type}:{region}"
        if cache_key not in self._scanners:
            if scan_type == "security_groups":
                self._scanners[cache_key] = SecurityGroupScanner(region=region)
            elif scan_type == "iam":
                self._scanners[cache_key] = IAMScanner(region=region)
            elif scan_type == "encryption":
                self._scanners[cache_key] = EncryptionScanner(region=region)
            else:
                raise ValueError(f"Unknown scan type: {scan_type}")

        return self._scanners[cache_key]

    async def scan_account(
        self,
        aws_account_id: str,
        scan_types: Optional[List[str]] = None,
        region: str = "us-east-1",
    ) -> Dict[str, int]:
        """
        Perform comprehensive security scan of AWS account.

        Args:
            aws_account_id: AWS account ID to scan
            scan_types: Optional list of scan types (default: all)
            region: AWS region to scan

        Returns:
            Dictionary with finding counts by scan type

        Example:
            >>> service = SecurityService()
            >>> results = await service.scan_account("123456789012")
            >>> print(results)
            {"security_groups": 5, "iam": 3, "encryption": 2}
        """
        scan_types = scan_types or ["security_groups", "iam", "encryption"]
        results: Dict[str, int] = {}

        self.logger.info(
            f"Starting security scan for account {aws_account_id}",
            extra={
                "account_id": aws_account_id,
                "scan_types": scan_types,
                "region": region,
            },
        )

        for scan_type in scan_types:
            findings = await self._run_scan(scan_type, aws_account_id, region)
            results[scan_type] = len(findings)

            # Push findings to IB if service is available
            if self.ib_service and self.ib_service.is_connected:
                await self._persist_findings(findings)

        self.logger.info(
            f"Security scan complete for account {aws_account_id}",
            extra={"results": results},
        )

        return results

    async def _run_scan(
        self, scan_type: str, account_id: str, region: str
    ) -> List[Dict[str, Any]]:
        """
        Run a specific type of scan.

        Args:
            scan_type: Type of scan to run
            account_id: AWS account ID
            region: AWS region

        Returns:
            List of findings from the scan
        """
        self.logger.info(f"Running {scan_type} scan for account {account_id}")

        try:
            scanner = self._get_scanner(scan_type, region)
            findings = await scanner.scan(account_id)

            self.logger.info(
                f"{scan_type} scan complete: {len(findings)} findings",
                extra={
                    "scan_type": scan_type,
                    "account_id": account_id,
                    "findings_count": len(findings),
                },
            )

            return findings

        except Exception as e:
            self.logger.error(
                f"{scan_type} scan failed: {e}",
                exc_info=True,
                extra={"scan_type": scan_type, "account_id": account_id},
            )
            raise

    async def _persist_findings(self, findings: List[Dict[str, Any]]) -> None:
        """
        Persist findings to Intelligence-Builder platform.

        Args:
            findings: List of findings to persist
        """
        if not self.ib_service:
            self.logger.warning("IB service not available, skipping persistence")
            return

        try:
            for finding in findings:
                # Create entity in IB
                entity_data = {
                    "entity_type": "security_finding",
                    "name": finding["title"],
                    "metadata": {
                        "finding_type": finding["finding_type"],
                        "severity": finding["severity"],
                        "description": finding["description"],
                        "resource_arn": finding["resource_arn"],
                        "resource_type": finding["resource_type"],
                        "aws_account_id": finding["aws_account_id"],
                        "region": finding["region"],
                        "remediation": finding["remediation"],
                        "metadata": finding.get("metadata", {}),
                    },
                }
                await self.ib_service.create_entity(entity_data)

        except Exception as e:
            self.logger.error(f"Failed to persist findings to IB: {e}", exc_info=True)

    async def get_findings(
        self,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get security findings from Intelligence-Builder.

        Args:
            severity: Optional severity filter (low, medium, high, critical)
            limit: Maximum number of findings to return

        Returns:
            List of security findings
        """
        if not self.ib_service or not self.ib_service.is_connected:
            self.logger.warning("IB service not available")
            return []

        try:
            filters = {}
            if severity:
                filters["severity"] = severity

            result = await self.ib_service.query_entities(
                entity_type="security_finding",
                filters=filters,
                limit=limit,
            )

            findings = result.get("entities", [])
            self.logger.info(
                f"Retrieved {len(findings)} findings from IB",
                extra={"severity": severity, "count": len(findings)},
            )

            return findings

        except Exception as e:
            self.logger.error(
                f"Failed to retrieve findings from IB: {e}", exc_info=True
            )
            return []

    async def get_finding_stats(self) -> Dict[str, Any]:
        """
        Get statistics about security findings.

        Returns:
            Dictionary with finding statistics
        """
        if not self.ib_service or not self.ib_service.is_connected:
            return {
                "total": 0,
                "by_severity": {},
                "by_type": {},
                "ib_available": False,
            }

        try:
            # Get all findings
            result = await self.ib_service.query_entities(
                entity_type="security_finding",
                limit=1000,
            )

            findings = result.get("entities", [])

            # Calculate stats
            by_severity: Dict[str, int] = {}
            by_type: Dict[str, int] = {}

            for finding in findings:
                metadata = finding.get("metadata", {})
                severity = metadata.get("severity", "unknown")
                finding_type = metadata.get("finding_type", "unknown")

                by_severity[severity] = by_severity.get(severity, 0) + 1
                by_type[finding_type] = by_type.get(finding_type, 0) + 1

            return {
                "total": len(findings),
                "by_severity": by_severity,
                "by_type": by_type,
                "ib_available": True,
            }

        except Exception as e:
            self.logger.error(f"Failed to get finding stats: {e}", exc_info=True)
            return {
                "total": 0,
                "by_severity": {},
                "by_type": {},
                "ib_available": False,
                "error": str(e),
            }
