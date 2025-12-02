"""Context assembly for answer generation.

This module provides the AnswerContext dataclass and ContextAssembler service
that gathers relevant KB entries, findings, and documents based on NLU results.
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from ib_platform.kb.models import KBEntry
from ib_platform.kb.service import KnowledgeBaseService

logger = logging.getLogger(__name__)


@dataclass
class AnswerContext:
    """Context for answer generation.

    Attributes:
        kb_entries: Relevant knowledge base entries (controls, practices, patterns)
        findings: Relevant security/cost findings
        documents: Relevant document context
        conversation_history: Previous messages in the conversation
    """

    kb_entries: list[KBEntry] = field(default_factory=list)
    findings: list[Any] = field(default_factory=list)  # List[Finding]
    documents: list[dict[str, Any]] = field(default_factory=list)
    conversation_history: list[dict[str, str]] = field(default_factory=list)


class ContextAssembler:
    """Assembles context from various sources for answer generation.

    Gathers relevant KB entries, findings, and documents based on NLU entities
    and intent to provide rich context for LLM-based answer generation.

    Example:
        >>> kb_service = KnowledgeBaseService.get_instance()
        >>> findings_service = FindingsService(db)
        >>> assembler = ContextAssembler(kb_service, findings_service)
        >>> context = await assembler.assemble(nlu_result, tenant_id)
    """

    def __init__(
        self,
        kb_service: KnowledgeBaseService,
        findings_service: Any = None,  # FindingsService
        document_service: Any = None,  # DocumentService (future)
    ) -> None:
        """Initialize the context assembler.

        Args:
            kb_service: Knowledge base service for retrieving KB entries
            findings_service: Optional findings service for retrieving findings
            document_service: Optional document service for retrieving documents
        """
        self.kb_service = kb_service
        self.findings_service = findings_service
        self.document_service = document_service

    async def assemble(
        self,
        nlu_result: Any,  # NLUResult
        aws_account_id: UUID | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> AnswerContext:
        """Assemble context from various sources based on NLU result.

        Args:
            nlu_result: NLU processing result with intent and entities
            aws_account_id: Optional AWS account ID for finding queries
            conversation_history: Optional previous conversation messages

        Returns:
            AnswerContext with gathered KB entries, findings, and documents
        """
        context = AnswerContext(
            conversation_history=conversation_history or [],
        )

        # Gather KB entries based on entities
        await self._gather_kb_entries(nlu_result, context)

        # Gather findings if available and relevant
        if self.findings_service and aws_account_id:
            await self._gather_findings(nlu_result, aws_account_id, context)

        # Gather documents if available and relevant
        if self.document_service:
            await self._gather_documents(nlu_result, context)

        logger.info(
            f"Assembled context: {len(context.kb_entries)} KB entries, "
            f"{len(context.findings)} findings, {len(context.documents)} documents"
        )

        return context

    async def _gather_kb_entries(
        self, nlu_result: Any, context: AnswerContext
    ) -> None:
        """Gather relevant KB entries based on NLU entities.

        Args:
            nlu_result: NLU processing result
            context: Answer context to populate
        """
        # Get KB entries for compliance frameworks
        if hasattr(nlu_result, "entities") and hasattr(
            nlu_result.entities, "compliance_frameworks"
        ):
            for framework in nlu_result.entities.compliance_frameworks:
                entries = self.kb_service.get_for_framework(framework)
                context.kb_entries.extend(entries[:10])  # Limit to top 10 per framework

        # Get KB entries for AWS services
        if hasattr(nlu_result, "entities") and hasattr(
            nlu_result.entities, "aws_services"
        ):
            for service in nlu_result.entities.aws_services:
                entries = self.kb_service.get_for_service(service)
                context.kb_entries.extend(entries[:10])  # Limit to top 10 per service

        # Get KB entries via search if we have keywords
        if hasattr(nlu_result, "query"):
            search_results = self.kb_service.search(nlu_result.query, limit=5)
            context.kb_entries.extend(search_results)

        # Deduplicate KB entries (by control_name)
        seen = set()
        unique_entries = []
        for entry in context.kb_entries:
            key = (entry.control_name, entry.framework, entry.service)
            if key not in seen:
                seen.add(key)
                unique_entries.append(entry)
        context.kb_entries = unique_entries[:20]  # Limit total to 20

    async def _gather_findings(
        self, nlu_result: Any, aws_account_id: UUID, context: AnswerContext
    ) -> None:
        """Gather relevant findings based on NLU entities.

        Args:
            nlu_result: NLU processing result
            aws_account_id: AWS account ID to query
            context: Answer context to populate
        """
        if not self.findings_service:
            return

        try:
            # Get findings filtered by services if mentioned
            service = None
            if hasattr(nlu_result, "entities") and hasattr(
                nlu_result.entities, "aws_services"
            ):
                if nlu_result.entities.aws_services:
                    service = nlu_result.entities.aws_services[0]

            # Query findings
            findings = await self.findings_service.get_findings_by_account(
                aws_account_id=aws_account_id,
                service=service,
                limit=10,
            )
            context.findings = findings

        except Exception as e:
            logger.warning(f"Failed to gather findings: {e}")

    async def _gather_documents(self, nlu_result: Any, context: AnswerContext) -> None:
        """Gather relevant documents based on NLU result.

        Args:
            nlu_result: NLU processing result
            context: Answer context to populate
        """
        if not self.document_service:
            return

        # Future implementation when document service is available
        # Will search for relevant architecture documents, diagrams, etc.
        pass
