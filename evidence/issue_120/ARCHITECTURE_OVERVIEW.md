# LLM Analysis Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application Layer                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   /documents │  │   /security  │  │     /chat    │          │
│  │   endpoints  │  │   endpoints  │  │   endpoints  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
└─────────┼──────────────────┼──────────────────┼───────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Intelligence-Builder Platform                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              DocumentAnalyzer                              │  │
│  │  - Analyzes uploaded documents                            │  │
│  │  - Extracts AWS resources, compliance, security concerns  │  │
│  │  - Returns structured JSON                                 │  │
│  └────────────────────────────┬──────────────────────────────┘  │
│                                │                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         SecurityAnalysisService (Facade)                  │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────────┐  │  │
│  │  │ RiskScorer  │ │FindingExpla- │ │ Remediation      │  │  │
│  │  │             │ │iner (LLM)    │ │ Generator        │  │  │
│  │  └─────────────┘ └──────────────┘ └──────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │ FindingCorrelator                                 │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              EntityExtractor                              │  │
│  │  - Extracts AWS services (S3, EC2, Lambda, etc.)         │  │
│  │  - Identifies compliance frameworks (HIPAA, PCI-DSS)     │  │
│  │  - Finds resource IDs (ARNs, instance IDs)               │  │
│  │  - Detects finding IDs (SEC-001, CVE-2023-12345)         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              AnswerService                                 │  │
│  │  - Generates expert security answers                      │  │
│  │  - Streams responses in real-time                         │  │
│  │  - Integrates KB + findings + documents                   │  │
│  │  - Manages conversation history                           │  │
│  └────────────────────────────┬──────────────────────────────┘  │
│                                │                                  │
└────────────────────────────────┼──────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   Anthropic Claude AI  │
                    │  claude-3-5-sonnet     │
                    └────────────────────────┘
```

## Component Responsibilities

### 1. DocumentAnalyzer
**Input:** Document text (PDF/TXT extracted)
**Output:** Structured analysis JSON
```json
{
  "aws_resources": ["S3", "EC2", "Lambda"],
  "compliance_frameworks": ["HIPAA", "PCI-DSS"],
  "security_concerns": ["Public S3 bucket", "Missing encryption"],
  "key_topics": ["Data Storage", "Access Control"],
  "summary": "Architecture document describing..."
}
```
**LLM Usage:** Claude 3.5 Sonnet for document comprehension

### 2. FindingExplainer
**Input:** Security finding object
**Output:** Human-readable explanation
```json
{
  "finding_id": "abc-123",
  "what_it_means": "Your S3 bucket allows public access...",
  "why_it_matters": "This creates data exposure risk...",
  "technical_details": "The bucket policy allows s3:GetObject...",
  "model_used": "claude-3-5-sonnet-20241022",
  "target_audience": "general"
}
```
**LLM Usage:** Claude 3.5 Sonnet for explanation generation
**Audiences:** general, technical, executive
**Fallback:** Template-based explanations when LLM unavailable

### 3. EntityExtractor
**Input:** User query or document text
**Output:** Structured entities
```python
NLUEntities(
    aws_services=["S3", "Lambda"],
    compliance_frameworks=["SOC2", "HIPAA"],
    finding_ids=["SEC-001"],
    resource_ids=["arn:aws:s3:::my-bucket", "i-1234567890abcdef0"]
)
```
**LLM Usage:** None (regex-based for performance)
**Patterns:** 28 AWS services, 13 compliance frameworks, ARNs, instance IDs

### 4. AnswerService
**Input:** User question + context
**Output:** Expert security answer (streaming or complete)
**Context Sources:**
- Knowledge Base (AWS security best practices)
- Active findings (from security scans)
- Uploaded documents (architecture docs)
- Conversation history (last 10 messages)

**LLM Usage:** Claude 3.5 Sonnet with security expert system prompt

## Data Flow Examples

### Example 1: Document Upload & Analysis
```
1. User uploads architecture.pdf
   ↓
2. TextExtractor extracts text
   ↓
3. DocumentAnalyzer sends to Claude
   ↓
4. Claude returns JSON analysis
   ↓
5. System stores/returns results
```

### Example 2: Security Finding Explanation
```
1. Scanner finds "Public S3 bucket"
   ↓
2. FindingExplainer formats prompt
   ↓
3. Claude generates explanation
   ↓
4. Response parsed into sections
   ↓
5. Returned to user (general/technical/executive)
```

### Example 3: Chat Query
```
1. User asks "How do I secure my S3 buckets?"
   ↓
2. EntityExtractor identifies: S3
   ↓
3. NLUService determines intent: security_best_practices
   ↓
4. ContextAssembler gathers:
   - KB entries about S3 security
   - Active S3 findings
   - S3-related documents
   ↓
5. AnswerService generates response
   ↓
6. Streams answer in real-time
```

## LLM Integration Points

| Component | LLM Used | Purpose | Fallback |
|-----------|----------|---------|----------|
| DocumentAnalyzer | Claude 3.5 Sonnet | Document comprehension | Keyword extraction |
| FindingExplainer | Claude 3.5 Sonnet | Human explanation | Template-based |
| AnswerService | Claude 3.5 Sonnet | Conversational AI | Error message |
| EntityExtractor | None | Entity extraction | N/A (regex only) |

## Configuration

All LLM components use environment variable:
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

Default model: `claude-3-5-sonnet-20241022`
- Max tokens: 2000-3000 (configurable)
- Temperature: 0.0 (deterministic for analysis)
- Temperature: default (for conversational answers)

## Error Handling Strategy

1. **API Key Missing**
   - DocumentAnalyzer: Raises AnalysisError
   - FindingExplainer: Silent fallback to templates
   - AnswerService: HTTP 503 error

2. **LLM API Failure**
   - Catches exceptions
   - Returns user-friendly error messages
   - Logs error details

3. **Invalid Response**
   - JSON parsing with error recovery
   - Falls back to keyword extraction
   - Never crashes user request

## Performance Considerations

- **Token Limits:** Documents truncated at 100k chars (~25k tokens)
- **Batch Processing:** FindingExplainer supports batch mode
- **Streaming:** AnswerService streams for better UX
- **Caching:** Not implemented (future enhancement)

## Test Coverage Summary

| Component | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| DocumentAnalyzer | 10 | 90% | 9/10 pass |
| FindingExplainer | 16 | 100% | 16/16 pass |
| EntityExtractor | 44 | 100% | 44/44 pass |
| AnswerService | 9 | 100% | 9/9 pass |
| **Total** | **79** | **98.7%** | **78/79 pass** |
