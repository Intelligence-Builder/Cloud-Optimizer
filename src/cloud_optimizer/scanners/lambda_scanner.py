"""Lambda Security Scanner.

Issue #133: 9.1.1 Lambda function scanner with rules

Implements comprehensive security scanning for AWS Lambda functions with
configurable rules checking for common misconfigurations and security
vulnerabilities.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from botocore.exceptions import ClientError

from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

logger = logging.getLogger(__name__)

# Patterns that may indicate secrets in environment variables
SECRET_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"access[_-]?key", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
    re.compile(r"auth[_-]?token", re.IGNORECASE),
    re.compile(r"bearer[_-]?token", re.IGNORECASE),
    re.compile(r"jwt[_-]?token", re.IGNORECASE),
    re.compile(r"credentials?", re.IGNORECASE),
    re.compile(r"db[_-]?pass", re.IGNORECASE),
    re.compile(r"database[_-]?password", re.IGNORECASE),
    re.compile(r"connection[_-]?string", re.IGNORECASE),
]


class LambdaScanner(BaseScanner):
    """Scanner for Lambda function security configurations.

    Implements security scanning for AWS Lambda functions with rules checking
    for common misconfigurations and security vulnerabilities including:
    - Deprecated runtime versions
    - Overly permissive IAM roles
    - Secrets exposed in environment variables
    - Missing VPC configuration for private resource access
    - Missing CloudWatch Logs configuration
    - Unused functions (90+ days)
    - Public access via resource policy
    - Default execution role usage
    """

    SERVICE = "Lambda"

    def _register_rules(self) -> None:
        """Register Lambda security rules."""
        # Deprecated runtimes as of 2024-2025
        self.deprecated_runtimes: Set[str] = {
            "nodejs12.x",
            "nodejs10.x",
            "nodejs14.x",
            "nodejs16.x",
            "python2.7",
            "python3.6",
            "python3.7",
            "python3.8",
            "ruby2.5",
            "ruby2.7",
            "dotnetcore2.1",
            "dotnetcore3.1",
            "dotnet6",
            "java8",
            "java8.al2",
            "go1.x",
        }

        self.register_rule(
            ScannerRule(
                rule_id="LAMBDA_001",
                title="Lambda Function Uses Deprecated Runtime",
                description="Lambda function is using a runtime that is deprecated or nearing end of support",
                severity="high",
                service="Lambda",
                resource_type="AWS::Lambda::Function",
                recommendation="Update to a supported runtime version",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Review function code for compatibility with newer runtime",
                    "Update function runtime to latest supported version",
                    "Test function thoroughly after runtime update",
                    "Update deployment pipelines",
                ],
                documentation_url="https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="LAMBDA_002",
                title="Lambda Function Not in VPC",
                description="Lambda function is not configured to run in a VPC",
                severity="medium",
                service="Lambda",
                resource_type="AWS::Lambda::Function",
                recommendation="Configure VPC access if function needs to access VPC resources securely",
                compliance_frameworks=["SOC2"],
                remediation_steps=[
                    "Create VPC configuration with appropriate subnets",
                    "Configure security groups for function",
                    "Ensure NAT Gateway exists for internet access",
                    "Test function connectivity after VPC configuration",
                ],
                documentation_url="https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="LAMBDA_003",
                title="Lambda Execution Role Has Overly Permissive Permissions",
                description="Lambda execution role has wildcard permissions or excessive privileges",
                severity="high",
                service="Lambda",
                resource_type="AWS::Lambda::Function",
                recommendation="Follow principle of least privilege for Lambda execution roles",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Review IAM role permissions",
                    "Remove wildcard actions and resources",
                    "Grant only required permissions",
                    "Use resource-based policies where appropriate",
                ],
                documentation_url="https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="LAMBDA_004",
                title="Lambda Function Missing Dead Letter Queue",
                description="Lambda function does not have a Dead Letter Queue configured",
                severity="low",
                service="Lambda",
                resource_type="AWS::Lambda::Function",
                recommendation="Configure DLQ to capture failed invocations for debugging",
                compliance_frameworks=[],
                remediation_steps=[
                    "Create SNS topic or SQS queue for DLQ",
                    "Configure function DLQ settings",
                    "Set up monitoring and alerts for DLQ messages",
                    "Implement DLQ processing for failed events",
                ],
                documentation_url="https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html#invocation-dlq",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="LAMBDA_005",
                title="Lambda Function Missing Reserved Concurrency",
                description="Lambda function does not have reserved concurrency configured",
                severity="low",
                service="Lambda",
                resource_type="AWS::Lambda::Function",
                recommendation="Configure reserved concurrency to prevent throttling and control costs",
                compliance_frameworks=[],
                remediation_steps=[
                    "Determine appropriate concurrency limit based on load",
                    "Configure reserved concurrency",
                    "Monitor throttling metrics",
                    "Adjust concurrency based on usage patterns",
                ],
                documentation_url="https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="LAMBDA_006",
                title="Lambda Function Exposes Secrets in Environment Variables",
                description="Lambda function has environment variables that appear to contain secrets",
                severity="critical",
                service="Lambda",
                resource_type="AWS::Lambda::Function",
                recommendation="Use AWS Secrets Manager or SSM Parameter Store for sensitive data",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Identify secrets in environment variables",
                    "Create secrets in AWS Secrets Manager or SSM Parameter Store",
                    "Update function code to retrieve secrets at runtime",
                    "Remove secrets from environment variables",
                    "Rotate exposed credentials immediately",
                ],
                documentation_url="https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="LAMBDA_007",
                title="Lambda Function Missing CloudWatch Logs Configuration",
                description="Lambda function's execution role does not allow CloudWatch Logs writes",
                severity="medium",
                service="Lambda",
                resource_type="AWS::Lambda::Function",
                recommendation="Ensure execution role has permissions to write to CloudWatch Logs",
                compliance_frameworks=["SOC2", "HIPAA"],
                remediation_steps=[
                    "Review execution role policies",
                    "Add AWSLambdaBasicExecutionRole or logs:CreateLogGroup permissions",
                    "Verify log group is created and receiving logs",
                    "Configure log retention policy",
                ],
                documentation_url="https://docs.aws.amazon.com/lambda/latest/dg/monitoring-cloudwatchlogs.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="LAMBDA_008",
                title="Lambda Function Unused for 90+ Days",
                description="Lambda function has not been invoked in the last 90 days",
                severity="low",
                service="Lambda",
                resource_type="AWS::Lambda::Function",
                recommendation="Review and consider removing unused Lambda functions",
                compliance_frameworks=[],
                remediation_steps=[
                    "Verify function is no longer needed",
                    "Check for scheduled or event-based triggers",
                    "Archive function code if needed for reference",
                    "Delete unused function to reduce attack surface",
                ],
                documentation_url="https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="LAMBDA_009",
                title="Lambda Function Has Public Access via Resource Policy",
                description="Lambda function resource policy allows public or overly permissive access",
                severity="critical",
                service="Lambda",
                resource_type="AWS::Lambda::Function",
                recommendation="Restrict resource policy to specific principals and accounts",
                compliance_frameworks=["CIS", "PCI-DSS", "SOC2"],
                remediation_steps=[
                    "Review function resource policy",
                    "Remove wildcard principal permissions",
                    "Restrict to specific AWS accounts and principals",
                    "Add conditions for source ARN verification",
                ],
                documentation_url="https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="LAMBDA_010",
                title="Lambda Function Uses Default Execution Role",
                description="Lambda function is using an auto-generated or default execution role",
                severity="medium",
                service="Lambda",
                resource_type="AWS::Lambda::Function",
                recommendation="Create a dedicated IAM role with least privilege permissions",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Review current role permissions",
                    "Create dedicated IAM role for the function",
                    "Apply least privilege principle to permissions",
                    "Update function to use the new role",
                    "Test function after role change",
                ],
                documentation_url="https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html",
            )
        )

    async def scan(self) -> List[ScanResult]:
        """
        Scan Lambda functions for security issues.

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        for region in self.regions:
            try:
                lambda_client = self.get_client("lambda", region=region)
                iam_client = self.get_client("iam")
                cloudwatch_client = self.get_client("cloudwatch", region=region)
                logger.info(f"Scanning Lambda functions in {region}")

                # Get all Lambda functions
                results.extend(
                    await self._check_lambda_functions(
                        lambda_client, iam_client, cloudwatch_client, region
                    )
                )

            except ClientError as e:
                logger.error(f"Error scanning Lambda in {region}: {e}")

        return results

    def _check_secrets_in_env_vars(
        self, env_vars: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """Check environment variables for potential secrets.

        Args:
            env_vars: Dictionary of environment variable names to values

        Returns:
            List of suspicious env var details
        """
        suspicious: List[Dict[str, str]] = []
        for var_name, var_value in env_vars.items():
            for pattern in SECRET_PATTERNS:
                if pattern.search(var_name):
                    # Don't include the actual value for security
                    suspicious.append(
                        {
                            "variable_name": var_name,
                            "pattern_matched": pattern.pattern,
                            "value_length": str(len(var_value)),
                        }
                    )
                    break
        return suspicious

    def _is_default_role(self, role_arn: str) -> bool:
        """Check if role appears to be an auto-generated default role.

        Args:
            role_arn: IAM role ARN

        Returns:
            True if role appears to be a default/auto-generated role
        """
        role_name = role_arn.split("/")[-1]
        default_patterns = [
            "service-role/",
            "-role-",
            "AWSLambdaBasicExecutionRole",
            "lambda_basic_execution",
        ]
        return any(pattern.lower() in role_arn.lower() for pattern in default_patterns)

    async def _check_lambda_functions(
        self,
        lambda_client: Any,
        iam_client: Any,
        cloudwatch_client: Any,
        region: str,
    ) -> List[ScanResult]:
        """Check Lambda functions for security issues.

        Args:
            lambda_client: boto3 Lambda client
            iam_client: boto3 IAM client
            cloudwatch_client: boto3 CloudWatch client
            region: AWS region being scanned

        Returns:
            List of scan results (findings)
        """
        results: List[ScanResult] = []
        now = datetime.now(timezone.utc)

        try:
            paginator = lambda_client.get_paginator("list_functions")
            for page in paginator.paginate():
                functions = page.get("Functions", [])

                for function in functions:
                    function_name = function["FunctionName"]
                    function_arn = function["FunctionArn"]
                    runtime = function.get("Runtime", "")

                    # Check deprecated runtime (LAMBDA_001)
                    if runtime in self.deprecated_runtimes:
                        results.append(
                            self.create_result(
                                rule_id="LAMBDA_001",
                                resource_id=function_arn,
                                resource_name=function_name,
                                region=region,
                                metadata={
                                    "runtime": runtime,
                                    "handler": function.get("Handler"),
                                },
                            )
                        )

                    # Check VPC configuration (LAMBDA_002)
                    vpc_config = function.get("VpcConfig", {})
                    if not vpc_config.get("VpcId"):
                        # Note: Not all functions need VPC access
                        # This is a warning for functions that might benefit from it
                        results.append(
                            self.create_result(
                                rule_id="LAMBDA_002",
                                resource_id=function_arn,
                                resource_name=function_name,
                                region=region,
                                metadata={
                                    "runtime": runtime,
                                },
                            )
                        )

                    # Check execution role permissions (LAMBDA_003)
                    role_arn = function.get("Role")
                    if role_arn:
                        try:
                            # Extract role name from ARN
                            role_name = role_arn.split("/")[-1]

                            # Get attached policies
                            attached_policies = iam_client.list_attached_role_policies(
                                RoleName=role_name
                            )

                            for policy in attached_policies.get("AttachedPolicies", []):
                                policy_arn = policy["PolicyArn"]

                                # Check for AWS managed policies with broad permissions
                                if (
                                    "AdministratorAccess" in policy_arn
                                    or "PowerUserAccess" in policy_arn
                                ):
                                    results.append(
                                        self.create_result(
                                            rule_id="LAMBDA_003",
                                            resource_id=function_arn,
                                            resource_name=function_name,
                                            region=region,
                                            metadata={
                                                "role_arn": role_arn,
                                                "policy_arn": policy_arn,
                                                "issue": "overly_permissive_managed_policy",
                                            },
                                        )
                                    )

                            # Check inline policies
                            inline_policies = iam_client.list_role_policies(
                                RoleName=role_name
                            )

                            for policy_name in inline_policies.get("PolicyNames", []):
                                policy_doc = iam_client.get_role_policy(
                                    RoleName=role_name, PolicyName=policy_name
                                )

                                document = policy_doc.get("PolicyDocument", {})
                                if "Statement" in document:
                                    for statement in document["Statement"]:
                                        if statement.get("Effect") == "Allow":
                                            actions = statement.get("Action", [])
                                            if not isinstance(actions, list):
                                                actions = [actions]

                                            resources = statement.get("Resource", [])
                                            if not isinstance(resources, list):
                                                resources = [resources]

                                            # Check for wildcard permissions
                                            if "*" in actions and "*" in resources:
                                                results.append(
                                                    self.create_result(
                                                        rule_id="LAMBDA_003",
                                                        resource_id=function_arn,
                                                        resource_name=function_name,
                                                        region=region,
                                                        metadata={
                                                            "role_arn": role_arn,
                                                            "policy_name": policy_name,
                                                            "issue": "wildcard_permissions",
                                                        },
                                                    )
                                                )

                        except ClientError as e:
                            error_code = e.response.get("Error", {}).get("Code", "")
                            if error_code != "NoSuchEntity":
                                logger.error(f"Error checking role {role_name}: {e}")

                    # Check Dead Letter Queue (LAMBDA_004)
                    dead_letter_config = function.get("DeadLetterConfig", {})
                    if not dead_letter_config.get("TargetArn"):
                        results.append(
                            self.create_result(
                                rule_id="LAMBDA_004",
                                resource_id=function_arn,
                                resource_name=function_name,
                                region=region,
                            )
                        )

                    # Check Reserved Concurrency (LAMBDA_005)
                    # Need to get function concurrency separately
                    try:
                        concurrency = lambda_client.get_function_concurrency(
                            FunctionName=function_name
                        )
                        reserved_concurrency = concurrency.get(
                            "ReservedConcurrentExecutions"
                        )

                        if reserved_concurrency is None:
                            results.append(
                                self.create_result(
                                    rule_id="LAMBDA_005",
                                    resource_id=function_arn,
                                    resource_name=function_name,
                                    region=region,
                                )
                            )

                    except ClientError as e:
                        # Function may not have concurrency configured
                        error_code = e.response.get("Error", {}).get("Code", "")
                        if error_code == "ResourceNotFoundException":
                            results.append(
                                self.create_result(
                                    rule_id="LAMBDA_005",
                                    resource_id=function_arn,
                                    resource_name=function_name,
                                    region=region,
                                )
                            )

                    # Check for secrets in environment variables (LAMBDA_006)
                    env_vars = function.get("Environment", {}).get("Variables", {})
                    if env_vars:
                        suspicious_vars = self._check_secrets_in_env_vars(env_vars)
                        if suspicious_vars:
                            results.append(
                                self.create_result(
                                    rule_id="LAMBDA_006",
                                    resource_id=function_arn,
                                    resource_name=function_name,
                                    region=region,
                                    metadata={
                                        "suspicious_variables": suspicious_vars,
                                        "total_env_vars": len(env_vars),
                                    },
                                )
                            )

                    # Check for CloudWatch Logs permissions (LAMBDA_007)
                    role_arn = function.get("Role", "")
                    if role_arn:
                        has_logs_permission = False
                        try:
                            role_name = role_arn.split("/")[-1]
                            # Check attached policies for logs permissions
                            attached = iam_client.list_attached_role_policies(
                                RoleName=role_name
                            )
                            for policy in attached.get("AttachedPolicies", []):
                                policy_arn = policy["PolicyArn"]
                                if (
                                    "AWSLambdaBasicExecutionRole" in policy_arn
                                    or "CloudWatchLogsFullAccess" in policy_arn
                                    or "CloudWatchFullAccess" in policy_arn
                                ):
                                    has_logs_permission = True
                                    break

                            # Check inline policies if no managed policy found
                            if not has_logs_permission:
                                inline_policies = iam_client.list_role_policies(
                                    RoleName=role_name
                                )
                                for policy_name in inline_policies.get(
                                    "PolicyNames", []
                                ):
                                    policy_doc = iam_client.get_role_policy(
                                        RoleName=role_name, PolicyName=policy_name
                                    )
                                    doc = policy_doc.get("PolicyDocument", {})
                                    for stmt in doc.get("Statement", []):
                                        if stmt.get("Effect") == "Allow":
                                            actions = stmt.get("Action", [])
                                            if not isinstance(actions, list):
                                                actions = [actions]
                                            for action in actions:
                                                if (
                                                    action.startswith("logs:")
                                                    or action == "*"
                                                ):
                                                    has_logs_permission = True
                                                    break
                                        if has_logs_permission:
                                            break

                            if not has_logs_permission:
                                results.append(
                                    self.create_result(
                                        rule_id="LAMBDA_007",
                                        resource_id=function_arn,
                                        resource_name=function_name,
                                        region=region,
                                        metadata={"role_arn": role_arn},
                                    )
                                )

                        except ClientError as e:
                            logger.debug(f"Error checking logs permission: {e}")

                    # Check for unused functions (LAMBDA_008)
                    # Get function invocation metrics
                    try:
                        metrics_response = cloudwatch_client.get_metric_statistics(
                            Namespace="AWS/Lambda",
                            MetricName="Invocations",
                            Dimensions=[
                                {"Name": "FunctionName", "Value": function_name}
                            ],
                            StartTime=now.replace(
                                day=now.day if now.day <= 28 else 28
                            ).replace(month=now.month - 3 if now.month > 3 else 12),
                            EndTime=now,
                            Period=86400 * 90,  # 90 days
                            Statistics=["Sum"],
                        )
                        datapoints = metrics_response.get("Datapoints", [])
                        total_invocations = sum(dp.get("Sum", 0) for dp in datapoints)

                        if total_invocations == 0:
                            results.append(
                                self.create_result(
                                    rule_id="LAMBDA_008",
                                    resource_id=function_arn,
                                    resource_name=function_name,
                                    region=region,
                                    metadata={
                                        "last_modified": function.get(
                                            "LastModified", "unknown"
                                        ),
                                        "invocations_90_days": 0,
                                    },
                                )
                            )
                    except ClientError as e:
                        logger.debug(f"Error checking invocation metrics: {e}")

                    # Check for public access via resource policy (LAMBDA_009)
                    try:
                        policy_response = lambda_client.get_policy(
                            FunctionName=function_name
                        )
                        policy_str = policy_response.get("Policy", "{}")
                        policy = json.loads(policy_str)

                        for statement in policy.get("Statement", []):
                            principal = statement.get("Principal", {})
                            if isinstance(principal, str) and principal == "*":
                                # Public access
                                condition = statement.get("Condition", {})
                                if not condition:
                                    # No condition means truly public
                                    results.append(
                                        self.create_result(
                                            rule_id="LAMBDA_009",
                                            resource_id=function_arn,
                                            resource_name=function_name,
                                            region=region,
                                            metadata={
                                                "statement_sid": statement.get(
                                                    "Sid", "unknown"
                                                ),
                                                "principal": "*",
                                                "has_conditions": False,
                                            },
                                        )
                                    )
                            elif isinstance(principal, dict):
                                for key, value in principal.items():
                                    if value == "*":
                                        results.append(
                                            self.create_result(
                                                rule_id="LAMBDA_009",
                                                resource_id=function_arn,
                                                resource_name=function_name,
                                                region=region,
                                                metadata={
                                                    "statement_sid": statement.get(
                                                        "Sid", "unknown"
                                                    ),
                                                    "principal_type": key,
                                                    "principal_value": "*",
                                                },
                                            )
                                        )

                    except ClientError as e:
                        # No resource policy is fine
                        error_code = e.response.get("Error", {}).get("Code", "")
                        if error_code != "ResourceNotFoundException":
                            logger.debug(f"Error checking resource policy: {e}")

                    # Check for default execution role (LAMBDA_010)
                    if role_arn and self._is_default_role(role_arn):
                        results.append(
                            self.create_result(
                                rule_id="LAMBDA_010",
                                resource_id=function_arn,
                                resource_name=function_name,
                                region=region,
                                metadata={
                                    "role_arn": role_arn,
                                    "role_name": role_arn.split("/")[-1],
                                },
                            )
                        )

        except ClientError as e:
            logger.error(f"Error checking Lambda functions in {region}: {e}")

        return results
