"""AWS integrations for Cloud Optimizer."""

from cloud_optimizer.integrations.aws.base import BaseAWSScanner
from cloud_optimizer.integrations.aws.cost import CostExplorerScanner
from cloud_optimizer.integrations.aws.encryption import EncryptionScanner
from cloud_optimizer.integrations.aws.iam import IAMScanner
from cloud_optimizer.integrations.aws.operations import SystemsManagerScanner
from cloud_optimizer.integrations.aws.performance import CloudWatchScanner
from cloud_optimizer.integrations.aws.reliability import ReliabilityScanner
from cloud_optimizer.integrations.aws.s3_security import S3SecurityScanner
from cloud_optimizer.integrations.aws.security_groups import SecurityGroupScanner

__all__ = [
    "BaseAWSScanner",
    "SecurityGroupScanner",
    "IAMScanner",
    "EncryptionScanner",
    "CostExplorerScanner",
    "CloudWatchScanner",
    "ReliabilityScanner",
    "SystemsManagerScanner",
    "S3SecurityScanner",
]
