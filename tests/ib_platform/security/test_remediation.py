"""Tests for remediation plan generation."""

import pytest

from cloud_optimizer.models.finding import Finding
from ib_platform.security.remediation import (
    RemediationGenerator,
    RemediationPlan,
    RemediationStep,
)


class TestRemediationGenerator:
    """Test cases for RemediationGenerator class."""

    def test_generator_initialization(self) -> None:
        """Test that RemediationGenerator initializes correctly."""
        generator = RemediationGenerator()
        assert generator is not None

    def test_generate_plan_for_s3_finding(self, sample_finding: Finding) -> None:
        """Test remediation plan generation for S3 finding."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding, prefer_terraform=True)

        assert isinstance(plan, RemediationPlan)
        assert plan.finding_id == str(sample_finding.finding_id)
        assert len(plan.steps) > 0
        assert plan.total_estimated_time > 0
        assert len(plan.prerequisites) > 0
        assert len(plan.rollback_steps) > 0
        assert len(plan.references) > 0

        # Check that steps are numbered correctly
        for i, step in enumerate(plan.steps, 1):
            assert step.step_number == i

    def test_generate_plan_for_iam_finding(self, critical_finding: Finding) -> None:
        """Test remediation plan generation for IAM finding."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(critical_finding, prefer_terraform=True)

        assert isinstance(plan, RemediationPlan)
        assert plan.finding_id == str(critical_finding.finding_id)
        assert len(plan.steps) > 0

        # IAM changes should have high-risk steps
        high_risk_steps = [s for s in plan.steps if s.risk_level == "high"]
        assert len(high_risk_steps) > 0

    def test_generate_plan_prefer_terraform(self, sample_finding: Finding) -> None:
        """Test that Terraform examples are included when preferred."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding, prefer_terraform=True)

        # Should have at least one terraform command
        terraform_steps = [
            s for s in plan.steps if s.command_type == "terraform"
        ]
        assert len(terraform_steps) > 0

    def test_generate_plan_prefer_aws_cli(self, sample_finding: Finding) -> None:
        """Test that AWS CLI examples are included when preferred."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding, prefer_terraform=False)

        # Should have at least one aws-cli command
        cli_steps = [s for s in plan.steps if s.command_type == "aws-cli"]
        assert len(cli_steps) > 0

    def test_remediation_step_structure(self, sample_finding: Finding) -> None:
        """Test that remediation steps have proper structure."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding)

        for step in plan.steps:
            assert isinstance(step, RemediationStep)
            assert step.step_number > 0
            assert len(step.title) > 0
            assert len(step.description) > 0
            assert step.estimated_time > 0
            assert step.risk_level in ["low", "medium", "high"]

            # Validation should be present
            assert step.validation is not None

    def test_remediation_plan_to_dict(self, sample_finding: Finding) -> None:
        """Test conversion of RemediationPlan to dictionary."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding)
        result = plan.to_dict()

        assert isinstance(result, dict)
        assert "finding_id" in result
        assert "title" in result
        assert "summary" in result
        assert "steps" in result
        assert "total_steps" in result
        assert "total_estimated_time_minutes" in result
        assert "prerequisites" in result
        assert "rollback_steps" in result
        assert "references" in result

        # Check steps are dicts
        assert all(isinstance(s, dict) for s in result["steps"])

    def test_remediation_step_to_dict(self, sample_finding: Finding) -> None:
        """Test conversion of RemediationStep to dictionary."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding)

        if plan.steps:
            step_dict = plan.steps[0].to_dict()

            assert isinstance(step_dict, dict)
            assert "step_number" in step_dict
            assert "title" in step_dict
            assert "description" in step_dict
            assert "command" in step_dict
            assert "command_type" in step_dict
            assert "estimated_time_minutes" in step_dict
            assert "risk_level" in step_dict
            assert "validation" in step_dict

    def test_prerequisites_for_critical_findings(
        self, critical_finding: Finding
    ) -> None:
        """Test that critical findings have appropriate prerequisites."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(critical_finding)

        # Critical findings should require approvals
        prerequisites_text = " ".join(plan.prerequisites).lower()
        assert "approval" in prerequisites_text or "security" in prerequisites_text

    def test_prerequisites_include_permissions(self, sample_finding: Finding) -> None:
        """Test that prerequisites include IAM permissions."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding)

        prerequisites_text = " ".join(plan.prerequisites).lower()
        assert "permission" in prerequisites_text or "iam" in prerequisites_text

    def test_rollback_steps_present(self, sample_finding: Finding) -> None:
        """Test that rollback steps are included."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding)

        assert len(plan.rollback_steps) > 0
        rollback_text = " ".join(plan.rollback_steps).lower()
        assert "backup" in rollback_text or "rollback" in rollback_text or "revert" in rollback_text

    def test_references_include_aws_docs(self, sample_finding: Finding) -> None:
        """Test that references include AWS documentation."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding)

        assert len(plan.references) > 0
        # Parse each reference to check for required AWS documentation domains
        from urllib.parse import urlparse
        allowed_domains = {"docs.aws.amazon.com", "aws.amazon.com"}
        found = any(
            urlparse(ref).netloc in allowed_domains
            for ref in plan.references
        )
        assert found

    def test_s3_specific_remediation(self, sample_finding: Finding) -> None:
        """Test S3-specific remediation steps."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding)

        # Should have steps related to S3 public access block
        steps_text = " ".join(s.description.lower() for s in plan.steps)
        assert "s3" in steps_text
        assert "public" in steps_text or "access" in steps_text

    @pytest.mark.asyncio
    async def test_generate_plans_batch(
        self, multiple_findings: list[Finding]
    ) -> None:
        """Test batch generation of remediation plans."""
        generator = RemediationGenerator()
        plans = await generator.generate_plans_batch(multiple_findings)

        assert len(plans) == len(multiple_findings)
        for plan in plans:
            assert isinstance(plan, RemediationPlan)
            assert len(plan.steps) > 0

    def test_terraform_code_format(self, sample_finding: Finding) -> None:
        """Test that Terraform code is properly formatted."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding, prefer_terraform=True)

        terraform_steps = [
            s for s in plan.steps if s.command_type == "terraform"
        ]

        if terraform_steps:
            # Check for basic Terraform syntax
            for step in terraform_steps:
                if step.command and "resource" in step.command:
                    assert "resource " in step.command
                    assert "{" in step.command
                    assert "}" in step.command

    def test_validation_steps_present(self, sample_finding: Finding) -> None:
        """Test that validation is included for each step."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding)

        validation_count = sum(1 for s in plan.steps if s.validation)
        # Most steps should have validation
        assert validation_count >= len(plan.steps) * 0.8

    def test_estimated_time_reasonable(self, sample_finding: Finding) -> None:
        """Test that estimated times are reasonable."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding)

        # Individual steps should be between 1-60 minutes
        for step in plan.steps:
            assert 1 <= step.estimated_time <= 60

        # Total time should be sum of individual times
        expected_total = sum(s.estimated_time for s in plan.steps)
        assert plan.total_estimated_time == expected_total

    def test_generic_resource_remediation(self, low_severity_finding: Finding) -> None:
        """Test remediation for generic resource types."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(low_severity_finding)

        # Should still generate a valid plan
        assert isinstance(plan, RemediationPlan)
        assert len(plan.steps) > 0
        assert plan.total_estimated_time > 0

    def test_plan_title_descriptive(self, sample_finding: Finding) -> None:
        """Test that plan title is descriptive."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(sample_finding)

        assert "Remediation" in plan.title
        assert len(plan.title) > 10

    def test_plan_summary_includes_severity(self, critical_finding: Finding) -> None:
        """Test that plan summary mentions severity."""
        generator = RemediationGenerator()
        plan = generator.generate_plan(critical_finding)

        assert critical_finding.severity.value in plan.summary.lower()
