# AWS Marketplace Listing - Cloud Optimizer

## Product Overview

**Cloud Optimizer** is an enterprise-grade AWS security and compliance scanning platform that helps organizations identify vulnerabilities, ensure compliance, and optimize their cloud infrastructure security posture.

Built on the Intelligence-Builder GraphRAG platform, Cloud Optimizer provides intelligent security analysis with natural language querying, automated compliance reporting, and actionable remediation guidance.

## Product Description

### Short Description (255 characters)
Cloud Optimizer: Enterprise AWS security scanning and compliance platform. Automated vulnerability detection, compliance frameworks (SOC2, ISO27001, NIST), and intelligent security insights powered by GraphRAG technology.

### Full Description

Cloud Optimizer provides comprehensive security and compliance scanning for AWS environments, enabling organizations to:

**Security Scanning**
- Automated security vulnerability detection across 15+ AWS services
- Real-time threat identification for Lambda, API Gateway, S3, CloudFront, and more
- Secrets detection and exposure analysis
- Cross-account security posture assessment
- Container security scanning with CVE detection

**Compliance & Governance**
- Pre-built compliance frameworks: SOC2, ISO 27001, NIST 800-53, PCI-DSS, HIPAA
- Automated compliance reporting and evidence generation
- Custom compliance rule engine
- Audit trail and change tracking
- Compliance dashboard with executive summaries

**Intelligent Analysis**
- Natural language security queries powered by GraphRAG
- Knowledge graph-based relationship analysis
- Pattern detection across your infrastructure
- AI-powered remediation recommendations
- Security trends and risk analytics

**Enterprise Features**
- Multi-account AWS organization support
- Role-based access control (RBAC)
- SSO/SAML integration
- API-first architecture with comprehensive REST API
- Webhook notifications and alerting
- Export to PDF, CSV, and JSON

## Target Audience

### Primary Users
- **Security Engineers**: Daily security scanning and vulnerability remediation
- **Compliance Officers**: Compliance framework implementation and audit preparation
- **DevSecOps Teams**: Automated security in CI/CD pipelines
- **Cloud Architects**: Security posture assessment and improvement planning
- **CISOs**: Executive security reporting and risk management

### Organization Size
- **SMB (10-100 employees)**: Professional Tier
- **Mid-Market (100-1000 employees)**: Professional or Enterprise Tier
- **Enterprise (1000+ employees)**: Enterprise Tier with multi-account support

### Industry Verticals
- Financial Services (PCI-DSS, SOC2)
- Healthcare (HIPAA compliance)
- Technology/SaaS (SOC2, ISO27001)
- Government/Public Sector (NIST 800-53, FedRAMP)
- E-commerce (PCI-DSS)

## Use Cases

### 1. Continuous Security Monitoring
**Scenario**: A SaaS company needs 24/7 security monitoring across their AWS infrastructure.

**Solution**: Cloud Optimizer provides:
- Scheduled daily scans of all AWS accounts
- Real-time alerting via SNS/Slack/Email when vulnerabilities detected
- Security dashboard showing current risk score
- Automated remediation guidance

**Benefit**: Reduce security incident detection time from days to minutes.

### 2. SOC2 Compliance Preparation
**Scenario**: A startup preparing for SOC2 Type II audit needs evidence of continuous security monitoring.

**Solution**: Cloud Optimizer provides:
- Pre-configured SOC2 control mappings
- Automated evidence collection and timestamping
- Compliance reports for auditors
- Historical audit trail

**Benefit**: Reduce audit preparation time by 70% and streamline auditor evidence requests.

### 3. Multi-Account Security Governance
**Scenario**: An enterprise with 50+ AWS accounts needs centralized security visibility.

**Solution**: Cloud Optimizer provides:
- Cross-account scanning with AWS Organizations integration
- Centralized security dashboard across all accounts
- Account-level and organization-level compliance reporting
- Security pattern detection across accounts

**Benefit**: Unified security posture view across entire AWS organization.

### 4. DevSecOps Integration
**Scenario**: A development team wants to shift-left security testing into their CI/CD pipeline.

**Solution**: Cloud Optimizer provides:
- REST API for integration with CI/CD tools
- Pre-deployment security checks
- Infrastructure-as-code scanning
- Automated security gates

**Benefit**: Catch security issues before production deployment.

### 5. Security Incident Investigation
**Scenario**: Security team investigating a potential data exposure needs to understand attack surface.

**Solution**: Cloud Optimizer provides:
- Natural language queries: "Show me all publicly accessible S3 buckets"
- GraphRAG relationship mapping: "What resources can access this database?"
- Historical configuration tracking
- Secrets exposure detection

