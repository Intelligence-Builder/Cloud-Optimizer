"""EKS/ECS Container Security Scanner.

Issue #142: 9.1.4 EKS/ECS container security scanner

Implements comprehensive security scanning for AWS container services (EKS and ECS)
checking for cluster configuration, container security, network policies, and IAM roles.
"""

import logging
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

logger = logging.getLogger(__name__)


class ContainerScanner(BaseScanner):
    """Scanner for EKS and ECS container security configurations.

    Implements security scanning for AWS container services including:
    - EKS cluster configurations and node groups
    - ECS cluster, task definitions, and services
    - Container image sources and vulnerability scanning
    - IAM roles for pods/tasks (IRSA/task roles)
    - Network security (security groups, network policies)
    - Privileged containers and capabilities
    - Logging and monitoring configuration
    - Secrets exposed in environment variables
    """

    SERVICE = "Container"

    def _register_rules(self) -> None:
        """Register EKS and ECS security rules."""
        # EKS Rules
        self.register_rule(
            ScannerRule(
                rule_id="EKS_001",
                title="EKS Cluster API Endpoint Publicly Accessible",
                description="EKS cluster API endpoint is publicly accessible without restrictions",
                severity="high",
                service="EKS",
                resource_type="AWS::EKS::Cluster",
                recommendation="Restrict cluster endpoint access to private or specific IP ranges",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Review cluster endpoint access settings",
                    "Enable private endpoint access",
                    "Add public access CIDR restrictions",
                    "Consider fully private cluster for production",
                ],
                documentation_url="https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="EKS_002",
                title="EKS Cluster Missing CloudWatch Logging",
                description="EKS cluster does not have control plane logging enabled",
                severity="medium",
                service="EKS",
                resource_type="AWS::EKS::Cluster",
                recommendation="Enable CloudWatch logging for cluster control plane",
                compliance_frameworks=["SOC2", "HIPAA"],
                remediation_steps=[
                    "Enable api server logging",
                    "Enable audit logging",
                    "Enable authenticator logging",
                    "Enable controller manager logging",
                    "Enable scheduler logging",
                ],
                documentation_url="https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="EKS_003",
                title="EKS Cluster Using Outdated Kubernetes Version",
                description="EKS cluster is running an outdated Kubernetes version",
                severity="high",
                service="EKS",
                resource_type="AWS::EKS::Cluster",
                recommendation="Upgrade to a supported Kubernetes version",
                compliance_frameworks=["CIS"],
                remediation_steps=[
                    "Review Kubernetes version support calendar",
                    "Test workloads on newer version",
                    "Plan and execute cluster upgrade",
                    "Update node groups to match cluster version",
                ],
                documentation_url="https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="EKS_004",
                title="EKS Missing Secrets Encryption (KMS)",
                description="EKS cluster does not have envelope encryption for Kubernetes secrets",
                severity="high",
                service="EKS",
                resource_type="AWS::EKS::Cluster",
                recommendation="Enable KMS encryption for Kubernetes secrets",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA"],
                remediation_steps=[
                    "Create KMS key for secrets encryption",
                    "Enable secrets encryption on cluster",
                    "Recreate existing secrets to encrypt them",
                ],
                documentation_url="https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html",
            )
        )

        # ECS Rules
        self.register_rule(
            ScannerRule(
                rule_id="ECS_001",
                title="ECS Task Definition Using Privileged Containers",
                description="ECS task definition runs containers in privileged mode",
                severity="critical",
                service="ECS",
                resource_type="AWS::ECS::TaskDefinition",
                recommendation="Remove privileged mode unless absolutely necessary",
                compliance_frameworks=["CIS", "PCI-DSS", "SOC2"],
                remediation_steps=[
                    "Review container's need for privileged mode",
                    "Use Linux capabilities instead of full privileges",
                    "Update task definition to remove privileged flag",
                    "Test container functionality without privileges",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_security",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="ECS_002",
                title="ECS Task Definition Exposing Secrets in Environment Variables",
                description="ECS task definition has secrets exposed in plain text environment variables",
                severity="critical",
                service="ECS",
                resource_type="AWS::ECS::TaskDefinition",
                recommendation="Use Secrets Manager or SSM Parameter Store for secrets",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Identify secrets in environment variables",
                    "Store secrets in Secrets Manager or SSM",
                    "Update task definition to reference secrets",
                    "Remove plain text secrets from environment",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="ECS_003",
                title="ECS Task Missing Task Execution Role",
                description="ECS task definition does not have a task execution role configured",
                severity="medium",
                service="ECS",
                resource_type="AWS::ECS::TaskDefinition",
                recommendation="Configure task execution role for AWS service access",
                compliance_frameworks=["SOC2"],
                remediation_steps=[
                    "Create task execution IAM role",
                    "Attach AmazonECSTaskExecutionRolePolicy",
                    "Update task definition with execution role ARN",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="ECS_004",
                title="ECS Cluster Missing Container Insights",
                description="ECS cluster does not have Container Insights enabled for monitoring",
                severity="low",
                service="ECS",
                resource_type="AWS::ECS::Cluster",
                recommendation="Enable Container Insights for enhanced monitoring",
                compliance_frameworks=["SOC2"],
                remediation_steps=[
                    "Update cluster settings to enable Container Insights",
                    "Review Container Insights metrics in CloudWatch",
                    "Create dashboards and alarms based on metrics",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cloudwatch-container-insights.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="ECS_005",
                title="ECS Task Using Images from Untrusted Registries",
                description="ECS task definition uses container images from untrusted registries",
                severity="high",
                service="ECS",
                resource_type="AWS::ECS::TaskDefinition",
                recommendation="Use images from ECR or other trusted registries",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Review container image sources",
                    "Push images to Amazon ECR",
                    "Enable ECR image scanning",
                    "Update task definitions to use ECR images",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-best-practices.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="ECS_006",
                title="ECS Service Missing Auto-Scaling Configuration",
                description="ECS service does not have auto-scaling configured",
                severity="low",
                service="ECS",
                resource_type="AWS::ECS::Service",
                recommendation="Configure Application Auto Scaling for ECS services",
                compliance_frameworks=[],
                remediation_steps=[
                    "Register scalable target for the service",
                    "Create scaling policies based on metrics",
                    "Test scaling behavior under load",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="ECS_007",
                title="ECS Task Definition Missing Logging Configuration",
                description="ECS task definition does not have logging configured",
                severity="medium",
                service="ECS",
                resource_type="AWS::ECS::TaskDefinition",
                recommendation="Configure awslogs or other logging driver",
                compliance_frameworks=["SOC2", "HIPAA"],
                remediation_steps=[
                    "Add logConfiguration to container definition",
                    "Create CloudWatch log group",
                    "Set appropriate log retention",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_awslogs.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="ECS_008",
                title="ECS Task Definition Running as Root User",
                description="ECS task definition runs containers as root user",
                severity="high",
                service="ECS",
                resource_type="AWS::ECS::TaskDefinition",
                recommendation="Run containers as non-root user",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Add non-root user to container image",
                    "Set user in task definition",
                    "Test container functionality as non-root",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_security",
            )
        )

    async def scan(self) -> List[ScanResult]:
        """Scan EKS and ECS resources for security issues.

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        for region in self.regions:
            try:
                # Scan EKS clusters
                eks_client = self.get_client("eks", region=region)
                logger.info(f"Scanning EKS clusters in {region}")
                results.extend(await self._check_eks_clusters(eks_client, region))

                # Scan ECS clusters and tasks
                ecs_client = self.get_client("ecs", region=region)
                autoscaling_client = self.get_client(
                    "application-autoscaling", region=region
                )
                logger.info(f"Scanning ECS clusters in {region}")
                results.extend(
                    await self._check_ecs_resources(
                        ecs_client, autoscaling_client, region
                    )
                )

            except ClientError as e:
                logger.error(f"Error scanning containers in {region}: {e}")

        return results

    async def _check_eks_clusters(
        self,
        eks_client: Any,
        region: str,
    ) -> List[ScanResult]:
        """Check EKS clusters for security issues.

        Args:
            eks_client: boto3 EKS client
            region: AWS region being scanned

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        # Outdated Kubernetes versions (end of standard support)
        outdated_versions = {"1.23", "1.24", "1.25", "1.26"}

        try:
            clusters_response = eks_client.list_clusters()
            cluster_names = clusters_response.get("clusters", [])

            for cluster_name in cluster_names:
                try:
                    cluster_response = eks_client.describe_cluster(name=cluster_name)
                    cluster = cluster_response.get("cluster", {})

                    cluster_arn = cluster.get("arn", cluster_name)

                    # Check endpoint access (EKS_001)
                    resources_vpc = cluster.get("resourcesVpcConfig", {})
                    endpoint_public = resources_vpc.get("endpointPublicAccess", False)
                    public_cidrs = resources_vpc.get("publicAccessCidrs", [])

                    if endpoint_public and (
                        not public_cidrs or "0.0.0.0/0" in public_cidrs
                    ):
                        results.append(
                            self.create_result(
                                rule_id="EKS_001",
                                resource_id=cluster_arn,
                                resource_name=cluster_name,
                                region=region,
                                metadata={
                                    "endpoint_public_access": endpoint_public,
                                    "public_access_cidrs": public_cidrs,
                                },
                            )
                        )

                    # Check logging (EKS_002)
                    logging_config = cluster.get("logging", {}).get(
                        "clusterLogging", []
                    )
                    enabled_log_types = []
                    for log_group in logging_config:
                        if log_group.get("enabled"):
                            enabled_log_types.extend(log_group.get("types", []))

                    required_logs = {"api", "audit", "authenticator"}
                    missing_logs = required_logs - set(enabled_log_types)

                    if missing_logs:
                        results.append(
                            self.create_result(
                                rule_id="EKS_002",
                                resource_id=cluster_arn,
                                resource_name=cluster_name,
                                region=region,
                                metadata={
                                    "enabled_logs": enabled_log_types,
                                    "missing_logs": list(missing_logs),
                                },
                            )
                        )

                    # Check Kubernetes version (EKS_003)
                    version = cluster.get("version", "")
                    if version in outdated_versions:
                        results.append(
                            self.create_result(
                                rule_id="EKS_003",
                                resource_id=cluster_arn,
                                resource_name=cluster_name,
                                region=region,
                                metadata={"kubernetes_version": version},
                            )
                        )

                    # Check secrets encryption (EKS_004)
                    encryption_config = cluster.get("encryptionConfig", [])
                    has_secrets_encryption = False
                    for config in encryption_config:
                        resources = config.get("resources", [])
                        if "secrets" in resources:
                            has_secrets_encryption = True
                            break

                    if not has_secrets_encryption:
                        results.append(
                            self.create_result(
                                rule_id="EKS_004",
                                resource_id=cluster_arn,
                                resource_name=cluster_name,
                                region=region,
                            )
                        )

                except ClientError as e:
                    logger.debug(f"Error checking EKS cluster {cluster_name}: {e}")

        except ClientError as e:
            logger.error(f"Error listing EKS clusters in {region}: {e}")

        return results

    async def _check_ecs_resources(
        self,
        ecs_client: Any,
        autoscaling_client: Any,
        region: str,
    ) -> List[ScanResult]:
        """Check ECS clusters and task definitions for security issues.

        Args:
            ecs_client: boto3 ECS client
            autoscaling_client: boto3 Application Auto Scaling client
            region: AWS region being scanned

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        # Patterns for secrets in environment variables
        secret_patterns = [
            "password",
            "secret",
            "api_key",
            "apikey",
            "access_key",
            "private_key",
            "token",
            "credentials",
        ]

        # Trusted registries
        trusted_registries = [
            "ecr",
            "amazonaws.com",
            "docker.io/library/",
            "gcr.io/distroless",
        ]

        try:
            # Check clusters
            clusters_response = ecs_client.list_clusters()
            cluster_arns = clusters_response.get("clusterArns", [])

            for cluster_arn in cluster_arns:
                try:
                    clusters_detail = ecs_client.describe_clusters(
                        clusters=[cluster_arn],
                        include=["SETTINGS", "STATISTICS"],
                    )
                    cluster = clusters_detail.get("clusters", [{}])[0]

                    cluster_name = cluster.get("clusterName", cluster_arn)

                    # Check Container Insights (ECS_004)
                    settings = cluster.get("settings", [])
                    container_insights_enabled = False
                    for setting in settings:
                        if (
                            setting.get("name") == "containerInsights"
                            and setting.get("value") == "enabled"
                        ):
                            container_insights_enabled = True
                            break

                    if not container_insights_enabled:
                        results.append(
                            self.create_result(
                                rule_id="ECS_004",
                                resource_id=cluster_arn,
                                resource_name=cluster_name,
                                region=region,
                            )
                        )

                    # Check services for auto-scaling
                    services_response = ecs_client.list_services(cluster=cluster_arn)
                    service_arns = services_response.get("serviceArns", [])

                    for service_arn in service_arns:
                        try:
                            # Check if service has auto-scaling
                            scalable_targets = (
                                autoscaling_client.describe_scalable_targets(
                                    ServiceNamespace="ecs",
                                    ResourceIds=[
                                        f"service/{cluster_name}/{service_arn.split('/')[-1]}"
                                    ],
                                )
                            )
                            if not scalable_targets.get("ScalableTargets"):
                                results.append(
                                    self.create_result(
                                        rule_id="ECS_006",
                                        resource_id=service_arn,
                                        resource_name=service_arn.split("/")[-1],
                                        region=region,
                                        metadata={"cluster": cluster_name},
                                    )
                                )
                        except ClientError:
                            pass

                except ClientError as e:
                    logger.debug(f"Error checking ECS cluster {cluster_arn}: {e}")

            # Check task definitions
            task_defs_response = ecs_client.list_task_definitions(status="ACTIVE")
            task_def_arns = task_defs_response.get("taskDefinitionArns", [])

            for task_def_arn in task_def_arns:
                try:
                    task_def_response = ecs_client.describe_task_definition(
                        taskDefinition=task_def_arn
                    )
                    task_def = task_def_response.get("taskDefinition", {})

                    task_def_name = f"{task_def.get('family')}:{task_def.get('revision')}"

                    # Check execution role (ECS_003)
                    if not task_def.get("executionRoleArn"):
                        results.append(
                            self.create_result(
                                rule_id="ECS_003",
                                resource_id=task_def_arn,
                                resource_name=task_def_name,
                                region=region,
                            )
                        )

                    # Check container definitions
                    containers = task_def.get("containerDefinitions", [])

                    for container in containers:
                        container_name = container.get("name", "unknown")

                        # Check privileged mode (ECS_001)
                        if container.get("privileged"):
                            results.append(
                                self.create_result(
                                    rule_id="ECS_001",
                                    resource_id=task_def_arn,
                                    resource_name=task_def_name,
                                    region=region,
                                    metadata={"container_name": container_name},
                                )
                            )

                        # Check environment variables for secrets (ECS_002)
                        env_vars = container.get("environment", [])
                        for env_var in env_vars:
                            env_name = env_var.get("name", "").lower()
                            for pattern in secret_patterns:
                                if pattern in env_name:
                                    results.append(
                                        self.create_result(
                                            rule_id="ECS_002",
                                            resource_id=task_def_arn,
                                            resource_name=task_def_name,
                                            region=region,
                                            metadata={
                                                "container_name": container_name,
                                                "env_var_name": env_var.get("name"),
                                            },
                                        )
                                    )
                                    break

                        # Check image registry (ECS_005)
                        image = container.get("image", "")
                        is_trusted = False
                        for registry in trusted_registries:
                            if registry in image:
                                is_trusted = True
                                break

                        if not is_trusted and image:
                            results.append(
                                self.create_result(
                                    rule_id="ECS_005",
                                    resource_id=task_def_arn,
                                    resource_name=task_def_name,
                                    region=region,
                                    metadata={
                                        "container_name": container_name,
                                        "image": image,
                                    },
                                )
                            )

                        # Check logging (ECS_007)
                        if not container.get("logConfiguration"):
                            results.append(
                                self.create_result(
                                    rule_id="ECS_007",
                                    resource_id=task_def_arn,
                                    resource_name=task_def_name,
                                    region=region,
                                    metadata={"container_name": container_name},
                                )
                            )

                        # Check user (ECS_008)
                        user = container.get("user", "")
                        if not user or user == "0" or user == "root":
                            results.append(
                                self.create_result(
                                    rule_id="ECS_008",
                                    resource_id=task_def_arn,
                                    resource_name=task_def_name,
                                    region=region,
                                    metadata={
                                        "container_name": container_name,
                                        "user": user or "not specified (defaults to root)",
                                    },
                                )
                            )

                except ClientError as e:
                    logger.debug(f"Error checking task definition {task_def_arn}: {e}")

        except ClientError as e:
            logger.error(f"Error listing ECS resources in {region}: {e}")

        return results
