# 8.1 NLU Pipeline

## Parent Epic
Epic 8: MVP Phase 2 - Expert System (Intelligence-Builder)

## Overview

Implement the Natural Language Understanding pipeline that processes user questions to extract intent, entities, and context for answer generation. Uses LLM-based classification for flexibility and accuracy.

## Background

The NLU pipeline is the entry point for all user questions. It must:
- Classify question intent (security advice, finding explanation, compliance question)
- Extract entities (AWS services, compliance frameworks, resources)
- Build context from conversation history
- Handle multi-turn conversations

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| NLU-001 | Intent classification | Classify into security_advice, finding_explanation, compliance_question, document_analysis, general_question |
| NLU-002 | Entity extraction | Extract AWS services, compliance frameworks, resources, severity levels |
| NLU-003 | Context tracking | Track conversation history, reference previous messages |
| NLU-004 | Question analysis | Detect question type, extract key topics, identify required context |

## Technical Specification

### Intent Classification

```python
# src/ib_platform/nlu/intents.py
from enum import Enum

class Intent(Enum):
    SECURITY_ADVICE = "security_advice"          # General security questions
    FINDING_EXPLANATION = "finding_explanation"  # Explain a specific finding
    COMPLIANCE_QUESTION = "compliance_question"  # Compliance-related questions
    DOCUMENT_ANALYSIS = "document_analysis"      # Questions about uploaded docs
    COST_OPTIMIZATION = "cost_optimization"      # Cost-related questions
    REMEDIATION_HELP = "remediation_help"        # How to fix something
    GENERAL_QUESTION = "general_question"        # General cloud/security questions
    GREETING = "greeting"                        # Greetings
    OUT_OF_SCOPE = "out_of_scope"                # Not cloud security related


INTENT_EXAMPLES = {
    Intent.SECURITY_ADVICE: [
        "What security concerns should I have with S3?",
        "Is my Redshift cluster secure?",
        "How should I secure my API Gateway?",
    ],
    Intent.FINDING_EXPLANATION: [
        "Explain this finding about public S3 buckets",
        "What does the IAM_002 finding mean?",
        "Why is this marked as critical?",
    ],
    Intent.COMPLIANCE_QUESTION: [
        "What do I need for HIPAA compliance?",
        "How does this relate to SOC 2?",
        "Is this a PCI-DSS violation?",
    ],
    Intent.DOCUMENT_ANALYSIS: [
        "What security issues do you see in my architecture?",
        "Review this diagram for vulnerabilities",
        "What's missing from my design?",
    ],
    Intent.COST_OPTIMIZATION: [
        "How can I reduce my AWS costs?",
        "Are there unused resources?",
        "Should I use reserved instances?",
    ],
    Intent.REMEDIATION_HELP: [
        "How do I fix this S3 bucket issue?",
        "Show me the Terraform to fix this",
        "What's the remediation for this?",
    ],
}
```

### Entity Extraction

```python
# src/ib_platform/nlu/entities.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class ExtractedEntities:
    aws_services: list[str]           # ["S3", "RDS", "Lambda"]
    compliance_frameworks: list[str]  # ["HIPAA", "SOC2"]
    resource_ids: list[str]           # ["bucket-name", "i-abc123"]
    severity_levels: list[str]        # ["critical", "high"]
    finding_ids: list[str]            # ["S3_001", "IAM_002"]
    regions: list[str]                # ["us-east-1"]
    keywords: list[str]               # Key terms extracted


AWS_SERVICES = {
    "s3": ["s3", "bucket", "buckets", "simple storage"],
    "ec2": ["ec2", "instance", "instances", "virtual machine", "vm"],
    "rds": ["rds", "database", "databases", "aurora", "mysql", "postgres"],
    "iam": ["iam", "user", "users", "role", "roles", "policy", "permission"],
    "lambda": ["lambda", "function", "serverless"],
    "vpc": ["vpc", "network", "subnet", "security group"],
    "kms": ["kms", "key", "encryption"],
    "cloudtrail": ["cloudtrail", "trail", "logging", "audit"],
    "redshift": ["redshift", "warehouse", "data warehouse"],
    "glue": ["glue", "etl", "catalog"],
}

COMPLIANCE_FRAMEWORKS = {
    "hipaa": ["hipaa", "phi", "healthcare", "patient"],
    "soc2": ["soc2", "soc 2", "type 2", "type ii"],
    "pci": ["pci", "pci-dss", "payment", "cardholder"],
    "gdpr": ["gdpr", "privacy", "data protection", "eu"],
    "cis": ["cis", "benchmark", "benchmarks"],
    "nist": ["nist", "800-53", "framework"],
}
```

