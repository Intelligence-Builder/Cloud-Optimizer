"""CloudWatch performance scanner for AWS performance optimization.

Scans AWS CloudWatch metrics for performance bottlenecks, scaling
recommendations, and latency issues.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from cloud_optimizer.integrations.aws.base import BaseAWSScanner

logger = logging.getLogger(__name__)


class CloudWatchScanner(BaseAWSScanner):
    """Scanner for AWS CloudWatch performance metrics.

    Detects:
    - CPU bottlenecks (>80% utilization)
    - Memory issues (>85% utilization)
    - Disk queue issues (high queue depth)
    - Network bottlenecks
    - Lambda throttling and errors
    - RDS performance issues

    Example:
        scanner = CloudWatchScanner()
        findings = await scanner.scan("123456789012")
    """

    # Performance thresholds
    CPU_HIGH_THRESHOLD = 80.0  # CPU utilization above 80%
    CPU_CRITICAL_THRESHOLD = 95.0  # CPU utilization above 95%
    MEMORY_HIGH_THRESHOLD = 85.0  # Memory utilization above 85%
    MEMORY_CRITICAL_THRESHOLD = 95.0  # Memory utilization above 95%
    DISK_QUEUE_THRESHOLD = 10.0  # Disk queue depth above 10
    NETWORK_ERROR_THRESHOLD = 100  # Network errors above 100/period
    LAMBDA_ERROR_RATE_THRESHOLD = 5.0  # Lambda error rate above 5%
    LAMBDA_THROTTLE_THRESHOLD = 1  # Any throttling is concerning
    RDS_CPU_THRESHOLD = 80.0  # RDS CPU above 80%
    RDS_CONNECTIONS_THRESHOLD = 0.9  # Using >90% of max connections

    def get_scanner_name(self) -> str:
        """Return scanner name for logging."""
        return "CloudWatchScanner"

    async def scan(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Scan AWS CloudWatch metrics for performance issues.

        Args:
            account_id: AWS account ID to scan

        Returns:
            List of performance optimization findings
        """
        logger.info(f"Starting performance scan for account {account_id}")
        findings: List[Dict[str, Any]] = []

        try:
            # Get clients
            ec2_client = self.get_client("ec2")
            cloudwatch_client = self.get_client("cloudwatch")
            lambda_client = self.get_client("lambda")
            rds_client = self.get_client("rds")

            # 1. Check EC2 instance performance
            findings.extend(
                self._check_ec2_performance(ec2_client, cloudwatch_client, account_id)
            )

            # 2. Check Lambda function performance
            findings.extend(
                self._check_lambda_performance(
                    lambda_client, cloudwatch_client, account_id
                )
            )

            # 3. Check RDS database performance
            findings.extend(
                self._check_rds_performance(rds_client, cloudwatch_client, account_id)
            )

            logger.info(
                f"Performance scan complete: {len(findings)} findings",
                extra={"account_id": account_id, "findings_count": len(findings)},
            )

        except ClientError as e:
            logger.error(f"Performance scan failed: {e}")
            raise

        return findings

    def _check_ec2_performance(
        self, ec2_client: Any, cloudwatch_client: Any, account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Check EC2 instance performance metrics.

        Args:
            ec2_client: Boto3 EC2 client
            cloudwatch_client: Boto3 CloudWatch client
            account_id: AWS account ID

        Returns:
            List of EC2 performance findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            # Get running instances
            response = ec2_client.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            )

            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    instance_type = instance.get("InstanceType", "unknown")

                    # Get instance name from tags
                    instance_name = instance_id
                    for tag in instance.get("Tags", []):
                        if tag["Key"] == "Name":
                            instance_name = tag["Value"]
                            break

                    # Check CPU utilization
                    cpu_metrics = self._get_metric_statistics(
                        cloudwatch_client,
                        namespace="AWS/EC2",
                        metric_name="CPUUtilization",
                        dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                        statistic="Average",
                        period=3600,  # 1 hour
                        duration_hours=24,  # Last 24 hours
                    )

                    if cpu_metrics:
                        avg_cpu = sum(cpu_metrics) / len(cpu_metrics)
                        max_cpu = max(cpu_metrics)

                        if max_cpu >= self.CPU_CRITICAL_THRESHOLD:
                            findings.append(
                                self._create_cpu_bottleneck_finding(
                                    resource_id=instance_id,
                                    resource_name=instance_name,
                                    instance_type=instance_type,
                                    avg_cpu=avg_cpu,
                                    max_cpu=max_cpu,
                                    severity="critical",
                                    account_id=account_id,
                                )
                            )
                        elif avg_cpu >= self.CPU_HIGH_THRESHOLD:
                            findings.append(
                                self._create_cpu_bottleneck_finding(
                                    resource_id=instance_id,
                                    resource_name=instance_name,
                                    instance_type=instance_type,
                                    avg_cpu=avg_cpu,
                                    max_cpu=max_cpu,
                                    severity="high",
                                    account_id=account_id,
                                )
                            )

                    # Check disk queue depth
                    disk_queue_metrics = self._get_metric_statistics(
                        cloudwatch_client,
                        namespace="AWS/EC2",
                        metric_name="DiskQueueDepth",
                        dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                        statistic="Average",
                        period=3600,
                        duration_hours=24,
                    )

                    if disk_queue_metrics:
                        avg_queue = sum(disk_queue_metrics) / len(disk_queue_metrics)
                        max_queue = max(disk_queue_metrics)

                        if avg_queue >= self.DISK_QUEUE_THRESHOLD:
                            findings.append(
                                self._create_disk_queue_finding(
                                    resource_id=instance_id,
                                    resource_name=instance_name,
                                    instance_type=instance_type,
                                    avg_queue=avg_queue,
                                    max_queue=max_queue,
                                    account_id=account_id,
                                )
                            )

                    # Check network errors
                    network_error_metrics = self._get_metric_statistics(
                        cloudwatch_client,
                        namespace="AWS/EC2",
                        metric_name="NetworkPacketsDropped",
                        dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                        statistic="Sum",
                        period=3600,
                        duration_hours=24,
                    )

                    if network_error_metrics:
                        total_errors = sum(network_error_metrics)
                        if total_errors >= self.NETWORK_ERROR_THRESHOLD:
                            findings.append(
                                self._create_network_issue_finding(
                                    resource_id=instance_id,
                                    resource_name=instance_name,
                                    instance_type=instance_type,
                                    total_errors=total_errors,
                                    account_id=account_id,
                                )
                            )

        except ClientError as e:
            logger.warning(f"Failed to check EC2 performance: {e}")

        return findings

    def _check_lambda_performance(
        self, lambda_client: Any, cloudwatch_client: Any, account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Check Lambda function performance metrics.

        Args:
            lambda_client: Boto3 Lambda client
            cloudwatch_client: Boto3 CloudWatch client
            account_id: AWS account ID

        Returns:
            List of Lambda performance findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            # List all Lambda functions
            paginator = lambda_client.get_paginator("list_functions")
            for page in paginator.paginate():
                for function in page.get("Functions", []):
                    function_name = function["FunctionName"]
                    memory_size = function.get("MemorySize", 128)
                    timeout = function.get("Timeout", 3)

                    # Check error rate
                    error_metrics = self._get_metric_statistics(
                        cloudwatch_client,
                        namespace="AWS/Lambda",
                        metric_name="Errors",
                        dimensions=[{"Name": "FunctionName", "Value": function_name}],
                        statistic="Sum",
                        period=3600,
                        duration_hours=24,
                    )

                    invocation_metrics = self._get_metric_statistics(
                        cloudwatch_client,
                        namespace="AWS/Lambda",
                        metric_name="Invocations",
                        dimensions=[{"Name": "FunctionName", "Value": function_name}],
                        statistic="Sum",
                        period=3600,
                        duration_hours=24,
                    )

                    if error_metrics and invocation_metrics:
                        total_errors = sum(error_metrics)
                        total_invocations = sum(invocation_metrics)

                        if total_invocations > 0:
                            error_rate = (total_errors / total_invocations) * 100

                            if error_rate >= self.LAMBDA_ERROR_RATE_THRESHOLD:
                                findings.append(
                                    self._create_lambda_error_finding(
                                        function_name=function_name,
                                        error_rate=error_rate,
                                        total_errors=total_errors,
                                        total_invocations=total_invocations,
                                        memory_size=memory_size,
                                        timeout=timeout,
                                        account_id=account_id,
                                    )
                                )

                    # Check throttling
                    throttle_metrics = self._get_metric_statistics(
                        cloudwatch_client,
                        namespace="AWS/Lambda",
                        metric_name="Throttles",
                        dimensions=[{"Name": "FunctionName", "Value": function_name}],
                        statistic="Sum",
                        period=3600,
                        duration_hours=24,
                    )

                    if throttle_metrics:
                        total_throttles = sum(throttle_metrics)
                        if total_throttles >= self.LAMBDA_THROTTLE_THRESHOLD:
                            findings.append(
                                self._create_lambda_throttle_finding(
                                    function_name=function_name,
                                    total_throttles=total_throttles,
                                    memory_size=memory_size,
                                    timeout=timeout,
                                    account_id=account_id,
                                )
                            )

        except ClientError as e:
            logger.warning(f"Failed to check Lambda performance: {e}")

        return findings

    def _check_rds_performance(
        self, rds_client: Any, cloudwatch_client: Any, account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Check RDS database performance metrics.

        Args:
            rds_client: Boto3 RDS client
            cloudwatch_client: Boto3 CloudWatch client
            account_id: AWS account ID

        Returns:
            List of RDS performance findings
        """
        findings: List[Dict[str, Any]] = []

        try:
            # Get all RDS instances
            response = rds_client.describe_db_instances()

            for db_instance in response.get("DBInstances", []):
                db_identifier = db_instance["DBInstanceIdentifier"]
                db_class = db_instance.get("DBInstanceClass", "unknown")
                engine = db_instance.get("Engine", "unknown")

                # Check CPU utilization
                cpu_metrics = self._get_metric_statistics(
                    cloudwatch_client,
                    namespace="AWS/RDS",
                    metric_name="CPUUtilization",
                    dimensions=[
                        {"Name": "DBInstanceIdentifier", "Value": db_identifier}
                    ],
                    statistic="Average",
                    period=3600,
                    duration_hours=24,
                )

                if cpu_metrics:
                    avg_cpu = sum(cpu_metrics) / len(cpu_metrics)
                    max_cpu = max(cpu_metrics)

                    if avg_cpu >= self.RDS_CPU_THRESHOLD:
                        findings.append(
                            self._create_rds_cpu_finding(
                                db_identifier=db_identifier,
                                db_class=db_class,
                                engine=engine,
                                avg_cpu=avg_cpu,
                                max_cpu=max_cpu,
                                account_id=account_id,
                            )
                        )

                # Check database connections
                connection_metrics = self._get_metric_statistics(
                    cloudwatch_client,
                    namespace="AWS/RDS",
                    metric_name="DatabaseConnections",
                    dimensions=[
                        {"Name": "DBInstanceIdentifier", "Value": db_identifier}
                    ],
                    statistic="Average",
                    period=3600,
                    duration_hours=24,
                )

                if connection_metrics:
                    # Estimate max connections based on instance class
                    # This is a rough estimate; actual max depends on configuration
                    max_connections = self._estimate_rds_max_connections(db_class)
                    avg_connections = sum(connection_metrics) / len(connection_metrics)
                    connection_usage = avg_connections / max_connections

                    if connection_usage >= self.RDS_CONNECTIONS_THRESHOLD:
                        findings.append(
                            self._create_rds_connections_finding(
                                db_identifier=db_identifier,
                                db_class=db_class,
                                engine=engine,
                                avg_connections=avg_connections,
                                max_connections=max_connections,
                                connection_usage=connection_usage,
                                account_id=account_id,
                            )
                        )

        except ClientError as e:
            logger.warning(f"Failed to check RDS performance: {e}")

        return findings

    def _get_metric_statistics(
        self,
        cloudwatch_client: Any,
        namespace: str,
        metric_name: str,
        dimensions: List[Dict[str, str]],
        statistic: str,
        period: int,
        duration_hours: int,
    ) -> List[float]:
        """
        Get CloudWatch metric statistics.

        Args:
            cloudwatch_client: Boto3 CloudWatch client
            namespace: CloudWatch namespace
            metric_name: Metric name
            dimensions: Metric dimensions
            statistic: Statistic type (Average, Sum, Maximum, etc.)
            period: Period in seconds
            duration_hours: Duration to look back in hours

        Returns:
            List of metric values
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=duration_hours)

            response = cloudwatch_client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[statistic],
            )

            datapoints = response.get("Datapoints", [])
            return [dp[statistic] for dp in datapoints if statistic in dp]

        except ClientError as e:
            logger.debug(f"Failed to get metric {metric_name}: {e}")
            return []

    def _estimate_rds_max_connections(self, db_class: str) -> int:
        """
        Estimate maximum RDS connections based on instance class.

        Args:
            db_class: RDS instance class (e.g., db.t3.micro)

        Returns:
            Estimated maximum connections
        """
        # Rough estimates based on instance size
        # Actual limits depend on DB engine and configuration
        # Check larger sizes first to avoid substring matches (e.g., "large" matching "xlarge")
        size_estimates = [
            ("4xlarge", 5000),
            ("2xlarge", 3000),
            ("xlarge", 2000),
            ("large", 1000),
            ("medium", 500),
            ("small", 200),
            ("micro", 100),
        ]

        db_class_lower = db_class.lower()
        for size, connections in size_estimates:
            if size in db_class_lower:
                return connections

        # Default fallback
        return 500

    def _create_cpu_bottleneck_finding(
        self,
        resource_id: str,
        resource_name: str,
        instance_type: str,
        avg_cpu: float,
        max_cpu: float,
        severity: str,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for CPU bottleneck."""
        return {
            "finding_type": "performance_bottleneck",
            "severity": severity,
            "title": f"High CPU utilization on {resource_name} ({avg_cpu:.1f}% avg)",
            "description": (
                f"EC2 instance {resource_name} ({instance_type}) is experiencing high "
                f"CPU utilization. Average: {avg_cpu:.1f}%, Peak: {max_cpu:.1f}%. "
                f"This may indicate the instance is undersized for its workload."
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:instance/{resource_id}",
            "resource_id": resource_id,
            "resource_name": resource_name,
            "resource_type": "ec2_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Consider upgrading instance {resource_name} to a larger instance type, "
                "implementing auto-scaling, or optimizing application code to reduce CPU usage. "
                "Review CloudWatch metrics to identify peak usage patterns."
            ),
            "metadata": {
                "resource_id": resource_id,
                "instance_type": instance_type,
                "avg_cpu": avg_cpu,
                "max_cpu": max_cpu,
                "metric_type": "cpu_utilization",
            },
        }

    def _create_disk_queue_finding(
        self,
        resource_id: str,
        resource_name: str,
        instance_type: str,
        avg_queue: float,
        max_queue: float,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for disk queue issues."""
        severity = "critical" if avg_queue >= 20 else "high"

        return {
            "finding_type": "performance_bottleneck",
            "severity": severity,
            "title": f"High disk queue depth on {resource_name} ({avg_queue:.1f} avg)",
            "description": (
                f"EC2 instance {resource_name} ({instance_type}) has high disk queue depth. "
                f"Average: {avg_queue:.1f}, Peak: {max_queue:.1f}. This indicates I/O bottleneck."
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:instance/{resource_id}",
            "resource_id": resource_id,
            "resource_name": resource_name,
            "resource_type": "ec2_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                "Upgrade EBS volume type to higher IOPS (gp3 or io2), increase provisioned IOPS, "
                "or optimize application I/O patterns. Consider using instance store volumes "
                "for temporary data if available."
            ),
            "metadata": {
                "resource_id": resource_id,
                "instance_type": instance_type,
                "avg_queue": avg_queue,
                "max_queue": max_queue,
                "metric_type": "disk_queue_depth",
            },
        }

    def _create_network_issue_finding(
        self,
        resource_id: str,
        resource_name: str,
        instance_type: str,
        total_errors: float,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for network issues."""
        severity = "high" if total_errors >= 1000 else "medium"

        return {
            "finding_type": "latency_issue",
            "severity": severity,
            "title": f"Network packet drops on {resource_name} ({total_errors:.0f} total)",
            "description": (
                f"EC2 instance {resource_name} ({instance_type}) is dropping network packets. "
                f"Total dropped: {total_errors:.0f} packets in the last 24 hours. "
                "This may indicate network congestion or misconfiguration."
            ),
            "resource_arn": f"arn:aws:ec2:{self.region}:{account_id}:instance/{resource_id}",
            "resource_id": resource_id,
            "resource_name": resource_name,
            "resource_type": "ec2_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                "Investigate network configuration, check security group rules, "
                "verify VPC routing, and consider upgrading to instance type with "
                "enhanced networking support."
            ),
            "metadata": {
                "resource_id": resource_id,
                "instance_type": instance_type,
                "total_errors": total_errors,
                "metric_type": "network_packets_dropped",
            },
        }

    def _create_lambda_error_finding(
        self,
        function_name: str,
        error_rate: float,
        total_errors: float,
        total_invocations: float,
        memory_size: int,
        timeout: int,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for Lambda errors."""
        severity = "critical" if error_rate >= 10 else "high"

        return {
            "finding_type": "performance_bottleneck",
            "severity": severity,
            "title": f"High error rate in Lambda function {function_name} ({error_rate:.1f}%)",
            "description": (
                f"Lambda function {function_name} has high error rate: {error_rate:.1f}% "
                f"({total_errors:.0f} errors out of {total_invocations:.0f} invocations). "
                f"Memory: {memory_size}MB, Timeout: {timeout}s."
            ),
            "resource_arn": f"arn:aws:lambda:{self.region}:{account_id}:function:{function_name}",
            "resource_id": function_name,
            "resource_name": function_name,
            "resource_type": "lambda_function",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Review CloudWatch Logs for function {function_name} to identify error causes. "
                "Consider increasing memory allocation, timeout value, or fixing application bugs. "
                "Implement proper error handling and retry logic."
            ),
            "metadata": {
                "function_name": function_name,
                "error_rate": error_rate,
                "total_errors": total_errors,
                "total_invocations": total_invocations,
                "memory_size": memory_size,
                "timeout": timeout,
                "metric_type": "lambda_errors",
            },
        }

    def _create_lambda_throttle_finding(
        self,
        function_name: str,
        total_throttles: float,
        memory_size: int,
        timeout: int,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for Lambda throttling."""
        severity = "critical" if total_throttles >= 100 else "high"

        return {
            "finding_type": "scaling_recommendation",
            "severity": severity,
            "title": f"Lambda function {function_name} is being throttled ({total_throttles:.0f} times)",
            "description": (
                f"Lambda function {function_name} was throttled {total_throttles:.0f} times "
                f"in the last 24 hours due to concurrency limits. Memory: {memory_size}MB, "
                f"Timeout: {timeout}s."
            ),
            "resource_arn": f"arn:aws:lambda:{self.region}:{account_id}:function:{function_name}",
            "resource_id": function_name,
            "resource_name": function_name,
            "resource_type": "lambda_function",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                f"Request increased concurrency limit for function {function_name}, "
                "implement reserved concurrency for critical functions, or use SQS "
                "to queue requests and process them at a controlled rate."
            ),
            "metadata": {
                "function_name": function_name,
                "total_throttles": total_throttles,
                "memory_size": memory_size,
                "timeout": timeout,
                "metric_type": "lambda_throttles",
            },
        }

    def _create_rds_cpu_finding(
        self,
        db_identifier: str,
        db_class: str,
        engine: str,
        avg_cpu: float,
        max_cpu: float,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for RDS CPU issues."""
        severity = "critical" if avg_cpu >= 90 else "high"

        return {
            "finding_type": "performance_bottleneck",
            "severity": severity,
            "title": f"High CPU on RDS instance {db_identifier} ({avg_cpu:.1f}% avg)",
            "description": (
                f"RDS instance {db_identifier} ({db_class}, {engine}) has high CPU utilization. "
                f"Average: {avg_cpu:.1f}%, Peak: {max_cpu:.1f}%. This may impact database performance."
            ),
            "resource_arn": f"arn:aws:rds:{self.region}:{account_id}:db:{db_identifier}",
            "resource_id": db_identifier,
            "resource_name": db_identifier,
            "resource_type": "rds_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                "Optimize database queries, add indexes, upgrade to larger instance class, "
                "or implement read replicas to distribute load. Review Performance Insights "
                "for query optimization opportunities."
            ),
            "metadata": {
                "db_identifier": db_identifier,
                "db_class": db_class,
                "engine": engine,
                "avg_cpu": avg_cpu,
                "max_cpu": max_cpu,
                "metric_type": "rds_cpu_utilization",
            },
        }

    def _create_rds_connections_finding(
        self,
        db_identifier: str,
        db_class: str,
        engine: str,
        avg_connections: float,
        max_connections: int,
        connection_usage: float,
        account_id: str,
    ) -> Dict[str, Any]:
        """Create finding for RDS connection issues."""
        severity = "critical" if connection_usage >= 0.95 else "high"

        return {
            "finding_type": "scaling_recommendation",
            "severity": severity,
            "title": f"High connection usage on RDS instance {db_identifier} ({connection_usage*100:.0f}%)",
            "description": (
                f"RDS instance {db_identifier} ({db_class}, {engine}) is using "
                f"{connection_usage*100:.0f}% of maximum connections. "
                f"Average connections: {avg_connections:.0f}/{max_connections}."
            ),
            "resource_arn": f"arn:aws:rds:{self.region}:{account_id}:db:{db_identifier}",
            "resource_id": db_identifier,
            "resource_name": db_identifier,
            "resource_type": "rds_instance",
            "aws_account_id": account_id,
            "region": self.region,
            "remediation": (
                "Implement connection pooling in application, increase max_connections "
                "parameter (may require instance upgrade), or investigate connection leaks. "
                "Consider using RDS Proxy to manage connections efficiently."
            ),
            "metadata": {
                "db_identifier": db_identifier,
                "db_class": db_class,
                "engine": engine,
                "avg_connections": avg_connections,
                "max_connections": max_connections,
                "connection_usage": connection_usage,
                "metric_type": "rds_connections",
            },
        }
