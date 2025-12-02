# Next Session Prompt

Copy and paste this to start your next Claude Code session:

---

## Context

I'm building **Cloud Optimizer v2**, an AWS Marketplace Container Product for security scanning, cost optimization, and AI-powered compliance guidance.

**Repository**: https://github.com/Intelligence-Builder/Cloud-Optimizer
**Project Board**: https://github.com/orgs/Intelligence-Builder/projects/5

## Current State

The backlog has been fully structured:
- **87 sub-tasks** created across 15 parent issues
- Each sub-task is 2-4 hours of work with clear acceptance criteria
- All issues have implementation code snippets and file lists

### Issue Structure

```
Phase 1 (Epic 6 - Container Foundation):
- #40-47: Container Packaging (8 tasks)
- #48-53: AWS Marketplace (6 tasks)
- #54-57: Trial Management (4 tasks)
- #58-61: Basic Auth (4 tasks)
- #62-71: Chat UI (10 tasks)

Phase 2 (Epic 7 - Scanning):
- #72-76: AWS Connection (5 tasks)
- #77-84: Security Scanner (8 tasks)
- #85-90: Cost Scanner (6 tasks)
- #91-95: Findings Management (5 tasks)
- #96-100: Compliance Mapping (5 tasks)

Phase 2 (Epic 8 - Intelligence-Builder):
- #101-105: NLU Pipeline (5 tasks)
- #106-110: Answer Generation (5 tasks)
- #111-115: Security Analysis (5 tasks)
- #116-120: Document Analysis (5 tasks)
- #121-126: Knowledge Base (6 tasks)
```

## Key Documentation

- `docs/SESSION_HANDOFF.md` - Full handoff with technical context
- `docs/issues/mvp/ISSUE_*.md` - Detailed specs for each parent issue
- `docs/PHASED_IMPLEMENTATION_PLAN.md` - Overall MVP plan
- `DATABASE_TRUTH.md` - Database credentials (cloudguardian/securepass123)

## Tech Stack

- Backend: Python 3.11+, FastAPI, SQLAlchemy async
- Frontend: React 18, Vite, Tailwind
- Database: PostgreSQL 15
- AI: Anthropic Claude API
- Container: Docker, AWS Marketplace

## What I Need

[Choose one or describe your goal]:

1. **Start implementing Phase 1** - Begin with container packaging (#40-47) or auth (#58-61)
2. **Start implementing Phase 2** - Begin with KB (#121-126) which has no dependencies
3. **Review specific issues** - Look at issues #X, #Y, #Z and plan implementation
4. **Other**: [describe]

---
