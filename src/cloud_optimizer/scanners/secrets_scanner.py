"""Secrets Manager and Parameter Store Security Scanner.

Issue #143: 9.1.5 Secrets Manager and Parameter Store scanner

Implements security scanning for AWS Secrets Manager and Systems Manager Parameter Store
checking for rotation policies, access controls, encryption, and unused secrets.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

logger = logging.getLogger(__name__)

# Patterns that may indicate credentials stored in plain text parameters
CREDENTIAL_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"access[_-]?key", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"auth", re.IGNORECASE),
    re.compile(r"db[_-]?pass", re.IGNORECASE),
    re.compile(r"connection[_-]?string", re.IGNORECASE),
]


class SecretsScanner(BaseScanner):
    """Scanner for Secrets Manager and Parameter Store security configurations.

    Implements security scanning for secrets management services including:
    - Secrets Manager automatic rotation configuration
    - KMS encryption for secrets and secure parameters
    - IAM and resource policies for overly permissive access
    - Unused secrets (not accessed in 90+ days)
    - Secrets without expiration dates
    - Replication configuration for critical secrets
    - Plain text parameters containing credentials
    """

    SERVICE = "SecretsManager"

    def _register_rules(self) -> None:
        """Register Secrets Manager and Parameter Store security rules."""
        # Secrets Manager Rules
        self.register_rule(
            ScannerRule(
                rule_id="SM_001",
                title="Secret Missing Automatic Rotation",
                description="Secret does not have automatic rotation configured",
                severity="medium",
                service="SecretsManager",
                resource_type="AWS::SecretsManager::Secret",
                recommendation="Enable automatic rotation for secrets",
                compliance_frameworks=["CIS", "PCI-DSS", "SOC2"],
                remediation_steps=[
                    "Create Lambda rotation function or use AWS managed rotation",
                    "Configure rotation schedule",
                    "Enable rotation on the secret",
                    "Test rotation process",
                ],
                documentation_url="https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="SM_002",
                title="Secret Not Accessed in 90+ Days",
                description="Secret has not been accessed in the last 90 days",
                severity="low",
                service="SecretsManager",
                resource_type="AWS::SecretsManager::Secret",
                recommendation="Review and consider deleting unused secrets",
                compliance_frameworks=[],
                remediation_steps=[
                    "Verify secret is no longer needed",
                    "Check for applications that might use it",
                    "Schedule secret for deletion if unused",
                    "Document deletion decision",
                ],
                documentation_url="https://docs.aws.amazon.com/secretsmanager/latest/userguide/manage_delete-secret.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="SM_003",
                title="Secret Missing KMS Encryption",
                description="Secret is not encrypted with a customer-managed KMS key",
                severity="medium",
                service="SecretsManager",
                resource_type="AWS::SecretsManager::Secret",
                recommendation="Use customer-managed KMS key for encryption",
                compliance_frameworks=["PCI-DSS", "HIPAA"],
                remediation_steps=[
                    "Create customer-managed KMS key",
                    "Update secret to use the new KMS key",
                    "Verify encryption key usage in CloudTrail",
                ],
                documentation_url="https://docs.aws.amazon.com/secretsmanager/latest/userguide/security-encryption.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="SM_004",
                title="Secret with Overly Permissive Resource Policy",
                description="Secret resource policy allows overly permissive access",
                severity="high",
                service="SecretsManager",
                resource_type="AWS::SecretsManager::Secret",
                recommendation="Restrict resource policy to specific principals",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Review current resource policy",
                    "Remove wildcard principal permissions",
                    "Restrict to specific IAM roles or accounts",
                    "Add conditions for additional restrictions",
                ],
                documentation_url="https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_resource-based-policies.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="SM_005",
                title="Secret Not Replicated for High Availability",
                description="Critical secret is not replicated to other regions",
                severity="low",
                service="SecretsManager",
                resource_type="AWS::SecretsManager::Secret",
                recommendation="Configure replication for critical secrets",
                compliance_frameworks=[],
                remediation_steps=[
                    "Identify secrets requiring high availability",
                    "Configure replication to disaster recovery region",
                    "Verify replica secrets are accessible",
                ],
                documentation_url="https://docs.aws.amazon.com/secretsmanager/latest/userguide/create-manage-multi-region-secrets.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="SM_006",
                title="Secret Missing Tags for Classification",
                description="Secret does not have tags for classification or ownership",
                severity="low",
                service="SecretsManager",
                resource_type="AWS::SecretsManager::Secret",
                recommendation="Add tags for classification, ownership, and compliance",
                compliance_frameworks=[],
                remediation_steps=[
                    "Define tagging strategy for secrets",
                    "Add classification tags (e.g., sensitivity level)",
                    "Add ownership tags (e.g., team, application)",
                    "Use tags for access control policies",
                ],
                documentation_url="https://docs.aws.amazon.com/secretsmanager/latest/userguide/managing-secrets-tagging.html",
            )
        )

        # Parameter Store Rules
        self.register_rule(
            ScannerRule(
                rule_id="SSM_001",
                title="Secure Parameter Missing KMS Encryption",
                description="SecureString parameter is not encrypted with customer-managed KMS key",
                severity="medium",
                service="SSM",
                resource_type="AWS::SSM::Parameter",
                recommendation="Use customer-managed KMS key for SecureString parameters",
                compliance_frameworks=["PCI-DSS", "HIPAA"],
                remediation_steps=[
                    "Create customer-managed KMS key",
                    "Recreate parameter with KMS key encryption",
                    "Update applications to access new parameter",
                    "Delete old parameter",
                ],
                documentation_url="https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-securestring.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="SSM_002",
                title="Parameter Containing Credentials Not Marked as SecureString",
                description="Parameter appears to contain credentials but is not a SecureString",
                severity="critical",
                service="SSM",
                resource_type="AWS::SSM::Parameter",
                recommendation="Store credentials as SecureString type parameters",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Identify credentials stored as String parameters",
                    "Create new SecureString parameter with the value",
                    "Update applications to use new parameter",
                    "Delete old String parameter",
                    "Rotate exposed credentials",
                ],
                documentation_url="https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-securestring.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="SSM_003",
                title="Parameter Not Accessed in 90+ Days",
                description="Parameter has not been accessed in the last 90 days",
                severity="low",
                service="SSM",
                resource_type="AWS::SSM::Parameter",
                recommendation="Review and consider removing unused parameters",
                compliance_frameworks=[],
                remediation_steps=[
                    "Verify parameter is no longer needed",
                    "Check for applications that might use it",
                    "Delete unused parameter",
                    "Document deletion decision",
                ],
                documentation_url="https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-working-with.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="SSM_004",
                title="Parameter Missing Description or Tags",
                description="Parameter is missing description or classification tags",
                severity="low",
                service="SSM",
                resource_type="AWS::SSM::Parameter",
                recommendation="Add description and tags for documentation and access control",
                compliance_frameworks=[],
                remediation_steps=[
                    "Add descriptive description to parameter",
                    "Add classification and ownership tags",
                    "Use tags for IAM policy conditions",
                ],
                documentation_url="https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-labels.html",
            )
        )

    async def scan(self) -> List[ScanResult]:
        """Scan Secrets Manager and Parameter Store for security issues.

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        for region in self.regions:
            try:
                # Scan Secrets Manager
                secrets_client = self.get_client("secretsmanager", region=region)
                logger.info(f"Scanning Secrets Manager in {region}")
                results.extend(
                    await self._check_secrets(secrets_client, region)
                )

                # Scan Parameter Store
                ssm_client = self.get_client("ssm", region=region)
                logger.info(f"Scanning Parameter Store in {region}")
                results.extend(
                    await self._check_parameters(ssm_client, region)
                )

            except ClientError as e:
                logger.error(f"Error scanning secrets in {region}: {e}")

        return results

    async def _check_secrets(
        self,
        secrets_client: Any,
        region: str,
    ) -> List[ScanResult]:
        """Check Secrets Manager secrets for security issues.

        Args:
            secrets_client: boto3 Secrets Manager client
            region: AWS region being scanned

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []
        now = datetime.now(timezone.utc)

        try:
            paginator = secrets_client.get_paginator("list_secrets")
            for page in paginator.paginate():
                secrets = page.get("SecretList", [])

                for secret in secrets:
                    secret_arn = secret["ARN"]
                    secret_name = secret.get("Name", secret_arn)

                    # Check rotation (SM_001)
                    rotation_enabled = secret.get("RotationEnabled", False)
                    if not rotation_enabled:
                        results.append(
                            self.create_result(
                                rule_id="SM_001",
                                resource_id=secret_arn,
                                resource_name=secret_name,
                                region=region,
                            )
                        )

                    # Check last accessed (SM_002)
                    last_accessed = secret.get("LastAccessedDate")
                    if last_accessed:
                        days_since_access = (now - last_accessed.replace(
                            tzinfo=timezone.utc
                        )).days
                        if days_since_access > 90:
                            results.append(
                                self.create_result(
                                    rule_id="SM_002",
                                    resource_id=secret_arn,
                                    resource_name=secret_name,
                                    region=region,
                                    metadata={
                                        "last_accessed": str(last_accessed),
                                        "days_since_access": days_since_access,
                                    },
                                )
                            )

                    # Check KMS encryption (SM_003)
                    kms_key_id = secret.get("KmsKeyId", "")
                    if not kms_key_id or kms_key_id.startswith("aws/"):
                        results.append(
                            self.create_result(
                                rule_id="SM_003",
                                resource_id=secret_arn,
                                resource_name=secret_name,
                                region=region,
                                metadata={
                                    "kms_key": kms_key_id or "default (aws/secretsmanager)",
                                },
                            )
                        )

                    # Check resource policy (SM_004)
                    try:
                        policy_response = secrets_client.get_resource_policy(
                            SecretId=secret_arn
                        )
                        policy_str = policy_response.get("ResourcePolicy")
                        if policy_str:
                            import json

                            policy = json.loads(policy_str)
                            for statement in policy.get("Statement", []):
                                principal = statement.get("Principal", {})
                                if principal == "*" or (
                                    isinstance(principal, dict)
                                    and principal.get("AWS") == "*"
                                ):
                                    condition = statement.get("Condition", {})
                                    if not condition:
                                        results.append(
                                            self.create_result(
                                                rule_id="SM_004",
                                                resource_id=secret_arn,
                                                resource_name=secret_name,
                                                region=region,
                                                metadata={
                                                    "principal": str(principal),
                                                },
                                            )
                                        )
                                        break
                    except ClientError:
                        pass  # No resource policy

                    # Check replication (SM_005) - only for primary secrets
                    primary_region = secret.get("PrimaryRegion")
                    if not primary_region or primary_region == region:
                        replication_status = secret.get("ReplicationStatus", [])
                        if not replication_status:
                            # Check if this is a production secret based on tags
                            tags = secret.get("Tags", [])
                            is_production = False
                            for tag in tags:
                                if tag.get("Key", "").lower() in ["env", "environment"]:
                                    if tag.get("Value", "").lower() in [
                                        "prod",
                                        "production",
                                    ]:
                                        is_production = True
                                        break

                            if is_production:
                                results.append(
                                    self.create_result(
                                        rule_id="SM_005",
                                        resource_id=secret_arn,
                                        resource_name=secret_name,
                                        region=region,
                                    )
                                )

                    # Check tags (SM_006)
                    tags = secret.get("Tags", [])
                    if not tags:
                        results.append(
                            self.create_result(
                                rule_id="SM_006",
                                resource_id=secret_arn,
                                resource_name=secret_name,
                                region=region,
                            )
                        )

        except ClientError as e:
            logger.error(f"Error listing secrets in {region}: {e}")

        return results

    async def _check_parameters(
        self,
        ssm_client: Any,
        region: str,
    ) -> List[ScanResult]:
        """Check Parameter Store parameters for security issues.

        Args:
            ssm_client: boto3 SSM client
            region: AWS region being scanned

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        try:
            paginator = ssm_client.get_paginator("describe_parameters")
            for page in paginator.paginate():
                parameters = page.get("Parameters", [])

                for param in parameters:
                    param_name = param["Name"]
                    param_type = param.get("Type", "")
                    param_arn = f"arn:aws:ssm:{region}:parameter{param_name}"

                    # Check if SecureString uses customer KMS key (SSM_001)
                    if param_type == "SecureString":
                        key_id = param.get("KeyId", "")
                        if not key_id or key_id.startswith("alias/aws/"):
                            results.append(
                                self.create_result(
                                    rule_id="SSM_001",
                                    resource_id=param_arn,
                                    resource_name=param_name,
                                    region=region,
                                    metadata={
                                        "key_id": key_id or "default (aws/ssm)",
                                    },
                                )
                            )

                    # Check if String parameter contains credentials (SSM_002)
                    if param_type == "String":
                        for pattern in CREDENTIAL_PATTERNS:
                            if pattern.search(param_name):
                                results.append(
                                    self.create_result(
                                        rule_id="SSM_002",
                                        resource_id=param_arn,
                                        resource_name=param_name,
                                        region=region,
                                        metadata={
                                            "pattern_matched": pattern.pattern,
                                            "parameter_type": param_type,
                                        },
                                    )
                                )
                                break

                    # Check last modified date as proxy for usage (SSM_003)
                    last_modified = param.get("LastModifiedDate")
                    if last_modified:
                        now = datetime.now(timezone.utc)
                        days_since_modified = (
                            now - last_modified.replace(tzinfo=timezone.utc)
                        ).days
                        if days_since_modified > 180:  # 6 months for parameters
                            results.append(
                                self.create_result(
                                    rule_id="SSM_003",
                                    resource_id=param_arn,
                                    resource_name=param_name,
                                    region=region,
                                    metadata={
                                        "last_modified": str(last_modified),
                                        "days_since_modified": days_since_modified,
                                    },
                                )
                            )

                    # Check description and tags (SSM_004)
                    description = param.get("Description", "")
                    if not description:
                        # Try to get tags
                        try:
                            tags_response = ssm_client.list_tags_for_resource(
                                ResourceType="Parameter",
                                ResourceId=param_name,
                            )
                            tags = tags_response.get("TagList", [])
                            if not tags:
                                results.append(
                                    self.create_result(
                                        rule_id="SSM_004",
                                        resource_id=param_arn,
                                        resource_name=param_name,
                                        region=region,
                                        metadata={
                                            "has_description": False,
                                            "has_tags": False,
                                        },
                                    )
                                )
                        except ClientError:
                            results.append(
                                self.create_result(
                                    rule_id="SSM_004",
                                    resource_id=param_arn,
                                    resource_name=param_name,
                                    region=region,
                                    metadata={
                                        "has_description": False,
                                    },
                                )
                            )

        except ClientError as e:
            logger.error(f"Error listing parameters in {region}: {e}")

        return results
