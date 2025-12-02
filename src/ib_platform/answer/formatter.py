"""Response formatting utilities.

Provides formatters for consistent response structure with severity indicators,
markdown formatting, and code snippets.
"""

from typing import Any


class ResponseFormatter:
    """Formats responses with consistent structure and styling.

    Provides static methods for formatting security advice, remediation steps,
    findings summaries, and code examples with proper markdown and severity icons.

    Example:
        >>> formatted = ResponseFormatter.format_security_advice(
        ...     content="Enable MFA for all IAM users",
        ...     findings=[finding1, finding2],
        ...     compliance=["CIS", "NIST"],
        ... )
    """

    SEVERITY_ICONS = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
        "info": "ℹ️",
    }

    @staticmethod
    def format_security_advice(
        content: str,
        findings: list[Any] | None = None,
        compliance: list[str] | None = None,
    ) -> str:
        """Format security advice response with optional findings and compliance.

        Args:
            content: Main response content
            findings: Optional list of related findings
            compliance: Optional list of compliance frameworks

        Returns:
            Formatted markdown string

        Example:
            >>> ResponseFormatter.format_security_advice(
            ...     content="Enable MFA",
            ...     findings=[finding],
            ...     compliance=["CIS", "NIST"]
            ... )
        """
        parts = [content]

        if findings:
            parts.append("\n---\n")
            parts.append("## Related Findings\n")
            for f in findings[:3]:  # Show top 3
                severity_icon = ResponseFormatter.get_severity_icon(
                    f.severity.value if hasattr(f.severity, "value") else f.severity
                )
                parts.append(
                    f"- {severity_icon} **[{f.rule_id}]** {f.title} ({f.severity.value.upper() if hasattr(f.severity, 'value') else f.severity.upper()})"
                )

        if compliance:
            parts.append("\n## Compliance Frameworks\n")
            parts.append(", ".join(compliance))

        return "\n".join(parts)

    @staticmethod
    def format_remediation(
        title: str,
        steps: list[str],
        code: str | None = None,
        language: str = "hcl",
    ) -> str:
        """Format remediation guidance with steps and optional code.

        Args:
            title: Remediation title
            steps: List of remediation steps
            code: Optional code example
            language: Code language for syntax highlighting (default: hcl for Terraform)

        Returns:
            Formatted markdown string

        Example:
            >>> ResponseFormatter.format_remediation(
            ...     title="Enable S3 Bucket Encryption",
            ...     steps=["Navigate to S3", "Select bucket", "Enable encryption"],
            ...     code="resource...",
            ...     language="hcl"
            ... )
        """
        parts = [f"## Remediation: {title}\n"]

        parts.append("### Steps:\n")
        for i, step in enumerate(steps, 1):
            parts.append(f"{i}. {step}")

        if code:
            parts.append(f"\n### Code Example ({language}):\n")
            parts.append(f"```{language}")
            parts.append(code)
            parts.append("```")

        return "\n".join(parts)

    @staticmethod
    def format_finding_summary(
        findings: list[Any], max_count: int = 10
    ) -> str:
        """Format summary of findings with severity grouping.

        Args:
            findings: List of findings to summarize
            max_count: Maximum number of findings to include (default: 10)

        Returns:
            Formatted markdown string with findings grouped by severity

        Example:
            >>> summary = ResponseFormatter.format_finding_summary(findings, max_count=5)
        """
        if not findings:
            return "✅ No security findings detected."

        parts = ["## Security Findings Summary\n"]

        # Group by severity
        by_severity: dict[str, list[Any]] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": [],
        }

        for finding in findings[:max_count]:
            severity = (
                finding.severity.value
                if hasattr(finding.severity, "value")
                else finding.severity.lower()
            )
            if severity in by_severity:
                by_severity[severity].append(finding)

        # Display in severity order
        for severity in ["critical", "high", "medium", "low", "info"]:
            findings_list = by_severity[severity]
            if findings_list:
                icon = ResponseFormatter.get_severity_icon(severity)
                parts.append(f"\n### {icon} {severity.upper()} ({len(findings_list)})\n")
                for finding in findings_list:
                    parts.append(f"- **{finding.title}**")
                    parts.append(f"  Service: {finding.service}")
                    parts.append(f"  Resource: {finding.resource_id}")
                    if finding.compliance_frameworks:
                        parts.append(
                            f"  Compliance: {', '.join(finding.compliance_frameworks)}"
                        )
                    parts.append("")

        total_count = len(findings)
        if total_count > max_count:
            parts.append(f"\n*Showing {max_count} of {total_count} findings*")

        return "\n".join(parts)

    @staticmethod
    def format_code_snippet(
        code: str,
        language: str = "bash",
        description: str | None = None,
    ) -> str:
        """Format code snippet with optional description.

        Args:
            code: Code content
            language: Programming language for syntax highlighting
            description: Optional description of what the code does

        Returns:
            Formatted markdown string

        Example:
            >>> ResponseFormatter.format_code_snippet(
            ...     code="aws s3api put-bucket-encryption...",
            ...     language="bash",
            ...     description="Enable S3 bucket encryption"
            ... )
        """
        parts = []

        if description:
            parts.append(f"**{description}**\n")

        parts.append(f"```{language}")
        parts.append(code)
        parts.append("```")

        return "\n".join(parts)

    @staticmethod
    def format_compliance_mapping(
        control_name: str,
        framework: str,
        requirements: list[str],
        implementation: str | None = None,
    ) -> str:
        """Format compliance control mapping.

        Args:
            control_name: Name of the control
            framework: Compliance framework (e.g., CIS, NIST)
            requirements: List of requirements
            implementation: Optional implementation guidance

        Returns:
            Formatted markdown string

        Example:
            >>> ResponseFormatter.format_compliance_mapping(
            ...     control_name="Enable MFA",
            ...     framework="CIS",
            ...     requirements=["MFA for all users", "MFA for console access"],
            ...     implementation="Use AWS IAM to configure MFA"
            ... )
        """
        parts = [f"## {framework}: {control_name}\n"]

        parts.append("### Requirements:\n")
        for req in requirements:
            parts.append(f"- {req}")

        if implementation:
            parts.append("\n### Implementation:\n")
            parts.append(implementation)

        return "\n".join(parts)

    @staticmethod
    def get_severity_icon(severity: str) -> str:
        """Get emoji icon for severity level.

        Args:
            severity: Severity level (critical, high, medium, low, info)

        Returns:
            Emoji icon for the severity

        Example:
            >>> ResponseFormatter.get_severity_icon("critical")
            '🔴'
        """
        return ResponseFormatter.SEVERITY_ICONS.get(severity.lower(), "⚪")

    @staticmethod
    def format_multi_code_example(
        terraform: str | None = None,
        cli: str | None = None,
        console_steps: list[str] | None = None,
    ) -> str:
        """Format multiple code examples (Terraform, CLI, Console).

        Args:
            terraform: Optional Terraform code
            cli: Optional AWS CLI commands
            console_steps: Optional AWS Console steps

        Returns:
            Formatted markdown string with all provided examples

        Example:
            >>> ResponseFormatter.format_multi_code_example(
            ...     terraform="resource...",
            ...     cli="aws s3api...",
            ...     console_steps=["Step 1", "Step 2"]
            ... )
        """
        parts = ["## Implementation Examples\n"]

        if terraform:
            parts.append("### Terraform\n")
            parts.append("```hcl")
            parts.append(terraform)
            parts.append("```\n")

        if cli:
            parts.append("### AWS CLI\n")
            parts.append("```bash")
            parts.append(cli)
            parts.append("```\n")

        if console_steps:
            parts.append("### AWS Console\n")
            for i, step in enumerate(console_steps, 1):
                parts.append(f"{i}. {step}")
            parts.append("")

        return "\n".join(parts)
