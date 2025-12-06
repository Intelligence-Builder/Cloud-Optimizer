# Business Continuity and Disaster Recovery Plan

**Document Version:** 1.0
**Last Updated:** December 5, 2025
**Owner:** Engineering Team
**Issue Reference:** #163

---

## 1. Executive Summary

This Business Continuity Plan (BCP) and Disaster Recovery Plan (DRP) ensures Cloud Optimizer can maintain or rapidly restore critical business functions during and after a disaster or service disruption.

### Key Metrics

| Metric | Target | Current Capability |
|--------|--------|-------------------|
| Recovery Time Objective (RTO) | 4 hours | 4 hours |
| Recovery Point Objective (RPO) | 1 hour | 1 hour (point-in-time recovery) |
| Maximum Tolerable Downtime (MTD) | 8 hours | 8 hours |
| Service Availability | 99.9% | 99.9% (Multi-AZ) |

---

## 2. Scope and Objectives

### 2.1 Scope

This plan covers:
- Cloud Optimizer web application and API
- Database (PostgreSQL RDS)
- Background processing services
- Supporting AWS infrastructure

### 2.2 Objectives

1. Minimize service disruption impact on customers
2. Ensure data integrity and prevent data loss
3. Restore services within defined RTO/RPO targets
4. Maintain regulatory compliance (SOC 2)
5. Protect company reputation and customer trust

---

## 3. Critical Systems Inventory

### 3.1 Tier 1: Mission Critical (RTO: 1-4 hours)

| System | Description | Dependencies | Backup Strategy |
|--------|-------------|--------------|-----------------|
| API Server | FastAPI application | Database, Secrets | ECS Multi-AZ, ALB |
| Database | PostgreSQL RDS | KMS, VPC | Multi-AZ, automated backups |
| Load Balancer | Application LB | VPC, Subnets | AWS managed, multi-AZ |
| Authentication | JWT token service | Secrets Manager | Stateless, key rotation |

### 3.2 Tier 2: Business Essential (RTO: 8-24 hours)

| System | Description | Dependencies | Backup Strategy |
|--------|-------------|--------------|-----------------|
| Scanner Services | AWS security scanners | AWS APIs, Database | Stateless, redeployable |
| Alerting | PagerDuty/OpsGenie | SNS, Lambda | AWS managed |
| Monitoring | CloudWatch | N/A | AWS managed |

### 3.3 Tier 3: Non-Critical (RTO: 24-72 hours)

| System | Description | Dependencies | Backup Strategy |
|--------|-------------|--------------|-----------------|
| Analytics | Usage metrics | Database | Rebuild from logs |
| Documentation | Static sites | S3, CloudFront | Git repository |

---

## 4. Disaster Scenarios

### 4.1 Scenario Classification

| Scenario | Probability | Impact | Response Time |
|----------|-------------|--------|---------------|
| Single AZ failure | Medium | Low | Automatic |
| Region outage | Low | High | 4-8 hours |
| Database corruption | Low | High | 1-4 hours |
| Security breach | Low | Critical | Immediate |
| DDoS attack | Medium | Medium | Automatic/1 hour |
| Deployment failure | Medium | Low | 15-30 minutes |

### 4.2 Response Procedures by Scenario

#### 4.2.1 Single Availability Zone Failure

**Automatic Response:**
- ALB routes traffic to healthy AZ
- ECS maintains desired replica count across AZs
- RDS failover to standby (if Multi-AZ enabled)

**Manual Verification:**
1. Check CloudWatch alarms for AZ-specific issues
2. Verify traffic distribution via ALB metrics
3. Confirm database connectivity
4. Monitor for cascading failures

#### 4.2.2 Database Failure

**Automated Backup Strategy:**
- Automated daily backups: 03:00-04:00 UTC
- Backup retention: 30 days
- Point-in-time recovery: Up to 5 minutes
- Snapshot on deletion: Enabled

**Recovery Steps:**
1. Identify failure type (instance, storage, corruption)
2. For instance failure: RDS automatic failover (Multi-AZ)
3. For data corruption:
   ```bash
   # Restore from point-in-time
   aws rds restore-db-instance-to-point-in-time \
     --source-db-instance-identifier cloud-optimizer-db \
     --target-db-instance-identifier cloud-optimizer-db-restored \
     --restore-time 2024-01-01T12:00:00Z
   ```
