# Epic 8: MVP Phase 2 - Expert System (Intelligence-Builder)

## Overview

Implement the Intelligence-Builder (IB) components that power the expert Q&A system. This includes NLU pipeline for understanding user questions, answer generation with compliance-aware responses, document analysis for architecture review, and security analysis integration.

## Business Value

- **Expert-Level Responses**: Provide security expert-level advice without human experts
- **Document Intelligence**: Analyze architecture documents and provide recommendations
- **Compliance Awareness**: Responses mapped to regulatory requirements
- **Context-Aware**: Answers consider customer's specific AWS environment

## MVP Use Cases Enabled

1. **Security Q&A** - "What security concerns should I have with S3 to Glue to Redshift?"
2. **Document Analysis** - Upload architecture PDF, get security recommendations
3. **Finding Analysis** - "Explain this finding and how to fix it"
4. **Compliance Guidance** - "What do I need for HIPAA compliance?"

## Requirements Summary

| Sub-Issue | Requirements | Count | Priority |
|-----------|--------------|-------|----------|
| 8.1 NLU Pipeline | NLU-001 to NLU-004 | 4 | P0 |
| 8.2 Answer Generation | ANS-001 to ANS-005 | 5 | P0 |
| 8.3 Security Analysis Integration | IB-SEC-001 to IB-SEC-004 | 4 | P0 |
| 8.4 Document Analysis | DOC-001 to DOC-004 | 4 | P0 |
| 8.5 Knowledge Base Integration | KB-001 to KB-003 | 3 | P0 |
| **Total** | | **20** | |

## Architecture Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Intelligence-Builder (IB)                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      NLU Pipeline                                ││
│  │  Question → Intent Classification → Entity Extraction → Context ││
│  └─────────────────────────────────────────────────────────────────┘│
│                              │                                       │
│  ┌───────────────────────────┼───────────────────────────────────┐  │
│  │                    Context Assembly                            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐│  │
│  │  │ Compliance  │  │ Findings    │  │ Document Context        ││  │
│  │  │ KB          │  │ (from CO)   │  │ (uploaded docs)         ││  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘│  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│  ┌───────────────────────────┼───────────────────────────────────┐  │
│  │                   Answer Generation                            │  │
│  │  Context + Question → LLM → Structured Response → Streaming    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Timeline

- **Phase 2**: Weeks 7-12
- **Milestone**: Expert Q&A working with compliance awareness

## Sub-Issues

- [ ] #XX 8.1 NLU Pipeline (NLU-*)
- [ ] #XX 8.2 Answer Generation Engine (ANS-*)
- [ ] #XX 8.3 Security Analysis Integration (IB-SEC-*)
- [ ] #XX 8.4 Document Analysis Service (DOC-*)
- [ ] #XX 8.5 Knowledge Base Integration (KB-*)

## Dependencies

- Epic 6: Container Foundation (running platform)
- Epic 7: Scanning (findings data)

## Success Criteria

1. [ ] User question understood with >90% intent accuracy
2. [ ] Answers include relevant compliance framework references
3. [ ] Document upload extracts architecture entities
4. [ ] Findings explained with actionable remediation
5. [ ] Response streaming works smoothly
6. [ ] 80%+ test coverage on IB code

## Reference Documents

- [IB_STRATEGIC_DESIGN.md](../02-architecture/IB_STRATEGIC_DESIGN.md) - IB architecture
- [REQUIREMENTS_V2.md](../02-architecture/REQUIREMENTS_V2.md) - NLU-*, ANS-*, DOC-* requirements
- [DEPLOYMENT.md](../04-operations/DEPLOYMENT.md) - KB management

## Labels

`epic`, `mvp`, `phase-2`, `ib`, `expert-system`, `P0`
