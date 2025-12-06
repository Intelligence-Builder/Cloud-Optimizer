# Data Retention Policy

**Document Version:** 1.0
**Effective Date:** December 5, 2025
**Last Reviewed:** December 5, 2025
**Policy Owner:** Data Protection Officer
**Issue Reference:** #163

---

## 1. Purpose

This policy defines the requirements for retaining and disposing of data in Cloud Optimizer systems to meet business needs, legal requirements, and compliance obligations.

---

## 2. Scope

This policy applies to all data processed by Cloud Optimizer:
- Customer data
- User account data
- Application logs
- Security findings
- System metrics
- Audit records
- Backup data

---

## 3. Data Retention Principles

1. **Necessity:** Retain data only as long as needed for business purposes
2. **Compliance:** Meet all legal and regulatory retention requirements
3. **Minimization:** Limit data collection and storage to what is necessary
4. **Security:** Protect retained data according to classification level
5. **Accessibility:** Ensure authorized access to retained data
6. **Disposal:** Securely delete data when retention period expires

---

## 4. Retention Schedules

### 4.1 Customer Data

| Data Type | Retention Period | Trigger | Legal Basis |
|-----------|-----------------|---------|-------------|
| AWS Account Connections | Active subscription + 30 days | Account deletion or subscription end | Contract |
| Security Scan Results | 2 years | Scan date | Business need |
| Compliance Reports | 7 years | Report generation date | SOC 2, regulatory |
| Cost Analysis Data | 3 years | Analysis date | Business need |

### 4.2 User Account Data

| Data Type | Retention Period | Trigger | Legal Basis |
|-----------|-----------------|---------|-------------|
| Account Information | Active + 30 days | Account deletion | Contract |
| Authentication Tokens | Session duration | Logout or expiry | Security |
| Password Hashes | Current only | Password change | Security |
| MFA Secrets | Active use only | Deactivation | Security |

### 4.3 Operational Data

| Data Type | Retention Period | Trigger | Legal Basis |
|-----------|-----------------|---------|-------------|
| Application Logs | 30 days | Log creation | Operations |
| Error Logs | 90 days | Log creation | Debugging |
| Audit Logs | 365 days | Log creation | SOC 2 compliance |
| Security Event Logs | 2 years | Event date | Compliance |
| Metrics Data | 15 months | Collection date | CloudWatch default |

### 4.4 Backup Data

| Data Type | Retention Period | Trigger | Legal Basis |
|-----------|-----------------|---------|-------------|
| Database Backups | 30 days (automated) | Backup date | Recovery |
| Deletion Snapshots | 90 days | Deletion date | Recovery |
| DR Backups | 30 days | Backup date | Business continuity |

---

## 5. Extended Retention

Data may be retained beyond standard periods when:
- Subject to legal hold or litigation
- Required for ongoing investigation
- Regulatory examination in progress
- Customer contractual requirement

Extended retention must be:
- Documented with justification
- Approved by Legal/Compliance
- Reviewed quarterly for continued need

---

## 6. Data Disposal

### 6.1 Disposal Methods

| Classification | Disposal Method |
|----------------|-----------------|
| Public | Standard deletion |
| Internal | Standard deletion with verification |
| Confidential | Secure deletion (overwrite) |
| Restricted | Cryptographic erasure or physical destruction |

### 6.2 Disposal Procedures

**Digital Data:**
1. Verify retention period has expired
2. Confirm no legal holds apply
3. Execute deletion using approved tools
4. Verify deletion complete
5. Document disposal

**Cloud Resources:**
1. Terminate/delete cloud resources
2. Verify no orphaned storage
3. Confirm encryption keys destroyed (for crypto-shredding)
4. Document disposal

### 6.3 Disposal Verification

- Automated deletion jobs log completion
- Periodic audits verify disposal
- Annual review of disposal processes

---

## 7. Customer Data Rights

### 7.1 Data Access Requests

Customers may request access to their data:
- Response within 30 days
- Export in machine-readable format (JSON)
- Via API or support request

### 7.2 Data Deletion Requests

Customers may request data deletion:
- Process within 30 days
- Confirm completion in writing
- Retain proof of deletion for 3 years

### 7.3 Data Portability

Customers may request data export:
- Provide in structured, machine-readable format
- Include all customer-generated data
- Process within 30 days

---

## 8. Roles and Responsibilities

| Role | Responsibilities |
|------|-----------------|
| Data Protection Officer | Policy ownership, compliance monitoring |
| Engineering Team | Implement retention automation |
| Operations Team | Execute disposal procedures |
| Legal/Compliance | Legal hold management |
| All Employees | Adhere to retention requirements |

---

## 9. Implementation

### 9.1 Automated Retention

The following automated processes enforce retention:
- CloudWatch Logs: Retention policy set per log group
- RDS: Automated backup retention configured
- S3: Lifecycle policies for object expiration
- Application: Background jobs for data cleanup

### 9.2 Manual Processes

The following require manual review:
- Legal hold placement and release
- Customer deletion requests
- Extended retention approvals
- Disposal verification

---

## 10. Monitoring and Audit

### 10.1 Monitoring

- Track data volumes by category
- Alert on retention policy failures
- Monitor disposal job completion

### 10.2 Annual Audit

- Review retention schedules for accuracy
- Verify disposal procedures followed
- Assess compliance with policy
- Update based on legal changes

---

## 11. Exceptions

Exceptions to this policy require:
- Written justification
- Approval from Data Protection Officer
- Legal/Compliance review
- Annual review for continued need

---

## 12. Compliance

This policy supports compliance with:
- SOC 2 C1.3 (Confidential Information Disposal)
- GDPR Article 17 (Right to Erasure)
- CCPA Section 1798.105 (Right to Deletion)
- ISO 27001 A.8.3 (Media Handling)

---

## 13. Policy Review

This policy will be reviewed annually or upon:
- Changes to legal requirements
- Changes to business operations
- Compliance audit findings
- Data breach incidents

---

*Approved by: Data Protection Officer*
*Next Review Date: December 5, 2026*
