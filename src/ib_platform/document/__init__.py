"""Document analysis module for Intelligence-Builder platform.

This module provides document upload, text extraction, and analysis capabilities
for Cloud Optimizer chat integration.
"""

from ib_platform.document.analysis import DocumentAnalyzer
from ib_platform.document.context import DocumentContext
from ib_platform.document.extraction import TextExtractor
from ib_platform.document.models import Document
from ib_platform.document.service import DocumentService

__all__ = [
    "Document",
    "DocumentService",
    "TextExtractor",
    "DocumentAnalyzer",
    "DocumentContext",
]
