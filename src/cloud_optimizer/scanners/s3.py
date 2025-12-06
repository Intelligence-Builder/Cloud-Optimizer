"""S3 Security Scanner."""

import logging
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

logger = logging.getLogger(__name__)


class S3Scanner(BaseScanner):
    """Scanner for S3 bucket security configurations."""

    SERVICE = "S3"

    def _register_rules(self) -> None:
        """Register S3 security rules."""
        self.register_rule(
            ScannerRule(
                rule_id="S3_001",
                title="S3 Bucket Has Public Access",
                description="S3 bucket allows public access which could expose sensitive data",
                severity="critical",
                service="S3",
                resource_type="AWS::S3::Bucket",
                recommendation="Block all public access using S3 Block Public Access settings",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Enable 'Block all public access' in bucket settings",
                    "Review bucket policy for Principal: '*'",
                    "Review bucket ACL for public grants",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="S3_002",
                title="S3 Bucket Encryption Not Enabled",
                description="S3 bucket does not have default encryption enabled",
                severity="high",
                service="S3",
                resource_type="AWS::S3::Bucket",
                recommendation="Enable default encryption using SSE-S3 or SSE-KMS",
                compliance_frameworks=["PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Enable default encryption (SSE-S3 or SSE-KMS)",
                    "For PHI/PCI data, use SSE-KMS with customer managed keys",
                    "Verify encryption is applied to existing objects",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="S3_003",
                title="S3 Bucket Versioning Disabled",
                description="S3 bucket does not have versioning enabled",
                severity="medium",
                service="S3",
                resource_type="AWS::S3::Bucket",
                recommendation="Enable versioning to protect against accidental deletion",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Enable versioning in bucket configuration",
                    "Configure lifecycle policies to manage old versions",
                    "Consider MFA Delete for additional protection",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="S3_004",
                title="S3 Bucket Access Logging Disabled",
                description="S3 bucket does not have access logging enabled",
                severity="medium",
                service="S3",
                resource_type="AWS::S3::Bucket",
                recommendation="Enable access logging for audit and compliance purposes",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Enable server access logging",
                    "Configure a separate logging bucket",
                    "Set up log analysis and monitoring",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="S3_005",
                title="S3 Bucket Lifecycle Policy Not Configured",
                description="S3 bucket does not have a lifecycle policy to manage object lifecycle",
                severity="low",
                service="S3",
                resource_type="AWS::S3::Bucket",
                recommendation="Configure lifecycle policies to optimize storage costs",
                compliance_frameworks=[],
                remediation_steps=[
                    "Define lifecycle rules for object transitions",
                    "Configure automatic deletion of old versions",
                    "Set up intelligent-tiering for cost optimization",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html",
            )
        )

    async def scan(self) -> List[ScanResult]:
        """
        Scan S3 buckets for security issues.

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []
        s3 = self.get_client("s3")

        try:
            # List all buckets (S3 is global)
            response = s3.list_buckets()
            buckets = response.get("Buckets", [])

            logger.info(f"Scanning {len(buckets)} S3 buckets")

            for bucket in buckets:
                bucket_name = bucket["Name"]
                try:
                    # Get bucket region
                    location_response = s3.get_bucket_location(Bucket=bucket_name)
                    region = location_response.get("LocationConstraint") or "us-east-1"

                    # Check each rule
                    results.extend(
                        await self._check_public_access(s3, bucket_name, region)
                    )
                    results.extend(
                        await self._check_encryption(s3, bucket_name, region)
                    )
                    results.extend(
                        await self._check_versioning(s3, bucket_name, region)
                    )
                    results.extend(await self._check_logging(s3, bucket_name, region))
                    results.extend(await self._check_lifecycle(s3, bucket_name, region))

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    if error_code == "AccessDenied":
                        logger.warning(f"Access denied to bucket {bucket_name}")
                    else:
                        logger.error(f"Error scanning bucket {bucket_name}: {e}")

        except ClientError as e:
            logger.error(f"Error listing S3 buckets: {e}")

        return results

    async def _check_public_access(
        self, s3: Any, bucket_name: str, region: str
    ) -> List[ScanResult]:
        """Check S3_001: Public bucket access."""
        results: List[ScanResult] = []

        try:
            response = s3.get_public_access_block(Bucket=bucket_name)
            config = response.get("PublicAccessBlockConfiguration", {})

            # Check if all public access blocks are enabled
            all_blocked = all(
                [
                    config.get("BlockPublicAcls", False),
                    config.get("IgnorePublicAcls", False),
                    config.get("BlockPublicPolicy", False),
                    config.get("RestrictPublicBuckets", False),
                ]
            )

            if not all_blocked:
                results.append(
                    self.create_result(
                        rule_id="S3_001",
                        resource_id=f"arn:aws:s3:::{bucket_name}",
                        resource_name=bucket_name,
                        region=region,
                        metadata={"public_access_config": config},
                    )
                )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchPublicAccessBlockConfiguration":
                # No configuration means public access is allowed
                results.append(
                    self.create_result(
                        rule_id="S3_001",
                        resource_id=f"arn:aws:s3:::{bucket_name}",
                        resource_name=bucket_name,
                        region=region,
                        metadata={"public_access_config": "not_configured"},
                    )
                )

        return results

    async def _check_encryption(
        self, s3: Any, bucket_name: str, region: str
    ) -> List[ScanResult]:
        """Check S3_002: Default encryption."""
        results: List[ScanResult] = []

        try:
            s3.get_bucket_encryption(Bucket=bucket_name)
            # Encryption is configured
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ServerSideEncryptionConfigurationNotFoundError":
                results.append(
                    self.create_result(
                        rule_id="S3_002",
                        resource_id=f"arn:aws:s3:::{bucket_name}",
                        resource_name=bucket_name,
                        region=region,
                    )
                )

        return results

    async def _check_versioning(
        self, s3: Any, bucket_name: str, region: str
    ) -> List[ScanResult]:
        """Check S3_003: Versioning enabled."""
        results: List[ScanResult] = []

        try:
            response = s3.get_bucket_versioning(Bucket=bucket_name)
            status = response.get("Status", "")

            if status != "Enabled":
                results.append(
                    self.create_result(
                        rule_id="S3_003",
                        resource_id=f"arn:aws:s3:::{bucket_name}",
                        resource_name=bucket_name,
                        region=region,
                        metadata={"versioning_status": status or "Disabled"},
                    )
                )

        except ClientError as e:
            logger.error(f"Error checking versioning for {bucket_name}: {e}")

        return results

    async def _check_logging(
        self, s3: Any, bucket_name: str, region: str
    ) -> List[ScanResult]:
        """Check S3_004: Access logging enabled."""
        results: List[ScanResult] = []

        try:
            response = s3.get_bucket_logging(Bucket=bucket_name)
            logging_enabled = "LoggingEnabled" in response

            if not logging_enabled:
                results.append(
                    self.create_result(
                        rule_id="S3_004",
                        resource_id=f"arn:aws:s3:::{bucket_name}",
                        resource_name=bucket_name,
                        region=region,
                    )
                )

        except ClientError as e:
            logger.error(f"Error checking logging for {bucket_name}: {e}")

        return results

    async def _check_lifecycle(
        self, s3: Any, bucket_name: str, region: str
    ) -> List[ScanResult]:
        """Check S3_005: Lifecycle policy configured."""
        results: List[ScanResult] = []

        try:
            s3.get_bucket_lifecycle_configuration(Bucket=bucket_name)
            # Lifecycle policy exists
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchLifecycleConfiguration":
                results.append(
                    self.create_result(
                        rule_id="S3_005",
                        resource_id=f"arn:aws:s3:::{bucket_name}",
                        resource_name=bucket_name,
                        region=region,
                    )
                )

        return results
