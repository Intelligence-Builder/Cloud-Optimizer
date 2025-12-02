"""
Configuration management for Cloud Optimizer.

Uses pydantic-settings for environment-based configuration with validation.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Cloud Optimizer"
    app_version: str = "2.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "cloud_optimizer"
    database_user: str = "cloud_optimizer"
    database_password: str = "securepass123"

    # JWT Settings
    jwt_secret_key: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32",
        description="Secret key for JWT signing",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    @property
    def database_url(self) -> str:
        """Get async database URL for SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Get sync database URL for Alembic migrations."""
        return (
            f"postgresql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    # Intelligence-Builder Platform
    ib_platform_url: str = Field(
        default="http://localhost:8000",
        description="Intelligence-Builder platform URL",
    )
    ib_api_key: Optional[str] = Field(
        default=None,
        description="Intelligence-Builder API key",
    )
    ib_tenant_id: str = Field(
        default="default",
        description="Tenant ID for multi-tenancy",
    )

    # AWS Configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_default_region: str = "us-east-1"
    aws_session_token: Optional[str] = None

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_reload: bool = False

    # Feature Flags
    enable_security_domain: bool = True
    enable_cost_domain: bool = False
    enable_performance_domain: bool = False
    enable_reliability_domain: bool = False
    enable_opex_domain: bool = False

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return upper

    @property
    def enabled_domains(self) -> list[str]:
        """Get list of enabled domains."""
        domains = []
        if self.enable_security_domain:
            domains.append("security")
        if self.enable_cost_domain:
            domains.append("cost")
        if self.enable_performance_domain:
            domains.append("performance")
        if self.enable_reliability_domain:
            domains.append("reliability")
        if self.enable_opex_domain:
            domains.append("opex")
        return domains


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
