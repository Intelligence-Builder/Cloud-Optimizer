"""Text extraction from documents.

Provides text extraction from PDF and TXT files.
"""

from typing import Protocol

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # type: ignore


class ExtractionError(Exception):
    """Raised when text extraction fails."""

    pass


class TextExtractor:
    """Extract text from various document formats."""

    def extract_text(self, file_path: str, content_type: str) -> str:
        """Extract text from a document.

        Args:
            file_path: Path to the document file
            content_type: MIME type of the document

        Returns:
            Extracted text content

        Raises:
            ExtractionError: If extraction fails
        """
        if content_type == "application/pdf":
            return self._extract_pdf(file_path)
        elif content_type == "text/plain":
            return self._extract_text(file_path)
        else:
            raise ExtractionError(f"Unsupported content type: {content_type}")

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text

        Raises:
            ExtractionError: If extraction fails
        """
        if PdfReader is None:
            raise ExtractionError(
                "pypdf library not installed. Install with: pip install pypdf"
            )

        try:
            reader = PdfReader(file_path)
            text_parts = []

            for page_num, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"--- Page {page_num} ---\n{text}")
                except Exception as e:
                    # Log warning but continue with other pages
                    text_parts.append(
                        f"--- Page {page_num} ---\n[Error extracting page: {e}]"
                    )

            if not text_parts:
                raise ExtractionError("No text could be extracted from PDF")

            return "\n\n".join(text_parts)

        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Failed to extract PDF: {e}") from e

    def _extract_text(self, file_path: str) -> str:
        """Extract text from plain text file.

        Args:
            file_path: Path to text file

        Returns:
            File content

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            # Try UTF-8 first
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                # Fallback to latin-1
                with open(file_path, "r", encoding="latin-1") as f:
                    return f.read()

        except Exception as e:
            raise ExtractionError(f"Failed to extract text: {e}") from e

    def extract_from_bytes(self, content: bytes, content_type: str) -> str:
        """Extract text from bytes content.

        Args:
            content: File content as bytes
            content_type: MIME type of the document

        Returns:
            Extracted text content

        Raises:
            ExtractionError: If extraction fails
        """
        import tempfile

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            return self.extract_text(tmp_path, content_type)
        finally:
            # Clean up temporary file
            import os

            try:
                os.unlink(tmp_path)
            except Exception:
                pass  # Ignore cleanup errors
