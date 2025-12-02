"""Tests for finding explanation generation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cloud_optimizer.models.finding import Finding
from ib_platform.security.explanation import FindingExplainer


class TestFindingExplainer:
    """Test cases for FindingExplainer class."""

    def test_explainer_initialization_without_api_key(self) -> None:
        """Test that explainer initializes without API key (fallback mode)."""
        with patch.dict("os.environ", {}, clear=True):
            explainer = FindingExplainer()
            assert explainer is not None
            assert not explainer.is_available()
            assert explainer.client is None

    def test_explainer_initialization_with_api_key(self) -> None:
        """Test that explainer initializes with API key."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            explainer = FindingExplainer()
            assert explainer is not None
            assert explainer.is_available()
            assert explainer.client is not None

    def test_explainer_initialization_with_explicit_key(self) -> None:
        """Test that explainer accepts explicit API key."""
        explainer = FindingExplainer(api_key="explicit-test-key")
        assert explainer.is_available()
        assert explainer.client is not None

    @pytest.mark.asyncio
    async def test_explain_finding_fallback_mode(
        self, sample_finding: Finding
    ) -> None:
        """Test that fallback explanation works without API key."""
        explainer = FindingExplainer()  # No API key
        explanation = await explainer.explain_finding(sample_finding)

        assert explanation is not None
        assert "finding_id" in explanation
        assert "explanation" in explanation
        assert "what_it_means" in explanation
        assert "why_it_matters" in explanation
        assert explanation["model_used"] == "fallback"
        assert explanation["target_audience"] == "general"

        # Check content quality
        assert len(explanation["explanation"]) > 0
        assert sample_finding.severity.value in explanation["explanation"]

    @pytest.mark.asyncio
    async def test_explain_finding_with_llm(self, sample_finding: Finding) -> None:
        """Test explanation generation with mocked LLM."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""
WHAT IT MEANS: The S3 bucket has public access enabled, allowing anyone on the internet to potentially view or download files.

WHY IT MATTERS: This creates a significant data exposure risk and could lead to data breaches, regulatory violations, and unauthorized access to sensitive information.

TECHNICAL DETAILS: The bucket policy or ACL configuration allows public read access, which is explicitly flagged by AWS security tools.
"""
            )
        ]

        with patch("ib_platform.security.explanation.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            explainer = FindingExplainer(api_key="test-key")
            explanation = await explainer.explain_finding(
                sample_finding,
                include_technical_details=True,
                target_audience="general",
            )

            assert explanation is not None
            assert explanation["model_used"] != "fallback"
            assert "what_it_means" in explanation
            assert "why_it_matters" in explanation
            assert "technical_details" in explanation
            assert len(explanation["what_it_means"]) > 0
            assert len(explanation["why_it_matters"]) > 0

    @pytest.mark.asyncio
    async def test_explain_finding_technical_audience(
        self, sample_finding: Finding
    ) -> None:
        """Test explanation for technical audience."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="WHAT IT MEANS: Technical explanation here. WHY IT MATTERS: Impact details."
            )
        ]

        with patch("ib_platform.security.explanation.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            explainer = FindingExplainer(api_key="test-key")
            explanation = await explainer.explain_finding(
                sample_finding,
                target_audience="technical",
            )

            assert explanation["target_audience"] == "technical"

    @pytest.mark.asyncio
    async def test_explain_finding_executive_audience(
        self, sample_finding: Finding
    ) -> None:
        """Test explanation for executive audience."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="WHAT IT MEANS: Business impact. WHY IT MATTERS: Strategic concerns."
            )
        ]

        with patch("ib_platform.security.explanation.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            explainer = FindingExplainer(api_key="test-key")
            explanation = await explainer.explain_finding(
                sample_finding,
                target_audience="executive",
                include_technical_details=False,
            )

            assert explanation["target_audience"] == "executive"
            # Executive explanations shouldn't include technical details
            assert explanation.get("technical_details") is None

    @pytest.mark.asyncio
    async def test_explain_finding_with_compliance(
        self, sample_finding: Finding
    ) -> None:
        """Test that compliance frameworks are mentioned in explanation."""
        explainer = FindingExplainer()  # Fallback mode
        explanation = await explainer.explain_finding(sample_finding)

        # Sample finding has PCI-DSS and HIPAA
        assert (
            "PCI-DSS" in explanation["why_it_matters"]
            or "HIPAA" in explanation["why_it_matters"]
        )

    @pytest.mark.asyncio
    async def test_explain_findings_batch(
        self, multiple_findings: list[Finding]
    ) -> None:
        """Test batch explanation generation."""
        explainer = FindingExplainer()  # Fallback mode
        explanations = await explainer.explain_findings_batch(
            multiple_findings,
            target_audience="general",
        )

        assert len(explanations) == len(multiple_findings)
        for explanation in explanations:
            assert "finding_id" in explanation
            assert "explanation" in explanation
            assert "what_it_means" in explanation
            assert "why_it_matters" in explanation

    @pytest.mark.asyncio
    async def test_explain_finding_error_handling(
        self, sample_finding: Finding
    ) -> None:
        """Test that errors fall back to non-LLM explanation."""
        with patch("ib_platform.security.explanation.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(
                side_effect=Exception("API Error")
            )
            mock_anthropic.return_value = mock_client

            explainer = FindingExplainer(api_key="test-key")
            explanation = await explainer.explain_finding(sample_finding)

            # Should fall back to non-LLM explanation
            assert explanation is not None
            assert explanation["model_used"] == "fallback"
            assert "explanation" in explanation

    def test_parse_explanation_with_sections(self) -> None:
        """Test parsing of structured explanation."""
        explainer = FindingExplainer()

        text = """
WHAT IT MEANS: This is the explanation of what it means.

WHY IT MATTERS: This is why it matters for the business.

TECHNICAL DETAILS: These are the technical details.
"""

        parsed = explainer._parse_explanation(text)

        assert "what_it_means" in parsed
        assert "why_it_matters" in parsed
        assert "technical_details" in parsed
        assert len(parsed["what_it_means"]) > 0
        assert len(parsed["why_it_matters"]) > 0
        assert len(parsed["technical_details"]) > 0

    def test_parse_explanation_without_sections(self) -> None:
        """Test parsing of unstructured explanation."""
        explainer = FindingExplainer()

        text = "This is a plain explanation without sections."

        parsed = explainer._parse_explanation(text)

        # Should put everything in explanation
        assert parsed["explanation"] == text

    def test_build_explanation_prompt(self, sample_finding: Finding) -> None:
        """Test that prompt is built correctly."""
        explainer = FindingExplainer()

        prompt = explainer._build_explanation_prompt(
            sample_finding,
            include_technical_details=True,
            target_audience="general",
        )

        assert isinstance(prompt, str)
        assert sample_finding.title in prompt
        assert sample_finding.severity.value in prompt
        assert sample_finding.resource_type in prompt
        assert sample_finding.description in prompt
        assert sample_finding.recommendation in prompt

        # Should include compliance frameworks
        assert "PCI-DSS" in prompt or "HIPAA" in prompt

    def test_build_explanation_prompt_without_technical(
        self, sample_finding: Finding
    ) -> None:
        """Test prompt without technical details."""
        explainer = FindingExplainer()

        prompt = explainer._build_explanation_prompt(
            sample_finding,
            include_technical_details=False,
            target_audience="executive",
        )

        assert "TECHNICAL DETAILS" not in prompt
        assert "executive leadership" in prompt.lower()

    def test_fallback_explanation_content(self, critical_finding: Finding) -> None:
        """Test that fallback explanation has appropriate content."""
        explainer = FindingExplainer()

        fallback = explainer._generate_fallback_explanation(critical_finding)

        assert fallback["finding_id"] == str(critical_finding.finding_id)
        assert critical_finding.severity.value in fallback["explanation"]
        assert critical_finding.resource_type in fallback["explanation"]
        assert len(fallback["what_it_means"]) > 0
        assert len(fallback["why_it_matters"]) > 0

        # Critical findings should mention urgency
        assert (
            "critical" in fallback["why_it_matters"].lower()
            or "urgent" in fallback["why_it_matters"].lower()
        )

    def test_is_available_method(self) -> None:
        """Test is_available method."""
        # Without API key
        explainer_no_key = FindingExplainer()
        assert not explainer_no_key.is_available()

        # With API key
        explainer_with_key = FindingExplainer(api_key="test-key")
        assert explainer_with_key.is_available()
