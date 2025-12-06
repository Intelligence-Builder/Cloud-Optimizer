# Cloud Optimizer - Penetration Test Scope Document

**Issue:** #162 - Penetration Testing Preparation
**Version:** 1.0
**Date:** 2025-12-05
**Classification:** CONFIDENTIAL

---

## 1. Executive Summary

This document defines the scope, objectives, and rules of engagement for penetration testing of the Cloud Optimizer application. The testing aims to identify security vulnerabilities before production deployment and ensure compliance with SOC 2 requirements.

## 2. Application Overview

### 2.1 Application Description
Cloud Optimizer is a cloud security and cost optimization platform that:
- Scans AWS accounts for security vulnerabilities
- Analyzes cloud configurations against best practices
- Provides remediation recommendations
- Generates compliance reports (SOC 2, ISO 27001, FedRAMP, PCI-DSS, HIPAA)

### 2.2 Technology Stack
| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | React / TypeScript |
| Database | PostgreSQL 15 |
| Cache | Redis |
| Container | Docker / ECS Fargate |
| Infrastructure | AWS (ALB, ECS, RDS, S3) |
| Authentication | JWT / OAuth 2.0 |

### 2.3 Architecture Components
- **API Server**: RESTful API on port 8080
- **Frontend**: React SPA served via CloudFront
- **Database**: PostgreSQL with encrypted connections
- **Background Workers**: Async task processing
- **External Integrations**: AWS APIs, SSO providers

## 3. Scope Definition

### 3.1 In-Scope Assets

#### 3.1.1 Web Application
| Asset | Description | Priority |
|-------|-------------|----------|
| `api.cloud-optimizer.example.com` | Production API | Critical |
| `app.cloud-optimizer.example.com` | Frontend application | Critical |
| `pentest.cloud-optimizer.example.com` | Isolated test environment | High |

#### 3.1.2 API Endpoints
| Category | Endpoints | Authentication |
|----------|-----------|----------------|
| Authentication | `/api/v1/auth/*` | Public/JWT |
| AWS Accounts | `/api/v1/aws-accounts/*` | JWT Required |
| Scans | `/api/v1/scans/*` | JWT Required |
| Findings | `/api/v1/findings/*` | JWT Required |
| Reports | `/api/v1/reports/*` | JWT Required |
| Users | `/api/v1/users/*` | JWT + Admin |
| Health | `/health`, `/ready` | Public |

#### 3.1.3 Infrastructure Components
- Application Load Balancer (ALB)
- ECS Fargate Services
- RDS PostgreSQL Database
- S3 Buckets (report storage)
- CloudFront Distribution
- VPC and Security Groups

### 3.2 Out-of-Scope Assets

The following are **explicitly excluded** from testing:

| Asset | Reason |
|-------|--------|
| AWS Console | AWS's responsibility |
| Third-party SaaS integrations | External providers |
| Customer AWS accounts | Customer data |
| Production database | Use test environment |
| Physical infrastructure | AWS data centers |
| Other AWS services not listed | Not part of application |

### 3.3 Testing Types Authorized

| Test Type | Authorized | Notes |
|-----------|------------|-------|
| Network Penetration Testing | Yes | Test environment only |
| Web Application Testing | Yes | OWASP Top 10 focus |
| API Security Testing | Yes | All documented endpoints |
| Authentication Testing | Yes | Including MFA bypass attempts |
| Authorization Testing | Yes | RBAC and privilege escalation |
| Session Management Testing | Yes | JWT token security |
| Input Validation Testing | Yes | SQL injection, XSS, etc. |
| Business Logic Testing | Yes | Workflow manipulation |
| DoS/DDoS Testing | Limited | Coordinated with ops team |
| Social Engineering | No | Not authorized |
| Physical Testing | No | Not authorized |

## 4. Test Environment

### 4.1 Environment Details
```
Environment: Penetration Test
URL: https://pentest.cloud-optimizer.example.com
API: https://pentest-api.cloud-optimizer.example.com
Region: us-east-1
```

### 4.2 Test Credentials

Credentials will be provided via secure channel prior to engagement.

| Role | Username | Access Level |
|------|----------|--------------|
| Standard User | `pentest-user@example.com` | Basic features |
| Admin User | `pentest-admin@example.com` | Administrative features |
| Read-Only User | `pentest-readonly@example.com` | View-only access |
| API Service Account | `pentest-api-key` | API access |

### 4.3 Sample Data
The test environment contains:
- 5 simulated AWS accounts
- 1000+ sample security findings
- Sample compliance reports
- Test user accounts

**Note:** No real customer data is present in the test environment.

## 5. Rules of Engagement

