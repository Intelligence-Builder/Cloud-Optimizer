# RDS PostgreSQL Production Setup

Issue #141: 13.2.2 RDS PostgreSQL production setup with encryption

## Overview

This document describes the production RDS PostgreSQL deployment for Cloud Optimizer, including Multi-AZ configuration, encryption, monitoring, and high availability features.

## Architecture

```
                                   ┌─────────────────────┐
                                   │   CloudWatch        │
                                   │   Alarms &          │
                                   │   Dashboard         │
                                   └─────────────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
                    ▼                       ▼                       ▼
    ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
    │    Application      │   │    Application      │   │    Application      │
    │    (ECS/EKS)        │   │    (ECS/EKS)        │   │    (ECS/EKS)        │
    └─────────────────────┘   └─────────────────────┘   └─────────────────────┘
              │                         │                         │
              └─────────────────────────┼─────────────────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │       RDS Proxy           │
                          │   (Connection Pooling)    │
                          │   RequireTLS: true        │
                          └───────────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼                                       ▼
    ┌─────────────────────────────┐       ┌─────────────────────────────┐
    │   RDS PostgreSQL Primary    │       │   RDS PostgreSQL Replica    │
    │   (Multi-AZ: AZ-a)          │──────▶│   (Read-only: AZ-b)         │
    │   Encrypted: KMS            │ sync  │   For reporting workloads   │
    │   Backup: 30 days           │       │                             │
    └─────────────────────────────┘       └─────────────────────────────┘
                    │
                    ▼
    ┌─────────────────────────────┐
    │     Secrets Manager         │
    │   Master Credentials        │
    │   Rotation: Enabled         │
    └─────────────────────────────┘
```

## Features

### Security
- **Encryption at Rest**: AWS KMS customer-managed key with automatic rotation
- **Encryption in Transit**: SSL/TLS enforced via `rds.force_ssl = 1`
- **IAM Authentication**: Enabled for admin access
- **Credentials Management**: AWS Secrets Manager with auto-generated passwords
- **Network Isolation**: Private subnets only, no public accessibility
- **Security Groups**: Restricted to application tier only

### High Availability
- **Multi-AZ Deployment**: Synchronous standby in different AZ
- **Read Replica**: Async replica for reporting workloads
- **Automated Failover**: AWS-managed failover to standby

### Backup & Recovery
- **Automated Backups**: Daily, 30-day retention
- **Backup Window**: 03:00-04:00 UTC
- **Point-in-Time Recovery**: Enabled
- **Snapshot Retention**: Copy tags to snapshots

### Monitoring
- **Enhanced Monitoring**: 60-second granularity
- **Performance Insights**: 2-year retention (production)
- **CloudWatch Logs**: PostgreSQL and upgrade logs exported
- **CloudWatch Alarms**: CPU, storage, connections, latency

### Connection Pooling
- **RDS Proxy**: Connection pooling for application connections
- **TLS Required**: All proxy connections encrypted
- **Idle Timeout**: 30 minutes

## Deployment

### Prerequisites

1. VPC with private subnets (at least 2 in different AZs)
2. Application security group that needs database access
3. SNS topic for alarm notifications (optional)

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Environment | production | Environment name |
| VpcId | - | VPC ID for RDS deployment |
| PrivateSubnetIds | - | List of private subnet IDs |
| ApplicationSecurityGroupId | - | Security group for app tier |
| DBInstanceClass | db.r6g.xlarge | Instance type (4 vCPU, 32GB) |
| DBAllocatedStorage | 500 | Initial storage in GB |
| DBMaxAllocatedStorage | 1000 | Max storage for autoscaling |
| DBName | cloudoptimizer | Database name |
| DBMasterUsername | dbadmin | Master username |
| EnableReadReplica | true | Create read replica |
| EnableRDSProxy | true | Create RDS Proxy |
| BackupRetentionPeriod | 30 | Backup retention days |
| SNSAlertTopicArn | - | SNS topic for alarms |

### Deploy Stack

```bash
aws cloudformation deploy \
  --template-file cloudformation/rds/rds-postgresql.yaml \
  --stack-name cloud-optimizer-rds-production \
  --parameter-overrides \
    Environment=production \
    VpcId=vpc-xxxxxxxxx \
    PrivateSubnetIds=subnet-aaa,subnet-bbb \
    ApplicationSecurityGroupId=sg-xxxxxxxxx \
    SNSAlertTopicArn=arn:aws:sns:us-east-1:123456789:alerts \
  --capabilities CAPABILITY_NAMED_IAM
```

### Stack Outputs

| Output | Description |
|--------|-------------|
| RDSInstanceEndpoint | Primary instance endpoint |
| RDSReadReplicaEndpoint | Read replica endpoint |
| RDSProxyEndpoint | RDS Proxy endpoint (recommended) |
| DBSecretArn | Secrets Manager ARN for credentials |
| ConnectionString | Template connection string |

