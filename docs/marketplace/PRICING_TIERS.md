# Cloud Optimizer - Pricing Tiers

## Overview

Cloud Optimizer offers flexible pricing designed to scale with your organization's needs. All tiers include usage-based pricing with transparent metering for security scans, AI-powered chat questions, and document analysis.

## Pricing Model

**Base Model**: Usage-Based Pricing (Pay-as-you-go)

All pricing tiers use the same metering dimensions:
- **Security Scans**: $0.50 per scan
- **Chat Questions**: $0.02 per question
- **Document Analysis**: $0.25 per document

## Tier Comparison

| Feature | Free Trial | Professional | Enterprise |
|---------|-----------|--------------|------------|
| **Duration** | 14 days | Monthly/Annual | Monthly/Annual |
| **Base Price** | $0 | $500/month | Custom |
| **AWS Accounts** | 1 | Up to 5 | Unlimited |
| **Security Scans** | 50 total | Unlimited (metered) | Unlimited (metered) |
| **Chat Questions** | 500 total | Unlimited (metered) | Unlimited (metered) |
| **Document Analysis** | 20 total | Unlimited (metered) | Unlimited (metered) |
| **Compliance Frameworks** | All standard | All standard | Custom frameworks |
| **Support** | Community | Email (24hr) | Dedicated + Phone (4hr) |
| **SLA** | None | 99.5% | 99.9% |
| **SSO/SAML** | No | No | Yes |
| **API Access** | Limited | Full | Full + Priority |
| **Data Retention** | 30 days | 1 year | Custom |
| **Users** | 1 | 5 | Unlimited |
| **Multi-Region** | No | Single region | Multi-region |
| **Custom Rules** | No | 10 rules | Unlimited |
| **Training** | Self-service | Documentation | Onboarding + Workshops |
| **Audit Reports** | Basic | Standard | Custom + Executive |

## Tier Details

### Free Trial Tier

**Perfect for**: Evaluating Cloud Optimizer before purchasing

**What's Included**:
- 14-day trial period (no credit card required)
- 1 AWS account connection
- 50 security scans total
- 500 chat questions total
- 20 document analyses total
- Access to all standard compliance frameworks (SOC2, ISO27001, NIST, PCI-DSS, HIPAA)
- Community support via Slack
- All scanner types enabled
- 30-day data retention

**Trial Limits**:
```json
{
  "duration_days": 14,
  "limits": {
    "scans": 50,
    "chat_questions": 500,
    "documents": 20,
    "aws_accounts": 1,
    "users": 1,
    "custom_rules": 0
  }
}
```

**After Trial Expires**:
- Read-only access to historical scan data
- Upgrade prompt on all pages
- Cannot run new scans or queries
- Data preserved for 30 days

**Trial Extension**:
- One-time 7-day extension available
- Request via in-app banner or support email
- Limits remain the same

### Professional Tier

**Perfect for**: SMBs and growing companies with moderate security scanning needs

**Base Price**: $500/month (billed monthly) or $5,000/year (billed annually, save 17%)

**What's Included**:
- Up to 5 AWS accounts
- Unlimited security scans (usage-based pricing)
- Unlimited chat questions (usage-based pricing)
- Unlimited document analyses (usage-based pricing)
- Up to 5 user accounts
- All standard compliance frameworks
- Email support (24-hour response SLA)
- 99.5% uptime SLA
- API access with rate limiting
- 1-year data retention
- Up to 10 custom security rules
- Weekly summary reports
- Webhook integrations (Slack, Teams, PagerDuty)

**Usage Metering Dimensions**:
```yaml
SecurityScans:
  Description: "Number of AWS account scans performed"
  Unit: "Scans"
  PricePerUnit: $0.50
  Calculation: "One scan = full analysis of one AWS account"
  Example: "100 scans/month = $50 usage fee"

ChatQuestions:
  Description: "AI-powered security questions via natural language interface"
  Unit: "Questions"
  PricePerUnit: $0.02
  Calculation: "Each question submitted to GraphRAG engine"
  Example: "1,000 questions/month = $20 usage fee"

DocumentAnalysis:
  Description: "Architecture and policy document security analysis"
  Unit: "Documents"
  PricePerUnit: $0.25
  Calculation: "Each document uploaded and analyzed"
  Example: "50 documents/month = $12.50 usage fee"
```

**Estimated Monthly Cost** (typical usage):
```
Base Price:              $500.00
+ 200 scans × $0.50:     $100.00
+ 2,000 questions × $0.02: $40.00
+ 100 documents × $0.25:  $25.00
────────────────────────────────
Total:                   $665.00/month
```

**Account Limits**:
```json
{
  "aws_accounts": 5,
  "users": 5,
  "custom_rules": 10,
  "webhooks": 5,
  "api_rate_limit": "100 requests/minute",
  "data_retention_days": 365,
  "scan_frequency": "Hourly minimum"
}
```

**Annual Pricing**:
- $5,000/year (paid upfront)
- Saves $1,000 (17% discount) vs monthly billing
- Same usage metering rates
- Lock in pricing for 12 months

