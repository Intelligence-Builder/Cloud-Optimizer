"""Scanner registry for discovering and running scanners."""

import logging
from typing import Dict, List, Optional, Type

import boto3

from cloud_optimizer.scanners.base import BaseScanner
from cloud_optimizer.scanners.ec2 import EC2Scanner
from cloud_optimizer.scanners.iam import IAMScanner
from cloud_optimizer.scanners.lambda_scanner import LambdaScanner
from cloud_optimizer.scanners.rds import RDSScanner
from cloud_optimizer.scanners.s3 import S3Scanner

logger = logging.getLogger(__name__)


class ScannerRegistry:
    """Registry for discovering and managing security scanners."""

    _scanners: Dict[str, Type[BaseScanner]] = {
        "S3": S3Scanner,
        "IAM": IAMScanner,
        "EC2": EC2Scanner,
        "RDS": RDSScanner,
        "Lambda": LambdaScanner,
    }

    @classmethod
    def get_scanner(
        cls, service: str, session: boto3.Session, regions: Optional[List[str]] = None
    ) -> BaseScanner:
        """
        Get scanner instance for a service.

        Args:
            service: Service name (e.g., "S3", "EC2", "IAM")
            session: Boto3 session with AWS credentials
            regions: List of AWS regions to scan (defaults to ["us-east-1"])

        Returns:
            Scanner instance for the service

        Raises:
            ValueError: If service is not registered
        """
        scanner_class = cls._scanners.get(service)
        if not scanner_class:
            raise ValueError(
                f"Unknown scanner: {service}. Available scanners: {cls.get_all_services()}"
            )

        logger.debug(f"Creating {service} scanner for regions: {regions}")
        return scanner_class(session, regions)

    @classmethod
    def get_all_services(cls) -> List[str]:
        """
        Get list of all registered service names.

        Returns:
            List of service names
        """
        return list(cls._scanners.keys())

    @classmethod
    def get_all_scanners(
        cls, session: boto3.Session, regions: Optional[List[str]] = None
    ) -> List[BaseScanner]:
        """
        Get all registered scanner instances.

        Args:
            session: Boto3 session with AWS credentials
            regions: List of AWS regions to scan (defaults to ["us-east-1"])

        Returns:
            List of all scanner instances
        """
        scanners = []
        for service in cls.get_all_services():
            try:
                scanner = cls.get_scanner(service, session, regions)
                scanners.append(scanner)
            except Exception as e:
                logger.error(f"Error creating scanner for {service}: {e}")

        return scanners

    @classmethod
    def register_scanner(cls, service: str, scanner_class: Type[BaseScanner]) -> None:
        """
        Register a custom scanner.

        Args:
            service: Service name
            scanner_class: Scanner class that extends BaseScanner

        Raises:
            TypeError: If scanner_class is not a subclass of BaseScanner
        """
        if not issubclass(scanner_class, BaseScanner):
            raise TypeError(f"{scanner_class} must be a subclass of BaseScanner")

        cls._scanners[service] = scanner_class
        logger.info(f"Registered scanner for service: {service}")

    @classmethod
    def unregister_scanner(cls, service: str) -> None:
        """
        Unregister a scanner.

        Args:
            service: Service name to unregister
        """
        if service in cls._scanners:
            del cls._scanners[service]
            logger.info(f"Unregistered scanner for service: {service}")

    @classmethod
    def get_scanner_info(cls, service: str) -> Dict[str, any]:
        """
        Get information about a registered scanner.

        Args:
            service: Service name

        Returns:
            Dictionary with scanner information

        Raises:
            ValueError: If service is not registered
        """
        scanner_class = cls._scanners.get(service)
        if not scanner_class:
            raise ValueError(f"Unknown scanner: {service}")

        # Create a temporary instance to get rule information
        import boto3

        temp_session = boto3.Session()
        temp_scanner = scanner_class(temp_session, ["us-east-1"])

        return {
            "service": service,
            "class_name": scanner_class.__name__,
            "module": scanner_class.__module__,
            "rule_count": len(temp_scanner.rules),
            "rules": [
                {
                    "rule_id": rule.rule_id,
                    "title": rule.title,
                    "severity": rule.severity,
                    "compliance_frameworks": rule.compliance_frameworks,
                }
                for rule in temp_scanner.rules.values()
            ],
        }

    @classmethod
    def get_all_scanner_info(cls) -> Dict[str, Dict[str, any]]:
        """
        Get information about all registered scanners.

        Returns:
            Dictionary mapping service names to scanner information
        """
        info = {}
        for service in cls.get_all_services():
            try:
                info[service] = cls.get_scanner_info(service)
            except Exception as e:
                logger.error(f"Error getting info for {service}: {e}")
                info[service] = {"error": str(e)}

        return info
