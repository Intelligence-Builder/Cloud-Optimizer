# Cloud Optimizer - Application Architecture for Security Testing

**Issue:** #162 - Penetration Testing Preparation
**Version:** 1.0
**Classification:** CONFIDENTIAL - For Authorized Security Testers Only

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                           VPC (10.0.0.0/16)                              │ │
│  │                                                                           │ │
│  │  ┌────────────┐    ┌─────────────────────────────────────────────────┐  │ │
│  │  │ CloudFront │    │              Public Subnets                      │  │ │
│  │  │    CDN     │    │  ┌─────────────────────────────────────────┐    │  │ │
│  │  └─────┬──────┘    │  │         Application Load Balancer       │    │  │ │
│  │        │           │  │           (Internet-facing)              │    │  │ │
│  │        │           │  │   - Port 443 (HTTPS)                     │    │  │ │
│  │        │           │  │   - SSL Termination                      │    │  │ │
│  │        │           │  │   - WAF Integration                      │    │  │ │
│  │        │           │  └──────────────────┬──────────────────────┘    │  │ │
│  │        │           └─────────────────────┼───────────────────────────┘  │ │
│  │        │                                 │                               │ │
│  │  ┌─────┴──────────────────────────────────┴─────────────────────────┐   │ │
│  │  │                      Private Subnets                              │   │ │
│  │  │                                                                   │   │ │
│  │  │   ┌────────────────────┐    ┌────────────────────────────────┐   │   │ │
│  │  │   │   ECS Fargate      │    │      ECS Fargate               │   │   │ │
│  │  │   │   (API Service)    │    │      (Background Workers)      │   │   │ │
│  │  │   │                    │    │                                │   │   │ │
│  │  │   │   Port 8080        │    │   - Scan execution             │   │   │ │
│  │  │   │   - FastAPI        │    │   - Report generation          │   │   │ │
│  │  │   │   - JWT Auth       │    │   - AWS API calls              │   │   │ │
│  │  │   └────────┬───────────┘    └────────────────────────────────┘   │   │ │
│  │  │            │                                                      │   │ │
│  │  │   ┌────────┴───────────┐    ┌────────────────────────────────┐   │   │ │
│  │  │   │   Redis Cache      │    │      PostgreSQL RDS            │   │   │ │
│  │  │   │   (ElastiCache)    │    │      (Multi-AZ)                │   │   │ │
│  │  │   │                    │    │                                │   │   │ │
│  │  │   │   Port 6379        │    │   Port 5432                    │   │   │ │
│  │  │   │   - Sessions       │    │   - User data                  │   │   │ │
│  │  │   │   - Rate limits    │    │   - Scan results               │   │   │ │
│  │  │   │   - Cache          │    │   - Audit logs                 │   │   │ │
│  │  │   └────────────────────┘    └────────────────────────────────┘   │   │ │
│  │  │                                                                   │   │ │
│  │  └───────────────────────────────────────────────────────────────────┘   │ │
│  │                                                                           │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐   │ │
│  │  │                      S3 Buckets                                    │   │ │
│  │  │   - Report Storage (encrypted)                                     │   │ │
│  │  │   - Static Assets                                                  │   │ │
│  │  │   - Audit Logs                                                     │   │ │
│  │  └───────────────────────────────────────────────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Component Details

### 2.1 Frontend Application (React)

| Aspect | Details |
|--------|---------|
| Framework | React 18 with TypeScript |
| Hosting | CloudFront + S3 |
| Authentication | JWT stored in httpOnly cookies |
| State Management | React Query |
| Build | Vite |

**Security Features:**
- CSP headers enforced
- XSS protection via React's built-in escaping
- CORS configured for API domain only
- No sensitive data in localStorage

### 2.2 Backend API (FastAPI)

| Aspect | Details |
|--------|---------|
| Framework | FastAPI 0.100+ |
| Runtime | Python 3.11+ / uvicorn |
| Container | Docker / ECS Fargate |
| Port | 8080 (internal) |

