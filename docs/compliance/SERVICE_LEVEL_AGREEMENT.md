# Service Level Agreement (SLA)

**Document Version:** 1.0
**Last Updated:** December 5, 2025
**Owner:** Engineering Team
**Issue Reference:** #163

---

## 1. Overview

This Service Level Agreement (SLA) defines the expected levels of service for Cloud Optimizer, including availability targets, performance metrics, support response times, and remedies for service level breaches.

### 1.1 Parties

- **Service Provider:** Cloud Optimizer (Intelligence Builder, Inc.)
- **Customer:** Subscribing organization using Cloud Optimizer services

### 1.2 Effective Date

This SLA is effective upon customer subscription and remains in effect for the duration of the service agreement.

---

## 2. Service Description

Cloud Optimizer provides:

1. **Security Scanning Service** - Automated AWS security configuration analysis
2. **Compliance Monitoring** - Continuous compliance posture assessment
3. **Dashboard & Reporting** - Real-time visibility and historical reporting
4. **API Access** - Programmatic access to all scanning capabilities
5. **Alert Notifications** - Real-time security alerts and notifications

---

## 3. Service Level Objectives (SLOs)

### 3.1 Availability

| Service Tier | Monthly Uptime Target | Maximum Downtime/Month |
|--------------|----------------------|------------------------|
| Enterprise   | 99.9%                | 43 minutes             |
| Business     | 99.5%                | 3.6 hours              |
| Starter      | 99.0%                | 7.3 hours              |

**Availability Calculation:**
```
Uptime % = ((Total Minutes - Downtime Minutes) / Total Minutes) × 100
```

**Exclusions from Downtime Calculation:**
- Scheduled maintenance (with 48-hour advance notice)
- Force majeure events
- Customer-caused outages
- Third-party service failures outside our control
- AWS regional outages

### 3.2 Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time (p50) | < 200ms | 50th percentile |
| API Response Time (p95) | < 1 second | 95th percentile |
| API Response Time (p99) | < 3 seconds | 99th percentile |
| Dashboard Load Time | < 3 seconds | Initial page load |
| Scan Initiation | < 10 seconds | Time to start scan |
| Scan Completion (small) | < 5 minutes | < 50 resources |
| Scan Completion (medium) | < 15 minutes | 50-500 resources |
| Scan Completion (large) | < 60 minutes | > 500 resources |

### 3.3 Data Durability

| Metric | Target |
|--------|--------|
| Data Durability | 99.999999999% (11 nines) |
| Backup Frequency | Daily (minimum) |
| Point-in-Time Recovery | Up to 30 days |
| Data Retention | Per subscription tier |

---

## 4. Support Service Levels

### 4.1 Support Tiers

| Tier | Included With | Support Hours | Channels |
|------|---------------|---------------|----------|
| Enterprise | Enterprise plan | 24/7/365 | Phone, Email, Chat, Dedicated Slack |
| Business | Business plan | 8am-8pm ET (M-F) | Email, Chat |
| Starter | Starter plan | 9am-5pm ET (M-F) | Email |

### 4.2 Response Time Targets

| Severity | Description | Enterprise | Business | Starter |
|----------|-------------|------------|----------|---------|
| P1 (Critical) | Service unavailable, data loss risk | 15 min | 1 hour | 4 hours |
| P2 (High) | Major feature unavailable, workaround exists | 1 hour | 4 hours | 1 business day |
| P3 (Medium) | Minor feature issue, no workaround needed | 4 hours | 1 business day | 2 business days |
| P4 (Low) | General questions, feature requests | 1 business day | 2 business days | 5 business days |

### 4.3 Resolution Time Targets

| Severity | Target Resolution Time |
|----------|----------------------|
| P1 (Critical) | 4 hours |
| P2 (High) | 8 hours |
| P3 (Medium) | 3 business days |
| P4 (Low) | 10 business days |

---