**Benefit**: Reduce investigation time and improve incident response accuracy.

## Architecture Overview

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Your AWS Account                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           Cloud Optimizer Container                 │    │
│  │                                                      │    │
│  │  ┌──────────────┐      ┌────────────────┐         │    │
│  │  │   FastAPI    │◄─────┤  React UI      │         │    │
│  │  │   Backend    │      │  Dashboard     │         │    │
│  │  └──────┬───────┘      └────────────────┘         │    │
│  │         │                                           │    │
│  │         ├───► Security Scanners (15+ services)     │    │
│  │         ├───► Compliance Engine                    │    │
│  │         └───► GraphRAG Query Engine                │    │
│  │                                                      │    │
│  └──────────────────┬───────────────────────────────┬──┘    │
│                     │                               │       │
│                     ▼                               ▼       │
│            ┌─────────────────┐          ┌──────────────┐   │
│            │   PostgreSQL    │          │  AWS Services│   │
│            │   RDS Instance  │          │  (Read-Only) │   │
│            └─────────────────┘          └──────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         AWS Marketplace Integration                  │   │
│  │  • License Validation (RegisterUsage API)           │   │
│  │  • Usage Metering (MeterUsage API)                  │   │
│  │  • Entitlement Checking                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Technical Architecture

**Frontend**
- React 18+ with TypeScript
- Material-UI component library
- Real-time updates via WebSocket
- Responsive design for mobile/tablet

**Backend**
- FastAPI (Python 3.11+)
- Async/await for high performance
- REST API with OpenAPI documentation
- GraphRAG query engine

**Database**
- PostgreSQL 15+ (RDS recommended)
- Automated backups and encryption
- Connection pooling for scalability

**Security**
- AWS IAM role-based access (no credentials stored)
- TLS/HTTPS for all communication
- Secrets encryption at rest
- Audit logging for all operations

## Supported AWS Services

Cloud Optimizer scans and analyzes the following AWS services:

| Service | Security Checks | Compliance Checks |
|---------|----------------|-------------------|
| **Lambda** | Runtime vulnerabilities, excessive permissions, secrets in env vars | Function logging, encryption |
| **API Gateway** | Public endpoints, authentication, rate limiting | API logging, encryption in transit |
| **S3** | Public buckets, encryption, versioning, access logs | Bucket policies, lifecycle rules |
| **CloudFront** | Origin access, SSL/TLS config, logging | CDN security headers |
| **RDS** | Public accessibility, encryption, backup retention | Audit logging, multi-AZ |
| **EC2** | Security groups, public IPs, unencrypted volumes | Instance metadata, patch compliance |
| **IAM** | Overly permissive policies, unused credentials | MFA enforcement, password policy |
| **Secrets Manager** | Rotation status, access policies | Encryption, audit logging |
| **CloudWatch** | Log retention, metric alarms | Monitoring coverage |
| **VPC** | Flow logs, network ACLs, security groups | Network segmentation |
| **ECS/EKS** | Container vulnerabilities, secrets management | Cluster logging, network policies |
| **DynamoDB** | Encryption, backup status, point-in-time recovery | Access logging |
| **SNS/SQS** | Encryption, access policies | Message retention |
| **CloudTrail** | Trail status, log integrity | Multi-region logging |
| **KMS** | Key rotation, usage policies | Key deletion protection |

## Pricing Summary

Cloud Optimizer offers three pricing tiers to meet the needs of organizations at any scale:

### Free Trial (14 Days)
- 50 security scans
- 500 chat questions
- 20 document analyses
- All features enabled
- No credit card required

### Professional Tier
- **Starting at $500/month**
- Usage-based pricing
- Up to 5 AWS accounts
- Standard compliance frameworks
- Email support
- 99.5% SLA

### Enterprise Tier
- **Custom pricing**
- Unlimited AWS accounts
- Custom compliance frameworks
- Dedicated support
- 99.9% SLA
- SSO/SAML integration
- Custom training and onboarding

**Usage Dimensions**
- Security Scans: $0.50 per scan
- Chat Questions: $0.02 per question
- Document Analysis: $0.25 per document

See [PRICING_TIERS.md](PRICING_TIERS.md) for complete pricing details.

## Support Information

### Support Channels

**Free Trial & Professional Tier**
- Email support: support@cloudoptimizer.io
- Documentation: docs.cloudoptimizer.io
- Community Slack: slack.cloudoptimizer.io
- Response SLA: 24 hours (business days)

**Enterprise Tier**
- Dedicated support engineer
- Priority email and Slack channel
- Phone support (business hours)
- Quarterly business reviews
- Response SLA: 4 hours (24/7)

