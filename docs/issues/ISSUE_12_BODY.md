## Parent Epic
Part of #3 (Epic 3: Cloud Optimizer v2 Clean Rebuild)

## Reference Documentation
- **See `docs/platform/TECHNICAL_DESIGN.md` for IB platform specs**
- **See `docs/AI_DEVELOPER_GUIDE.md` for CO v2 development standards**

## Objective
Set up new clean repository with proper CI/CD and quality gates.

## Repository Structure
```
cloud-optimizer/
├── .github/
│   └── workflows/
│       ├── ci.yml              # CI pipeline
│       ├── release.yml         # Release workflow
│       └── codeql.yml          # Security scanning
├── src/
│   └── cloud_optimizer/
│       ├── __init__.py
│       ├── main.py             # FastAPI app entry
│       ├── config.py           # Settings management
│       └── ...
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   └── test_services/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .pre-commit-config.yaml
├── .gitignore
└── README.md
```

## CI/CD Pipeline (ci.yml)
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pre-commit run --all-files
      - run: pytest --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v4

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff mypy
      - run: ruff check src/
      - run: mypy src/
```

## Pre-commit Configuration
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.3.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
```

## Docker Configuration
```dockerfile
# docker/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
CMD ["uvicorn", "cloud_optimizer.main:app", "--host", "0.0.0.0"]
```

## pyproject.toml
```toml
[project]
name = "cloud-optimizer"
version = "2.0.0"
requires-python = ">=3.11"

[tool.black]
line-length = 88

[tool.isort]
profile = "black"

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## Acceptance Criteria
- [ ] Repository structure matches design
- [ ] CI pipeline runs on push/PR
- [ ] Pre-commit hooks configured and working
- [ ] Docker build succeeds
- [ ] README with setup instructions
- [ ] .gitignore covers Python, IDE, env files
- [ ] requirements.txt and requirements-dev.txt split
- [ ] pyproject.toml with tool configurations
- [ ] GitHub Actions badge in README
