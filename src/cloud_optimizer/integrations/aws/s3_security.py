"""S3 security scanner."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from cloud_optimizer.integrations.aws.base import BaseAWSScanner

logger = logging.getLogger(__name__)


class S3SecurityScanner(BaseAWSScanner):
    """Scanner for S3 public access, logging, and versioning issues."""

    def get_scanner_name(self) -> str:
        """Return scanner name."""
        return "S3SecurityScanner"

    async def scan(self, account_id: str) -> List[Dict[str, Any]]:
        """Scan S3 buckets for common misconfigurations."""
        findings: List[Dict[str, Any]] = []
        s3 = self.get_client("s3")

        try:
            response = s3.list_buckets()
        except ClientError as exc:
            logger.error("Failed to list S3 buckets: %s", exc)
            raise

        for bucket in response.get("Buckets", []):
            bucket_name = bucket["Name"]
            findings.extend(self._check_bucket(bucket_name, account_id, s3))

        return findings

    def _check_bucket(
        self,
        bucket_name: str,
        account_id: str,
        s3_client,
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []

        if self._is_public(bucket_name, s3_client):
            findings.append(
                self._build_finding(
                    bucket_name,
                    account_id,
                    finding_type="s3_public_access",
                    severity="critical",
                    title="S3 bucket allows public access",
                    description=(
                        f"S3 bucket {bucket_name} is publicly accessible. "
                        "Public buckets can expose sensitive data."
                    ),
                    remediation=(
                        "Enable block public access settings, review bucket ACLs, "
                        "and ensure bucket policies restrict access to trusted principals."
                    ),
                )
            )

        if not self._is_versioning_enabled(bucket_name, s3_client):
            findings.append(
                self._build_finding(
                    bucket_name,
                    account_id,
                    finding_type="s3_versioning_disabled",
                    severity="medium",
                    title="S3 bucket versioning disabled",
                    description=(
                        f"S3 bucket {bucket_name} does not have versioning enabled. "
                        "Versioning protects against accidental deletions or overwrites."
                    ),
                    remediation=(
                        "Enable versioning via the S3 console or API to protect "
                        "against accidental object deletions."
                    ),
                )
            )

        if not self._is_logging_enabled(bucket_name, s3_client):
            findings.append(
                self._build_finding(
                    bucket_name,
                    account_id,
                    finding_type="s3_logging_disabled",
                    severity="low",
                    title="S3 bucket does not have access logging enabled",
                    description=(
                        f"S3 bucket {bucket_name} does not record access logs, "
                        "reducing visibility into data access patterns."
                    ),
                    remediation=(
                        "Enable server access logging and send logs to a dedicated "
                        "logging bucket with restricted permissions."
                    ),
                )
            )

        return findings

    def _is_public(self, bucket_name: str, s3_client) -> bool:
        try:
            public_access = s3_client.get_public_access_block(Bucket=bucket_name)
            config = public_access.get("PublicAccessBlockConfiguration", {})
            return not all(
                [
                    config.get("BlockPublicAcls", False),
                    config.get("IgnorePublicAcls", False),
                    config.get("BlockPublicPolicy", False),
                    config.get("RestrictPublicBuckets", False),
                ]
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code == "NoSuchPublicAccessBlockConfiguration":
                return True
            logger.debug(
                "Unable to determine public access for %s: %s", bucket_name, exc
            )
            return False

    def _is_versioning_enabled(self, bucket_name: str, s3_client) -> bool:
        try:
            response = s3_client.get_bucket_versioning(Bucket=bucket_name)
            return response.get("Status") == "Enabled"
        except ClientError as exc:
            logger.debug("Unable to query versioning for %s: %s", bucket_name, exc)
            return False

    def _is_logging_enabled(self, bucket_name: str, s3_client) -> bool:
        try:
            response = s3_client.get_bucket_logging(Bucket=bucket_name)
            return "LoggingEnabled" in response
        except ClientError as exc:
            logger.debug("Unable to query logging for %s: %s", bucket_name, exc)
            return False

    def _build_finding(
        self,
        bucket_name: str,
        account_id: str,
        *,
        finding_type: str,
        severity: str,
        title: str,
        description: str,
        remediation: str,
    ) -> Dict[str, Any]:
        resource_arn = (
            f"arn:aws:s3:::{bucket_name}"  # S3 bucket ARNs omit region/account
        )
        return {
            "finding_type": finding_type,
            "severity": severity,
            "title": title,
            "description": description,
            "resource_arn": resource_arn,
            "resource_id": bucket_name,
            "resource_name": bucket_name,
            "resource_type": "s3_bucket",
            "service": "s3",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": remediation,
            "metadata": {},
        }
