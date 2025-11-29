"""AWS integrations for Cloud Optimizer."""

from cloud_optimizer.integrations.aws.base import BaseAWSScanner
from cloud_optimizer.integrations.aws.encryption import EncryptionScanner
from cloud_optimizer.integrations.aws.iam import IAMScanner
from cloud_optimizer.integrations.aws.security_groups import SecurityGroupScanner

__all__ = [
    "BaseAWSScanner",
    "SecurityGroupScanner",
    "IAMScanner",
    "EncryptionScanner",
]
