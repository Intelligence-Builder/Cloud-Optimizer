# Runbook: High CPU Utilization

## Alert Details
- **Alarm Name**: `cloud-optimizer-*-high-cpu-utilization`
- **Severity**: High (P2)
- **Threshold**: CPU > 80% for 5 minutes
- **Escalation Policy**: high

## Overview
This runbook addresses high CPU utilization alerts for Cloud Optimizer services running on EKS/ECS.

## Impact
- Degraded API response times
- Potential request timeouts
- Risk of service unavailability if sustained

## Diagnostic Steps

### 1. Identify Affected Resources
```bash
# Check which pods/containers are affected
kubectl top pods -n cloud-optimizer

# View container metrics in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=cloud-optimizer \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average
```

### 2. Check Application Logs
```bash
# View recent logs for the service
kubectl logs -n cloud-optimizer -l app=cloud-optimizer --tail=100

# Check for error patterns
kubectl logs -n cloud-optimizer -l app=cloud-optimizer --tail=500 | grep -i error
```

### 3. Check Request Patterns
```bash
# View request rates in CloudWatch Logs Insights
# Query: fields @timestamp, @message | filter @message like /request_started/ | stats count() by bin(1m)
```

## Resolution Steps

### Immediate Actions

1. **Scale Up (if needed)**
   ```bash
   # Kubernetes
   kubectl scale deployment cloud-optimizer -n cloud-optimizer --replicas=5

   # ECS
   aws ecs update-service --cluster cloud-optimizer --service cloud-optimizer --desired-count 5
   ```

2. **Check for Stuck Requests**
   ```bash
   # Look for long-running requests
   kubectl exec -it -n cloud-optimizer deployment/cloud-optimizer -- curl localhost:8080/health
   ```

3. **Restart Unhealthy Pods**
   ```bash
   kubectl rollout restart deployment/cloud-optimizer -n cloud-optimizer
   ```

### Root Cause Investigation

1. **Check for Memory Leaks**
   - Review memory growth patterns
   - Check for large response payloads

2. **Check for Infinite Loops**
   - Review recent deployments
   - Check for recursive operations

3. **Check External Dependencies**
   - Database query performance
   - External API response times

## Prevention

1. Set up horizontal pod autoscaling (HPA)
2. Implement request timeouts
3. Add circuit breakers for external calls
4. Regular load testing

## Escalation

If the issue persists after following these steps:
1. Engage secondary on-call
2. Open incident bridge
3. Notify engineering lead

## Related Alarms
- `cloud-optimizer-*-high-memory-utilization`
- `cloud-optimizer-*-high-latency`
- `cloud-optimizer-*-error-rate`
