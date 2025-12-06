"""RDS Security Scanner."""

import logging
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

logger = logging.getLogger(__name__)


class RDSScanner(BaseScanner):
    """Scanner for RDS security configurations."""

    SERVICE = "RDS"

    def _register_rules(self) -> None:
        """Register RDS security rules."""
        self.register_rule(
            ScannerRule(
                rule_id="RDS_001",
                title="RDS Instance Publicly Accessible",
                description="RDS database instance is configured to be publicly accessible",
                severity="critical",
                service="RDS",
                resource_type="AWS::RDS::DBInstance",
                recommendation="Disable public accessibility and use VPC security groups",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Modify DB instance to disable public accessibility",
                    "Ensure DB is in private subnet",
                    "Use VPN or Direct Connect for external access",
                    "Implement bastion host or AWS Systems Manager for access",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_CommonTasks.Connect.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="RDS_002",
                title="RDS Storage Not Encrypted",
                description="RDS database instance does not have storage encryption enabled",
                severity="high",
                service="RDS",
                resource_type="AWS::RDS::DBInstance",
                recommendation="Enable encryption at rest using KMS",
                compliance_frameworks=["PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Create encrypted snapshot of database",
                    "Restore snapshot to new encrypted instance",
                    "Update application connection strings",
                    "Enable encryption by default for new instances",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="RDS_003",
                title="RDS Automated Backups Not Enabled",
                description="RDS database instance does not have automated backups configured",
                severity="medium",
                service="RDS",
                resource_type="AWS::RDS::DBInstance",
                recommendation="Enable automated backups with appropriate retention period",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Set backup retention period to at least 7 days",
                    "Configure preferred backup window",
                    "Enable backup replication to another region for DR",
                    "Test backup restoration regularly",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="RDS_004",
                title="RDS Multi-AZ Not Enabled",
                description="RDS database instance is not configured for Multi-AZ deployment",
                severity="medium",
                service="RDS",
                resource_type="AWS::RDS::DBInstance",
                recommendation="Enable Multi-AZ for high availability and automatic failover",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Modify DB instance to enable Multi-AZ",
                    "Plan maintenance window for Multi-AZ conversion",
                    "Test failover procedures",
                    "Monitor replication lag and performance",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="RDS_005",
                title="RDS Using Default Port",
                description="RDS database instance is using the default port for its engine",
                severity="low",
                service="RDS",
                resource_type="AWS::RDS::DBInstance",
                recommendation="Use non-default port to reduce exposure to automated attacks",
                compliance_frameworks=[],
                remediation_steps=[
                    "Modify DB instance to use non-default port",
                    "Update application connection strings",
                    "Update security group rules",
                    "Document port changes in runbooks",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Limits.html",
            )
        )

    async def scan(self) -> List[ScanResult]:
        """
        Scan RDS resources for security issues.

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        # Default ports for different RDS engines
        self.default_ports = {
            "mysql": 3306,
            "postgres": 5432,
            "mariadb": 3306,
            "oracle": 1521,
            "sqlserver": 1433,
            "aurora-mysql": 3306,
            "aurora-postgresql": 5432,
        }

        for region in self.regions:
            try:
                rds = self.get_client("rds", region=region)
                logger.info(f"Scanning RDS resources in {region}")

                # Check RDS instances
                results.extend(await self._check_db_instances(rds, region))

                # Check RDS clusters (Aurora)
                results.extend(await self._check_db_clusters(rds, region))

            except ClientError as e:
                logger.error(f"Error scanning RDS in {region}: {e}")

        return results

    async def _check_db_instances(self, rds: Any, region: str) -> List[ScanResult]:
        """Check RDS DB instances."""
        results: List[ScanResult] = []

        try:
            paginator = rds.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                instances = page.get("DBInstances", [])

                for instance in instances:
                    db_instance_id = instance["DBInstanceIdentifier"]
                    db_arn = instance["DBInstanceArn"]
                    engine = instance.get("Engine", "").lower()
                    port = instance.get("DbInstancePort") or instance.get(
                        "Endpoint", {}
                    ).get("Port")

                    # Check public accessibility (RDS_001)
                    if instance.get("PubliclyAccessible", False):
                        results.append(
                            self.create_result(
                                rule_id="RDS_001",
                                resource_id=db_arn,
                                resource_name=db_instance_id,
                                region=region,
                                metadata={
                                    "engine": engine,
                                    "endpoint": instance.get("Endpoint", {}),
                                },
                            )
                        )

                    # Check storage encryption (RDS_002)
                    if not instance.get("StorageEncrypted", False):
                        results.append(
                            self.create_result(
                                rule_id="RDS_002",
                                resource_id=db_arn,
                                resource_name=db_instance_id,
                                region=region,
                                metadata={
                                    "engine": engine,
                                    "storage_type": instance.get("StorageType"),
                                },
                            )
                        )

                    # Check automated backups (RDS_003)
                    backup_retention = instance.get("BackupRetentionPeriod", 0)
                    if backup_retention < 7:
                        results.append(
                            self.create_result(
                                rule_id="RDS_003",
                                resource_id=db_arn,
                                resource_name=db_instance_id,
                                region=region,
                                metadata={
                                    "backup_retention_period": backup_retention,
                                    "preferred_backup_window": instance.get(
                                        "PreferredBackupWindow"
                                    ),
                                },
                            )
                        )

                    # Check Multi-AZ (RDS_004)
                    if not instance.get("MultiAZ", False):
                        results.append(
                            self.create_result(
                                rule_id="RDS_004",
                                resource_id=db_arn,
                                resource_name=db_instance_id,
                                region=region,
                                metadata={
                                    "availability_zone": instance.get(
                                        "AvailabilityZone"
                                    ),
                                    "engine": engine,
                                },
                            )
                        )

                    # Check default port (RDS_005)
                    default_port = self.default_ports.get(engine)
                    if port and default_port and port == default_port:
                        results.append(
                            self.create_result(
                                rule_id="RDS_005",
                                resource_id=db_arn,
                                resource_name=db_instance_id,
                                region=region,
                                metadata={
                                    "engine": engine,
                                    "port": port,
                                    "default_port": default_port,
                                },
                            )
                        )

        except ClientError as e:
            logger.error(f"Error checking RDS instances in {region}: {e}")

        return results

    async def _check_db_clusters(self, rds: Any, region: str) -> List[ScanResult]:
        """Check RDS DB clusters (Aurora)."""
        results: List[ScanResult] = []

        try:
            paginator = rds.get_paginator("describe_db_clusters")
            for page in paginator.paginate():
                clusters = page.get("DBClusters", [])

                for cluster in clusters:
                    cluster_id = cluster["DBClusterIdentifier"]
                    cluster_arn = cluster["DBClusterArn"]
                    engine = cluster.get("Engine", "").lower()
                    port = cluster.get("Port")

                    # Aurora clusters can't be publicly accessible directly,
                    # but we check the instances in the cluster
                    # This is handled in _check_db_instances

                    # Check storage encryption (RDS_002)
                    if not cluster.get("StorageEncrypted", False):
                        results.append(
                            self.create_result(
                                rule_id="RDS_002",
                                resource_id=cluster_arn,
                                resource_name=cluster_id,
                                region=region,
                                metadata={
                                    "engine": engine,
                                    "cluster": True,
                                },
                            )
                        )

                    # Check automated backups (RDS_003)
                    backup_retention = cluster.get("BackupRetentionPeriod", 0)
                    if backup_retention < 7:
                        results.append(
                            self.create_result(
                                rule_id="RDS_003",
                                resource_id=cluster_arn,
                                resource_name=cluster_id,
                                region=region,
                                metadata={
                                    "backup_retention_period": backup_retention,
                                    "preferred_backup_window": cluster.get(
                                        "PreferredBackupWindow"
                                    ),
                                    "cluster": True,
                                },
                            )
                        )

                    # Check Multi-AZ (RDS_004)
                    # Aurora clusters are inherently Multi-AZ if they have instances
                    # in multiple AZs
                    cluster_members = cluster.get("DBClusterMembers", [])
                    if len(cluster_members) < 2:
                        results.append(
                            self.create_result(
                                rule_id="RDS_004",
                                resource_id=cluster_arn,
                                resource_name=cluster_id,
                                region=region,
                                metadata={
                                    "cluster_members": len(cluster_members),
                                    "engine": engine,
                                    "cluster": True,
                                },
                            )
                        )

                    # Check default port (RDS_005)
                    default_port = self.default_ports.get(engine)
                    if port and default_port and port == default_port:
                        results.append(
                            self.create_result(
                                rule_id="RDS_005",
                                resource_id=cluster_arn,
                                resource_name=cluster_id,
                                region=region,
                                metadata={
                                    "engine": engine,
                                    "port": port,
                                    "default_port": default_port,
                                    "cluster": True,
                                },
                            )
                        )

        except ClientError as e:
            logger.error(f"Error checking RDS clusters in {region}: {e}")

        return results
