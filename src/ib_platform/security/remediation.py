"""Remediation plan generation for security findings.

This module generates step-by-step remediation plans with code examples
for fixing security findings, including Terraform and AWS CLI commands.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cloud_optimizer.models.finding import Finding, FindingSeverity

logger = logging.getLogger(__name__)


@dataclass
class RemediationStep:
    """A single step in a remediation plan.

    Attributes:
        step_number: Sequential step number
        title: Brief title of the step
        description: Detailed description of what to do
        command: Optional command or code to execute
        command_type: Type of command (terraform, aws-cli, console, manual)
        estimated_time: Estimated time to complete (in minutes)
        risk_level: Risk level of performing this step (low, medium, high)
        validation: How to validate this step was successful
    """

    step_number: int
    title: str
    description: str
    command: Optional[str] = None
    command_type: Optional[str] = None
    estimated_time: int = 5
    risk_level: str = "low"
    validation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with step details
        """
        return {
            "step_number": self.step_number,
            "title": self.title,
            "description": self.description,
            "command": self.command,
            "command_type": self.command_type,
            "estimated_time_minutes": self.estimated_time,
            "risk_level": self.risk_level,
            "validation": self.validation,
        }


@dataclass
class RemediationPlan:
    """Complete remediation plan for a security finding.

    Attributes:
        finding_id: ID of the finding being remediated
        title: Plan title
        summary: Brief summary of the remediation
        steps: List of remediation steps
        total_estimated_time: Total estimated time in minutes
        prerequisites: List of prerequisites before starting
        rollback_steps: Steps to rollback if something goes wrong
        references: Links to documentation and resources
    """

    finding_id: str
    title: str
    summary: str
    steps: List[RemediationStep] = field(default_factory=list)
    total_estimated_time: int = 0
    prerequisites: List[str] = field(default_factory=list)
    rollback_steps: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with plan details
        """
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "summary": self.summary,
            "steps": [step.to_dict() for step in self.steps],
            "total_steps": len(self.steps),
            "total_estimated_time_minutes": self.total_estimated_time,
            "prerequisites": self.prerequisites,
            "rollback_steps": self.rollback_steps,
            "references": self.references,
        }


class RemediationGenerator:
    """Generate remediation plans for security findings.

    This service creates detailed, actionable remediation plans with
    code examples in Terraform and AWS CLI formats.
    """

    def __init__(self) -> None:
        """Initialize the remediation generator."""
        logger.info("Initialized RemediationGenerator")

    def generate_plan(
        self,
        finding: Finding,
        prefer_terraform: bool = True,
    ) -> RemediationPlan:
        """Generate a remediation plan for a finding.

        Args:
            finding: Finding to generate plan for
            prefer_terraform: Prefer Terraform over AWS CLI when both available

        Returns:
            Complete remediation plan
        """
        logger.info(
            f"Generating remediation plan for finding {finding.finding_id} "
            f"(resource_type: {finding.resource_type})"
        )

        # Create plan based on resource type and rule
        plan = self._create_base_plan(finding)

        # Generate specific steps based on resource type
        steps = self._generate_steps_for_resource(
            finding, prefer_terraform=prefer_terraform
        )

        # Calculate total time
        total_time = sum(step.estimated_time for step in steps)

        plan.steps = steps
        plan.total_estimated_time = total_time

        # Add prerequisites
        plan.prerequisites = self._generate_prerequisites(finding)

        # Add rollback steps
        plan.rollback_steps = self._generate_rollback_steps(finding)

        # Add references
        plan.references = self._generate_references(finding)

        logger.info(
            f"Generated remediation plan with {len(steps)} steps, "
            f"estimated time: {total_time} minutes"
        )

        return plan

    def _create_base_plan(self, finding: Finding) -> RemediationPlan:
        """Create base remediation plan structure.

        Args:
            finding: Finding to create plan for

        Returns:
            Base remediation plan
        """
        title = f"Remediation Plan: {finding.title}"
        summary = f"This plan addresses the {finding.severity.value} severity finding: {finding.title}"

        return RemediationPlan(
            finding_id=str(finding.finding_id),
            title=title,
            summary=summary,
        )

    def _generate_steps_for_resource(
        self,
        finding: Finding,
        prefer_terraform: bool = True,
    ) -> List[RemediationStep]:
        """Generate remediation steps based on resource type.

        Args:
            finding: Finding to generate steps for
            prefer_terraform: Prefer Terraform examples

        Returns:
            List of remediation steps
        """
        resource_type = finding.resource_type.lower()

        # Route to specific generators
        if "s3" in resource_type:
            return self._generate_s3_steps(finding, prefer_terraform)
        elif "iam" in resource_type:
            return self._generate_iam_steps(finding, prefer_terraform)
        elif "rds" in resource_type:
            return self._generate_rds_steps(finding, prefer_terraform)
        elif "kms" in resource_type:
            return self._generate_kms_steps(finding, prefer_terraform)
        elif "security" in resource_type or "sg-" in finding.resource_id:
            return self._generate_security_group_steps(finding, prefer_terraform)
        else:
            return self._generate_generic_steps(finding, prefer_terraform)

    def _generate_s3_steps(
        self, finding: Finding, prefer_terraform: bool
    ) -> List[RemediationStep]:
        """Generate steps for S3 bucket findings.

        Args:
            finding: S3-related finding
            prefer_terraform: Prefer Terraform examples

        Returns:
            List of remediation steps
        """
        steps = []

        # Step 1: Review current configuration
        steps.append(
            RemediationStep(
                step_number=1,
                title="Review Current S3 Bucket Configuration",
                description=f"Review the current configuration of bucket {finding.resource_id} to understand the security issue.",
                command=f"aws s3api get-bucket-policy --bucket {finding.resource_id}",
                command_type="aws-cli",
                estimated_time=5,
                risk_level="low",
                validation="Verify you can see the current bucket policy",
            )
        )

        # Step 2: Apply fix
        if prefer_terraform:
            tf_code = f"""resource "aws_s3_bucket_public_access_block" "{finding.resource_id.replace("-", "_")}" {{
  bucket = "{finding.resource_id}"

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}"""
            steps.append(
                RemediationStep(
                    step_number=2,
                    title="Update Terraform Configuration",
                    description="Add or update the S3 bucket public access block configuration in Terraform.",
                    command=tf_code,
                    command_type="terraform",
                    estimated_time=10,
                    risk_level="low",
                    validation="Run terraform plan to verify changes",
                )
            )

            steps.append(
                RemediationStep(
                    step_number=3,
                    title="Apply Terraform Changes",
                    description="Apply the Terraform configuration to update the S3 bucket.",
                    command="terraform apply",
                    command_type="terraform",
                    estimated_time=5,
                    risk_level="medium",
                    validation="Verify bucket policy is updated in AWS Console",
                )
            )
        else:
            steps.append(
                RemediationStep(
                    step_number=2,
                    title="Enable S3 Public Access Block",
                    description="Enable public access block on the S3 bucket to prevent public access.",
                    command=f"""aws s3api put-public-access-block \\
  --bucket {finding.resource_id} \\
  --public-access-block-configuration \\
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" """,
                    command_type="aws-cli",
                    estimated_time=5,
                    risk_level="medium",
                    validation="Run get-public-access-block to verify settings",
                )
            )

        # Step 3: Verify
        steps.append(
            RemediationStep(
                step_number=len(steps) + 1,
                title="Verify Remediation",
                description="Verify that the security issue has been resolved.",
                command=f"aws s3api get-public-access-block --bucket {finding.resource_id}",
                command_type="aws-cli",
                estimated_time=3,
                risk_level="low",
                validation="All four settings should show as 'true'",
            )
        )

        return steps

    def _generate_iam_steps(
        self, finding: Finding, prefer_terraform: bool
    ) -> List[RemediationStep]:
        """Generate steps for IAM findings.

        Args:
            finding: IAM-related finding
            prefer_terraform: Prefer Terraform examples

        Returns:
            List of remediation steps
        """
        steps = []

        steps.append(
            RemediationStep(
                step_number=1,
                title="Review IAM Policy",
                description=f"Review the current IAM policy for {finding.resource_id}.",
                command=f"aws iam get-role-policy --role-name {finding.resource_id} --policy-name <policy-name>",
                command_type="aws-cli",
                estimated_time=5,
                risk_level="low",
                validation="Verify you can see the current policy",
            )
        )

        if prefer_terraform:
            steps.append(
                RemediationStep(
                    step_number=2,
                    title="Update IAM Policy in Terraform",
                    description="Update the IAM policy to follow principle of least privilege.",
                    command="""# Update your Terraform IAM policy
# Remove wildcards and overly permissive actions
# Example:
data "aws_iam_policy_document" "least_privilege" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::specific-bucket/*"
    ]
  }
}""",
                    command_type="terraform",
                    estimated_time=15,
                    risk_level="high",
                    validation="Run terraform plan to review changes",
                )
            )
        else:
            steps.append(
                RemediationStep(
                    step_number=2,
                    title="Update IAM Policy",
                    description="Update the IAM policy with more restrictive permissions.",
                    command="# Review and update policy JSON, then:\naws iam put-role-policy --role-name <role> --policy-name <name> --policy-document file://policy.json",
                    command_type="aws-cli",
                    estimated_time=15,
                    risk_level="high",
                    validation="Test that applications still work with new policy",
                )
            )

        return steps

    def _generate_rds_steps(
        self, finding: Finding, prefer_terraform: bool
    ) -> List[RemediationStep]:
        """Generate steps for RDS findings.

        Args:
            finding: RDS-related finding
            prefer_terraform: Prefer Terraform examples

        Returns:
            List of remediation steps
        """
        steps = []

        steps.append(
            RemediationStep(
                step_number=1,
                title="Review RDS Instance Configuration",
                description=f"Review the configuration of RDS instance {finding.resource_id}.",
                command=f"aws rds describe-db-instances --db-instance-identifier {finding.resource_id}",
                command_type="aws-cli",
                estimated_time=5,
                risk_level="low",
                validation="Verify instance details are returned",
            )
        )

        if "encryption" in finding.title.lower():
            if prefer_terraform:
                steps.append(
                    RemediationStep(
                        step_number=2,
                        title="Enable RDS Encryption in Terraform",
                        description="Update Terraform to enable encryption. Note: Requires creating a new encrypted instance.",
                        command="""resource "aws_db_instance" "encrypted" {
  # ... other configuration ...
  storage_encrypted = true
  kms_key_id       = aws_kms_key.rds.arn
}""",
                        command_type="terraform",
                        estimated_time=30,
                        risk_level="high",
                        validation="Verify encryption is enabled on new instance",
                    )
                )

        return steps

    def _generate_kms_steps(
        self, finding: Finding, prefer_terraform: bool
    ) -> List[RemediationStep]:
        """Generate steps for KMS findings.

        Args:
            finding: KMS-related finding
            prefer_terraform: Prefer Terraform examples

        Returns:
            List of remediation steps
        """
        steps = [
            RemediationStep(
                step_number=1,
                title="Review KMS Key Policy",
                description=f"Review the key policy for {finding.resource_id}.",
                command=f"aws kms get-key-policy --key-id {finding.resource_id} --policy-name default",
                command_type="aws-cli",
                estimated_time=5,
                risk_level="low",
                validation="Verify key policy is returned",
            )
        ]

        return steps

    def _generate_security_group_steps(
        self, finding: Finding, prefer_terraform: bool
    ) -> List[RemediationStep]:
        """Generate steps for Security Group findings.

        Args:
            finding: Security Group finding
            prefer_terraform: Prefer Terraform examples

        Returns:
            List of remediation steps
        """
        steps = [
            RemediationStep(
                step_number=1,
                title="Review Security Group Rules",
                description=f"Review the ingress and egress rules for security group {finding.resource_id}.",
                command=f"aws ec2 describe-security-groups --group-ids {finding.resource_id}",
                command_type="aws-cli",
                estimated_time=5,
                risk_level="low",
                validation="Verify security group rules are listed",
            )
        ]

        if "0.0.0.0/0" in str(finding.evidence) or "public" in finding.title.lower():
            steps.append(
                RemediationStep(
                    step_number=2,
                    title="Remove Overly Permissive Rules",
                    description="Remove or restrict rules that allow access from 0.0.0.0/0.",
                    command=f"aws ec2 revoke-security-group-ingress --group-id {finding.resource_id} --ip-permissions ...",
                    command_type="aws-cli",
                    estimated_time=10,
                    risk_level="medium",
                    validation="Verify overly permissive rules are removed",
                )
            )

        return steps

    def _generate_generic_steps(
        self, finding: Finding, prefer_terraform: bool
    ) -> List[RemediationStep]:
        """Generate generic remediation steps.

        Args:
            finding: Finding to generate steps for
            prefer_terraform: Prefer Terraform examples

        Returns:
            List of generic remediation steps
        """
        return [
            RemediationStep(
                step_number=1,
                title="Review Resource Configuration",
                description=f"Review the configuration of {finding.resource_type} {finding.resource_id}.",
                command=None,
                command_type="console",
                estimated_time=10,
                risk_level="low",
                validation="Understand the current state",
            ),
            RemediationStep(
                step_number=2,
                title="Apply Recommended Fix",
                description=finding.recommendation,
                command=None,
                command_type="manual",
                estimated_time=20,
                risk_level="medium",
                validation="Verify issue is resolved",
            ),
        ]

    def _generate_prerequisites(self, finding: Finding) -> List[str]:
        """Generate prerequisites for remediation.

        Args:
            finding: Finding being remediated

        Returns:
            List of prerequisites
        """
        prerequisites = [
            "AWS CLI configured with appropriate credentials",
            f"Appropriate IAM permissions for {finding.service}",
        ]

        if finding.severity in [FindingSeverity.CRITICAL, FindingSeverity.HIGH]:
            prerequisites.extend(
                [
                    "Approval from security team for high-impact changes",
                    "Change management ticket created and approved",
                    "Backup or snapshot of current configuration",
                ]
            )

        prerequisites.append("Understanding of the resource and its dependencies")

        return prerequisites

    def _generate_rollback_steps(self, finding: Finding) -> List[str]:
        """Generate rollback steps in case of issues.

        Args:
            finding: Finding being remediated

        Returns:
            List of rollback steps
        """
        return [
            "Document current state before making changes",
            "Create backup of existing configuration",
            "Test rollback procedure in non-production environment",
            "Have AWS Console open to manually revert if needed",
            "Keep backup configuration file handy for quick restoration",
        ]

    def _generate_references(self, finding: Finding) -> List[str]:
        """Generate reference documentation links.

        Args:
            finding: Finding being remediated

        Returns:
            List of reference URLs
        """
        resource_type = finding.resource_type.lower()
        references = []

        # AWS documentation
        if "s3" in resource_type:
            references.extend(
                [
                    "https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html",
                    "https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html",
                ]
            )
        elif "iam" in resource_type:
            references.extend(
                [
                    "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html",
                    "https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html",
                ]
            )
        elif "rds" in resource_type:
            references.extend(
                [
                    "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.Security.html",
                    "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html",
                ]
            )

        # Compliance framework references
        if finding.compliance_frameworks:
            references.append("https://aws.amazon.com/compliance/services-in-scope/")

        # General security references
        references.extend(
            [
                "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html",
                "https://docs.aws.amazon.com/security/",
            ]
        )

        return references

    async def generate_plans_batch(
        self,
        findings: List[Finding],
        prefer_terraform: bool = True,
    ) -> List[RemediationPlan]:
        """Generate remediation plans for multiple findings.

        Args:
            findings: List of findings
            prefer_terraform: Prefer Terraform examples

        Returns:
            List of remediation plans
        """
        logger.info(f"Generating remediation plans for {len(findings)} findings")

        plans = [self.generate_plan(finding, prefer_terraform) for finding in findings]

        logger.info(f"Generated {len(plans)} remediation plans")
        return plans
