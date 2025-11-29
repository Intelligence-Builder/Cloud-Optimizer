# Docker Operations Guide

**Version:** 1.0.0
**Last Updated:** 2025-11-29

---

## Overview

Cloud Optimizer uses Docker for:
- **Test Infrastructure** - PostgreSQL and Memgraph for integration tests
- **Development Stack** - Full development environment
- **LocalStack** - AWS service emulation for testing

---

## Quick Reference

```bash
# Start test infrastructure
docker-compose -f docker/docker-compose.test.yml up -d

# Stop test infrastructure
docker-compose -f docker/docker-compose.test.yml down

# View logs
docker-compose -f docker/docker-compose.test.yml logs -f

# Check status
docker-compose -f docker/docker-compose.test.yml ps
```

---

## Test Infrastructure

### Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| PostgreSQL | co-test-postgres | 5434 | Graph backend (CTE) |
| Memgraph | co-test-memgraph | 7688 | Graph backend (native) |
| LocalStack | co-test-localstack | 4566 | AWS emulation |

### Starting Services

```bash
cd /Users/robertstanley/desktop/cloud-optimizer

# Start all test services
docker-compose -f docker/docker-compose.test.yml up -d

# Wait for health checks
docker-compose -f docker/docker-compose.test.yml ps

# Expected output:
# co-test-postgres   Up (healthy)   0.0.0.0:5434->5432
# co-test-memgraph   Up (healthy)   0.0.0.0:7688->7687
```

### Stopping Services

```bash
# Stop and remove containers
docker-compose -f docker/docker-compose.test.yml down

# Stop, remove, and delete volumes
docker-compose -f docker/docker-compose.test.yml down -v
```

---

## PostgreSQL Configuration

### Connection Details

```python
POSTGRES_TEST_CONFIG = {
    "host": "localhost",
    "port": 5434,
    "user": "test",
    "password": "test",
    "database": "test_intelligence",
}
```

### Schema Initialization

The `docker/init-test-db.sql` script creates:
- `intelligence` schema
- `entities` table
- `relationships` table
- `patterns` table
- `domains` table

### Direct Access

```bash
# Connect to PostgreSQL
docker exec -it co-test-postgres psql -U test -d test_intelligence

# Run a query
docker exec co-test-postgres psql -U test -d test_intelligence -c "SELECT count(*) FROM intelligence.entities"
```

---

## Memgraph Configuration

### Connection Details

```python
MEMGRAPH_TEST_CONFIG = {
    "uri": "bolt://localhost:7688",
    "username": "",  # No auth for test
    "password": "",
}
```

### Direct Access

```bash
# Connect to Memgraph via mgconsole (if available)
docker exec -it co-test-memgraph mgconsole

# Or via Cypher shell
docker exec -it co-test-memgraph cypher-shell
```

### Memgraph Lab (Optional)

Memgraph provides a web UI at port 7444 (if exposed):
```yaml
# Add to docker-compose.test.yml if needed
ports:
  - "7444:7444"  # Memgraph Lab
```

---

## LocalStack Configuration

### Enabled Services

```yaml
SERVICES: ec2,iam,s3,cloudwatch,rds
```

### Usage with AWS SDK

```python
import boto3

# Configure boto3 to use LocalStack
session = boto3.Session()
s3_client = session.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1',
)

# Create a test bucket
s3_client.create_bucket(Bucket='test-bucket')
```

---

## Troubleshooting

### Port Conflicts

```bash
# Check what's using a port
lsof -i :5434
lsof -i :7688

# Kill process using port (if needed)
kill -9 <PID>
```

### Container Won't Start

```bash
# Check logs
docker logs co-test-postgres
docker logs co-test-memgraph

# Remove and recreate
docker-compose -f docker/docker-compose.test.yml down
docker-compose -f docker/docker-compose.test.yml up -d --force-recreate
```

### Database Connection Refused

```bash
# Verify container is running
docker ps | grep co-test

# Check health status
docker inspect co-test-postgres --format='{{.State.Health.Status}}'

# Wait for healthy status before running tests
while ! docker inspect co-test-postgres --format='{{.State.Health.Status}}' | grep -q healthy; do
    sleep 1
done
```

### Clean Slate

```bash
# Remove everything and start fresh
docker-compose -f docker/docker-compose.test.yml down -v
docker system prune -f
docker-compose -f docker/docker-compose.test.yml up -d
```

---

## Docker Compose Files

### docker/docker-compose.test.yml

```yaml
version: '3.8'

services:
  postgres-test:
    image: postgres:15-alpine
    container_name: co-test-postgres
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: test_intelligence
    ports:
      - "5434:5432"
    volumes:
      - ./init-test-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test -d test_intelligence"]
      interval: 5s
      timeout: 5s
      retries: 5

  memgraph-test:
    image: memgraph/memgraph:latest
    container_name: co-test-memgraph
    ports:
      - "7688:7687"
    entrypoint: ["/usr/lib/memgraph/memgraph", "--log-level=WARNING"]
    healthcheck:
      test: ["CMD", "echo", "ok"]
      interval: 5s
      timeout: 5s
      retries: 5

  localstack:
    image: localstack/localstack:latest
    container_name: co-test-localstack
    ports:
      - "4566:4566"
    environment:
      SERVICES: ec2,iam,s3,cloudwatch,rds
      DEBUG: 0
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_intelligence
        ports:
          - 5434:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        env:
          TEST_POSTGRES_PORT: 5434
        run: |
          pip install -e ".[dev]"
          PYTHONPATH=src pytest tests/ib_platform/ -v
```

---

## Related Documentation

- [QUICKSTART.md](../01-guides/QUICKSTART.md) - Quick start guide
- [DEVELOPMENT_STANDARDS.md](../03-development/DEVELOPMENT_STANDARDS.md) - Development standards