**Endpoints Structure:**
```
/api/v1/
├── auth/
│   ├── login          POST   # JWT authentication
│   ├── logout         POST   # Token invalidation
│   ├── refresh        POST   # Token refresh
│   └── register       POST   # User registration
├── users/
│   ├── me             GET    # Current user
│   ├── {id}           GET    # User by ID (admin)
│   └── list           GET    # List users (admin)
├── aws-accounts/
│   ├── list           GET    # List connected accounts
│   ├── connect        POST   # Connect new account
│   ├── {id}           GET    # Account details
│   └── {id}/delete    DELETE # Remove account
├── scans/
│   ├── list           GET    # List scans
│   ├── start          POST   # Start new scan
│   ├── {id}           GET    # Scan details
│   └── {id}/cancel    POST   # Cancel scan
├── findings/
│   ├── list           GET    # List findings
│   ├── {id}           GET    # Finding details
│   └── {id}/status    PATCH  # Update finding status
├── reports/
│   ├── list           GET    # List reports
│   ├── generate       POST   # Generate report
│   └── {id}/download  GET    # Download report
└── health             GET    # Health check (public)
```

### 2.3 Database (PostgreSQL)

| Aspect | Details |
|--------|---------|
| Version | PostgreSQL 15 |
| Hosting | RDS Multi-AZ |
| Encryption | At-rest (AES-256), In-transit (TLS) |
| Backups | Daily automated, 7-day retention |

**Key Tables:**
- `users` - User accounts and credentials
- `organizations` - Multi-tenant organization data
- `aws_accounts` - Connected AWS account metadata
- `scans` - Scan execution records
- `findings` - Security findings
- `audit_logs` - All user actions

### 2.4 Authentication Flow

```
┌────────────┐         ┌─────────────┐         ┌──────────────┐
│   Client   │         │   FastAPI   │         │  PostgreSQL  │
└─────┬──────┘         └──────┬──────┘         └──────┬───────┘
      │                       │                       │
      │  POST /auth/login     │                       │
      │  (email, password)    │                       │
      ├──────────────────────►│                       │
      │                       │  Query user           │
      │                       ├──────────────────────►│
      │                       │  User record          │
      │                       │◄──────────────────────┤
      │                       │                       │
      │                       │  Verify bcrypt hash   │
      │                       │  Generate JWT         │
      │                       │  (15min access,       │
      │                       │   7d refresh)         │
      │  Set-Cookie: token    │                       │
      │◄──────────────────────┤                       │
      │                       │                       │
      │  GET /api/resource    │                       │
      │  Cookie: token        │                       │
      ├──────────────────────►│                       │
      │                       │  Validate JWT         │
      │                       │  Check permissions    │
      │  Response             │                       │
      │◄──────────────────────┤                       │
```

**JWT Token Structure:**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_uuid",
    "email": "user@example.com",
    "org_id": "org_uuid",
    "roles": ["user", "admin"],
    "exp": 1699999999,
    "iat": 1699998999,
    "jti": "unique_token_id"
  }
}
```

## 3. Security Controls

### 3.1 Network Security

| Control | Implementation |
|---------|----------------|
| TLS | 1.2 minimum, 1.3 preferred |
| WAF | AWS WAF with OWASP rules |
| Security Groups | Least privilege, no 0.0.0.0/0 |
| VPC | Private subnets for services |
| NACLs | Additional network filtering |

### 3.2 Application Security

| Control | Implementation |
|---------|----------------|
| Authentication | JWT with RS256/HS256 |
| Authorization | RBAC with role checks |
| Input Validation | Pydantic models |
| Output Encoding | FastAPI automatic JSON encoding |
| Rate Limiting | 100 req/min per user, 1000/min global |
| CORS | Configured for specific origins |
| CSP | Restrictive policy |

### 3.3 Security Headers

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: accelerometer=(), camera=(), geolocation=()
Content-Security-Policy: default-src 'self'; script-src 'self'
```

### 3.4 Data Protection