### 5.1 Testing Window
| Parameter | Value |
|-----------|-------|
| Start Date | TBD |
| End Date | TBD |
| Testing Hours | 09:00 - 17:00 EST (Mon-Fri) |
| After-Hours Testing | Requires approval |

### 5.2 Authorized Activities

**Authorized:**
- Vulnerability scanning
- Manual exploitation attempts
- Credential stuffing (test accounts only)
- Parameter manipulation
- Session hijacking attempts
- File upload testing
- API fuzzing
- Rate limit testing (within reasonable bounds)

**Not Authorized:**
- Denial of Service attacks on production
- Testing against customer data
- Social engineering attacks
- Physical security testing
- Modification of audit logs
- Data exfiltration of real data

### 5.3 Testing Restrictions

1. **No Persistent Changes**: Do not modify production configurations
2. **Data Handling**: Any data obtained must be handled per NDA
3. **Immediate Reporting**: Critical findings must be reported immediately
4. **Communication**: Notify team before high-intensity scanning
5. **Stop Conditions**: Halt testing if production impact detected

### 5.4 Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| Security Lead | TBD | security@example.com |
| DevOps On-Call | TBD | ops@example.com |
| Emergency Hotline | TBD | +1-xxx-xxx-xxxx |

## 6. Communication Protocol

### 6.1 Regular Updates
- Daily status updates via email
- Weekly progress meetings (30 min)
- Immediate notification of critical findings

### 6.2 Finding Classification

| Severity | Response Time | Example |
|----------|---------------|---------|
| Critical | Immediate | RCE, SQL injection with data access |
| High | 4 hours | Auth bypass, IDOR with PII access |
| Medium | 24 hours | XSS, CSRF, information disclosure |
| Low | 48 hours | Missing headers, verbose errors |
| Informational | End of engagement | Best practice recommendations |

### 6.3 Reporting Requirements

**Interim Reports:**
- Weekly summary of findings
- Critical/High findings as discovered

**Final Report:**
- Executive summary
- Technical findings with evidence
- Risk ratings (CVSS 3.1)
- Remediation recommendations
- Proof of concept (sanitized)
- Retest verification

## 7. Technical Requirements

### 7.1 Tester Requirements
- [ ] Signed NDA and MSA
- [ ] Valid certifications (OSCP, CEH, GWAPT, etc.)
- [ ] Background check completed
- [ ] Insurance verification
- [ ] Secure testing environment

### 7.2 Evidence Requirements
- Screenshots of all findings
- HTTP request/response captures
- Proof of concept code (where applicable)
- Video recordings for complex vulnerabilities
- Detailed reproduction steps

## 8. Compliance Alignment

This penetration test supports compliance with:

| Framework | Requirement |
|-----------|-------------|
| SOC 2 | CC6.1 - Vulnerability Management |
| SOC 2 | CC7.2 - Security Monitoring |
| ISO 27001 | A.12.6.1 - Technical Vulnerability Management |
| PCI-DSS | 11.3 - Penetration Testing |
| FedRAMP | CA-8 - Penetration Testing |

## 9. Acceptance Criteria

The penetration test is considered complete when:
- [ ] All in-scope assets have been tested
- [ ] OWASP Top 10 (2021) vulnerabilities assessed
- [ ] API security testing completed
- [ ] Authentication/authorization testing completed
- [ ] Final report delivered
- [ ] All critical/high findings verified remediated
- [ ] Retest of remediated vulnerabilities completed

## 10. Document Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Security Lead | | | |
| Engineering Lead | | | |
| Legal/Compliance | | | |
| Pentesting Firm | | | |

---

## Appendix A: OWASP Testing Checklist

- [ ] A01:2021 - Broken Access Control
- [ ] A02:2021 - Cryptographic Failures
- [ ] A03:2021 - Injection
- [ ] A04:2021 - Insecure Design
- [ ] A05:2021 - Security Misconfiguration
- [ ] A06:2021 - Vulnerable and Outdated Components
- [ ] A07:2021 - Identification and Authentication Failures
- [ ] A08:2021 - Software and Data Integrity Failures
- [ ] A09:2021 - Security Logging and Monitoring Failures
- [ ] A10:2021 - Server-Side Request Forgery (SSRF)

## Appendix B: API Security Checklist

- [ ] Authentication bypass attempts
- [ ] Authorization testing (BOLA/IDOR)
- [ ] Rate limiting effectiveness
- [ ] Input validation on all parameters
- [ ] JWT token security
- [ ] API versioning security
- [ ] Error handling and information leakage
- [ ] Mass assignment vulnerabilities
- [ ] Security header presence
- [ ] CORS configuration
