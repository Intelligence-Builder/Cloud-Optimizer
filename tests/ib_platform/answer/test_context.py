"""Tests for context assembly."""

import pytest
from uuid import uuid4

from ib_platform.answer.context import AnswerContext, ContextAssembler


@pytest.mark.asyncio
async def test_answer_context_initialization():
    """Test AnswerContext initialization."""
    context = AnswerContext()

    assert context.kb_entries == []
    assert context.findings == []
    assert context.documents == []
    assert context.conversation_history == []


@pytest.mark.asyncio
async def test_context_assembler_initialization(mock_kb_service, mock_findings_service):
    """Test ContextAssembler initialization."""
    assembler = ContextAssembler(
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    assert assembler.kb_service is mock_kb_service
    assert assembler.findings_service is mock_findings_service


@pytest.mark.asyncio
async def test_assemble_with_frameworks(
    mock_kb_service, mock_findings_service, simple_nlu_result
):
    """Test context assembly with compliance frameworks."""
    assembler = ContextAssembler(
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    context = await assembler.assemble(
        nlu_result=simple_nlu_result,
        aws_account_id=uuid4(),
    )

    # Should have gathered KB entries
    assert len(context.kb_entries) > 0
    mock_kb_service.get_for_framework.assert_called()


@pytest.mark.asyncio
async def test_assemble_with_services(
    mock_kb_service, mock_findings_service, simple_nlu_result
):
    """Test context assembly with AWS services."""
    assembler = ContextAssembler(
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    context = await assembler.assemble(
        nlu_result=simple_nlu_result,
        aws_account_id=uuid4(),
    )

    # Should have gathered KB entries for services
    assert len(context.kb_entries) > 0
    mock_kb_service.get_for_service.assert_called()


@pytest.mark.asyncio
async def test_assemble_with_findings(
    mock_kb_service, mock_findings_service, simple_nlu_result
):
    """Test context assembly gathers findings."""
    assembler = ContextAssembler(
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    aws_account_id = uuid4()
    context = await assembler.assemble(
        nlu_result=simple_nlu_result,
        aws_account_id=aws_account_id,
    )

    # Should have gathered findings
    assert len(context.findings) > 0
    mock_findings_service.get_findings_by_account.assert_called_once()


@pytest.mark.asyncio
async def test_assemble_without_findings_service(mock_kb_service, simple_nlu_result):
    """Test context assembly without findings service."""
    assembler = ContextAssembler(
        kb_service=mock_kb_service,
        findings_service=None,
    )

    context = await assembler.assemble(
        nlu_result=simple_nlu_result,
        aws_account_id=uuid4(),
    )

    # Should still work, just without findings
    assert len(context.findings) == 0
    assert len(context.kb_entries) > 0


@pytest.mark.asyncio
async def test_assemble_with_conversation_history(
    mock_kb_service, simple_nlu_result, sample_conversation_history
):
    """Test context assembly preserves conversation history."""
    assembler = ContextAssembler(kb_service=mock_kb_service)

    context = await assembler.assemble(
        nlu_result=simple_nlu_result,
        conversation_history=sample_conversation_history,
    )

    assert context.conversation_history == sample_conversation_history


@pytest.mark.asyncio
async def test_gather_kb_entries_deduplication(mock_kb_service, simple_nlu_result):
    """Test that KB entries are deduplicated."""
    assembler = ContextAssembler(kb_service=mock_kb_service)

    context = await assembler.assemble(nlu_result=simple_nlu_result)

    # Should deduplicate entries
    control_names = [entry.control_name for entry in context.kb_entries]
    assert len(control_names) == len(set(control_names))


@pytest.mark.asyncio
async def test_gather_findings_handles_errors(
    mock_kb_service, mock_findings_service, simple_nlu_result
):
    """Test that finding gathering handles errors gracefully."""
    # Make findings service raise an error
    mock_findings_service.get_findings_by_account.side_effect = Exception(
        "Database error"
    )

    assembler = ContextAssembler(
        kb_service=mock_kb_service,
        findings_service=mock_findings_service,
    )

    # Should not raise, should just log warning and continue
    context = await assembler.assemble(
        nlu_result=simple_nlu_result,
        aws_account_id=uuid4(),
    )

    assert len(context.findings) == 0
    assert len(context.kb_entries) > 0  # KB entries should still be gathered
