"""Systems Manager scanner for AWS operational excellence.

Scans AWS resources for operational best practices including monitoring,
automation, documentation, and Systems Manager compliance.
"""

import logging
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from cloud_optimizer.integrations.aws.base import BaseAWSScanner

logger = logging.getLogger(__name__)


class SystemsManagerScanner(BaseAWSScanner):
    """Scanner for AWS operational excellence opportunities.

    Detects:
    - EC2 instances without CloudWatch alarms
    - Missing SSM agent on EC2 instances
    - EC2 instances without associated runbooks
    - Resources without proper tagging
    - Missing automation documents

    Example:
        scanner = SystemsManagerScanner()
        findings = await scanner.scan("123456789012")
    """

    # Thresholds for operational excellence
    REQUIRED_TAGS = ["Name", "Environment", "Owner"]
    CRITICAL_METRICS = [
        "CPUUtilization",
        "StatusCheckFailed",
    ]

    def get_scanner_name(self) -> str:
        """Return scanner name for logging."""
        return "SystemsManagerScanner"

    async def scan(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan AWS resources for operational excellence gaps.

        Args:
            account_id: AWS account ID to scan

        Returns:
            List of operational excellence findings
        """
        logger.info(f"Starting operational excellence scan for account {account_id}")
        findings: List[Dict[str, Any]] = []

        try:
            # Get EC2 client for instance checks
            ec2_client = self.get_client("ec2")
            cloudwatch_client = self.get_client("cloudwatch")
            ssm_client = self.get_client("ssm")

            # Get all running instances
            instances = self._get_running_instances(ec2_client)

            for instance in instances:
                instance_id = instance["InstanceId"]

                # 1. Check for CloudWatch alarms
                findings.extend(
                    self._check_cloudwatch_alarms(
                        cloudwatch_client, instance, account_id
                    )
                )

                # 2. Check for SSM agent
                findings.extend(self._check_ssm_agent(ssm_client, instance, account_id))

                # 3. Check for automation documents/runbooks
                findings.extend(
                    self._check_automation_documents(ssm_client, instance, account_id)
                )

                # 4. Check for proper tagging
                findings.extend(self._check_instance_tags(instance, account_id))

            # 5. Check for SSM documents existence
            findings.extend(self._check_ssm_documents(ssm_client, account_id))

            logger.info(
                f"Operational excellence scan complete: {len(findings)} findings",
                extra={"account_id": account_id, "findings_count": len(findings)},
            )

        except ClientError as e:
            logger.error(f"Operational excellence scan failed: {e}")
            raise

        return findings

    def _get_running_instances(self, ec2_client: Any) -> List[Dict[str, Any]]:
        """
        Get all running EC2 instances.

        Args:
            ec2_client: Boto3 EC2 client

        Returns:
            List of running instances
        """
        try:
            response = ec2_client.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )

            instances: List[Dict[str, Any]] = []
            for reservation in response.get("Reservations", []):
                instances.extend(reservation.get("Instances", []))

            logger.info(f"Found {len(instances)} running instances")
            return instances

        except ClientError as e:
            logger.warning(f"Failed to get running instances: {e}")
            return []

    def _check_cloudwatch_alarms(
        self, cloudwatch_client: Any, instance: Dict[str, Any], account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Check if EC2 instance has required CloudWatch alarms.

        Args:
            cloudwatch_client: Boto3 CloudWatch client
            instance: EC2 instance data
            account_id: AWS account ID

        Returns:
            List of monitoring gap findings
        """
        findings: List[Dict[str, Any]] = []
        instance_id = instance["InstanceId"]

        try:
            # Get alarms for this instance
            response = cloudwatch_client.describe_alarms(
                AlarmNamePrefix=f"{instance_id}"
            )

            existing_alarms = response.get("MetricAlarms", [])
            alarm_metrics = {
                alarm["MetricName"]
                for alarm in existing_alarms
                if alarm.get("Namespace") == "AWS/EC2"
            }

            # Check for missing critical alarms
            missing_metrics = [
                metric
                for metric in self.CRITICAL_METRICS
                if metric not in alarm_metrics
            ]

            if missing_metrics:
                findings.append(
                    self._create_monitoring_gap_finding(
                        instance=instance,
                        missing_metrics=missing_metrics,
                        account_id=account_id,
                    )
                )

        except ClientError as e:
            logger.warning(f"Failed to check CloudWatch alarms for {instance_id}: {e}")

        return findings

    def _check_ssm_agent(
        self, ssm_client: Any, instance: Dict[str, Any], account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Check if EC2 instance has SSM agent installed and online.

        Args:
            ssm_client: Boto3 SSM client
            instance: EC2 instance data
            account_id: AWS account ID

        Returns:
            List of SSM agent findings
        """
        findings: List[Dict[str, Any]] = []
        instance_id = instance["InstanceId"]

        try:
            # Check if instance is managed by SSM
            response = ssm_client.describe_instance_information(
                Filters=[{"Key": "InstanceIds", "Values": [instance_id]}]
            )

            if not response.get("InstanceInformationList"):
                # Instance is not managed by SSM
                findings.append(
                    self._create_ssm_agent_missing_finding(
                        instance=instance,
                        account_id=account_id,
                    )
                )

        except ClientError as e:
            logger.warning(f"Failed to check SSM agent for {instance_id}: {e}")

        return findings

    def _check_automation_documents(
        self, ssm_client: Any, instance: Dict[str, Any], account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Check if instance has automation documents/runbooks configured.

        Args:
            ssm_client: Boto3 SSM client
            instance: EC2 instance data
            account_id: AWS account ID

        Returns:
            List of automation opportunity findings
        """
        findings: List[Dict[str, Any]] = []
        instance_id = instance["InstanceId"]

        try:
            # Check for maintenance window associations
            response = ssm_client.describe_maintenance_window_targets(
                Filters=[
                    {
                        "Key": "OwnerInformation",
                        "Values": [instance_id],
                    }
                ]
            )

            targets = response.get("Targets", [])

            if not targets:
                # No automation configured for this instance
                findings.append(
                    self._create_automation_opportunity_finding(
                        instance=instance,
                        account_id=account_id,
                    )
                )

        except ClientError as e:
            # Maintenance windows might not exist - not critical
            logger.debug(f"Failed to check automation for {instance_id}: {e}")

        return findings

    def _check_instance_tags(
        self, instance: Dict[str, Any], account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Check if instance has required tags.

        Args:
            instance: EC2 instance data
            account_id: AWS account ID

        Returns:
            List of documentation issue findings
        """
        findings: List[Dict[str, Any]] = []
        instance_id = instance["InstanceId"]

        # Get instance tags
        tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}

        # Check for missing required tags
        missing_tags = [tag for tag in self.REQUIRED_TAGS if tag not in tags]

        if missing_tags:
            findings.append(
                self._create_tagging_issue_finding(
                    instance=instance,
                    missing_tags=missing_tags,
                    account_id=account_id,
                )
            )

        return findings

    def _check_ssm_documents(
        self, ssm_client: Any, account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Check for existence of custom SSM automation documents.

        Args:
            ssm_client: Boto3 SSM client
            account_id: AWS account ID

        Returns:
            List of documentation issue findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            # Check for custom automation documents
            response = ssm_client.list_documents(
                Filters=[
                    {
                        "Key": "Owner",
                        "Values": ["Self"],
                    },
                    {
                        "Key": "DocumentType",
                        "Values": ["Automation"],
                    },
                ]
            )

            custom_docs = response.get("DocumentIdentifiers", [])

            if len(custom_docs) == 0:
                # No custom automation documents found
                findings.append(
                    self._create_missing_runbooks_finding(
                        account_id=account_id,
                    )
                )

        except ClientError as e:
            logger.warning(f"Failed to check SSM documents: {e}")

        return findings

    def _create_monitoring_gap_finding(
        self,
        instance: Dict[str, Any],
        missing_metrics: List[str],
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for missing CloudWatch alarms."""
        instance_id = instance["InstanceId"]
        instance_type = instance.get("InstanceType", "unknown")

        # Get instance name from tags
        tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
        instance_name = tags.get("Name", instance_id)

        severity = self._calculate_monitoring_severity(missing_metrics)

        return {
            "finding_type": "monitoring_gap",
            "severity": severity,
            "title": f"Missing CloudWatch alarms: {instance_name}",
            "description": (
                f"EC2 instance {instance_id} ({instance_type}) is missing "
                f"critical CloudWatch alarms for: {', '.join(missing_metrics)}. "
                "Without proper monitoring, issues may go undetected."
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:instance/{instance_id}",
            "resource_id": instance_id,
            "resource_name": instance_name,
            "resource_type": "ec2_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Create CloudWatch alarms for {instance_id} to monitor: "
                f"{', '.join(missing_metrics)}. Use AWS Console or CLI to set up "
                "alarms with appropriate thresholds and SNS notifications."
            ),
            "metadata": {
                "instance_id": instance_id,
                "instance_type": instance_type,
                "missing_metrics": missing_metrics,
            },
        }

    def _create_ssm_agent_missing_finding(
        self, instance: Dict[str, Any], account_id: str
    ) -> Dict[str, Any]:
        """Create finding for missing SSM agent."""
        instance_id = instance["InstanceId"]
        instance_type = instance.get("InstanceType", "unknown")

        tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
        instance_name = tags.get("Name", instance_id)

        return {
            "finding_type": "automation_opportunity",
            "severity": "medium",
            "title": f"SSM agent not installed: {instance_name}",
            "description": (
                f"EC2 instance {instance_id} ({instance_type}) does not have "
                "AWS Systems Manager agent installed or running. SSM enables "
                "automated patching, configuration management, and remote access."
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:instance/{instance_id}",
            "resource_id": instance_id,
            "resource_name": instance_name,
            "resource_type": "ec2_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Install and configure AWS Systems Manager agent on {instance_id}. "
                "Ensure the instance has an IAM role with AmazonSSMManagedInstanceCore "
                "policy attached. Follow AWS documentation for SSM agent installation."
            ),
            "metadata": {
                "instance_id": instance_id,
                "instance_type": instance_type,
                "platform": instance.get("Platform", "linux"),
            },
        }

    def _create_automation_opportunity_finding(
        self, instance: Dict[str, Any], account_id: str
    ) -> Dict[str, Any]:
        """Create finding for missing automation configuration."""
        instance_id = instance["InstanceId"]
        instance_type = instance.get("InstanceType", "unknown")

        tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
        instance_name = tags.get("Name", instance_id)

        return {
            "finding_type": "automation_opportunity",
            "severity": "low",
            "title": f"No automation configured: {instance_name}",
            "description": (
                f"EC2 instance {instance_id} ({instance_type}) has no automation "
                "runbooks or maintenance windows configured. Consider setting up "
                "automated patching, backups, or other maintenance tasks."
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:instance/{instance_id}",
            "resource_id": instance_id,
            "resource_name": instance_name,
            "resource_type": "ec2_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Create SSM maintenance windows or automation documents for {instance_id}. "
                "Consider automating: OS patching, backup tasks, compliance checks, "
                "or custom administrative scripts using SSM Run Command."
            ),
            "metadata": {
                "instance_id": instance_id,
                "instance_type": instance_type,
            },
        }

    def _create_tagging_issue_finding(
        self,
        instance: Dict[str, Any],
        missing_tags: List[str],
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for missing required tags."""
        instance_id = instance["InstanceId"]
        instance_type = instance.get("InstanceType", "unknown")

        tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
        instance_name = tags.get("Name", instance_id)

        severity = self._calculate_tagging_severity(missing_tags)

        return {
            "finding_type": "documentation_issue",
            "severity": severity,
            "title": f"Missing required tags: {instance_name}",
            "description": (
                f"EC2 instance {instance_id} ({instance_type}) is missing "
                f"required tags: {', '.join(missing_tags)}. Proper tagging "
                "is essential for cost allocation, automation, and resource management."
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:instance/{instance_id}",
            "resource_id": instance_id,
            "resource_name": instance_name,
            "resource_type": "ec2_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Add missing tags to {instance_id}: {', '.join(missing_tags)}. "
                "Use AWS Console, CLI, or Infrastructure as Code to apply consistent "
                "tagging across all resources. Implement tag policies to enforce compliance."
            ),
            "metadata": {
                "instance_id": instance_id,
                "instance_type": instance_type,
                "missing_tags": missing_tags,
                "existing_tags": list(tags.keys()),
            },
        }

    def _create_missing_runbooks_finding(self, account_id: str) -> Dict[str, Any]:
        """Create finding for missing custom automation documents."""
        return {
            "finding_type": "documentation_issue",
            "severity": "low",
            "title": "No custom automation runbooks found",
            "description": (
                "No custom SSM automation documents were found in this account. "
                "Custom runbooks enable automated incident response, routine "
                "maintenance, and standardized operational procedures."
            ),
            "resource_arn": f"arn:aws:ssm:{self.region}:{account_id}:document",
            "resource_id": f"ssm-documents-{account_id}",
            "resource_name": "custom-automation-documents",
            "resource_type": "ssm_document",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                "Create custom SSM automation documents for common operational tasks. "
                "Examples: EC2 instance recovery, snapshot creation, application restarts, "
                "log collection, or security incident response procedures."
            ),
            "metadata": {
                "document_type": "Automation",
            },
        }

    def _calculate_monitoring_severity(self, missing_metrics: List[str]) -> str:
        """
        Calculate severity based on missing monitoring metrics.

        Args:
            missing_metrics: List of missing metric names

        Returns:
            Severity level (low, medium, high, critical)
        """
        # Critical metrics missing = high severity
        critical_count = sum(
            1 for metric in missing_metrics if metric in self.CRITICAL_METRICS
        )

        if critical_count >= 2:
            return "high"
        elif critical_count == 1:
            return "medium"
        else:
            return "low"

    def _calculate_tagging_severity(self, missing_tags: List[str]) -> str:
        """
        Calculate severity based on missing tags.

        Args:
            missing_tags: List of missing tag names

        Returns:
            Severity level (low, medium, high, critical)
        """
        # All required tags missing = medium severity
        if len(missing_tags) >= len(self.REQUIRED_TAGS):
            return "medium"
        elif len(missing_tags) >= 2:
            return "low"
        else:
            return "low"
