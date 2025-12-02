"""
Password handling for Cloud Optimizer.

Implements password policy validation and secure bcrypt hashing.
"""

import re
from dataclasses import dataclass

import bcrypt


@dataclass
class PasswordValidationResult:
    """Result of password validation."""

    is_valid: bool
    errors: list[str]


class PasswordPolicy:
    """
    Password policy enforcement.

    Requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    """

    MIN_LENGTH = 8
    BCRYPT_ROUNDS = 12  # Good balance of security and performance

    def validate(self, password: str) -> PasswordValidationResult:
        """
        Validate password against policy.

        Args:
            password: Plain text password to validate.

        Returns:
            PasswordValidationResult with validation status and any errors.
        """
        errors: list[str] = []

        if len(password) < self.MIN_LENGTH:
            errors.append(f"Password must be at least {self.MIN_LENGTH} characters")

        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least 1 uppercase letter")

        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least 1 lowercase letter")

        if not re.search(r"\d", password):
            errors.append("Password must contain at least 1 number")

        return PasswordValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
        )

    def hash(self, password: str) -> str:
        """
        Hash password using bcrypt.

        Args:
            password: Plain text password.

        Returns:
            Bcrypt hash of password.
        """
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    def verify(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash.

        Args:
            password: Plain text password to verify.
            password_hash: Bcrypt hash to verify against.

        Returns:
            True if password matches hash, False otherwise.
        """
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)


# Singleton instance
_password_policy: PasswordPolicy | None = None


def get_password_policy() -> PasswordPolicy:
    """Get or create password policy instance."""
    global _password_policy
    if _password_policy is None:
        _password_policy = PasswordPolicy()
    return _password_policy
