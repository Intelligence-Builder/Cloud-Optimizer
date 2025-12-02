# Document Analysis Module

Document upload, text extraction, and analysis for Cloud Optimizer chat integration.

## Overview

The Document Analysis module provides comprehensive document handling capabilities for the Cloud Optimizer platform, enabling users to upload documents (PDF, TXT) that can be analyzed and integrated into chat contexts.

## Components

### 1. Document Model (`models.py`)

SQLAlchemy model for document storage:

- **Fields:**
  - `document_id`: UUID primary key
  - `user_id`: Foreign key to users table
  - `filename`: Original filename
  - `content_type`: MIME type (application/pdf, text/plain)
  - `file_size`: Size in bytes
  - `storage_path`: File system storage path
  - `extracted_text`: Extracted text content
  - `status`: Processing status (uploading, processing, completed, failed)
  - `error_message`: Error details if failed
  - `created_at`, `updated_at`: Timestamps

### 2. Document Service (`service.py`)

Upload and management service:

- **Constants:**
  - `MAX_FILE_SIZE`: 10MB (10 * 1024 * 1024 bytes)
  - `ALLOWED_TYPES`: ["application/pdf", "text/plain"]
  - `STORAGE_BASE_PATH`: "/tmp/cloud_optimizer/documents"

- **Methods:**
  - `upload_document()`: Upload and validate document
  - `get_document()`: Retrieve document by ID
  - `list_documents()`: List user's documents
  - `delete_document()`: Delete document and file
  - `update_status()`: Update processing status
  - `update_extracted_text()`: Save extracted text
  - `get_file_content()`: Read file content

### 3. Text Extractor (`extraction.py`)

Text extraction from documents:

- **Supported Formats:**
  - PDF: Uses `pypdf` library
  - TXT: Direct file reading with encoding detection

- **Methods:**
  - `extract_text()`: Extract from file path
  - `extract_from_bytes()`: Extract from bytes content

- **Features:**
  - Page-by-page PDF extraction
  - UTF-8 and Latin-1 encoding support
  - Error handling per page

### 4. Document Analyzer (`analysis.py`)

LLM-based document analysis:

- **Analysis Output:**
  - AWS resources mentioned (EC2, S3, Lambda, etc.)
  - Compliance frameworks (HIPAA, PCI-DSS, NIST, etc.)
  - Security concerns identified
  - Key topics discussed
  - Document summary (2-3 sentences)

- **Methods:**
  - `analyze_document()`: Full LLM analysis
  - `extract_entities()`: Keyword-based fallback extraction

- **LLM:** Uses Claude 3.5 Sonnet via Anthropic API

### 5. Document Context (`context.py`)

Chat integration for document context:

- **Methods:**
  - `get_relevant_chunks()`: Find relevant text chunks for query
  - `get_document_summary()`: User's document statistics

- **Features:**
  - Chunking with overlap (1000 chars, 200 char overlap)
  - Keyword-based relevance scoring
  - Sentence boundary detection

## API Endpoints

### POST `/api/v1/documents/upload`

Upload a document for analysis.

**Request:**
- `file`: Multipart file upload (PDF or TXT, max 10MB)

**Response:**
```json
{
  "document_id": "uuid",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "file_size": 1024,
  "status": "processing",
  "created_at": "2025-12-02T07:00:00Z"
}
```

**Status Codes:**
- 201: Document uploaded successfully
- 400: Invalid file (wrong type, empty)
- 413: File too large

### GET `/api/v1/documents/`

List user's documents.

**Query Parameters:**
- `limit`: Max results (default: 50, max: 100)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "documents": [...],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

### GET `/api/v1/documents/{document_id}`

Get document details.

**Response:**
```json
{
  "document_id": "uuid",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "file_size": 1024,
  "status": "completed",
  "extracted_text": "...",
  "error_message": null,
  "created_at": "2025-12-02T07:00:00Z",
  "updated_at": "2025-12-02T07:01:00Z"
}
```

### DELETE `/api/v1/documents/{document_id}`

Delete a document.

**Status Codes:**
- 204: Document deleted
- 404: Document not found

### POST `/api/v1/documents/{document_id}/analyze`

Analyze document with LLM.

