"""Document API endpoints for Cloud Optimizer.

Implements document upload, listing, retrieval, and analysis.
"""

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from cloud_optimizer.api.schemas.documents import (
    DocumentAnalysisResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    ErrorResponse,
)
from cloud_optimizer.database import AsyncSessionDep
from cloud_optimizer.middleware.auth import CurrentUser, get_current_user
from cloud_optimizer.middleware.trial import (
    RequireDocumentLimit,
    record_trial_usage,
)
from ib_platform.document import (
    DocumentAnalyzer,
    DocumentContext,
    DocumentService,
    TextExtractor,
)
from ib_platform.document.analysis import AnalysisError
from ib_platform.document.extraction import ExtractionError
from ib_platform.document.models import DocumentStatus
from ib_platform.document.service import DocumentValidationError

router = APIRouter()


def get_document_service(db: AsyncSessionDep) -> DocumentService:
    """Dependency to get document service with database session."""
    return DocumentService(db)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


async def process_document_background(
    document_id: UUID, storage_path: str, content_type: str
) -> None:
    """Background task to extract text from document.

    Args:
        document_id: Document ID
        storage_path: Path to stored file
        content_type: MIME type
    """
    from cloud_optimizer.database import get_session_factory

    extractor = TextExtractor()

    async with get_session_factory()() as session:
        service = DocumentService(session)

        try:
            # Extract text
            extracted_text = extractor.extract_text(storage_path, content_type)

            # Update document with extracted text
            await service.update_extracted_text(document_id, extracted_text)

        except ExtractionError as e:
            # Update status to failed
            await service.update_status(
                document_id, DocumentStatus.FAILED, error_message=str(e)
            )
        except Exception as e:
            # Unexpected error
            await service.update_status(
                document_id,
                DocumentStatus.FAILED,
                error_message=f"Unexpected error: {e}",
            )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description="Upload a PDF or TXT document for analysis (max 10MB)",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        413: {"model": ErrorResponse, "description": "File too large"},
    },
)
async def upload_document(
    background_tasks: BackgroundTasks,
    service: DocumentServiceDep,
    user_id: CurrentUser,
    db: AsyncSessionDep,
    file: UploadFile = File(...),
    _document_limit: RequireDocumentLimit = None,
) -> DocumentUploadResponse:
    """Upload a document for analysis."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required"
        )

    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Content type is required"
        )

    try:
        # Upload document
        document = await service.upload_document(
            user_id=user_id,
            filename=file.filename,
            content_type=file.content_type,
            file_data=file.file,
        )

        # Schedule background text extraction
        background_tasks.add_task(
            process_document_background,
            document.document_id,
            document.storage_path,
            document.content_type,
        )

        # Record trial usage after successful document upload
        await record_trial_usage("documents", user_id, db)

        return DocumentUploadResponse(
            document_id=document.document_id,
            filename=document.filename,
            content_type=document.content_type,
            file_size=document.file_size,
            status=document.status,
            created_at=document.created_at,
        )

    except DocumentValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List documents",
    description="Get list of uploaded documents for current user",
)
async def list_documents(
    service: DocumentServiceDep,
    user_id: UUID = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
) -> DocumentListResponse:
    """List documents for current user."""
    if limit > 100:
        limit = 100

    documents = await service.list_documents(user_id, limit=limit, offset=offset)

    # Count total (simplified - would need separate query in production)
    total = len(documents)

    items = [
        {
            "document_id": doc.document_id,
            "filename": doc.filename,
            "content_type": doc.content_type,
            "file_size": doc.file_size,
            "status": doc.status,
            "created_at": doc.created_at,
            "has_extracted_text": doc.extracted_text is not None,
        }
        for doc in documents
    ]

    return DocumentListResponse(
        documents=items, total=total, limit=limit, offset=offset
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details",
    description="Get detailed information about a specific document",
    responses={404: {"model": ErrorResponse, "description": "Document not found"}},
)
async def get_document(
    document_id: UUID,
    service: DocumentServiceDep,
    user_id: UUID = Depends(get_current_user),
) -> DocumentDetailResponse:
    """Get document details."""
    document = await service.get_document(document_id, user_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    return DocumentDetailResponse(
        document_id=document.document_id,
        filename=document.filename,
        content_type=document.content_type,
        file_size=document.file_size,
        status=document.status,
        extracted_text=document.extracted_text,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
    description="Delete a document and its stored file",
    responses={404: {"model": ErrorResponse, "description": "Document not found"}},
)
async def delete_document(
    document_id: UUID,
    service: DocumentServiceDep,
    user_id: UUID = Depends(get_current_user),
) -> None:
    """Delete a document."""
    deleted = await service.delete_document(document_id, user_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )


@router.post(
    "/{document_id}/analyze",
    response_model=DocumentAnalysisResponse,
    summary="Analyze document",
    description="Analyze document with LLM to extract entities and concerns",
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
        400: {"model": ErrorResponse, "description": "Analysis failed"},
    },
)
async def analyze_document(
    document_id: UUID,
    service: DocumentServiceDep,
    user_id: UUID = Depends(get_current_user),
) -> DocumentAnalysisResponse:
    """Analyze document to extract structured information."""
    document = await service.get_document(document_id, user_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    if not document.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text not yet extracted",
        )

    try:
        analyzer = DocumentAnalyzer()
        result = await analyzer.analyze_document(document.extracted_text)

        return DocumentAnalysisResponse(
            aws_resources=result.aws_resources,
            compliance_frameworks=result.compliance_frameworks,
            security_concerns=result.security_concerns,
            key_topics=result.key_topics,
            summary=result.summary,
        )

    except AnalysisError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
