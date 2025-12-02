"""Document analysis using LLM.

Analyzes documents to extract AWS resources, compliance mentions, and security concerns.
"""

import json
from dataclasses import dataclass
from typing import Any

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore

from cloud_optimizer.config import get_settings


@dataclass
class DocumentAnalysisResult:
    """Result of document analysis."""

    aws_resources: list[str]
    compliance_frameworks: list[str]
    security_concerns: list[str]
    key_topics: list[str]
    summary: str


class AnalysisError(Exception):
    """Raised when document analysis fails."""

    pass


class DocumentAnalyzer:
    """Analyze documents using LLM to extract structured information."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize document analyzer.

        Args:
            api_key: Anthropic API key (uses settings if not provided)
        """
        settings = get_settings()
        self.api_key = api_key or settings.anthropic_api_key

        if not self.api_key:
            raise AnalysisError("Anthropic API key not configured")

        if anthropic is None:
            raise AnalysisError(
                "anthropic library not installed. Install with: pip install anthropic"
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)

    async def analyze_document(self, text: str) -> DocumentAnalysisResult:
        """Analyze document text to extract structured information.

        Args:
            text: Document text content

        Returns:
            Analysis result with extracted information

        Raises:
            AnalysisError: If analysis fails
        """
        if not text or len(text.strip()) < 10:
            raise AnalysisError("Document text is too short to analyze")

        # Truncate very long documents (Claude has token limits)
        max_chars = 100000  # ~25k tokens
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Document truncated for analysis]"

        prompt = self._build_analysis_prompt(text)

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            result_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    result_text += block.text

            # Parse JSON response
            return self._parse_analysis_result(result_text)

        except Exception as e:
            raise AnalysisError(f"Failed to analyze document: {e}") from e

    def _build_analysis_prompt(self, text: str) -> str:
        """Build analysis prompt for LLM.

        Args:
            text: Document text

        Returns:
            Formatted prompt
        """
        return f"""Analyze the following document and extract structured information.

Document:
{text}

Please analyze this document and provide the following information in JSON format:

1. AWS Resources: List all AWS services, resources, or product names mentioned (e.g., EC2, S3, Lambda, RDS)
2. Compliance Frameworks: List any compliance frameworks mentioned (e.g., HIPAA, PCI-DSS, SOC 2, GDPR, CIS)
3. Security Concerns: List any security issues, vulnerabilities, or concerns mentioned
4. Key Topics: List the main topics or themes discussed in the document
5. Summary: Provide a brief 2-3 sentence summary of the document

Respond ONLY with valid JSON in this exact format:
{{
    "aws_resources": ["service1", "service2"],
    "compliance_frameworks": ["framework1", "framework2"],
    "security_concerns": ["concern1", "concern2"],
    "key_topics": ["topic1", "topic2"],
    "summary": "Brief summary here"
}}

Important:
- Return ONLY the JSON object, no additional text
- If a category has no items, use an empty array []
- Use proper JSON formatting with double quotes
"""

    def _parse_analysis_result(self, result_text: str) -> DocumentAnalysisResult:
        """Parse analysis result from LLM response.

        Args:
            result_text: LLM response text

        Returns:
            Parsed analysis result

        Raises:
            AnalysisError: If parsing fails
        """
        try:
            # Extract JSON from response (in case there's extra text)
            start = result_text.find("{")
            end = result_text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON object found in response")

            json_str = result_text[start:end]
            data = json.loads(json_str)

            return DocumentAnalysisResult(
                aws_resources=data.get("aws_resources", []),
                compliance_frameworks=data.get("compliance_frameworks", []),
                security_concerns=data.get("security_concerns", []),
                key_topics=data.get("key_topics", []),
                summary=data.get("summary", ""),
            )

        except Exception as e:
            raise AnalysisError(f"Failed to parse analysis result: {e}") from e

    def extract_entities(self, text: str, entity_type: str) -> list[str]:
        """Extract specific entities from text.

        Args:
            text: Document text
            entity_type: Type of entity to extract (e.g., "aws_resources", "compliance")

        Returns:
            List of extracted entities
        """
        # Simple keyword-based extraction as fallback
        entities = set()

        if entity_type == "aws_resources":
            aws_services = [
                "EC2",
                "S3",
                "Lambda",
                "RDS",
                "DynamoDB",
                "CloudWatch",
                "IAM",
                "VPC",
                "ECS",
                "EKS",
                "CloudFormation",
                "CloudTrail",
                "Config",
                "GuardDuty",
                "SecurityHub",
                "KMS",
                "Secrets Manager",
                "SNS",
                "SQS",
                "API Gateway",
                "Route53",
                "CloudFront",
                "ELB",
                "ALB",
                "NLB",
            ]
            for service in aws_services:
                if service.lower() in text.lower():
                    entities.add(service)

        elif entity_type == "compliance":
            frameworks = [
                "HIPAA",
                "PCI-DSS",
                "SOC 2",
                "GDPR",
                "CIS",
                "NIST",
                "ISO 27001",
                "FedRAMP",
            ]
            for framework in frameworks:
                if framework.lower() in text.lower():
                    entities.add(framework)

        return sorted(list(entities))
