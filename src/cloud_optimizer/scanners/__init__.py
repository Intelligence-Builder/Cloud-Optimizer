"""Scanner modules for Cloud Optimizer.

This module provides AWS security scanning capabilities including:
- Service-specific scanners (Lambda, API Gateway, CloudFront, EKS/ECS, etc.)
- Multi-account scanning support
- Cross-account role assumption
- Custom rule engine
- Rule import/export functionality
"""

# Issue #134: API Gateway scanner
from cloud_optimizer.scanners.apigateway_scanner import APIGatewayScanner
from cloud_optimizer.scanners.base import BaseScanner, ScannerRule, ScanResult

# Issue #140: CloudFront scanner
from cloud_optimizer.scanners.cloudfront_scanner import CloudFrontScanner

# Issue #142: EKS/ECS container scanner
from cloud_optimizer.scanners.container_scanner import ContainerScanner
from cloud_optimizer.scanners.cost import CostScanner

# Issue #148: Cross-account role assumption
from cloud_optimizer.scanners.cross_account import (
    AssumedRoleCredentials,
    CredentialCache,
    CrossAccountRoleManager,
    get_cloudformation_template,
    get_terraform_template,
)

# Issues #150, #151: Custom rule engine and import/export
from cloud_optimizer.scanners.custom_rules import (
    CustomRule,
    RuleCondition,
    RuleEngine,
    RuleImportExporter,
    RuleOperator,
    RulePackage,
    RuleType,
    RuleValidator,
    get_example_rules,
)
from cloud_optimizer.scanners.ec2 import EC2Scanner
from cloud_optimizer.scanners.iam import IAMScanner
from cloud_optimizer.scanners.lambda_scanner import LambdaScanner

# Issue #147: Multi-account scanning support
from cloud_optimizer.scanners.multi_account import (
    AccountRegistry,
    AccountScanResult,
    AccountStatus,
    AuthMethod,
    AWSAccount,
    MultiAccountScanner,
)
from cloud_optimizer.scanners.rds import RDSScanner
from cloud_optimizer.scanners.registry import ScannerRegistry
from cloud_optimizer.scanners.s3 import S3Scanner

# Issue #143: Secrets Manager and Parameter Store scanner
from cloud_optimizer.scanners.secrets_scanner import SecretsScanner

__all__ = [
    # Base classes
    "BaseScanner",
    "ScanResult",
    "ScannerRule",
    # Service scanners
    "CostScanner",
    "EC2Scanner",
    "IAMScanner",
    "LambdaScanner",
    "RDSScanner",
    "S3Scanner",
    "APIGatewayScanner",
    "CloudFrontScanner",
    "ContainerScanner",
    "SecretsScanner",
    # Registry
    "ScannerRegistry",
    # Multi-account
    "AccountRegistry",
    "AccountScanResult",
    "AccountStatus",
    "AuthMethod",
    "AWSAccount",
    "MultiAccountScanner",
    # Cross-account
    "AssumedRoleCredentials",
    "CredentialCache",
    "CrossAccountRoleManager",
    "get_cloudformation_template",
    "get_terraform_template",
    # Custom rules
    "CustomRule",
    "RuleCondition",
    "RuleEngine",
    "RuleImportExporter",
    "RuleOperator",
    "RulePackage",
    "RuleType",
    "RuleValidator",
    "get_example_rules",
]
