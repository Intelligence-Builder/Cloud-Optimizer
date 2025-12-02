"""Pytest fixtures for answer generation tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from ib_platform.kb.models import KBEntry
from ib_platform.kb.service import KnowledgeBaseService


@pytest.fixture
def mock_kb_service():
    """Create a mock KnowledgeBaseService."""
    service = MagicMock(spec=KnowledgeBaseService)
    service.is_loaded.return_value = True

    # Mock KB entry
    kb_entry = KBEntry(
        entry_type="control",
        control_name="Enable MFA",
        description="Multi-factor authentication should be enabled",
        guidance="Configure MFA in IAM console",
        framework="CIS",
        service="IAM",
        terraform="resource...",
        cli="aws iam...",
        metadata={"score": 3},
    )

    service.get_for_framework.return_value = [kb_entry]
    service.get_for_service.return_value = [kb_entry]
    service.search.return_value = [kb_entry]

    return service


@pytest.fixture
def mock_findings_service():
    """Create a mock FindingsService."""
    service = AsyncMock()

    # Mock finding
    from cloud_optimizer.models.finding import Finding, FindingSeverity, FindingStatus

    finding = Finding(
        finding_id=uuid4(),
        scan_job_id=uuid4(),
        aws_account_id=uuid4(),
        rule_id="iam-mfa-enabled",
        finding_type="security",
        severity=FindingSeverity.HIGH,
        status=FindingStatus.OPEN,
        service="IAM",
        resource_type="User",
        resource_id="user-123",
        region="us-east-1",
        title="MFA not enabled for IAM user",
        description="IAM user does not have MFA enabled",
        recommendation="Enable MFA for this user",
        evidence={},
        compliance_frameworks=["CIS", "NIST"],
    )

    service.get_findings_by_account.return_value = [finding]

    return service


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""

    class MockTextStream:
        def __init__(self, chunks):
            self.chunks = chunks
            self.index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.index >= len(self.chunks):
                raise StopAsyncIteration
            chunk = self.chunks[self.index]
            self.index += 1
            return chunk

    class MockStreamManager:
        def __init__(self, chunks):
            self.chunks = chunks
            self.text_stream = MockTextStream(chunks)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockContent:
        def __init__(self, text):
            self.text = text

    class MockResponse:
        def __init__(self, text):
            self.content = [MockContent(text)]

    class MockMessages:
        def __init__(self):
            self.chunks = ["Here's ", "my ", "security ", "advice."]

        def stream(self, **kwargs):
            return MockStreamManager(self.chunks)

        async def create(self, **kwargs):
            return MockResponse("Here's my security advice.")

    client = AsyncMock()
    client.messages = MockMessages()

    return client


@pytest.fixture
def simple_nlu_result():
    """Create a simple NLU result for testing."""

    class SimpleEntities:
        def __init__(self):
            self.aws_services = ["S3", "IAM"]
            self.compliance_frameworks = ["CIS", "NIST"]

    class SimpleNLUResult:
        def __init__(self):
            self.query = "How do I secure S3?"
            self.intent = "security_advice"
            self.entities = SimpleEntities()

    return SimpleNLUResult()


@pytest.fixture
def sample_conversation_history():
    """Create sample conversation history."""
    return [
        {"role": "user", "content": "What is MFA?"},
        {"role": "assistant", "content": "MFA is multi-factor authentication..."},
    ]
