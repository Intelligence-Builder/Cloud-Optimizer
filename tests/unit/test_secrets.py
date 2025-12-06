"""Unit tests for AWS Secrets Manager integration."""

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from cloud_optimizer.secrets import (
    CachedSecret,
    SecretsManager,
    SecretsManagerConfig,
    get_secret,
    get_secrets_manager,
)


class TestCachedSecret:
    """Tests for CachedSecret dataclass."""

    def test_cached_secret_not_expired(self) -> None:
        """Test that fresh cached secret is not expired."""
        secret = CachedSecret(
            value="test-value",
            fetched_at=time.time(),
            ttl_seconds=3600,
        )
        assert not secret.is_expired

    def test_cached_secret_expired(self) -> None:
        """Test that old cached secret is expired."""
        secret = CachedSecret(
            value="test-value",
            fetched_at=time.time() - 7200,  # 2 hours ago
            ttl_seconds=3600,  # 1 hour TTL
        )
        assert secret.is_expired


class TestSecretsManagerConfig:
    """Tests for SecretsManagerConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = SecretsManagerConfig()
        assert config.enabled is False
        assert config.region == "us-east-1"
        assert config.cache_ttl_seconds == 3600

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = SecretsManagerConfig(
            enabled=True,
            region="eu-west-1",
            cache_ttl_seconds=1800,
            secret_mappings={"MY_SECRET": "my-app/secret"},
        )
        assert config.enabled is True
        assert config.region == "eu-west-1"
        assert config.cache_ttl_seconds == 1800
        assert config.secret_mappings["MY_SECRET"] == "my-app/secret"


class TestSecretsManager:
    """Tests for SecretsManager class."""

    def test_disabled_returns_env_var(self) -> None:
        """Test that disabled Secrets Manager returns environment variable."""
        config = SecretsManagerConfig(enabled=False)
        manager = SecretsManager(config)

        with patch.dict(os.environ, {"TEST_SECRET": "env-value"}):
            result = manager.get_secret("TEST_SECRET")
            assert result == "env-value"

    def test_disabled_returns_default(self) -> None:
        """Test that disabled Secrets Manager returns default value."""
        config = SecretsManagerConfig(enabled=False)
        manager = SecretsManager(config)

        with patch.dict(os.environ, {}, clear=True):
            result = manager.get_secret("NONEXISTENT", default="default-value")
            assert result == "default-value"

    def test_cache_hit(self) -> None:
        """Test that cached secrets are returned without API call."""
        config = SecretsManagerConfig(enabled=True)
        manager = SecretsManager(config)

        # Pre-populate cache (key is just env_var_name when secret_key is None)
        manager._cache["TEST_SECRET"] = CachedSecret(
            value="cached-value",
            fetched_at=time.time(),
            ttl_seconds=3600,
        )

        # Should return cached value without calling AWS
        result = manager.get_secret("TEST_SECRET")
        assert result == "cached-value"

    def test_cache_miss_fallback_to_env(self) -> None:
        """Test fallback to environment variable on cache miss."""
        config = SecretsManagerConfig(
            enabled=True,
            secret_mappings={"TEST_SECRET": "test/secret"},
        )
        manager = SecretsManager(config)

        # Mock boto3 client to raise exception
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = Exception("API Error")
        manager._client = mock_client

        with patch.dict(os.environ, {"TEST_SECRET": "env-fallback"}):
            result = manager.get_secret("TEST_SECRET")
            assert result == "env-fallback"

    def test_clear_cache(self) -> None:
        """Test cache clearing."""
        config = SecretsManagerConfig(enabled=False)
        manager = SecretsManager(config)

        manager._cache["key1"] = CachedSecret("value1", time.time())
        manager._cache["key2"] = CachedSecret("value2", time.time())

        manager.clear_cache()
        assert len(manager._cache) == 0

    def test_fetch_json_secret(self) -> None:
        """Test fetching a specific key from JSON secret."""
        config = SecretsManagerConfig(
            enabled=True,
            secret_mappings={"DB_PASSWORD": "db/credentials"},
        )
        manager = SecretsManager(config)

        # Mock the boto3 client
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps({"password": "secret-pass", "username": "admin"})
        }
        manager._client = mock_client

        result = manager.get_secret("DB_PASSWORD", secret_key="password")
        assert result == "secret-pass"

    def test_fetch_plain_text_secret(self) -> None:
        """Test fetching plain text secret."""
        config = SecretsManagerConfig(
            enabled=True,
            secret_mappings={"API_KEY": "api/key"},
        )
        manager = SecretsManager(config)

        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretString": "plain-text-api-key"
        }
        manager._client = mock_client

        result = manager.get_secret("API_KEY")
        assert result == "plain-text-api-key"

    def test_secret_not_found(self) -> None:
        """Test handling of ResourceNotFoundException."""
        config = SecretsManagerConfig(
            enabled=True,
            secret_mappings={"MISSING": "missing/secret"},
        )
        manager = SecretsManager(config)

        mock_client = MagicMock()
        mock_exceptions = MagicMock()
        mock_exceptions.ResourceNotFoundException = Exception
        mock_client.exceptions = mock_exceptions
        mock_client.get_secret_value.side_effect = mock_exceptions.ResourceNotFoundException()
        manager._client = mock_client

        with patch.dict(os.environ, {"MISSING": "env-fallback"}):
            result = manager.get_secret("MISSING")
            assert result == "env-fallback"


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_secrets_manager_singleton(self) -> None:
        """Test that get_secrets_manager returns same instance."""
        import cloud_optimizer.secrets as secrets_module

        # Reset the global instance
        secrets_module._secrets_manager = None

        manager1 = get_secrets_manager()
        manager2 = get_secrets_manager()
        assert manager1 is manager2

    def test_get_secret_function(self) -> None:
        """Test the convenience get_secret function."""
        import cloud_optimizer.secrets as secrets_module

        # Reset and create a disabled manager
        secrets_module._secrets_manager = None

        with patch.dict(os.environ, {"CONVENIENCE_TEST": "convenience-value"}):
            result = get_secret("CONVENIENCE_TEST")
            assert result == "convenience-value"


class TestSecretsManagerLoadConfigFromEnv:
    """Tests for loading configuration from environment."""

    def test_load_config_enabled(self) -> None:
        """Test loading config with Secrets Manager enabled."""
        env_vars = {
            "SECRETS_MANAGER_ENABLED": "true",
            "AWS_DEFAULT_REGION": "eu-central-1",
            "SECRETS_MANAGER_CACHE_TTL": "7200",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            manager = SecretsManager()
            assert manager.config.enabled is True
            assert manager.config.region == "eu-central-1"
            assert manager.config.cache_ttl_seconds == 7200

    def test_load_config_disabled_by_default(self) -> None:
        """Test that Secrets Manager is disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            manager = SecretsManager()
            assert manager.config.enabled is False
