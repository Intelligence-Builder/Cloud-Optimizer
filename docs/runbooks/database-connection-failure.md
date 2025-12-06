# Runbook: Database Connection Failure

## Alert Details
- **Alarm Name**: `cloud-optimizer-*-database-connection-failed`
- **Severity**: Critical (P1)
- **Threshold**: Health check fails 3 consecutive times
- **Escalation Policy**: critical

## Overview
This runbook addresses database connectivity issues between Cloud Optimizer and PostgreSQL.

## Impact
- Complete service outage for affected operations
- API requests returning 503 errors
- Data operations blocked

## Diagnostic Steps

### 1. Check Database Status
```bash
# Check PostgreSQL pod/instance status
kubectl get pods -n cloud-optimizer -l app=postgres

# Check database logs
kubectl logs -n cloud-optimizer -l app=postgres --tail=100

# Check RDS status (if using RDS)
aws rds describe-db-instances --db-instance-identifier cloud-optimizer-prod
```

### 2. Test Connectivity
```bash
# From application pod
kubectl exec -it -n cloud-optimizer deployment/cloud-optimizer -- \
  python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='postgres.cloud-optimizer.svc.cluster.local',
        port=5432,
        dbname='cloudguardian',
        user='cloudguardian',
        password='****',
        connect_timeout=5
    )
    print('Connection successful')
    conn.close()
except Exception as e:
    print(f'Connection failed: {e}')
"

# Check network policy
kubectl get networkpolicy -n cloud-optimizer
```

### 3. Check Connection Pool
```bash
# View active connections
kubectl exec -it postgres-0 -n cloud-optimizer -- \
  psql -U cloudguardian -c "
    SELECT state, count(*)
    FROM pg_stat_activity
    WHERE datname = 'cloudguardian'
    GROUP BY state;"

# Check max connections
kubectl exec -it postgres-0 -n cloud-optimizer -- \
  psql -U cloudguardian -c "SHOW max_connections;"
```

### 4. Check DNS Resolution
```bash
# Test DNS from application pod
kubectl exec -it -n cloud-optimizer deployment/cloud-optimizer -- \
  nslookup postgres.cloud-optimizer.svc.cluster.local
```

## Resolution Steps

### Immediate Actions

1. **Restart Database Pod (if stuck)**
   ```bash
   kubectl delete pod postgres-0 -n cloud-optimizer
   # Wait for pod to restart
   kubectl wait --for=condition=ready pod/postgres-0 -n cloud-optimizer --timeout=120s
   ```

2. **Clear Stuck Connections**
   ```bash
   kubectl exec -it postgres-0 -n cloud-optimizer -- \
     psql -U cloudguardian -c "
       SELECT pg_terminate_backend(pid)
       FROM pg_stat_activity
       WHERE datname = 'cloudguardian'
       AND state = 'idle'
       AND state_change < NOW() - INTERVAL '10 minutes';"
   ```

3. **Restart Application Pods**
   ```bash
   kubectl rollout restart deployment/cloud-optimizer -n cloud-optimizer
   ```

4. **Check PVC Status**
   ```bash
   kubectl get pvc -n cloud-optimizer
   kubectl describe pvc postgres-data -n cloud-optimizer
   ```

### RDS Specific Actions

1. **Check RDS Events**
   ```bash
   aws rds describe-events \
     --source-identifier cloud-optimizer-prod \
     --source-type db-instance \
     --duration 60
   ```

2. **Reboot RDS Instance (if needed)**
   ```bash
   aws rds reboot-db-instance --db-instance-identifier cloud-optimizer-prod
   ```

3. **Failover to Replica (Multi-AZ)**
   ```bash
   aws rds failover-db-cluster --db-cluster-identifier cloud-optimizer-prod
   ```

## Prevention

1. Implement connection pooling (PgBouncer)
2. Configure proper connection timeouts
3. Set up read replicas for query distribution
4. Monitor connection pool metrics
5. Regular database maintenance (VACUUM, ANALYZE)

## Escalation

This is a P1 incident. Immediate escalation required:
1. Page DBA team
2. Create incident bridge immediately
3. Notify all engineering stakeholders
4. Prepare for extended outage communication

## Communication Template

```
[INCIDENT] Cloud Optimizer - Database Connectivity Issue

Status: Investigating | Identified | Monitoring | Resolved
Impact: Service unavailable for all users
Started: [TIMESTAMP]

We are experiencing database connectivity issues affecting the Cloud Optimizer service.
All data operations are currently unavailable.

Updates will be provided every 10 minutes.

Timeline:
- [TIME] Issue detected
- [TIME] On-call paged
- [TIME] Investigation started
```

## Recovery Verification

After resolution, verify:
1. [ ] Health endpoint returns healthy
2. [ ] API requests succeed
3. [ ] No error logs in application
4. [ ] Connection pool metrics normal
5. [ ] Database replication (if applicable) caught up

## Related Alarms
- `cloud-optimizer-*-database-replication-lag`
- `cloud-optimizer-*-connection-pool-exhausted`
- `cloud-optimizer-*-high-error-rate`
