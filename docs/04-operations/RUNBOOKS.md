# Operational Runbooks

**Version:** 1.0.0
**Last Updated:** 2025-12-01

---

## 1. Incident Response

### Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| **SEV-1** | Critical Service Outage | 15 mins | API down, DB unreachable |
| **SEV-2** | Major Feature Broken | 1 hour | Scans failing, Auth issues |
| **SEV-3** | Minor Issue | 4 hours | Dashboard slow, visual bugs |
| **SEV-4** | Non-Critical | 24 hours | Typo, minor glitch |

### Incident Commander Checklist
1. [ ] **Acknowledge:** Ack the alert in PagerDuty.
2. [ ] **Assess:** Determine impact and severity.
3. [ ] **Communicate:** Create a status page update (if user facing).
4. [ ] **Mitigate:** Focus on restoring service (rollback, restart, scale).
5. [ ] **Analyze:** Find root cause after service is restored.

---

## 2. Common Incidents

### 2.1 High Database Latency
**Symptoms:** API timeouts, slow dashboard loading.
**Alert:** `DB_CPU_HIGH` or `DB_LATENCY_HIGH`.

**Steps:**
1. Check active queries:
   ```sql
   SELECT pid, now() - query_start as duration, query 
   FROM pg_stat_activity 
   WHERE state != 'idle' 
   ORDER BY duration DESC;
   ```
2. Kill stuck queries if necessary:
   ```sql
   SELECT pg_terminate_backend(pid);
   ```
3. Check connection count:
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```
4. If CPU is high due to legitimate load, consider scaling up instance class (requires downtime if not Multi-AZ failover).

### 2.2 IB Platform Unavailable
**Symptoms:** Scans failing, "Intelligence Unavailable" errors.
**Alert:** `IB_HEALTH_CHECK_FAILED`.

**Steps:**
1. Verify IB Platform status (check internal dashboard).
2. If IB is down, the application should degrade gracefully (local regex patterns).
3. Check IB logs for specific errors.
4. Restart IB container/service if stuck.

### 2.3 AWS Rate Limiting
**Symptoms:** Scans failing with `ThrottlingException`.
**Alert:** `AWS_API_THROTTLED`.

**Steps:**
1. Identify which tenant is causing the throttle.
2. Check if the tenant has too many concurrent scans.
3. Temporarily increase backoff configuration in `config.py` or reduce concurrency.

---

## 3. Routine Maintenance

### 3.1 Database Vacuum
PostgreSQL requires regular vacuuming to reclaim storage.
**Schedule:** Weekly (Automated via RDS).
**Manual Trigger:**
```sql
VACUUM (VERBOSE, ANALYZE);
```

### 3.2 Rotate Secrets
**Schedule:** Every 90 days.
**Steps:**
1. Generate new secret in Secrets Manager.
2. Update ECS task definition with new secret version.
3. Force new deployment:
   ```bash
   aws ecs update-service --cluster co-prod --service api --force-new-deployment
   ```
4. Verify application health.
5. Revoke old secret.

### 3.3 DR Drill
**Schedule:** Quarterly.
**Steps:**
1. Restore RDS snapshot to a new instance in a different AZ/Region.
2. Point a staging environment to the restored DB.
3. Verify data integrity and application functionality.
4. Record "Time to Restore" metric.
