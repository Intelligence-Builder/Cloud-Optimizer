"""EC2 Security Scanner."""

import logging
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

logger = logging.getLogger(__name__)


class EC2Scanner(BaseScanner):
    """Scanner for EC2 security configurations."""

    SERVICE = "EC2"

    def _register_rules(self) -> None:
        """Register EC2 security rules."""
        self.register_rule(
            ScannerRule(
                rule_id="EC2_001",
                title="Security Group Allows 0.0.0.0/0 on SSH (Port 22)",
                description="Security group allows SSH access from the internet",
                severity="critical",
                service="EC2",
                resource_type="AWS::EC2::SecurityGroup",
                recommendation="Restrict SSH access to specific IP addresses or use VPN/bastion host",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Modify security group to restrict SSH to known IP addresses",
                    "Use AWS Systems Manager Session Manager instead of SSH",
                    "Implement bastion host architecture",
                    "Enable VPC Flow Logs for monitoring",
                ],
                documentation_url="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/security-group-rules.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="EC2_002",
                title="Security Group Allows 0.0.0.0/0 on RDP (Port 3389)",
                description="Security group allows RDP access from the internet",
                severity="critical",
                service="EC2",
                resource_type="AWS::EC2::SecurityGroup",
                recommendation="Restrict RDP access to specific IP addresses or use VPN",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Modify security group to restrict RDP to known IP addresses",
                    "Use AWS Systems Manager Session Manager",
                    "Implement Remote Desktop Gateway",
                    "Enable VPC Flow Logs for monitoring",
                ],
                documentation_url="https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/connecting_to_windows_instance.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="EC2_003",
                title="EBS Volume Not Encrypted",
                description="EBS volume does not have encryption enabled",
                severity="high",
                service="EC2",
                resource_type="AWS::EC2::Volume",
                recommendation="Enable EBS encryption for data at rest",
                compliance_frameworks=["PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Create encrypted snapshot of the volume",
                    "Create new encrypted volume from snapshot",
                    "Replace unencrypted volume with encrypted one",
                    "Enable EBS encryption by default in account settings",
                ],
                documentation_url="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EBSEncryption.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="EC2_004",
                title="Instance Using IMDSv1",
                description="EC2 instance is not enforcing IMDSv2 (Instance Metadata Service Version 2)",
                severity="medium",
                service="EC2",
                resource_type="AWS::EC2::Instance",
                recommendation="Require IMDSv2 to protect against SSRF attacks",
                compliance_frameworks=["CIS"],
                remediation_steps=[
                    "Modify instance metadata options to require IMDSv2",
                    "Update application code to use IMDSv2 token-based authentication",
                    "Test applications before enforcing IMDSv2",
                ],
                documentation_url="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="EC2_005",
                title="Instance Has Public IP Address",
                description="EC2 instance has a public IP address assigned",
                severity="medium",
                service="EC2",
                resource_type="AWS::EC2::Instance",
                recommendation="Use private subnets with NAT Gateway for outbound internet access",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Move instance to private subnet",
                    "Use NAT Gateway for outbound internet access",
                    "Use load balancer for inbound traffic",
                    "Implement proper network segmentation",
                ],
                documentation_url="https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html",
            )
        )

    async def scan(self) -> List[ScanResult]:
        """
        Scan EC2 resources for security issues.

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        for region in self.regions:
            try:
                ec2 = self.get_client("ec2", region=region)
                logger.info(f"Scanning EC2 resources in {region}")

                # Check security groups
                results.extend(await self._check_security_groups(ec2, region))

                # Check EBS volumes
                results.extend(await self._check_ebs_volumes(ec2, region))

                # Check EC2 instances
                results.extend(await self._check_instances(ec2, region))

            except ClientError as e:
                logger.error(f"Error scanning EC2 in {region}: {e}")

        return results

    async def _check_security_groups(self, ec2: Any, region: str) -> List[ScanResult]:
        """Check EC2_001 and EC2_002: Security group rules."""
        results: List[ScanResult] = []

        try:
            response = ec2.describe_security_groups()
            security_groups = response.get("SecurityGroups", [])

            for sg in security_groups:
                sg_id = sg["GroupId"]
                sg_name = sg.get("GroupName", sg_id)
                vpc_id = sg.get("VpcId", "")

                # Check ingress rules
                for rule in sg.get("IpPermissions", []):
                    from_port = rule.get("FromPort")
                    to_port = rule.get("ToPort")

                    # Check for 0.0.0.0/0 CIDR
                    for ip_range in rule.get("IpRanges", []):
                        cidr = ip_range.get("CidrIp", "")

                        if cidr == "0.0.0.0/0":
                            # Check for SSH (port 22)
                            if (
                                from_port == 22
                                or to_port == 22
                                or (from_port is None and to_port is None)
                            ):
                                results.append(
                                    self.create_result(
                                        rule_id="EC2_001",
                                        resource_id=f"arn:aws:ec2:{region}:account:security-group/{sg_id}",
                                        resource_name=sg_name,
                                        region=region,
                                        metadata={
                                            "security_group_id": sg_id,
                                            "vpc_id": vpc_id,
                                            "rule": rule,
                                        },
                                    )
                                )

                            # Check for RDP (port 3389)
                            if from_port == 3389 or to_port == 3389:
                                results.append(
                                    self.create_result(
                                        rule_id="EC2_002",
                                        resource_id=f"arn:aws:ec2:{region}:account:security-group/{sg_id}",
                                        resource_name=sg_name,
                                        region=region,
                                        metadata={
                                            "security_group_id": sg_id,
                                            "vpc_id": vpc_id,
                                            "rule": rule,
                                        },
                                    )
                                )

        except ClientError as e:
            logger.error(f"Error checking security groups in {region}: {e}")

        return results

    async def _check_ebs_volumes(self, ec2: Any, region: str) -> List[ScanResult]:
        """Check EC2_003: EBS encryption."""
        results: List[ScanResult] = []

        try:
            response = ec2.describe_volumes()
            volumes = response.get("Volumes", [])

            for volume in volumes:
                volume_id = volume["VolumeId"]
                encrypted = volume.get("Encrypted", False)

                if not encrypted:
                    # Get volume name from tags
                    volume_name = volume_id
                    for tag in volume.get("Tags", []):
                        if tag["Key"] == "Name":
                            volume_name = tag["Value"]
                            break

                    results.append(
                        self.create_result(
                            rule_id="EC2_003",
                            resource_id=f"arn:aws:ec2:{region}:account:volume/{volume_id}",
                            resource_name=volume_name,
                            region=region,
                            metadata={
                                "volume_id": volume_id,
                                "size": volume.get("Size"),
                                "volume_type": volume.get("VolumeType"),
                                "state": volume.get("State"),
                            },
                        )
                    )

        except ClientError as e:
            logger.error(f"Error checking EBS volumes in {region}: {e}")

        return results

    async def _check_instances(self, ec2: Any, region: str) -> List[ScanResult]:
        """Check EC2_004 and EC2_005: Instance configurations."""
        results: List[ScanResult] = []

        try:
            response = ec2.describe_instances()
            reservations = response.get("Reservations", [])

            for reservation in reservations:
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    state = instance.get("State", {}).get("Name", "")

                    # Skip terminated instances
                    if state == "terminated":
                        continue

                    # Get instance name from tags
                    instance_name = instance_id
                    for tag in instance.get("Tags", []):
                        if tag["Key"] == "Name":
                            instance_name = tag["Value"]
                            break

                    # Check IMDSv2 (EC2_004)
                    metadata_options = instance.get("MetadataOptions", {})
                    http_tokens = metadata_options.get("HttpTokens", "optional")

                    if http_tokens != "required":
                        results.append(
                            self.create_result(
                                rule_id="EC2_004",
                                resource_id=f"arn:aws:ec2:{region}:account:instance/{instance_id}",
                                resource_name=instance_name,
                                region=region,
                                metadata={
                                    "instance_id": instance_id,
                                    "http_tokens": http_tokens,
                                    "instance_type": instance.get("InstanceType"),
                                    "state": state,
                                },
                            )
                        )

                    # Check public IP (EC2_005)
                    public_ip = instance.get("PublicIpAddress")
                    if public_ip:
                        results.append(
                            self.create_result(
                                rule_id="EC2_005",
                                resource_id=f"arn:aws:ec2:{region}:account:instance/{instance_id}",
                                resource_name=instance_name,
                                region=region,
                                metadata={
                                    "instance_id": instance_id,
                                    "public_ip": public_ip,
                                    "instance_type": instance.get("InstanceType"),
                                    "subnet_id": instance.get("SubnetId"),
                                    "state": state,
                                },
                            )
                        )

        except ClientError as e:
            logger.error(f"Error checking EC2 instances in {region}: {e}")

        return results
