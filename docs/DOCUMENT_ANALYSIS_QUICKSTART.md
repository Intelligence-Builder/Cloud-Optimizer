# Document Analysis Quick Start Guide

Quick reference for using the Document Analysis module in Cloud Optimizer.

## Installation

```bash
# Install dependencies
pip install pypdf anthropic

# Or using the project
pip install -e .

# Set environment variable
export ANTHROPIC_API_KEY=your-api-key-here
```

## Database Setup

```bash
# Apply migration
alembic upgrade head

# Create storage directory
mkdir -p /tmp/cloud_optimizer/documents
```

## API Usage

### Upload Document

```bash
curl -X POST http://localhost:8080/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@security_guide.pdf"
```

**Response:**
```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "security_guide.pdf",
  "content_type": "application/pdf",
  "file_size": 51200,
  "status": "processing",
  "created_at": "2025-12-02T07:00:00Z"
}
```

### List Documents

```bash
curl http://localhost:8080/api/v1/documents/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Document Details

```bash
curl http://localhost:8080/api/v1/documents/{document_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Analyze Document

```bash
curl -X POST http://localhost:8080/api/v1/documents/{document_id}/analyze \
  -H "Authorization: Bearer YOUR_TOKEN"
```

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

### Delete Document

```bash
curl -X DELETE http://localhost:8080/api/v1/documents/{document_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Python Usage

### Upload and Process

```python
from pathlib import Path
from uuid import UUID
from ib_platform.document import DocumentService, TextExtractor
from cloud_optimizer.database import get_session_factory

async def upload_and_extract(user_id: UUID, file_path: Path):
    """Upload document and extract text."""
    async with get_session_factory()() as session:
        service = DocumentService(session)

        # Upload
        with open(file_path, "rb") as f:
            document = await service.upload_document(
                user_id=user_id,
                filename=file_path.name,
                content_type="application/pdf",
                file_data=f
            )

        # Extract text
        extractor = TextExtractor()
        text = extractor.extract_text(
            document.storage_path,
            document.content_type
        )

        # Save extracted text
        await service.update_extracted_text(
            document.document_id,
            text
        )

        return document
```

### Analyze with LLM

```python
from ib_platform.document import DocumentAnalyzer

async def analyze_document(extracted_text: str):
    """Analyze document with Claude."""
    analyzer = DocumentAnalyzer()  # Uses ANTHROPIC_API_KEY from env

    result = await analyzer.analyze_document(extracted_text)

    print(f"AWS Resources: {result.aws_resources}")
    print(f"Compliance: {result.compliance_frameworks}")
    print(f"Security Concerns: {result.security_concerns}")
    print(f"Summary: {result.summary}")

    return result
```

### Get Context for Chat

```python
from ib_platform.document import DocumentContext

async def get_chat_context(session, user_id: UUID, query: str):
    """Get relevant document chunks for chat query."""
    context = DocumentContext(session)

    chunks = await context.get_relevant_chunks(
        user_id=user_id,
        query=query,
        max_chunks=3
    )

    # Build context string
    context_text = "\n\n".join([
        f"[From {chunk.filename}]\n{chunk.content}"
        for chunk in chunks
    ])

    return context_text
```

### Complete Example

```python
import asyncio
from pathlib import Path
from uuid import uuid4
from cloud_optimizer.database import get_session_factory
from ib_platform.document import (
    DocumentService,
    TextExtractor,
    DocumentAnalyzer,
    DocumentContext
)

async def process_document_complete():
    """Complete document processing workflow."""
    user_id = uuid4()  # Replace with actual user ID

    async with get_session_factory()() as session:
        # 1. Upload
        service = DocumentService(session)
        with open("security_guide.pdf", "rb") as f:
            doc = await service.upload_document(
                user_id=user_id,
                filename="security_guide.pdf",
                content_type="application/pdf",
                file_data=f
            )

        # 2. Extract
        extractor = TextExtractor()
        text = extractor.extract_text(doc.storage_path, doc.content_type)
        await service.update_extracted_text(doc.document_id, text)

        # 3. Analyze
        analyzer = DocumentAnalyzer()
        analysis = await analyzer.analyze_document(text)

        print(f"Analysis Results:")
        print(f"  Resources: {', '.join(analysis.aws_resources)}")
        print(f"  Compliance: {', '.join(analysis.compliance_frameworks)}")
        print(f"  Summary: {analysis.summary}")

        # 4. Get Context
        context = DocumentContext(session)
        chunks = await context.get_relevant_chunks(
            user_id, "S3 bucket security", max_chunks=2
        )

        print(f"\nRelevant Chunks: {len(chunks)}")
        for chunk in chunks:
            print(f"  [{chunk.filename}] Score: {chunk.relevance_score:.2f}")

# Run
asyncio.run(process_document_complete())
```

## Configuration

### Environment Variables

```bash
# Required for LLM analysis
ANTHROPIC_API_KEY=sk-ant-...

