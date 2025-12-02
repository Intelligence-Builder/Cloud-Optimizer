"""Tests for text extraction."""

import tempfile
from pathlib import Path

import pytest

from ib_platform.document.extraction import ExtractionError, TextExtractor


def test_extract_text_from_txt_file(sample_txt_content: bytes):
    """Test extracting text from plain text file."""
    extractor = TextExtractor()

    # Create temporary file
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".txt", delete=False
    ) as tmp_file:
        tmp_file.write(sample_txt_content)
        tmp_path = tmp_file.name

    try:
        # Extract text
        text = extractor.extract_text(tmp_path, "text/plain")

        assert "AWS Security Best Practices" in text
        assert "IAM policies" in text
        assert "CIS AWS Foundations Benchmark" in text

    finally:
        Path(tmp_path).unlink()


def test_extract_text_from_bytes(sample_txt_content: bytes):
    """Test extracting text from bytes content."""
    extractor = TextExtractor()

    text = extractor.extract_from_bytes(sample_txt_content, "text/plain")

    assert "AWS Security Best Practices" in text
    assert len(text) > 0


def test_extract_unsupported_content_type():
    """Test extracting from unsupported content type."""
    extractor = TextExtractor()

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        with pytest.raises(ExtractionError) as exc_info:
            extractor.extract_text(tmp_path, "image/jpeg")

        assert "Unsupported content type" in str(exc_info.value)

    finally:
        Path(tmp_path).unlink()


def test_extract_text_file_not_found():
    """Test extracting from non-existent file."""
    extractor = TextExtractor()

    with pytest.raises(ExtractionError):
        extractor.extract_text("/nonexistent/file.txt", "text/plain")


def test_extract_text_with_encoding():
    """Test extracting text with different encodings."""
    extractor = TextExtractor()

    # Create file with latin-1 encoding
    content = "Test with special chars: café, naïve"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", encoding="latin-1", delete=False
    ) as tmp_file:
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        text = extractor.extract_text(tmp_path, "text/plain")
        assert "Test with special chars" in text

    finally:
        Path(tmp_path).unlink()


@pytest.mark.skipif(
    not hasattr(pytest, "importorskip") or pytest.importorskip("pypdf", reason="pypdf not installed"),
    reason="pypdf not installed",
)
def test_extract_pdf_without_pypdf(monkeypatch):
    """Test PDF extraction when pypdf is not available."""
    extractor = TextExtractor()

    # Mock pypdf as None
    import ib_platform.document.extraction as extraction_module

    original_pdfreader = extraction_module.PdfReader
    extraction_module.PdfReader = None

    try:
        with pytest.raises(ExtractionError) as exc_info:
            extractor.extract_text("/tmp/test.pdf", "application/pdf")

        assert "pypdf library not installed" in str(exc_info.value)

    finally:
        extraction_module.PdfReader = original_pdfreader
