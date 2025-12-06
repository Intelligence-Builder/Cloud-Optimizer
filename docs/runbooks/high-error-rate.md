# Runbook: High Error Rate

## Alert Details
- **Alarm Name**: `cloud-optimizer-*-high-error-rate`
- **Severity**: Critical (P1) if > 10%, High (P2) if > 5%
- **Threshold**: Error rate > 5% for 5 minutes
- **Escalation Policy**: critical (>10%), high (5-10%)

## Overview
This runbook addresses elevated error rates in the Cloud Optimizer API.

## Impact
- Users experiencing failed requests
- Potential data inconsistency
- Customer trust degradation
- SLA breach risk

## Diagnostic Steps

### 1. Identify Error Types
```bash
# CloudWatch Logs Insights query
fields @timestamp, @message
| filter @message like /error|exception|failed/i
| stats count(*) by status_code
| sort count desc
| limit 20
```

### 2. Check Recent Deployments
```bash
# View recent deployments
kubectl rollout history deployment/cloud-optimizer -n cloud-optimizer

# Check current version
kubectl describe deployment cloud-optimizer -n cloud-optimizer | grep Image
```

### 3. Check Downstream Dependencies
```bash
# Database connectivity
kubectl exec -it -n cloud-optimizer deployment/cloud-optimizer -- \
  python -c "from cloud_optimizer.database import get_session; print('DB OK')"

# External service health
curl -s https://api.intelligence-builder.com/health
```

### 4. Review Error Distribution
```bash
# Group errors by endpoint
fields @timestamp, path, status_code, error_message
| filter status_code >= 400
| stats count(*) by path, status_code
| sort count desc
```

## Resolution Steps

### Immediate Actions

1. **Rollback if Recent Deployment**
   ```bash
   kubectl rollout undo deployment/cloud-optimizer -n cloud-optimizer
   ```

2. **Check Database Connections**
   ```bash
   # View active connections
   kubectl exec -it postgres-0 -- psql -U cloudguardian -c "SELECT count(*) FROM pg_stat_activity;"
   ```

3. **Restart Affected Pods**
   ```bash
   kubectl delete pods -n cloud-optimizer -l app=cloud-optimizer --field-selector=status.phase!=Running
   ```

4. **Enable Debug Logging (Temporarily)**
   ```bash
   kubectl set env deployment/cloud-optimizer -n cloud-optimizer LOG_LEVEL=DEBUG
   ```

### Error Type Specific Actions

#### 5xx Server Errors
1. Check application logs for stack traces
2. Review memory and CPU metrics
3. Check for database deadlocks

#### 4xx Client Errors
1. Review recent API changes
2. Check authentication service
3. Verify request validation rules

#### Database Errors
1. Check connection pool exhaustion
2. Review slow query log
3. Check for table locks

## Prevention

1. Implement comprehensive error handling
2. Add retry logic with exponential backoff
3. Set up circuit breakers
4. Implement proper connection pooling
5. Regular chaos engineering tests

## Escalation

If error rate exceeds 10% or persists > 15 minutes:
1. Page secondary on-call
2. Create incident bridge
3. Notify all stakeholders
4. Consider maintenance mode

## Communication Template

```
[INCIDENT] Cloud Optimizer - Elevated Error Rates

Status: Investigating
Impact: Some API requests may fail
Started: [TIMESTAMP]

We are investigating elevated error rates in the Cloud Optimizer service.
Updates will be provided every 15 minutes.

Current actions:
- Reviewing application logs
- Checking downstream dependencies
- Monitoring error trends
```

## Related Alarms
- `cloud-optimizer-*-5xx-errors`
- `cloud-optimizer-*-4xx-errors`
- `cloud-optimizer-*-database-errors`
- `cloud-optimizer-*-high-latency`
