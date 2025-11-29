# Smart-Scaffold Integration Guide

**Project:** Cloud-Optimizer V2
**Created:** 2025-11-28
**Purpose:** Guide for using Smart-Scaffold with Cloud-Optimizer V2 project

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
- smart-scaffold-app (ports 8080, 8090)
- smart-scaffold-postgres (port 5433)
- smart-scaffold-redis (port 6386)
- smart-scaffold-memgraph (ports 7687, 7444)
- smart-scaffold-prometheus (port 9090)
- smart-scaffold-grafana (port 3000)

### 2. Initialize Cloud-Optimizer V2 Project

```bash
cd /Users/robertstanley/desktop/Cloud-Optimizer

# Initialize Smart-Scaffold for this project
smart-scaffold init

# Add GitHub integration
smart-scaffold auth github
```

### 3. Access Smart-Scaffold Dashboard

Open in browser:
- **Dashboard:** http://localhost:8080
- **Metrics:** http://localhost:8090
- **Grafana:** http://localhost:3000 (admin/admin)
- **Prometheus:** http://localhost:9090

---

## Configuration

The `.smart-scaffold.yml` file configures Smart-Scaffold for Cloud-Optimizer V2:

### Key Settings

```yaml
project:
  name: Cloud-Optimizer
  repository: Intelligence-Builder/Cloud-Optimizer

quality_gates:
  required_coverage: 80%    # Target test coverage
  required_docs: true       # Documentation required
  required_tests: true      # Tests required

epics:
  - Security Domain Implementation
  - AWS Integration
  - Cost Optimization Features
  - Performance Pillar
  - Reliability Pillar
```

---

## Creating Issues with Smart-Scaffold

### Basic Issue Creation

```bash
# Create issue with UKG references
smart-scaffold github create \
  --title "Implement security analysis endpoint" \
  --labels "security,feature,high" \
  --file docs/issues/SECURITY_ANALYSIS.md \
  --enable-references \
  --create-evidence-dir
```

### Issue with Epic Assignment

```bash
# Create issue and assign to epic
smart-scaffold github create \
  --title "Add CVE detection patterns" \
  --labels "security,feature" \
  --epic "Security Domain Implementation" \
  --enable-references
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

## Cloud-Optimizer V2 Specific Workflows

### Workflow 1: Implement Security Feature

```bash
# 1. Create feature issue
smart-scaffold github create \
  --title "Implement vulnerability analysis via IB SDK" \
  --labels "security,feature,high" \
  --epic "Security Domain Implementation" \
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
  --epic "AWS Integration" \
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
  --reference docs/platform/STRATEGIC_DESIGN.md

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

## Cloud-Optimizer V2 Epics

The project has these main epics configured:

### Epic 1: Security Domain Implementation
**Priority:** Critical
**Labels:** security, critical

Issues:
- Implement vulnerability detection
- Add compliance checking
- Create threat analysis endpoints
- Integrate with IB pattern engine

### Epic 2: AWS Integration
**Priority:** High
**Labels:** aws, integration

Issues:
- Resource scanning
- Well-Architected Framework assessment
- Cost analysis integration
- Performance metrics collection

### Epic 3: Cost Optimization
**Priority:** High
**Labels:** cost, optimization

Issues:
- Cost trend analysis
- Savings recommendations
- Resource right-sizing
- Reserved instance analysis

### Epic 4: Performance & Reliability
**Priority:** Medium
**Labels:** performance, reliability

Issues:
- Performance pillar assessment
- Reliability analysis
- Operational excellence checks

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
│   ├── platform/                 # IB platform design docs
│   ├── smart-scaffold/           # This documentation
│   └── issues/                   # Issue templates
├── src/cloud_optimizer/
│   ├── services/
│   │   └── intelligence_builder.py  # IB SDK integration
│   └── routers/
│       └── security.py           # Security API endpoints
└── tests/
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
  --epic "Security Domain Implementation"
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

## Quick Command Reference

```bash
# Project setup
smart-scaffold init
smart-scaffold auth github

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

- [SMART_SCAFFOLD_PROCESS_EXAMPLE.md](./SMART_SCAFFOLD_PROCESS_EXAMPLE.md) - Real example walkthrough
- [SMART_SCAFFOLD_PROCESS_SUMMARY.md](./SMART_SCAFFOLD_PROCESS_SUMMARY.md) - Process summary
- [../platform/STRATEGIC_DESIGN.md](../platform/STRATEGIC_DESIGN.md) - IB Platform architecture

---

**Integration Status:** Ready for configuration
**Last Updated:** 2025-11-28
