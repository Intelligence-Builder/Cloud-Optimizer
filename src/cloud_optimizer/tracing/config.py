"""Configuration for AWS X-Ray tracing.

Issue #167: Distributed tracing with X-Ray.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SamplingRule:
    """X-Ray sampling rule configuration."""

    name: str
    priority: int = 1000
    fixed_rate: float = 0.05  # 5% default sampling
    reservoir_size: int = 1  # Minimum traces per second
    service_name: str = "*"
    service_type: str = "*"
    host: str = "*"
    http_method: str = "*"
    url_path: str = "*"


@dataclass
class TracingConfig:
    """Configuration for X-Ray tracing service."""

    enabled: bool = True
    service_name: str = "cloud-optimizer"
    daemon_address: str = "127.0.0.1:2000"  # X-Ray daemon address
    context_missing: str = "LOG_ERROR"  # LOG_ERROR, RUNTIME_ERROR, IGNORE_ERROR
    plugins: list[str] = field(default_factory=lambda: ["EC2Plugin", "ECSPlugin"])
    sampling_rules: list[SamplingRule] = field(default_factory=list)
    stream_sql: bool = True  # Capture SQL queries
    capture_request_body: bool = False  # Don't capture request bodies (PII)
    capture_response_body: bool = False  # Don't capture response bodies (PII)

    # Paths to exclude from tracing
    excluded_paths: list[str] = field(
        default_factory=lambda: [
            "/health",
            "/healthz",
            "/ready",
            "/readyz",
            "/live",
            "/livez",
            "/metrics",
            "/favicon.ico",
        ]
    )

    # Annotations to add to all segments
    default_annotations: dict[str, str] = field(default_factory=dict)

    # Metadata to add to all segments
    default_metadata: dict[str, dict] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set default sampling rules if none provided."""
        if not self.sampling_rules:
            self.sampling_rules = [
                # High priority for errors - always trace
                SamplingRule(
                    name="error-traces",
                    priority=1,
                    fixed_rate=1.0,  # 100% of errors
                    reservoir_size=10,
                    url_path="*",
                ),
                # API endpoints - moderate sampling
                SamplingRule(
                    name="api-traces",
                    priority=100,
                    fixed_rate=0.10,  # 10% of API calls
                    reservoir_size=5,
                    url_path="/api/*",
                ),
                # Health checks - minimal sampling
                SamplingRule(
                    name="health-traces",
                    priority=1000,
                    fixed_rate=0.01,  # 1% of health checks
                    reservoir_size=1,
                    url_path="/health*",
                ),
                # Default rule
                SamplingRule(
                    name="default",
                    priority=10000,
                    fixed_rate=0.05,  # 5% default
                    reservoir_size=1,
                ),
            ]
