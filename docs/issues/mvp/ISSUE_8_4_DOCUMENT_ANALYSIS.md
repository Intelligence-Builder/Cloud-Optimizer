# 8.4 Document Analysis Service

## Parent Epic
Epic 8: MVP Phase 2 - Expert System (Intelligence-Builder)

## Overview

Implement document analysis capabilities that process uploaded architecture documents (PDF, TXT) to extract entities, identify security concerns, and provide recommendations. Enables the "upload your architecture and get recommendations" use case.

## Background

Document analysis is a key differentiator for trial customers who want to:
- Get security review of architecture designs
- Understand compliance implications of proposed architectures
- Identify missing security controls before deployment
- Get recommendations for security improvements

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| DOC-001 | PDF parsing | Extract text from PDF documents, handle multi-page |
| DOC-002 | Entity extraction | Identify AWS services, data flows, security controls |
| DOC-003 | Security analysis | Identify security gaps and recommend improvements |
| DOC-004 | Document context | Use document content in chat responses |

## Technical Specification

### Document Processing Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Document Processing Pipeline                      │
│                                                                       │
│  Upload → Extraction → Entity Analysis → Security Review → Storage   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  PDF/TXT → Text Extraction → LLM Analysis → Structured Output   ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Database Schema

```sql
-- Uploaded documents
CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    conversation_id UUID,  -- Associated chat conversation
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size INTEGER NOT NULL,
    storage_path VARCHAR(500) NOT NULL,  -- S3 or local path
    status VARCHAR(20) NOT NULL DEFAULT 'processing',  -- processing, analyzed, error
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Document analysis results
CREATE TABLE document_analyses (
    analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(document_id),
    extracted_text TEXT,
    summary TEXT,
    entities JSONB,          -- AWS services, data flows, etc.
    security_concerns JSONB, -- Identified issues
    recommendations JSONB,   -- Suggested improvements
    compliance_gaps JSONB,   -- Missing compliance controls
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_tenant ON documents(tenant_id);
CREATE INDEX idx_documents_conversation ON documents(conversation_id);
CREATE INDEX idx_analyses_document ON document_analyses(document_id);
```

### Document Service

```python
# src/ib_platform/document/service.py
import pypdf
from anthropic import Anthropic
from pathlib import Path

class DocumentService:
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_TYPES = ["application/pdf", "text/plain"]

    def __init__(
        self,
        db: AsyncSession,
        anthropic_client: Anthropic,
        storage_path: Path,
    ):
        self.db = db
        self.client = anthropic_client
        self.storage_path = storage_path

    async def upload(
        self,
        tenant_id: UUID,
        file: UploadFile,
        conversation_id: UUID = None,
    ) -> Document:
        """Upload and process a document."""
        # Validate file
        if file.content_type not in self.ALLOWED_TYPES:
            raise InvalidDocumentTypeException(
                f"Unsupported file type: {file.content_type}"
            )

        content = await file.read()
        if len(content) > self.MAX_FILE_SIZE:
            raise DocumentTooLargeException(
                f"File exceeds {self.MAX_FILE_SIZE / 1024 / 1024}MB limit"
            )

        # Save file
        storage_path = await self._save_file(tenant_id, file.filename, content)

        # Create document record
        document = Document(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            filename=file.filename,
            content_type=file.content_type,
            file_size=len(content),
            storage_path=str(storage_path),
            status="processing",
        )
        self.db.add(document)
        await self.db.commit()

        # Start async analysis
        asyncio.create_task(self._analyze_document(document.document_id))

        return document

    async def _analyze_document(self, document_id: UUID):
        """Analyze document content."""
        document = await self._get_document(document_id)

        try:
            # Extract text
            text = await self._extract_text(document)

            # Analyze with LLM
            analysis = await self._analyze_with_llm(text)

            # Save analysis
            doc_analysis = DocumentAnalysis(
                document_id=document_id,
                extracted_text=text[:50000],  # Limit stored text
                summary=analysis["summary"],
                entities=analysis["entities"],
                security_concerns=analysis["security_concerns"],
                recommendations=analysis["recommendations"],
                compliance_gaps=analysis["compliance_gaps"],
            )
            self.db.add(doc_analysis)

            document.status = "analyzed"
            await self.db.commit()

        except Exception as e:
            document.status = "error"
            await self.db.commit()
            raise

    async def _extract_text(self, document: Document) -> str:
        """Extract text from document."""
        file_path = Path(document.storage_path)

        if document.content_type == "application/pdf":
            return await self._extract_pdf_text(file_path)
        elif document.content_type == "text/plain":
            return file_path.read_text()
        else:
            raise UnsupportedDocumentTypeException()

    async def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF."""
        text_parts = []

        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        return "\n\n".join(text_parts)

    async def _analyze_with_llm(self, text: str) -> dict:
        """Analyze document text with LLM."""
        prompt = f"""Analyze this architecture document for AWS security.

Document content:
---
{text[:30000]}
---

Provide analysis in JSON format:
{{
    "summary": "Brief summary of the architecture (2-3 sentences)",
    "entities": {{
        "aws_services": ["list of AWS services mentioned"],
        "data_flows": ["description of data flows"],
        "data_types": ["types of data handled (PII, PHI, financial, etc.)"],
        "external_integrations": ["third-party services/APIs"]
    }},
    "security_concerns": [
        {{
            "title": "Concern title",
            "severity": "high/medium/low",
            "description": "Description of the concern",
            "affected_components": ["components affected"]
        }}
    ],
    "recommendations": [
        {{
            "title": "Recommendation title",
            "priority": "high/medium/low",
            "description": "What to do",
            "compliance_relevance": ["HIPAA", "SOC2", etc.]
        }}
    ],
    "compliance_gaps": [
        {{
            "framework": "HIPAA/SOC2/PCI-DSS/etc.",
            "gap": "Description of what's missing",
            "recommendation": "How to address it"
        }}
    ]
}}"""

        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse JSON response
        content = response.content[0].text
        # Extract JSON from response (may be wrapped in markdown)
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())

        raise AnalysisParsingException("Could not parse analysis response")

    async def get_document(
        self,
        tenant_id: UUID,
        document_id: UUID,
    ) -> Document:
        """Get document by ID."""
        result = await self.db.execute(
            select(Document)
            .where(Document.document_id == document_id)
            .where(Document.tenant_id == tenant_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            raise DocumentNotFoundException()
        return document

    async def get_analysis(
        self,
        tenant_id: UUID,
        document_id: UUID,
    ) -> DocumentAnalysis:
        """Get document analysis."""
        document = await self.get_document(tenant_id, document_id)

        result = await self.db.execute(
            select(DocumentAnalysis)
            .where(DocumentAnalysis.document_id == document_id)
        )
        analysis = result.scalar_one_or_none()
        if not analysis:
            raise AnalysisNotFoundException()
        return analysis

    async def get_for_conversation(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
    ) -> list[DocumentContext]:
        """Get document context for a conversation."""
        result = await self.db.execute(
            select(Document, DocumentAnalysis)
            .join(DocumentAnalysis)
            .where(Document.tenant_id == tenant_id)
            .where(Document.conversation_id == conversation_id)
            .where(Document.status == "analyzed")
        )

        contexts = []
        for doc, analysis in result:
            contexts.append(
                DocumentContext(
                    document_id=doc.document_id,
                    filename=doc.filename,
                    summary=analysis.summary,
                    entities=analysis.entities,
                    security_concerns=analysis.security_concerns,
                )
            )

        return contexts

    async def delete_document(
        self,
        tenant_id: UUID,
        document_id: UUID,
    ):
        """Delete document and analysis."""
        document = await self.get_document(tenant_id, document_id)

        # Delete file
        file_path = Path(document.storage_path)
        if file_path.exists():
            file_path.unlink()

        # Delete records
        await self.db.execute(
            delete(DocumentAnalysis)
            .where(DocumentAnalysis.document_id == document_id)
        )
        await self.db.execute(
            delete(Document)
            .where(Document.document_id == document_id)
        )
        await self.db.commit()
```

