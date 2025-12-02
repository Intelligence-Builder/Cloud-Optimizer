"""Lambda Security Scanner."""

import logging
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

logger = logging.getLogger(__name__)


class LambdaScanner(BaseScanner):
    """Scanner for Lambda function security configurations."""

    SERVICE = "Lambda"

    def _register_rules(self) -> None:
        """Register Lambda security rules."""
        # Deprecated runtimes as of 2024
        self.deprecated_runtimes = {
            "nodejs12.x",
            "nodejs10.x",
            "python2.7",
            "python3.6",
            "python3.7",
            "ruby2.5",
            "ruby2.7",
            "dotnetcore2.1",
            "dotnetcore3.1",
            "java8",
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
                logger.info(f"Scanning Lambda functions in {region}")

                # Get all Lambda functions
                results.extend(await self._check_lambda_functions(lambda_client, iam_client, region))

            except ClientError as e:
                logger.error(f"Error scanning Lambda in {region}: {e}")

        return results

    async def _check_lambda_functions(
        self, lambda_client: Any, iam_client: Any, region: str
    ) -> List[ScanResult]:
        """Check Lambda functions."""
        results: List[ScanResult] = []

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
                                if "AdministratorAccess" in policy_arn or "PowerUserAccess" in policy_arn:
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
                            inline_policies = iam_client.list_role_policies(RoleName=role_name)

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
                        reserved_concurrency = concurrency.get("ReservedConcurrentExecutions")

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

        except ClientError as e:
            logger.error(f"Error checking Lambda functions in {region}: {e}")

        return results