| Data Type | Protection |
|-----------|------------|
| Passwords | bcrypt (cost factor 12) |
| AWS Credentials | Encrypted in database, IAM roles preferred |
| API Keys | Hashed, not reversible |
| PII | Encrypted at rest |
| Logs | No sensitive data logged |

## 4. Attack Surface Analysis

### 4.1 External Attack Surface

| Entry Point | Risk Level | Notes |
|-------------|------------|-------|
| ALB (443) | High | Internet-facing, WAF protected |
| CloudFront | Medium | Static content only |
| API Endpoints | High | Primary attack vector |

### 4.2 Internal Attack Surface

| Component | Risk Level | Notes |
|-----------|------------|-------|
| Database | Critical | Contains all data |
| Redis | Medium | Session/cache data |
| S3 Buckets | High | Report storage |
| ECS Tasks | Medium | Application logic |

### 4.3 Known Trust Boundaries

1. **Internet → WAF/ALB**: First line of defense
2. **ALB → ECS**: Internal network, still validated
3. **ECS → Database**: Credentials required
4. **ECS → AWS APIs**: IAM role-based

## 5. Authentication & Authorization Details

### 5.1 User Roles

| Role | Permissions |
|------|-------------|
| `viewer` | Read findings, reports |
| `user` | + Create scans, manage findings |
| `admin` | + Manage users, organization settings |
| `super_admin` | + System-wide access |

### 5.2 Permission Matrix

| Resource | viewer | user | admin | super_admin |
|----------|--------|------|-------|-------------|
| View Findings | Yes | Yes | Yes | Yes |
| Create Scan | No | Yes | Yes | Yes |
| Update Finding | No | Yes | Yes | Yes |
| Manage Users | No | No | Yes | Yes |
| System Config | No | No | No | Yes |

### 5.3 Session Management

- Access Token: 15 minutes
- Refresh Token: 7 days
- Concurrent Sessions: Limited to 5
- Session Invalidation: On logout, password change

## 6. API Security Specifications

### 6.1 Rate Limits

| Endpoint Category | Rate Limit |
|-------------------|------------|
| Authentication | 5/min per IP |
| API (authenticated) | 100/min per user |
| API (global) | 1000/min total |
| Health Check | Unlimited |

### 6.2 Request Validation

All requests validated using:
- Pydantic schemas for body
- Query parameter type validation
- Path parameter validation
- Header validation for auth

### 6.3 Error Handling

Standardized error response:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "User-friendly message",
    "details": []
  }
}
```

**Note:** Stack traces never exposed in production.

## 7. Logging and Monitoring

### 7.1 Audit Log Events

| Event | Logged Fields |
|-------|---------------|
| Login Success | user_id, ip, timestamp |
| Login Failure | email_hash, ip, timestamp, reason |
| Resource Access | user_id, resource, action, timestamp |
| Admin Action | user_id, action, target, before, after |

### 7.2 Security Monitoring

- CloudWatch Alarms for anomalies
- AWS GuardDuty integration
- Failed login threshold alerts
- Rate limit breach alerts

## 8. Test Environment Setup

### 8.1 Access Information

```
Test Environment URL: https://pentest.cloud-optimizer.example.com
API Base URL: https://pentest-api.cloud-optimizer.example.com/api/v1
```

### 8.2 Test Data

The environment contains:
- 10 test user accounts (various roles)
- 5 simulated AWS accounts
- 1000+ sample security findings
- Sample compliance reports

### 8.3 Resetting Test Environment

Test environment can be reset upon request. Contact security team.

---

## Appendix A: API Examples

### A.1 Authentication
```bash
# Login
curl -X POST https://api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### A.2 Protected Resource
```bash
curl -X GET https://api/api/v1/findings \
  -H "Authorization: Bearer eyJ..."
```

## Appendix B: Security Contacts

| Role | Contact |
|------|---------|
| Security Lead | security@example.com |
| DevOps | ops@example.com |
| Emergency | +1-xxx-xxx-xxxx |
