# Epic 3: Cloud Optimizer v2 Clean Rebuild

## Overview

Create a clean, enterprise-grade Cloud Optimizer v2 application that consumes Intelligence-Builder platform services via SDK. Target: < 10K LOC.

**Duration**: 4-6 weeks
**Priority**: High
**Dependencies**: Epic 2 (Security Domain) complete

## Objectives

1. Set up new clean repository with proper CI/CD and quality gates
2. Build core application structure with FastAPI and IB SDK integration
3. Implement Security domain features with AWS integration

## Repository Structure

```
cloud-optimizer-v2/
├── .github/workflows/
├── src/cloud_optimizer/
│   ├── main.py           # FastAPI app
│   ├── config.py         # Configuration
│   ├── ib_client.py      # IB SDK client
│   ├── services/         # Business logic
│   ├── api/              # API layer
│   └── integrations/aws/ # AWS integration
├── tests/
├── docker/
└── docs/
```

## Deliverables

### 3.1 Repository Foundation
- GitHub repository setup
- Project structure with clean layout
- CI/CD pipeline with GitHub Actions
- Pre-commit hooks (black, isort, flake8, mypy)
- Docker development environment

### 3.2 Core Application Structure
- FastAPI application with proper lifecycle
- Configuration management
- IB SDK client connection
- Health check endpoints
- Logging and monitoring

### 3.3 Security Domain Integration
- Security service with CO-specific logic
- AWS security scanning (security groups, IAM, encryption)
- Security API endpoints
- Security dashboard endpoints

## Acceptance Criteria

- [ ] Repository clean and minimal (< 10K LOC target, < 5K ideal)
- [ ] Application starts and connects to IB platform
- [ ] Security scanning works with AWS credentials
- [ ] Findings pushed to IB successfully
- [ ] Dashboard displays security metrics
- [ ] Code coverage > 80%
- [ ] All quality gates passing
- [ ] No file > 500 lines

## Sub-Tasks

1. New Repository Setup (Week 1)
2. Core Application Structure (Week 1-2)
3. Security Domain Integration (Week 2-4)
4. AWS Integration (Week 3-4)
5. Dashboard and Reporting (Week 4-6)