## Connection Strings

### Via RDS Proxy (Recommended)

```python
# Python with SQLAlchemy
DATABASE_URL = "postgresql://dbadmin:PASSWORD@cloud-optimizer-proxy-production.proxy-xxxxx.us-east-1.rds.amazonaws.com:5432/cloudoptimizer?sslmode=require"
```

### Direct Connection (Primary)

```python
DATABASE_URL = "postgresql://dbadmin:PASSWORD@cloud-optimizer-production.xxxxx.us-east-1.rds.amazonaws.com:5432/cloudoptimizer?sslmode=require"
```

### Read Replica (Reporting Only)

```python
READ_REPLICA_URL = "postgresql://dbadmin:PASSWORD@cloud-optimizer-production-replica.xxxxx.us-east-1.rds.amazonaws.com:5432/cloudoptimizer?sslmode=require"
```

### Retrieving Credentials from Secrets Manager

```python
import boto3
import json

def get_db_credentials():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(
        SecretId='cloud-optimizer/rds/production/master-credentials'
    )
    return json.loads(response['SecretString'])
```

## Parameter Group Settings

### Memory Optimization (db.r6g.xlarge - 32GB RAM)

| Parameter | Value | Description |
|-----------|-------|-------------|
| shared_buffers | 8GB | Buffer cache (25% RAM) |
| effective_cache_size | 24GB | Planner cache estimate |
| work_mem | 256MB | Per-operation memory |
| maintenance_work_mem | 2GB | Maintenance operations |

### WAL Settings

| Parameter | Value | Description |
|-----------|-------|-------------|
| wal_buffers | 64MB | WAL buffer size |
| checkpoint_completion_target | 0.9 | Spread checkpoints |
| max_wal_size | 4GB | Max WAL before checkpoint |

### Performance

| Parameter | Value | Description |
|-----------|-------|-------------|
| random_page_cost | 1.1 | SSD-optimized |
| effective_io_concurrency | 200 | Concurrent I/O |
| max_connections | 200 | Connection limit |

## CloudWatch Alarms

| Alarm | Threshold | Description |
|-------|-----------|-------------|
| CPU Utilization | > 80% for 5 min | High CPU usage |
| Free Storage Space | < 20 GB | Low disk space |
| Database Connections | > 180 (90%) | Connection exhaustion |
| Read Latency | > 100ms | Slow reads |
| Write Latency | > 100ms | Slow writes |
| Freeable Memory | < 1 GB | Low memory |
| Replica Lag | > 30 seconds | Replication delay |

## Maintenance

### Maintenance Window

- **Window**: Sunday 04:00-05:00 UTC
- **Auto Minor Upgrade**: Enabled
- **Major Version Upgrade**: Requires manual approval

### Backup Strategy

1. **Automated Daily Backups**: 03:00-04:00 UTC, 30-day retention
2. **Pre-Deployment Snapshots**: Create manual snapshot before major changes
3. **Cross-Region Backup**: Configure for DR (separate template)
4. **Monthly Restore Test**: Validate backup integrity

### Scaling Recommendations

| Metric | Action |
|--------|--------|
| CPU > 80% sustained | Upgrade instance class |
| Storage > 80% | Enable autoscaling or increase storage |
| Connections > 90% | Enable RDS Proxy or increase max_connections |
| Read load high | Add read replicas |

## Troubleshooting

### Connection Issues

```bash
# Test SSL connection
psql "host=cloud-optimizer-production.xxxxx.rds.amazonaws.com \
      port=5432 \
      dbname=cloudoptimizer \
      user=dbadmin \
      sslmode=require"
```

### Performance Issues

```sql
-- Check active queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;

-- Check connection count
SELECT count(*) FROM pg_stat_activity;

-- Check table bloat
SELECT schemaname, relname, n_dead_tup, last_vacuum, last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
```

### Log Analysis

```bash
# View PostgreSQL logs in CloudWatch
aws logs tail /aws/rds/instance/cloud-optimizer-production/postgresql --follow
```

## Cost Estimation

| Resource | Estimated Monthly Cost |
|----------|----------------------|
| db.r6g.xlarge (Multi-AZ) | ~$800 |
| 500 GB gp3 storage | ~$60 |
| Read Replica | ~$400 |
| RDS Proxy | ~$90 |
| Enhanced Monitoring | ~$10 |
| Performance Insights | ~$30 |
| **Total** | **~$1,390/month** |

*Costs are estimates for US regions and may vary*

## Related Documentation

- [VPC Setup](../vpc/VPC_SETUP.md) - Issue #139
- [Database Migrations](../migrations/DATABASE_MIGRATIONS.md) - Issue #144
- [AWS Best Practices for RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
