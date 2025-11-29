# Smart-Scaffold Integration Guide

**Project:** Cloud-Optimizer
**Created:** 2025-11-29
**Purpose:** Guide for using Smart-Scaffold with Cloud-Optimizer project

---

## What is Smart-Scaffold?

Smart-Scaffold is an AI development companion that enhances your coding experience by providing:
- **Knowledge Graph** - Project memory across sessions
- **Quality Gates** - Automatic quality checking before commits
- **GitHub Integration** - Enhanced issue creation with UKG references
- **Multi-Project Support** - Separate context for each project
- **Coordinated Agents** - Multiple AI agents working together

---

## Quick Start

### 1. Prerequisites

Ensure Smart-Scaffold is running:
```bash
cd /users/robertstanley/desktop/smart-scaffold

# Start Smart-Scaffold services
docker-compose up -d

# Verify services are healthy
docker-compose ps
```

**Expected Services:**
- smart-scaffold-postgres (port 5433)
- smart-scaffold-redis (port 6386)
- smart-scaffold-memgraph (ports 7687, 7444)

### 2. Initialize Cloud-Optimizer Project

```bash
cd /Users/robertstanley/desktop/Cloud-Optimizer

# Initialize Smart-Scaffold for this project
smart-scaffold init

# Add GitHub integration
smart-scaffold auth github
```

### 3. Seed Knowledge Graph

```bash
# Seed KG with project data
smart-scaffold kg seed-project --source all

# Verify seeding
smart-scaffold status
```

### 4. Access Smart-Scaffold Dashboard

Open in browser:
- **Dashboard:** http://localhost:8080
- **Grafana:** http://localhost:3000 (admin/admin)
- **Prometheus:** http://localhost:9090

---

## Configuration

The `.smart-scaffold.yml` file configures Smart-Scaffold for Cloud-Optimizer:

### Key Settings

```yaml
project:
  name: Cloud-Optimizer
  repository: Intelligence-Builder/Cloud-Optimizer

quality_gates:
  required_coverage: 80%    # Target test coverage
  required_docs: true       # Documentation required
  required_tests: true      # Tests required
  max_file_lines: 500       # No file over 500 lines

epics:
  - Epic 1: Platform Foundation
  - Epic 2: Security Domain Implementation
  - Epic 3: Cloud Optimizer v2 Clean Rebuild
  - Epic 4: Remaining Cloud Optimizer Pillars
  - Epic 5: Smart-Scaffold Integration
```

---

## Creating Issues with Smart-Scaffold

### Basic Issue Creation

```bash
# Create issue with UKG references
smart-scaffold github create \
  --title "Implement cost analysis endpoint" \
  --labels "cost,feature,high" \
  --file docs/issues/COST_ANALYSIS.md \
  --enable-references \
  --create-evidence-dir
```

### Issue with Epic Assignment

```bash
# Create issue and assign to epic
smart-scaffold github create \
  --title "Add CVE detection patterns" \
  --labels "security,feature" \
  --epic "Epic 2: Security Domain Implementation" \
  --enable-references
```

### Simplified Alias

```bash
# Using 's' alias
smart-scaffold s issue \
  --title "Issue Title" \
  --labels "priority-high"
```

### What Gets Added Automatically

When you create an issue with `--enable-references`, Smart-Scaffold automatically adds:

1. **Relevant Standards** (3-5 per issue)
   - Code quality standards
   - Security best practices
   - Testing requirements

2. **Architectural Patterns** (2-4 per issue)
   - SDK usage patterns
   - Integration patterns

3. **Similar Completed Issues**
   - Historical learning from past work
   - Solutions that worked
   - Common pitfalls to avoid

4. **Evidence Directory**
   - Automatically created structure
   - Ready for test results and validation

---

## Cloud-Optimizer Specific Workflows

### Workflow 1: Implement Security Feature

```bash
# 1. Create feature issue
smart-scaffold github create \
  --title "Implement vulnerability analysis via IB SDK" \
  --labels "security,feature,high" \
  --epic "Epic 2: Security Domain Implementation" \
  --enable-references

# 2. Get UKG context for security patterns
smart-scaffold ukg query \
  --context security_implementation \
  --query "vulnerability detection patterns"

# 3. Create evidence directory
mkdir -p evidence/security_analysis

# 4. Execute implementation using IB SDK
# ... perform implementation work ...

# 5. Update issue with progress
smart-scaffold github update <issue-number> \
  --comment "Completed vulnerability detection endpoint" \
  --label "in-progress"
```

### Workflow 2: AWS Integration Task

```bash
# Create issue for AWS integration
smart-scaffold github create \
  --title "Add Well-Architected Framework assessment" \
  --labels "aws,feature,high" \
  --epic "Epic 4: Remaining Cloud Optimizer Pillars" \
  --body "$(cat <<'EOF'
## Objective
Implement WAF assessment using IB platform for analysis

## Integration Points
- IB SDK for pattern detection
- AWS SDK for resource scanning
- Security domain for findings

## Tasks
- [ ] Define AWS resource scanning
- [ ] Map findings to IB entities
- [ ] Create assessment report endpoint
- [ ] Add test coverage >80%
EOF
)" \
  --enable-references
```

---

## Using the Knowledge Graph

### Query for Context

```bash
# Get security implementation context
smart-scaffold ukg query \
  --context security_implementation \
  --query "CVE detection best practices"

# Get IB SDK patterns
smart-scaffold ukg query \
  --context platform_integration \
  --query "Intelligence-Builder SDK usage"

# Get AWS integration patterns
smart-scaffold ukg query \
  --context aws_integration \
  --query "Well-Architected Framework analysis"
```

