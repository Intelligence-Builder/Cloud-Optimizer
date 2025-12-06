"""
AWS Secrets Manager integration for Cloud Optimizer.

Provides secure secret fetching with caching and fallback to environment variables.
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CachedSecret:
    """Cached secret with expiration."""

    value: str
    fetched_at: float
    ttl_seconds: int = 3600  # 1 hour default

    @property
    def is_expired(self) -> bool:
        """Check if the cached secret has expired."""
        return time.time() - self.fetched_at > self.ttl_seconds


@dataclass
class SecretsManagerConfig:
    """Configuration for AWS Secrets Manager."""

    enabled: bool = False
    region: str = "us-east-1"
    cache_ttl_seconds: int = 3600  # 1 hour
    # Secret name mappings (env var name -> Secrets Manager secret name)
    secret_mappings: dict[str, str] = field(default_factory=dict)


class SecretsManager:
    """
    AWS Secrets Manager client with caching and fallback.

    Features:
    - Fetches secrets from AWS Secrets Manager
    - Caches secrets to reduce API calls
    - Falls back to environment variables when Secrets Manager is unavailable
    - Supports JSON secrets with multiple key-value pairs
    """

    def __init__(self, config: SecretsManagerConfig | None = None) -> None:
        """
        Initialize the secrets manager.

        Args:
            config: Optional configuration. If not provided, uses environment variables.
        """
        self.config = config or self._load_config_from_env()
        self._cache: dict[str, CachedSecret] = {}
        self._client: Any = None

    def _load_config_from_env(self) -> SecretsManagerConfig:
        """Load configuration from environment variables."""
        enabled = os.getenv("SECRETS_MANAGER_ENABLED", "false").lower() == "true"
        region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        cache_ttl = int(os.getenv("SECRETS_MANAGER_CACHE_TTL", "3600"))

        # Default secret mappings for Cloud Optimizer
        mappings = {
            "DATABASE_PASSWORD": os.getenv(
                "SECRETS_MANAGER_DB_SECRET", "cloud-optimizer/database"
            ),
            "JWT_SECRET_KEY": os.getenv(
                "SECRETS_MANAGER_JWT_SECRET", "cloud-optimizer/jwt"
            ),
            "ENCRYPTION_KEY": os.getenv(
                "SECRETS_MANAGER_ENCRYPTION_SECRET", "cloud-optimizer/encryption"
            ),
            "IB_API_KEY": os.getenv(
                "SECRETS_MANAGER_IB_SECRET", "cloud-optimizer/intelligence-builder"
            ),
            "ANTHROPIC_API_KEY": os.getenv(
                "SECRETS_MANAGER_ANTHROPIC_SECRET", "cloud-optimizer/anthropic"
            ),
        }

        return SecretsManagerConfig(
            enabled=enabled,
            region=region,
            cache_ttl_seconds=cache_ttl,
            secret_mappings=mappings,
        )

    @property
    def client(self) -> Any:
        """Get or create the Secrets Manager client."""
        if self._client is None and self.config.enabled:
            try:
                import boto3

                self._client = boto3.client(
                    "secretsmanager",
                    region_name=self.config.region,
                )
                logger.info(
                    "secrets_manager_client_initialized",
                    region=self.config.region,
                )
            except Exception as e:
                logger.warning(
                    "secrets_manager_client_failed",
                    error=str(e),
                    message="Falling back to environment variables",
                )
                self.config.enabled = False
        return self._client

    def get_secret(
        self,
        env_var_name: str,
        secret_key: str | None = None,
        default: str | None = None,
    ) -> str | None:
        """
        Get a secret value with fallback to environment variable.

        Args:
            env_var_name: Name of the environment variable to use as fallback.
            secret_key: Key within a JSON secret (for multi-value secrets).
            default: Default value if secret not found anywhere.

        Returns:
            The secret value or default.
        """
        # If Secrets Manager is disabled, use environment variable
        if not self.config.enabled:
            return os.getenv(env_var_name, default)

        # Check cache first
        cache_key = f"{env_var_name}:{secret_key}" if secret_key else env_var_name
        cached = self._cache.get(cache_key)
        if cached and not cached.is_expired:
            logger.debug("secrets_manager_cache_hit", key=cache_key)
            return cached.value

        # Try to fetch from Secrets Manager
        secret_name = self.config.secret_mappings.get(env_var_name)
        if secret_name:
            try:
                value = self._fetch_from_secrets_manager(secret_name, secret_key)
                if value is not None:
                    # Cache the value
                    self._cache[cache_key] = CachedSecret(
                        value=value,
                        fetched_at=time.time(),
                        ttl_seconds=self.config.cache_ttl_seconds,
                    )
                    logger.info(
                        "secrets_manager_fetched",
                        secret_name=secret_name,
                        key=secret_key,
                    )
                    return value
            except Exception as e:
                logger.warning(
                    "secrets_manager_fetch_failed",
                    secret_name=secret_name,
                    error=str(e),
                    message="Falling back to environment variable",
                )

        # Fallback to environment variable
        env_value = os.getenv(env_var_name, default)
        if env_value:
            logger.debug(
                "secrets_manager_fallback_env",
                env_var=env_var_name,
            )
        return env_value

    def _fetch_from_secrets_manager(
        self,
        secret_name: str,
        secret_key: str | None = None,
    ) -> str | None:
        """
        Fetch a secret from AWS Secrets Manager.

        Args:
            secret_name: Name of the secret in Secrets Manager.
            secret_key: Optional key for JSON secrets.

        Returns:
            The secret value or None if not found.
        """
        if not self.client:
            return None

        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_string = response.get("SecretString")

            if not secret_string:
                return None

            # Try to parse as JSON
            if secret_key:
                try:
                    secret_dict = json.loads(secret_string)
                    return secret_dict.get(secret_key)
                except json.JSONDecodeError:
                    # Not JSON, return as-is if no key requested
                    logger.warning(
                        "secrets_manager_not_json",
                        secret_name=secret_name,
                        message="Expected JSON but got plain text",
                    )
                    return None

            # Return plain text secret or full JSON string
            return secret_string

        except self.client.exceptions.ResourceNotFoundException:
            logger.warning(
                "secrets_manager_not_found",
                secret_name=secret_name,
            )
            return None
        except self.client.exceptions.AccessDeniedException:
            logger.error(
                "secrets_manager_access_denied",
                secret_name=secret_name,
            )
            return None

    def clear_cache(self) -> None:
        """Clear all cached secrets."""
        self._cache.clear()
        logger.info("secrets_manager_cache_cleared")

    def refresh_secret(self, env_var_name: str, secret_key: str | None = None) -> None:
        """
        Force refresh a specific secret from Secrets Manager.

        Args:
            env_var_name: Environment variable name for the secret.
            secret_key: Optional key for JSON secrets.
        """
        cache_key = f"{env_var_name}:{secret_key}" if secret_key else env_var_name
        if cache_key in self._cache:
            del self._cache[cache_key]
        # Re-fetch the secret
        self.get_secret(env_var_name, secret_key)


# Global secrets manager instance
_secrets_manager: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def get_secret(
    env_var_name: str,
    secret_key: str | None = None,
    default: str | None = None,
) -> str | None:
    """
    Convenience function to get a secret.

    Args:
        env_var_name: Name of the environment variable.
        secret_key: Optional key for JSON secrets.
        default: Default value if not found.

    Returns:
        The secret value or default.
    """
    return get_secrets_manager().get_secret(env_var_name, secret_key, default)
