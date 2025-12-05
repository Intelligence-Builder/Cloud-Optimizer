"""Organization-Wide Security Posture Dashboard.

Issue #149: 9.2.3 Organization-wide security posture dashboard

Creates a comprehensive dashboard providing organization-wide visibility into
security posture across all AWS accounts with trend analysis, heat maps,
and executive-level metrics.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from cloud_optimizer.scanners.base import ScanResult
from cloud_optimizer.scanners.multi_account import AccountScanResult, AWSAccount

logger = logging.getLogger(__name__)


class SecurityTrend(str, Enum):
    """Security posture trend direction."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class SeverityLevel(str, Enum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SecurityScore:
    """Security score for an account or organization.

    Attributes:
        score: Numeric score (0-100)
        findings_count: Total findings count
        critical_count: Critical severity findings
        high_count: High severity findings
        medium_count: Medium severity findings
        low_count: Low severity findings
        trend: Score trend direction
        change_percentage: Percentage change from previous period
    """

    score: float
    findings_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    trend: SecurityTrend = SecurityTrend.STABLE
    change_percentage: float = 0.0

    @property
    def grade(self) -> str:
        """Get letter grade for score.

        Returns:
            Letter grade (A-F)
        """
        if self.score >= 90:
            return "A"
        elif self.score >= 80:
            return "B"
        elif self.score >= 70:
            return "C"
        elif self.score >= 60:
            return "D"
        else:
            return "F"

    @property
    def status(self) -> str:
        """Get status description.

        Returns:
            Status description
        """
        if self.score >= 90:
            return "Excellent"
        elif self.score >= 80:
            return "Good"
        elif self.score >= 70:
            return "Fair"
        elif self.score >= 60:
            return "Needs Improvement"
        else:
            return "Critical"


@dataclass
class AccountSecuritySummary:
    """Security summary for a single account.

    Attributes:
        account_id: AWS account ID
        account_name: Account friendly name
        environment: Account environment (prod, staging, dev)
        score: Security score
        findings_by_service: Finding counts by service
        top_issues: Top security issues
        last_scan: Last scan timestamp
    """

    account_id: str
    account_name: str
    environment: str
    score: SecurityScore
    findings_by_service: Dict[str, int] = field(default_factory=dict)
    top_issues: List[Dict[str, Any]] = field(default_factory=list)
    last_scan: Optional[datetime] = None


@dataclass
class OrganizationSummary:
    """Organization-wide security summary.

    Attributes:
        total_accounts: Number of accounts
        total_findings: Total findings across all accounts
        org_score: Organization-wide security score
        accounts_by_score: Account count by score range
        findings_by_severity: Findings by severity level
        findings_by_service: Findings by AWS service
        top_issues: Top issues across organization
        trend_30d: 30-day trend data
        trend_60d: 60-day trend data
        trend_90d: 90-day trend data
    """

    total_accounts: int = 0
    total_findings: int = 0
    org_score: SecurityScore = field(default_factory=lambda: SecurityScore(score=100))
    accounts_by_score: Dict[str, int] = field(default_factory=dict)
    findings_by_severity: Dict[str, int] = field(default_factory=dict)
    findings_by_service: Dict[str, int] = field(default_factory=dict)
    top_issues: List[Dict[str, Any]] = field(default_factory=list)
    trend_30d: List[Dict[str, Any]] = field(default_factory=list)
    trend_60d: List[Dict[str, Any]] = field(default_factory=list)
    trend_90d: List[Dict[str, Any]] = field(default_factory=list)


