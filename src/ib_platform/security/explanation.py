"""Finding explanation service using LLM.

This module provides human-readable explanations for security findings
using Claude AI to generate contextual, accessible descriptions.
"""

import logging
import os
from typing import Any, Dict, Optional

from anthropic import Anthropic

from cloud_optimizer.models.finding import Finding

logger = logging.getLogger(__name__)


class FindingExplainer:
    """Generate human-readable explanations for security findings using Claude.

    This service uses Claude AI to transform technical security findings into
    clear, contextual explanations that are accessible to non-technical stakeholders.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
    ) -> None:
        """Initialize the finding explainer.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use for explanations
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model

        if not self.api_key:
            logger.warning(
                "No Anthropic API key provided. FindingExplainer will be disabled."
            )
            self.client = None
        else:
            self.client = Anthropic(api_key=self.api_key)
            logger.info(f"Initialized FindingExplainer with model {model}")

    def is_available(self) -> bool:
        """Check if the explainer is available.

        Returns:
            True if API key is configured and client is ready
        """
        return self.client is not None

    async def explain_finding(
        self,
        finding: Finding,
        include_technical_details: bool = True,
        target_audience: str = "general",
    ) -> Dict[str, Any]:
        """Generate a human-readable explanation for a finding.

        Args:
            finding: Finding to explain
            include_technical_details: Include technical details in explanation
            target_audience: Target audience level (general, technical, executive)

        Returns:
            Dictionary containing:
                - explanation: Human-readable explanation
                - what_it_means: Plain language summary
                - why_it_matters: Business impact explanation
                - technical_details: Optional technical context
                - model_used: Claude model used
        """
        if not self.is_available():
            return self._generate_fallback_explanation(finding)

        try:
            # Build prompt based on target audience
            prompt = self._build_explanation_prompt(
                finding, include_technical_details, target_audience
            )

            # Call Claude API
            logger.debug(f"Generating explanation for finding {finding.finding_id}")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            explanation_text = response.content[0].text

            # Parse the response into structured format
            parsed = self._parse_explanation(explanation_text)

            logger.info(
                f"Generated explanation for finding {finding.finding_id} "
                f"(audience: {target_audience})"
            )

            return {
                "finding_id": str(finding.finding_id),
                "explanation": parsed.get("explanation", explanation_text),
                "what_it_means": parsed.get("what_it_means", ""),
                "why_it_matters": parsed.get("why_it_matters", ""),
                "technical_details": parsed.get("technical_details", "")
                if include_technical_details
                else None,
                "model_used": self.model,
                "target_audience": target_audience,
            }

        except Exception as e:
            logger.error(
                f"Error generating explanation for finding {finding.finding_id}: {e}"
            )
            return self._generate_fallback_explanation(finding)

    def _build_explanation_prompt(
        self,
        finding: Finding,
        include_technical_details: bool,
        target_audience: str,
    ) -> str:
        """Build the prompt for Claude based on finding and parameters.

        Args:
            finding: Finding to explain
            include_technical_details: Whether to include technical details
            target_audience: Target audience level

        Returns:
            Formatted prompt string
        """
        audience_context = {
            "general": "a general audience with limited technical knowledge",
            "technical": "a technical team with cloud infrastructure experience",
            "executive": "executive leadership focused on business impact",
        }

        compliance_text = ""
        if finding.compliance_frameworks:
            frameworks = ", ".join(finding.compliance_frameworks)
            compliance_text = f"\n- Affects compliance frameworks: {frameworks}"

        prompt = f"""Explain this security finding for {audience_context.get(target_audience, 'a general audience')}:

Title: {finding.title}
Severity: {finding.severity.value}
Resource Type: {finding.resource_type}
Resource ID: {finding.resource_id}
Service: {finding.service}
Description: {finding.description}
Recommendation: {finding.recommendation}{compliance_text}

Please provide:
1. WHAT IT MEANS: A clear, plain-language explanation of what this finding represents
2. WHY IT MATTERS: The business impact and risks if not addressed
{"3. TECHNICAL DETAILS: The technical context and how this issue manifests" if include_technical_details else ""}

Format your response with these exact section headers. Keep the language appropriate for the target audience.
Be concise but thorough - aim for 2-3 sentences per section."""

        return prompt

    def _parse_explanation(self, text: str) -> Dict[str, str]:
        """Parse Claude's response into structured sections.

        Args:
            text: Raw response text from Claude

        Returns:
            Dictionary with parsed sections
        """
        sections = {
            "explanation": "",
            "what_it_means": "",
            "why_it_matters": "",
            "technical_details": "",
        }

        # Simple parsing logic - look for section headers
        current_section = "explanation"
        lines = text.split("\n")

        for line in lines:
            line_lower = line.lower().strip()

            if "what it means" in line_lower:
                current_section = "what_it_means"
                continue
            elif "why it matters" in line_lower:
                current_section = "why_it_matters"
                continue
            elif "technical details" in line_lower:
                current_section = "technical_details"
                continue

            # Add non-empty lines to current section
            if line.strip():
                if sections[current_section]:
                    sections[current_section] += " " + line.strip()
                else:
                    sections[current_section] = line.strip()

        # If no sections were found, put everything in explanation
        if not sections["what_it_means"] and not sections["why_it_matters"]:
            sections["explanation"] = text

        return sections

    def _generate_fallback_explanation(self, finding: Finding) -> Dict[str, Any]:
        """Generate a basic explanation without LLM when unavailable.

        Args:
            finding: Finding to explain

        Returns:
            Dictionary with basic explanation
        """
        severity_impacts = {
            "critical": "immediate security risk requiring urgent attention",
            "high": "significant security risk that should be addressed promptly",
            "medium": "moderate security risk that should be reviewed and fixed",
            "low": "minor security concern that should be addressed when convenient",
            "info": "informational finding for awareness",
        }

        impact = severity_impacts.get(
            finding.severity.value, "security issue requiring attention"
        )

        explanation = (
            f"This is a {finding.severity.value} severity security finding. "
            f"The {finding.resource_type} resource '{finding.resource_id}' has "
            f"a configuration issue that represents {impact}."
        )

        what_it_means = finding.description

        why_it_matters = (
            f"This {finding.severity.value} severity issue could impact your "
            f"security posture and should be reviewed. {finding.recommendation}"
        )

        if finding.compliance_frameworks:
            frameworks = ", ".join(finding.compliance_frameworks)
            why_it_matters += (
                f" This finding also affects compliance with: {frameworks}."
            )

        return {
            "finding_id": str(finding.finding_id),
            "explanation": explanation,
            "what_it_means": what_it_means,
            "why_it_matters": why_it_matters,
            "technical_details": str(finding.evidence) if finding.evidence else None,
            "model_used": "fallback",
            "target_audience": "general",
        }

    async def explain_findings_batch(
        self,
        findings: list[Finding],
        include_technical_details: bool = True,
        target_audience: str = "general",
    ) -> list[Dict[str, Any]]:
        """Generate explanations for multiple findings.

        Args:
            findings: List of findings to explain
            include_technical_details: Include technical details
            target_audience: Target audience level

        Returns:
            List of explanation dictionaries
        """
        logger.info(f"Generating explanations for {len(findings)} findings")

        explanations = []
        for finding in findings:
            explanation = await self.explain_finding(
                finding, include_technical_details, target_audience
            )
            explanations.append(explanation)

        logger.info(f"Completed {len(explanations)} explanations")
        return explanations
