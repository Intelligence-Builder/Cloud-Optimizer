"""Document context for chat integration.

Provides relevant document chunks to enhance chat responses.
"""

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ib_platform.document.models import Document, DocumentStatus


@dataclass
class DocumentChunk:
    """A chunk of text from a document."""

    document_id: UUID
    filename: str
    content: str
    relevance_score: float


class DocumentContext:
    """Provide document context for chat queries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize document context.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def get_relevant_chunks(
        self, user_id: UUID, query: str, max_chunks: int = 3
    ) -> list[DocumentChunk]:
        """Get relevant document chunks for a query.

        Args:
            user_id: User ID
            query: Chat query
            max_chunks: Maximum number of chunks to return

        Returns:
            List of relevant document chunks
        """
        # Get all completed documents for user
        result = await self.session.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.status == DocumentStatus.COMPLETED.value,
                Document.extracted_text.isnot(None),
            )
        )
        documents = result.scalars().all()

        if not documents:
            return []

        # Score and rank chunks
        chunks = []
        for doc in documents:
            if not doc.extracted_text:
                continue

            # Split document into chunks
            doc_chunks = self._split_into_chunks(doc.extracted_text)

            # Score each chunk
            for chunk_text in doc_chunks:
                score = self._calculate_relevance(query, chunk_text)
                if score > 0:
                    chunks.append(
                        DocumentChunk(
                            document_id=doc.document_id,
                            filename=doc.filename,
                            content=chunk_text,
                            relevance_score=score,
                        )
                    )

        # Sort by relevance and return top chunks
        chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        return chunks[:max_chunks]

    def _split_into_chunks(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> list[str]:
        """Split text into overlapping chunks.

        Args:
            text: Text to split
            chunk_size: Maximum chunk size in characters
            overlap: Overlap size between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for period, question mark, or exclamation
                sentence_end = max(
                    text.rfind(".", start, end),
                    text.rfind("?", start, end),
                    text.rfind("!", start, end),
                )
                if sentence_end > start:
                    end = sentence_end + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = end - overlap if end < len(text) else end

        return chunks

    def _calculate_relevance(self, query: str, chunk: str) -> float:
        """Calculate relevance score between query and chunk.

        Args:
            query: Query text
            chunk: Document chunk

        Returns:
            Relevance score (0-1)
        """
        # Simple keyword matching (could be enhanced with embeddings)
        query_lower = query.lower()
        chunk_lower = chunk.lower()

        # Extract keywords from query (simple word extraction)
        keywords = self._extract_keywords(query_lower)

        if not keywords:
            return 0.0

        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword in chunk_lower)

        # Calculate score (0-1)
        score = matches / len(keywords)

        # Boost score if exact query phrase is found
        if query_lower in chunk_lower:
            score = min(1.0, score + 0.3)

        return score

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            List of keywords
        """
        # Remove common stop words
        stop_words = {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "has",
            "he",
            "in",
            "is",
            "it",
            "its",
            "of",
            "on",
            "that",
            "the",
            "to",
            "was",
            "will",
            "with",
            "what",
            "where",
            "when",
            "how",
            "why",
            "which",
        }

        # Extract words (alphanumeric + hyphen)
        words = re.findall(r"[a-z0-9-]+", text.lower())

        # Filter stop words and short words
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]

        return keywords

    async def get_document_summary(self, user_id: UUID) -> dict[str, Any]:
        """Get summary of user's documents.

        Args:
            user_id: User ID

        Returns:
            Document summary statistics
        """
        result = await self.session.execute(
            select(Document).where(Document.user_id == user_id)
        )
        documents = result.scalars().all()

        total_docs = len(documents)
        completed = sum(1 for d in documents if d.status == DocumentStatus.COMPLETED.value)
        processing = sum(
            1 for d in documents if d.status == DocumentStatus.PROCESSING.value
        )
        failed = sum(1 for d in documents if d.status == DocumentStatus.FAILED.value)
        total_size = sum(d.file_size for d in documents)

        return {
            "total_documents": total_docs,
            "completed": completed,
            "processing": processing,
            "failed": failed,
            "total_size_bytes": total_size,
            "documents": [
                {
                    "document_id": str(d.document_id),
                    "filename": d.filename,
                    "status": d.status,
                    "created_at": d.created_at.isoformat(),
                }
                for d in documents
            ],
        }