4. Update application connection strings
5. Verify data integrity
6. Update DNS/ALB target groups

#### 4.2.3 Security Breach

**Immediate Response (0-15 minutes):**
1. Activate incident response team
2. Isolate compromised systems:
   ```bash
   # Isolate ECS service
   aws ecs update-service --cluster production \
     --service cloud-optimizer --desired-count 0

   # Restrict security groups
   aws ec2 revoke-security-group-ingress \
     --group-id sg-xxx --ip-permissions all
   ```
3. Preserve evidence (snapshots, logs)
4. Notify security officer

**Investigation Phase (15 min - 4 hours):**
1. Review CloudTrail logs
2. Analyze GuardDuty findings
3. Check database access logs
4. Review application logs

**Recovery Phase:**
1. Patch vulnerabilities
2. Rotate all credentials
3. Deploy clean infrastructure
4. Restore from known-good backup
5. Implement additional controls

---

## 5. Recovery Procedures

### 5.1 Full System Recovery

**Pre-requisites:**
- AWS CLI configured with appropriate permissions
- Access to CloudFormation templates
- Database backup access
- Container image registry access

**Step-by-Step Recovery:**

```bash
# 1. Deploy infrastructure
aws cloudformation create-stack \
  --stack-name cloud-optimizer-recovery \
  --template-body file://cloudformation/cloud-optimizer-standalone.yaml \
  --parameters file://cloudformation/parameters/production.json \
  --capabilities CAPABILITY_NAMED_IAM

# 2. Wait for stack completion
aws cloudformation wait stack-create-complete \
  --stack-name cloud-optimizer-recovery

# 3. Restore database from backup
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier cloud-optimizer-db-recovery \
  --db-snapshot-identifier latest-snapshot

# 4. Update application configuration
# Update secrets in Secrets Manager with new endpoints

# 5. Deploy application
# Trigger GitHub Actions deployment or manual ECS update

# 6. Verify health
curl https://app.cloudoptimizer.com/health

# 7. Update DNS (if needed)
aws route53 change-resource-record-sets \
  --hosted-zone-id ZXXXXX \
  --change-batch file://dns-update.json
```

### 5.2 Database Point-in-Time Recovery

```bash
# Identify target recovery time (before incident)
TARGET_TIME="2024-01-01T11:55:00Z"

# Create restored instance
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier cloud-optimizer-prod \
  --target-db-instance-identifier cloud-optimizer-pit-restore \
  --restore-time $TARGET_TIME \
  --db-subnet-group-name cloud-optimizer-db-subnet \
  --multi-az

# Wait for restoration
aws rds wait db-instance-available \
  --db-instance-identifier cloud-optimizer-pit-restore

# Verify data
psql -h restored-endpoint -U cloudguardian -d cloudguardian \
  -c "SELECT COUNT(*) FROM users;"

# Rename instances to swap
aws rds modify-db-instance \
  --db-instance-identifier cloud-optimizer-prod \
  --new-db-instance-identifier cloud-optimizer-old

aws rds modify-db-instance \
  --db-instance-identifier cloud-optimizer-pit-restore \
  --new-db-instance-identifier cloud-optimizer-prod
```

### 5.3 Container Service Recovery

```bash
# Force new deployment with latest image
aws ecs update-service \
  --cluster cloud-optimizer-cluster \
  --service cloud-optimizer \
  --force-new-deployment

# Or rollback to previous task definition
aws ecs update-service \
  --cluster cloud-optimizer-cluster \
  --service cloud-optimizer \
  --task-definition cloud-optimizer:PREVIOUS_VERSION

# Monitor deployment
aws ecs wait services-stable \
  --cluster cloud-optimizer-cluster \
  --services cloud-optimizer
```

---

## 6. Communication Plan

### 6.1 Internal Communication

| Audience | Channel | Frequency | Owner |
|----------|---------|-----------|-------|
| Engineering Team | Slack #incidents | Real-time | On-call engineer |
| Management | Email + Phone | Hourly | Engineering Manager |
| All Staff | Slack #company | Major milestones | Communications |

### 6.2 External Communication

| Audience | Channel | Frequency | Owner |
|----------|---------|-----------|-------|
| Customers | Status page | Real-time | Support |
| Enterprise clients | Direct email | As needed | Account Manager |
| Regulatory | Formal notification | Within 72h | Compliance |

