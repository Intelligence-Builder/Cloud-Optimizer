"""Pydantic schemas for document API endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response for document upload."""

    document_id: UUID = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the document")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Processing status")
    created_at: datetime = Field(..., description="Upload timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True


class DocumentListItem(BaseModel):
    """Document list item."""

    document_id: UUID = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Processing status")
    created_at: datetime = Field(..., description="Upload timestamp")
    has_extracted_text: bool = Field(..., description="Whether text has been extracted")

    class Config:
        """Pydantic config."""

        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response for document list."""

    documents: list[DocumentListItem] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class DocumentDetailResponse(BaseModel):
    """Response for document detail."""

    document_id: UUID = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Processing status")
    extracted_text: str | None = Field(None, description="Extracted text content")
    error_message: str | None = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic config."""

        from_attributes = True


class DocumentAnalysisResponse(BaseModel):
    """Response for document analysis."""

    aws_resources: list[str] = Field(..., description="AWS resources mentioned")
    compliance_frameworks: list[str] = Field(
        ..., description="Compliance frameworks mentioned"
    )
    security_concerns: list[str] = Field(
        ..., description="Security concerns identified"
    )
    key_topics: list[str] = Field(..., description="Key topics discussed")
    summary: str = Field(..., description="Document summary")


class DocumentContextResponse(BaseModel):
    """Response for document context query."""

    chunks: list[dict] = Field(..., description="Relevant document chunks")
    total_chunks: int = Field(..., description="Total number of chunks found")


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str = Field(..., description="Error detail message")
