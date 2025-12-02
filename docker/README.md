# Cloud Optimizer - Docker Deployment

Production-ready containerization for Cloud Optimizer with multi-stage builds, health checks, and orchestration.

## Quick Start

### Development

```bash
# Start with docker-compose (existing simple setup)
docker-compose up -d
```

### Production

```bash
# Copy and configure environment
cp docker/.env.production.example docker/.env.production
# Edit .env.production with your values

# Start production stack
docker-compose -f docker/docker-compose.prod.yml --env-file docker/.env.production up -d
```

## Files

- **Dockerfile**: Multi-stage production build (builder + runtime)
- **docker-compose.prod.yml**: Full production stack (postgres, redis, app)
- **.env.production.example**: Environment variable template
- **init-db.sql**: PostgreSQL initialization script

## Container Features

### Dockerfile
- Multi-stage build for minimal image size (<500MB)
- Non-root user (appuser, uid 1000)
- Health check endpoint integration
- Automatic database migrations on startup
- Python 3.11 slim base

### Security
- Non-root user execution
- Minimal attack surface (slim image)
- No unnecessary build dependencies in runtime
- Environment-based secrets management

### Health Checks
- **Liveness**: `/live` - Process is alive
- **Readiness**: `/ready` - Ready to accept traffic
- **Health**: `/health` - Detailed component status

## Environment Variables

Required:
- `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`
- `DATABASE_USER`, `DATABASE_PASSWORD`
- `JWT_SECRET_KEY`

Optional:
- `IB_PLATFORM_URL`, `IB_API_KEY` - Intelligence-Builder platform
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` - AWS credentials
- Feature flags: `ENABLE_*_DOMAIN`

See `.env.production.example` for complete list.

## Building

```bash
# Build image
docker build -f docker/Dockerfile -t cloud-optimizer:latest .

# Check image size
docker images cloud-optimizer:latest

# Test run
docker run --rm -p 8000:8000 \
  -e DATABASE_HOST=host.docker.internal \
  -e DATABASE_PORT=5432 \
  -e DATABASE_NAME=cloud_optimizer \
  -e DATABASE_USER=cloud_optimizer \
  -e DATABASE_PASSWORD=securepass123 \
  -e JWT_SECRET_KEY=change-me \
  cloud-optimizer:latest
```

## Production Stack

The production docker-compose includes:

1. **PostgreSQL 15** - Primary database with persistent volume
2. **Redis 7** - Caching layer with persistence
3. **Cloud Optimizer** - Main application with health checks

All services have:
- Health checks with retries
- Automatic restart policies
- Named volumes for data persistence
- Dedicated network isolation

## Monitoring

```bash
# View logs
docker-compose -f docker/docker-compose.prod.yml logs -f app

# Check health
curl http://localhost:8000/health | jq

# View component status
curl http://localhost:8000/health | jq '.components'
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs cloud-optimizer-app

# Verify environment
docker exec cloud-optimizer-app env | grep DATABASE
```

### Database connection fails
```bash
# Check database is healthy
docker-compose -f docker/docker-compose.prod.yml ps

# Test connection from app container
docker exec cloud-optimizer-app curl -f http://postgres:5432 || echo "Connection failed"
```

### Migrations fail
```bash
# Run migrations manually
docker exec cloud-optimizer-app alembic upgrade head

# Check migration status
docker exec cloud-optimizer-app alembic current
```

## Kubernetes Deployment

The health endpoints are Kubernetes-compatible:

```yaml
livenessProbe:
  httpGet:
    path: /live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```
