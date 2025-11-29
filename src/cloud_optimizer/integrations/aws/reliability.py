"""Reliability scanner for AWS infrastructure reliability analysis.

Scans AWS infrastructure for reliability issues including single points
of failure, missing redundancy, backup configurations, and health checks.
"""

import logging
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from cloud_optimizer.integrations.aws.base import BaseAWSScanner

logger = logging.getLogger(__name__)


class ReliabilityScanner(BaseAWSScanner):
    """Scanner for AWS infrastructure reliability issues.

    Detects:
    - Single-AZ RDS instances (single point of failure)
    - RDS instances without Multi-AZ enabled
    - RDS instances without automated backups enabled
    - Load balancers without health checks
    - EC2 instances without Auto Scaling Groups
    - Unattached EBS volumes without snapshots

    Example:
        scanner = ReliabilityScanner()
        findings = await scanner.scan("123456789012")
    """

    # Thresholds for reliability analysis
    MIN_BACKUP_RETENTION_DAYS = 7
    MIN_HEALTHY_INSTANCES = 2

    def get_scanner_name(self) -> str:
        """Return scanner name for logging."""
        return "ReliabilityScanner"

    async def scan(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan AWS infrastructure for reliability issues.

        Args:
            account_id: AWS account ID to scan

        Returns:
            List of reliability findings
        """
        logger.info(
            f"Starting reliability scan for account {account_id}",
            extra={"account_id": account_id, "region": self.region},
        )
        findings: List[Dict[str, Any]] = []

        try:
            # 1. Check RDS instances for reliability issues
            findings.extend(self._check_rds_reliability(account_id))

            # 2. Check Load Balancers for health check configurations
            findings.extend(self._check_elb_health_checks(account_id))

            # 3. Check EBS volumes for backup snapshots
            findings.extend(self._check_ebs_snapshots(account_id))

            # 4. Check EC2 instances for Auto Scaling configuration
            findings.extend(self._check_ec2_auto_scaling(account_id))

            logger.info(
                f"Reliability scan complete: {len(findings)} findings",
                extra={"account_id": account_id, "findings_count": len(findings)},
            )

        except ClientError as e:
            logger.error(f"Reliability scan failed: {e}", exc_info=True)
            raise

        return findings

    def _check_rds_reliability(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Check RDS instances for reliability issues.

        Args:
            account_id: AWS account ID

        Returns:
            List of RDS reliability findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            rds_client = self.get_client("rds")
            response = rds_client.describe_db_instances()

            for db_instance in response.get("DBInstances", []):
                db_identifier = db_instance.get("DBInstanceIdentifier", "unknown")
                multi_az = db_instance.get("MultiAZ", False)
                backup_retention = db_instance.get("BackupRetentionPeriod", 0)
                engine = db_instance.get("Engine", "unknown")

                # Check for Multi-AZ configuration
                if not multi_az:
                    findings.append(
                        self._create_single_az_rds_finding(
                            db_identifier=db_identifier,
                            engine=engine,
                            account_id=account_id,
                        )
                    )

                # Check for backup configuration
                if backup_retention < self.MIN_BACKUP_RETENTION_DAYS:
                    findings.append(
                        self._create_backup_configuration_finding(
                            db_identifier=db_identifier,
                            current_retention=backup_retention,
                            engine=engine,
                            account_id=account_id,
                        )
                    )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            logger.warning(f"Failed to check RDS reliability: {error_code} - {e}")

        return findings

    def _check_elb_health_checks(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Check Load Balancers for health check configurations.

        Args:
            account_id: AWS account ID

        Returns:
            List of ELB health check findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            # Check Classic Load Balancers
            elb_client = self.get_client("elb")
            classic_lbs = elb_client.describe_load_balancers()

            for lb in classic_lbs.get("LoadBalancerDescriptions", []):
                lb_name = lb.get("LoadBalancerName", "unknown")
                health_check = lb.get("HealthCheck", {})
                interval = health_check.get("Interval", 0)
                timeout = health_check.get("Timeout", 0)
                unhealthy_threshold = health_check.get("UnhealthyThreshold", 0)

                # Check if health check is properly configured
                if interval == 0 or timeout == 0 or unhealthy_threshold == 0:
                    findings.append(
                        self._create_missing_health_check_finding(
                            lb_name=lb_name,
                            lb_type="classic",
                            account_id=account_id,
                        )
                    )
                # Check if timeout is too short
                elif timeout >= interval:
                    findings.append(
                        self._create_misconfigured_health_check_finding(
                            lb_name=lb_name,
                            lb_type="classic",
                            interval=interval,
                            timeout=timeout,
                            account_id=account_id,
                        )
                    )

            # Check Application/Network Load Balancers
            elbv2_client = self.get_client("elbv2")
            modern_lbs = elbv2_client.describe_load_balancers()

            for lb in modern_lbs.get("LoadBalancers", []):
                lb_arn = lb.get("LoadBalancerArn", "")
                lb_name = lb.get("LoadBalancerName", "unknown")
                lb_type = lb.get("Type", "unknown")

                # Check target groups for health checks
                target_groups = elbv2_client.describe_target_groups(
                    LoadBalancerArn=lb_arn
                )

                for tg in target_groups.get("TargetGroups", []):
                    tg_name = tg.get("TargetGroupName", "unknown")
                    interval = tg.get("HealthCheckIntervalSeconds", 0)
                    timeout = tg.get("HealthCheckTimeoutSeconds", 0)

                    if interval == 0 or timeout == 0:
                        findings.append(
                            self._create_missing_health_check_finding(
                                lb_name=f"{lb_name}/{tg_name}",
                                lb_type=lb_type,
                                account_id=account_id,
                            )
                        )
                    elif timeout >= interval:
                        findings.append(
                            self._create_misconfigured_health_check_finding(
                                lb_name=f"{lb_name}/{tg_name}",
                                lb_type=lb_type,
                                interval=interval,
                                timeout=timeout,
                                account_id=account_id,
                            )
                        )

        except ClientError as e:
            logger.warning(f"Failed to check ELB health checks: {e}")

        return findings

    def _check_ebs_snapshots(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Check EBS volumes for backup snapshots.

        Args:
            account_id: AWS account ID

        Returns:
            List of EBS snapshot findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            ec2_client = self.get_client("ec2")
            volumes = ec2_client.describe_volumes()

            for volume in volumes.get("Volumes", []):
                volume_id = volume.get("VolumeId", "unknown")
                state = volume.get("State", "unknown")
                size_gb = volume.get("Size", 0)

                # Only check volumes that are in-use
                if state != "in-use":
                    continue

                # Check if volume has any snapshots
                snapshots = ec2_client.describe_snapshots(
                    Filters=[{"Name": "volume-id", "Values": [volume_id]}],
                    OwnerIds=[account_id],
                )

                if not snapshots.get("Snapshots", []):
                    findings.append(
                        self._create_no_snapshot_finding(
                            volume_id=volume_id,
                            size_gb=size_gb,
                            account_id=account_id,
                        )
                    )

        except ClientError as e:
            logger.warning(f"Failed to check EBS snapshots: {e}")

        return findings

    def _check_ec2_auto_scaling(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Check EC2 instances for Auto Scaling Group configuration.

        Args:
            account_id: AWS account ID

        Returns:
            List of EC2 Auto Scaling findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            ec2_client = self.get_client("ec2")
            autoscaling_client = self.get_client("autoscaling")

            # Get all running EC2 instances
            instances = ec2_client.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )

            # Get all Auto Scaling Groups
            asg_response = autoscaling_client.describe_auto_scaling_groups()
            asg_instance_ids = set()

            for asg in asg_response.get("AutoScalingGroups", []):
                for instance in asg.get("Instances", []):
                    asg_instance_ids.add(instance.get("InstanceId"))

            # Check each instance
            for reservation in instances.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance.get("InstanceId", "unknown")
                    instance_type = instance.get("InstanceType", "unknown")

                    # Skip instances that are part of ASGs
                    if instance_id in asg_instance_ids:
                        continue

                    # Check instance tags for production/critical markers
                    tags = {
                        tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])
                    }
                    env = tags.get("Environment", "").lower()
                    name = tags.get("Name", "")

                    # Only flag production instances without ASG
                    if env in ["production", "prod", "prd"]:
                        findings.append(
                            self._create_no_auto_scaling_finding(
                                instance_id=instance_id,
                                instance_type=instance_type,
                                instance_name=name,
                                account_id=account_id,
                            )
                        )

        except ClientError as e:
            logger.warning(f"Failed to check EC2 Auto Scaling: {e}")

        return findings

    def _create_single_az_rds_finding(
        self, db_identifier: str, engine: str, account_id: str
    ) -> Dict[str, Any]:
        """Create finding for single-AZ RDS instance (SPOF)."""
        severity = self._calculate_severity(
            has_multi_az=False,
            has_backups=True,  # Assume backups exist (checked separately)
            resource_type="rds",
        )

        return {
            "finding_type": "single_point_of_failure",
            "severity": severity,
            "title": f"Single-AZ RDS instance: {db_identifier}",
            "description": (
                f"RDS instance {db_identifier} ({engine}) is not configured for Multi-AZ. "
                "This creates a single point of failure if the Availability Zone becomes unavailable."
            ),
            "resource_arn": f"arn:aws:rds:{self.region}:{account_id}:db:{db_identifier}",
            "resource_id": db_identifier,
            "resource_name": db_identifier,
            "resource_type": "rds_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Enable Multi-AZ for RDS instance {db_identifier}. "
                "Navigate to RDS Console, select the instance, and choose 'Modify' to enable Multi-AZ. "
                "Note: This will cause a brief outage during failover setup."
            ),
            "metadata": {
                "db_identifier": db_identifier,
                "engine": engine,
                "multi_az": False,
            },
        }

    def _create_backup_configuration_finding(
        self,
        db_identifier: str,
        current_retention: int,
        engine: str,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for insufficient RDS backup retention."""
        # Determine severity based on retention period
        if current_retention == 0:
            severity = "critical"
            title = f"RDS backups disabled: {db_identifier}"
            description = (
                f"RDS instance {db_identifier} ({engine}) has automated backups disabled. "
                "This creates a risk of data loss in case of database failure or corruption."
            )
        else:
            severity = "medium"
            title = f"Insufficient RDS backup retention: {db_identifier} ({current_retention} days)"
            description = (
                f"RDS instance {db_identifier} ({engine}) has backup retention set to "
                f"{current_retention} days, which is below the recommended {self.MIN_BACKUP_RETENTION_DAYS} days."
            )

        return {
            "finding_type": "backup_configuration",
            "severity": severity,
            "title": title,
            "description": description,
            "resource_arn": f"arn:aws:rds:{self.region}:{account_id}:db:{db_identifier}",
            "resource_id": db_identifier,
            "resource_name": db_identifier,
            "resource_type": "rds_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Enable automated backups for RDS instance {db_identifier} with at least "
                f"{self.MIN_BACKUP_RETENTION_DAYS} days retention. Navigate to RDS Console, "
                "select the instance, choose 'Modify', and set backup retention period."
            ),
            "metadata": {
                "db_identifier": db_identifier,
                "engine": engine,
                "current_retention_days": current_retention,
                "recommended_retention_days": self.MIN_BACKUP_RETENTION_DAYS,
            },
        }

    def _create_missing_health_check_finding(
        self, lb_name: str, lb_type: str, account_id: str
    ) -> Dict[str, Any]:
        """Create finding for load balancer without health checks."""
        severity = "high"

        return {
            "finding_type": "health_check",
            "severity": severity,
            "title": f"Missing health check: {lb_name}",
            "description": (
                f"{lb_type.upper()} Load Balancer {lb_name} does not have health checks configured. "
                "Without health checks, the load balancer cannot detect and route traffic away "
                "from unhealthy instances."
            ),
            "resource_arn": f"arn:aws:elasticloadbalancing:{self.region}:{account_id}:loadbalancer/{lb_name}",
            "resource_id": lb_name,
            "resource_name": lb_name,
            "resource_type": f"{lb_type}_load_balancer",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Configure health checks for {lb_type.upper()} Load Balancer {lb_name}. "
                "Navigate to EC2 Console > Load Balancers, select the load balancer, "
                "and configure health check settings with appropriate interval, timeout, and thresholds."
            ),
            "metadata": {
                "lb_name": lb_name,
                "lb_type": lb_type,
            },
        }

    def _create_misconfigured_health_check_finding(
        self,
        lb_name: str,
        lb_type: str,
        interval: int,
        timeout: int,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for misconfigured health check (timeout >= interval)."""
        severity = "medium"

        return {
            "finding_type": "health_check",
            "severity": severity,
            "title": f"Misconfigured health check: {lb_name}",
            "description": (
                f"{lb_type.upper()} Load Balancer {lb_name} has health check timeout ({timeout}s) "
                f"greater than or equal to interval ({interval}s). Health checks may fail to execute properly."
            ),
            "resource_arn": f"arn:aws:elasticloadbalancing:{self.region}:{account_id}:loadbalancer/{lb_name}",
            "resource_id": lb_name,
            "resource_name": lb_name,
            "resource_type": f"{lb_type}_load_balancer",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Adjust health check settings for {lb_name}. Timeout should be less than interval. "
                "Recommended: interval 30s, timeout 5s. Navigate to EC2 Console > Load Balancers "
                "to modify health check configuration."
            ),
            "metadata": {
                "lb_name": lb_name,
                "lb_type": lb_type,
                "interval_seconds": interval,
                "timeout_seconds": timeout,
            },
        }

    def _create_no_snapshot_finding(
        self, volume_id: str, size_gb: int, account_id: str
    ) -> Dict[str, Any]:
        """Create finding for EBS volume without snapshots."""
        severity = "medium"

        return {
            "finding_type": "backup_configuration",
            "severity": severity,
            "title": f"EBS volume without snapshots: {volume_id}",
            "description": (
                f"EBS volume {volume_id} ({size_gb} GB) is in-use but has no snapshots. "
                "Without snapshots, data cannot be recovered in case of volume failure or accidental deletion."
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:volume/{volume_id}",
            "resource_id": volume_id,
            "resource_name": volume_id,
            "resource_type": "ebs_volume",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Create snapshots for EBS volume {volume_id}. Navigate to EC2 Console > Volumes, "
                "select the volume, and choose 'Create Snapshot'. Consider setting up automated "
                "snapshot lifecycle policies using AWS Data Lifecycle Manager."
            ),
            "metadata": {
                "volume_id": volume_id,
                "size_gb": size_gb,
            },
        }

    def _create_no_auto_scaling_finding(
        self,
        instance_id: str,
        instance_type: str,
        instance_name: str,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for production EC2 instance without Auto Scaling."""
        severity = "medium"

        return {
            "finding_type": "single_point_of_failure",
            "severity": severity,
            "title": f"Production EC2 without Auto Scaling: {instance_name or instance_id}",
            "description": (
                f"Production EC2 instance {instance_id} ({instance_type}) is not part of an "
                "Auto Scaling Group. If this instance fails, there is no automatic replacement, "
                "creating a potential service outage."
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:instance/{instance_id}",
            "resource_id": instance_id,
            "resource_name": instance_name or instance_id,
            "resource_type": "ec2_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Consider adding instance {instance_id} to an Auto Scaling Group for automatic "
                "replacement and scaling. Create an AMI from the instance, create a launch template, "
                "and configure an Auto Scaling Group with min size 2 for redundancy."
            ),
            "metadata": {
                "instance_id": instance_id,
                "instance_type": instance_type,
                "instance_name": instance_name,
            },
        }

    def _calculate_severity(
        self, has_multi_az: bool, has_backups: bool, resource_type: str
    ) -> str:
        """
        Calculate severity based on reliability factors.

        Args:
            has_multi_az: Whether resource has multi-AZ redundancy
            has_backups: Whether resource has backup configuration
            resource_type: Type of resource (rds, ec2, etc.)

        Returns:
            Severity level (low, medium, high, critical)
        """
        # No Multi-AZ and no backups = Critical (complete SPOF)
        if not has_multi_az and not has_backups:
            return "critical"

        # No Multi-AZ but has backups = High (SPOF but recoverable)
        if not has_multi_az and has_backups:
            return "high"

        # Has Multi-AZ but no backups = Medium (redundant but no disaster recovery)
        if has_multi_az and not has_backups:
            return "medium"

        # Both Multi-AZ and backups = Low (well configured, minor improvements possible)
        return "low"
