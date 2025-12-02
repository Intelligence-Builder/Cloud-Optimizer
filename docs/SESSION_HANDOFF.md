# Cloud Optimizer v2 - Developer Session Handoff

## Project Overview

**Cloud Optimizer** is an AWS Marketplace Container Product that provides:
- Security scanning of AWS environments
- Cost optimization recommendations
- Compliance mapping (HIPAA, SOC2, PCI-DSS, GDPR, CIS, NIST)
- AI-powered expert guidance via chat interface (Intelligence-Builder)

**Repository**: https://github.com/Intelligence-Builder/Cloud-Optimizer
**Project Board**: https://github.com/orgs/Intelligence-Builder/projects/5

## Current State (2025-12-01)

### Backlog Structure

The MVP backlog consists of **3 Epics** with **15 parent issues** broken into **87 actionable sub-tasks**:

```
Epic 6: Container Foundation (Phase 1) - Issues #22-27
├── #23 - 6.1 Container Packaging → Sub-tasks #40-47 (8 tasks)
├── #24 - 6.2 AWS Marketplace Integration → Sub-tasks #48-53 (6 tasks)
├── #25 - 6.3 Trial Management → Sub-tasks #54-57 (4 tasks)
├── #26 - 6.4 Basic Authentication → Sub-tasks #58-61 (4 tasks)
└── #27 - 6.5 Chat Interface UI → Sub-tasks #62-71 (10 tasks)

Epic 7: Security & Cost Scanning (Phase 2) - Issues #28-33
├── #29 - 7.1 AWS Connection Manager → Sub-tasks #72-76 (5 tasks)
├── #30 - 7.2 Security Scanner → Sub-tasks #77-84 (8 tasks)
├── #31 - 7.3 Cost Scanner → Sub-tasks #85-90 (6 tasks)
├── #32 - 7.4 Findings Management → Sub-tasks #91-95 (5 tasks)
└── #33 - 7.5 Compliance Mapping → Sub-tasks #96-100 (5 tasks)

Epic 8: Expert System / Intelligence-Builder (Phase 2) - Issues #34-39
├── #35 - 8.1 NLU Pipeline → Sub-tasks #101-105 (5 tasks)
├── #36 - 8.2 Answer Generation → Sub-tasks #106-110 (5 tasks)
├── #37 - 8.3 Security Analysis → Sub-tasks #111-115 (5 tasks)
├── #38 - 8.4 Document Analysis → Sub-tasks #116-120 (5 tasks)
└── #39 - 8.5 Knowledge Base → Sub-tasks #121-126 (6 tasks)
```

### Issue Numbering Reference

| Issue # | Description |
|---------|-------------|
| #22 | Epic 6: Container Foundation |
| #23-27 | Phase 1 parent issues |
| #28 | Epic 7: Security & Cost Scanning |
| #29-33 | Phase 2 parent issues (scanning) |
| #34 | Epic 8: Expert System |
| #35-39 | Phase 2 parent issues (IB) |
| #40-71 | Phase 1 sub-tasks (32 total) |
| #72-100 | Phase 2 scanning sub-tasks (29 total) |
| #101-126 | Phase 2 IB sub-tasks (26 total) |

## Getting Started

### 1. View the Backlog

```bash
# List all issues in Backlog status
gh issue list --repo Intelligence-Builder/Cloud-Optimizer --label "mvp" --state open

# View Phase 1 issues only
gh issue list --repo Intelligence-Builder/Cloud-Optimizer --label "phase-1" --state open

# View a specific issue
gh issue view 40 --repo Intelligence-Builder/Cloud-Optimizer
```

### 2. Recommended Starting Point

**Start with Phase 1 (Epic 6)** - these are prerequisites for Phase 2:

1. **#40-47** (Container Packaging) - Create Dockerfile, docker-compose, health checks
2. **#58-61** (Basic Auth) - JWT authentication, user models
3. **#54-57** (Trial Management) - Usage tracking, limits
4. **#62-71** (Chat UI) - React frontend with SSE streaming

### 3. Pick Up an Issue

```bash
# Assign yourself to an issue
gh issue edit 40 --add-assignee @me --repo Intelligence-Builder/Cloud-Optimizer

# Move to In Progress (update project board)
gh issue edit 40 --add-label "in-progress" --repo Intelligence-Builder/Cloud-Optimizer
```

## Technical Context

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy (async) |
| Frontend | React 18, Vite, Tailwind CSS |
| Database | PostgreSQL 15 (with optional Memgraph for graph) |
| AI/LLM | Anthropic Claude API (Haiku for NLU, Sonnet for generation) |
| Infrastructure | Docker, AWS Marketplace Container |
| Testing | pytest, pytest-asyncio, pytest-cov |

### Project Structure

