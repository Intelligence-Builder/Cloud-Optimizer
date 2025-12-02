# 8.2 Answer Generation Engine

## Parent Epic
Epic 8: MVP Phase 2 - Expert System (Intelligence-Builder)

## Overview

Implement the answer generation engine that produces expert-level security responses using LLM (Claude) with context from the knowledge base, findings, and documents. Supports streaming responses for real-time UI feedback.

## Background

Answer generation is the core value delivery mechanism. It must:
- Provide expert-level security advice
- Ground responses in compliance frameworks
- Reference specific findings when relevant
- Stream responses for better UX
- Include actionable remediation steps

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| ANS-001 | Context assembly | Gather relevant KB entries, findings, documents for context |
| ANS-002 | Expert prompting | Use security expert persona with compliance awareness |
| ANS-003 | Streaming generation | Stream response chunks via SSE |
| ANS-004 | Response structure | Include severity, compliance mapping, remediation |
| ANS-005 | Citation handling | Reference sources (findings, KB, documents) |

## Technical Specification

### Answer Generation Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Answer Generation Pipeline                        │
│                                                                       │
│  NLU Result → Context Assembly → Prompt Building → LLM → Streaming   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    Context Sources                               ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  ││
│  │  │ Compliance   │  │ Findings     │  │ Documents            │  ││
│  │  │ KB           │  │ (if any)     │  │ (if uploaded)        │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Answer Service

