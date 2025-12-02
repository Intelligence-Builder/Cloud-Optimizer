"""Document service for upload and validation.

Handles document upload, validation, and storage operations.
"""

import os
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ib_platform.document.models import Document, DocumentStatus

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_TYPES = {"application/pdf", "text/plain"}
STORAGE_BASE_PATH = "/tmp/cloud_optimizer/documents"


class DocumentValidationError(Exception):
    """Raised when document validation fails."""

    pass


class DocumentService:
    """Service for document upload and management."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize document service.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def upload_document(
        self,
        user_id: UUID,
        filename: str,
        content_type: str,
        file_data: BinaryIO,
    ) -> Document:
        """Upload and store a document.

        Args:
            user_id: User ID uploading the document
            filename: Original filename
            content_type: MIME type of the file
            file_data: Binary file data

        Returns:
            Created Document instance

        Raises:
            DocumentValidationError: If validation fails
        """
        # Validate content type
        if content_type not in ALLOWED_TYPES:
            raise DocumentValidationError(
                f"Invalid content type. Allowed: {', '.join(ALLOWED_TYPES)}"
            )

        # Read file data to validate size
        file_content = file_data.read()
        file_size = len(file_content)

        # Validate file size
        if file_size > MAX_FILE_SIZE:
            raise DocumentValidationError(
                f"File size {file_size} exceeds maximum {MAX_FILE_SIZE} bytes"
            )

        if file_size == 0:
            raise DocumentValidationError("File is empty")

        # Create storage directory
        user_dir = Path(STORAGE_BASE_PATH) / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        # Create document record
        document = Document(
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            storage_path="",  # Will be updated after save
            status=DocumentStatus.UPLOADING.value,
        )

        self.session.add(document)
        await self.session.flush()  # Get document_id

        # Save file to storage
        storage_path = user_dir / f"{document.document_id}_{filename}"
        with open(storage_path, "wb") as f:
            f.write(file_content)

        # Update storage path
        document.storage_path = str(storage_path)
        document.status = DocumentStatus.PROCESSING.value

        await self.session.commit()
        await self.session.refresh(document)

        return document

    async def get_document(self, document_id: UUID, user_id: UUID) -> Document | None:
        """Get a document by ID.

        Args:
            document_id: Document ID
            user_id: User ID (for authorization)

        Returns:
            Document if found and belongs to user, None otherwise
        """
        result = await self.session.execute(
            select(Document).where(
                Document.document_id == document_id, Document.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_documents(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Document]:
        """List documents for a user.

        Args:
            user_id: User ID
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of documents
        """
        result = await self.session.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def delete_document(self, document_id: UUID, user_id: UUID) -> bool:
        """Delete a document.

        Args:
            document_id: Document ID
            user_id: User ID (for authorization)

        Returns:
            True if deleted, False if not found
        """
        document = await self.get_document(document_id, user_id)
        if not document:
            return False

        # Delete physical file
        if document.storage_path and os.path.exists(document.storage_path):
            os.remove(document.storage_path)

        # Delete database record
        await self.session.delete(document)
        await self.session.commit()

        return True

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> None:
        """Update document status.

        Args:
            document_id: Document ID
            status: New status
            error_message: Error message if status is FAILED
        """
        result = await self.session.execute(
            select(Document).where(Document.document_id == document_id)
        )
        document = result.scalar_one_or_none()
        if document:
            document.status = status.value
            if error_message:
                document.error_message = error_message
            await self.session.commit()

    async def update_extracted_text(
        self, document_id: UUID, extracted_text: str
    ) -> None:
        """Update extracted text for a document.

        Args:
            document_id: Document ID
            extracted_text: Extracted text content
        """
        result = await self.session.execute(
            select(Document).where(Document.document_id == document_id)
        )
        document = result.scalar_one_or_none()
        if document:
            document.extracted_text = extracted_text
            document.status = DocumentStatus.COMPLETED.value
            await self.session.commit()

    def get_file_content(self, document: Document) -> bytes:
        """Get file content for a document.

        Args:
            document: Document instance

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not os.path.exists(document.storage_path):
            raise FileNotFoundError(f"File not found: {document.storage_path}")

        with open(document.storage_path, "rb") as f:
            return f.read()