# Optional - override defaults
DOCUMENT_STORAGE_PATH=/custom/path/documents
DOCUMENT_MAX_SIZE=20971520  # 20MB
```

### Settings in config.py

```python
from cloud_optimizer.config import get_settings

settings = get_settings()
api_key = settings.anthropic_api_key  # From environment
```

## File Constraints

| Setting | Value | Notes |
|---------|-------|-------|
| Max File Size | 10MB | 10,485,760 bytes |
| Allowed Types | PDF, TXT | `application/pdf`, `text/plain` |
| Storage Path | `/tmp/cloud_optimizer/documents/` | Configurable |
| Chunk Size | 1000 chars | For context extraction |
| Chunk Overlap | 200 chars | Preserves context |

## Error Handling

### Common Errors

**File Too Large:**
```python
DocumentValidationError: File size exceeds maximum 10485760 bytes
```

**Invalid Type:**
```python
DocumentValidationError: Invalid content type. Allowed: application/pdf, text/plain
```

**Analysis Failed:**
```python
AnalysisError: Anthropic API key not configured
```

**Extraction Failed:**
```python
ExtractionError: pypdf library not installed
```

### Handling Errors

```python
from ib_platform.document.service import DocumentValidationError
from ib_platform.document.extraction import ExtractionError
from ib_platform.document.analysis import AnalysisError

try:
    document = await service.upload_document(...)
except DocumentValidationError as e:
    print(f"Validation failed: {e}")

try:
    text = extractor.extract_text(path, content_type)
except ExtractionError as e:
    print(f"Extraction failed: {e}")

try:
    result = await analyzer.analyze_document(text)
except AnalysisError as e:
    print(f"Analysis failed: {e}")
```

## Testing

### Run Tests

```bash
# All document tests
pytest tests/ib_platform/document/ -v

# Specific test
pytest tests/ib_platform/document/test_upload.py::test_upload_valid_text_document -v

# With coverage
pytest tests/ib_platform/document/ --cov=ib_platform.document
```

### Test Fixtures

```python
import pytest
from ib_platform.document.models import Document

@pytest.fixture
def sample_txt_content() -> bytes:
    return b"AWS Security Best Practices..."

@pytest.mark.asyncio
async def test_my_feature(db_session, sample_txt_content):
    # Your test here
    pass
```

## Common Patterns

### Background Processing

```python
from fastapi import BackgroundTasks

async def process_in_background(doc_id: UUID, path: str, type: str):
    """Background task for extraction."""
    # Extract and save
    pass

@router.post("/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    service: DocumentServiceDep
):
    doc = await service.upload_document(...)

    # Schedule background processing
    background_tasks.add_task(
        process_in_background,
        doc.document_id,
        doc.storage_path,
        doc.content_type
    )

    return doc
```

### Pagination

```python
@router.get("/")
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    service: DocumentServiceDep
):
    # Limit max to 100
    limit = min(limit, 100)

    docs = await service.list_documents(
        user_id,
        limit=limit,
        offset=offset
    )

    return {"documents": docs, "limit": limit, "offset": offset}
```

## Troubleshooting

### Issue: Text extraction fails for PDF

**Solution:** Ensure pypdf is installed
```bash
pip install pypdf
```

### Issue: Analysis returns empty results

**Solution:** Check API key configuration
```bash
echo $ANTHROPIC_API_KEY
# Should show: sk-ant-...
```

### Issue: Document not found after upload

**Solution:** Check user_id authorization
```python
doc = await service.get_document(doc_id, user_id)
# Returns None if wrong user_id
```

### Issue: Storage directory doesn't exist

**Solution:** Create directory
```bash
mkdir -p /tmp/cloud_optimizer/documents
chmod 755 /tmp/cloud_optimizer/documents
```

## Performance Tips

1. **Use Background Tasks:**
   - Don't block upload endpoint
   - Extract text asynchronously

2. **Limit Document Size:**
   - 10MB is reasonable for most docs
   - Large PDFs can be slow

3. **Cache Analysis Results:**
   - Store in document.metadata
   - Avoid re-analyzing same doc

4. **Optimize Chunking:**
   - Smaller chunks = faster search
   - Larger chunks = better context

## Security Checklist

- [ ] Validate file types
- [ ] Enforce size limits
- [ ] Check user authorization
- [ ] Use UUID filenames
- [ ] Store in user directories
- [ ] Clean up on deletion
- [ ] Never log API keys
- [ ] Sanitize file paths

## Resources

- [Module Documentation](../src/ib_platform/document/README.md)
- [API Schema](../src/cloud_optimizer/api/schemas/documents.py)
- [Test Examples](../tests/ib_platform/document/)
- [Database Migration](../alembic/versions/20251202_0726_b4591d8d37bd_add_documents_table.py)