**Response:**
```json
{
  "aws_resources": ["EC2", "S3", "Lambda"],
  "compliance_frameworks": ["HIPAA", "PCI-DSS"],
  "security_concerns": ["Unencrypted S3 buckets"],
  "key_topics": ["Security", "Compliance"],
  "summary": "Document discusses AWS security best practices..."
}
```

**Status Codes:**
- 200: Analysis complete
- 400: Analysis failed or text not extracted
- 404: Document not found

## Database Migration

Migration file: `alembic/versions/20251202_0726_b4591d8d37bd_add_documents_table.py`

**Run migration:**
```bash
alembic upgrade head
```

**Rollback migration:**
```bash
alembic downgrade -1
```

## Installation

### Required Dependencies

```bash
pip install pypdf anthropic
```

Or add to `pyproject.toml`:
```toml
[project]
dependencies = [
    ...
    "pypdf>=3.0.0",
    "anthropic>=0.8.0",
]
```

### Environment Variables

```bash
ANTHROPIC_API_KEY=your-api-key-here
```

## Usage Examples

### Upload Document

```python
from fastapi import UploadFile
from ib_platform.document import DocumentService

async with session as db:
    service = DocumentService(db)

    with open("security_guide.pdf", "rb") as f:
        upload_file = UploadFile(
            filename="security_guide.pdf",
            file=f
        )

        document = await service.upload_document(
            user_id=user_id,
            filename=upload_file.filename,
            content_type="application/pdf",
            file_data=upload_file.file
        )
```

### Extract Text

```python
from ib_platform.document import TextExtractor

extractor = TextExtractor()
text = extractor.extract_text(
    "/path/to/document.pdf",
    "application/pdf"
)
```

### Analyze Document

```python
from ib_platform.document import DocumentAnalyzer

analyzer = DocumentAnalyzer(api_key="your-key")
result = await analyzer.analyze_document(extracted_text)

print(f"AWS Resources: {result.aws_resources}")
print(f"Summary: {result.summary}")
```

### Get Relevant Chunks for Chat

```python
from ib_platform.document import DocumentContext

context = DocumentContext(session)
chunks = await context.get_relevant_chunks(
    user_id=user_id,
    query="How do I secure S3 buckets?",
    max_chunks=3
)

for chunk in chunks:
    print(f"[{chunk.filename}] Score: {chunk.relevance_score}")
    print(chunk.content)
```

## Testing

Run the test suite:

```bash
# All document tests
pytest tests/ib_platform/document/

# Specific test files
pytest tests/ib_platform/document/test_upload.py
pytest tests/ib_platform/document/test_extraction.py
pytest tests/ib_platform/document/test_analysis.py
pytest tests/ib_platform/document/test_context.py
```

## Architecture Decisions

### Storage Location

- Files stored in: `/tmp/cloud_optimizer/documents/{user_id}/`
- Filename format: `{document_id}_{original_filename}`
- Production deployment should use persistent storage (S3, etc.)

### Background Processing

- Text extraction runs asynchronously via FastAPI BackgroundTasks
- Prevents blocking upload endpoint
- Status updates tracked in database

### Chunking Strategy

- 1000 character chunks with 200 character overlap
- Preserves sentence boundaries
- Enables context for chat queries

### LLM Analysis

- Uses Claude 3.5 Sonnet for structured extraction
- Temperature 0.0 for consistent results
- Truncates long documents to ~25k tokens
- JSON response format for structured data

## Security Considerations

1. **File Validation:**
   - Content type whitelist
   - File size limits
   - User authorization on all operations

2. **Storage:**
   - User-specific directories
   - Document ownership verification
   - Proper file cleanup on deletion

3. **API Keys:**
   - Anthropic API key from environment
   - Never logged or exposed

## Future Enhancements

1. **Enhanced Analysis:**
   - Vector embeddings for semantic search
   - Multi-document cross-referencing
   - Cost/savings extraction

2. **Additional Formats:**
   - DOCX support
   - CSV/Excel for cost data
   - Image OCR

3. **Storage:**
   - S3 backend option
   - Configurable storage path
   - Document versioning

4. **Performance:**
   - Caching for analysis results
   - Parallel text extraction
   - Incremental chunking
