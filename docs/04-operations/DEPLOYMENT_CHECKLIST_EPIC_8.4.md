# Deployment Checklist: Epic 8.4 Document Analysis Service

**Epic:** Document Analysis Service for Cloud Optimizer
**Date:** 2025-12-02
**Status:** Ready for Deployment

## Pre-Deployment Validation

### Code Quality ✅

- [x] All Python files compile without syntax errors
- [x] Type hints present on all functions
- [x] Imports verified and working
- [x] No circular dependencies
- [x] Code follows project conventions

**Validation Commands:**
```bash
# Syntax validation
python -m py_compile src/ib_platform/document/*.py
python -m py_compile src/cloud_optimizer/api/schemas/documents.py
python -m py_compile src/cloud_optimizer/api/routers/documents.py

# Import validation
PYTHONPATH=src python -c "from ib_platform.document import *"
```

### Test Suite ✅

- [x] 34 tests created
- [x] Test fixtures configured
- [x] All test files compile
- [x] Coverage areas identified

**Test Execution:**
```bash
# Run all tests (after environment setup)
pytest tests/ib_platform/document/ -v

# Expected: 34 tests
# - test_upload.py: 11 tests
# - test_extraction.py: 6 tests
# - test_analysis.py: 9 tests
# - test_context.py: 8 tests
```

### Documentation ✅

- [x] Module README created
- [x] API documentation complete
- [x] Quick start guide created
- [x] Implementation summary written
- [x] Code comments present

## Deployment Steps

### 1. Environment Configuration

#### Required Environment Variables

```bash
# Add to .env file
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional overrides
DOCUMENT_STORAGE_PATH=/tmp/cloud_optimizer/documents
DOCUMENT_MAX_SIZE=10485760
```

**Validation:**
```bash
# Check environment variable is set
echo $ANTHROPIC_API_KEY
# Should output: sk-ant-...
```

- [ ] ANTHROPIC_API_KEY configured
- [ ] Storage path configured (if custom)

### 2. Install Dependencies

```bash
# Install new dependencies
pip install pypdf>=4.0.0

# Or reinstall entire project
pip install -e .
```

**Validation:**
```bash
# Verify pypdf is installed
python -c "import pypdf; print(f'pypdf {pypdf.__version__}')"

# Verify anthropic is installed
python -c "import anthropic; print(f'anthropic {anthropic.__version__}')"
```

- [ ] pypdf installed
- [ ] anthropic installed
- [ ] Dependencies verified

### 3. Database Migration

```bash
# Backup database (IMPORTANT!)
pg_dump cloud_optimizer > backup_$(date +%Y%m%d_%H%M%S).sql

# Apply migration
alembic upgrade head

# Verify table created
psql cloud_optimizer -c "\d documents"
```

**Expected Output:**
```
                      Table "public.documents"
     Column      |           Type           | Nullable | Default
-----------------+--------------------------+----------+---------
 document_id     | uuid                     | not null | gen_random_uuid()
 user_id         | uuid                     | not null |
 filename        | character varying(255)   | not null |
 content_type    | character varying(100)   | not null |
 file_size       | integer                  | not null |
 storage_path    | character varying(500)   | not null |
 extracted_text  | text                     |          |
 status          | character varying(20)    | not null | 'processing'
 error_message   | text                     |          |
 created_at      | timestamp with time zone | not null | now()
 updated_at      | timestamp with time zone | not null | now()
Indexes:
    "documents_pkey" PRIMARY KEY, btree (document_id)
    "ix_documents_status" btree (status)
    "ix_documents_user_id" btree (user_id)
Foreign-key constraints:
    "documents_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
```

- [ ] Database backed up
- [ ] Migration applied successfully
- [ ] Table structure verified
- [ ] Indexes created
- [ ] Foreign key constraint present

### 4. Storage Directory Setup

```bash
# Create storage directory
mkdir -p /tmp/cloud_optimizer/documents

# Set permissions
chmod 755 /tmp/cloud_optimizer/documents

# Verify
ls -ld /tmp/cloud_optimizer/documents
```

**Expected Output:**
```
drwxr-xr-x  2 user  group  64 Dec  2 07:00 /tmp/cloud_optimizer/documents
```

- [ ] Storage directory created
- [ ] Permissions set correctly
- [ ] Directory accessible

### 5. API Router Registration

**File:** `src/cloud_optimizer/api/main.py` (or equivalent)

```python
from cloud_optimizer.api.routers import documents

# Register router
app.include_router(
    documents.router,
    prefix="/api/v1/documents",
    tags=["documents"],
)
```

- [ ] Router imported
- [ ] Router registered with prefix
- [ ] Tags configured

### 6. Test Deployment

#### Manual API Testing

```bash
# Start server
uvicorn cloud_optimizer.api.main:app --reload

# Test upload (replace TOKEN)
curl -X POST http://localhost:8080/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_document.txt"

# Test list
curl http://localhost:8080/api/v1/documents/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Responses:**
- Upload: 201 Created with document metadata
- List: 200 OK with document array

- [ ] Upload endpoint working
- [ ] List endpoint working
- [ ] Get endpoint working
- [ ] Delete endpoint working
- [ ] Analyze endpoint working

#### Automated Testing

```bash
# Run test suite
pytest tests/ib_platform/document/ -v --tb=short