### 6.3 Status Page Updates

```markdown
## Incident Template

**Status:** [Investigating | Identified | Monitoring | Resolved]
**Impact:** [Major | Minor | Degraded Performance]

### Summary
[Brief description of the issue]

### Affected Services
- [List affected services]

### Current Status
[What we know and what we're doing]

### Next Update
[Expected time of next update]
```

---

## 7. Testing Schedule

### 7.1 Test Types

| Test Type | Frequency | Participants | Duration |
|-----------|-----------|--------------|----------|
| Tabletop Exercise | Quarterly | Engineering, Management | 2 hours |
| Backup Restoration | Monthly | DBA, Engineering | 1-2 hours |
| Failover Test | Semi-annually | Engineering | 4 hours |
| Full DR Test | Annually | All teams | 8 hours |

### 7.2 Test Scenarios

**Quarterly Tabletop:**
- Q1: Database corruption scenario
- Q2: Security breach response
- Q3: Regional outage
- Q4: DDoS attack

**Monthly Backup Tests:**
1. Select random backup from past 7 days
2. Restore to test environment
3. Verify data integrity
4. Document restoration time
5. Delete test resources

### 7.3 Test Documentation

Each test must document:
- Test date and participants
- Scenario tested
- Expected vs actual RTO/RPO
- Issues encountered
- Improvements identified
- Follow-up actions

---

## 8. Roles and Responsibilities

### 8.1 Incident Response Team

| Role | Responsibilities | Primary | Backup |
|------|-----------------|---------|--------|
| Incident Commander | Overall coordination | Engineering Manager | Senior Engineer |
| Technical Lead | Technical decisions | Lead Engineer | Senior Engineer |
| Communications | Internal/external comms | Support Lead | Product Manager |
| Scribe | Documentation | Any team member | Any team member |

### 8.2 Escalation Matrix

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| P1 (Critical) | 15 minutes | Immediate page to on-call |
| P2 (High) | 30 minutes | Page during business hours |
| P3 (Medium) | 4 hours | Email notification |
| P4 (Low) | Next business day | Ticket creation |

---

## 9. Vendor Dependencies

### 9.1 Critical Vendors

| Vendor | Service | SLA | Contact |
|--------|---------|-----|---------|
| AWS | Infrastructure | 99.99% | Support console |
| GitHub | Code repository | 99.95% | Support portal |
| PagerDuty | Alerting | 99.9% | Support email |

### 9.2 Vendor Failure Procedures

**AWS Regional Outage:**
1. Confirm outage via AWS Health Dashboard
2. Activate cross-region failover (if configured)
3. Update DNS to secondary region
4. Notify customers via status page

**GitHub Outage:**
1. Use local git repositories
2. Deploy from local Docker images
3. Restore GitHub access when available

---

## 10. Document Maintenance

### 10.1 Review Schedule

| Review Type | Frequency | Owner |
|-------------|-----------|-------|
| Full plan review | Annually | Compliance Team |
| Contact information | Quarterly | Operations |
| Procedure updates | After each incident | Engineering |
| Test results review | After each test | Engineering Manager |

### 10.2 Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-12-05 | 1.0 | Initial document | Engineering |

---

## Appendices

### A. Emergency Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| On-Call Engineer | Rotation | Via PagerDuty | oncall@company.com |
| Engineering Manager | TBD | TBD | eng-manager@company.com |
| AWS Support | N/A | Support Console | N/A |

### B. Quick Reference Commands

```bash
# Check service health
curl https://app.cloudoptimizer.com/health

# View recent CloudWatch alarms
aws cloudwatch describe-alarms --state-value ALARM

# List recent RDS snapshots
aws rds describe-db-snapshots --db-instance-identifier cloud-optimizer-prod

# Force ECS deployment
aws ecs update-service --cluster prod --service api --force-new-deployment

# Check ALB target health
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:...
```

### C. Related Documents

- [Incident Response Policy](./policies/INCIDENT_RESPONSE_POLICY.md)
- [Change Management Policy](./policies/CHANGE_MANAGEMENT_POLICY.md)
- [Information Security Policy](./policies/INFORMATION_SECURITY_POLICY.md)
- [SOC 2 Readiness Checklist](./SOC2_READINESS_CHECKLIST.md)

---

*This document is reviewed and updated annually or after significant infrastructure changes.*
