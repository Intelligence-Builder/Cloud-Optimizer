# Cloud Optimizer Helm Chart

A Helm chart for deploying Cloud Optimizer - AWS security scanning SaaS platform on Kubernetes.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- AWS Load Balancer Controller (for ALB Ingress)
- PostgreSQL database (managed or in-cluster)
- Kubernetes secrets created for sensitive credentials

## Installing the Chart

### 1. Create Required Secrets

Before installing the chart, create the necessary Kubernetes secrets:

```bash
# Database credentials
kubectl create secret generic cloud-optimizer-db-credentials \
  --from-literal=password=YOUR_DB_PASSWORD

# JWT secret key
kubectl create secret generic cloud-optimizer-jwt \
  --from-literal=secret-key=YOUR_JWT_SECRET

# Intelligence Builder credentials
kubectl create secret generic cloud-optimizer-ib-credentials \
  --from-literal=api-key=YOUR_IB_API_KEY

# AWS credentials
kubectl create secret generic cloud-optimizer-aws-credentials \
  --from-literal=access-key-id=YOUR_AWS_ACCESS_KEY_ID \
  --from-literal=secret-access-key=YOUR_AWS_SECRET_ACCESS_KEY
```

### 2. Install the Chart

#### Development Environment

```bash
helm install cloud-optimizer . -f values-dev.yaml \
  --namespace cloud-optimizer \
  --create-namespace
```

#### Production Environment

```bash
helm install cloud-optimizer . -f values-prod.yaml \
  --namespace cloud-optimizer \
  --create-namespace
```

#### Custom Values

```bash
helm install cloud-optimizer . \
  --set image.tag=2.0.0 \
  --set replicaCount=3 \
  --set database.host=my-postgres-host \
  --namespace cloud-optimizer \
  --create-namespace
```

## Upgrading the Chart

```bash
# Development
helm upgrade cloud-optimizer . -f values-dev.yaml \
  --namespace cloud-optimizer

# Production
helm upgrade cloud-optimizer . -f values-prod.yaml \
  --namespace cloud-optimizer
```

## Uninstalling the Chart

```bash
helm uninstall cloud-optimizer --namespace cloud-optimizer
```

## Configuration

The following table lists the configurable parameters of the Cloud Optimizer chart and their default values.

### General Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `2` |
| `image.repository` | Image repository | `cloud-optimizer` |
| `image.tag` | Image tag | `""` (defaults to Chart appVersion) |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `nameOverride` | Override chart name | `""` |
| `fullnameOverride` | Override full name | `""` |

### Service Account

| Parameter | Description | Default |
|-----------|-------------|---------|
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.annotations` | Service account annotations | `{}` |
| `serviceAccount.name` | Service account name | `""` |

### Service

| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `8000` |

### Ingress

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `alb` |
| `ingress.annotations` | Ingress annotations | See values.yaml |
| `ingress.hosts` | Ingress hosts configuration | See values.yaml |
| `ingress.tls` | Ingress TLS configuration | `[]` |

### Resources

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.limits.cpu` | CPU limit | `1000m` |
| `resources.limits.memory` | Memory limit | `1Gi` |
| `resources.requests.cpu` | CPU request | `500m` |
| `resources.requests.memory` | Memory request | `512Mi` |

### Autoscaling

| Parameter | Description | Default |
|-----------|-------------|---------|
| `autoscaling.enabled` | Enable HPA | `true` |
| `autoscaling.minReplicas` | Minimum replicas | `2` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization | `80` |

### Health Probes

| Parameter | Description | Default |
|-----------|-------------|---------|
| `livenessProbe.initialDelaySeconds` | Liveness probe initial delay | `30` |
| `livenessProbe.periodSeconds` | Liveness probe period | `10` |
| `livenessProbe.timeoutSeconds` | Liveness probe timeout | `5` |
| `livenessProbe.failureThreshold` | Liveness probe failure threshold | `3` |
| `readinessProbe.initialDelaySeconds` | Readiness probe initial delay | `10` |
| `readinessProbe.periodSeconds` | Readiness probe period | `5` |
| `readinessProbe.timeoutSeconds` | Readiness probe timeout | `3` |
| `readinessProbe.failureThreshold` | Readiness probe failure threshold | `3` |

### Database Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `database.host` | Database host | `postgres-service` |
| `database.port` | Database port | `5432` |
| `database.name` | Database name | `cloud_optimizer` |
| `database.user` | Database user | `cloud_optimizer` |

### Secrets

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secrets.databasePasswordSecret` | Database password secret name | `cloud-optimizer-db-credentials` |
| `secrets.jwtSecretKey` | JWT secret key secret name | `cloud-optimizer-jwt` |
| `secrets.ibCredentials` | Intelligence Builder credentials secret name | `cloud-optimizer-ib-credentials` |
| `secrets.awsCredentials` | AWS credentials secret name | `cloud-optimizer-aws-credentials` |

### Application Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.apiHost` | API host | `0.0.0.0` |
| `config.apiPort` | API port | `8000` |
| `config.jwtAlgorithm` | JWT algorithm | `HS256` |
| `config.jwtAccessTokenExpireMinutes` | JWT token expiration (minutes) | `15` |
| `config.ibPlatformUrl` | Intelligence Builder platform URL | `https://ib-platform.example.com` |
| `config.ibTenantId` | Intelligence Builder tenant ID | `""` |
| `config.awsDefaultRegion` | AWS default region | `us-east-1` |
| `config.logLevel` | Log level | `INFO` |
| `config.debug` | Debug mode | `false` |

