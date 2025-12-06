"""
PII (Personally Identifiable Information) redaction for logs.

Provides automatic redaction of sensitive data including:
- Email addresses
- Phone numbers
- AWS credentials
- Credit card numbers
- Social Security Numbers
- IP addresses (optional)
- Custom patterns
"""

import re
from dataclasses import dataclass, field
from typing import Any, Pattern

# Pre-compiled regex patterns for PII detection
PII_PATTERNS: dict[str, Pattern[str]] = {
    # Email addresses
    "email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        re.IGNORECASE,
    ),
    # Phone numbers (various formats)
    "phone": re.compile(
        r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"
    ),
    # Credit card numbers (basic pattern)
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    # Social Security Numbers
    "ssn": re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
    # AWS Access Key ID
    "aws_access_key": re.compile(r"\b(?:AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}\b"),
    # AWS Secret Access Key (40 char base64-ish)
    "aws_secret_key": re.compile(
        r"\b[A-Za-z0-9/+=]{40}\b(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])"
    ),
    # JWT tokens
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    # Generic API keys (common patterns)
    "api_key": re.compile(
        r"\b(?:api[_-]?key|apikey|api[_-]?token)[\"'\s:=]+[A-Za-z0-9_-]{20,}\b",
        re.IGNORECASE,
    ),
    # Password fields
    "password": re.compile(
        r"\b(?:password|passwd|pwd|secret)[\"'\s:=]+[^\s\"']{8,}\b",
        re.IGNORECASE,
    ),
    # Authorization headers
    "auth_header": re.compile(
        r"\b(?:Bearer|Basic)\s+[A-Za-z0-9_-]+\.?[A-Za-z0-9_-]*\.?[A-Za-z0-9_-]*\b"
    ),
}

# Fields that should always be redacted (case-insensitive)
SENSITIVE_FIELD_NAMES: set[str] = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "secret_key",
    "private_key",
    "auth",
    "authorization",
    "credential",
    "credentials",
    "ssn",
    "social_security",
    "credit_card",
    "card_number",
    "cvv",
    "cvc",
    "pin",
    "session_id",
    "session_token",
    "refresh_token",
    "access_token",
    "id_token",
    "encryption_key",
    "aws_secret_access_key",
    "aws_session_token",
}

# Default redaction placeholder
DEFAULT_REDACTION = "[REDACTED]"


@dataclass
class PIIFilter:
    """
    Configurable PII filter for log redaction.

    Attributes:
        enabled: Whether PII filtering is enabled
        patterns: Dictionary of pattern names to compiled regex
        sensitive_fields: Set of field names to always redact
        redaction_text: Text to replace PII with
        redact_ip_addresses: Whether to redact IP addresses
        custom_patterns: Additional custom patterns
    """

    enabled: bool = True
    patterns: dict[str, Pattern[str]] = field(
        default_factory=lambda: PII_PATTERNS.copy()
    )
    sensitive_fields: set[str] = field(
        default_factory=lambda: SENSITIVE_FIELD_NAMES.copy()
    )
    redaction_text: str = DEFAULT_REDACTION
    redact_ip_addresses: bool = False
    custom_patterns: dict[str, Pattern[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize additional patterns after dataclass init."""
        if self.redact_ip_addresses:
            self.patterns["ipv4"] = re.compile(
                r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
                r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
            )
            self.patterns["ipv6"] = re.compile(
                r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
            )

        # Merge custom patterns
        if self.custom_patterns:
            self.patterns.update(self.custom_patterns)

    def is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field name is in the sensitive list."""
        return field_name.lower() in self.sensitive_fields

    def redact_string(self, value: str) -> str:
        """
        Redact PII from a string value.

        Args:
            value: String to redact

        Returns:
            String with PII replaced by redaction text
        """
        if not self.enabled or not value:
            return value

        result = value
        for pattern in self.patterns.values():
            result = pattern.sub(self.redaction_text, result)

        return result

    def redact_value(self, key: str, value: Any) -> Any:
        """
        Redact a value based on its key and content.

        Args:
            key: Field name
            value: Value to potentially redact

        Returns:
            Redacted value if sensitive, original otherwise
        """
        if not self.enabled:
            return value

        # Check if field name is sensitive
        if self.is_sensitive_field(key):
            return self.redaction_text

        # Redact string content
        if isinstance(value, str):
            return self.redact_string(value)

        return value

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively redact PII from a dictionary.

        Args:
            data: Dictionary to redact

        Returns:
            New dictionary with PII redacted
        """
        if not self.enabled:
            return data

        result: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self.redact_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.redact_dict(item) if isinstance(item, dict)
                    else self.redact_value(key, item)
                    for item in value
                ]
            else:
                result[key] = self.redact_value(key, value)

        return result


# Global filter instance
_default_filter: PIIFilter = PIIFilter()


def get_pii_filter() -> PIIFilter:
    """Get the default PII filter instance."""
    return _default_filter


def set_pii_filter(filter_instance: PIIFilter) -> None:
    """Set a custom PII filter as the default."""
    global _default_filter
    _default_filter = filter_instance


def redact_pii(value: Any, field_name: str = "") -> Any:
    """
    Redact PII from a value using the default filter.

    Args:
        value: Value to redact (string or dict)
        field_name: Optional field name for context

    Returns:
        Redacted value
    """
    pii_filter = get_pii_filter()

    if isinstance(value, dict):
        return pii_filter.redact_dict(value)
    elif isinstance(value, str):
        if field_name and pii_filter.is_sensitive_field(field_name):
            return pii_filter.redaction_text
        return pii_filter.redact_string(value)

    return value


class PIIRedactionProcessor:
    """
    Structlog processor for automatic PII redaction.

    This processor should be added to the structlog processor chain
    to automatically redact sensitive information from all log events.
    """

    def __init__(self, pii_filter: PIIFilter | None = None):
        self.pii_filter = pii_filter or get_pii_filter()

    def __call__(
        self,
        logger: Any,
        method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a log event and redact PII."""
        if not self.pii_filter.enabled:
            return event_dict

        return self.pii_filter.redact_dict(event_dict)
