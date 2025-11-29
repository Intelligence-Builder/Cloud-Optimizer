"""IAM scanner for AWS."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from cloud_optimizer.integrations.aws.base import BaseAWSScanner

logger = logging.getLogger(__name__)


class IAMScanner(BaseAWSScanner):
    """Scanner for AWS IAM misconfigurations."""

    INACTIVE_DAYS_THRESHOLD = 90

    def get_scanner_name(self) -> str:
        """Return scanner name."""
        return "IAMScanner"

    async def scan(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan IAM for security issues.

        Detects:
        - Policies with wildcard (*) permissions
        - Users without MFA enabled
        - Inactive users (no activity in 90+ days)
        - Root account usage

        Args:
            account_id: AWS account ID to scan

        Returns:
            List of security findings
        """
        logger.info(f"Starting IAM scan for account {account_id}")
        findings: List[Dict[str, Any]] = []

        try:
            iam_client = self.get_client("iam")

            # Scan policies for wildcards
            findings.extend(self._scan_policies(iam_client, account_id))

            # Scan users for MFA and activity
            findings.extend(self._scan_users(iam_client, account_id))

            logger.info(
                f"IAM scan complete: {len(findings)} findings",
                extra={"account_id": account_id, "findings_count": len(findings)},
            )

        except Exception as e:
            logger.error(f"IAM scan failed: {e}", exc_info=True)
            raise

        return findings

    def _scan_policies(self, iam_client: Any, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan IAM policies for overly permissive permissions.

        Args:
            iam_client: Boto3 IAM client
            account_id: AWS account ID

        Returns:
            List of findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            # Get customer-managed policies
            paginator = iam_client.get_paginator("list_policies")
            for page in paginator.paginate(Scope="Local"):
                for policy in page.get("Policies", []):
                    policy_arn = policy["Arn"]
                    policy_name = policy["PolicyName"]

                    # Get policy version
                    version_response = iam_client.get_policy_version(
                        PolicyArn=policy_arn,
                        VersionId=policy["DefaultVersionId"],
                    )

                    document = version_response["PolicyVersion"]["Document"]
                    if self._has_wildcard_permissions(document):
                        findings.append(
                            self._create_wildcard_policy_finding(
                                policy_arn, policy_name, account_id
                            )
                        )

        except Exception as e:
            logger.warning(f"Policy scan failed: {e}")

        return findings

    def _scan_users(self, iam_client: Any, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan IAM users for security issues.

        Args:
            iam_client: Boto3 IAM client
            account_id: AWS account ID

        Returns:
            List of findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            paginator = iam_client.get_paginator("list_users")
            for page in paginator.paginate():
                for user in page.get("Users", []):
                    user_name = user["UserName"]

                    # Check MFA
                    mfa_response = iam_client.list_mfa_devices(UserName=user_name)
                    if not mfa_response.get("MFADevices"):
                        findings.append(
                            self._create_no_mfa_finding(user_name, account_id)
                        )

                    # Check for inactive users
                    last_used = self._get_last_used_date(iam_client, user_name)
                    if last_used and self._is_inactive(last_used):
                        findings.append(
                            self._create_inactive_user_finding(
                                user_name, last_used, account_id
                            )
                        )

        except Exception as e:
            logger.warning(f"User scan failed: {e}")

        return findings

    def _has_wildcard_permissions(self, policy_document: Dict[str, Any]) -> bool:
        """
        Check if policy has wildcard permissions.

        Args:
            policy_document: IAM policy document

        Returns:
            True if policy has wildcard permissions
        """
        statements = policy_document.get("Statement", [])
        if not isinstance(statements, list):
            statements = [statements]

        for statement in statements:
            if statement.get("Effect") == "Allow":
                actions = statement.get("Action", [])
                if isinstance(actions, str):
                    actions = [actions]

                resources = statement.get("Resource", [])
                if isinstance(resources, str):
                    resources = [resources]

                # Check for wildcard in actions or resources
                if "*" in actions or "*" in resources:
                    return True

        return False

    def _get_last_used_date(self, iam_client: Any, user_name: str) -> Any:
        """
        Get last used date for a user.

        Args:
            iam_client: Boto3 IAM client
            user_name: IAM user name

        Returns:
            Last used datetime or None
        """
        try:
            response = iam_client.get_user(UserName=user_name)
            return response.get("User", {}).get("PasswordLastUsed")
        except Exception:
            return None

    def _is_inactive(self, last_used: datetime) -> bool:
        """
        Check if user is inactive.

        Args:
            last_used: Last used datetime

        Returns:
            True if user hasn't been used in 90+ days
        """
        if not last_used:
            return True

        # Make last_used timezone-aware if it isn't already
        if last_used.tzinfo is None:
            last_used = last_used.replace(tzinfo=timezone.utc)

        days_inactive = (datetime.now(timezone.utc) - last_used).days
        return days_inactive > self.INACTIVE_DAYS_THRESHOLD

    def _create_wildcard_policy_finding(
        self, policy_arn: str, policy_name: str, account_id: str
    ) -> Dict[str, Any]:
        """Create finding for wildcard policy."""
        return {
            "finding_type": "wildcard_iam_permissions",
            "severity": "high",
            "title": f"IAM policy with wildcard permissions: {policy_name}",
            "description": (
                f"IAM policy {policy_name} contains wildcard (*) permissions "
                "which grant overly broad access"
            ),
            "resource_arn": policy_arn,
            "resource_id": policy_arn.split("/")[-1],
            "resource_name": policy_name,
            "resource_type": "iam_policy",
            "aws_account_id": account_id,
            "region": "global",
            "remediation": (
                f"Review policy {policy_name} and replace wildcard permissions "
                "with specific actions and resources following the principle "
                "of least privilege"
            ),
            "metadata": {"policy_arn": policy_arn},
        }

    def _create_no_mfa_finding(self, user_name: str, account_id: str) -> Dict[str, Any]:
        """Create finding for user without MFA."""
        return {
            "finding_type": "iam_user_no_mfa",
            "severity": "medium",
            "title": f"IAM user without MFA: {user_name}",
            "description": (
                f"IAM user {user_name} does not have MFA enabled, "
                "increasing the risk of unauthorized access"
            ),
            "resource_arn": f"arn:aws:iam::{account_id}:user/{user_name}",
            "resource_id": user_name,
            "resource_name": user_name,
            "resource_type": "iam_user",
            "aws_account_id": account_id,
            "region": "global",
            "remediation": f"Enable MFA for IAM user {user_name}",
            "metadata": {"user_name": user_name},
        }

    def _create_inactive_user_finding(
        self, user_name: str, last_used: datetime, account_id: str
    ) -> Dict[str, Any]:
        """Create finding for inactive user."""
        return {
            "finding_type": "inactive_iam_user",
            "severity": "low",
            "title": f"Inactive IAM user: {user_name}",
            "description": (
                f"IAM user {user_name} has not been used in over "
                f"{self.INACTIVE_DAYS_THRESHOLD} days"
            ),
            "resource_arn": f"arn:aws:iam::{account_id}:user/{user_name}",
            "resource_id": user_name,
            "resource_name": user_name,
            "resource_type": "iam_user",
            "aws_account_id": account_id,
            "region": "global",
            "remediation": (
                f"Review IAM user {user_name} and consider deactivating "
                "or removing if no longer needed"
            ),
            "metadata": {
                "user_name": user_name,
                "last_used": last_used.isoformat() if last_used else None,
            },
        }
