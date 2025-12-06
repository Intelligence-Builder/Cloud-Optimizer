"""Security Analysis Service - Unified facade for security analysis.

This module provides a unified interface to all security analysis capabilities,
coordinating scoring, explanation, remediation, and correlation services.
"""

import logging
from typing import Any, Dict, List, Optional

from cloud_optimizer.models.finding import Finding

from .correlation import FindingCluster, FindingCorrelator
from .explanation import FindingExplainer
from .remediation import RemediationGenerator, RemediationPlan
from .scoring import PrioritizedFinding, RiskScorer

logger = logging.getLogger(__name__)


class SecurityAnalysisService:
    """Unified security analysis service facade.

    This service coordinates all security analysis operations:
    - Risk scoring and prioritization
    - Finding explanation generation
    - Remediation plan creation
    - Finding correlation and clustering

    Example usage:
        ```python
        service = SecurityAnalysisService(anthropic_api_key="...")

        # Analyze findings
        analysis = await service.analyze_findings(findings)

        # Get prioritized findings with explanations
        prioritized = analysis["prioritized_findings"]

        # Get remediation plans
        plans = analysis["remediation_plans"]

        # Get correlated clusters
        clusters = analysis["clusters"]
        ```
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        min_cluster_size: int = 2,
    ) -> None:
        """Initialize the security analysis service.

        Args:
            anthropic_api_key: Anthropic API key for LLM explanations
            min_cluster_size: Minimum findings to form a cluster
        """
        self.scorer = RiskScorer()
        self.explainer = FindingExplainer(api_key=anthropic_api_key)
        self.remediation = RemediationGenerator()
        self.correlator = FindingCorrelator(min_cluster_size=min_cluster_size)

        logger.info(
            f"Initialized SecurityAnalysisService "
            f"(LLM available: {self.explainer.is_available()})"
        )

    async def analyze_findings(
        self,
        findings: List[Finding],
        include_explanations: bool = True,
        include_remediation: bool = True,
        include_clusters: bool = True,
        target_audience: str = "general",
        prefer_terraform: bool = True,
    ) -> Dict[str, Any]:
        """Perform comprehensive security analysis on findings.

        Args:
            findings: List of findings to analyze
            include_explanations: Generate LLM explanations
            include_remediation: Generate remediation plans
            include_clusters: Generate finding clusters
            target_audience: Target audience for explanations (general, technical, executive)
            prefer_terraform: Prefer Terraform in remediation examples

        Returns:
            Dictionary containing:
                - prioritized_findings: Risk-scored findings
                - explanations: Finding explanations (if requested)
                - remediation_plans: Remediation plans (if requested)
                - clusters: Finding clusters (if requested)
                - summary: Analysis summary statistics
        """
        logger.info(
            f"Starting comprehensive analysis of {len(findings)} findings "
            f"(explanations={include_explanations}, "
            f"remediation={include_remediation}, "
            f"clusters={include_clusters})"
        )

        result = {
            "finding_count": len(findings),
            "prioritized_findings": [],
            "explanations": [],
            "remediation_plans": [],
            "clusters": [],
            "summary": {},
        }

        if not findings:
            logger.warning("No findings to analyze")
            return result

        # 1. Score and prioritize findings
        prioritized = self.scorer.score_findings(findings)
        result["prioritized_findings"] = [p.to_dict() for p in prioritized]

        # 2. Generate explanations if requested
        if include_explanations and self.explainer.is_available():
            explanations = await self.explainer.explain_findings_batch(
                findings=findings,
                target_audience=target_audience,
            )
            result["explanations"] = explanations
        elif include_explanations and not self.explainer.is_available():
            logger.warning("Explanations requested but LLM not available")

        # 3. Generate remediation plans if requested
        if include_remediation:
            plans = await self.remediation.generate_plans_batch(
                findings=findings,
                prefer_terraform=prefer_terraform,
            )
            result["remediation_plans"] = [p.to_dict() for p in plans]

        # 4. Correlate and cluster findings if requested
        if include_clusters:
            clusters = self.correlator.correlate_findings(findings)
            result["clusters"] = [c.to_dict() for c in clusters]
            result["cluster_summary"] = self.correlator.get_cluster_summary(clusters)

        # 5. Generate summary statistics
        result["summary"] = self._generate_summary(
            prioritized=prioritized,
            explanations=result.get("explanations", []),
            plans=result.get("remediation_plans", []),
            clusters=result.get("clusters", []),
        )

        logger.info(
            f"Analysis complete: {len(prioritized)} findings prioritized, "
            f"{len(result.get('explanations', []))} explanations, "
            f"{len(result.get('remediation_plans', []))} plans, "
            f"{len(result.get('clusters', []))} clusters"
        )

        return result

    async def score_and_prioritize(
        self,
        findings: List[Finding],
    ) -> List[PrioritizedFinding]:
        """Score and prioritize findings.

        Args:
            findings: Findings to score

        Returns:
            List of prioritized findings
        """
        return self.scorer.score_findings(findings)

    async def explain_finding(
        self,
        finding: Finding,
        target_audience: str = "general",
        include_technical_details: bool = True,
    ) -> Dict[str, Any]:
        """Generate explanation for a single finding.

        Args:
            finding: Finding to explain
            target_audience: Target audience level
            include_technical_details: Include technical context

        Returns:
            Explanation dictionary
        """
        return await self.explainer.explain_finding(
            finding=finding,
            target_audience=target_audience,
            include_technical_details=include_technical_details,
        )

    async def generate_remediation_plan(
        self,
        finding: Finding,
        prefer_terraform: bool = True,
    ) -> RemediationPlan:
        """Generate remediation plan for a finding.

        Args:
            finding: Finding to remediate
            prefer_terraform: Prefer Terraform examples

        Returns:
            Remediation plan
        """
        return self.remediation.generate_plan(
            finding=finding,
            prefer_terraform=prefer_terraform,
        )

    def correlate_findings(
        self,
        findings: List[Finding],
    ) -> List[FindingCluster]:
        """Correlate findings and create clusters.

        Args:
            findings: Findings to correlate

        Returns:
            List of finding clusters
        """
        return self.correlator.correlate_findings(findings)

    def get_score_breakdown(
        self,
        prioritized_finding: PrioritizedFinding,
    ) -> Dict[str, Any]:
        """Get detailed score breakdown for a prioritized finding.

        Args:
            prioritized_finding: Prioritized finding

        Returns:
            Score breakdown dictionary
        """
        return self.scorer.get_score_breakdown(prioritized_finding)

    def _generate_summary(
        self,
        prioritized: List[PrioritizedFinding],
        explanations: List[Dict[str, Any]],
        plans: List[Dict[str, Any]],
        clusters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate analysis summary statistics.

        Args:
            prioritized: Prioritized findings
            explanations: Generated explanations
            plans: Generated remediation plans
            clusters: Generated clusters

        Returns:
            Summary statistics dictionary
        """
        # Priority distribution
        priority_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        for p in prioritized:
            priority_counts[p.priority_rank] += 1

        # Average scores
        if prioritized:
            avg_risk_score = sum(p.risk_score for p in prioritized) / len(prioritized)
            avg_severity_score = sum(p.severity_score for p in prioritized) / len(
                prioritized
            )
            avg_compliance_score = sum(p.compliance_score for p in prioritized) / len(
                prioritized
            )
        else:
            avg_risk_score = 0.0
            avg_severity_score = 0.0
            avg_compliance_score = 0.0

        # Remediation time
        total_remediation_time = sum(
            plan.get("total_estimated_time_minutes", 0) for plan in plans
        )

        summary = {
            "total_findings": len(prioritized),
            "priority_distribution": priority_counts,
            "average_scores": {
                "risk": round(avg_risk_score, 1),
                "severity": round(avg_severity_score, 1),
                "compliance": round(avg_compliance_score, 1),
            },
            "explanations_generated": len(explanations),
            "remediation_plans": len(plans),
            "total_remediation_time_minutes": total_remediation_time,
            "clusters_identified": len(clusters),
        }

        return summary

    async def analyze_top_findings(
        self,
        findings: List[Finding],
        top_n: int = 10,
        target_audience: str = "executive",
    ) -> Dict[str, Any]:
        """Analyze top N highest priority findings for executive summary.

        Args:
            findings: All findings
            top_n: Number of top findings to analyze
            target_audience: Target audience (usually executive)

        Returns:
            Analysis of top findings with executive-focused explanations
        """
        logger.info(f"Analyzing top {top_n} findings for {target_audience} audience")

        # Score and get top N
        prioritized = self.scorer.score_findings(findings)
        top_findings = [p.finding for p in prioritized[:top_n]]

        # Generate explanations for top findings
        explanations = []
        if self.explainer.is_available():
            explanations = await self.explainer.explain_findings_batch(
                findings=top_findings,
                target_audience=target_audience,
                include_technical_details=False,
            )

        # Generate plans for top findings
        plans = await self.remediation.generate_plans_batch(
            findings=top_findings,
            prefer_terraform=True,
        )

        return {
            "top_findings_count": len(top_findings),
            "prioritized_findings": [
                prioritized[i].to_dict() for i in range(min(top_n, len(prioritized)))
            ],
            "explanations": explanations,
            "remediation_plans": [p.to_dict() for p in plans],
            "executive_summary": self._generate_executive_summary(
                prioritized[:top_n], explanations
            ),
        }

    def _generate_executive_summary(
        self,
        top_prioritized: List[PrioritizedFinding],
        explanations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate executive-level summary.

        Args:
            top_prioritized: Top prioritized findings
            explanations: Generated explanations

        Returns:
            Executive summary dictionary
        """
        critical_count = sum(
            1 for p in top_prioritized if p.priority_rank == "critical"
        )
        high_count = sum(1 for p in top_prioritized if p.priority_rank == "high")

        # Key risks from explanations
        key_risks = []
        for explanation in explanations[:3]:  # Top 3
            if explanation.get("why_it_matters"):
                key_risks.append(explanation["why_it_matters"])

        return {
            "critical_issues": critical_count,
            "high_priority_issues": high_count,
            "immediate_action_required": critical_count + high_count,
            "key_risks": key_risks,
            "recommendation": self._generate_executive_recommendation(
                critical_count, high_count
            ),
        }

    def _generate_executive_recommendation(
        self,
        critical_count: int,
        high_count: int,
    ) -> str:
        """Generate executive recommendation based on finding counts.

        Args:
            critical_count: Number of critical findings
            high_count: Number of high priority findings

        Returns:
            Executive recommendation text
        """
        if critical_count > 0:
            return (
                f"Immediate action required: {critical_count} critical security "
                f"issue(s) identified that pose significant risk to the organization. "
                f"Recommend scheduling emergency remediation session."
            )
        elif high_count > 0:
            return (
                f"Prompt attention needed: {high_count} high-priority security "
                f"issue(s) identified. Recommend addressing within 1-2 weeks."
            )
        else:
            return (
                "Security posture is stable. Continue with standard remediation "
                "timeline for remaining findings."
            )
