"""System prompts for answer generation.

Contains prompts and templates used by the AnswerService to generate
expert-level security responses.
"""

SECURITY_EXPERT_SYSTEM_PROMPT = """You are a cloud security expert assistant for Cloud Optimizer.
Your role is to provide accurate, actionable security advice for AWS environments.

Key behaviors:
1. Ground advice in specific compliance frameworks (HIPAA, SOC2, PCI-DSS, GDPR, CIS, NIST)
2. Provide specific, actionable remediation steps
3. Include severity assessment when discussing risks
4. Reference the user's actual findings when available
5. Be concise but thorough - prioritize the most important points
6. Use markdown formatting for readability
7. If you're not sure about something, say so

When discussing findings:
- Always mention the compliance frameworks affected
- Provide the specific remediation steps
- Include code snippets (Terraform, CLI, Console steps) when helpful

Format severity indicators:
- 🔴 CRITICAL: Immediate action required
- 🟠 HIGH: Address within 24-48 hours
- 🟡 MEDIUM: Address within 1-2 weeks
- 🟢 LOW: Address in next review cycle

When providing code examples:
- Use Terraform for infrastructure as code
- Use AWS CLI for command-line remediation
- Include console step-by-step instructions when helpful
- Always explain what the code does

Be professional, helpful, and security-focused in all responses."""


def build_context_message(
    question: str,
    kb_entries: list,
    findings: list,
    documents: list,
    conversation_history: list | None = None,
) -> str:
    """Build enriched user message with context.

    Args:
        question: User's question
        kb_entries: Relevant knowledge base entries
        findings: Relevant security findings
        documents: Relevant document context
        conversation_history: Previous conversation messages

    Returns:
        Formatted message string with all context included
    """
    parts = []

    # Add findings context
    if findings:
        parts.append("## Current Security Findings\n")
        for finding in findings[:5]:  # Top 5
            severity_icon = _get_severity_icon(finding.severity.value)
            parts.append(
                f"- {severity_icon} **{finding.title}** ({finding.severity.value.upper()})"
            )
            parts.append(f"  Resource: {finding.resource_id}")
            if finding.compliance_frameworks:
                parts.append(
                    f"  Compliance: {', '.join(finding.compliance_frameworks)}"
                )
            parts.append(f"  Recommendation: {finding.recommendation}\n")

    # Add compliance context
    if kb_entries:
        parts.append("## Relevant Compliance Requirements\n")
        for entry in kb_entries[:5]:
            if entry.framework:
                parts.append(f"- **{entry.framework}**: {entry.control_name}")
            else:
                parts.append(
                    f"- **{entry.service or 'General'}**: {entry.control_name}"
                )
            parts.append(f"  {entry.description[:200]}...")
            if entry.guidance:
                parts.append(f"  Guidance: {entry.guidance[:200]}...\n")

    # Add document context
    if documents:
        parts.append("## Architecture Context\n")
        for doc in documents:
            parts.append(f"From document '{doc.get('filename', 'Unknown')}':")
            parts.append(doc.get("summary", doc.get("content", ""))[:500])
            parts.append("")

    # Add the actual question
    parts.append("## User Question\n")
    parts.append(question)

    return "\n".join(parts)


def _get_severity_icon(severity: str) -> str:
    """Get emoji icon for severity level.

    Args:
        severity: Severity level (critical, high, medium, low, info)

    Returns:
        Emoji icon for the severity
    """
    icons = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
        "info": "ℹ️",
    }
    return icons.get(severity.lower(), "⚪")