# Run with coverage
pytest tests/ib_platform/document/ \
  --cov=ib_platform.document \
  --cov-report=term-missing
```

- [ ] All tests passing
- [ ] Coverage >80%
- [ ] No warnings or errors

### 7. Integration Testing

#### Chat Integration

**Test that document context works with chat:**

```python
# Upload document with known content
# Ask chat question related to document
# Verify chat response includes document context
```

- [ ] Document upload via UI
- [ ] Text extraction completes
- [ ] Analysis returns results
- [ ] Chat uses document context

### 8. Monitoring Setup

#### Log Monitoring

**Add logging for:**
- Document uploads
- Extraction failures
- Analysis errors
- Storage issues

```python
import structlog

logger = structlog.get_logger()

# In service.py
logger.info("document_uploaded",
    document_id=str(doc.document_id),
    filename=doc.filename,
    size=doc.file_size
)
```

- [ ] Upload logging enabled
- [ ] Error logging enabled
- [ ] Analysis logging enabled

#### Metrics Monitoring

**Track:**
- Upload count per user
- Average file size
- Extraction success rate
- Analysis success rate
- Storage usage

- [ ] Metrics collection configured

## Post-Deployment Validation

### Smoke Tests

```bash
# 1. Upload a document
RESULT=$(curl -X POST http://localhost:8080/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.txt" -s)

DOC_ID=$(echo $RESULT | jq -r '.document_id')

# 2. Wait for processing (5 seconds)
sleep 5

# 3. Get document
curl http://localhost:8080/api/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"

# 4. Analyze
curl -X POST http://localhost:8080/api/v1/documents/$DOC_ID/analyze \
  -H "Authorization: Bearer $TOKEN"

# 5. Delete
curl -X DELETE http://localhost:8080/api/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"
```

- [ ] Upload successful
- [ ] Processing completes
- [ ] Analysis returns data
- [ ] Deletion works

### Performance Tests

```bash
# Test with 10MB file
dd if=/dev/zero of=test_10mb.txt bs=1M count=10

# Upload should succeed
curl -X POST http://localhost:8080/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_10mb.txt"

# Test with 11MB file (should fail)
dd if=/dev/zero of=test_11mb.txt bs=1M count=11

# Upload should fail with 400
curl -X POST http://localhost:8080/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_11mb.txt"
```

- [ ] 10MB file uploads successfully
- [ ] >10MB file rejected
- [ ] Invalid types rejected

## Rollback Plan

### If Deployment Fails

#### 1. Rollback Database

```bash
# Restore from backup
psql cloud_optimizer < backup_YYYYMMDD_HHMMSS.sql

# Or rollback migration
alembic downgrade -1
```

#### 2. Remove Router Registration

```python
# Comment out in main.py
# app.include_router(documents.router, ...)
```

#### 3. Restart Application

```bash
# Restart without document module
systemctl restart cloud-optimizer
```

## Production Considerations

### Security

- [ ] API rate limiting configured
- [ ] File type validation strict
- [ ] User quotas implemented
- [ ] Storage quotas set
- [ ] API key rotation scheduled

### Performance

- [ ] Background task queue configured
- [ ] Analysis result caching enabled
- [ ] Storage cleanup scheduled
- [ ] Database indexes optimized

### Scalability

- [ ] S3 backend configured (optional)
- [ ] Load balancer configured
- [ ] CDN for document delivery (optional)

### Backup

- [ ] Document storage backed up
- [ ] Database backup includes documents table
- [ ] Backup retention policy set

## Known Issues

### 1. Large PDF Processing

**Issue:** Very large PDFs (>5MB) may take >30 seconds to process
**Mitigation:** Use background tasks, provide status endpoint

### 2. LLM Rate Limits

**Issue:** Anthropic API has rate limits
**Mitigation:** Implement retry logic, queue analysis requests

### 3. Storage Growth

**Issue:** Document storage can grow large
**Mitigation:** Implement cleanup policy, user quotas

## Support Information

### Documentation

- Module README: `src/ib_platform/document/README.md`
- Quick Start: `docs/DOCUMENT_ANALYSIS_QUICKSTART.md`
- Implementation Summary: `EPIC_8.4_IMPLEMENTATION_SUMMARY.md`

### Troubleshooting

- Check logs: `tail -f logs/cloud-optimizer.log`
- Verify environment: `echo $ANTHROPIC_API_KEY`
- Test database: `psql cloud_optimizer -c "SELECT COUNT(*) FROM documents"`
- Check storage: `du -sh /tmp/cloud_optimizer/documents/`

### Contact

- Epic Owner: [Name]
- Technical Lead: [Name]
- Documentation: See files above

## Sign-Off

- [ ] Code review completed
- [ ] Tests passing
- [ ] Documentation reviewed
- [ ] Security reviewed
- [ ] Performance acceptable
- [ ] Ready for production

**Deployed By:** _______________
**Date:** _______________
**Version:** 2.0.0
**Git Commit:** _______________

---

## Quick Reference Commands

```bash
# Install dependencies
pip install pypdf anthropic

# Apply migration
alembic upgrade head

# Create storage
mkdir -p /tmp/cloud_optimizer/documents

# Run tests
pytest tests/ib_platform/document/ -v

# Start server
uvicorn cloud_optimizer.api.main:app --reload

# Check status
curl http://localhost:8080/api/v1/documents/ \
  -H "Authorization: Bearer $TOKEN"
```
