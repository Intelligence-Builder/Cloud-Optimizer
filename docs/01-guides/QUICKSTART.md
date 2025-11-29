# Cloud Optimizer Quick Start Guide

**Time to First Run:** 10 minutes
**Prerequisites:** Python 3.11+, Docker, Git

---

## 1. Clone and Setup (2 minutes)

```bash
# Clone the repository
git clone https://github.com/Intelligence-Builder/Cloud-Optimizer.git
cd Cloud-Optimizer

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

---

## 2. Start Infrastructure (3 minutes)

```bash
# Start test databases (PostgreSQL, Memgraph)
docker-compose -f docker/docker-compose.test.yml up -d

# Verify containers are running
docker-compose -f docker/docker-compose.test.yml ps
```

**Expected output:**
```
co-test-postgres   Up (healthy)   0.0.0.0:5434->5432
co-test-memgraph   Up (healthy)   0.0.0.0:7688->7687
```

---

## 3. Configure Environment (2 minutes)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings (optional for local development)
# Default settings work for local testing
```

**Key environment variables:**
```bash
# Database (defaults work with docker-compose.test.yml)
TEST_POSTGRES_PORT=5434
TEST_MEMGRAPH_URI=bolt://localhost:7688

# AWS (optional - for real AWS integration)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

---

## 4. Run Tests (3 minutes)

```bash
# Run all IB Platform tests
PYTHONPATH=src pytest tests/ib_platform/ -v

# Expected: 241 passed
```

**Test breakdown:**
- Graph tests: 102 (PostgreSQL + Memgraph backends)
- Pattern tests: 70
- Domain tests: 69

---

## 5. Verify Installation

```python
# Quick verification script
python -c "
from ib_platform.graph import GraphBackendFactory
from ib_platform.patterns import PatternDetector
from ib_platform.domains import DomainRegistry

print('Graph Factory:', GraphBackendFactory)
print('Pattern Detector:', PatternDetector)
print('Domain Registry:', DomainRegistry)
print('All imports successful!')
"
```

---

## Next Steps

### For Development
1. Read [DEVELOPMENT_STANDARDS.md](../03-development/DEVELOPMENT_STANDARDS.md)
2. Review [ARCHITECTURE.md](../02-architecture/ARCHITECTURE.md)
3. Check GitHub issues for available tasks

### For Integration
1. Read [IB_SDK_INTEGRATION.md](../05-integration/IB_SDK_INTEGRATION.md)
2. Review domain patterns in [DOMAIN_PATTERNS.md](../05-integration/DOMAIN_PATTERNS.md)

### For Testing
1. Read [TESTING_GUIDE.md](../03-development/TESTING_GUIDE.md)
2. Run integration tests: `PYTHONPATH=src pytest tests/ib_platform/graph/ -v`

---

## Troubleshooting

### Docker Issues
```bash
# Check container logs
docker logs co-test-postgres
docker logs co-test-memgraph

# Restart containers
docker-compose -f docker/docker-compose.test.yml restart
```

### Port Conflicts
If ports 5434 or 7688 are in use:
```bash
# Check what's using the port
lsof -i :5434
lsof -i :7688

# Update ports in docker-compose.test.yml and conftest.py
```

### Import Errors
```bash
# Ensure PYTHONPATH includes src
export PYTHONPATH=src:$PYTHONPATH

# Or use pip install
pip install -e .
```

---

## Quick Commands Reference

```bash
# Start infrastructure
docker-compose -f docker/docker-compose.test.yml up -d

# Stop infrastructure
docker-compose -f docker/docker-compose.test.yml down

# Run all tests
PYTHONPATH=src pytest tests/ib_platform/ -v

# Run specific test file
PYTHONPATH=src pytest tests/ib_platform/graph/test_postgres_cte.py -v

# Check code quality
python -m black src/ tests/ --check
python -m isort src/ tests/ --check

# Format code
python -m black src/ tests/
python -m isort src/ tests/
```
