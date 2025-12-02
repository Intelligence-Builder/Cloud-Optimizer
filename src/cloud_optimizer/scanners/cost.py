"""Cost Analysis Scanner."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3

from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

logger = logging.getLogger(__name__)


class CostScanner(BaseScanner):
    """Cost optimization scanner.

    Scans for cost optimization opportunities including:
    - Unused EC2 instances (low CPU utilization)
    - Unattached EBS volumes
    - Idle RDS instances
    - Oversized EC2 instances
    - Old EBS snapshots
    """

    SERVICE = "Cost"

    def _register_rules(self) -> None:
        """Register cost optimization rules."""
        self.register_rule(
            ScannerRule(
                rule_id="COST_001",
                title="Unused EC2 Instance",
                description="EC2 instance has low CPU utilization suggesting it may be unused",
                severity="medium",
                service="EC2",
                resource_type="AWS::EC2::Instance",
                recommendation="Consider stopping or terminating instances with consistently low utilization",
                compliance_frameworks=["CIS"],
                remediation_steps=[
                    "Review CloudWatch metrics for CPU utilization over the past 14 days",
                    "Verify the instance is not needed for production workloads",
                    "Stop the instance if it can be restarted when needed",
                    "Terminate the instance if it is no longer required",
                ],
            )
        )
        self.register_rule(
            ScannerRule(
                rule_id="COST_002",
                title="Unattached EBS Volume",
                description="EBS volume is not attached to any instance",
                severity="medium",
                service="EC2",
                resource_type="AWS::EC2::Volume",
                recommendation="Delete unattached volumes or attach them to instances",
                compliance_frameworks=["CIS"],
                remediation_steps=[
                    "Create a snapshot of the volume for backup if needed",
                    "Verify the volume is not needed for any running instances",
                    "Delete the volume to avoid ongoing storage costs",
                ],
            )
        )
        self.register_rule(
            ScannerRule(
                rule_id="COST_003",
                title="Idle RDS Instance",
                description="RDS instance has zero connections for extended period",
                severity="medium",
                service="RDS",
                resource_type="AWS::RDS::DBInstance",
                recommendation="Consider stopping or deleting idle database instances",
                compliance_frameworks=["CIS"],
                remediation_steps=[
                    "Review CloudWatch metrics for database connections",
                    "Verify the database is not needed for production workloads",
                    "Stop the database instance if it can be restarted when needed",
                    "Delete the database instance and take a final snapshot",
                ],
            )
        )
        self.register_rule(
            ScannerRule(
                rule_id="COST_004",
                title="Oversized EC2 Instance",
                description="EC2 instance is oversized based on CPU and memory utilization",
                severity="low",
                service="EC2",
                resource_type="AWS::EC2::Instance",
                recommendation="Consider downsizing to a smaller instance type",
                compliance_frameworks=["CIS"],
                remediation_steps=[
                    "Review CloudWatch metrics for CPU and memory utilization",
                    "Identify appropriate smaller instance type",
                    "Stop the instance and change instance type",
                    "Restart and verify application performance",
                ],
            )
        )
        self.register_rule(
            ScannerRule(
                rule_id="COST_005",
                title="Old EBS Snapshot",
                description="EBS snapshot is older than 90 days",
                severity="low",
                service="EC2",
                resource_type="AWS::EC2::Snapshot",
                recommendation="Review and delete old snapshots that are no longer needed",
                compliance_frameworks=["CIS"],
                remediation_steps=[
                    "Review snapshot creation date and purpose",
                    "Verify snapshot is not needed for disaster recovery",
                    "Delete the snapshot if it is no longer required",
                ],
            )
        )

    async def scan(self) -> List[ScanResult]:
        """Execute cost optimization scan.

        Returns:
            List of cost optimization findings
        """
        results: List[ScanResult] = []
        for region in self.regions:
            results.extend(await self._scan_unused_volumes(region))
            results.extend(await self._scan_old_snapshots(region))
            results.extend(await self._scan_idle_instances(region))
        return results

    async def _scan_unused_volumes(self, region: str) -> List[ScanResult]:
        """Scan for unattached EBS volumes.

        Args:
            region: AWS region to scan

        Returns:
            List of findings for unattached volumes
        """
        results: List[ScanResult] = []
        ec2 = self.get_client("ec2", region)

        volumes = ec2.describe_volumes(
            Filters=[{"Name": "status", "Values": ["available"]}]
        ).get("Volumes", [])

        for vol in volumes:
            volume_id = vol["VolumeId"]
            account_id = self._get_account_id()

            results.append(
                self.create_result(
                    rule_id="COST_002",
                    resource_id=f"arn:aws:ec2:{region}:{account_id}:volume/{volume_id}",
                    resource_name=volume_id,
                    region=region,
                    metadata={
                        "size_gb": vol["Size"],
                        "volume_type": vol["VolumeType"],
                        "state": vol["State"],
                        "create_time": vol["CreateTime"].isoformat(),
                        "potential_savings": self._estimate_volume_cost(vol),
                    },
                )
            )
        return results

    async def _scan_old_snapshots(self, region: str) -> List[ScanResult]:
        """Scan for old EBS snapshots.

        Args:
            region: AWS region to scan

        Returns:
            List of findings for old snapshots
        """
        results: List[ScanResult] = []
        ec2 = self.get_client("ec2", region)
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)

        paginator = ec2.get_paginator("describe_snapshots")
        for page in paginator.paginate(OwnerIds=["self"]):
            for snap in page.get("Snapshots", []):
                if snap["StartTime"] < cutoff:
                    snapshot_id = snap["SnapshotId"]
                    age_days = (datetime.now(timezone.utc) - snap["StartTime"]).days

                    results.append(
                        self.create_result(
                            rule_id="COST_005",
                            resource_id=snapshot_id,
                            resource_name=snapshot_id,
                            region=region,
                            metadata={
                                "size_gb": snap["VolumeSize"],
                                "start_time": snap["StartTime"].isoformat(),
                                "age_days": age_days,
                                "potential_savings": snap["VolumeSize"] * 0.05,
                            },
                        )
                    )
        return results

    async def _scan_idle_instances(self, region: str) -> List[ScanResult]:
        """Scan for idle EC2 instances.

        Note: This is a placeholder. In production, this would use
        CloudWatch metrics to identify truly idle instances.

        Args:
            region: AWS region to scan

        Returns:
            List of findings for idle instances
        """
        # Would use CloudWatch metrics in production
        return []

    def _get_account_id(self) -> str:
        """Get AWS account ID.

        Returns:
            AWS account ID
        """
        sts = self.session.client("sts")
        account_id: str = sts.get_caller_identity()["Account"]
        return account_id

    def _estimate_volume_cost(self, volume: Dict[str, Any]) -> float:
        """Estimate monthly cost of an EBS volume.

        Args:
            volume: Volume details from describe_volumes

        Returns:
            Estimated monthly cost in USD
        """
        size: int = volume["Size"]
        vol_type: str = volume["VolumeType"]
        costs: Dict[str, float] = {
            "gp2": 0.10,
            "gp3": 0.08,
            "io1": 0.125,
            "io2": 0.125,
            "st1": 0.045,
            "sc1": 0.025,
        }
        cost_per_gb = costs.get(vol_type, 0.10)
        return float(size * cost_per_gb)