## 5. Scheduled Maintenance

### 5.1 Maintenance Windows

| Maintenance Type | Frequency | Duration | Notice Period |
|-----------------|-----------|----------|---------------|
| Routine Updates | Weekly | < 15 min | 48 hours |
| Security Patches | As needed | < 30 min | 24 hours (or less for critical) |
| Major Upgrades | Quarterly | < 4 hours | 2 weeks |
| Database Maintenance | Monthly | < 2 hours | 1 week |

### 5.2 Preferred Maintenance Windows

- **Primary:** Sundays 02:00-06:00 UTC
- **Secondary:** Saturdays 02:00-06:00 UTC
- **Emergency:** As required with maximum possible notice

### 5.3 Maintenance Notifications

Notifications will be sent via:
- Email to designated contacts
- Status page (status.cloudoptimizer.com)
- In-app banner (for non-emergency maintenance)

---

## 6. Service Credits

### 6.1 Credit Schedule

If Cloud Optimizer fails to meet the monthly availability target:

| Monthly Uptime | Service Credit (% of Monthly Fee) |
|----------------|-----------------------------------|
| 99.0% - 99.9%  | 10% |
| 95.0% - 99.0%  | 25% |
| 90.0% - 95.0%  | 50% |
| < 90.0%        | 100% |

### 6.2 Credit Request Process

1. Customer must request credit within 30 days of incident
2. Request must include:
   - Account information
   - Dates and times of unavailability
   - Description of impact
3. Credits applied to future invoices (not cash refunds)
4. Maximum credit per month: 100% of monthly fee

### 6.3 Credit Exclusions

Service credits do not apply when downtime is caused by:
- Scheduled maintenance (properly notified)
- Customer actions or configurations
- Force majeure events
- Features labeled as "beta" or "preview"
- API rate limiting due to customer excess usage
- Suspension due to payment or Terms of Service issues

---

## 7. Customer Responsibilities

To maintain SLA eligibility, customers must:

### 7.1 Technical Requirements

- Maintain valid AWS credentials with required permissions
- Use supported browsers and API client versions
- Configure network to allow Cloud Optimizer connections
- Implement recommended security practices

### 7.2 Operational Requirements

- Designate technical and administrative contacts
- Maintain current contact information
- Report issues through proper support channels
- Cooperate with troubleshooting efforts
- Implement recommended configurations

### 7.3 Security Requirements

- Protect account credentials
- Enable MFA for all users
- Review and act on security recommendations
- Report suspected security incidents immediately

---

## 8. Monitoring and Reporting

### 8.1 Service Monitoring

Cloud Optimizer monitors service health using:

| Component | Monitoring Interval | Alert Threshold |
|-----------|--------------------|-----------------|
| API Endpoints | 30 seconds | 3 consecutive failures |
| Database | 1 minute | Connection pool > 80% |
| Background Jobs | 5 minutes | Queue depth > 1000 |
| External Dependencies | 1 minute | Degraded response |

### 8.2 Status Page

Real-time service status available at:
- **URL:** status.cloudoptimizer.com
- **Components Monitored:**
  - API Services
  - Web Dashboard
  - Scanning Engine
  - Database
  - Authentication

### 8.3 Monthly Reports

Enterprise customers receive monthly SLA reports including:
- Uptime percentage
- Performance metrics
- Incident summary
- Support ticket statistics
- Trend analysis

---

## 9. Incident Management

### 9.1 Incident Classification

| Level | Description | Example |
|-------|-------------|---------|
| SEV-1 | Complete service outage | All customers unable to access |
| SEV-2 | Major feature unavailable | Scanning engine down |
| SEV-3 | Partial degradation | Slow response times |
| SEV-4 | Minor impact | UI glitch |

### 9.2 Incident Communication

