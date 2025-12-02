"""Tests for document context."""

from uuid import UUID, uuid4

import pytest

from ib_platform.document.context import DocumentContext
from ib_platform.document.models import Document, DocumentStatus


@pytest.mark.asyncio
async def test_get_relevant_chunks_no_documents(db_session, sample_user_id: UUID):
    """Test getting relevant chunks when no documents exist."""
    context = DocumentContext(db_session)

    chunks = await context.get_relevant_chunks(
        sample_user_id, "AWS security best practices"
    )

    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_get_relevant_chunks_with_documents(db_session, sample_user_id: UUID):
    """Test getting relevant chunks from documents."""
    context = DocumentContext(db_session)

    # Add document with extracted text
    doc = Document(
        document_id=uuid4(),
        user_id=sample_user_id,
        filename="security_guide.txt",
        content_type="text/plain",
        file_size=500,
        storage_path="/tmp/security_guide.txt",
        status=DocumentStatus.COMPLETED.value,
        extracted_text="""
        AWS Security Best Practices

        This document covers security best practices for AWS.

        IAM Policies:
        Always use least privilege when creating IAM policies.
        Avoid using wildcards in policy statements.

        S3 Buckets:
        Enable encryption at rest for all S3 buckets.
        Use bucket policies to restrict access.
        """,
    )
    db_session.add(doc)
    await db_session.commit()

    # Query for relevant chunks
    chunks = await context.get_relevant_chunks(
        sample_user_id, "IAM policy best practices", max_chunks=3
    )

    assert len(chunks) > 0
    # Should find chunk containing IAM information
    assert any("IAM" in chunk.content for chunk in chunks)
    # Chunks should have relevance scores
    assert all(chunk.relevance_score > 0 for chunk in chunks)


@pytest.mark.asyncio
async def test_get_relevant_chunks_only_completed(db_session, sample_user_id: UUID):
    """Test that only completed documents are included."""
    context = DocumentContext(db_session)

    # Add processing document
    processing_doc = Document(
        document_id=uuid4(),
        user_id=sample_user_id,
        filename="processing.txt",
        content_type="text/plain",
        file_size=100,
        storage_path="/tmp/processing.txt",
        status=DocumentStatus.PROCESSING.value,
        extracted_text="This should not be found",
    )

    # Add completed document
    completed_doc = Document(
        document_id=uuid4(),
        user_id=sample_user_id,
        filename="completed.txt",
        content_type="text/plain",
        file_size=100,
        storage_path="/tmp/completed.txt",
        status=DocumentStatus.COMPLETED.value,
        extracted_text="AWS security information",
    )

    db_session.add(processing_doc)
    db_session.add(completed_doc)
    await db_session.commit()

    chunks = await context.get_relevant_chunks(sample_user_id, "AWS security")

    # Should only find chunk from completed document
    assert len(chunks) > 0
    assert all("processing" not in chunk.content.lower() for chunk in chunks)


def test_split_into_chunks():
    """Test splitting text into chunks."""
    context = DocumentContext.__new__(DocumentContext)

    # Short text (no splitting needed)
    short_text = "This is a short text."
    chunks = context._split_into_chunks(short_text, chunk_size=1000)

    assert len(chunks) == 1
    assert chunks[0] == short_text

    # Long text (needs splitting)
    long_text = "Sentence one. " * 100  # Long repeated text
    chunks = context._split_into_chunks(long_text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    # Chunks should overlap
    assert len(chunks[0]) <= 120  # chunk_size + some for sentence boundary


def test_calculate_relevance():
    """Test calculating relevance score."""
    context = DocumentContext.__new__(DocumentContext)

    # High relevance (exact match)
    score = context._calculate_relevance(
        "AWS security", "This document discusses AWS security best practices"
    )
    assert score > 0.5

    # Low relevance (no match)
    score = context._calculate_relevance(
        "AWS security", "This is about cooking recipes"
    )
    assert score == 0.0

    # Partial match
    score = context._calculate_relevance(
        "AWS IAM policies", "IAM best practices for cloud security"
    )
    assert 0.0 < score < 1.0


def test_extract_keywords():
    """Test extracting keywords from text."""
    context = DocumentContext.__new__(DocumentContext)

    text = "AWS security best practices for IAM policies and S3 buckets"
    keywords = context._extract_keywords(text)

    # Should include meaningful words
    assert "aws" in keywords
    assert "security" in keywords
    assert "iam" in keywords
    assert "policies" in keywords
    assert "buckets" in keywords

    # Should not include stop words
    assert "the" not in keywords
    assert "and" not in keywords
    assert "for" not in keywords


@pytest.mark.asyncio
async def test_get_document_summary(db_session, sample_user_id: UUID):
    """Test getting document summary."""
    context = DocumentContext(db_session)

    # Add various documents
    completed = Document(
        document_id=uuid4(),
        user_id=sample_user_id,
        filename="completed.txt",
        content_type="text/plain",
        file_size=1000,
        storage_path="/tmp/completed.txt",
        status=DocumentStatus.COMPLETED.value,
    )

    processing = Document(
        document_id=uuid4(),
        user_id=sample_user_id,
        filename="processing.txt",
        content_type="text/plain",
        file_size=2000,
        storage_path="/tmp/processing.txt",
        status=DocumentStatus.PROCESSING.value,
    )

    failed = Document(
        document_id=uuid4(),
        user_id=sample_user_id,
        filename="failed.txt",
        content_type="text/plain",
        file_size=500,
        storage_path="/tmp/failed.txt",
        status=DocumentStatus.FAILED.value,
    )

    db_session.add(completed)
    db_session.add(processing)
    db_session.add(failed)
    await db_session.commit()

    summary = await context.get_document_summary(sample_user_id)

    assert summary["total_documents"] == 3
    assert summary["completed"] == 1
    assert summary["processing"] == 1
    assert summary["failed"] == 1
    assert summary["total_size_bytes"] == 3500
    assert len(summary["documents"]) == 3


@pytest.mark.asyncio
async def test_get_document_summary_empty(db_session, sample_user_id: UUID):
    """Test getting summary when no documents exist."""
    context = DocumentContext(db_session)

    summary = await context.get_document_summary(sample_user_id)

    assert summary["total_documents"] == 0
    assert summary["completed"] == 0
    assert summary["processing"] == 0
    assert summary["failed"] == 0
    assert summary["total_size_bytes"] == 0
    assert summary["documents"] == []
