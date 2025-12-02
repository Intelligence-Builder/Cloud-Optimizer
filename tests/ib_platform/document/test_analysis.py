"""Tests for document analysis."""

import pytest

from ib_platform.document.analysis import AnalysisError, DocumentAnalyzer


def test_extract_entities_aws_resources(sample_analysis_text: str):
    """Test extracting AWS resources from text."""
    analyzer = DocumentAnalyzer.__new__(
        DocumentAnalyzer
    )  # Create without __init__ for testing

    resources = analyzer.extract_entities(sample_analysis_text, "aws_resources")

    assert "EC2" in resources
    assert "S3" in resources
    assert "RDS" in resources
    assert "Lambda" in resources
    assert "IAM" in resources


def test_extract_entities_compliance(sample_analysis_text: str):
    """Test extracting compliance frameworks from text."""
    analyzer = DocumentAnalyzer.__new__(DocumentAnalyzer)

    frameworks = analyzer.extract_entities(sample_analysis_text, "compliance")

    assert "HIPAA" in frameworks
    assert "PCI-DSS" in frameworks


def test_extract_entities_no_matches():
    """Test extracting entities when none are found."""
    analyzer = DocumentAnalyzer.__new__(DocumentAnalyzer)

    text = "This is a simple document with no AWS resources or compliance mentions."
    resources = analyzer.extract_entities(text, "aws_resources")

    assert len(resources) == 0


def test_analyzer_requires_api_key():
    """Test that analyzer requires API key."""
    # Clear environment
    import os

    old_key = os.environ.get("ANTHROPIC_API_KEY")
    if old_key:
        del os.environ["ANTHROPIC_API_KEY"]

    try:
        with pytest.raises(AnalysisError) as exc_info:
            DocumentAnalyzer()

        assert "API key not configured" in str(exc_info.value)

    finally:
        if old_key:
            os.environ["ANTHROPIC_API_KEY"] = old_key


@pytest.mark.asyncio
async def test_analyze_document_too_short():
    """Test analyzing document that is too short."""
    analyzer = DocumentAnalyzer.__new__(DocumentAnalyzer)
    analyzer.api_key = "test-key"

    with pytest.raises(AnalysisError) as exc_info:
        await analyzer.analyze_document("short")

    assert "too short" in str(exc_info.value)


def test_build_analysis_prompt():
    """Test building analysis prompt."""
    analyzer = DocumentAnalyzer.__new__(DocumentAnalyzer)

    text = "Sample document text"
    prompt = analyzer._build_analysis_prompt(text)

    assert "Sample document text" in prompt
    assert "AWS Resources" in prompt
    assert "Compliance Frameworks" in prompt
    assert "Security Concerns" in prompt
    assert "JSON" in prompt


def test_parse_analysis_result():
    """Test parsing analysis result from JSON."""
    analyzer = DocumentAnalyzer.__new__(DocumentAnalyzer)

    json_response = """{
        "aws_resources": ["EC2", "S3"],
        "compliance_frameworks": ["HIPAA", "PCI-DSS"],
        "security_concerns": ["Overly permissive IAM"],
        "key_topics": ["Security", "Compliance"],
        "summary": "This is a test summary"
    }"""

    result = analyzer._parse_analysis_result(json_response)

    assert result.aws_resources == ["EC2", "S3"]
    assert result.compliance_frameworks == ["HIPAA", "PCI-DSS"]
    assert result.security_concerns == ["Overly permissive IAM"]
    assert result.key_topics == ["Security", "Compliance"]
    assert result.summary == "This is a test summary"


def test_parse_analysis_result_with_extra_text():
    """Test parsing analysis result with extra text around JSON."""
    analyzer = DocumentAnalyzer.__new__(DocumentAnalyzer)

    response = """Here is the analysis:
    {
        "aws_resources": ["Lambda"],
        "compliance_frameworks": [],
        "security_concerns": [],
        "key_topics": ["Serverless"],
        "summary": "Test"
    }
    That's the complete analysis."""

    result = analyzer._parse_analysis_result(response)

    assert result.aws_resources == ["Lambda"]
    assert result.key_topics == ["Serverless"]


def test_parse_analysis_result_invalid_json():
    """Test parsing invalid JSON response."""
    analyzer = DocumentAnalyzer.__new__(DocumentAnalyzer)

    with pytest.raises(AnalysisError):
        analyzer._parse_analysis_result("This is not JSON")


def test_parse_analysis_result_missing_fields():
    """Test parsing JSON with missing fields."""
    analyzer = DocumentAnalyzer.__new__(DocumentAnalyzer)

    json_response = """{
        "aws_resources": ["EC2"],
        "summary": "Test"
    }"""

    result = analyzer._parse_analysis_result(json_response)

    # Should use empty lists for missing fields
    assert result.aws_resources == ["EC2"]
    assert result.compliance_frameworks == []
    assert result.security_concerns == []
    assert result.key_topics == []
    assert result.summary == "Test"