class SecurityScoreCalculator:
    """Calculates security scores based on findings.

    Uses a weighted scoring system based on finding severity:
    - Critical: -10 points each
    - High: -5 points each
    - Medium: -2 points each
    - Low: -0.5 points each

    Base score is 100, minimum score is 0.
    """

    # Severity weights for score calculation
    SEVERITY_WEIGHTS = {
        "critical": 10.0,
        "high": 5.0,
        "medium": 2.0,
        "low": 0.5,
    }

    @classmethod
    def calculate_score(
        cls,
        findings: List[ScanResult],
        rules: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> SecurityScore:
        """Calculate security score from findings.

        Args:
            findings: List of scan findings
            rules: Optional rule definitions for severity lookup

        Returns:
            Calculated security score
        """
        base_score = 100.0
        penalty = 0.0

        # Count findings by severity
        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        for finding in findings:
            if finding.passed:
                continue

            # Get severity from evidence or rule lookup
            severity = finding.evidence.get("severity", "medium").lower()
            if severity not in counts:
                severity = "medium"

            counts[severity] += 1
            penalty += cls.SEVERITY_WEIGHTS.get(severity, 2.0)

        # Calculate final score
        score = max(0.0, base_score - penalty)

        return SecurityScore(
            score=round(score, 1),
            findings_count=sum(counts.values()),
            critical_count=counts["critical"],
            high_count=counts["high"],
            medium_count=counts["medium"],
            low_count=counts["low"],
        )

    @classmethod
    def calculate_org_score(
        cls,
        account_scores: List[SecurityScore],
    ) -> SecurityScore:
        """Calculate organization-wide score from account scores.

        Uses weighted average based on finding counts.

        Args:
            account_scores: List of account security scores

        Returns:
            Organization security score
        """
        if not account_scores:
            return SecurityScore(score=100.0)

        total_findings = sum(s.findings_count for s in account_scores)
        if total_findings == 0:
            # Simple average if no findings
            avg_score = sum(s.score for s in account_scores) / len(account_scores)
            return SecurityScore(score=round(avg_score, 1))

        # Weighted average by finding count
        weighted_sum = sum(
            s.score * s.findings_count for s in account_scores
        )
        weighted_avg = weighted_sum / total_findings

        # Aggregate severity counts
        return SecurityScore(
            score=round(weighted_avg, 1),
            findings_count=total_findings,
            critical_count=sum(s.critical_count for s in account_scores),
            high_count=sum(s.high_count for s in account_scores),
            medium_count=sum(s.medium_count for s in account_scores),
            low_count=sum(s.low_count for s in account_scores),
        )


class SecurityDashboard:
    """Organization-wide security posture dashboard.

    Provides aggregated views, trend analysis, and recommendations
    based on scan results across all AWS accounts.
    """

    def __init__(self) -> None:
        """Initialize dashboard."""
        self._scan_history: List[Tuple[datetime, List[AccountScanResult]]] = []
        self._calculator = SecurityScoreCalculator()

    def record_scan_results(self, results: List[AccountScanResult]) -> None:
        """Record scan results for trend tracking.

        Args:
            results: Scan results to record
        """
        now = datetime.now(timezone.utc)
        self._scan_history.append((now, results))

        # Keep only last 90 days of history
        cutoff = now - timedelta(days=90)
        self._scan_history = [
            (ts, r) for ts, r in self._scan_history if ts > cutoff
        ]

    def get_organization_summary(
        self,
        results: List[AccountScanResult],
    ) -> OrganizationSummary:
        """Get organization-wide security summary.

        Args:
            results: Current scan results

        Returns:
            Organization summary
        """
        summary = OrganizationSummary()
        summary.total_accounts = len(results)

        # Calculate per-account scores
        account_scores: List[SecurityScore] = []
        findings_by_severity: Dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        findings_by_service: Dict[str, int] = {}
        all_findings: List[ScanResult] = []

        for result in results:
            # Calculate account score
            score = self._calculator.calculate_score(result.findings)
            account_scores.append(score)

            # Aggregate findings
            all_findings.extend(result.findings)

            for finding in result.findings:
                if finding.passed:
                    continue

                # Count by severity
                severity = finding.evidence.get("severity", "medium").lower()
                if severity in findings_by_severity:
                    findings_by_severity[severity] += 1

                # Count by service
                service = finding.rule_id.split("_")[0]
                findings_by_service[service] = (
                    findings_by_service.get(service, 0) + 1
                )

        # Calculate org score
        summary.org_score = self._calculator.calculate_org_score(account_scores)
        summary.total_findings = summary.org_score.findings_count
        summary.findings_by_severity = findings_by_severity
        summary.findings_by_service = findings_by_service

        # Categorize accounts by score
        summary.accounts_by_score = {
            "excellent": sum(1 for s in account_scores if s.score >= 90),
            "good": sum(1 for s in account_scores if 80 <= s.score < 90),
            "fair": sum(1 for s in account_scores if 70 <= s.score < 80),
            "poor": sum(1 for s in account_scores if 60 <= s.score < 70),
            "critical": sum(1 for s in account_scores if s.score < 60),
        }

        # Get top issues
        summary.top_issues = self._get_top_issues(all_findings)

        # Calculate trends
        summary.trend_30d = self._calculate_trend(days=30)
        summary.trend_60d = self._calculate_trend(days=60)
        summary.trend_90d = self._calculate_trend(days=90)

        return summary

    def get_account_summary(
        self,
        result: AccountScanResult,
    ) -> AccountSecuritySummary:
        """Get security summary for a single account.

        Args:
            result: Account scan result

        Returns:
            Account security summary
        """
        score = self._calculator.calculate_score(result.findings)

        # Group findings by service
        findings_by_service: Dict[str, int] = {}
        for finding in result.findings:
            if finding.passed:
                continue
            service = finding.rule_id.split("_")[0]
            findings_by_service[service] = findings_by_service.get(service, 0) + 1

        return AccountSecuritySummary(
            account_id=result.account.account_id,
            account_name=result.account.name,
            environment=result.account.environment,
            score=score,
            findings_by_service=findings_by_service,
            top_issues=self._get_top_issues(result.findings, limit=5),
            last_scan=datetime.now(timezone.utc),
        )

    def get_heat_map_data(
        self,
        results: List[AccountScanResult],
    ) -> List[Dict[str, Any]]:
        """Get data for account heat map visualization.

        Args:
            results: Scan results

        Returns:
            List of account data for heat map
        """
        heat_map_data: List[Dict[str, Any]] = []

        for result in results:
            score = self._calculator.calculate_score(result.findings)

            # Determine color based on score
            if score.score >= 90:
                color = "green"
            elif score.score >= 70:
                color = "yellow"
            elif score.score >= 50:
                color = "orange"
            else:
                color = "red"

            heat_map_data.append({
                "account_id": result.account.account_id,
                "account_name": result.account.name,
                "environment": result.account.environment,
                "score": score.score,
                "grade": score.grade,
                "color": color,
                "findings_count": score.findings_count,
                "critical_count": score.critical_count,
            })

        # Sort by score (worst first)
        heat_map_data.sort(key=lambda x: x["score"])

        return heat_map_data

    def get_recommendations(
        self,
        results: List[AccountScanResult],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get prioritized recommendations based on findings.

        Args:
            results: Scan results
            limit: Maximum number of recommendations

        Returns:
            List of recommendations
        """
        # Aggregate all findings
        all_findings: List[Dict[str, Any]] = []
        for result in results:
            for finding in result.findings:
                if finding.passed:
                    continue
                all_findings.append({
                    "rule_id": finding.rule_id,
                    "account_id": result.account.account_id,
                    "severity": finding.evidence.get("severity", "medium"),
                    "resource_id": finding.resource_id,
                    "remediation": finding.evidence.get("remediation", ""),
                })

        # Group by rule_id and count occurrences
        rule_counts: Dict[str, Dict[str, Any]] = {}
        for finding in all_findings:
            rule_id = finding["rule_id"]
            if rule_id not in rule_counts:
                rule_counts[rule_id] = {
                    "rule_id": rule_id,
                    "severity": finding["severity"],
                    "count": 0,
                    "affected_accounts": set(),
                    "remediation": finding["remediation"],
                }
            rule_counts[rule_id]["count"] += 1
            rule_counts[rule_id]["affected_accounts"].add(finding["account_id"])

        # Calculate priority score
        severity_priority = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        recommendations: List[Dict[str, Any]] = []

        for rule_id, data in rule_counts.items():
            priority = (
                severity_priority.get(data["severity"], 2) * 100
                + len(data["affected_accounts"]) * 10
                + data["count"]
            )

            recommendations.append({
                "rule_id": rule_id,
                "severity": data["severity"],
                "occurrence_count": data["count"],
                "affected_accounts_count": len(data["affected_accounts"]),
                "priority_score": priority,
                "remediation": data["remediation"],
                "impact": self._estimate_impact(data["severity"], data["count"]),
            })

        # Sort by priority (highest first)
        recommendations.sort(key=lambda x: x["priority_score"], reverse=True)

        return recommendations[:limit]

    def _get_top_issues(
        self,
        findings: List[ScanResult],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top issues from findings.

        Args:
            findings: List of findings
            limit: Maximum number of issues

        Returns:
            List of top issues
        """
        # Count findings by rule
        rule_counts: Dict[str, int] = {}
        rule_severity: Dict[str, str] = {}

        for finding in findings:
            if finding.passed:
                continue
            rule_id = finding.rule_id
            rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1
            rule_severity[rule_id] = finding.evidence.get("severity", "medium")

        # Sort by count
        sorted_rules = sorted(
            rule_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return [
            {
                "rule_id": rule_id,
                "count": count,
                "severity": rule_severity.get(rule_id, "medium"),
            }
            for rule_id, count in sorted_rules[:limit]
        ]

    def _calculate_trend(self, days: int) -> List[Dict[str, Any]]:
        """Calculate trend data for a time period.

        Args:
            days: Number of days to include

        Returns:
            List of trend data points
        """
        if not self._scan_history:
            return []

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)

        trend_data: List[Dict[str, Any]] = []
        for ts, results in self._scan_history:
            if ts < cutoff:
                continue

            # Calculate aggregate score for this scan
            all_findings: List[ScanResult] = []
            for result in results:
                all_findings.extend(result.findings)

            score = self._calculator.calculate_score(all_findings)

            trend_data.append({
                "timestamp": ts.isoformat(),
                "score": score.score,
                "findings_count": score.findings_count,
                "critical_count": score.critical_count,
            })

        return trend_data

    def _estimate_impact(self, severity: str, count: int) -> str:
        """Estimate impact of addressing an issue.

        Args:
            severity: Issue severity
            count: Number of occurrences

        Returns:
            Impact description
        """
        if severity == "critical":
            return "Critical - Address immediately"
        elif severity == "high" and count >= 5:
            return "High - Significant security improvement"
        elif severity == "high":
            return "High - Important security fix"
        elif severity == "medium" and count >= 10:
            return "Medium - Substantial improvement"
        elif severity == "medium":
            return "Medium - Recommended fix"
        else:
            return "Low - Minor improvement"

    def export_summary_to_dict(
        self,
        results: List[AccountScanResult],
    ) -> Dict[str, Any]:
        """Export dashboard summary to dictionary for API/UI.

        Args:
            results: Scan results

        Returns:
            Dictionary with all dashboard data
        """
        org_summary = self.get_organization_summary(results)
        heat_map = self.get_heat_map_data(results)
        recommendations = self.get_recommendations(results)

        return {
            "organization": {
                "total_accounts": org_summary.total_accounts,
                "total_findings": org_summary.total_findings,
                "security_score": org_summary.org_score.score,
                "grade": org_summary.org_score.grade,
                "status": org_summary.org_score.status,
            },
            "findings_by_severity": org_summary.findings_by_severity,
            "findings_by_service": org_summary.findings_by_service,
            "accounts_by_score": org_summary.accounts_by_score,
            "top_issues": org_summary.top_issues,
            "heat_map": heat_map,
            "recommendations": recommendations,
            "trends": {
                "30_day": org_summary.trend_30d,
                "60_day": org_summary.trend_60d,
                "90_day": org_summary.trend_90d,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
