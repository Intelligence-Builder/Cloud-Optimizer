"""Unit tests for the Security Dashboard services."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cloud_optimizer.scanners.base import ScanResult
from cloud_optimizer.scanners.multi_account import (
    AccountScanResult,
    AuthMethod,
    AWSAccount,
)
from cloud_optimizer.services.security_dashboard import (
    OrganizationSummary,
    SecurityDashboard,
    SecurityScoreCalculator,
)


def _make_account(account_id: str, name: str, environment: str = "prod") -> AWSAccount:
    """Create a minimal AWSAccount for dashboard tests."""
    return AWSAccount(
        account_id=account_id,
        name=name,
        auth_method=AuthMethod.ASSUME_ROLE,
        role_arn=f"arn:aws:iam::{account_id}:role/Scanner",
        environment=environment,
    )


def _make_finding(rule_id: str, severity: str, passed: bool = False) -> ScanResult:
    """Create a scan result with the desired severity."""
    return ScanResult(
        rule_id=rule_id,
        passed=passed,
        resource_id=f"{rule_id}-resource",
        evidence={"severity": severity, "remediation": f"Fix {rule_id}"},
    )


def test_security_score_calculator_penalizes_severity() -> None:
    """SecurityScoreCalculator should deduct weighted points per severity."""
    findings = [
        _make_finding("TEST_CRIT", "critical"),
        _make_finding("TEST_HIGH", "high"),
        _make_finding("TEST_MED", "medium"),
        _make_finding("TEST_LOW", "low"),
        _make_finding("PASSED_RULE", "critical", passed=True),  # ignored
    ]

    score = SecurityScoreCalculator.calculate_score(findings)

    # Penalty = 10 + 5 + 2 + 0.5 = 17.5
    assert score.score == pytest.approx(82.5)
    assert score.critical_count == 1
    assert score.high_count == 1
    assert score.medium_count == 1
    assert score.low_count == 1
    assert score.findings_count == 4


def test_organization_summary_aggregates_findings() -> None:
    """Dashboard summary should aggregate per-account scores and totals."""
    dashboard = SecurityDashboard()
    account_a = AccountScanResult(
        account=_make_account("111111111111", "Prod"),
        findings=[
            _make_finding("RULE_A", "critical"),
            _make_finding("RULE_B", "medium"),
        ],
    )
    account_b = AccountScanResult(
        account=_make_account("222222222222", "Staging"),
        findings=[_make_finding("RULE_C", "high")],
    )

    summary = dashboard.get_organization_summary([account_a, account_b])

    assert isinstance(summary, OrganizationSummary)
    assert summary.total_accounts == 2
    assert summary.total_findings == 3
    assert summary.findings_by_severity["critical"] == 1
    assert summary.findings_by_severity["high"] == 1
    assert summary.findings_by_severity["medium"] == 1
    assert summary.findings_by_service["RULE"] == 3  # service derived from rule prefix
    assert summary.org_score.score < 100  # penalties applied


def test_heat_map_data_sorted_and_colored() -> None:
    """Heat map output should include risk color coding and be sorted (worst first)."""
    dashboard = SecurityDashboard()
    good_account = AccountScanResult(
        account=_make_account("111111111111", "Good"),
        findings=[],
    )
    very_risky_account = AccountScanResult(
        account=_make_account("222222222222", "Risky"),
        findings=[_make_finding("RULE_X", "critical")] * 6,
    )

    heat_map = dashboard.get_heat_map_data([good_account, very_risky_account])

    assert heat_map[0]["account_name"] == "Risky"
    assert heat_map[0]["color"] == "red"
    assert heat_map[1]["color"] == "green"


def test_recommendations_prioritize_severity_and_frequency() -> None:
    """Recommendations should be sorted by severity and occurrence."""
    dashboard = SecurityDashboard()
    account = AccountScanResult(
        account=_make_account("123456789012", "Prod"),
        findings=[
            _make_finding("RULE_CRIT", "critical"),
            _make_finding("RULE_HIGH", "high"),
            _make_finding("RULE_CRIT", "critical"),
        ],
    )

    recommendations = dashboard.get_recommendations([account], limit=5)

    assert recommendations
    assert recommendations[0]["rule_id"] == "RULE_CRIT"
    assert recommendations[0]["priority_score"] > recommendations[1]["priority_score"]


def test_record_scan_results_trims_history_after_90_days() -> None:
    """Historical scan data older than 90 days should be purged."""
    dashboard = SecurityDashboard()
    old_timestamp = datetime.now(timezone.utc) - timedelta(days=120)
    dashboard._scan_history = [(old_timestamp, [])]  # preload stale entry

    dashboard.record_scan_results(
        [
            AccountScanResult(
                account=_make_account("111111111111", "Prod"),
                findings=[_make_finding("RULE_A", "medium")],
            )
        ]
    )

    assert len(dashboard._scan_history) == 1
    ts, results = dashboard._scan_history[0]
    assert ts > old_timestamp
    assert results
