"""Shared fixtures for document tests."""

import tempfile
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cloud_optimizer.database import Base
from ib_platform.document.models import Document, DocumentStatus


@pytest.fixture
def sample_user_id() -> UUID:
    """Sample user ID for testing."""
    return uuid4()


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF file content."""
    # Minimal valid PDF
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
409
%%EOF"""


@pytest.fixture
def sample_txt_content() -> bytes:
    """Sample text file content."""
    return b"""AWS Security Best Practices

This document outlines security best practices for AWS environments.

Key Topics:
- IAM policies and roles
- S3 bucket encryption
- VPC security groups
- CloudTrail logging

Compliance Frameworks:
- CIS AWS Foundations Benchmark
- NIST 800-53
- PCI-DSS

Security Concerns:
- Overly permissive IAM policies
- Unencrypted S3 buckets
- Missing CloudTrail logs
"""


@pytest.fixture
def sample_document(sample_user_id: UUID) -> Document:
    """Sample document model for testing."""
    return Document(
        document_id=uuid4(),
        user_id=sample_user_id,
        filename="test_document.txt",
        content_type="text/plain",
        file_size=1024,
        storage_path="/tmp/test_document.txt",
        status=DocumentStatus.COMPLETED.value,
        extracted_text="Sample extracted text for testing",
    )


@pytest.fixture
def temp_storage_dir() -> Path:
    """Temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
async def db_engine():
    """Create test database engine."""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncSession:
    """Create test database session."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_analysis_text() -> str:
    """Sample text for analysis testing."""
    return """
    AWS Security Assessment Report

    Resources Identified:
    - EC2 instances in us-east-1
    - S3 buckets for data storage
    - RDS PostgreSQL database
    - Lambda functions for processing

    Compliance Requirements:
    - HIPAA compliance required
    - PCI-DSS Level 1

    Security Findings:
    - IAM roles with overly permissive policies
    - S3 buckets without encryption
    - Security groups allowing 0.0.0.0/0 access
    - Missing MFA on root account

    Recommendations:
    - Implement least privilege IAM policies
    - Enable S3 bucket encryption
    - Restrict security group rules
    - Enable MFA on all accounts
    """
