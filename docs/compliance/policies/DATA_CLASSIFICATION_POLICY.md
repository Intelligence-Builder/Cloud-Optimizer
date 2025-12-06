# Data Classification Policy

**Policy Number:** DCP-001
**Version:** 1.0
**Effective Date:** December 5, 2025
**Policy Owner:** Security Team
**Classification:** Internal

---

## 1. Purpose

This policy establishes a framework for classifying information based on sensitivity and criticality, ensuring appropriate protection controls are applied throughout the data lifecycle.

## 2. Scope

This policy applies to all data:
- Created, collected, or processed by Cloud Optimizer
- Stored in any system or medium
- Transmitted across networks
- Shared with third parties

## 3. Classification Levels

### 3.1 Restricted (Highest Sensitivity)

**Definition:** Data that, if disclosed, could cause severe harm to individuals or the organization.

**Examples:**
- AWS credentials (access keys, secret keys)
- Database passwords
- Encryption keys
- PII: SSN, credit card numbers, bank accounts
- Customer authentication credentials

**Controls:**
- Encryption at rest (AES-256 or equivalent)
- Encryption in transit (TLS 1.2+)
- Access limited to named individuals
- No storage in logs or debugging output
- Immediate incident response if exposed

### 3.2 Confidential

**Definition:** Data that is sensitive and should be protected from unauthorized access.

**Examples:**
- Customer AWS account information
- Security scan findings and vulnerabilities
- Customer contact information (email, phone)
- Internal business plans and strategies
- Compliance audit results

**Controls:**
- Encryption at rest recommended
- Encryption in transit required
- Role-based access control
- Audit logging of access
- PII redaction in logs

### 3.3 Internal

**Definition:** Data intended for internal use that should not be publicly disclosed.

**Examples:**
- System architecture documentation
- Internal policies and procedures
- Non-sensitive configuration data
- Aggregated usage metrics
- Employee directory information

**Controls:**
- Authentication required for access
- Logical access controls
- Not shared externally without approval

### 3.4 Public

**Definition:** Data that can be freely shared without restriction.

**Examples:**
- Marketing materials
- Public documentation
- Published API specifications
- Press releases
- Public-facing website content

**Controls:**
- No special protection required
- Review before publication
- Version control for accuracy

## 4. Data Handling Requirements

### 4.1 Storage

| Classification | At Rest | Location Restrictions |
|---------------|---------|----------------------|
| Restricted | Encrypted (mandatory) | Secure systems only |
| Confidential | Encrypted (recommended) | Approved systems |
| Internal | Standard protection | Internal systems |
| Public | No restriction | Any location |

### 4.2 Transmission

| Classification | In Transit | Methods Allowed |
|---------------|------------|-----------------|
| Restricted | Encrypted (TLS 1.2+) | Secure APIs only |
| Confidential | Encrypted | HTTPS, SFTP |
| Internal | Encrypted preferred | Standard protocols |
| Public | No restriction | Any method |

### 4.3 Retention

| Classification | Minimum Retention | Maximum Retention |
|---------------|-------------------|-------------------|
| Restricted | As needed | 90 days after use |
| Confidential | 1 year | 7 years |
| Internal | 1 year | 5 years |
| Public | As needed | Indefinite |

### 4.4 Disposal

| Classification | Method |
|---------------|--------|
| Restricted | Secure deletion, cryptographic erasure |
| Confidential | Secure deletion |
| Internal | Standard deletion |
| Public | Standard deletion |

## 5. Data Types in Cloud Optimizer

### 5.1 Restricted Data

| Data Element | Storage Location | Protection |
|--------------|------------------|------------|
| AWS Access Keys | PostgreSQL (encrypted) | Fernet encryption |
| AWS Secret Keys | PostgreSQL (encrypted) | Fernet encryption |
| JWT Secrets | Environment variable | AWS Secrets Manager |
| Database Password | Environment variable | AWS Secrets Manager |

### 5.2 Confidential Data

| Data Element | Storage Location | Protection |
|--------------|------------------|------------|
| User Email | PostgreSQL | TLS in transit |
| User Password Hash | PostgreSQL | Bcrypt hashed |
| Security Findings | PostgreSQL | RLS (planned) |
| AWS Account IDs | PostgreSQL | Access control |

### 5.3 Internal Data

| Data Element | Storage Location | Protection |
|--------------|------------------|------------|
| System Logs | CloudWatch | PII redaction |
| Correlation IDs | CloudWatch | None required |
| Configuration | Environment | Access control |
| Metrics | CloudWatch | None required |

## 6. Labeling and Marking

### 6.1 Document Marking

All documents should include classification:
- Header or footer notation
- File naming convention (e.g., `DOC_CONFIDENTIAL_xxx.pdf`)

### 6.2 System Marking

- Database fields should be annotated in schema
- API responses should not include classification in response body
- Logs should never contain Restricted data

## 7. Responsibilities

### 7.1 Data Owners
- Classify data assets
- Define access requirements
- Review classification annually

### 7.2 All Personnel
- Handle data according to classification
- Report misclassification
- Protect data appropriately

## 8. PII Detection Patterns

Cloud Optimizer automatically detects and redacts:

```python
# Restricted - Always Redacted
- Email addresses
- Phone numbers
- Credit card numbers
- Social Security Numbers
- AWS access keys
- AWS secret keys
- JWT tokens
- Generic API keys
- Password fields
- Authorization headers
```

## 9. Compliance Mapping

| Classification | SOC 2 | GDPR | HIPAA |
|---------------|-------|------|-------|
| Restricted | C1.1, CC6.7 | Art. 32 | 164.312 |
| Confidential | C1.1 | Art. 32 | 164.312 |
| Internal | CC5.1 | - | - |
| Public | - | - | - |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-05 | Smart Scaffold | Initial policy creation |
