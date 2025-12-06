"""Tests for document upload service."""

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

from ib_platform.document.models import Document, DocumentStatus
from ib_platform.document.service import (
    ALLOWED_TYPES,
    MAX_FILE_SIZE,
    DocumentService,
    DocumentValidationError,
)


@pytest.mark.asyncio
async def test_upload_valid_text_document(
    db_session, sample_user_id: UUID, sample_txt_content: bytes
):
    """Test uploading a valid text document."""
    service = DocumentService(db_session)

    # Create file-like object
    file_data = io.BytesIO(sample_txt_content)

    # Upload document
    document = await service.upload_document(
        user_id=sample_user_id,
        filename="test.txt",
        content_type="text/plain",
        file_data=file_data,
    )

    assert document.document_id is not None
    assert document.user_id == sample_user_id
    assert document.filename == "test.txt"
    assert document.content_type == "text/plain"
    assert document.file_size == len(sample_txt_content)
    assert document.status == DocumentStatus.PROCESSING.value
    assert Path(document.storage_path).exists()

    # Cleanup
    Path(document.storage_path).unlink()


@pytest.mark.asyncio
async def test_upload_invalid_content_type(db_session, sample_user_id: UUID):
    """Test uploading document with invalid content type."""
    service = DocumentService(db_session)

    file_data = io.BytesIO(b"test content")

    with pytest.raises(DocumentValidationError) as exc_info:
        await service.upload_document(
            user_id=sample_user_id,
            filename="test.jpg",
            content_type="image/jpeg",
            file_data=file_data,
        )

    assert "Invalid content type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_file_too_large(db_session, sample_user_id: UUID):
    """Test uploading file that exceeds size limit."""
    service = DocumentService(db_session)

    # Create file larger than MAX_FILE_SIZE
    large_content = b"x" * (MAX_FILE_SIZE + 1)
    file_data = io.BytesIO(large_content)

    with pytest.raises(DocumentValidationError) as exc_info:
        await service.upload_document(
            user_id=sample_user_id,
            filename="large.txt",
            content_type="text/plain",
            file_data=file_data,
        )

    assert "exceeds maximum" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_empty_file(db_session, sample_user_id: UUID):
    """Test uploading empty file."""
    service = DocumentService(db_session)

    file_data = io.BytesIO(b"")

    with pytest.raises(DocumentValidationError) as exc_info:
        await service.upload_document(
            user_id=sample_user_id,
            filename="empty.txt",
            content_type="text/plain",
            file_data=file_data,
        )

    assert "empty" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_document(
    db_session, sample_user_id: UUID, sample_document: Document
):
    """Test retrieving a document."""
    service = DocumentService(db_session)

    # Add document to session
    db_session.add(sample_document)
    await db_session.commit()

    # Get document
    retrieved = await service.get_document(sample_document.document_id, sample_user_id)

    assert retrieved is not None
    assert retrieved.document_id == sample_document.document_id
    assert retrieved.filename == sample_document.filename


@pytest.mark.asyncio
async def test_get_document_not_found(db_session, sample_user_id: UUID):
    """Test retrieving non-existent document."""
    from uuid import uuid4

    service = DocumentService(db_session)

    retrieved = await service.get_document(uuid4(), sample_user_id)

    assert retrieved is None


@pytest.mark.asyncio
async def test_get_document_wrong_user(db_session, sample_document: Document):
    """Test retrieving document with wrong user ID."""
    from uuid import uuid4

    service = DocumentService(db_session)

    # Add document to session
    db_session.add(sample_document)
    await db_session.commit()

    # Try to get with different user_id
    retrieved = await service.get_document(sample_document.document_id, uuid4())

    assert retrieved is None


@pytest.mark.asyncio
async def test_list_documents(db_session, sample_user_id: UUID):
    """Test listing documents for a user."""
    from uuid import uuid4

    service = DocumentService(db_session)
    base_time = datetime.now(timezone.utc)

    # Create multiple documents
    for i in range(3):
        doc = Document(
            document_id=uuid4(),
            user_id=sample_user_id,
            filename=f"test_{i}.txt",
            content_type="text/plain",
            file_size=100 * i,
            storage_path=f"/tmp/test_{i}.txt",
            status=DocumentStatus.COMPLETED.value,
            created_at=base_time + timedelta(seconds=i),
            updated_at=base_time + timedelta(seconds=i),
        )
        db_session.add(doc)

    await db_session.commit()

    # List documents
    documents = await service.list_documents(sample_user_id, limit=10, offset=0)

    assert len(documents) == 3
    # Should be ordered by created_at desc (most recent first)
    assert documents[0].filename == "test_2.txt"


@pytest.mark.asyncio
async def test_update_status(db_session, sample_document: Document):
    """Test updating document status."""
    service = DocumentService(db_session)

    # Add document
    db_session.add(sample_document)
    await db_session.commit()

    # Update status
    await service.update_status(
        sample_document.document_id,
        DocumentStatus.FAILED,
        error_message="Test error",
    )

    # Verify update
    await db_session.refresh(sample_document)
    assert sample_document.status == DocumentStatus.FAILED.value
    assert sample_document.error_message == "Test error"


@pytest.mark.asyncio
async def test_update_extracted_text(db_session, sample_document: Document):
    """Test updating extracted text."""
    service = DocumentService(db_session)

    # Add document
    sample_document.extracted_text = None
    sample_document.status = DocumentStatus.PROCESSING.value
    db_session.add(sample_document)
    await db_session.commit()

    # Update extracted text
    extracted = "This is the extracted text content"
    await service.update_extracted_text(sample_document.document_id, extracted)

    # Verify update
    await db_session.refresh(sample_document)
    assert sample_document.extracted_text == extracted
    assert sample_document.status == DocumentStatus.COMPLETED.value
