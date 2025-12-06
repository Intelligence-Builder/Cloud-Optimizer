"""Risk scoring and finding prioritization module.

This module provides risk scoring functionality for security findings,
calculating scores based on severity, compliance impact, resource type,
and exposure level.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from cloud_optimizer.models.finding import Finding, FindingSeverity

logger = logging.getLogger(__name__)


@dataclass
class PrioritizedFinding:
    """A finding with calculated risk score and priority information.

    Attributes:
        finding: Original finding object
        risk_score: Calculated risk score (0-100)
        severity_score: Score from severity (0-40)
        compliance_score: Score from compliance impact (0-30)
        resource_score: Score from resource type (0-20)
        exposure_score: Score from exposure level (0-10)
        priority_rank: Priority level (critical, high, medium, low)
    """

    finding: Finding
    risk_score: float
    severity_score: float
    compliance_score: float
    resource_score: float
    exposure_score: float
    priority_rank: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with finding and scoring details
        """
        return {
            "finding_id": str(self.finding.finding_id),
            "rule_id": self.finding.rule_id,
            "title": self.finding.title,
            "severity": self.finding.severity.value,
            "resource_type": self.finding.resource_type,
            "resource_id": self.finding.resource_id,
            "risk_score": self.risk_score,
            "severity_score": self.severity_score,
            "compliance_score": self.compliance_score,
            "resource_score": self.resource_score,
            "exposure_score": self.exposure_score,
            "priority_rank": self.priority_rank,
            "compliance_frameworks": self.finding.compliance_frameworks,
        }