### Enterprise Tier

**Perfect for**: Large organizations with complex multi-account AWS environments

**Base Price**: Custom (contact sales)

**What's Included**:
- **Unlimited** AWS accounts
- **Unlimited** security scans (usage-based pricing at discounted rates)
- **Unlimited** chat questions (usage-based pricing at discounted rates)
- **Unlimited** document analyses (usage-based pricing at discounted rates)
- **Unlimited** user accounts
- All standard compliance frameworks
- **Custom compliance framework development**
- Dedicated support engineer (4-hour response SLA, 24/7)
- 99.9% uptime SLA with credits
- Priority API access (no rate limits)
- **Custom data retention** (2+ years)
- **Unlimited** custom security rules
- Single Sign-On (SSO/SAML integration)
- Multi-region deployment
- Quarterly business reviews
- Custom training and onboarding workshops
- Executive-level compliance reports
- Advanced integrations (SIEM, ticketing systems)
- Private Slack channel with engineering team

**Enterprise Usage Pricing** (Volume Discounts):

Tiered pricing based on monthly volume:

**Security Scans**:
- 0-1,000 scans: $0.50/scan
- 1,001-5,000 scans: $0.40/scan
- 5,001-10,000 scans: $0.30/scan
- 10,001+ scans: $0.20/scan

**Chat Questions**:
- 0-10,000 questions: $0.02/question
- 10,001-50,000 questions: $0.015/question
- 50,001+ questions: $0.01/question

**Document Analysis**:
- 0-1,000 documents: $0.25/document
- 1,001-5,000 documents: $0.20/document
- 5,001+ documents: $0.15/document

**Example Enterprise Pricing**:

For an organization with:
- 50 AWS accounts
- 2,000 scans/month
- 20,000 questions/month
- 500 documents/month

```
Base Price (negotiated):           $2,500.00/month

Usage:
  Scans (2,000 × $0.50):            $1,000.00
  Questions (10,000 × $0.02):         $200.00
  Questions (10,000 × $0.015):        $150.00
  Documents (500 × $0.25):            $125.00
────────────────────────────────────────────
Total:                             $3,975.00/month

Annual Contract (paid upfront):   $45,000.00/year
  (Saves $2,700 vs monthly billing - 6% discount)
```

**Enterprise Account Limits**:
```json
{
  "aws_accounts": "unlimited",
  "users": "unlimited",
  "custom_rules": "unlimited",
  "webhooks": "unlimited",
  "api_rate_limit": "priority (no limit)",
  "data_retention_days": "custom (730+ days)",
  "scan_frequency": "real-time",
  "sso_providers": "unlimited",
  "regions": "multi-region",
  "dedicated_support": true,
  "custom_frameworks": true
}
```

**Enterprise Add-Ons** (Optional):
- **Professional Services**: Custom scanner development, migration assistance
- **Custom Training**: On-site workshops, certification programs
- **Managed Service**: We run scans and provide reports for you
- **White-Label**: Rebrand for MSPs and resellers

## Usage Metering Details

### How Usage is Measured

**Security Scans**:
- **Definition**: A complete security analysis of one AWS account across all enabled services
- **What Counts**:
  - Full account scan (all services)
  - Scheduled scans
  - Manual scans
  - API-triggered scans
- **What Doesn't Count**:
  - Re-scanning same account within 1 hour (deduplication)
  - Failed scans (error before completion)
  - Health checks and status queries

**Chat Questions**:
- **Definition**: A natural language question submitted to the GraphRAG query engine
- **What Counts**:
  - Questions typed in chat interface
  - API-submitted questions
  - Follow-up questions in same conversation
- **What Doesn't Count**:
  - Auto-complete suggestions
  - Clicking suggested questions (counted as 1 question)
  - System-generated insights

**Document Analysis**:
- **Definition**: Upload and analysis of architecture diagrams, policy docs, or configurations
- **What Counts**:
  - PDF uploads
  - Word document uploads
  - Text file analysis
  - CloudFormation/Terraform template analysis
- **What Doesn't Count**:
  - Re-analysis of same document (cached results)
  - Document downloads
  - Viewing analyzed documents

### Metering Reporting

**Real-Time Tracking**:
- View current usage in dashboard
- Meter updates within 1 minute
- Set usage alerts and budgets

**AWS Marketplace Integration**:
- Usage reported hourly to AWS Marketplace
- Billed monthly through your AWS bill
- Consolidated billing with AWS services

**Usage Dashboard**:
```json
{
  "current_month": {
    "scans": {
      "count": 156,
      "cost": "$78.00",
      "trend": "+12% vs last month"
    },
    "questions": {
      "count": 2340,
      "cost": "$46.80",
      "trend": "+5% vs last month"
    },
    "documents": {
      "count": 45,
      "cost": "$11.25",
      "trend": "-8% vs last month"
    },
    "total_usage_cost": "$136.05",
    "base_subscription": "$500.00",
    "estimated_monthly_total": "$636.05"
  }
}
```

## Billing & Payment

