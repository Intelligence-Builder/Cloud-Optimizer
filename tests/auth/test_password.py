"""Tests for password policy and hashing."""

from cloud_optimizer.auth.password import PasswordPolicy, get_password_policy


class TestPasswordPolicy:
    """Tests for PasswordPolicy class."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.policy = PasswordPolicy()

    def test_valid_password(self) -> None:
        """Test that valid passwords pass validation."""
        result = self.policy.validate("SecurePass1")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_password_too_short(self) -> None:
        """Test that short passwords fail validation."""
        result = self.policy.validate("Pass1")
        assert not result.is_valid
        assert "at least 8 characters" in result.errors[0]

    def test_password_no_uppercase(self) -> None:
        """Test that passwords without uppercase fail."""
        result = self.policy.validate("securepass1")
        assert not result.is_valid
        assert any("uppercase" in e for e in result.errors)

    def test_password_no_lowercase(self) -> None:
        """Test that passwords without lowercase fail."""
        result = self.policy.validate("SECUREPASS1")
        assert not result.is_valid
        assert any("lowercase" in e for e in result.errors)

    def test_password_no_number(self) -> None:
        """Test that passwords without numbers fail."""
        result = self.policy.validate("SecurePass")
        assert not result.is_valid
        assert any("number" in e for e in result.errors)

    def test_password_multiple_errors(self) -> None:
        """Test that all validation errors are collected."""
        result = self.policy.validate("abc")
        assert not result.is_valid
        # Should have multiple errors: short, no uppercase, no number
        assert len(result.errors) >= 3

    def test_hash_creates_different_hashes(self) -> None:
        """Test that hashing same password creates different hashes (salt)."""
        password = "SecurePass1"
        hash1 = self.policy.hash(password)
        hash2 = self.policy.hash(password)
        assert hash1 != hash2  # Different salts

    def test_verify_correct_password(self) -> None:
        """Test that verification works for correct password."""
        password = "SecurePass1"
        hashed = self.policy.hash(password)
        assert self.policy.verify(password, hashed)

    def test_verify_wrong_password(self) -> None:
        """Test that verification fails for wrong password."""
        password = "SecurePass1"
        hashed = self.policy.hash(password)
        assert not self.policy.verify("WrongPass1", hashed)

    def test_verify_case_sensitive(self) -> None:
        """Test that verification is case sensitive."""
        password = "SecurePass1"
        hashed = self.policy.hash(password)
        assert not self.policy.verify("securepass1", hashed)


class TestPasswordPolicySingleton:
    """Tests for password policy singleton."""

    def test_get_password_policy_returns_instance(self) -> None:
        """Test that get_password_policy returns an instance."""
        policy = get_password_policy()
        assert isinstance(policy, PasswordPolicy)

    def test_get_password_policy_returns_same_instance(self) -> None:
        """Test that get_password_policy returns same instance."""
        policy1 = get_password_policy()
        policy2 = get_password_policy()
        assert policy1 is policy2
