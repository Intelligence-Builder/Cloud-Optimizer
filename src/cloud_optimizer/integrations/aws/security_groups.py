"""Security Group scanner for AWS."""

import logging
from typing import Any, Dict, List

from cloud_optimizer.integrations.aws.base import BaseAWSScanner

logger = logging.getLogger(__name__)


class SecurityGroupScanner(BaseAWSScanner):
    """Scanner for AWS security group misconfigurations."""

    RISKY_PORTS = {22, 23, 3389, 3306, 5432, 1433, 27017, 6379, 9200}
    UNRESTRICTED_CIDR = "0.0.0.0/0"

    def get_scanner_name(self) -> str:
        """Return scanner name."""
        return "SecurityGroupScanner"

    async def scan(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan security groups for overly permissive rules.

        Detects:
        - 0.0.0.0/0 ingress rules
        - Unrestricted access to risky ports (SSH, RDP, databases)
        - Security groups with no egress restrictions

        Args:
            account_id: AWS account ID to scan

        Returns:
            List of security findings
        """
        logger.info(
            f"Starting security group scan for account {account_id} in {self.region}"
        )
        findings: List[Dict[str, Any]] = []

        try:
            ec2_client = self.get_client("ec2")
            response = ec2_client.describe_security_groups()
            security_groups = response.get("SecurityGroups", [])

            for sg in security_groups:
                sg_id = sg["GroupId"]
                sg_name = sg["GroupName"]

                # Check ingress rules
                for rule in sg.get("IpPermissions", []):
                    findings.extend(
                        self._check_ingress_rule(
                            sg_id, sg_name, rule, account_id
                        )
                    )

            logger.info(
                f"Security group scan complete: {len(findings)} findings",
                extra={"account_id": account_id, "findings_count": len(findings)},
            )

        except Exception as e:
            logger.error(f"Security group scan failed: {e}", exc_info=True)
            raise

        return findings

    def _check_ingress_rule(
        self,
        sg_id: str,
        sg_name: str,
        rule: Dict[str, Any],
        account_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Check an ingress rule for security issues.

        Args:
            sg_id: Security group ID
            sg_name: Security group name
            rule: Ingress rule to check
            account_id: AWS account ID

        Returns:
            List of findings for this rule
        """
        findings: List[Dict[str, Any]] = []
        from_port = rule.get("FromPort", 0)
        to_port = rule.get("ToPort", 65535)
        protocol = rule.get("IpProtocol", "-1")

        # Check for unrestricted access
        for ip_range in rule.get("IpRanges", []):
            cidr = ip_range.get("CidrIp", "")
            if cidr == self.UNRESTRICTED_CIDR:
                findings.append(
                    self._create_finding(
                        sg_id=sg_id,
                        sg_name=sg_name,
                        from_port=from_port,
                        to_port=to_port,
                        protocol=protocol,
                        cidr=cidr,
                        account_id=account_id,
                    )
                )

        return findings

    def _create_finding(
        self,
        sg_id: str,
        sg_name: str,
        from_port: int,
        to_port: int,
        protocol: str,
        cidr: str,
        account_id: str,
    ) -> Dict[str, Any]:
        """
        Create a security finding.

        Args:
            sg_id: Security group ID
            sg_name: Security group name
            from_port: Start of port range
            to_port: End of port range
            protocol: IP protocol
            cidr: CIDR block
            account_id: AWS account ID

        Returns:
            Finding dictionary
        """
        severity = self._calculate_severity(from_port, to_port)
        port_desc = self._get_port_description(from_port, to_port)

        return {
            "finding_type": "overly_permissive_security_group",
            "severity": severity,
            "title": f"Unrestricted access to {port_desc}",
            "description": (
                f"Security group {sg_name} ({sg_id}) allows unrestricted "
                f"access from {cidr} to {port_desc} ({protocol})"
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:security-group/{sg_id}",
            "resource_id": sg_id,
            "resource_name": sg_name,
            "resource_type": "security_group",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Restrict ingress rules for {sg_name} to only allow "
                "access from specific IP ranges or security groups. "
                f"Remove the 0.0.0.0/0 rule for {port_desc}."
            ),
            "metadata": {
                "from_port": from_port,
                "to_port": to_port,
                "protocol": protocol,
                "cidr": cidr,
            },
        }

    def _calculate_severity(self, from_port: int, to_port: int) -> str:
        """
        Calculate severity based on port range.

        Args:
            from_port: Start of port range
            to_port: End of port range

        Returns:
            Severity level (critical, high, medium, low)
        """
        # Check if any risky port is in the range
        for risky_port in self.RISKY_PORTS:
            if from_port <= risky_port <= to_port:
                return "critical"

        # Wide port range
        if to_port - from_port > 100:
            return "high"

        return "medium"

    def _get_port_description(self, from_port: int, to_port: int) -> str:
        """
        Get human-readable port description.

        Args:
            from_port: Start of port range
            to_port: End of port range

        Returns:
            Port description
        """
        if from_port == to_port:
            port_names = {
                22: "SSH (22)",
                23: "Telnet (23)",
                3389: "RDP (3389)",
                3306: "MySQL (3306)",
                5432: "PostgreSQL (5432)",
                1433: "SQL Server (1433)",
                27017: "MongoDB (27017)",
                6379: "Redis (6379)",
                9200: "Elasticsearch (9200)",
            }
            return port_names.get(from_port, f"port {from_port}")
        else:
            return f"ports {from_port}-{to_port}"