### AWS Marketplace Billing
- All payments processed through AWS Marketplace
- Usage charges appear on your AWS bill
- Pay with existing AWS payment method
- Consolidated billing for AWS Organizations
- Invoice available in AWS Billing Console

### Billing Cycle
- Base subscription: Charged on 1st of month
- Usage charges: Metered hourly, billed monthly
- Pro-rated charges for mid-month upgrades
- No pro-rating for downgrades (effective next month)

### Payment Terms
- **Monthly**: Charged monthly, pay-as-you-go
- **Annual**: Paid upfront, discount applied
- **Enterprise**: Custom terms (quarterly/annual)

### Invoicing
- PDF invoice available in Cloud Optimizer dashboard
- Detailed usage breakdown by dimension
- Account-level usage attribution (Enterprise tier)
- Cost allocation tags supported

## Tier Upgrade & Downgrade

### Upgrading

**Trial → Professional**:
- Immediate upgrade available in-app
- Subscribe via AWS Marketplace
- Data and configuration preserved
- No downtime

**Professional → Enterprise**:
- Contact sales for custom quote
- Migration assistance included
- SSO setup and configuration
- Dedicated onboarding

### Downgrading

**Professional → Trial**:
- Not available (subscribe to pause instead)

**Enterprise → Professional**:
- 30-day notice required
- Feature limitations take effect next billing cycle
- Data migration assistance
- SSO disabled

### Pausing Subscription

**Professional & Enterprise**:
- Pause subscription for up to 3 months
- Pay $100/month retention fee
- Data preserved, no new scans
- Reactivate anytime with same configuration

## Frequently Asked Questions

### General

**Q: What happens when my trial expires?**
A: You'll have read-only access to your data for 30 days. To continue scanning, subscribe to Professional or Enterprise tier.

**Q: Can I extend my trial?**
A: Yes, one-time 7-day extension available. Request via in-app banner or email support@cloudoptimizer.io.

**Q: What payment methods are accepted?**
A: All payments processed through AWS Marketplace. Use your existing AWS payment method (credit card, bank transfer, AWS credits).

**Q: Is there a setup fee?**
A: No setup fees for Professional tier. Enterprise tier may include onboarding services based on custom quote.

**Q: Can I cancel anytime?**
A: Yes, monthly subscriptions can be cancelled anytime with no penalty. Annual subscriptions are non-refundable but can be paused.

### Usage & Billing

**Q: How do I control costs?**
A: Set usage budgets and alerts in the dashboard. Configure scan schedules to control scan frequency. Professional tier includes cost forecasting.

**Q: What if I exceed my expected usage?**
A: Usage is unlimited and metered. You'll only pay for actual usage with no overage penalties. Set budget alerts to monitor spending.

**Q: Are there discounts for high volume?**
A: Enterprise tier includes volume discounts. Contact sales for custom pricing based on expected usage.

**Q: Do unused scans roll over?**
A: Trial tier has fixed limits. Professional/Enterprise are usage-based with no rollover (pay only for actual usage).

**Q: Can I get a refund?**
A: Monthly subscriptions: Refund available if cancelled within 7 days of first charge. Annual subscriptions: Non-refundable, but can be paused.

### Features

**Q: What compliance frameworks are included?**
A: All tiers include SOC2, ISO 27001, NIST 800-53, PCI-DSS, and HIPAA frameworks. Enterprise tier can create custom frameworks.

**Q: What's the difference between Professional and Enterprise support?**
A: Professional: Email support, 24-hour response, business hours. Enterprise: Dedicated engineer, phone + email, 4-hour response, 24/7 availability.

**Q: Can I add users mid-month?**
A: Professional tier limited to 5 users (included in base price). Enterprise tier has unlimited users.

**Q: What AWS services are scanned?**
A: All tiers scan 15+ AWS services: Lambda, API Gateway, S3, CloudFront, RDS, EC2, IAM, Secrets Manager, CloudWatch, VPC, ECS/EKS, DynamoDB, SNS/SQS, CloudTrail, KMS.

### Technical

**Q: Where is my data stored?**
A: All data stored in your AWS account in your PostgreSQL database. Cloud Optimizer is deployed in your AWS environment.

**Q: What IAM permissions are required?**
A: Read-only SecurityAudit managed policy. No write permissions required. Enterprise tier can use custom IAM policies.

**Q: Can I run Cloud Optimizer in a private VPC?**
A: Yes, deploy in private subnet. Only requires outbound HTTPS to AWS Marketplace for license validation.

**Q: What's the API rate limit?**
A: Professional: 100 requests/minute. Enterprise: No rate limit (priority queue).

## Contact Sales

Ready to upgrade or have questions about pricing?

**Email**: sales@cloudoptimizer.io
**Phone**: +1 (555) 123-4567
**Schedule Demo**: https://cloudoptimizer.io/demo
**Enterprise Quote**: https://cloudoptimizer.io/enterprise

---

**Pricing subject to change.** Current as of December 2025.

For the most up-to-date pricing, visit the [AWS Marketplace listing](https://aws.amazon.com/marketplace/pp/cloud-optimizer).
