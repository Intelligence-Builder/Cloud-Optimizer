"""API Gateway Security Scanner.

Issue #134: 9.1.2 API Gateway scanner with rules

Implements security scanning for AWS API Gateway (REST and HTTP APIs) with rules
checking for authentication, authorization, and common misconfigurations.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

logger = logging.getLogger(__name__)


class APIGatewayScanner(BaseScanner):
    """Scanner for API Gateway security configurations.

    Implements security scanning for AWS API Gateway REST and HTTP APIs with rules
    checking for authentication, authorization, and common misconfigurations including:
    - Missing authentication mechanism
    - Publicly accessible without authorization
    - Missing CloudWatch logging
    - Missing throttling/rate limiting
    - Missing request validation
    - Using default endpoint without custom domain
    - Stage missing cache encryption
    - Missing WAF integration for public APIs
    - Overly permissive resource policy
    """

    SERVICE = "APIGateway"

    def _register_rules(self) -> None:
        """Register API Gateway security rules."""
        self.register_rule(
            ScannerRule(
                rule_id="APIGW_001",
                title="API Gateway Missing Authentication Mechanism",
                description="API Gateway does not have any authentication mechanism configured",
                severity="critical",
                service="APIGateway",
                resource_type="AWS::ApiGateway::RestApi",
                recommendation="Configure IAM, Cognito, or Lambda authorizers for API authentication",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Review API authentication requirements",
                    "Implement IAM authorization for internal APIs",
                    "Configure Cognito user pools for user authentication",
                    "Create Lambda authorizers for custom authentication",
                    "Apply authentication to all routes requiring protection",
                ],
                documentation_url="https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-control-access-to-api.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="APIGW_002",
                title="API Gateway Publicly Accessible Without Authorization",
                description="API Gateway endpoint is publicly accessible without any authorization",
                severity="critical",
                service="APIGateway",
                resource_type="AWS::ApiGateway::RestApi",
                recommendation="Add authentication or restrict access using resource policies",
                compliance_frameworks=["CIS", "PCI-DSS", "SOC2"],
                remediation_steps=[
                    "Identify sensitive endpoints",
                    "Add authorization to all public-facing endpoints",
                    "Consider using private APIs for internal services",
                    "Implement resource policies to restrict access",
                ],
                documentation_url="https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-authorization-flow.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="APIGW_003",
                title="API Gateway Missing CloudWatch Logging",
                description="API Gateway does not have CloudWatch logging enabled",
                severity="medium",
                service="APIGateway",
                resource_type="AWS::ApiGateway::Stage",
                recommendation="Enable CloudWatch logging for monitoring and troubleshooting",
                compliance_frameworks=["SOC2", "HIPAA"],
                remediation_steps=[
                    "Create CloudWatch Logs role for API Gateway",
                    "Enable execution logging on the stage",
                    "Enable access logging for request/response logging",
                    "Configure log retention policy",
                ],
                documentation_url="https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="APIGW_004",
                title="API Gateway Missing Throttling/Rate Limiting",
                description="API Gateway does not have throttling or rate limiting configured",
                severity="medium",
                service="APIGateway",
                resource_type="AWS::ApiGateway::Stage",
                recommendation="Configure throttling to protect against abuse and DoS attacks",
                compliance_frameworks=["SOC2"],
                remediation_steps=[
                    "Determine appropriate rate limits based on usage patterns",
                    "Configure stage-level throttling settings",
                    "Set method-level throttling for sensitive endpoints",
                    "Implement usage plans with API keys for metered access",
                ],
                documentation_url="https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="APIGW_005",
                title="API Gateway Missing Request Validation",
                description="API Gateway does not validate request parameters or body",
                severity="low",
                service="APIGateway",
                resource_type="AWS::ApiGateway::RestApi",
                recommendation="Enable request validation to reject invalid requests early",
                compliance_frameworks=[],
                remediation_steps=[
                    "Create request validators for your API",
                    "Define models for request body validation",
                    "Apply validators to methods requiring validation",
                    "Test validation with invalid requests",
                ],
                documentation_url="https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-method-request-validation.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="APIGW_006",
                title="API Gateway Using Default Endpoint Without Custom Domain",
                description="API Gateway is using the default execute-api endpoint without a custom domain",
                severity="low",
                service="APIGateway",
                resource_type="AWS::ApiGateway::RestApi",
                recommendation="Use custom domain names for production APIs",
                compliance_frameworks=[],
                remediation_steps=[
                    "Register a custom domain name",
                    "Request or import SSL certificate in ACM",
                    "Create custom domain mapping in API Gateway",
                    "Update DNS to point to API Gateway domain",
                ],
                documentation_url="https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-custom-domains.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="APIGW_007",
                title="API Gateway Stage Missing Cache Encryption",
                description="API Gateway stage has caching enabled without encryption",
                severity="medium",
                service="APIGateway",
                resource_type="AWS::ApiGateway::Stage",
                recommendation="Enable cache encryption if caching is used",
                compliance_frameworks=["PCI-DSS", "HIPAA"],
                remediation_steps=[
                    "Review cached data for sensitivity",
                    "Enable cache encryption in stage settings",
                    "Consider disabling caching for sensitive endpoints",
                ],
                documentation_url="https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-caching.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="APIGW_008",
                title="API Gateway Missing WAF Integration",
                description="Public API Gateway is not protected by AWS WAF",
                severity="high",
                service="APIGateway",
                resource_type="AWS::ApiGateway::RestApi",
                recommendation="Attach AWS WAF web ACL to protect against web exploits",
                compliance_frameworks=["CIS", "PCI-DSS", "SOC2"],
                remediation_steps=[
                    "Create AWS WAF web ACL with appropriate rules",
                    "Include OWASP rules for common web attacks",
                    "Associate WAF web ACL with API Gateway stage",
                    "Monitor WAF logs for blocked requests",
                ],
                documentation_url="https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-control-access-aws-waf.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="APIGW_009",
                title="API Gateway Overly Permissive Resource Policy",
                description="API Gateway resource policy allows overly permissive access",
                severity="high",
                service="APIGateway",
                resource_type="AWS::ApiGateway::RestApi",
                recommendation="Restrict resource policy to specific principals and IP ranges",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Review current resource policy",
                    "Remove wildcard principal permissions",
                    "Add IP-based restrictions where appropriate",
                    "Use VPC endpoint policies for private APIs",
                ],
                documentation_url="https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-resource-policies.html",
            )
        )

    async def scan(self) -> List[ScanResult]:
        """Scan API Gateway resources for security issues.

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        for region in self.regions:
            try:
                # Scan REST APIs
                apigw_client = self.get_client("apigateway", region=region)
                waf_client = self.get_client("wafv2", region=region)
                logger.info(f"Scanning API Gateway REST APIs in {region}")
                results.extend(
                    await self._check_rest_apis(apigw_client, waf_client, region)
                )

                # Scan HTTP APIs (API Gateway V2)
                apigwv2_client = self.get_client("apigatewayv2", region=region)
                logger.info(f"Scanning API Gateway HTTP APIs in {region}")
                results.extend(
                    await self._check_http_apis(apigwv2_client, region)
                )

            except ClientError as e:
                logger.error(f"Error scanning API Gateway in {region}: {e}")

        return results

    async def _check_rest_apis(
        self,
        apigw_client: Any,
        waf_client: Any,
        region: str,
    ) -> List[ScanResult]:
        """Check REST APIs for security issues.

        Args:
            apigw_client: boto3 API Gateway client
            waf_client: boto3 WAFv2 client
            region: AWS region being scanned

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        try:
            paginator = apigw_client.get_paginator("get_rest_apis")
            for page in paginator.paginate():
                apis = page.get("items", [])

                for api in apis:
                    api_id = api["id"]
                    api_name = api.get("name", api_id)

                    # Get API details
                    try:
                        # Check resource policy (APIGW_009)
                        policy_str = api.get("policy")
                        if policy_str:
                            policy = json.loads(policy_str)
                            for statement in policy.get("Statement", []):
                                principal = statement.get("Principal", {})
                                if principal == "*" or (
                                    isinstance(principal, dict)
                                    and principal.get("AWS") == "*"
                                ):
                                    condition = statement.get("Condition", {})
                                    if not condition:
                                        results.append(
                                            self.create_result(
                                                rule_id="APIGW_009",
                                                resource_id=api_id,
                                                resource_name=api_name,
                                                region=region,
                                                metadata={
                                                    "principal": str(principal),
                                                    "statement_effect": statement.get(
                                                        "Effect"
                                                    ),
                                                },
                                            )
                                        )

                        # Get authorizers
                        authorizers_response = apigw_client.get_authorizers(
                            restApiId=api_id
                        )
                        authorizers = authorizers_response.get("items", [])

                        # Get resources and methods
                        resources_response = apigw_client.get_resources(
                            restApiId=api_id
                        )
                        resources = resources_response.get("items", [])

                        has_authentication = len(authorizers) > 0
                        has_validators = False
                        unauthenticated_methods = []

                        # Check request validators
                        validators_response = apigw_client.get_request_validators(
                            restApiId=api_id
                        )
                        validators = validators_response.get("items", [])
                        if validators:
                            has_validators = True

                        # Check each resource and method
                        for resource in resources:
                            resource_path = resource.get("path", "/")
                            methods = resource.get("resourceMethods", {})

                            for method_name, method_details in methods.items():
                                if method_name == "OPTIONS":
                                    continue  # Skip CORS preflight

                                # Get method details
                                try:
                                    method_info = apigw_client.get_method(
                                        restApiId=api_id,
                                        resourceId=resource["id"],
                                        httpMethod=method_name,
                                    )

                                    auth_type = method_info.get("authorizationType")
                                    if auth_type in ["NONE", None]:
                                        unauthenticated_methods.append(
                                            f"{method_name} {resource_path}"
                                        )

                                except ClientError:
                                    pass

                        # Check if API has no authentication (APIGW_001)
                        if not has_authentication and not any(
                            "IAM" in str(m.get("authorizationType", ""))
                            for r in resources
                            for m in r.get("resourceMethods", {}).values()
                        ):
                            results.append(
                                self.create_result(
                                    rule_id="APIGW_001",
                                    resource_id=api_id,
                                    resource_name=api_name,
                                    region=region,
                                    metadata={"authorizer_count": 0},
                                )
                            )

                        # Check for unauthenticated public endpoints (APIGW_002)
                        if unauthenticated_methods:
                            results.append(
                                self.create_result(
                                    rule_id="APIGW_002",
                                    resource_id=api_id,
                                    resource_name=api_name,
                                    region=region,
                                    metadata={
                                        "unauthenticated_methods": unauthenticated_methods[
                                            :10
                                        ],
                                        "total_unauthenticated": len(
                                            unauthenticated_methods
                                        ),
                                    },
                                )
                            )

                        # Check for missing request validation (APIGW_005)
                        if not has_validators:
                            results.append(
                                self.create_result(
                                    rule_id="APIGW_005",
                                    resource_id=api_id,
                                    resource_name=api_name,
                                    region=region,
                                )
                            )

                        # Check for default endpoint (APIGW_006)
                        if not api.get("disableExecuteApiEndpoint", False):
                            # Check if custom domain mappings exist
                            try:
                                domain_names = apigw_client.get_domain_names()
                                has_custom_domain = False
                                for domain in domain_names.get("items", []):
                                    mappings = apigw_client.get_base_path_mappings(
                                        domainName=domain["domainName"]
                                    )
                                    for mapping in mappings.get("items", []):
                                        if mapping.get("restApiId") == api_id:
                                            has_custom_domain = True
                                            break
                                    if has_custom_domain:
                                        break

                                if not has_custom_domain:
                                    results.append(
                                        self.create_result(
                                            rule_id="APIGW_006",
                                            resource_id=api_id,
                                            resource_name=api_name,
                                            region=region,
                                        )
                                    )
                            except ClientError:
                                pass

                        # Check stages
                        stages_response = apigw_client.get_stages(restApiId=api_id)
                        stages = stages_response.get("item", [])

                        for stage in stages:
                            stage_name = stage.get("stageName", "unknown")
                            stage_id = f"{api_id}/{stage_name}"

                            # Check CloudWatch logging (APIGW_003)
                            method_settings = stage.get("methodSettings", {})
                            has_logging = False
                            for settings in method_settings.values():
                                if settings.get("loggingLevel") in [
                                    "INFO",
                                    "ERROR",
                                ]:
                                    has_logging = True
                                    break

                            if (
                                not has_logging
                                and not stage.get("accessLogSettings", {}).get(
                                    "destinationArn"
                                )
                            ):
                                results.append(
                                    self.create_result(
                                        rule_id="APIGW_003",
                                        resource_id=stage_id,
                                        resource_name=f"{api_name}/{stage_name}",
                                        region=region,
                                    )
                                )

                            # Check throttling (APIGW_004)
                            default_settings = method_settings.get("*/*", {})
                            if (
                                not default_settings.get("throttlingBurstLimit")
                                and not default_settings.get("throttlingRateLimit")
                            ):
                                results.append(
                                    self.create_result(
                                        rule_id="APIGW_004",
                                        resource_id=stage_id,
                                        resource_name=f"{api_name}/{stage_name}",
                                        region=region,
                                    )
                                )

                            # Check cache encryption (APIGW_007)
                            for path, settings in method_settings.items():
                                if settings.get("cachingEnabled") and not settings.get(
                                    "cacheDataEncrypted"
                                ):
                                    results.append(
                                        self.create_result(
                                            rule_id="APIGW_007",
                                            resource_id=stage_id,
                                            resource_name=f"{api_name}/{stage_name}",
                                            region=region,
                                            metadata={"method_path": path},
                                        )
                                    )
                                    break

                            # Check WAF integration (APIGW_008)
                            stage_arn = f"arn:aws:apigateway:{region}::/restapis/{api_id}/stages/{stage_name}"
                            try:
                                waf_response = waf_client.get_web_acl_for_resource(
                                    ResourceArn=stage_arn
                                )
                                if not waf_response.get("WebACL"):
                                    results.append(
                                        self.create_result(
                                            rule_id="APIGW_008",
                                            resource_id=stage_id,
                                            resource_name=f"{api_name}/{stage_name}",
                                            region=region,
                                        )
                                    )
                            except ClientError:
                                # No WAF association
                                results.append(
                                    self.create_result(
                                        rule_id="APIGW_008",
                                        resource_id=stage_id,
                                        resource_name=f"{api_name}/{stage_name}",
                                        region=region,
                                    )
                                )

                    except ClientError as e:
                        logger.debug(f"Error checking API {api_id}: {e}")

        except ClientError as e:
            logger.error(f"Error listing REST APIs in {region}: {e}")

        return results

    async def _check_http_apis(
        self,
        apigwv2_client: Any,
        region: str,
    ) -> List[ScanResult]:
        """Check HTTP APIs (API Gateway V2) for security issues.

        Args:
            apigwv2_client: boto3 API Gateway V2 client
            region: AWS region being scanned

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        try:
            paginator = apigwv2_client.get_paginator("get_apis")
            for page in paginator.paginate():
                apis = page.get("Items", [])

                for api in apis:
                    api_id = api["ApiId"]
                    api_name = api.get("Name", api_id)
                    protocol_type = api.get("ProtocolType", "HTTP")

                    # Skip WebSocket APIs for now
                    if protocol_type == "WEBSOCKET":
                        continue

                    try:
                        # Get authorizers
                        authorizers_response = apigwv2_client.get_authorizers(
                            ApiId=api_id
                        )
                        authorizers = authorizers_response.get("Items", [])

                        # Get routes
                        routes_response = apigwv2_client.get_routes(ApiId=api_id)
                        routes = routes_response.get("Items", [])

                        # Check authentication (APIGW_001)
                        if not authorizers:
                            results.append(
                                self.create_result(
                                    rule_id="APIGW_001",
                                    resource_id=api_id,
                                    resource_name=api_name,
                                    region=region,
                                    metadata={
                                        "api_type": "HTTP API",
                                        "protocol": protocol_type,
                                    },
                                )
                            )

                        # Check for unauthenticated routes (APIGW_002)
                        unauthenticated_routes = []
                        for route in routes:
                            if route.get("AuthorizationType") == "NONE":
                                route_key = route.get("RouteKey", "unknown")
                                if route_key != "$default":
                                    unauthenticated_routes.append(route_key)

                        if unauthenticated_routes:
                            results.append(
                                self.create_result(
                                    rule_id="APIGW_002",
                                    resource_id=api_id,
                                    resource_name=api_name,
                                    region=region,
                                    metadata={
                                        "api_type": "HTTP API",
                                        "unauthenticated_routes": unauthenticated_routes[
                                            :10
                                        ],
                                        "total_unauthenticated": len(
                                            unauthenticated_routes
                                        ),
                                    },
                                )
                            )

                        # Check stages
                        stages_response = apigwv2_client.get_stages(ApiId=api_id)
                        stages = stages_response.get("Items", [])

                        for stage in stages:
                            stage_name = stage.get("StageName", "unknown")
                            stage_id = f"{api_id}/{stage_name}"

                            # Check logging (APIGW_003)
                            access_log_settings = stage.get("AccessLogSettings", {})
                            if not access_log_settings.get("DestinationArn"):
                                results.append(
                                    self.create_result(
                                        rule_id="APIGW_003",
                                        resource_id=stage_id,
                                        resource_name=f"{api_name}/{stage_name}",
                                        region=region,
                                        metadata={"api_type": "HTTP API"},
                                    )
                                )

                            # Check throttling (APIGW_004)
                            default_route_settings = stage.get(
                                "DefaultRouteSettings", {}
                            )
                            if (
                                not default_route_settings.get("ThrottlingBurstLimit")
                                and not default_route_settings.get("ThrottlingRateLimit")
                            ):
                                results.append(
                                    self.create_result(
                                        rule_id="APIGW_004",
                                        resource_id=stage_id,
                                        resource_name=f"{api_name}/{stage_name}",
                                        region=region,
                                        metadata={"api_type": "HTTP API"},
                                    )
                                )

                    except ClientError as e:
                        logger.debug(f"Error checking HTTP API {api_id}: {e}")

        except ClientError as e:
            logger.error(f"Error listing HTTP APIs in {region}: {e}")

        return results
