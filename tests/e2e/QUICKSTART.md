# E2E Tests Quick Start

Get started with Cloud Optimizer E2E tests in 3 minutes.

## TL;DR

```bash
# 1. Make sure Docker is running
docker info

# 2. Run the tests
./tests/e2e/run_e2e_tests.sh
```

That's it! The script handles everything:
- Starts PostgreSQL, LocalStack, and the API
- Waits for services to be healthy
- Runs all E2E tests
- Tears everything down

## What Gets Tested?

- ✅ API health and readiness checks
- ✅ Database migrations and connectivity
- ✅ LocalStack AWS integration
- ✅ Security scanning endpoints
- ✅ Chat endpoints (graceful degradation)
- ✅ Complete end-to-end workflows

## Common Commands

```bash
# Run all E2E tests
./tests/e2e/run_e2e_tests.sh

# Run with verbose output
./tests/e2e/run_e2e_tests.sh --verbose

# Run specific test
./tests/e2e/run_e2e_tests.sh --test test_api_health_check_works

# Keep services running (for debugging)
./tests/e2e/run_e2e_tests.sh --keep-running

# Run with pytest directly (after starting services)
pytest tests/e2e/ -v -m e2e
```

## Manual Service Control

Start services:
```bash
docker-compose -f docker/docker-compose.e2e.yml up -d
```

Check status:
```bash
docker-compose -f docker/docker-compose.e2e.yml ps
```

View logs:
```bash
docker-compose -f docker/docker-compose.e2e.yml logs -f app
```

Stop services:
```bash
docker-compose -f docker/docker-compose.e2e.yml down -v
```

## Service URLs

When services are running:
- **API**: http://localhost:18080
- **API Docs**: http://localhost:18080/docs
- **PostgreSQL**: localhost:5546 (user: test, password: test, db: test_intelligence)
- **LocalStack**: http://localhost:5566
- **Intelligence-Builder**: http://localhost:8100 (runs outside the compose stack)

## Troubleshooting

### Services won't start

Check Docker:
```bash
docker info
docker-compose version
```

View logs:
```bash
docker-compose -f docker/docker-compose.e2e.yml logs
```

### Port conflicts

The E2E environment uses dedicated ports to avoid conflicts:
- 18080 (API) instead of 8080
- 5546 (PostgreSQL) instead of 5432/5434
- 5566 (LocalStack) instead of the default 4566
- 8100 (Intelligence-Builder API exposed from the host)

If you still have conflicts, you can modify ports in `docker/docker-compose.e2e.yml`.

### Intelligence-Builder API

E2E tests require the Intelligence-Builder API to be reachable on the host.

1. Start the IB docker stack (see the Intelligence-Builder repository) and expose port 8100.
2. Export your IB API key so the compose file can inject it into the Cloud Optimizer service:
   ```bash
   export IB_API_KEY=test-api-key  # replace with your real key
   ```
3. Optionally override the host/port:
   ```bash
   export E2E_IB_PLATFORM_URL=http://127.0.0.1:9000
   ```
4. Verify the service:
   ```bash
   curl http://localhost:8100/
   ```

If the security tests skip with `"IB service not available"`, the API key or IB stack was not configured correctly.

### Tests are slow

First run takes longer (downloading images). Subsequent runs are faster.

Expected timing:
- First run: ~2-3 minutes
- Subsequent runs: ~1 minute

### Clean up everything

Remove all E2E resources:
```bash
docker-compose -f docker/docker-compose.e2e.yml down -v
docker volume prune -f
```

## Next Steps

- Read full documentation: [README.md](README.md)
- Add new E2E tests: See "Writing New E2E Tests" in README
- CI/CD integration: See "CI/CD Integration" in README

## Getting Help

1. Check [README.md](README.md) troubleshooting section
2. View service logs: `docker-compose logs`
3. Test services manually:
   ```bash
   curl http://localhost:18080/health
   docker exec co-e2e-postgres psql -U test -c "SELECT 1"
   curl http://localhost:5566/_localstack/health
   ```
4. Open a GitHub issue with logs attached

## Key Features

### No Mocks
Tests use real services:
- Real PostgreSQL database
- Real LocalStack for AWS
- Real Cloud Optimizer API

### Automatic Cleanup
Services are stopped and volumes removed after tests (unless `--keep-running`).

### Graceful Degradation
Tests gracefully skip if optional services (IB SDK, Anthropic) are unavailable.

### Isolation
E2E environment is isolated from local development:
- Different ports
- Separate database
- Separate Docker network

### Fast Feedback
Tests run in parallel where possible and fail fast on issues.
