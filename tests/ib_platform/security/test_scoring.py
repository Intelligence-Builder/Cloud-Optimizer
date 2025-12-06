"""Tests for security analysis risk scoring."""

import pytest

from cloud_optimizer.models.finding import Finding, FindingSeverity
from ib_platform.security.scoring import PrioritizedFinding, RiskScorer


class TestRiskScorer:
    """Test cases for RiskScorer class."""

    def test_scorer_initialization(self) -> None:
        """Test that RiskScorer initializes correctly."""
        scorer = RiskScorer()
        assert scorer is not None
        assert scorer.SEVERITY_WEIGHTS[FindingSeverity.CRITICAL] == 40.0
        assert scorer.SEVERITY_WEIGHTS[FindingSeverity.HIGH] == 30.0
        assert scorer.SEVERITY_WEIGHTS[FindingSeverity.MEDIUM] == 15.0
        assert scorer.SEVERITY_WEIGHTS[FindingSeverity.LOW] == 5.0

    def test_score_critical_finding(self, critical_finding: Finding) -> None:
        """Test scoring of a critical severity finding."""
        scorer = RiskScorer()
        prioritized = scorer.score_finding(critical_finding)

        assert isinstance(prioritized, PrioritizedFinding)
        assert prioritized.severity_score == 40.0  # Critical severity
        assert prioritized.compliance_score == 30.0  # HIPAA is high-value
        assert prioritized.resource_score == 20.0  # IAM is high-risk
        assert prioritized.exposure_score == 10.0  # Has public exposure in evidence
        assert prioritized.risk_score == 100.0  # Max score
        assert prioritized.priority_rank == "critical"

    def test_score_high_severity_finding(self, sample_finding: Finding) -> None:
        """Test scoring of a high severity finding."""
        scorer = RiskScorer()
        prioritized = scorer.score_finding(sample_finding)

        assert prioritized.severity_score == 30.0  # High severity
        assert prioritized.compliance_score == 30.0  # HIPAA is high-value
        assert prioritized.resource_score == 20.0  # S3 is high-risk
        assert prioritized.exposure_score == 10.0  # Has public in evidence
        assert prioritized.risk_score == 90.0
        assert prioritized.priority_rank == "critical"  # 90 >= 80

    def test_score_low_severity_finding(self, low_severity_finding: Finding) -> None:
        """Test scoring of a low severity finding."""
        scorer = RiskScorer()
        prioritized = scorer.score_finding(low_severity_finding)

        assert prioritized.severity_score == 5.0  # Low severity
        assert prioritized.compliance_score == 0.0  # No compliance frameworks
        assert prioritized.resource_score == 10.0  # EC2 not in high-risk list
        assert prioritized.exposure_score == 0.0  # No exposure keywords
        assert prioritized.risk_score == 15.0
        assert prioritized.priority_rank == "low"  # < 30

    def test_score_findings_batch(self, multiple_findings: list[Finding]) -> None:
        """Test scoring multiple findings at once."""
        scorer = RiskScorer()
        prioritized = scorer.score_findings(multiple_findings)

        assert len(prioritized) == 5
        # Should be sorted by risk score descending
        assert prioritized[0].risk_score >= prioritized[1].risk_score
        assert prioritized[1].risk_score >= prioritized[2].risk_score

        # Critical finding should be first
        assert prioritized[0].finding.severity == FindingSeverity.CRITICAL

    def test_severity_score_calculation(self) -> None:
        """Test severity score calculation for all levels."""
        scorer = RiskScorer()

        assert scorer.SEVERITY_WEIGHTS[FindingSeverity.CRITICAL] == 40.0
        assert scorer.SEVERITY_WEIGHTS[FindingSeverity.HIGH] == 30.0
        assert scorer.SEVERITY_WEIGHTS[FindingSeverity.MEDIUM] == 15.0
        assert scorer.SEVERITY_WEIGHTS[FindingSeverity.LOW] == 5.0
        assert scorer.SEVERITY_WEIGHTS[FindingSeverity.INFO] == 0.0

    def test_compliance_score_high_value_frameworks(
        self, sample_finding: Finding
    ) -> None:
        """Test that high-value compliance frameworks get higher scores."""
        scorer = RiskScorer()
        # sample_finding has HIPAA and PCI-DSS
        prioritized = scorer.score_finding(sample_finding)
        assert prioritized.compliance_score == 30.0

    def test_compliance_score_other_frameworks(self) -> None:
        """Test that other frameworks get moderate scores."""
        from datetime import datetime, timezone
        from uuid import uuid4

        finding = Finding(
            finding_id=uuid4(),
            scan_job_id=uuid4(),
            aws_account_id=uuid4(),
            rule_id="TEST-001",
            finding_type="security",
            severity=FindingSeverity.MEDIUM,
            status="open",
            service="s3",
            resource_type="aws_s3_bucket",
            resource_id="test-bucket",
            region="us-east-1",
            title="Test finding",
            description="Test",
            recommendation="Fix it",
            compliance_frameworks=["CIS", "NIST"],  # Not in high-value list
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )

        scorer = RiskScorer()
        prioritized = scorer.score_finding(finding)
        assert prioritized.compliance_score == 15.0

    def test_resource_score_high_risk_resources(self) -> None:
        """Test that high-risk resources get higher scores."""
        scorer = RiskScorer()

        # Test each high-risk resource type
        high_risk_types = ["iam", "s3", "rds", "kms", "secretsmanager", "lambda", "ec2"]

        for resource_type in high_risk_types:
            from datetime import datetime, timezone
            from uuid import uuid4

            finding = Finding(
                finding_id=uuid4(),
                scan_job_id=uuid4(),
                aws_account_id=uuid4(),
                rule_id="TEST-001",
                finding_type="security",
                severity=FindingSeverity.MEDIUM,
                status="open",
                service="test",
                resource_type=f"aws_{resource_type}_resource",
                resource_id="test",
                region="us-east-1",
                title="Test",
                description="Test",
                recommendation="Fix",
                first_seen_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
            )

            prioritized = scorer.score_finding(finding)
            assert prioritized.resource_score == 20.0, f"Failed for {resource_type}"

    def test_exposure_score_keywords(self) -> None:
        """Test that exposure keywords increase score."""
        scorer = RiskScorer()
        from datetime import datetime, timezone
        from uuid import uuid4

        keywords = ["public", "internet", "0.0.0.0/0", "world", "anonymous"]

        for keyword in keywords:
            finding = Finding(
                finding_id=uuid4(),
                scan_job_id=uuid4(),
                aws_account_id=uuid4(),
                rule_id="TEST-001",
                finding_type="security",
                severity=FindingSeverity.MEDIUM,
                status="open",
                service="test",
                resource_type="test",
                resource_id="test",
                region="us-east-1",
                title=f"Test with {keyword}",
                description="Test",
                recommendation="Fix",
                first_seen_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
            )

            prioritized = scorer.score_finding(finding)
            assert prioritized.exposure_score == 10.0, f"Failed for keyword: {keyword}"

    def test_priority_rank_thresholds(self) -> None:
        """Test priority rank assignment based on score thresholds."""
        scorer = RiskScorer()

        # Critical: 80-100
        assert scorer._determine_priority_rank(100) == "critical"
        assert scorer._determine_priority_rank(80) == "critical"

        # High: 60-79
        assert scorer._determine_priority_rank(79) == "high"
        assert scorer._determine_priority_rank(60) == "high"

        # Medium: 30-59
        assert scorer._determine_priority_rank(59) == "medium"
        assert scorer._determine_priority_rank(30) == "medium"

        # Low: 0-29
        assert scorer._determine_priority_rank(29) == "low"
        assert scorer._determine_priority_rank(0) == "low"

    def test_get_score_breakdown(self, sample_finding: Finding) -> None:
        """Test detailed score breakdown generation."""
        scorer = RiskScorer()
        prioritized = scorer.score_finding(sample_finding)
        breakdown = scorer.get_score_breakdown(prioritized)

        assert "finding_id" in breakdown
        assert "total_score" in breakdown
        assert "priority_rank" in breakdown
        assert "components" in breakdown
        assert "explanation" in breakdown

        components = breakdown["components"]
        assert "severity" in components
        assert "compliance" in components
        assert "resource_type" in components
        assert "exposure" in components

        # Check that each component has expected structure
        assert components["severity"]["score"] == prioritized.severity_score
        assert components["severity"]["max"] == 40
        assert components["compliance"]["max"] == 30
        assert components["resource_type"]["max"] == 20
        assert components["exposure"]["max"] == 10

    def test_prioritized_finding_to_dict(self, sample_finding: Finding) -> None:
        """Test conversion of PrioritizedFinding to dictionary."""
        scorer = RiskScorer()
        prioritized = scorer.score_finding(sample_finding)
        result = prioritized.to_dict()

        assert isinstance(result, dict)
        assert "finding_id" in result
        assert "risk_score" in result
        assert "severity_score" in result
        assert "compliance_score" in result
        assert "resource_score" in result
        assert "exposure_score" in result
        assert "priority_rank" in result
        assert "title" in result
        assert "severity" in result

    def test_empty_findings_list(self) -> None:
        """Test scoring empty findings list."""
        scorer = RiskScorer()
        prioritized = scorer.score_findings([])
        assert prioritized == []

    def test_score_explanation_generation(self, sample_finding: Finding) -> None:
        """Test that score explanation is human-readable."""
        scorer = RiskScorer()
        prioritized = scorer.score_finding(sample_finding)
        explanation = scorer._generate_score_explanation(prioritized)

        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "Severity" in explanation or "severity" in explanation
        assert sample_finding.severity.value in explanation
