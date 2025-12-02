"""Cost Explorer scanner for AWS cost optimization.

Scans AWS Cost Explorer for cost anomalies, savings opportunities,
reserved instance recommendations, rightsizing suggestions, and idle resources.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from cloud_optimizer.integrations.aws.base import BaseAWSScanner

logger = logging.getLogger(__name__)


class CostExplorerScanner(BaseAWSScanner):
    """Scanner for AWS Cost Explorer optimization opportunities.

    Detects:
    - Cost anomalies (unusual spending patterns)
    - Savings opportunities
    - Reserved instance recommendations
    - Rightsizing recommendations
    - Idle resources

    Example:
        scanner = CostExplorerScanner()
        findings = await scanner.scan("123456789012")
    """

    # Thresholds for anomaly detection
    ANOMALY_PERCENTAGE_THRESHOLD = 20  # 20% deviation from baseline
    IDLE_DAYS_THRESHOLD = 14  # Resources idle for 14+ days

    def get_scanner_name(self) -> str:
        """Return scanner name for logging."""
        return "CostExplorerScanner"

    async def scan(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan AWS Cost Explorer for optimization opportunities.

        Args:
            account_id: AWS account ID to scan

        Returns:
            List of cost optimization findings
        """
        logger.info(f"Starting cost optimization scan for account {account_id}")
        findings: List[Dict[str, Any]] = []

        try:
            # Cost Explorer is a global service (us-east-1)
            ce_client = self.get_client("ce")

            # 1. Find cost anomalies
            findings.extend(self._find_cost_anomalies(ce_client, account_id))

            # 2. Get RI recommendations
            findings.extend(self._get_ri_recommendations(ce_client, account_id))

            # 3. Get rightsizing recommendations
            findings.extend(
                self._get_rightsizing_recommendations(ce_client, account_id)
            )

            # 4. Find idle resources
            findings.extend(self._find_idle_resources(account_id))

            logger.info(
                f"Cost optimization scan complete: {len(findings)} findings",
                extra={"account_id": account_id, "findings_count": len(findings)},
            )

        except ClientError as e:
            logger.error(f"Cost Explorer scan failed: {e}")
            raise

        return findings

    def _find_cost_anomalies(
        self, ce_client: Any, account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Find cost anomalies using Cost Explorer Anomaly Detection.

        Args:
            ce_client: Boto3 Cost Explorer client
            account_id: AWS account ID

        Returns:
            List of cost anomaly findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            # Get anomalies from the last 30 days
            end_date = datetime.utcnow().strftime("%Y-%m-%d")
            start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

            response = ce_client.get_anomalies(
                DateInterval={"StartDate": start_date, "EndDate": end_date},
                MaxResults=100,
            )

            for anomaly in response.get("Anomalies", []):
                anomaly_id = anomaly.get("AnomalyId", "unknown")
                impact = anomaly.get("Impact", {})
                total_impact = float(impact.get("TotalImpact", 0))

                # Only report significant anomalies
                if total_impact > 0:
                    findings.append(
                        self._create_cost_anomaly_finding(
                            anomaly_id=anomaly_id,
                            anomaly=anomaly,
                            account_id=account_id,
                        )
                    )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "UnrecognizedClientException":
                logger.warning("Cost Anomaly Detection not enabled for account")
            else:
                logger.warning(f"Failed to get cost anomalies: {e}")

        return findings

    def _get_ri_recommendations(
        self, ce_client: Any, account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get Reserved Instance purchase recommendations.

        Args:
            ce_client: Boto3 Cost Explorer client
            account_id: AWS account ID

        Returns:
            List of RI recommendation findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            # Get EC2 RI recommendations
            response = ce_client.get_reservation_purchase_recommendation(
                Service="Amazon Elastic Compute Cloud - Compute",
                LookbackPeriodInDays="SIXTY_DAYS",
                TermInYears="ONE_YEAR",
                PaymentOption="NO_UPFRONT",
            )

            for rec in response.get("Recommendations", []):
                for detail in rec.get("RecommendationDetails", []):
                    instance_type = (
                        detail.get("InstanceDetails", {})
                        .get("EC2InstanceDetails", {})
                        .get("InstanceType", "unknown")
                    )

                    estimated_savings = float(
                        detail.get("EstimatedMonthlySavingsAmount", 0)
                    )

                    if estimated_savings > 0:
                        findings.append(
                            self._create_ri_recommendation_finding(
                                instance_type=instance_type,
                                detail=detail,
                                account_id=account_id,
                            )
                        )

        except ClientError as e:
            logger.warning(f"Failed to get RI recommendations: {e}")

        return findings

    def _get_rightsizing_recommendations(
        self, ce_client: Any, account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get EC2 rightsizing recommendations.

        Args:
            ce_client: Boto3 Cost Explorer client
            account_id: AWS account ID

        Returns:
            List of rightsizing recommendation findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            response = ce_client.get_rightsizing_recommendation(
                Service="AmazonEC2",
            )

            for rec in response.get("RightsizingRecommendations", []):
                current = rec.get("CurrentInstance", {})
                resource_id = current.get("ResourceId", "unknown")
                resource_details = current.get("ResourceDetails", {}).get(
                    "EC2ResourceDetails", {}
                )
                current_type = resource_details.get("InstanceType", "unknown")

                # Get target recommendation
                modify_rec = rec.get("ModifyRecommendationDetail", {})
                target_options = modify_rec.get("TargetInstances", [])

                if target_options:
                    target = target_options[0]
                    target_type = (
                        target.get("ResourceDetails", {})
                        .get("EC2ResourceDetails", {})
                        .get("InstanceType", "unknown")
                    )

                    estimated_savings = float(target.get("EstimatedMonthlySavings", 0))

                    if estimated_savings > 0:
                        findings.append(
                            self._create_rightsizing_finding(
                                resource_id=resource_id,
                                current_type=current_type,
                                target_type=target_type,
                                estimated_savings=estimated_savings,
                                account_id=account_id,
                            )
                        )

        except ClientError as e:
            logger.warning(f"Failed to get rightsizing recommendations: {e}")

        return findings

    def _find_idle_resources(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Find idle/underutilized resources.

        Args:
            account_id: AWS account ID

        Returns:
            List of idle resource findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            # Check for idle EBS volumes (not attached)
            ec2_client = self.get_client("ec2")
            volumes = ec2_client.describe_volumes(
                Filters=[{"Name": "status", "Values": ["available"]}]
            )

            for volume in volumes.get("Volumes", []):
                volume_id = volume["VolumeId"]
                size_gb = volume.get("Size", 0)
                create_time = volume.get("CreateTime")

                # Check if volume has been idle for threshold days
                if create_time:
                    days_idle = (
                        datetime.utcnow() - create_time.replace(tzinfo=None)
                    ).days
                    if days_idle >= self.IDLE_DAYS_THRESHOLD:
                        findings.append(
                            self._create_idle_resource_finding(
                                resource_id=volume_id,
                                resource_type="ebs_volume",
                                days_idle=days_idle,
                                size_gb=size_gb,
                                account_id=account_id,
                            )
                        )

            # Check for unattached Elastic IPs
            addresses = ec2_client.describe_addresses()
            for address in addresses.get("Addresses", []):
                if "InstanceId" not in address and "NetworkInterfaceId" not in address:
                    allocation_id = address.get("AllocationId", "unknown")
                    public_ip = address.get("PublicIp", "unknown")

                    findings.append(
                        self._create_idle_eip_finding(
                            allocation_id=allocation_id,
                            public_ip=public_ip,
                            account_id=account_id,
                        )
                    )

        except ClientError as e:
            logger.warning(f"Failed to find idle resources: {e}")

        return findings

    def _create_cost_anomaly_finding(
        self, anomaly_id: str, anomaly: Dict[str, Any], account_id: str
    ) -> Dict[str, Any]:
        """Create finding for cost anomaly."""
        impact = anomaly.get("Impact", {})
        total_impact = float(impact.get("TotalImpact", 0))
        root_causes = anomaly.get("RootCauses", [])

        # Determine severity based on impact
        if total_impact > 1000:
            severity = "critical"
        elif total_impact > 500:
            severity = "high"
        elif total_impact > 100:
            severity = "medium"
        else:
            severity = "low"

        root_cause_str = ""
        if root_causes:
            cause = root_causes[0]
            root_cause_str = (
                f"{cause.get('Service', 'Unknown')} - {cause.get('Region', 'Unknown')}"
            )

        return {
            "finding_type": "cost_anomaly",
            "severity": severity,
            "title": f"Cost anomaly detected: ${total_impact:.2f} impact",
            "description": (
                f"Unusual spending pattern detected with estimated impact of "
                f"${total_impact:.2f}. Root cause: {root_cause_str or 'Unknown'}"
            ),
            "resource_arn": f"arn:aws:ce:{self.region}:{account_id}:anomaly/{anomaly_id}",
            "resource_id": anomaly_id,
            "resource_name": f"cost-anomaly-{anomaly_id[:8]}",
            "resource_type": "cost_anomaly",
            "aws_account_id": account_id,
            "region": "global",
            "remediation": (
                "Review the anomaly in AWS Cost Explorer Anomaly Detection. "
                "Investigate the root cause service and take corrective action."
            ),
            "metadata": {
                "anomaly_id": anomaly_id,
                "total_impact": total_impact,
                "root_causes": root_causes,
            },
        }

    def _create_ri_recommendation_finding(
        self, instance_type: str, detail: Dict[str, Any], account_id: str
    ) -> Dict[str, Any]:
        """Create finding for RI recommendation."""
        estimated_savings = float(detail.get("EstimatedMonthlySavingsAmount", 0))
        upfront_cost = float(detail.get("UpfrontCost", 0))
        recommended_count = int(detail.get("RecommendedNumberOfInstancesToPurchase", 0))

        return {
            "finding_type": "reserved_instance_recommendation",
            "severity": "medium",
            "title": f"RI recommendation: {instance_type} (save ${estimated_savings:.2f}/month)",
            "description": (
                f"Purchase {recommended_count} Reserved Instance(s) of type {instance_type} "
                f"to save approximately ${estimated_savings:.2f} per month. "
                f"Upfront cost: ${upfront_cost:.2f}"
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:reserved-instances/{instance_type}",
            "resource_id": instance_type,
            "resource_name": f"ri-recommendation-{instance_type}",
            "resource_type": "reserved_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Consider purchasing {recommended_count} Reserved Instance(s) of type "
                f"{instance_type}. Review usage patterns in AWS Cost Explorer before purchasing."
            ),
            "metadata": {
                "instance_type": instance_type,
                "estimated_monthly_savings": estimated_savings,
                "upfront_cost": upfront_cost,
                "recommended_count": recommended_count,
            },
        }

    def _create_rightsizing_finding(
        self,
        resource_id: str,
        current_type: str,
        target_type: str,
        estimated_savings: float,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for rightsizing recommendation."""
        return {
            "finding_type": "rightsizing_recommendation",
            "severity": "medium",
            "title": f"Rightsizing: {resource_id} ({current_type} -> {target_type})",
            "description": (
                f"EC2 instance {resource_id} can be resized from {current_type} to "
                f"{target_type} to save approximately ${estimated_savings:.2f} per month."
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:instance/{resource_id}",
            "resource_id": resource_id,
            "resource_name": resource_id,
            "resource_type": "ec2_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Resize instance {resource_id} from {current_type} to {target_type}. "
                "Stop the instance, change instance type, and restart."
            ),
            "metadata": {
                "resource_id": resource_id,
                "current_type": current_type,
                "target_type": target_type,
                "estimated_monthly_savings": estimated_savings,
            },
        }

    def _create_idle_resource_finding(
        self,
        resource_id: str,
        resource_type: str,
        days_idle: int,
        size_gb: int,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for idle resource."""
        # Estimate monthly cost (rough estimate: $0.10/GB/month for EBS)
        estimated_monthly_cost = size_gb * 0.10

        return {
            "finding_type": "idle_resource",
            "severity": "low",
            "title": f"Idle EBS volume: {resource_id} ({size_gb} GB, {days_idle} days unused)",
            "description": (
                f"EBS volume {resource_id} ({size_gb} GB) has been unattached for "
                f"{days_idle} days. Estimated monthly cost: ${estimated_monthly_cost:.2f}"
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:volume/{resource_id}",
            "resource_id": resource_id,
            "resource_name": resource_id,
            "resource_type": resource_type,
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Review if EBS volume {resource_id} is still needed. "
                "If not, create a snapshot for backup and delete the volume."
            ),
            "metadata": {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "size_gb": size_gb,
                "days_idle": days_idle,
                "estimated_monthly_cost": estimated_monthly_cost,
            },
        }

    def _create_idle_eip_finding(
        self, allocation_id: str, public_ip: str, account_id: str
    ) -> Dict[str, Any]:
        """Create finding for unattached Elastic IP."""
        # Unattached EIPs cost ~$3.60/month
        estimated_monthly_cost = 3.60

        return {
            "finding_type": "idle_resource",
            "severity": "low",
            "title": f"Unattached Elastic IP: {public_ip}",
            "description": (
                f"Elastic IP {public_ip} is not attached to any instance or network interface. "
                f"Unattached EIPs cost approximately ${estimated_monthly_cost:.2f}/month."
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:elastic-ip/{allocation_id}",
            "resource_id": allocation_id,
            "resource_name": public_ip,
            "resource_type": "elastic_ip",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Either attach Elastic IP {public_ip} to an instance or release it "
                "if no longer needed."
            ),
            "metadata": {
                "allocation_id": allocation_id,
                "public_ip": public_ip,
                "estimated_monthly_cost": estimated_monthly_cost,
            },
        }
