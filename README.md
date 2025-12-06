# Cloud Optimizer v2

**Cloud cost optimization and Well-Architected Framework analysis - built on Intelligence-Builder platform**

[![CI](https://github.com/Intelligence-Builder/Cloud-Optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/Intelligence-Builder/Cloud-Optimizer/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## Overview

Cloud Optimizer v2 is a **clean-slate rebuild** of the cloud optimization system, designed as a thin application layer on top of the [Intelligence-Builder](https://github.com/Intelligence-Builder/intelligence-builder) GraphRAG platform.

### Design Principles

- **Platform-First**: All knowledge graph operations use Intelligence-Builder via SDK
- **Clean & Minimal**: Target < 10K lines of code
- **Enterprise-Grade**: 80%+ test coverage, type hints, comprehensive docs
- **Domain-Focused**: 5 AWS Well-Architected pillars as domains

### Architecture

```
┌─────────────────────────────────────────────┐
│           Cloud Optimizer v2                │
│  ┌───────────────────────────────────────┐  │
│  │            FastAPI App                │  │
│  │  • AWS Integration                    │  │
│  │  • Business Logic                     │  │
│  │  • Dashboard APIs                     │  │
│  └───────────────────┬───────────────────┘  │
│                      │                       │
│         Intelligence-Builder SDK            │
│                      │                       │
└──────────────────────┼──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│      Intelligence-Builder Platform          │
│  • Knowledge Graph (PostgreSQL/Memgraph)    │
│  • Pattern Detection Engine                 │
│  • Domain Registry                          │
│  • Vector Search                            │
└─────────────────────────────────────────────┘
```

---

## Domains

Cloud Optimizer implements the 5 AWS Well-Architected Framework pillars:

| Domain | Description | Priority |
|--------|-------------|----------|
| **Security** | Vulnerability detection, compliance, access analysis | HIGH |
| Cost Optimization | Savings opportunities, rightsizing, reservations | Medium |
| Performance | Bottlenecks, scaling, latency optimization | Medium |
| Reliability | Single points of failure, DR, availability | Medium |
| Operational Excellence | Automation, monitoring, runbooks | Medium |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Access to Intelligence-Builder platform

### Installation

```bash
# Clone the repository
git clone https://github.com/Intelligence-Builder/Cloud-Optimizer.git
cd Cloud-Optimizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run the application
uvicorn cloud_optimizer.main:app --reload
```

### Configuration

```bash
# Required environment variables
IB_PLATFORM_URL=http://localhost:8000    # Intelligence-Builder URL
IB_API_KEY=your-api-key                   # IB platform API key
IB_TENANT_ID=your-tenant                  # Tenant ID

# AWS credentials (for scanning)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_DEFAULT_REGION=us-east-1
```

---

## Development

### Project Structure

```
cloud-optimizer/
├── src/cloud_optimizer/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── api/
│   │   └── routers/         # API endpoints
│   ├── services/            # Business logic
│   │   └── intelligence_builder.py  # IB SDK client
│   ├── domains/             # Future: Domain-specific extensions
│   ├── scanners/            # AWS service scanners (EC2, IAM, S3, RDS, Lambda, etc.)
│   ├── integrations/
│   │   └── aws/             # AWS integration
│   └── models/              # Data models
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker/
├── docs/
└── pyproject.toml
```

### Quality Standards

| Metric | Requirement |
|--------|-------------|
| Test Coverage | > 80% |
| Max File Size | < 500 lines |
| Cyclomatic Complexity | < 10 per function |
| Type Hints | 100% functions |

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cloud_optimizer --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/
mypy src/

# Pre-commit (runs all checks)
pre-commit run --all-files
```

---

## API Documentation

Once running, access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Related Projects

- [Intelligence-Builder](https://github.com/Intelligence-Builder/intelligence-builder) - Core GraphRAG platform
- [Smart-Scaffold](https://github.com/Intelligence-Builder/smart-scaffold) - Development workflow tooling