### Add Knowledge to Graph

```bash
# Add important decision to UKG
smart-scaffold ukg add \
  --type decision \
  --title "Use IB SDK for all graph operations" \
  --context architecture_decisions \
  --reference docs/02-architecture/STRATEGIC_DESIGN.md

# Add implementation pattern
smart-scaffold ukg add \
  --type pattern \
  --title "Security analysis endpoint pattern" \
  --context security_implementation
```

---

## Quality Gates

Smart-Scaffold automatically checks:

### Pre-Commit Checks
- Code coverage >= 80%
- All tests passing
- Documentation present
- Type hints on all functions
- No security vulnerabilities
- Import paths valid
- No file > 500 lines

### Issue Quality Checks
- Clear acceptance criteria
- UKG references included
- Epic assignment (for major work)
- Proper labels applied
- Evidence directory created

---

## Cloud-Optimizer Epics

The project has 5 main epics configured:

### Epic 1: Platform Foundation
**Priority:** Critical
**Labels:** platform, critical
**Issues:** #6, #7, #8

- Graph Database Abstraction Layer
- Pattern Engine Core
- Domain Module System

### Epic 2: Security Domain Implementation
**Priority:** High
**Labels:** security, high
**Issues:** #9, #10, #11

- Security Domain Definition
- Security Patterns Implementation
- Security API Endpoints

### Epic 3: Cloud Optimizer v2 Clean Rebuild
**Priority:** High
**Labels:** cloud-optimizer, high
**Issues:** #12, #13, #14

- Repository Foundation
- Core Application Structure
- Security Domain Integration

### Epic 4: Remaining Cloud Optimizer Pillars
**Priority:** Medium
**Labels:** cloud-optimizer, medium
**Issues:** #15, #16, #17, #18

- Cost Optimization Domain
- Performance Efficiency Domain
- Reliability Domain
- Operational Excellence Domain

### Epic 5: Smart-Scaffold Integration
**Priority:** Medium
**Labels:** smart-scaffold, medium
**Issues:** #19, #20, #21

- Smart-Scaffold KG Migration
- Context System Integration
- Production Cutover

---

## Project Structure with Smart-Scaffold

```
Cloud-Optimizer/
├── .smart-scaffold.yml           # Smart-Scaffold config
├── evidence/                     # Created by Smart-Scaffold
│   ├── security_analysis/
│   ├── aws_integration/
│   └── cost_optimization/
├── docs/
│   ├── 01-guides/                # Getting started guides
│   ├── 02-architecture/          # Architecture docs
│   ├── 03-development/           # Development standards
│   ├── 04-operations/            # Operations guides
│   ├── 05-integration/           # Integration docs
│   └── issues/                   # Issue templates
├── src/
│   ├── cloud_optimizer/          # Application code
│   └── ib_platform/              # IB Platform components
└── tests/                        # Test suite
```

---

## Best Practices

### 1. Always Enable UKG References

```bash
# Good: Includes automatic references
smart-scaffold github create \
  --enable-references \
  --create-evidence-dir

# Bad: Missing context and standards
smart-scaffold github create
```

### 2. Assign to Epics

Group related work under epics for better tracking:

```bash
smart-scaffold github create \
  --epic "Epic 2: Security Domain Implementation"
```

### 3. Update Knowledge Graph

After completing major work, add learnings to UKG:

```bash
smart-scaffold ukg add \
  --type lesson \
  --title "IB SDK pattern detection is fast" \
  --context platform_integration
```

### 4. Use Evidence Directories

Always create evidence directories for validation:

```bash
smart-scaffold github create \
  --create-evidence-dir
```

---

## Troubleshooting

### Smart-Scaffold Not Running

```bash
cd /users/robertstanley/desktop/smart-scaffold
docker-compose ps

# Restart if needed
docker-compose restart
```

### Cannot Connect to Knowledge Graph

```bash
# Check Memgraph is healthy
docker exec smart-scaffold-memgraph mgconsole --version

# Restart Memgraph
docker-compose restart memgraph
```

### GitHub Authentication Failed

```bash
# Re-authenticate
smart-scaffold auth github --force
```

### Quality Gates Failing

```bash
# Check what's failing
smart-scaffold check

# Get specific error details
smart-scaffold check --verbose
```

---

## Quick Command Reference

```bash
# Project setup
smart-scaffold init
smart-scaffold auth github

# Seed knowledge graph
smart-scaffold kg seed-project --source all

# Issue creation
smart-scaffold github create --enable-references --create-evidence-dir
smart-scaffold s issue  # Simplified alias

# Knowledge graph
smart-scaffold ukg query --context <context>
smart-scaffold ukg add --type <type>

# Quality checks
smart-scaffold check
smart-scaffold test coverage

# Monitoring
open http://localhost:8080  # Dashboard
open http://localhost:3000  # Grafana

# Work automation
smart-scaffold backlog process <issue-number>
smart-scaffold agents coordinate --task "<task>"
```

---

## Related Documentation

- [SMART_SCAFFOLD_PROCESS_EXAMPLE.md](../05-integration/SMART_SCAFFOLD_PROCESS_EXAMPLE.md) - Real example walkthrough
- [SMART_SCAFFOLD_PROCESS_SUMMARY.md](../05-integration/SMART_SCAFFOLD_PROCESS_SUMMARY.md) - Process summary
- [ARCHITECTURE.md](../02-architecture/ARCHITECTURE.md) - System architecture

---

**Integration Status:** Configured and ready
**Last Updated:** 2025-11-29