### Support Scope

**Included Support**
- Product usage questions
- Bug reports and troubleshooting
- Configuration assistance
- Best practices guidance
- API integration support

**Professional Services** (Additional fees)
- Custom scanner development
- Custom compliance framework creation
- AWS architecture review
- Migration assistance
- Custom training workshops

### Getting Help

1. **Documentation**: Start with our comprehensive docs at docs.cloudoptimizer.io
2. **Community**: Join our Slack community for peer support
3. **Email Support**: Send detailed questions to support@cloudoptimizer.io
4. **Enterprise Customers**: Contact your dedicated support engineer

### SLA Commitments

| Tier | Uptime SLA | Response Time | Support Hours |
|------|------------|---------------|---------------|
| **Free Trial** | Best effort | 48 hours | Business hours |
| **Professional** | 99.5% | 24 hours | Business hours |
| **Enterprise** | 99.9% | 4 hours | 24/7 |

## Getting Started

### Prerequisites
- AWS Account with admin access
- AWS Marketplace subscription
- PostgreSQL database (RDS recommended)
- ECS cluster or EC2 instance for container deployment

### Quick Start Guide

1. **Subscribe via AWS Marketplace**
   - Navigate to Cloud Optimizer in AWS Marketplace
   - Click "Subscribe" and accept terms
   - Choose your pricing tier

2. **Launch Container**
   ```bash
   docker run -d \
     --name cloud-optimizer \
     -p 8000:8000 \
     -e DATABASE_URL=postgresql://user:pass@host/db \
     -e AWS_REGION=us-east-1 \
     marketplace.amazonaws.com/cloud-optimizer:latest
   ```

3. **Configure AWS Permissions**
   - Create IAM role with SecurityAudit policy
   - Attach role to ECS task or EC2 instance

4. **Access Dashboard**
   - Navigate to http://your-instance:8000
   - Complete initial setup wizard
   - Add AWS accounts to scan

5. **Run First Scan**
   - Click "New Scan" in dashboard
   - Select AWS account and services
   - Review results and remediation guidance

### Detailed Documentation
For complete deployment instructions, see [END_USER_GUIDE.md](END_USER_GUIDE.md)

## Security & Compliance

### Security Practices
- **No AWS Credentials Storage**: Uses IAM roles exclusively
- **Encryption**: TLS in transit, AES-256 at rest
- **Audit Logging**: All actions logged with user attribution
- **Least Privilege**: Minimal IAM permissions required
- **Network Security**: VPC deployment with private subnets recommended

### Compliance Certifications
- SOC2 Type II (in progress)
- ISO 27001 (planned 2026)
- AWS Foundational Technical Review (FTR) compliant

### Data Handling
- **Scan Results**: Stored in your PostgreSQL database (your AWS account)
- **Usage Metrics**: Only dimension counts sent to AWS Marketplace
- **No PII Collection**: Cloud Optimizer does not collect or store personal information
- **Data Residency**: All data stays in your AWS account and region

## Product Roadmap

### Q1 2026
- Azure and GCP multi-cloud support
- SIEM integration (Splunk, Datadog)
- Advanced threat detection with ML
- Custom policy engine

### Q2 2026
- GitHub/GitLab IaC scanning
- Terraform state analysis
- Cost optimization recommendations
- Mobile app (iOS/Android)

### Q3 2026
- Kubernetes security scanning
- Container registry scanning
- Supply chain security analysis
- FedRAMP authorization

## Additional Resources

- **Product Website**: https://cloudoptimizer.io
- **Documentation**: https://docs.cloudoptimizer.io
- **API Reference**: https://api.cloudoptimizer.io/docs
- **GitHub**: https://github.com/intelligence-builder/cloud-optimizer
- **Community Slack**: https://slack.cloudoptimizer.io
- **Blog**: https://cloudoptimizer.io/blog
- **YouTube Channel**: https://youtube.com/@cloudoptimizer

## Contact Information

**Sales Inquiries**
- Email: sales@cloudoptimizer.io
- Schedule demo: https://cloudoptimizer.io/demo

**Technical Support**
- Email: support@cloudoptimizer.io
- Documentation: https://docs.cloudoptimizer.io

**General Information**
- Email: info@cloudoptimizer.io
- Website: https://cloudoptimizer.io

**Enterprise Partnerships**
- Email: partners@cloudoptimizer.io

---

**Cloud Optimizer** is developed by Intelligence-Builder and distributed exclusively through AWS Marketplace.

Copyright (c) 2025 Intelligence-Builder. All rights reserved.