| Phase | Action | Timeline |
|-------|--------|----------|
| Detection | Internal alert triggered | Immediate |
| Acknowledgment | Status page updated | Within 10 minutes |
| Updates | Status page + customer notification | Every 30 minutes |
| Resolution | Status page + incident summary | Upon resolution |
| Post-mortem | Root cause analysis shared | Within 5 business days |

### 9.3 Post-Incident Review

For SEV-1 and SEV-2 incidents:
- Root cause analysis completed within 5 business days
- Summary shared with affected customers
- Remediation actions documented
- Preventive measures implemented

---

## 10. Disaster Recovery

### 10.1 Recovery Objectives

| Metric | Target |
|--------|--------|
| Recovery Time Objective (RTO) | 4 hours |
| Recovery Point Objective (RPO) | 1 hour |
| Maximum Tolerable Downtime (MTD) | 8 hours |

### 10.2 Backup Strategy

| Data Type | Backup Frequency | Retention |
|-----------|-----------------|-----------|
| Database | Continuous (point-in-time) | 30 days |
| Configuration | Daily | 90 days |
| Logs | Real-time streaming | 1 year |
| Secrets | Encrypted, versioned | Indefinite |

### 10.3 Geographic Redundancy

- Primary region: AWS us-east-1
- Database: Multi-AZ deployment
- Static assets: CloudFront CDN (global)
- Cross-region backup: Available for Enterprise tier

---

## 11. Security Commitments

### 11.1 Security Standards

Cloud Optimizer maintains:
- SOC 2 Type I compliance (in progress)
- Data encryption at rest (AES-256)
- Data encryption in transit (TLS 1.2+)
- Regular penetration testing
- Continuous vulnerability scanning

### 11.2 Data Protection

| Aspect | Commitment |
|--------|------------|
| Data Encryption | AES-256 at rest, TLS 1.2+ in transit |
| Access Control | Role-based, MFA required |
| Audit Logging | All access logged, 1 year retention |
| Data Isolation | Tenant data logically separated |
| Data Location | US-based data centers (configurable) |

### 11.3 Compliance

- SOC 2 Type I (in progress)
- AWS Well-Architected Framework
- OWASP security guidelines

---

## 12. Amendments and Updates

### 12.1 SLA Changes

- Material changes require 30-day advance notice
- Non-material improvements may be made at any time
- Changes posted to documentation site

### 12.2 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-05 | Initial SLA document |

---

## 13. Contact Information

### 13.1 Support Channels

| Channel | Contact |
|---------|---------|
| Support Portal | support.cloudoptimizer.com |
| Email | support@cloudoptimizer.com |
| Emergency | Via PagerDuty (Enterprise only) |

### 13.2 Escalation

| Level | Contact | When to Use |
|-------|---------|-------------|
| Tier 1 | Support Team | Initial contact |
| Tier 2 | Senior Engineer | Unresolved after 2 hours |
| Tier 3 | Engineering Manager | SEV-1 incidents |
| Executive | Account Manager | SLA breach concerns |

---

## Appendix A: Definitions

| Term | Definition |
|------|------------|
| **Availability** | Percentage of time service is operational and accessible |
| **Downtime** | Period when service is unavailable (excluding exclusions) |
| **Incident** | Unplanned interruption or quality reduction |
| **Maintenance** | Scheduled service interruption for updates |
| **Response Time** | Time from ticket creation to first substantive response |
| **Resolution Time** | Time from ticket creation to issue resolution |
| **Service Credit** | Credit applied to future invoices |

---

## Appendix B: Related Documents

- [Business Continuity Plan](./BUSINESS_CONTINUITY_PLAN.md)
- [Incident Response Policy](./policies/INCIDENT_RESPONSE_POLICY.md)
- [Information Security Policy](./policies/INFORMATION_SECURITY_POLICY.md)
- [SOC 2 Readiness Checklist](./SOC2_READINESS_CHECKLIST.md)

---

*This SLA is subject to the terms of the Master Service Agreement between the parties.*
