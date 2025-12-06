"""IAM Security Scanner."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

logger = logging.getLogger(__name__)


class IAMScanner(BaseScanner):
    """Scanner for IAM security configurations."""

    SERVICE = "IAM"

    def _register_rules(self) -> None:
        """Register IAM security rules."""
        self.register_rule(
            ScannerRule(
                rule_id="IAM_001",
                title="Root Account Has Access Keys",
                description="Root account has active access keys which poses a critical security risk",
                severity="critical",
                service="IAM",
                resource_type="AWS::IAM::User",
                recommendation="Delete root account access keys and use IAM users instead",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Delete all root account access keys",
                    "Use IAM users with appropriate permissions instead",
                    "Enable MFA for root account",
                    "Use root account only for account-level tasks",
                ],
                documentation_url="https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="IAM_002",
                title="MFA Not Enabled for Console Users",
                description="IAM user has console access without MFA enabled",
                severity="high",
                service="IAM",
                resource_type="AWS::IAM::User",
                recommendation="Enable MFA for all users with console access",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Enable virtual MFA device for the user",
                    "Consider using hardware MFA for privileged users",
                    "Enforce MFA through IAM policies",
                ],
                documentation_url="https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="IAM_003",
                title="Password Policy Too Weak",
                description="Account password policy does not meet security best practices",
                severity="medium",
                service="IAM",
                resource_type="AWS::IAM::AccountPasswordPolicy",
                recommendation="Strengthen password policy to require longer, complex passwords",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Require minimum password length of 14 characters",
                    "Require uppercase, lowercase, numbers, and symbols",
                    "Enable password expiration (90 days)",
                    "Prevent password reuse (24 previous passwords)",
                ],
                documentation_url="https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_passwords_account-policy.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="IAM_004",
                title="Unused IAM Credentials",
                description="IAM user has credentials that have not been used in over 90 days",
                severity="medium",
                service="IAM",
                resource_type="AWS::IAM::User",
                recommendation="Disable or remove unused credentials to reduce attack surface",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Deactivate access keys not used in 90 days",
                    "Remove console access for inactive users",
                    "Implement regular credential review process",
                ],
                documentation_url="https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_finding-unused.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="IAM_005",
                title="Overly Permissive IAM Policy",
                description="IAM policy grants overly broad permissions (e.g., Action: '*', Resource: '*')",
                severity="high",
                service="IAM",
                resource_type="AWS::IAM::Policy",
                recommendation="Follow principle of least privilege and restrict permissions",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Review and restrict wildcard permissions",
                    "Use specific actions instead of '*'",
                    "Limit resources to those actually needed",
                    "Implement permission boundaries",
                ],
                documentation_url="https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html",
            )
        )

    async def scan(self) -> List[ScanResult]:
        """
        Scan IAM for security issues.

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []
        iam = self.get_client("iam")

        try:
            # IAM is global, only scan once
            logger.info("Scanning IAM configuration")

            # Check root account
            results.extend(await self._check_root_account(iam))

            # Check password policy
            results.extend(await self._check_password_policy(iam))

            # Check IAM users
            results.extend(await self._check_iam_users(iam))

            # Check IAM policies
            results.extend(await self._check_iam_policies(iam))

        except ClientError as e:
            logger.error(f"Error scanning IAM: {e}")

        return results

    async def _check_root_account(self, iam: Any) -> List[ScanResult]:
        """Check IAM_001: Root account access keys."""
        results: List[ScanResult] = []

        try:
            # Get account summary to check for root access keys
            summary = iam.get_account_summary()
            account_summary = summary.get("SummaryMap", {})

            # Check if root account has access keys
            root_access_keys = account_summary.get("AccountAccessKeysPresent", 0)

            if root_access_keys > 0:
                results.append(
                    self.create_result(
                        rule_id="IAM_001",
                        resource_id="arn:aws:iam::root:user/root",
                        resource_name="root",
                        region="global",
                        metadata={"access_keys_count": root_access_keys},
                    )
                )

        except ClientError as e:
            logger.error(f"Error checking root account: {e}")

        return results

    async def _check_password_policy(self, iam: Any) -> List[ScanResult]:
        """Check IAM_003: Password policy strength."""
        results: List[ScanResult] = []

        try:
            response = iam.get_account_password_policy()
            policy = response.get("PasswordPolicy", {})

            # Check password policy requirements
            issues = []

            if policy.get("MinimumPasswordLength", 0) < 14:
                issues.append("minimum_length_less_than_14")

            if not policy.get("RequireUppercaseCharacters", False):
                issues.append("no_uppercase_required")

            if not policy.get("RequireLowercaseCharacters", False):
                issues.append("no_lowercase_required")

            if not policy.get("RequireNumbers", False):
                issues.append("no_numbers_required")

            if not policy.get("RequireSymbols", False):
                issues.append("no_symbols_required")

            if not policy.get("ExpirePasswords", False):
                issues.append("no_password_expiration")

            if policy.get("PasswordReusePrevention", 0) < 24:
                issues.append("insufficient_password_history")

            if issues:
                results.append(
                    self.create_result(
                        rule_id="IAM_003",
                        resource_id="arn:aws:iam::account:password-policy",
                        resource_name="AccountPasswordPolicy",
                        region="global",
                        metadata={"policy_issues": issues, "current_policy": policy},
                    )
                )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchEntity":
                # No password policy configured
                results.append(
                    self.create_result(
                        rule_id="IAM_003",
                        resource_id="arn:aws:iam::account:password-policy",
                        resource_name="AccountPasswordPolicy",
                        region="global",
                        metadata={"policy_issues": ["no_policy_configured"]},
                    )
                )

        return results

    async def _check_iam_users(self, iam: Any) -> List[ScanResult]:
        """Check IAM_002 and IAM_004: MFA and unused credentials."""
        results: List[ScanResult] = []

        try:
            # List all IAM users
            paginator = iam.get_paginator("list_users")
            for page in paginator.paginate():
                users = page.get("Users", [])

                for user in users:
                    user_name = user["UserName"]
                    user_arn = user["Arn"]

                    # Check MFA (IAM_002)
                    try:
                        mfa_devices = iam.list_mfa_devices(UserName=user_name)
                        has_mfa = len(mfa_devices.get("MFADevices", [])) > 0

                        # Check if user has console access
                        try:
                            login_profile = iam.get_login_profile(UserName=user_name)
                            has_console_access = login_profile is not None

                            if has_console_access and not has_mfa:
                                results.append(
                                    self.create_result(
                                        rule_id="IAM_002",
                                        resource_id=user_arn,
                                        resource_name=user_name,
                                        region="global",
                                    )
                                )

                        except ClientError as e:
                            if (
                                e.response.get("Error", {}).get("Code")
                                != "NoSuchEntity"
                            ):
                                logger.error(
                                    f"Error checking login profile for {user_name}: {e}"
                                )

                    except ClientError as e:
                        logger.error(f"Error checking MFA for {user_name}: {e}")

                    # Check unused credentials (IAM_004)
                    try:
                        # Get credential report for user
                        # Note: This requires generate_credential_report to be called first
                        user_created = user["CreateDate"]
                        days_since_creation = (
                            datetime.now(user_created.tzinfo) - user_created
                        ).days

                        # Get access keys
                        access_keys = iam.list_access_keys(UserName=user_name)
                        for key in access_keys.get("AccessKeyMetadata", []):
                            if key["Status"] == "Active":
                                key_age = (
                                    datetime.now(key["CreateDate"].tzinfo)
                                    - key["CreateDate"]
                                ).days

                                # Check if key is old and potentially unused
                                if key_age > 90:
                                    results.append(
                                        self.create_result(
                                            rule_id="IAM_004",
                                            resource_id=user_arn,
                                            resource_name=user_name,
                                            region="global",
                                            metadata={
                                                "access_key_id": key["AccessKeyId"],
                                                "key_age_days": key_age,
                                            },
                                        )
                                    )

                    except ClientError as e:
                        logger.error(f"Error checking credentials for {user_name}: {e}")

        except ClientError as e:
            logger.error(f"Error listing IAM users: {e}")

        return results

    async def _check_iam_policies(self, iam: Any) -> List[ScanResult]:
        """Check IAM_005: Overly permissive policies."""
        results: List[ScanResult] = []

        try:
            # List customer managed policies
            paginator = iam.get_paginator("list_policies")
            for page in paginator.paginate(Scope="Local"):
                policies = page.get("Policies", [])

                for policy in policies:
                    policy_name = policy["PolicyName"]
                    policy_arn = policy["Arn"]

                    try:
                        # Get policy version
                        policy_version = iam.get_policy_version(
                            PolicyArn=policy_arn, VersionId=policy["DefaultVersionId"]
                        )

                        document = policy_version.get("PolicyVersion", {}).get(
                            "Document", {}
                        )

                        # Check for overly permissive statements
                        if "Statement" in document:
                            for statement in document["Statement"]:
                                if statement.get("Effect") == "Allow":
                                    # Check for wildcard actions
                                    actions = statement.get("Action", [])
                                    if not isinstance(actions, list):
                                        actions = [actions]

                                    # Check for wildcard resources
                                    resources = statement.get("Resource", [])
                                    if not isinstance(resources, list):
                                        resources = [resources]

                                    has_wildcard_action = "*" in actions
                                    has_wildcard_resource = "*" in resources

                                    if has_wildcard_action and has_wildcard_resource:
                                        results.append(
                                            self.create_result(
                                                rule_id="IAM_005",
                                                resource_id=policy_arn,
                                                resource_name=policy_name,
                                                region="global",
                                                metadata={
                                                    "issue": "wildcard_action_and_resource",
                                                    "statement": statement,
                                                },
                                            )
                                        )

                    except ClientError as e:
                        logger.error(f"Error checking policy {policy_name}: {e}")

        except ClientError as e:
            logger.error(f"Error listing IAM policies: {e}")

        return results
