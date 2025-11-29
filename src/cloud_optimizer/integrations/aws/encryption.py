"""Encryption scanner for AWS."""

import logging
from typing import Any, Dict, List

from cloud_optimizer.integrations.aws.base import BaseAWSScanner

logger = logging.getLogger(__name__)


class EncryptionScanner(BaseAWSScanner):
    """Scanner for AWS encryption misconfigurations."""

    def get_scanner_name(self) -> str:
        """Return scanner name."""
        return "EncryptionScanner"

    async def scan(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan AWS resources for encryption issues.

        Detects:
        - Unencrypted EBS volumes
        - Unencrypted S3 buckets
        - Unencrypted RDS instances

        Args:
            account_id: AWS account ID to scan

        Returns:
            List of security findings
        """
        logger.info(
            f"Starting encryption scan for account {account_id} in {self.region}"
        )
        findings: List[Dict[str, Any]] = []

        try:
            # Scan EBS volumes
            findings.extend(self._scan_ebs_volumes(account_id))

            # Scan S3 buckets
            findings.extend(self._scan_s3_buckets(account_id))

            # Scan RDS instances
            findings.extend(self._scan_rds_instances(account_id))

            logger.info(
                f"Encryption scan complete: {len(findings)} findings",
                extra={"account_id": account_id, "findings_count": len(findings)},
            )

        except Exception as e:
            logger.error(f"Encryption scan failed: {e}", exc_info=True)
            raise

        return findings

    def _scan_ebs_volumes(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan EBS volumes for encryption.

        Args:
            account_id: AWS account ID

        Returns:
            List of findings for unencrypted volumes
        """
        findings: List[Dict[str, Any]] = []

        try:
            ec2_client = self.get_client("ec2")
            response = ec2_client.describe_volumes()

            for volume in response.get("Volumes", []):
                volume_id = volume["VolumeId"]
                encrypted = volume.get("Encrypted", False)

                if not encrypted:
                    findings.append(
                        self._create_unencrypted_ebs_finding(
                            volume_id, volume, account_id
                        )
                    )

        except Exception as e:
            logger.warning(f"EBS volume scan failed: {e}")

        return findings

    def _scan_s3_buckets(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan S3 buckets for encryption.

        Args:
            account_id: AWS account ID

        Returns:
            List of findings for unencrypted buckets
        """
        findings: List[Dict[str, Any]] = []

        try:
            s3_client = self.get_client("s3")
            response = s3_client.list_buckets()

            for bucket in response.get("Buckets", []):
                bucket_name = bucket["Name"]

                # Check encryption
                try:
                    s3_client.get_bucket_encryption(Bucket=bucket_name)
                except s3_client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
                    findings.append(
                        self._create_unencrypted_s3_finding(
                            bucket_name, account_id
                        )
                    )
                except Exception as e:
                    logger.debug(f"Could not check encryption for {bucket_name}: {e}")

        except Exception as e:
            logger.warning(f"S3 bucket scan failed: {e}")

        return findings

    def _scan_rds_instances(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan RDS instances for encryption.

        Args:
            account_id: AWS account ID

        Returns:
            List of findings for unencrypted instances
        """
        findings: List[Dict[str, Any]] = []

        try:
            rds_client = self.get_client("rds")
            response = rds_client.describe_db_instances()

            for instance in response.get("DBInstances", []):
                instance_id = instance["DBInstanceIdentifier"]
                encrypted = instance.get("StorageEncrypted", False)

                if not encrypted:
                    findings.append(
                        self._create_unencrypted_rds_finding(
                            instance_id, instance, account_id
                        )
                    )

        except Exception as e:
            logger.warning(f"RDS instance scan failed: {e}")

        return findings

    def _create_unencrypted_ebs_finding(
        self, volume_id: str, volume: Dict[str, Any], account_id: str
    ) -> Dict[str, Any]:
        """Create finding for unencrypted EBS volume."""
        size_gb = volume.get("Size", 0)
        state = volume.get("State", "unknown")

        return {
            "finding_type": "unencrypted_ebs_volume",
            "severity": "high",
            "title": f"Unencrypted EBS volume: {volume_id}",
            "description": (
                f"EBS volume {volume_id} ({size_gb} GB, {state}) "
                "is not encrypted at rest"
            ),
            "resource_arn": (
                f"arn:aws:ec2:{self.region}:{account_id}:volume/{volume_id}"
            ),
            "resource_id": volume_id,
            "resource_name": volume_id,
            "resource_type": "ebs_volume",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Enable encryption for EBS volume {volume_id}. "
                "Create an encrypted snapshot and restore it to a new "
                "encrypted volume."
            ),
            "metadata": {
                "volume_id": volume_id,
                "size_gb": size_gb,
                "state": state,
            },
        }

    def _create_unencrypted_s3_finding(
        self, bucket_name: str, account_id: str
    ) -> Dict[str, Any]:
        """Create finding for unencrypted S3 bucket."""
        return {
            "finding_type": "unencrypted_s3_bucket",
            "severity": "high",
            "title": f"Unencrypted S3 bucket: {bucket_name}",
            "description": (
                f"S3 bucket {bucket_name} does not have default encryption enabled"
            ),
            "resource_arn": f"arn:aws:s3:::{bucket_name}",
            "resource_id": bucket_name,
            "resource_name": bucket_name,
            "resource_type": "s3_bucket",
            "aws_account_id": account_id,
            "region": "global",
            "remediation": (
                f"Enable default server-side encryption for S3 bucket {bucket_name} "
                "using AES-256 or AWS KMS"
            ),
            "metadata": {"bucket_name": bucket_name},
        }

    def _create_unencrypted_rds_finding(
        self, instance_id: str, instance: Dict[str, Any], account_id: str
    ) -> Dict[str, Any]:
        """Create finding for unencrypted RDS instance."""
        engine = instance.get("Engine", "unknown")
        engine_version = instance.get("EngineVersion", "unknown")

        return {
            "finding_type": "unencrypted_rds_instance",
            "severity": "critical",
            "title": f"Unencrypted RDS instance: {instance_id}",
            "description": (
                f"RDS instance {instance_id} ({engine} {engine_version}) "
                "does not have encryption at rest enabled"
            ),
            "resource_arn": (
                f"arn:aws:rds:{self.region}:{account_id}:db:{instance_id}"
            ),
            "resource_id": instance_id,
            "resource_name": instance_id,
            "resource_type": "rds_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Create an encrypted snapshot of RDS instance {instance_id} "
                "and restore it to a new instance with encryption enabled. "
                "Note: Encryption cannot be enabled on existing instances."
            ),
            "metadata": {
                "instance_id": instance_id,
                "engine": engine,
                "engine_version": engine_version,
            },
        }
