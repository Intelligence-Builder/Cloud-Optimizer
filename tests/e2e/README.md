# End-to-End Tests for Cloud Optimizer

Comprehensive E2E test suite that tests the real system without mocks.

## Overview

These E2E tests boot the complete docker-compose stack and test real flows:

- **Real Services**: PostgreSQL, LocalStack, Cloud Optimizer API
- **No Mocks**: All tests use actual service implementations
- **Complete Flows**: Tests cover end-to-end user journeys
- **Automatic Cleanup**: Services are torn down after tests complete

## Test Coverage

### Basic Health & Connectivity
- ✅ API health check works
- ✅ Database migrations ran successfully
- ✅ API documentation accessible
- ✅ Readiness/liveness checks pass

### LocalStack Integration
- ✅ LocalStack is available
- ✅ Can create AWS resources in LocalStack
- ✅ AWS SDK can interact with LocalStack

### Security Scanning
- ✅ Security scan endpoint works
- ✅ Security service health check
- ✅ Can list security findings
- ✅ Findings pagination works

### Chat Integration
- ✅ Chat health endpoint works
- ✅ Chat message endpoint responds (graceful degradation if no API key)

### Database Integration
- ✅ Can insert and query data
- ✅ Database constraints work
- ✅ Transactions and rollbacks work

### Integration Flows
- ✅ Complete security workflow (if IB SDK available)
- ✅ Concurrent API requests
- ✅ API error handling

### Performance Baselines
- ✅ API response time within limits
- ✅ Database query performance

## Prerequisites

### Required
- **Docker**: Docker Desktop or Docker Engine installed and running
- **Docker Compose**: Version 1.29+ (included with Docker Desktop)
- **Python**: 3.11+ with test dependencies installed

### Optional
- **Anthropic API Key**: For chat endpoint testing (gracefully skipped if not present)
- **IB SDK**: For advanced security analysis (gracefully skipped if not available)

## Installation

1. **Install test dependencies:**
   ```bash
   pip install -e ".[test]"
   ```

2. **Verify Docker is running:**
   ```bash
   docker info
   docker-compose version
   ```

## Running Tests

### Quick Start

Run all E2E tests:
```bash
pytest tests/e2e/ -v -m e2e
```

### Using the Test Script

Use the helper script for a better experience:
```bash
# Run all E2E tests
./tests/e2e/run_e2e_tests.sh

# Run with verbose output
./tests/e2e/run_e2e_tests.sh --verbose

# Run specific test
./tests/e2e/run_e2e_tests.sh --test test_api_health_check_works

# Keep services running after tests (for debugging)
./tests/e2e/run_e2e_tests.sh --keep-running
```

### Manual Control

Start services manually:
```bash
docker-compose -f docker/docker-compose.e2e.yml up -d
```

Wait for services to be healthy (check logs):
```bash
docker-compose -f docker/docker-compose.e2e.yml ps
docker-compose -f docker/docker-compose.e2e.yml logs app
```

Run tests:
```bash
pytest tests/e2e/ -v -m e2e
```

Stop services:
```bash
docker-compose -f docker/docker-compose.e2e.yml down -v
```

## Test Configuration

### Environment Variables

Tests read configuration from docker-compose.e2e.yml:

- **API_BASE_URL**: `http://localhost:18080` (configured in conftest.py)
- **POSTGRES_URL**: `postgresql+asyncpg://test:test@localhost:5546/test_intelligence`
- **LOCALSTACK_URL**: `http://localhost:5566`
- **IB_PLATFORM_URL**: Defaults to `http://host.docker.internal:8100` (override with `E2E_IB_PLATFORM_URL`)
- **IB_API_KEY**: Pulled from the host environment (`export IB_API_KEY=<local key>` before running tests)

### Ports Used

The E2E environment uses non-conflicting ports:
- **18080**: Cloud Optimizer API (vs. 8080 for local dev)
- **5546**: PostgreSQL (dedicated E2E port)
- **5566**: LocalStack (dedicated E2E port)
- **8100**: Intelligence-Builder API (runs outside the compose stack)

This allows E2E tests to run alongside local development.

## Test Architecture

### Fixtures (conftest.py)

**Session-scoped fixtures:**
- `docker_compose_manager`: Manages docker-compose lifecycle
- `docker_compose_up`: Starts and stops the stack
- `api_client`: HTTP client configured for E2E API
- `db_session`: Database session for direct DB access

**Function-scoped fixtures:**
- `clean_database`: Cleans test data before/after each test
- `localstack_endpoint`: LocalStack endpoint URL
- `aws_credentials_for_localstack`: AWS credentials for LocalStack

### Helper Functions

**Service Management:**
- `wait_for_api_health()`: Wait for API to be healthy
- `wait_for_postgres_ready()`: Wait for database to be ready

**Test Helpers:**
- `create_test_aws_account()`: Create test AWS account via API
- `trigger_security_scan()`: Trigger security scan via API
- `get_findings()`: Get findings via API

