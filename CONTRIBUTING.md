# Contributing to Cloud Optimizer

Thank you for your interest in contributing to Cloud Optimizer! This document provides guidelines and information for contributors.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to maintain a welcoming and inclusive community.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- AWS CLI configured (for integration tests)
- Git

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Intelligence-Builder/Cloud-Optimizer.git
   cd Cloud-Optimizer
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Start development services:
   ```bash
   docker-compose up -d postgres
   ```

4. Run migrations:
   ```bash
   PYTHONPATH=src alembic upgrade head
   ```

5. Start the development server:
   ```bash
   PYTHONPATH=src uvicorn cloud_optimizer.main:app --reload
   ```

## Development Workflow

### Branch Naming

Use descriptive branch names:
- `feature/issue-{number}-{short-description}` - New features
- `fix/issue-{number}-{short-description}` - Bug fixes
- `docs/issue-{number}-{short-description}` - Documentation updates
- `refactor/issue-{number}-{short-description}` - Code refactoring

### Commit Messages

Follow conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Code Style

- Follow PEP 8 style guidelines
- Use Black for code formatting (line length: 88)
- Use isort for import sorting
- Add type hints to all functions
- Write docstrings for public functions and classes

## Pull Request Process

### Before Submitting

1. **Run pre-commit hooks**:
   ```bash
   pre-commit run --all-files
   ```

2. **Run tests**:
   ```bash
   PYTHONPATH=src pytest tests/ -v
   ```

3. **Check code coverage** (minimum 80%):
   ```bash
   PYTHONPATH=src pytest tests/ --cov=src --cov-report=term-missing
   ```

4. **Verify type hints**:
   ```bash
   mypy src/
   ```

### PR Requirements

- Link the PR to a GitHub issue
- Provide a clear description of changes
- Include test coverage for new code
- Update documentation if needed
- Ensure all CI checks pass

### Code Review Process

1. **All PRs require at least one approval** before merging
2. Reviewers check for:
   - Code quality and style compliance
   - Test coverage and correctness
   - Security considerations
   - Documentation updates
   - Performance implications

3. Address all review comments before merging
4. Use "Squash and merge" for feature branches

### Automated Checks

All PRs must pass:
- Pre-commit hooks (formatting, linting)
- Unit tests
- Integration tests
- Type checking
- Security scanning (Bandit)
- Dependency vulnerability scanning

## Testing Guidelines

### Test Structure

```
tests/
├── unit/           # Unit tests (fast, no external deps)
├── integration/    # Integration tests (may use databases)
├── e2e/           # End-to-end tests (full system)
├── compliance/    # SOC 2 compliance tests
└── scanners/      # Security scanner tests
```

### Writing Tests

- Use pytest for all tests
- Use fixtures for common setup
- Mock external dependencies in unit tests
- Use real services in integration tests (via Docker)
- Aim for 80%+ code coverage

### Running Tests

```bash
# All tests
PYTHONPATH=src pytest tests/ -v

# Specific category
PYTHONPATH=src pytest tests/unit/ -v

# With coverage
PYTHONPATH=src pytest tests/ --cov=src --cov-report=html
```

## Security

### Reporting Vulnerabilities

Please report security vulnerabilities to security@company.com. Do NOT create public issues for security vulnerabilities.

### Security Guidelines

- Never commit secrets or credentials
- Use environment variables for configuration
- Follow OWASP security guidelines
- Use parameterized queries for database operations
- Validate all user input

## Documentation

- Update README.md for user-facing changes
- Add docstrings for new functions/classes
- Update API documentation if endpoints change
- Keep CHANGELOG.md up to date

## Questions?

- Create a GitHub issue for bugs or feature requests
- Contact the maintainers for other questions

---

Thank you for contributing to Cloud Optimizer!