```
cloud-optimizer/
├── src/
│   ├── cloud_optimizer/          # Main application
│   │   ├── api/                  # FastAPI routers
│   │   ├── core/                 # Config, security
│   │   └── models/               # SQLAlchemy models
│   └── ib_platform/              # Intelligence-Builder modules
│       ├── nlu/                  # Natural Language Understanding
│       ├── answer/               # Answer generation
│       ├── security/             # Security analysis
│       ├── document/             # Document processing
│       └── kb/                   # Knowledge base
├── frontend/                     # React application
├── docker/                       # Dockerfile, compose files
├── data/compliance/              # KB YAML files
├── tests/                        # Test suites
├── alembic/                      # Database migrations
└── docs/                         # Documentation
    └── issues/mvp/               # Detailed issue specs
```

### Key Files

| File | Purpose |
|------|---------|
| `docs/issues/mvp/ISSUE_*.md` | Detailed specs for each parent issue |
| `docs/PHASED_IMPLEMENTATION_PLAN.md` | Overall MVP implementation plan |
| `docs/DEPLOYMENT.md` | AWS Marketplace deployment guide |
| `DATABASE_TRUTH.md` | Database credentials and schema |
| `pyproject.toml` | Python dependencies |

### Database Credentials (Local Development)

```yaml
Database: cloudguardian
User: cloudguardian
Password: securepass123
Host: localhost
Port: 5432
Container: cloud-optimizer-postgres
```

## Sub-Task Structure

Each sub-task follows this format:

```markdown
## Parent Issue
#XX - Parent issue title

## Objective
What this task accomplishes

## Implementation
Code snippets showing the approach

## Files to Create
- List of files to create/modify

## Acceptance Criteria
- [ ] Checkboxes for completion

## Estimated Time
2-4 hours
```

## Development Workflow

### 1. Before Starting Work

```bash
# Pull latest
git pull origin main

# Start local services
docker-compose -f docker-compose-dev.yml up -d

# Verify database
PGPASSWORD=securepass123 psql -h localhost -p 5432 -U cloudguardian -d cloudguardian -c "\dt"
```

### 2. Working on an Issue

```bash
# Create feature branch
git checkout -b feature/issue-40-dockerfile

# Make changes following the issue spec
# ...

# Run tests
PYTHONPATH=src pytest tests/ -v

# Run pre-commit hooks
pre-commit run --all-files

# Commit (NEVER use --no-verify)
git add .
git commit -m "Implement multi-stage Dockerfile for container packaging

Closes #40

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 3. Quality Requirements

- **Test Coverage**: 80%+ per module
- **Pre-commit Hooks**: Must pass (black, isort, flake8, mypy)
- **Type Hints**: Required on all functions
- **No Mock Data**: Use real database tests

## Labels Reference

| Label | Meaning |
|-------|---------|
| `mvp` | Part of MVP scope |
| `phase-1` | Container Foundation phase |
| `phase-2` | Scanning & IB phase |
| `P0` | Critical priority |
| `container` | Docker/packaging related |
| `auth` | Authentication related |
| `trial` | Trial management |
| `ui`, `frontend` | React UI work |
| `scanning`, `security` | Security scanner |
| `cost` | Cost optimization |
| `findings` | Findings management |
| `compliance` | Compliance mapping |
| `nlu`, `ai` | NLU pipeline |
| `answer-generation` | Answer service |
| `analysis` | Security analysis |
| `document`, `pdf` | Document processing |
| `kb` | Knowledge base |

## Dependencies Between Issues

```
Phase 1 (Must complete first):
#40-47 (Container) ─┬─> #48-53 (Marketplace)
                    └─> #54-57 (Trial) ─┬─> #58-61 (Auth)
                                        └─> #62-71 (Chat UI)

Phase 2 (After Phase 1):
#72-76 (AWS Connection) ──> #77-84 (Security Scanner) ──┬──> #91-95 (Findings)
                      └──> #85-90 (Cost Scanner) ───────┘        │
                                                                  v
                                                         #96-100 (Compliance)

#101-105 (NLU) ──> #106-110 (Answer Gen) <── #121-126 (KB)
                          │
                          v
              #111-115 (Security Analysis)
                          │
                          v
              #116-120 (Document Analysis)
```

## Quick Commands

```bash
# View all sub-tasks for a parent issue
gh issue list --repo Intelligence-Builder/Cloud-Optimizer --search "in:body #35"

# View issue details
gh issue view 101 --repo Intelligence-Builder/Cloud-Optimizer

# List issues by label
gh issue list --repo Intelligence-Builder/Cloud-Optimizer --label "nlu"

# Create a PR after completing work
gh pr create --title "Implement NLU pipeline" --body "Closes #101, #102, #103"
```

## Session Goals Suggestions

### Option A: Start Phase 1 Container Work
Focus on #40-47 (Container Packaging) - foundational for everything else.

### Option B: Start Phase 1 Auth + Trial
Focus on #54-61 (Trial Management + Basic Auth) - core business logic.

### Option C: Start Phase 2 KB (No Dependencies)
Focus on #121-126 (Knowledge Base) - can be done in parallel, no blockers.

### Option D: Research/Planning
Read through `docs/issues/mvp/` specs to understand full scope before coding.

---

**Last Updated**: 2025-12-01
**Session Summary**: Created 87 sub-tasks from 15 parent issues across 3 epics
