"""Multi-Account Scanning Support.

Issue #147: 9.2.1 Multi-account scanning support

Enables Cloud Optimizer to scan multiple AWS accounts simultaneously with centralized
result aggregation and account relationship management.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from cloud_optimizer.scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)


class AccountStatus(str, Enum):
    """Account connection status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class AuthMethod(str, Enum):
    """Authentication method for accounts."""

    IAM_ROLE = "iam_role"
    ACCESS_KEY = "access_key"
    ASSUME_ROLE = "assume_role"


@dataclass
class AWSAccount:
    """Represents an AWS account configuration.

    Attributes:
        account_id: AWS account ID (12-digit number)
        name: Friendly name for the account
        auth_method: Authentication method to use
        role_arn: IAM role ARN for assume role authentication
        external_id: External ID for assume role (optional)
        access_key_id: Access key ID (for access_key auth)
        secret_access_key: Secret access key (for access_key auth)
        regions: List of regions to scan
        environment: Environment label (prod, staging, dev)
        business_unit: Business unit label
        status: Current account status
        last_scan: Timestamp of last successful scan
        error_message: Last error message if status is ERROR
        tags: Additional metadata tags
    """

    account_id: str
    name: str
    auth_method: AuthMethod = AuthMethod.ASSUME_ROLE
    role_arn: Optional[str] = None
    external_id: Optional[str] = None
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    regions: List[str] = field(default_factory=lambda: ["us-east-1"])
    environment: str = "unknown"
    business_unit: str = "unknown"
    status: AccountStatus = AccountStatus.PENDING
    last_scan: Optional[datetime] = None
    error_message: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate account configuration.

        Returns:
            True if configuration is valid
        """
        if len(self.account_id) != 12 or not self.account_id.isdigit():
            return False

        if self.auth_method == AuthMethod.ASSUME_ROLE and not self.role_arn:
            return False

        if self.auth_method == AuthMethod.ACCESS_KEY:
            if not self.access_key_id or not self.secret_access_key:
                return False

        return True


@dataclass
class AccountScanResult:
    """Results from scanning a single account.

    Attributes:
        account: The account that was scanned
        findings: List of scan findings
        scan_duration: Duration of scan in seconds
        scanners_run: List of scanner names that were executed
        error: Error message if scan failed
    """

    account: AWSAccount
    findings: List[ScanResult] = field(default_factory=list)
    scan_duration: float = 0.0
    scanners_run: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if scan was successful."""
        return self.error is None

    @property
    def finding_count(self) -> int:
        """Get total number of findings."""
        return len(self.findings)

    def findings_by_severity(self) -> Dict[str, int]:
        """Get finding counts by severity."""
        counts: Dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for finding in self.findings:
            # Count findings that didn't pass
            if not finding.passed:
                severity = finding.evidence.get("severity", "medium")
                if severity in counts:
                    counts[severity] += 1
        return counts