### NLU Service

```python
# src/ib_platform/nlu/service.py
from anthropic import Anthropic

class NLUService:
    def __init__(self, anthropic_client: Anthropic):
        self.client = anthropic_client

    async def process(self, message: str, conversation_history: list[dict]) -> NLUResult:
        """Process user message through NLU pipeline."""
        # Run intent classification and entity extraction in parallel
        intent_task = asyncio.create_task(self._classify_intent(message))
        entities_task = asyncio.create_task(self._extract_entities(message))

        intent, confidence = await intent_task
        entities = await entities_task

        # Build context from conversation history
        context = self._build_context(conversation_history, entities)

        return NLUResult(
            intent=intent,
            confidence=confidence,
            entities=entities,
            context=context,
            requires_findings=self._requires_findings(intent),
            requires_documents=self._requires_documents(intent, conversation_history),
        )

    async def _classify_intent(self, message: str) -> tuple[Intent, float]:
        """Classify message intent using Claude."""
        prompt = f"""Classify the following user message into one of these intents:
- security_advice: General security questions about AWS services
- finding_explanation: Questions about specific scan findings
- compliance_question: Questions about compliance frameworks (HIPAA, SOC2, etc.)
- document_analysis: Questions about uploaded architecture documents
- cost_optimization: Questions about reducing costs
- remediation_help: Questions about how to fix security issues
- general_question: General cloud questions
- greeting: Greetings or small talk
- out_of_scope: Not related to cloud security

Message: "{message}"

Respond with JSON: {{"intent": "intent_name", "confidence": 0.0-1.0}}"""

        response = await self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )

        result = json.loads(response.content[0].text)
        return Intent(result["intent"]), result["confidence"]

    async def _extract_entities(self, message: str) -> ExtractedEntities:
        """Extract entities from message."""
        message_lower = message.lower()

        # Extract AWS services
        aws_services = []
        for service, keywords in AWS_SERVICES.items():
            if any(kw in message_lower for kw in keywords):
                aws_services.append(service.upper())

        # Extract compliance frameworks
        compliance = []
        for framework, keywords in COMPLIANCE_FRAMEWORKS.items():
            if any(kw in message_lower for kw in keywords):
                compliance.append(framework.upper())

        # Extract finding IDs (pattern: XXX_NNN)
        finding_ids = re.findall(r'\b([A-Z]{2,}_\d{3})\b', message)

        # Extract severity levels
        severities = []
        for sev in ["critical", "high", "medium", "low"]:
            if sev in message_lower:
                severities.append(sev)

        return ExtractedEntities(
            aws_services=aws_services,
            compliance_frameworks=compliance,
            resource_ids=[],  # Extracted later from context
            severity_levels=severities,
            finding_ids=finding_ids,
            regions=[],
            keywords=self._extract_keywords(message),
        )

    def _extract_keywords(self, message: str) -> list[str]:
        """Extract key terms from message."""
        # Simple keyword extraction - could be enhanced with NLP
        stopwords = {"the", "a", "an", "is", "are", "what", "how", "should", "i", "my", "me"}
        words = re.findall(r'\b\w+\b', message.lower())
        return [w for w in words if w not in stopwords and len(w) > 2]

    def _build_context(
        self,
        history: list[dict],
        entities: ExtractedEntities,
    ) -> ConversationContext:
        """Build context from conversation history."""
        # Extract topic thread
        topics = []
        for msg in history[-5:]:  # Last 5 messages
            if msg["role"] == "user":
                topics.extend(self._extract_keywords(msg["content"]))

        # Track mentioned resources
        resources = []
        for msg in history:
            if "resource" in msg.get("metadata", {}):
                resources.append(msg["metadata"]["resource"])

        return ConversationContext(
            topics=list(set(topics)),
            mentioned_services=entities.aws_services,
            mentioned_frameworks=entities.compliance_frameworks,
            active_resources=resources,
            turn_count=len([m for m in history if m["role"] == "user"]),
        )

    def _requires_findings(self, intent: Intent) -> bool:
        """Check if intent requires findings data."""
        return intent in [
            Intent.FINDING_EXPLANATION,
            Intent.REMEDIATION_HELP,
            Intent.SECURITY_ADVICE,
            Intent.COMPLIANCE_QUESTION,
        ]

    def _requires_documents(
        self,
        intent: Intent,
        history: list[dict],
    ) -> bool:
        """Check if intent requires document context."""
        if intent == Intent.DOCUMENT_ANALYSIS:
            return True

        # Check if documents were uploaded in conversation
        for msg in history:
            if msg.get("metadata", {}).get("documents"):
                return True

        return False
```

