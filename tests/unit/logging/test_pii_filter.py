"""Tests for PII redaction functionality."""

import pytest

from cloud_optimizer.logging.pii_filter import (
    PIIFilter,
    PIIRedactionProcessor,
    redact_pii,
)


class TestPIIFilter:
    """Tests for PIIFilter class."""

    def test_email_redaction(self) -> None:
        """Test that email addresses are redacted."""
        pii_filter = PIIFilter()
        result = pii_filter.redact_string("Contact user@example.com for help")
        assert "[REDACTED]" in result
        assert "user@example.com" not in result

    def test_phone_number_redaction(self) -> None:
        """Test that phone numbers are redacted."""
        pii_filter = PIIFilter()
        test_cases = [
            "Call 555-123-4567",
            "Phone: (555) 123-4567",
            "Contact +1-555-123-4567",
            "Number: 5551234567",
        ]
        for test in test_cases:
            result = pii_filter.redact_string(test)
            assert "[REDACTED]" in result

    def test_credit_card_redaction(self) -> None:
        """Test that credit card numbers are redacted."""
        pii_filter = PIIFilter()
        test_cases = [
            "Card: 4111-1111-1111-1111",
            "CC: 4111 1111 1111 1111",
            "Number 4111111111111111",
        ]
        for test in test_cases:
            result = pii_filter.redact_string(test)
            assert "[REDACTED]" in result

    def test_ssn_redaction(self) -> None:
        """Test that SSN numbers are redacted."""
        pii_filter = PIIFilter()
        test_cases = [
            "SSN: 123-45-6789",
            "Social: 123 45 6789",
        ]
        for test in test_cases:
            result = pii_filter.redact_string(test)
            assert "[REDACTED]" in result

    def test_aws_access_key_redaction(self) -> None:
        """Test that AWS access keys are redacted."""
        pii_filter = PIIFilter()
        result = pii_filter.redact_string("Key: AKIAIOSFODNN7EXAMPLE")
        assert "[REDACTED]" in result
        assert "AKIAIOSFODNN7EXAMPLE" not in result

    def test_jwt_token_redaction(self) -> None:
        """Test that JWT tokens are redacted."""
        pii_filter = PIIFilter()
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = pii_filter.redact_string(f"Token: {jwt}")
        assert "[REDACTED]" in result

    def test_sensitive_field_detection(self) -> None:
        """Test that sensitive field names are detected."""
        pii_filter = PIIFilter()
        sensitive_fields = [
            "password",
            "api_key",
            "secret",
            "token",
            "access_token",
            "credentials",
        ]
        for field in sensitive_fields:
            assert pii_filter.is_sensitive_field(field)
            assert pii_filter.is_sensitive_field(field.upper())

    def test_non_sensitive_field(self) -> None:
        """Test that non-sensitive fields are not flagged."""
        pii_filter = PIIFilter()
        non_sensitive = ["name", "email_subject", "description", "count"]
        for field in non_sensitive:
            assert not pii_filter.is_sensitive_field(field)

    def test_redact_value_for_sensitive_field(self) -> None:
        """Test value redaction for sensitive fields."""
        pii_filter = PIIFilter()
        result = pii_filter.redact_value("password", "my_secret_password")
        assert result == "[REDACTED]"

    def test_redact_value_for_non_sensitive_field(self) -> None:
        """Test that non-sensitive field values are not redacted."""
        pii_filter = PIIFilter()
        result = pii_filter.redact_value("name", "John Doe")
        assert result == "John Doe"

    def test_redact_dict_nested(self) -> None:
        """Test recursive dictionary redaction."""
        pii_filter = PIIFilter()
        data = {
            "user": {
                "name": "John",
                "email": "john@example.com",
                "password": "secret123",
            },
            "message": "Contact user@test.com",
        }
        result = pii_filter.redact_dict(data)

        assert result["user"]["name"] == "John"
        assert result["user"]["password"] == "[REDACTED]"
        assert "john@example.com" not in str(result)
        assert "user@test.com" not in str(result)

    def test_redact_dict_with_list(self) -> None:
        """Test dictionary redaction with list values."""
        pii_filter = PIIFilter()
        data = {
            "users": [
                {"email": "a@test.com"},
                {"email": "b@test.com"},
            ]
        }
        result = pii_filter.redact_dict(data)

        for user in result["users"]:
            assert "test.com" not in str(user)

    def test_disabled_filter(self) -> None:
        """Test that disabled filter returns original values."""
        pii_filter = PIIFilter(enabled=False)
        original = "Email: user@example.com"
        result = pii_filter.redact_string(original)
        assert result == original

    def test_custom_redaction_text(self) -> None:
        """Test custom redaction placeholder."""
        pii_filter = PIIFilter(redaction_text="***HIDDEN***")
        result = pii_filter.redact_string("Email: user@example.com")
        assert "***HIDDEN***" in result

    def test_ip_address_redaction_when_enabled(self) -> None:
        """Test IP address redaction when enabled."""
        pii_filter = PIIFilter(redact_ip_addresses=True)
        result = pii_filter.redact_string("Client IP: 192.168.1.1")
        assert "[REDACTED]" in result
        assert "192.168.1.1" not in result

    def test_ip_address_not_redacted_by_default(self) -> None:
        """Test IP addresses are not redacted by default."""
        pii_filter = PIIFilter(redact_ip_addresses=False)
        result = pii_filter.redact_string("Client IP: 192.168.1.1")
        assert "192.168.1.1" in result


class TestPIIRedactionProcessor:
    """Tests for structlog PII redaction processor."""

    def test_processor_redacts_event_dict(self) -> None:
        """Test processor redacts event dictionary."""
        processor = PIIRedactionProcessor()
        event_dict = {
            "event": "login",
            "email": "user@example.com",
            "password": "secret",
        }
        result = processor(None, "info", event_dict)

        assert result["event"] == "login"
        assert result["password"] == "[REDACTED]"
        assert "user@example.com" not in str(result)

    def test_processor_with_custom_filter(self) -> None:
        """Test processor with custom PII filter."""
        custom_filter = PIIFilter(redaction_text="[REMOVED]")
        processor = PIIRedactionProcessor(pii_filter=custom_filter)

        event_dict = {"password": "secret123"}
        result = processor(None, "info", event_dict)

        assert result["password"] == "[REMOVED]"


class TestRedactPIIFunction:
    """Tests for the redact_pii convenience function."""

    def test_redact_string(self) -> None:
        """Test redacting a string."""
        result = redact_pii("Email: user@example.com")
        assert "[REDACTED]" in result

    def test_redact_dict(self) -> None:
        """Test redacting a dictionary."""
        data = {"email": "user@example.com", "password": "secret"}
        result = redact_pii(data)

        assert result["password"] == "[REDACTED]"
        assert "user@example.com" not in str(result)

    def test_redact_with_field_name(self) -> None:
        """Test redacting with a sensitive field name."""
        result = redact_pii("any_value", field_name="password")
        assert result == "[REDACTED]"

    def test_redact_non_pii_string(self) -> None:
        """Test that non-PII strings are not modified."""
        original = "This is a normal log message"
        result = redact_pii(original)
        assert result == original