```python
# src/ib_platform/answer/service.py
from anthropic import Anthropic
from typing import AsyncIterator

class AnswerService:
    SYSTEM_PROMPT = """You are a cloud security expert assistant for Cloud Optimizer.
Your role is to provide accurate, actionable security advice for AWS environments.

Key behaviors:
1. Ground advice in specific compliance frameworks (HIPAA, SOC2, PCI-DSS, GDPR, CIS, NIST)
2. Provide specific, actionable remediation steps
3. Include severity assessment when discussing risks
4. Reference the user's actual findings when available
5. Be concise but thorough - prioritize the most important points
6. Use markdown formatting for readability
7. If you're not sure about something, say so

When discussing findings:
- Always mention the compliance frameworks affected
- Provide the specific remediation steps
- Include code snippets (Terraform, CLI, Console steps) when helpful

Format severity indicators:
- 🔴 CRITICAL: Immediate action required
- 🟠 HIGH: Address within 24-48 hours
- 🟡 MEDIUM: Address within 1-2 weeks
- 🟢 LOW: Address in next review cycle"""

    def __init__(
        self,
        anthropic_client: Anthropic,
        kb_service: KnowledgeBaseService,
        findings_service: FindingsService,
        document_service: DocumentService,
    ):
        self.client = anthropic_client
        self.kb_service = kb_service
        self.findings_service = findings_service
        self.document_service = document_service

    async def generate(
        self,
        question: str,
        nlu_result: NLUResult,
        tenant_id: UUID,
        conversation_history: list[dict],
    ) -> AsyncIterator[str]:
        """Generate answer with streaming."""
        # Assemble context
        context = await self._assemble_context(nlu_result, tenant_id)

        # Build messages
        messages = self._build_messages(
            question, context, conversation_history
        )

        # Stream response
        async with self.client.messages.stream(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            system=self.SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def _assemble_context(
        self,
        nlu_result: NLUResult,
        tenant_id: UUID,
    ) -> AnswerContext:
        """Assemble context from various sources."""
        context = AnswerContext()

        # Get relevant KB entries
        if nlu_result.entities.compliance_frameworks:
            for framework in nlu_result.entities.compliance_frameworks:
                kb_entries = await self.kb_service.get_for_framework(framework)
                context.kb_entries.extend(kb_entries)

        if nlu_result.entities.aws_services:
            for service in nlu_result.entities.aws_services:
                kb_entries = await self.kb_service.get_for_service(service)
                context.kb_entries.extend(kb_entries)

        # Get relevant findings
        if nlu_result.requires_findings:
            findings = await self._get_relevant_findings(nlu_result, tenant_id)
            context.findings = findings

        # Get document context
        if nlu_result.requires_documents:
            docs = await self.document_service.get_for_conversation(
                tenant_id, nlu_result.context
            )
            context.documents = docs

        return context

    async def _get_relevant_findings(
        self,
        nlu_result: NLUResult,
        tenant_id: UUID,
    ) -> list[Finding]:
        """Get findings relevant to the question."""
        # If specific finding IDs mentioned, get those
        if nlu_result.entities.finding_ids:
            return await self.findings_service.get_by_rule_ids(
                tenant_id, nlu_result.entities.finding_ids
            )

        # Otherwise, get findings for mentioned services
        filters = FindingFilters()
        if nlu_result.entities.aws_services:
            filters.resource_type = [
                f"{svc.lower()}_*" for svc in nlu_result.entities.aws_services
            ]
        if nlu_result.entities.compliance_frameworks:
            filters.compliance_framework = nlu_result.entities.compliance_frameworks[0]

        page = await self.findings_service.get_findings(
            tenant_id, filters, Pagination(limit=10)
        )
        return page.items

    def _build_messages(
        self,
        question: str,
        context: AnswerContext,
        history: list[dict],
    ) -> list[dict]:
        """Build messages array for Claude."""
        messages = []

        # Add conversation history (last 10 messages)
        for msg in history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # Build user message with context
        user_content = self._build_user_message(question, context)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_user_message(
        self,
        question: str,
        context: AnswerContext,
    ) -> str:
        """Build enriched user message with context."""
        parts = []

        # Add findings context
        if context.findings:
            parts.append("## Current Security Findings\n")
            for finding in context.findings[:5]:  # Top 5
                parts.append(f"- **{finding.title}** ({finding.severity})")
                parts.append(f"  Resource: {finding.resource_id}")
                parts.append(f"  Compliance: {', '.join(finding.compliance_frameworks)}")
            parts.append("")

        # Add compliance context
        if context.kb_entries:
            parts.append("## Relevant Compliance Requirements\n")
            for entry in context.kb_entries[:5]:
                parts.append(f"- **{entry.framework}**: {entry.control_name}")
                parts.append(f"  {entry.description[:200]}...")
            parts.append("")

        # Add document context
        if context.documents:
            parts.append("## Architecture Context\n")
            for doc in context.documents:
                parts.append(f"From document '{doc.filename}':")
                parts.append(doc.summary[:500])
            parts.append("")

        # Add the actual question
        parts.append("## User Question\n")
        parts.append(question)

        return "\n".join(parts)


@dataclass
class AnswerContext:
    kb_entries: list[KBEntry] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    documents: list[DocumentContext] = field(default_factory=list)
```

### Streaming Handler

