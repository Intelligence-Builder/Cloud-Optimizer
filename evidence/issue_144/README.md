# Issue #144: ElastiCache Redis Cluster Setup - Evidence Documentation

## Overview

This directory contains evidence and documentation for Issue #144: ElastiCache Redis cluster setup for the Cloud Optimizer security scanning platform.

**Status**: ✅ COMPLETED
**Date**: 2025-12-06
**Template Location**: `/cloudformation/elasticache-redis.yaml`

## What Was Implemented

A production-ready CloudFormation template that deploys a highly available, secure ElastiCache Redis cluster with:

### Core Components
1. **ElastiCache Replication Group** - Multi-node Redis cluster with automatic failover
2. **Cache Subnet Group** - For private subnet deployment across multiple AZs
3. **Security Group** - Restricting access to port 6379 from ECS tasks only
4. **Parameter Group** - Custom Redis configuration optimized for performance
5. **CloudWatch Log Groups** - For slow queries and engine logs
6. **CloudWatch Alarms** - Comprehensive monitoring for CPU, memory, evictions, replication lag, and network

### Security Features
- ✅ Encryption at rest (enabled by default)
- ✅ Encryption in transit via TLS (enabled by default)
- ✅ Private subnet deployment only
- ✅ Security group-based access control
- ✅ No public accessibility
- ✅ CloudWatch logging for audit trail
- ✅ Automated backup retention

### High Availability Features
- ✅ Automatic failover enabled
- ✅ Multi-AZ deployment
- ✅ 2-6 configurable cache nodes
- ✅ Primary and reader endpoints
- ✅ Automated backups with configurable retention
- ✅ Configurable maintenance windows
- ✅ SNS notifications for cluster events

### Monitoring & Alerting
- ✅ CPU utilization alarm
- ✅ Memory usage alarm
- ✅ Cache eviction alarm
- ✅ Replication lag alarm
- ✅ Engine CPU alarm (single-threaded bottleneck detection)
- ✅ Network throughput alarm
- ✅ Integration with SNS for notifications

## Files in This Directory

### qa/test_summary.json
Comprehensive QA validation document containing:
- Template validation results
- Component implementation details
- Security feature verification
- Configuration documentation
- Best practices checklist
- Testing recommendations

### deployment_example.json
Deployment guide with:
- Example parameters for dev/staging/production
- AWS CLI deployment commands
- Environment variable configuration
- Connection examples (Python, Node.js)
- Monitoring setup recommendations
- Troubleshooting guide
- Cost optimization tips

### README.md (this file)
High-level overview and quick reference

## Template Validation

The CloudFormation template has been validated successfully:

```bash
aws cloudformation validate-template \
  --template-body file://cloudformation/elasticache-redis.yaml
```

**Result**: ✅ PASSED - Template is valid with 16 parameters defined

## Quick Start

### Prerequisites
- Existing VPC with at least 2 private subnets
- ECS security group already created
- AWS CLI configured with appropriate permissions

### Deploy to Development
```bash
aws cloudformation create-stack \
  --stack-name cloud-optimizer-dev-redis \
  --template-body file://cloudformation/elasticache-redis.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=development \
    ParameterKey=VpcId,ParameterValue=vpc-xxxxx \
    ParameterKey=PrivateSubnetIds,ParameterValue="subnet-xxxxx,subnet-yyyyy" \
    ParameterKey=ECSSecurityGroupId,ParameterValue=sg-xxxxx \
  --tags Key=Environment,Value=development Key=Application,Value=cloud-optimizer
```

### Get Connection Information
```bash
aws cloudformation describe-stacks \
  --stack-name cloud-optimizer-dev-redis \
  --query 'Stacks[0].Outputs' \
  --output table
```

Key outputs:
- **PrimaryEndpoint** - For write operations
- **ReaderEndpoint** - For read operations (load balanced)
- **SecureConnectionString** - Redis URL with TLS (`rediss://`)

## Configuration Parameters

### Required Parameters
- `VpcId` - VPC where cluster will be deployed
- `PrivateSubnetIds` - Comma-separated list of private subnet IDs (minimum 2)
- `ECSSecurityGroupId` - Security group of ECS tasks needing Redis access

### Key Optional Parameters
- `Environment` - development | staging | production (default: production)
- `NodeType` - Instance type (default: cache.t3.micro)
- `NumCacheNodes` - Number of nodes (default: 2, minimum: 2)
- `EngineVersion` - Redis version (default: 7.0)
- `EnableEncryptionAtRest` - Enable encryption at rest (default: true)
- `EnableEncryptionInTransit` - Enable TLS (default: true)
- `EnableAutoFailover` - Enable automatic failover (default: true)
- `AlarmTopicArn` - SNS topic for alarm notifications (optional)

See `deployment_example.json` for complete parameter examples.

## Cost Estimates

### Development/Staging
- **cache.t3.micro** (2 nodes): ~$25/month
- **cache.t3.small** (2 nodes): ~$50/month

### Production
- **cache.t3.medium** (3 nodes): ~$150/month
- **cache.m6g.large** (3 nodes): ~$250/month
- **cache.r6g.large** (3 nodes): ~$375/month

Note: Costs exclude data transfer and backup storage. Use Reserved Nodes for production to save up to 55%.

## Integration with Cloud Optimizer

### Environment Variables
After deployment, configure your application with:

```bash
REDIS_HOST=<PrimaryEndpoint from CloudFormation outputs>
REDIS_PORT=6379
REDIS_URL=<SecureConnectionString from CloudFormation outputs>
REDIS_TLS_ENABLED=true
```