### NLU Result Model

```python
# src/ib_platform/nlu/models.py
from dataclasses import dataclass

@dataclass
class NLUResult:
    intent: Intent
    confidence: float
    entities: ExtractedEntities
    context: ConversationContext
    requires_findings: bool
    requires_documents: bool

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.7

    def to_dict(self) -> dict:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "entities": {
                "aws_services": self.entities.aws_services,
                "compliance_frameworks": self.entities.compliance_frameworks,
                "finding_ids": self.entities.finding_ids,
            },
            "requires_findings": self.requires_findings,
            "requires_documents": self.requires_documents,
        }


@dataclass
class ConversationContext:
    topics: list[str]
    mentioned_services: list[str]
    mentioned_frameworks: list[str]
    active_resources: list[str]
    turn_count: int
```

## API Integration

```python
# Used internally by chat service
async def handle_message(message: str, conversation_id: str):
    # Get conversation history
    history = await get_conversation_history(conversation_id)

    # Process through NLU
    nlu_result = await nlu_service.process(message, history)

    # Route to appropriate handler based on intent
    if nlu_result.intent == Intent.FINDING_EXPLANATION:
        return await handle_finding_explanation(message, nlu_result)
    elif nlu_result.intent == Intent.COMPLIANCE_QUESTION:
        return await handle_compliance_question(message, nlu_result)
    # ... other handlers
```

## Files to Create

```
src/ib_platform/nlu/
├── __init__.py
├── intents.py               # Intent definitions and examples
├── entities.py              # Entity extraction
├── service.py               # Main NLU service
├── models.py                # NLU result models
└── context.py               # Conversation context tracking

tests/ib_platform/nlu/
├── test_intent_classification.py
├── test_entity_extraction.py
├── test_context_building.py
└── test_nlu_service.py
```

## Testing Requirements

### Unit Tests
- [ ] `test_intent_classification.py` - Each intent classified correctly
- [ ] `test_entity_extraction.py` - AWS services, frameworks extracted
- [ ] `test_context_building.py` - History context built correctly
- [ ] `test_keyword_extraction.py` - Keywords extracted

### Integration Tests
- [ ] `test_nlu_pipeline.py` - Full pipeline with mocked LLM
- [ ] `test_multi_turn.py` - Multi-turn conversation context

### Test Data

```python
TEST_CASES = [
    {
        "message": "What security concerns should I have with patient data in S3 going through Glue to Redshift?",
        "expected_intent": Intent.SECURITY_ADVICE,
        "expected_services": ["S3", "GLUE", "REDSHIFT"],
        "expected_frameworks": ["HIPAA"],  # "patient data" implies HIPAA
    },
    {
        "message": "Explain finding S3_001",
        "expected_intent": Intent.FINDING_EXPLANATION,
        "expected_finding_ids": ["S3_001"],
    },
    {
        "message": "What do I need for SOC 2 compliance?",
        "expected_intent": Intent.COMPLIANCE_QUESTION,
        "expected_frameworks": ["SOC2"],
    },
]
```

## Acceptance Criteria Checklist

- [ ] Intent classification >90% accuracy on test set
- [ ] AWS services extracted from questions
- [ ] Compliance frameworks detected from context
- [ ] Finding IDs extracted (e.g., S3_001)
- [ ] Conversation context tracks topics
- [ ] Multi-turn context preserved
- [ ] Low-confidence detection works
- [ ] Out-of-scope questions handled gracefully
- [ ] 80%+ test coverage

## Dependencies

- Anthropic API access (for Claude)

## Blocked By

- None (first IB component)

## Blocks

- 8.2 Answer Generation (uses NLU output)
- 8.3 Security Analysis (uses intent/entities)

## Estimated Effort

1.5 weeks

## Labels

`nlu`, `ib`, `ai`, `mvp`, `phase-2`, `P0`