```python
# src/ib_platform/answer/streaming.py
import asyncio
from typing import AsyncIterator
import json

class StreamingHandler:
    """Handle SSE streaming of answer chunks."""

    def __init__(self, answer_service: AnswerService):
        self.answer_service = answer_service

    async def stream_answer(
        self,
        question: str,
        nlu_result: NLUResult,
        tenant_id: UUID,
        conversation_history: list[dict],
    ) -> AsyncIterator[str]:
        """Generate SSE events for streaming response."""
        try:
            # Send start event
            yield self._sse_event("start", {"type": "start"})

            # Stream answer chunks
            full_response = ""
            async for chunk in self.answer_service.generate(
                question, nlu_result, tenant_id, conversation_history
            ):
                full_response += chunk
                yield self._sse_event("chunk", {"content": chunk})

            # Send completion event with metadata
            yield self._sse_event("done", {
                "type": "done",
                "intent": nlu_result.intent.value,
                "entities": nlu_result.entities.aws_services,
            })

        except Exception as e:
            yield self._sse_event("error", {
                "type": "error",
                "message": str(e),
            })

    def _sse_event(self, event: str, data: dict) -> str:
        """Format as SSE event."""
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# FastAPI endpoint
@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    tenant_id: UUID = Depends(get_tenant_id),
):
    async def generate():
        # Process through NLU
        nlu_result = await nlu_service.process(
            request.message, request.conversation_history
        )

        # Stream answer
        async for event in streaming_handler.stream_answer(
            request.message,
            nlu_result,
            tenant_id,
            request.conversation_history,
        ):
            yield event

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

### Response Formatter

```python
# src/ib_platform/answer/formatter.py
class ResponseFormatter:
    """Format responses with consistent structure."""

    @staticmethod
    def format_security_advice(
        content: str,
        findings: list[Finding] = None,
        compliance: list[str] = None,
    ) -> str:
        """Format security advice response."""
        parts = [content]

        if findings:
            parts.append("\n---\n")
            parts.append("**Related Findings:**\n")
            for f in findings[:3]:
                parts.append(f"- [{f.rule_id}] {f.title} ({f.severity})")

        if compliance:
            parts.append("\n**Compliance Frameworks:**")
            parts.append(", ".join(compliance))

        return "\n".join(parts)

    @staticmethod
    def format_remediation(
        title: str,
        steps: list[str],
        code: str = None,
        language: str = "hcl",
    ) -> str:
        """Format remediation guidance."""
        parts = [f"## Remediation: {title}\n"]

        parts.append("### Steps:\n")
        for i, step in enumerate(steps, 1):
            parts.append(f"{i}. {step}")

        if code:
            parts.append(f"\n### Code Example ({language}):\n")
            parts.append(f"```{language}")
            parts.append(code)
            parts.append("```")

        return "\n".join(parts)
```

## API Endpoints

```
POST /api/v1/chat/message           # Send message (returns full response)
POST /api/v1/chat/stream            # Stream response via SSE
GET  /api/v1/chat/stream/:id        # Connect to existing stream
```

## Files to Create

```
src/ib_platform/answer/
├── __init__.py
├── service.py               # Main answer service
├── streaming.py             # SSE streaming handler
├── context.py               # Context assembly
├── formatter.py             # Response formatting
└── prompts.py               # System prompts

tests/ib_platform/answer/
├── test_context_assembly.py
├── test_answer_generation.py
├── test_streaming.py
└── test_formatter.py
```

## Testing Requirements

### Unit Tests
- [ ] `test_context_assembly.py` - Context gathered correctly
- [ ] `test_prompt_building.py` - Messages built correctly
- [ ] `test_formatter.py` - Response formatting

### Integration Tests
- [ ] `test_answer_generation.py` - Full generation with mocked LLM
- [ ] `test_streaming.py` - SSE streaming works

### Test Mocking

```python
@pytest.fixture
def mock_anthropic():
    with patch("anthropic.Anthropic") as mock:
        client = MagicMock()

        # Mock streaming response
        async def mock_stream():
            for chunk in ["Here's ", "my ", "response."]:
                yield chunk

        client.messages.stream.return_value.__aenter__.return_value.text_stream = mock_stream()
        mock.return_value = client
        yield client
```

## Acceptance Criteria Checklist

- [ ] Context assembled from KB, findings, documents
- [ ] Expert-level prompting produces quality responses
- [ ] Responses include compliance framework references
- [ ] Severity indicators used appropriately
- [ ] Remediation steps included for findings
- [ ] SSE streaming works smoothly
- [ ] Conversation history maintained
- [ ] Response time <3 seconds to first chunk
- [ ] 80%+ test coverage

## Dependencies

- 8.1 NLU Pipeline (provides NLU result)
- 8.5 Knowledge Base (provides KB context)
- 7.4 Findings Management (provides findings)

## Blocked By

- 8.1 NLU Pipeline

## Blocks

- 6.5 Chat Interface (uses streaming)

## Estimated Effort

1.5 weeks

## Labels

`answer-generation`, `ib`, `ai`, `streaming`, `mvp`, `phase-2`, `P0`