### Python Connection Example
```python
import redis
import ssl

redis_client = redis.Redis(
    host='cloud-optimizer-prod-redis.xxxxx.ng.0001.use1.cache.amazonaws.com',
    port=6379,
    ssl=True,
    ssl_cert_reqs='required',
    decode_responses=True
)

# Test connection
redis_client.ping()
```

## Monitoring

### CloudWatch Metrics Dashboard
Monitor these key metrics:
- **CPUUtilization** - Overall CPU usage
- **EngineCPUUtilization** - Redis engine CPU (single-threaded)
- **DatabaseMemoryUsagePercentage** - Memory consumption
- **Evictions** - Cache evictions (indicates memory pressure)
- **CacheHits / CacheMisses** - Cache effectiveness
- **ReplicationLag** - Replica synchronization lag
- **CurrConnections** - Active connections
- **NetworkBytesIn/Out** - Network throughput

### CloudWatch Alarms
Pre-configured alarms will notify you when:
- CPU usage exceeds 75% (configurable)
- Memory usage exceeds 80% (configurable)
- Cache evictions exceed 1000 per 5 minutes
- Replication lag exceeds 30 seconds
- Engine CPU exceeds 90% (single-threaded bottleneck)
- Network input abnormally high

### CloudWatch Logs
Two log groups are created:
- `/aws/elasticache/${ApplicationName}/${Environment}/redis/slow-log` - Slow queries
- `/aws/elasticache/${ApplicationName}/${Environment}/redis/engine-log` - Engine events

## Security Checklist

Before deploying to production, verify:

- [ ] VPC has proper network isolation
- [ ] Private subnets have routes to NAT Gateway (for AWS API access)
- [ ] ECS security group is correctly configured
- [ ] Encryption at rest is enabled (`EnableEncryptionAtRest=true`)
- [ ] Encryption in transit is enabled (`EnableEncryptionInTransit=true`)
- [ ] SNS topic is configured for alarm notifications
- [ ] CloudWatch Logs are being delivered
- [ ] Backup retention is appropriate for compliance requirements
- [ ] Resource tags are applied for cost allocation

## Troubleshooting

### Cannot connect from ECS tasks
**Check**:
1. Security group rules allow port 6379 from ECS security group
2. ECS tasks are in same VPC as Redis cluster
3. Private subnet routing allows inter-subnet communication
4. Using correct endpoint (PrimaryEndpoint, not individual node)

### TLS certificate errors
**Fix**: Use `rediss://` URL (note double 's') and include CA certificate bundle in client configuration.

### High memory usage
**Solutions**:
1. Implement TTL on cached keys
2. Review `maxmemory-policy` (currently set to `allkeys-lru`)
3. Scale up to larger node type
4. Monitor eviction rate - frequent evictions indicate insufficient memory

### Replication lag
**Solutions**:
1. Monitor write patterns and optimize for batch operations
2. Check network metrics between AZs
3. Scale to larger node type for better network performance
4. Reduce write frequency if possible

## Best Practices Implemented

### Infrastructure as Code
- Parameterized template for multiple environments
- Conditional resource creation based on parameters
- Environment-specific configuration
- Comprehensive resource tagging

### Security
- Encryption enabled by default
- Private subnet deployment
- Least privilege security group rules
- No hardcoded credentials

### Reliability
- Multi-AZ deployment
- Automatic failover
- Automated backups
- Maintenance windows

### Observability
- CloudWatch Logs integration
- Comprehensive alarms
- SNS notifications
- Multiple monitoring metrics

### Cost Optimization
- Environment-specific backup retention
- Configurable node types
- Graviton-based instances available
- Option to disable alarms if not needed

## Additional Resources

- [AWS ElastiCache for Redis Documentation](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/)
- [Redis Best Practices](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/BestPractices.html)
- [CloudFormation Template Reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-elasticache-replicationgroup.html)

## Support

For issues or questions related to this CloudFormation template:
1. Check the troubleshooting section in `deployment_example.json`
2. Review CloudWatch Logs for Redis slow-log and engine-log
3. Check CloudWatch metrics and alarms
4. Consult AWS ElastiCache documentation

## Next Steps

After successful deployment:

1. **Configure Application** - Add Redis connection details to application environment variables
2. **Test Connection** - Verify connectivity from ECS tasks
3. **Setup Monitoring** - Create CloudWatch dashboard for Redis metrics
4. **Test Failover** - Perform controlled failover test in non-production
5. **Load Testing** - Validate performance under expected load
6. **Backup Verification** - Ensure automated backups are working
7. **Documentation** - Document Redis usage patterns in application code

## Changes Made

### Files Created
1. `/cloudformation/elasticache-redis.yaml` - Main CloudFormation template
2. `/evidence/issue_144/qa/test_summary.json` - QA validation results
3. `/evidence/issue_144/deployment_example.json` - Deployment guide
4. `/evidence/issue_144/README.md` - This file

### Template Validation
- ✅ Syntax validation passed
- ✅ AWS CloudFormation validate-template passed
- ✅ Security review completed
- ✅ Best practices review completed

## Completion Status

**Issue #144**: ✅ COMPLETED

All requirements met:
1. ✅ ElastiCache Redis cluster with replication group
2. ✅ Subnet group for private subnets
3. ✅ Security group allowing port 6379 from ECS tasks
4. ✅ Parameter group with appropriate settings
5. ✅ Encryption at rest and in transit
6. ✅ Auto-failover enabled for high availability
7. ✅ CloudWatch alarms for CPU and memory (plus additional metrics)
8. ✅ Template validation completed successfully
9. ✅ Evidence documentation created

Ready for deployment! 🚀
