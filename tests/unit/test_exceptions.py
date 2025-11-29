"""Tests for custom exceptions module."""

import pytest

from cloud_optimizer.exceptions import (
    AWSIntegrationError,
    CloudOptimizerError,
    ConfigurationError,
    IBServiceError,
    ScanError,
    ValidationError,
)


class TestCloudOptimizerError:
    """Test base CloudOptimizerError exception."""

    def test_exception_with_message_only(self) -> None:
        """Test creating exception with just a message."""
        error = CloudOptimizerError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_exception_with_message_and_details(self) -> None:
        """Test creating exception with message and details."""
        details = {"error_code": "ERR001", "field": "test_field"}
        error = CloudOptimizerError("Test error", details=details)

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == details
        assert error.details["error_code"] == "ERR001"

    def test_exception_can_be_raised(self) -> None:
        """Test that exception can be raised and caught."""
        with pytest.raises(CloudOptimizerError) as exc_info:
            raise CloudOptimizerError("Test error")

        assert str(exc_info.value) == "Test error"

    def test_exception_with_none_details(self) -> None:
        """Test that None details converts to empty dict."""
        error = CloudOptimizerError("Test error", details=None)

        assert error.details == {}


class TestConfigurationError:
    """Test ConfigurationError exception."""

    def test_configuration_error_inherits_base(self) -> None:
        """Test that ConfigurationError inherits from CloudOptimizerError."""
        error = ConfigurationError("Config error")

        assert isinstance(error, CloudOptimizerError)
        assert isinstance(error, ConfigurationError)

    def test_configuration_error_with_details(self) -> None:
        """Test ConfigurationError with details."""
        details = {"config_key": "db_url", "reason": "invalid format"}
        error = ConfigurationError("Invalid configuration", details=details)

        assert error.message == "Invalid configuration"
        assert error.details["config_key"] == "db_url"


class TestIBServiceError:
    """Test IBServiceError exception."""

    def test_ib_service_error_inherits_base(self) -> None:
        """Test that IBServiceError inherits from CloudOptimizerError."""
        error = IBServiceError("IB service error")

        assert isinstance(error, CloudOptimizerError)
        assert isinstance(error, IBServiceError)

    def test_ib_service_error_with_connection_details(self) -> None:
        """Test IBServiceError with connection details."""
        details = {"platform_url": "http://localhost:8000", "status_code": 500}
        error = IBServiceError("Connection failed", details=details)

        assert error.message == "Connection failed"
        assert error.details["platform_url"] == "http://localhost:8000"


class TestAWSIntegrationError:
    """Test AWSIntegrationError exception."""

    def test_aws_integration_error_inherits_base(self) -> None:
        """Test that AWSIntegrationError inherits from CloudOptimizerError."""
        error = AWSIntegrationError("AWS error")

        assert isinstance(error, CloudOptimizerError)
        assert isinstance(error, AWSIntegrationError)

    def test_aws_integration_error_with_aws_details(self) -> None:
        """Test AWSIntegrationError with AWS-specific details."""
        details = {
            "service": "ec2",
            "region": "us-east-1",
            "error_code": "AccessDenied",
        }
        error = AWSIntegrationError("AWS access denied", details=details)

        assert error.message == "AWS access denied"
        assert error.details["service"] == "ec2"
        assert error.details["region"] == "us-east-1"


class TestScanError:
    """Test ScanError exception."""

    def test_scan_error_inherits_base(self) -> None:
        """Test that ScanError inherits from CloudOptimizerError."""
        error = ScanError("Scan error")

        assert isinstance(error, CloudOptimizerError)
        assert isinstance(error, ScanError)

    def test_scan_error_with_scan_details(self) -> None:
        """Test ScanError with scan-specific details."""
        details = {"scan_type": "security", "resource_count": 42, "failed_at": 10}
        error = ScanError("Scan failed", details=details)

        assert error.message == "Scan failed"
        assert error.details["scan_type"] == "security"
        assert error.details["resource_count"] == 42


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_inherits_base(self) -> None:
        """Test that ValidationError inherits from CloudOptimizerError."""
        error = ValidationError("Validation error")

        assert isinstance(error, CloudOptimizerError)
        assert isinstance(error, ValidationError)

    def test_validation_error_with_validation_details(self) -> None:
        """Test ValidationError with validation-specific details."""
        details = {"field": "email", "value": "invalid", "constraint": "email format"}
        error = ValidationError("Invalid email", details=details)

        assert error.message == "Invalid email"
        assert error.details["field"] == "email"
        assert error.details["constraint"] == "email format"


class TestExceptionHierarchy:
    """Test exception hierarchy relationships."""

    def test_all_custom_exceptions_inherit_base(self) -> None:
        """Test that all custom exceptions inherit from CloudOptimizerError."""
        exceptions = [
            ConfigurationError("test"),
            IBServiceError("test"),
            AWSIntegrationError("test"),
            ScanError("test"),
            ValidationError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, CloudOptimizerError)
            assert isinstance(exc, Exception)

    def test_exceptions_can_be_caught_as_base(self) -> None:
        """Test that specific exceptions can be caught as base exception."""
        with pytest.raises(CloudOptimizerError):
            raise ConfigurationError("test")

        with pytest.raises(CloudOptimizerError):
            raise IBServiceError("test")

        with pytest.raises(CloudOptimizerError):
            raise ScanError("test")

    def test_exceptions_maintain_their_type(self) -> None:
        """Test that exceptions maintain their specific type when caught."""
        try:
            raise ConfigurationError("config error")
        except CloudOptimizerError as e:
            assert type(e).__name__ == "ConfigurationError"
            assert isinstance(e, ConfigurationError)