class AccountRegistry:
    """Registry for managing AWS accounts.

    Provides CRUD operations for account management and validation.
    """

    def __init__(self) -> None:
        """Initialize account registry."""
        self._accounts: Dict[str, AWSAccount] = {}

    def add_account(self, account: AWSAccount) -> bool:
        """Add an account to the registry.

        Args:
            account: Account to add

        Returns:
            True if account was added successfully
        """
        if not account.validate():
            logger.error(f"Invalid account configuration: {account.account_id}")
            return False

        self._accounts[account.account_id] = account
        logger.info(f"Added account {account.account_id} ({account.name})")
        return True

    def remove_account(self, account_id: str) -> bool:
        """Remove an account from the registry.

        Args:
            account_id: Account ID to remove

        Returns:
            True if account was removed
        """
        if account_id in self._accounts:
            del self._accounts[account_id]
            logger.info(f"Removed account {account_id}")
            return True
        return False

    def get_account(self, account_id: str) -> Optional[AWSAccount]:
        """Get an account by ID.

        Args:
            account_id: Account ID to retrieve

        Returns:
            Account if found, None otherwise
        """
        return self._accounts.get(account_id)

    def list_accounts(
        self,
        environment: Optional[str] = None,
        business_unit: Optional[str] = None,
        status: Optional[AccountStatus] = None,
    ) -> List[AWSAccount]:
        """List accounts with optional filtering.

        Args:
            environment: Filter by environment
            business_unit: Filter by business unit
            status: Filter by status

        Returns:
            List of matching accounts
        """
        accounts = list(self._accounts.values())

        if environment:
            accounts = [a for a in accounts if a.environment == environment]

        if business_unit:
            accounts = [a for a in accounts if a.business_unit == business_unit]

        if status:
            accounts = [a for a in accounts if a.status == status]

        return accounts

    def update_account_status(
        self,
        account_id: str,
        status: AccountStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """Update account status.

        Args:
            account_id: Account ID to update
            status: New status
            error_message: Error message if status is ERROR
        """
        if account_id in self._accounts:
            self._accounts[account_id].status = status
            self._accounts[account_id].error_message = error_message
            if status == AccountStatus.ACTIVE:
                self._accounts[account_id].last_scan = datetime.now(timezone.utc)


class MultiAccountScanner:
    """Orchestrates scanning across multiple AWS accounts.

    Provides concurrent scanning with result aggregation and error handling.
    """

    def __init__(
        self,
        registry: AccountRegistry,
        scanner_classes: List[Type[BaseScanner]],
        max_workers: int = 10,
    ) -> None:
        """Initialize multi-account scanner.

        Args:
            registry: Account registry with accounts to scan
            scanner_classes: List of scanner classes to run
            max_workers: Maximum concurrent account scans
        """
        self.registry = registry
        self.scanner_classes = scanner_classes
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def _get_session_for_account(self, account: AWSAccount) -> Optional[boto3.Session]:
        """Create boto3 session for an account.

        Args:
            account: Account to create session for

        Returns:
            Configured boto3 session or None on error
        """
        try:
            if account.auth_method == AuthMethod.ACCESS_KEY:
                return boto3.Session(
                    aws_access_key_id=account.access_key_id,
                    aws_secret_access_key=account.secret_access_key,
                )

            elif account.auth_method == AuthMethod.ASSUME_ROLE:
                # Use STS to assume role
                sts_client = boto3.client(
                    "sts",
                    config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
                )

                assume_params: Dict[str, Any] = {
                    "RoleArn": account.role_arn,
                    "RoleSessionName": f"CloudOptimizer-{account.account_id}",
                    "DurationSeconds": 3600,  # 1 hour
                }

                if account.external_id:
                    assume_params["ExternalId"] = account.external_id

                response = sts_client.assume_role(**assume_params)
                credentials = response["Credentials"]

                return boto3.Session(
                    aws_access_key_id=credentials["AccessKeyId"],
                    aws_secret_access_key=credentials["SecretAccessKey"],
                    aws_session_token=credentials["SessionToken"],
                )

            else:
                # Use default session (IAM role or instance profile)
                return boto3.Session()

        except ClientError as e:
            logger.error(f"Failed to get session for account {account.account_id}: {e}")
            return None

    async def _scan_account(self, account: AWSAccount) -> AccountScanResult:
        """Scan a single account.

        Args:
            account: Account to scan

        Returns:
            Scan results for the account
        """
        start_time = datetime.now(timezone.utc)
        result = AccountScanResult(account=account)

        try:
            # Get session for account
            session = self._get_session_for_account(account)
            if not session:
                result.error = "Failed to establish session"
                self.registry.update_account_status(
                    account.account_id,
                    AccountStatus.ERROR,
                    result.error,
                )
                return result

            # Verify credentials
            try:
                sts = session.client("sts")
                identity = sts.get_caller_identity()
                logger.info(
                    f"Scanning account {account.account_id} as {identity.get('Arn')}"
                )
            except ClientError as e:
                result.error = f"Credential verification failed: {e}"
                self.registry.update_account_status(
                    account.account_id,
                    AccountStatus.ERROR,
                    result.error,
                )
                return result

            # Run all scanners
            for scanner_class in self.scanner_classes:
                try:
                    scanner = scanner_class(session=session, regions=account.regions)
                    findings = await scanner.scan()

                    # Add account context to findings
                    for finding in findings:
                        finding.evidence["account_id"] = account.account_id
                        finding.evidence["account_name"] = account.name
                        finding.evidence["environment"] = account.environment

                    result.findings.extend(findings)
                    result.scanners_run.append(scanner_class.__name__)

                except Exception as e:
                    logger.error(
                        f"Scanner {scanner_class.__name__} failed for "
                        f"account {account.account_id}: {e}"
                    )

            # Calculate duration
            end_time = datetime.now(timezone.utc)
            result.scan_duration = (end_time - start_time).total_seconds()

            # Update account status
            self.registry.update_account_status(
                account.account_id,
                AccountStatus.ACTIVE,
            )

        except Exception as e:
            result.error = str(e)
            self.registry.update_account_status(
                account.account_id,
                AccountStatus.ERROR,
                result.error,
            )

        return result

    async def scan_all(
        self,
        environment: Optional[str] = None,
        business_unit: Optional[str] = None,
    ) -> List[AccountScanResult]:
        """Scan all accounts (or filtered subset) concurrently.

        Args:
            environment: Filter by environment
            business_unit: Filter by business unit

        Returns:
            List of scan results for all accounts
        """
        accounts = self.registry.list_accounts(
            environment=environment,
            business_unit=business_unit,
            status=AccountStatus.ACTIVE,
        )

        # Also include pending accounts
        accounts.extend(
            self.registry.list_accounts(
                environment=environment,
                business_unit=business_unit,
                status=AccountStatus.PENDING,
            )
        )

        if not accounts:
            logger.warning("No accounts to scan")
            return []

        logger.info(f"Starting scan of {len(accounts)} accounts")

        # Run scans concurrently
        tasks = [self._scan_account(account) for account in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        scan_results: List[AccountScanResult] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Scan failed with exception: {result}")
            elif isinstance(result, AccountScanResult):
                scan_results.append(result)

        # Log summary
        total_findings = sum(r.finding_count for r in scan_results)
        successful = sum(1 for r in scan_results if r.success)
        logger.info(
            f"Scan complete: {successful}/{len(accounts)} accounts successful, "
            f"{total_findings} total findings"
        )

        return scan_results

    def aggregate_results(
        self, results: List[AccountScanResult]
    ) -> Dict[str, Any]:
        """Aggregate results across all accounts.

        Args:
            results: List of account scan results

        Returns:
            Aggregated statistics and findings
        """
        total_findings = 0
        findings_by_severity: Dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        findings_by_account: Dict[str, int] = {}
        findings_by_scanner: Dict[str, int] = {}

        for result in results:
            total_findings += result.finding_count
            findings_by_account[result.account.account_id] = result.finding_count

            # Aggregate by severity
            account_severity = result.findings_by_severity()
            for severity, count in account_severity.items():
                findings_by_severity[severity] += count

            # Aggregate by scanner
            for finding in result.findings:
                scanner = finding.rule_id.split("_")[0]
                findings_by_scanner[scanner] = findings_by_scanner.get(scanner, 0) + 1

        return {
            "total_accounts": len(results),
            "successful_scans": sum(1 for r in results if r.success),
            "failed_scans": sum(1 for r in results if not r.success),
            "total_findings": total_findings,
            "findings_by_severity": findings_by_severity,
            "findings_by_account": findings_by_account,
            "findings_by_scanner": findings_by_scanner,
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        }