### Feature Flags

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.enableSecurityDomain` | Enable security domain | `true` |
| `config.enableCostDomain` | Enable cost domain | `true` |
| `config.enablePerformanceDomain` | Enable performance domain | `true` |
| `config.enableReliabilityDomain` | Enable reliability domain | `true` |
| `config.enableOperationsDomain` | Enable operations domain | `true` |

## Architecture

### Components

- **Deployment**: Manages the Cloud Optimizer application pods
- **Service**: ClusterIP service for internal communication
- **Ingress**: AWS ALB for external access with health checks
- **HorizontalPodAutoscaler**: Automatic scaling based on CPU/memory
- **ConfigMap**: Non-sensitive configuration
- **ServiceAccount**: Kubernetes service account with optional IAM role annotations

### Health Checks

The application provides a `/health` endpoint that is used for:
- Kubernetes liveness probes
- Kubernetes readiness probes
- ALB health checks

### Security

- Runs as non-root user (UID 1000)
- Drops all capabilities
- Read-only root filesystem disabled (required for application)
- Secrets managed via Kubernetes secrets, not in values files

## AWS-Specific Configuration

### ALB Ingress Controller

The chart is configured to use AWS Application Load Balancer (ALB) as the ingress controller. Key features:

- **Health Checks**: Configured to use `/health` endpoint
- **Target Type**: IP-based routing for better performance
- **SSL/TLS**: Production configuration includes HTTPS with certificate ARN
- **Scheme**: Internet-facing for production, internal for development

### IAM Roles for Service Accounts (IRSA)

For production deployments, you can configure IRSA for secure AWS access:

```yaml
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/cloud-optimizer-role
```

## Examples

### Example 1: Deploy to Development

```bash
# Create secrets
kubectl create namespace cloud-optimizer-dev
kubectl create secret generic cloud-optimizer-db-credentials \
  --from-literal=password=devpassword \
  --namespace cloud-optimizer-dev

kubectl create secret generic cloud-optimizer-jwt \
  --from-literal=secret-key=devsecret \
  --namespace cloud-optimizer-dev

kubectl create secret generic cloud-optimizer-ib-credentials \
  --from-literal=api-key=dev-api-key \
  --namespace cloud-optimizer-dev

kubectl create secret generic cloud-optimizer-aws-credentials \
  --from-literal=access-key-id=AKIAEXAMPLE \
  --from-literal=secret-access-key=secret \
  --namespace cloud-optimizer-dev

# Install chart
helm install cloud-optimizer . \
  -f values-dev.yaml \
  --namespace cloud-optimizer-dev
```

### Example 2: Deploy to Production with Custom Values

```bash
# Create production namespace
kubectl create namespace cloud-optimizer-prod

# Create secrets (use proper secret management in production)
# ... create secrets as above ...

# Install with custom overrides
helm install cloud-optimizer . \
  -f values-prod.yaml \
  --set image.tag=2.0.0 \
  --set database.host=prod-postgres.rds.amazonaws.com \
  --set config.ibTenantId=prod-tenant-123 \
  --set ingress.hosts[0].host=cloud-optimizer.company.com \
  --namespace cloud-optimizer-prod
```

### Example 3: Enable IRSA for AWS Access

```bash
# Create service account with IRSA annotation
helm install cloud-optimizer . \
  -f values-prod.yaml \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="arn:aws:iam::123456789012:role/cloud-optimizer-role" \
  --namespace cloud-optimizer-prod
```

## Troubleshooting

### Pods Not Starting

Check pod events:
```bash
kubectl describe pod -n cloud-optimizer -l app.kubernetes.io/name=cloud-optimizer
```

Check logs:
```bash
kubectl logs -n cloud-optimizer -l app.kubernetes.io/name=cloud-optimizer
```

### Database Connection Issues

Verify secrets exist:
```bash
kubectl get secrets -n cloud-optimizer
```

Check database configuration in ConfigMap:
```bash
kubectl get configmap cloud-optimizer -n cloud-optimizer -o yaml
```

### Ingress Not Working

Check ALB creation:
```bash
kubectl get ingress -n cloud-optimizer
kubectl describe ingress cloud-optimizer -n cloud-optimizer
```

Verify AWS Load Balancer Controller is running:
```bash
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
```

### Health Check Failures

Test health endpoint directly:
```bash
kubectl port-forward -n cloud-optimizer svc/cloud-optimizer 8000:8000
curl http://localhost:8000/health
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/cloud-optimizer/issues
- Documentation: https://docs.cloud-optimizer.io

## License

This chart is licensed under the same license as Cloud Optimizer.
