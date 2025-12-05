"""CloudFront Security Scanner.

Issue #140: 9.1.3 CloudFront distribution scanner

Implements security scanning for Amazon CloudFront distributions checking for SSL/TLS
configuration, origin access, logging, and security headers.
"""

import logging
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

logger = logging.getLogger(__name__)


class CloudFrontScanner(BaseScanner):
    """Scanner for CloudFront distribution security configurations.

    Implements security scanning for CloudFront distributions including:
    - SSL/TLS certificate validity and security
    - Origin access identity configuration for S3 origins
    - Viewer protocol policy (HTTPS enforcement)
    - Missing security headers (HSTS, CSP, X-Frame-Options)
    - Logging configuration
    - WAF integration
    - Geo-restriction configuration
    - Cache behavior security settings
    """

    SERVICE = "CloudFront"

    def _register_rules(self) -> None:
        """Register CloudFront security rules."""
        self.register_rule(
            ScannerRule(
                rule_id="CF_001",
                title="CloudFront Distribution Allows HTTP (Not HTTPS Only)",
                description="CloudFront distribution allows HTTP connections instead of enforcing HTTPS",
                severity="high",
                service="CloudFront",
                resource_type="AWS::CloudFront::Distribution",
                recommendation="Configure ViewerProtocolPolicy to redirect-to-https or https-only",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA", "SOC2"],
                remediation_steps=[
                    "Review distribution viewer protocol policy",
                    "Update default cache behavior to redirect-to-https",
                    "Update all cache behaviors to enforce HTTPS",
                    "Test that HTTP requests are properly redirected",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-viewers-to-cloudfront.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="CF_002",
                title="CloudFront Distribution Missing Origin Access Identity for S3",
                description="CloudFront distribution with S3 origin is not using Origin Access Identity",
                severity="high",
                service="CloudFront",
                resource_type="AWS::CloudFront::Distribution",
                recommendation="Configure Origin Access Identity (OAI) or Origin Access Control (OAC) for S3 origins",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Create Origin Access Identity or Origin Access Control",
                    "Update S3 bucket policy to allow access only from CloudFront",
                    "Update CloudFront origin configuration to use OAI/OAC",
                    "Remove public access from S3 bucket",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="CF_003",
                title="CloudFront Distribution Missing Security Headers",
                description="CloudFront distribution is not adding security headers to responses",
                severity="medium",
                service="CloudFront",
                resource_type="AWS::CloudFront::Distribution",
                recommendation="Configure response headers policy with security headers",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Create response headers policy",
                    "Enable security headers (HSTS, CSP, X-Frame-Options, etc.)",
                    "Apply policy to cache behaviors",
                    "Test headers are present in responses",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/adding-response-headers.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="CF_004",
                title="CloudFront Distribution Missing Logging",
                description="CloudFront distribution does not have access logging enabled",
                severity="medium",
                service="CloudFront",
                resource_type="AWS::CloudFront::Distribution",
                recommendation="Enable standard logging or real-time logging for monitoring",
                compliance_frameworks=["SOC2", "HIPAA", "PCI-DSS"],
                remediation_steps=[
                    "Create S3 bucket for CloudFront logs",
                    "Enable standard logging in distribution settings",
                    "Consider real-time logging for immediate analysis",
                    "Configure log retention policy",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/AccessLogs.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="CF_005",
                title="CloudFront Distribution Missing WAF Integration",
                description="CloudFront distribution is not protected by AWS WAF",
                severity="high",
                service="CloudFront",
                resource_type="AWS::CloudFront::Distribution",
                recommendation="Attach AWS WAF web ACL to protect against web exploits",
                compliance_frameworks=["CIS", "PCI-DSS", "SOC2"],
                remediation_steps=[
                    "Create AWS WAF web ACL in us-east-1 (global)",
                    "Add managed rule groups for common threats",
                    "Associate web ACL with CloudFront distribution",
                    "Monitor WAF logs for blocked requests",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/distribution-web-awswaf.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="CF_006",
                title="CloudFront Distribution Using Outdated SSL/TLS Protocols",
                description="CloudFront distribution supports outdated or insecure SSL/TLS protocols",
                severity="high",
                service="CloudFront",
                resource_type="AWS::CloudFront::Distribution",
                recommendation="Update minimum protocol version to TLSv1.2 or higher",
                compliance_frameworks=["CIS", "PCI-DSS", "HIPAA"],
                remediation_steps=[
                    "Review current SSL/TLS protocol settings",
                    "Update viewer certificate to use TLSv1.2_2021 or newer",
                    "Update origin protocol policy to TLSv1.2",
                    "Test that clients can connect with updated protocols",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/secure-connections-supported-viewer-protocols-ciphers.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="CF_007",
                title="CloudFront Distribution with Public S3 Bucket Origin",
                description="CloudFront distribution is using a public S3 bucket as origin",
                severity="medium",
                service="CloudFront",
                resource_type="AWS::CloudFront::Distribution",
                recommendation="Make S3 bucket private and use OAI/OAC for CloudFront access",
                compliance_frameworks=["CIS", "SOC2"],
                remediation_steps=[
                    "Configure Origin Access Control for the S3 origin",
                    "Update S3 bucket policy to allow only CloudFront access",
                    "Block public access to S3 bucket",
                    "Verify content is only accessible via CloudFront",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="CF_008",
                title="CloudFront Distribution Missing Custom Error Pages",
                description="CloudFront distribution does not have custom error pages configured",
                severity="low",
                service="CloudFront",
                resource_type="AWS::CloudFront::Distribution",
                recommendation="Configure custom error responses to prevent information disclosure",
                compliance_frameworks=[],
                remediation_steps=[
                    "Create custom error pages (403, 404, 500, etc.)",
                    "Upload error pages to S3 or origin",
                    "Configure custom error responses in distribution",
                    "Test error page responses",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/GeneratingCustomErrorResponses.html",
            )
        )

        self.register_rule(
            ScannerRule(
                rule_id="CF_009",
                title="CloudFront Distribution Cache Allowing Sensitive Headers",
                description="CloudFront cache behavior forwards sensitive headers that could leak information",
                severity="medium",
                service="CloudFront",
                resource_type="AWS::CloudFront::Distribution",
                recommendation="Review forwarded headers and remove unnecessary sensitive headers",
                compliance_frameworks=["SOC2"],
                remediation_steps=[
                    "Review cache behavior header forwarding",
                    "Remove forwarding of sensitive headers",
                    "Use only necessary headers for cache key",
                    "Test caching behavior after changes",
                ],
                documentation_url="https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/RequestAndResponseBehaviorCustomOrigin.html",
            )
        )

    async def scan(self) -> List[ScanResult]:
        """Scan CloudFront distributions for security issues.

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        # CloudFront is a global service, only needs to be scanned once
        try:
            cloudfront_client = self.get_client("cloudfront", region="us-east-1")
            s3_client = self.get_client("s3", region="us-east-1")
            logger.info("Scanning CloudFront distributions")

            results.extend(
                await self._check_distributions(cloudfront_client, s3_client)
            )

        except ClientError as e:
            logger.error(f"Error scanning CloudFront: {e}")

        return results

    async def _check_distributions(
        self,
        cloudfront_client: Any,
        s3_client: Any,
    ) -> List[ScanResult]:
        """Check CloudFront distributions for security issues.

        Args:
            cloudfront_client: boto3 CloudFront client
            s3_client: boto3 S3 client

        Returns:
            List of scan results
        """
        results: List[ScanResult] = []

        # Outdated TLS versions
        outdated_tls = {
            "SSLv3",
            "TLSv1",
            "TLSv1_2016",
            "TLSv1.1_2016",
        }

        # Sensitive headers to check
        sensitive_headers = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
        }

        try:
            paginator = cloudfront_client.get_paginator("list_distributions")
            for page in paginator.paginate():
                distribution_list = page.get("DistributionList", {})
                distributions = distribution_list.get("Items", [])

                for dist in distributions:
                    dist_id = dist["Id"]
                    dist_arn = dist["ARN"]
                    domain_name = dist.get("DomainName", dist_id)

                    # Get full distribution config
                    try:
                        config_response = cloudfront_client.get_distribution(
                            Id=dist_id
                        )
                        full_dist = config_response.get("Distribution", {})
                        dist_config = full_dist.get("DistributionConfig", {})

                        # Check default cache behavior
                        default_behavior = dist_config.get("DefaultCacheBehavior", {})

                        # Check HTTP/HTTPS (CF_001)
                        viewer_protocol = default_behavior.get("ViewerProtocolPolicy", "")
                        if viewer_protocol == "allow-all":
                            results.append(
                                self.create_result(
                                    rule_id="CF_001",
                                    resource_id=dist_arn,
                                    resource_name=domain_name,
                                    region="global",
                                    metadata={
                                        "viewer_protocol_policy": viewer_protocol,
                                    },
                                )
                            )

                        # Check origins
                        origins = dist_config.get("Origins", {}).get("Items", [])
                        for origin in origins:
                            origin_id = origin.get("Id", "unknown")
                            origin_domain = origin.get("DomainName", "")

                            # Check S3 origins for OAI/OAC (CF_002)
                            if ".s3." in origin_domain or origin_domain.endswith(
                                ".s3.amazonaws.com"
                            ):
                                s3_config = origin.get("S3OriginConfig", {})
                                oac_id = origin.get("OriginAccessControlId", "")
                                oai = s3_config.get(
                                    "OriginAccessIdentity", ""
                                )

                                if not oac_id and not oai:
                                    results.append(
                                        self.create_result(
                                            rule_id="CF_002",
                                            resource_id=dist_arn,
                                            resource_name=domain_name,
                                            region="global",
                                            metadata={
                                                "origin_id": origin_id,
                                                "origin_domain": origin_domain,
                                            },
                                        )
                                    )

                                # Check if S3 bucket is public (CF_007)
                                try:
                                    bucket_name = origin_domain.split(".s3.")[
                                        0
                                    ].split(".s3-")[0]
                                    if bucket_name:
                                        public_access = (
                                            s3_client.get_public_access_block(
                                                Bucket=bucket_name
                                            )
                                        )
                                        config = public_access.get(
                                            "PublicAccessBlockConfiguration", {}
                                        )
                                        if not config.get(
                                            "BlockPublicAcls"
                                        ) or not config.get("BlockPublicPolicy"):
                                            results.append(
                                                self.create_result(
                                                    rule_id="CF_007",
                                                    resource_id=dist_arn,
                                                    resource_name=domain_name,
                                                    region="global",
                                                    metadata={
                                                        "bucket_name": bucket_name,
                                                    },
                                                )
                                            )
                                except ClientError:
                                    pass  # Bucket may not exist or no access

                            # Check origin SSL protocol (CF_006 for origin)
                            custom_origin = origin.get("CustomOriginConfig", {})
                            if custom_origin:
                                origin_protocols = custom_origin.get(
                                    "OriginSslProtocols", {}
                                ).get("Items", [])
                                for protocol in origin_protocols:
                                    if protocol in outdated_tls:
                                        results.append(
                                            self.create_result(
                                                rule_id="CF_006",
                                                resource_id=dist_arn,
                                                resource_name=domain_name,
                                                region="global",
                                                metadata={
                                                    "protocol": protocol,
                                                    "location": "origin",
                                                    "origin_id": origin_id,
                                                },
                                            )
                                        )
                                        break

                        # Check viewer certificate (CF_006)
                        viewer_cert = dist_config.get("ViewerCertificate", {})
                        min_protocol = viewer_cert.get("MinimumProtocolVersion", "")
                        if min_protocol in outdated_tls:
                            results.append(
                                self.create_result(
                                    rule_id="CF_006",
                                    resource_id=dist_arn,
                                    resource_name=domain_name,
                                    region="global",
                                    metadata={
                                        "minimum_protocol_version": min_protocol,
                                        "location": "viewer",
                                    },
                                )
                            )

                        # Check response headers policy (CF_003)
                        response_headers_policy_id = default_behavior.get(
                            "ResponseHeadersPolicyId"
                        )
                        if not response_headers_policy_id:
                            results.append(
                                self.create_result(
                                    rule_id="CF_003",
                                    resource_id=dist_arn,
                                    resource_name=domain_name,
                                    region="global",
                                )
                            )

                        # Check logging (CF_004)
                        logging_config = dist_config.get("Logging", {})
                        if not logging_config.get("Enabled"):
                            results.append(
                                self.create_result(
                                    rule_id="CF_004",
                                    resource_id=dist_arn,
                                    resource_name=domain_name,
                                    region="global",
                                )
                            )

                        # Check WAF (CF_005)
                        waf_acl = dist_config.get("WebACLId", "")
                        if not waf_acl:
                            results.append(
                                self.create_result(
                                    rule_id="CF_005",
                                    resource_id=dist_arn,
                                    resource_name=domain_name,
                                    region="global",
                                )
                            )

                        # Check custom error responses (CF_008)
                        error_responses = dist_config.get(
                            "CustomErrorResponses", {}
                        ).get("Items", [])
                        if not error_responses:
                            results.append(
                                self.create_result(
                                    rule_id="CF_008",
                                    resource_id=dist_arn,
                                    resource_name=domain_name,
                                    region="global",
                                )
                            )

                        # Check forwarded headers (CF_009)
                        cache_policy_id = default_behavior.get("CachePolicyId")
                        if not cache_policy_id:
                            # Legacy forwarded headers configuration
                            forwarded_values = default_behavior.get(
                                "ForwardedValues", {}
                            )
                            headers = forwarded_values.get("Headers", {}).get(
                                "Items", []
                            )
                            headers_lower = [h.lower() for h in headers]
                            for sensitive in sensitive_headers:
                                if sensitive in headers_lower:
                                    results.append(
                                        self.create_result(
                                            rule_id="CF_009",
                                            resource_id=dist_arn,
                                            resource_name=domain_name,
                                            region="global",
                                            metadata={
                                                "sensitive_header": sensitive,
                                            },
                                        )
                                    )
                                    break

                    except ClientError as e:
                        logger.debug(f"Error checking distribution {dist_id}: {e}")

        except ClientError as e:
            logger.error(f"Error listing CloudFront distributions: {e}")

        return results