### Document Context for Chat

```python
# src/ib_platform/document/context.py
@dataclass
class DocumentContext:
    document_id: UUID
    filename: str
    summary: str
    entities: dict
    security_concerns: list[dict]

    def to_prompt_context(self) -> str:
        """Format for inclusion in chat prompts."""
        lines = [
            f"**Document: {self.filename}**",
            f"Summary: {self.summary}",
            "",
            "**AWS Services:**",
            ", ".join(self.entities.get("aws_services", [])),
            "",
            "**Data Types:**",
            ", ".join(self.entities.get("data_types", [])),
            "",
            "**Security Concerns:**",
        ]

        for concern in self.security_concerns[:5]:
            lines.append(f"- [{concern['severity']}] {concern['title']}")

        return "\n".join(lines)
```

## API Endpoints

```
POST /api/v1/documents/upload        # Upload document
GET  /api/v1/documents               # List documents
GET  /api/v1/documents/:id           # Get document
GET  /api/v1/documents/:id/analysis  # Get analysis
DELETE /api/v1/documents/:id         # Delete document
GET  /api/v1/documents/:id/download  # Download original
```

## Files to Create

```
src/ib_platform/document/
├── __init__.py
├── service.py               # Main document service
├── extraction.py            # Text extraction
├── analysis.py              # LLM analysis
├── context.py               # Chat context
└── models.py                # Data models

src/cloud_optimizer/api/routers/
└── documents.py             # API endpoints

alembic/versions/
└── xxx_create_document_tables.py

tests/ib_platform/document/
├── test_extraction.py
├── test_analysis.py
├── test_service.py
└── test_api.py
```

## Testing Requirements

### Unit Tests
- [ ] `test_pdf_extraction.py` - PDF text extraction
- [ ] `test_txt_extraction.py` - TXT file handling
- [ ] `test_entity_extraction.py` - Entity parsing from analysis
- [ ] `test_context_formatting.py` - Context for chat

### Integration Tests
- [ ] `test_document_upload.py` - Full upload flow
- [ ] `test_document_analysis.py` - Analysis with mocked LLM

### Test Files

```
tests/fixtures/documents/
├── sample_architecture.pdf
├── simple_design.txt
└── complex_multi_page.pdf
```

## Acceptance Criteria Checklist

- [ ] PDF upload works (up to 10MB)
- [ ] TXT upload works
- [ ] Text extracted from multi-page PDFs
- [ ] AWS services identified from documents
- [ ] Data flows extracted
- [ ] Security concerns identified with severity
- [ ] Recommendations provided with priority
- [ ] Compliance gaps identified
- [ ] Document context available for chat
- [ ] Trial limit enforced for documents
- [ ] 80%+ test coverage

## Dependencies

- 6.3 Trial Management (document limit)
- 6.5 Chat Interface (document upload UI)

## Blocked By

- 6.5 Chat Interface (upload capability)

## Blocks

- 8.2 Answer Generation (document context)

## Estimated Effort

1.5 weeks

## Labels

`document`, `analysis`, `ib`, `pdf`, `mvp`, `phase-2`, `P0`