class RiskScorer:
    """Calculate risk scores for security findings.

    Risk scoring formula:
    - Severity: 0-40 points (critical=40, high=30, medium=15, low=5, info=0)
    - Compliance: 0-30 points (high-value frameworks get 30, others get 15)
    - Resource Type: 0-20 points (high-risk resources get 20, others get 10)
    - Exposure: 0-10 points (public exposure keywords add 10 points)

    Total Score: 0-100 points

    Priority Ranks:
    - Critical: 80-100 points
    - High: 60-79 points
    - Medium: 30-59 points
    - Low: 0-29 points
    """

    # Severity weights (max 40 points)
    SEVERITY_WEIGHTS: Dict[FindingSeverity, float] = {
        FindingSeverity.CRITICAL: 40.0,
        FindingSeverity.HIGH: 30.0,
        FindingSeverity.MEDIUM: 15.0,
        FindingSeverity.LOW: 5.0,
        FindingSeverity.INFO: 0.0,
    }

    # High-value compliance frameworks (30 points)
    HIGH_VALUE_FRAMEWORKS: List[str] = [
        "HIPAA",
        "PCI-DSS",
        "PCI DSS",
        "SOX",
        "GDPR",
        "SOC2",
        "SOC 2",
    ]

    # High-risk resource types (20 points)
    HIGH_RISK_RESOURCES: List[str] = [
        "iam",
        "s3",
        "rds",
        "kms",
        "secretsmanager",
        "lambda",
        "ec2",
    ]

    # Public exposure keywords (10 points)
    EXPOSURE_KEYWORDS: List[str] = [
        "public",
        "internet",
        "0.0.0.0/0",
        "::/0",
        "world",
        "anonymous",
        "unauthenticated",
        "*",
    ]

    def __init__(self) -> None:
        """Initialize the risk scorer."""
        logger.info("Initialized RiskScorer")

    def score_finding(self, finding: Finding) -> PrioritizedFinding:
        """Calculate risk score for a single finding.

        Args:
            finding: Finding to score

        Returns:
            PrioritizedFinding with calculated scores
        """
        # Calculate component scores
        severity_score = self._calculate_severity_score(finding)
        compliance_score = self._calculate_compliance_score(finding)
        resource_score = self._calculate_resource_score(finding)
        exposure_score = self._calculate_exposure_score(finding)

        # Total risk score
        risk_score = severity_score + compliance_score + resource_score + exposure_score

        # Determine priority rank
        priority_rank = self._determine_priority_rank(risk_score)

        logger.debug(
            f"Scored finding {finding.finding_id}: "
            f"risk={risk_score:.1f}, "
            f"severity={severity_score:.1f}, "
            f"compliance={compliance_score:.1f}, "
            f"resource={resource_score:.1f}, "
            f"exposure={exposure_score:.1f}, "
            f"priority={priority_rank}"
        )

        return PrioritizedFinding(
            finding=finding,
            risk_score=risk_score,
            severity_score=severity_score,
            compliance_score=compliance_score,
            resource_score=resource_score,
            exposure_score=exposure_score,
            priority_rank=priority_rank,
        )

    def score_findings(self, findings: List[Finding]) -> List[PrioritizedFinding]:
        """Calculate risk scores for multiple findings and sort by priority.

        Args:
            findings: List of findings to score

        Returns:
            List of prioritized findings sorted by risk score (highest first)
        """
        logger.info(f"Scoring {len(findings)} findings")

        prioritized = [self.score_finding(finding) for finding in findings]

        # Sort by risk score descending
        prioritized.sort(key=lambda x: x.risk_score, reverse=True)

        logger.info(
            f"Completed scoring: "
            f"critical={sum(1 for p in prioritized if p.priority_rank == 'critical')}, "
            f"high={sum(1 for p in prioritized if p.priority_rank == 'high')}, "
            f"medium={sum(1 for p in prioritized if p.priority_rank == 'medium')}, "
            f"low={sum(1 for p in prioritized if p.priority_rank == 'low')}"
        )

        return prioritized

    def _calculate_severity_score(self, finding: Finding) -> float:
        """Calculate score based on severity (0-40 points).

        Args:
            finding: Finding to score

        Returns:
            Severity score
        """
        return self.SEVERITY_WEIGHTS.get(finding.severity, 0.0)

    def _calculate_compliance_score(self, finding: Finding) -> float:
        """Calculate score based on compliance impact (0-30 points).

        Args:
            finding: Finding to score

        Returns:
            Compliance score
        """
        if not finding.compliance_frameworks:
            return 0.0

        # Check if any framework is high-value
        frameworks_upper = [fw.upper() for fw in finding.compliance_frameworks]
        for high_value_fw in self.HIGH_VALUE_FRAMEWORKS:
            if any(high_value_fw.upper() in fw for fw in frameworks_upper):
                return 30.0

        # Has compliance impact but not high-value
        return 15.0

    def _calculate_resource_score(self, finding: Finding) -> float:
        """Calculate score based on resource type (0-20 points).

        Args:
            finding: Finding to score

        Returns:
            Resource type score
        """
        resource_type_lower = finding.resource_type.lower()

        # Check if resource type is high-risk
        for high_risk in self.HIGH_RISK_RESOURCES:
            if high_risk in resource_type_lower:
                return 20.0

        # Other resource types
        return 10.0

    def _calculate_exposure_score(self, finding: Finding) -> float:
        """Calculate score based on exposure level (0-10 points).

        Args:
            finding: Finding to score

        Returns:
            Exposure score
        """
        # Check evidence and description for exposure keywords
        text_to_check = [
            finding.title.lower(),
            finding.description.lower(),
            str(finding.evidence).lower(),
        ]

        for text in text_to_check:
            for keyword in self.EXPOSURE_KEYWORDS:
                if keyword.lower() in text:
                    return 10.0

        return 0.0

    def _determine_priority_rank(self, risk_score: float) -> str:
        """Determine priority rank based on risk score.

        Args:
            risk_score: Calculated risk score (0-100)

        Returns:
            Priority rank (critical, high, medium, low)
        """
        if risk_score >= 80:
            return "critical"
        elif risk_score >= 60:
            return "high"
        elif risk_score >= 30:
            return "medium"
        else:
            return "low"

    def get_score_breakdown(self, prioritized: PrioritizedFinding) -> Dict[str, Any]:
        """Get detailed breakdown of score calculation.

        Args:
            prioritized: Prioritized finding

        Returns:
            Dictionary with score breakdown and explanation
        """
        return {
            "finding_id": str(prioritized.finding.finding_id),
            "total_score": prioritized.risk_score,
            "priority_rank": prioritized.priority_rank,
            "components": {
                "severity": {
                    "score": prioritized.severity_score,
                    "max": 40,
                    "value": prioritized.finding.severity.value,
                },
                "compliance": {
                    "score": prioritized.compliance_score,
                    "max": 30,
                    "frameworks": prioritized.finding.compliance_frameworks,
                },
                "resource_type": {
                    "score": prioritized.resource_score,
                    "max": 20,
                    "type": prioritized.finding.resource_type,
                },
                "exposure": {
                    "score": prioritized.exposure_score,
                    "max": 10,
                },
            },
            "explanation": self._generate_score_explanation(prioritized),
        }

    def _generate_score_explanation(self, prioritized: PrioritizedFinding) -> str:
        """Generate human-readable explanation of score.

        Args:
            prioritized: Prioritized finding

        Returns:
            Explanation text
        """
        parts = []

        # Severity
        parts.append(
            f"Severity is {prioritized.finding.severity.value} "
            f"({prioritized.severity_score:.0f}/40 points)"
        )

        # Compliance
        if prioritized.compliance_score > 0:
            frameworks = ", ".join(prioritized.finding.compliance_frameworks)
            parts.append(
                f"Impacts compliance frameworks: {frameworks} "
                f"({prioritized.compliance_score:.0f}/30 points)"
            )

        # Resource type
        parts.append(
            f"Resource type {prioritized.finding.resource_type} "
            f"({prioritized.resource_score:.0f}/20 points)"
        )

        # Exposure
        if prioritized.exposure_score > 0:
            parts.append(
                f"Has public exposure risk ({prioritized.exposure_score:.0f}/10 points)"
            )

        return ". ".join(parts) + "."