## Writing New E2E Tests

### Test Template

```python
import pytest
from tests.e2e.conftest import skip_if_no_docker

@pytest.mark.e2e
@skip_if_no_docker()
async def test_my_feature(api_client, db_session, clean_database):
    """Test description here."""
    # Arrange: Set up test data

    # Act: Perform API call or operation
    response = await api_client.get("/api/v1/my-endpoint")

    # Assert: Verify results
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data

    # Optional: Verify database state
    result = await db_session.execute(text("SELECT * FROM my_table"))
    rows = result.fetchall()
    assert len(rows) > 0
```

### Best Practices

1. **Mark tests with `@pytest.mark.e2e`**: Allows running E2E tests separately
2. **Use `@skip_if_no_docker()`**: Gracefully skip if Docker unavailable
3. **Clean up test data**: Use `clean_database` fixture for isolation
4. **Graceful degradation**: Handle missing optional services (IB, Anthropic)
5. **Print useful info**: Use `print()` for test progress (visible with `-v`)
6. **Test real flows**: Avoid mocking - test the actual system behavior

### Handling Optional Services

Tests should gracefully handle missing optional services:

```python
response = await api_client.post("/api/v1/security/scan", json=request_data)

if response.status_code == 503:
    # Service not available - skip test
    pytest.skip("IB service not available in E2E environment")
else:
    # Service available - test it
    assert response.status_code == 200
    # ... rest of test
```

## Troubleshooting

### Services Not Starting

**Check Docker is running:**
```bash
docker info
```

**Check compose file syntax:**
```bash
docker-compose -f docker/docker-compose.e2e.yml config
```

**View service logs:**
```bash
docker-compose -f docker/docker-compose.e2e.yml logs
```

### Database Connection Issues

**Verify PostgreSQL is healthy:**
```bash
docker-compose -f docker/docker-compose.e2e.yml ps postgres-test
```

**Test connection manually:**
```bash
docker exec co-e2e-postgres psql -U test -d test_intelligence -c "SELECT 1"
```

### API Not Responding

**Check API logs:**
```bash
docker-compose -f docker/docker-compose.e2e.yml logs app
```

**Test API manually:**
```bash
curl http://localhost:18080/health
```

**Check healthcheck status:**
```bash
docker inspect co-e2e-app | grep -A 10 Health
```

### LocalStack Issues

**Verify LocalStack is healthy:**
```bash
curl http://localhost:5566/_localstack/health
```

**Check available services:**
```bash
aws --endpoint-url=http://localhost:5566 s3 ls
```

### Intelligence-Builder Issues

The Intelligence-Builder API must be reachable on the host (default `http://localhost:8100`) with a valid API key.

1. Start the IB docker stack (see the Intelligence-Builder repository) so the API listens on port 8100.
2. Export the API key so the E2E compose file can inject it:
   ```bash
   export IB_API_KEY=test-api-key  # replace with your local key
   ```
3. Override the host/port if needed:
   ```bash
   export E2E_IB_PLATFORM_URL=http://127.0.0.1:9000
   ```
4. Verify the service:
   ```bash
   curl http://localhost:8100/
   ```

If you still see `"IB service not available"` skips, the API key or IB container is not configured correctly.

### Port Conflicts

If ports are already in use, you can modify the ports in docker-compose.e2e.yml:

```yaml
ports:
  - "19080:8080"  # Change 18080 to 19080
```

Then update `API_BASE_URL` in conftest.py.

### Cleaning Up

**Remove all E2E containers and volumes:**
```bash
docker-compose -f docker/docker-compose.e2e.yml down -v
```

**Remove dangling volumes:**
```bash
docker volume prune
```

**Remove all test containers:**
```bash
docker ps -a | grep co-e2e | awk '{print $1}' | xargs docker rm -f
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[test]"

      - name: Run E2E tests
        run: |
          pytest tests/e2e/ -v -m e2e --tb=short

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: e2e-logs
          path: |
            docker-compose logs
```

## Performance Benchmarks

Typical E2E test suite execution time:

- **Setup**: 30-60 seconds (Docker Compose startup)
- **Test Execution**: 20-40 seconds (all tests)
- **Teardown**: 5-10 seconds
- **Total**: ~1-2 minutes

Individual test performance:
- Health checks: <100ms
- Database queries: <500ms
- API endpoints: <1000ms
- Security scans: <5000ms (if IB available)

## Contributing

When adding new features to Cloud Optimizer:

1. **Add E2E test**: Cover the complete user flow
2. **Test with real services**: Don't mock external dependencies
3. **Handle graceful degradation**: Skip if optional services unavailable
4. **Update this README**: Document new test coverage
5. **Run locally**: Verify tests pass before submitting PR

## Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

## Support

For issues or questions:
1. Check this README's troubleshooting section
2. Review test logs: `docker-compose logs`
3. Check GitHub issues
4. Contact the development team
