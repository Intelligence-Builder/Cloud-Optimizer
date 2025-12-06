# Cloud Optimizer - End User Guide

## AWS Marketplace Quick Start

Welcome to Cloud Optimizer! This guide will help you deploy and configure Cloud Optimizer from AWS Marketplace.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Subscription & Deployment](#subscription--deployment)
3. [Initial Configuration](#initial-configuration)
4. [Running Your First Scan](#running-your-first-scan)
5. [Understanding Results](#understanding-results)
6. [Using Natural Language Queries](#using-natural-language-queries)
7. [Compliance Reports](#compliance-reports)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Support](#support)

---

## Prerequisites

Before deploying Cloud Optimizer, ensure you have:

### AWS Requirements
- **AWS Account** with admin access
- **AWS Region**: Any commercial AWS region (us-east-1 recommended)
- **VPC** with private subnets (recommended for production)
- **RDS PostgreSQL** 15+ database instance
- **ECS Cluster** or **EC2 instance** for container deployment

### Minimum Infrastructure
```yaml
Database:
  Type: RDS PostgreSQL
  Version: 15.0 or higher
  Instance Class: db.t3.medium (minimum)
  Storage: 100 GB SSD
  Multi-AZ: Recommended for production
  Backup: Automated daily backups enabled

Compute:
  Option 1 (ECS):
    Task vCPU: 2
    Task Memory: 4 GB
    Service: Fargate or EC2 launch type

  Option 2 (EC2):
    Instance Type: t3.large (minimum)
    OS: Amazon Linux 2023 or Ubuntu 22.04
    Storage: 50 GB GP3
```

### IAM Permissions

Create an IAM role with the following permissions:

**For Cloud Optimizer Container**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "aws-marketplace:RegisterUsage",
        "aws-marketplace:MeterUsage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:Get*",
        "iam:List*",
        "ec2:Describe*",
        "s3:GetBucket*",
        "s3:GetObject*",
        "s3:ListBucket",
        "lambda:Get*",
        "lambda:List*",
        "apigateway:GET",
        "cloudfront:Get*",
        "cloudfront:List*",
        "rds:Describe*",
        "cloudwatch:Describe*",
        "cloudwatch:Get*",
        "cloudwatch:List*",
        "logs:Describe*",
        "logs:Get*",
        "secretsmanager:List*",
        "secretsmanager:Describe*",
        "kms:List*",
        "kms:Describe*",
        "cloudtrail:Get*",
        "cloudtrail:List*",
        "sns:Get*",
        "sns:List*",
        "sqs:Get*",
        "sqs:List*",
        "dynamodb:Describe*",
        "dynamodb:List*",
        "ecs:Describe*",
        "ecs:List*",
        "eks:Describe*",
        "eks:List*"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note**: These are **read-only** permissions. Cloud Optimizer never modifies your AWS resources.

---

## Subscription & Deployment

### Step 1: Subscribe via AWS Marketplace

1. Navigate to [AWS Marketplace](https://aws.amazon.com/marketplace)
2. Search for "Cloud Optimizer"
3. Click **Continue to Subscribe**
4. Review pricing and EULA
5. Click **Accept Terms**
6. Wait for subscription confirmation (typically < 5 minutes)

### Step 2: Choose Deployment Method

AWS Marketplace provides container image URL. Choose your deployment:

#### Option A: Deploy to ECS Fargate (Recommended)

**Create ECS Task Definition**:

```json
{
  "family": "cloud-optimizer",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/CloudOptimizerTaskRole",
  "containerDefinitions": [
    {
      "name": "cloud-optimizer",
      "image": "709825985650.dkr.ecr.us-east-1.amazonaws.com/aws-marketplace/cloud-optimizer:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://cloudguardian:PASSWORD@your-rds.rds.amazonaws.com:5432/cloudguardian"
        },
        {
          "name": "AWS_REGION",
          "value": "us-east-1"
        },
        {
          "name": "MARKETPLACE_ENABLED",
          "value": "true"
        },
        {
          "name": "MARKETPLACE_PRODUCT_CODE",
          "value": "YOUR_PRODUCT_CODE"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/cloud-optimizer",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**Create ECS Service**:

```bash
aws ecs create-service \
  --cluster cloud-optimizer-cluster \
  --service-name cloud-optimizer \
  --task-definition cloud-optimizer:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=cloud-optimizer,containerPort=8000"
```

#### Option B: Deploy to EC2

**Launch EC2 instance and run container**:

```bash
# Install Docker
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Login to AWS Marketplace ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  709825985650.dkr.ecr.us-east-1.amazonaws.com

# Pull and run Cloud Optimizer
docker run -d \
  --name cloud-optimizer \
  --restart unless-stopped \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://cloudguardian:PASSWORD@your-rds:5432/cloudguardian" \
  -e AWS_REGION="us-east-1" \
  -e MARKETPLACE_ENABLED="true" \
  -e MARKETPLACE_PRODUCT_CODE="YOUR_PRODUCT_CODE" \
  709825985650.dkr.ecr.us-east-1.amazonaws.com/aws-marketplace/cloud-optimizer:latest

# Check container logs
docker logs -f cloud-optimizer
```

### Step 3: Configure Load Balancer (Production)

**Create Application Load Balancer**:

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name cloud-optimizer-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx \
  --scheme internet-facing

# Create target group
aws elbv2 create-target-group \
  --name cloud-optimizer-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxx \
  --health-check-path /health \
  --health-check-interval-seconds 30

# Create HTTPS listener (recommended)
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

### Step 4: Configure DNS

Point your domain to the ALB:

```
cloud-optimizer.yourcompany.com  →  ALB DNS Name (CNAME or ALIAS)
```

---

## Initial Configuration

### Step 1: Access Dashboard

Navigate to your Cloud Optimizer URL:
```
https://cloud-optimizer.yourcompany.com
```

Or if testing without ALB:
```
http://ec2-instance-public-ip:8000
```

### Step 2: Complete Setup Wizard

**Welcome Screen**:
1. Review trial information (14 days, 50 scans, 500 questions, 20 documents)
2. Click **Get Started**

**Organization Setup**:
1. Enter organization name
2. Set primary contact email
3. Choose timezone and region preferences
4. Click **Next**

**Admin User Creation**:
1. Enter admin email
2. Set strong password (12+ characters)
3. Enable MFA (recommended)
4. Click **Create Admin Account**

**AWS Account Connection**:
1. Choose authentication method:
   - **IAM Role** (recommended): Assumes role via instance profile
   - **Access Keys**: Manual credential entry (not recommended)
2. For IAM Role:
   - Ensure ECS task or EC2 instance has CloudOptimizerTaskRole attached
   - Click **Detect Credentials**
   - Verify detected AWS account ID
3. Enter account nickname (e.g., "Production", "Staging")
4. Click **Connect Account**

### Step 3: Configure Scan Settings

**Default Scan Configuration**:

```yaml
Scan Frequency: Daily at 2:00 AM UTC
Services to Scan: All (15+ services)
Compliance Frameworks: SOC2, ISO 27001, NIST 800-53
Alert Notifications: Email (admin@yourcompany.com)
Scan Timeout: 30 minutes
Concurrent Scans: 5
```

**Customize Settings**:
- Navigate to **Settings → Scan Configuration**
- Adjust scan schedule (hourly, daily, weekly)
- Enable/disable specific AWS services
- Configure notification channels (Slack, email, SNS)

---

## Running Your First Scan

### Quick Scan (5-10 minutes)

1. Click **New Scan** in dashboard
2. Select AWS account
3. Choose **Quick Scan** preset:
   - Scans: IAM, S3, Lambda, RDS, Security Groups
   - Estimated time: 5 minutes
4. Click **Start Scan**

Watch real-time progress:
```
[████████░░░░] 67% - Scanning Lambda functions...
Found 3 vulnerabilities in 12 functions
```

### Full Account Scan (20-30 minutes)

1. Click **New Scan** in dashboard
2. Select AWS account
3. Choose **Full Scan** preset:
   - Scans all 15+ AWS services
   - Estimated time: 20-30 minutes
4. Click **Start Scan**

### Scheduled Scans

**Enable Daily Scans**:
1. Navigate to **Settings → Scheduled Scans**
2. Click **Create Schedule**
3. Configure:
   ```yaml
   Name: Daily Production Scan
   Account: Production (123456789012)
   Frequency: Daily at 2:00 AM UTC
   Services: All
   Notifications: #security-alerts Slack channel
   ```
4. Click **Save Schedule**

---

## Understanding Results

### Security Dashboard

**Overview Widgets**:
```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│   Risk Score: 72    │  Open Findings: 47  │ Critical Issues: 3  │
│   ⚠️  Medium Risk   │                     │                     │
└─────────────────────┴─────────────────────┴─────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              Findings by Severity                               │
│  Critical:  ▓▓▓ 3                                               │
│  High:      ▓▓▓▓▓▓▓▓▓▓▓▓▓ 13                                    │
│  Medium:    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 19                              │
│  Low:       ▓▓▓▓▓▓▓▓▓▓ 10                                       │
│  Info:      ▓▓ 2                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Finding Details

Click any finding to view:

**Example: Public S3 Bucket**
```yaml
Finding ID: FIND-2025-001234
Severity: CRITICAL
Service: S3
Resource: s3://customer-data-backup

Issue:
  S3 bucket is publicly accessible with read permissions.
  This bucket contains 10,000+ objects and may include sensitive data.

Risk:
  - Data exposure to unauthorized users
  - Potential data breach
  - Compliance violations (SOC2, GDPR)

Evidence:
  - Bucket Policy: Principal: "*"
  - Block Public Access: Disabled
  - Objects: 10,247 objects (125 GB)

Remediation:
  1. Enable S3 Block Public Access:
     aws s3api put-public-access-block \
       --bucket customer-data-backup \
       --public-access-block-configuration \
       "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

  2. Review and remove bucket policy public access:
     aws s3api delete-bucket-policy --bucket customer-data-backup

  3. Verify access is restricted:
     aws s3api get-public-access-block --bucket customer-data-backup

References:
  - AWS S3 Security Best Practices
  - CIS AWS Foundations Benchmark 2.1.5
  - SOC2 CC6.6 (Logical Access)
```

### Compliance View

Navigate to **Compliance → SOC2**:

```
┌─────────────────────────────────────────────────────────────────┐
│              SOC2 Trust Service Criteria                        │
├─────────────────────────────────────────────────┬───────────────┤
│ Control Category                                │ Compliance    │
├─────────────────────────────────────────────────┼───────────────┤
│ CC6.1 - Logical Access Controls                │ ✅ 95% (19/20)│
│ CC6.2 - Authentication                          │ ⚠️  80% (16/20)│
│ CC6.3 - Authorization                           │ ✅ 100% (12/12)│
│ CC6.6 - Encryption                              │ ❌ 65% (13/20)│
│ CC6.7 - Key Management                          │ ✅ 90% (9/10) │
├─────────────────────────────────────────────────┼───────────────┤
│ Overall SOC2 Compliance                         │ ⚠️  86%       │
└─────────────────────────────────────────────────┴───────────────┘
```

Click any control to see:
- Specific requirements
- Mapped AWS resources
- Pass/fail status
- Remediation guidance
- Audit evidence

---

## Using Natural Language Queries

### Chat Interface

Click **Chat** in navigation to access GraphRAG-powered queries.

**Example Queries**:

1. **Broad Security Questions**:
   ```
   You: "Show me all publicly accessible resources"

   Cloud Optimizer: I found 7 publicly accessible resources:

   S3 Buckets (3):
   - s3://customer-data-backup (10,247 objects)
   - s3://marketing-assets (523 objects)
   - s3://public-website (89 objects)

   RDS Instances (2):
   - prod-db-1.xxxxx.us-east-1.rds.amazonaws.com
   - staging-db.xxxxx.us-east-1.rds.amazonaws.com

   Lambda Functions (2):
   - public-api-handler (URL: https://xxxxx.lambda-url.us-east-1.on.aws)
   - webhook-receiver (URL: https://xxxxx.lambda-url.us-east-1.on.aws)

   Recommendation: Review each resource to determine if public access is required.
   ```

2. **Compliance-Specific**:
   ```
   You: "What do I need to fix for SOC2 compliance?"

   Cloud Optimizer: You have 8 SOC2 compliance gaps:

   Critical (3):
   1. CC6.6: S3 bucket 'customer-data-backup' lacks encryption
   2. CC6.2: IAM users without MFA: admin, developer-1, developer-2
   3. CC6.7: KMS key rotation not enabled for 'customer-data-key'

   High (5):
   4. CC6.1: Security group sg-xxxxx allows 0.0.0.0/0 on port 22
   5. CC6.1: RDS instance publicly accessible
   ...

   Would you like detailed remediation steps for any of these?
   ```

3. **Relationship Queries**:
   ```
   You: "What resources can access my customer database?"

   Cloud Optimizer: Analysis of database access paths:

   Direct Access:
   - Lambda: customer-api (IAM role: CustomerAPIRole)
   - Lambda: data-processor (IAM role: DataProcessorRole)
   - EC2: app-server-1 (Security group: sg-app)

   Security Groups:
   - sg-app: Allows inbound 5432 from sg-lambda
   - sg-lambda: Attached to Lambda functions

   IAM Policies:
   - CustomerAPIRole: rds:Connect, rds:DescribeDBInstances
   - DataProcessorRole: rds:Connect, rds:ExecuteStatement

   Recommendations:
   - Enable RDS IAM authentication
   - Restrict security group to specific CIDR ranges
   - Enable RDS audit logging
   ```

### Query Tips

**Best Practices**:
- Be specific: "Show Lambda functions with secrets in environment variables"
- Use AWS service names: "List all unencrypted RDS instances"
- Ask for remediation: "How do I fix public S3 buckets?"
- Compare states: "What changed in the last 24 hours?"

**Metering**: Each question counts toward your usage limit (500 in trial, unlimited in paid tiers).

---

## Compliance Reports

### Generate PDF Report

1. Navigate to **Compliance → Reports**
2. Click **Generate Report**
3. Configure report:
   ```yaml
   Report Type: SOC2 Audit Report
   Time Period: Last 30 days
   Include:
     - Executive Summary
     - Control Status
     - Evidence Screenshots
     - Remediation Timeline
   Format: PDF
   ```
4. Click **Generate**
5. Download PDF (typically ready in 30-60 seconds)

### Scheduled Reports

**Email Weekly Compliance Summary**:
1. Navigate to **Settings → Reports**
2. Click **Create Schedule**
3. Configure:
   ```yaml
   Name: Weekly SOC2 Summary
   Frequency: Weekly on Monday at 9:00 AM
   Recipients: security@yourcompany.com, ciso@yourcompany.com
   Report Type: Compliance Summary
   Frameworks: SOC2, ISO 27001
   Format: PDF
   ```
4. Click **Save Schedule**

### Export Data

**Export to CSV**:
- Navigate to **Findings → Export**
- Choose format: CSV, JSON, or Excel
- Select date range
- Click **Export**

**API Export** (Programmatic):
```bash
curl -X GET \
  https://cloud-optimizer.yourcompany.com/api/v1/findings \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Accept: application/json" \
  > findings.json
```

---

## Best Practices

### Security Scanning

**Scan Frequency**:
- **Production accounts**: Daily scans
- **Development accounts**: Weekly scans
- **Critical changes**: On-demand scans after deployments

**Alert Configuration**:
```yaml
Critical Findings: Immediate Slack + Email + PagerDuty
High Findings: Slack notification within 1 hour
Medium Findings: Daily summary email
Low/Info: Weekly report
```

**Scan Optimization**:
- Use region-specific scans if you only use specific regions
- Exclude non-production accounts from daily scans
- Configure scan windows during low-usage hours

### Cost Management

**Monitor Usage**:
1. Navigate to **Settings → Usage & Billing**
2. View current month usage:
   ```
   Scans: 156 / unlimited ($78.00)
   Questions: 2,340 / unlimited ($46.80)
   Documents: 45 / unlimited ($11.25)

   Total Usage Cost: $136.05
   Base Subscription: $500.00
   Estimated Total: $636.05
   ```
3. Set budget alerts:
   - Warning at 80% of budget
   - Critical at 100% of budget

**Reduce Costs**:
- Use scheduled scans instead of manual scans
- Cache frequently-asked chat questions
- Batch document uploads

### Compliance Automation

**Continuous Compliance**:
1. Enable daily scans
2. Configure compliance frameworks
3. Set up automated remediation (Enterprise tier)
4. Schedule weekly compliance reports

**Audit Preparation**:
- Generate historical compliance reports
- Export evidence screenshots
- Document remediation timelines
- Maintain audit trail logs

---

## Troubleshooting

### Container Won't Start

**Check logs**:
```bash
# ECS
aws logs tail /ecs/cloud-optimizer --follow

# EC2/Docker
docker logs cloud-optimizer
```

**Common issues**:

1. **Database connection failed**:
   ```
   Error: could not connect to server: Connection refused
   ```
   **Fix**:
   - Verify DATABASE_URL is correct
   - Check RDS security group allows inbound 5432 from container
   - Verify RDS is in same VPC or VPC peering configured

2. **License validation failed**:
   ```
   Error: AWS Marketplace license validation failed
   ```
   **Fix**:
   - Verify MARKETPLACE_PRODUCT_CODE is correct
   - Ensure ECS task role has `aws-marketplace:RegisterUsage` permission
   - Check AWS region matches subscription region

3. **Out of memory**:
   ```
   Error: Container killed (exit code 137)
   ```
   **Fix**:
   - Increase ECS task memory to 4096 MB minimum
   - For EC2, upgrade to t3.large or larger

### Scan Failures

**Symptom**: Scans fail with timeout or permission errors

**Diagnostics**:
1. Navigate to **Scans → Recent Scans**
2. Click failed scan
3. View error details

**Common errors**:

1. **AccessDenied for specific service**:
   ```
   Error: User is not authorized to perform: lambda:ListFunctions
   ```
   **Fix**: Add missing IAM permission to CloudOptimizerTaskRole

2. **Scan timeout**:
   ```
   Error: Scan exceeded 30 minute timeout
   ```
   **Fix**:
   - Increase timeout in Settings
   - Reduce number of services scanned
   - Check AWS API rate limiting

### Performance Issues

**Dashboard slow to load**:
1. Check database performance:
   ```sql
   SELECT * FROM pg_stat_activity
   WHERE state = 'active';
   ```
2. Upgrade RDS instance class if CPU > 80%
3. Enable PostgreSQL query caching

**Chat queries slow**:
1. Verify GraphRAG indexes are up to date
2. Check database connection pool settings
3. Contact support for index optimization

---

## Support

### Getting Help

**Documentation**:
- User Guide: https://docs.cloudoptimizer.io
- API Reference: https://api.cloudoptimizer.io/docs
- Video Tutorials: https://youtube.com/@cloudoptimizer

**Community Support** (Free Trial):
- Slack: https://slack.cloudoptimizer.io
- GitHub Discussions: https://github.com/intelligence-builder/cloud-optimizer/discussions

**Email Support** (Professional Tier):
- support@cloudoptimizer.io
- Response SLA: 24 hours (business days)

**Dedicated Support** (Enterprise Tier):
- Private Slack channel
- Phone support: +1 (555) 123-4567
- Response SLA: 4 hours (24/7)

### Opening a Support Ticket

Include the following information:

```yaml
Subject: [CRITICAL/HIGH/MEDIUM] Brief description

Environment:
  - Cloud Optimizer Version: 2.1.0
  - AWS Region: us-east-1
  - Deployment: ECS Fargate
  - Database: RDS PostgreSQL 15.3

Issue Description:
  Detailed description of the problem

Steps to Reproduce:
  1. Navigate to...
  2. Click on...
  3. Error occurs...

Expected Behavior:
  What should happen

Actual Behavior:
  What actually happens

Logs:
  Attach relevant logs (sanitize sensitive data)

Screenshots:
  Attach if applicable
```

### Escalation Path

1. **Email Support**: support@cloudoptimizer.io
2. **No response in SLA**: Reply with "[ESCALATE]" in subject
3. **Critical production issue**: Call +1 (555) 123-4567 (Enterprise only)

---

## Additional Resources

**Product Updates**:
- Release Notes: https://cloudoptimizer.io/releases
- Blog: https://cloudoptimizer.io/blog
- Newsletter: Subscribe at https://cloudoptimizer.io/subscribe

**Training**:
- Webinars: https://cloudoptimizer.io/webinars
- Certification: https://academy.cloudoptimizer.io
- On-site Training: sales@cloudoptimizer.io (Enterprise)

**Integrations**:
- Slack: https://docs.cloudoptimizer.io/integrations/slack
- Jira: https://docs.cloudoptimizer.io/integrations/jira
- Splunk: https://docs.cloudoptimizer.io/integrations/splunk

---

**Cloud Optimizer End User Guide**
Version 1.0 - December 2025

For the latest version of this guide, visit: https://docs.cloudoptimizer.io/marketplace/quick-start

Copyright © 2025 Intelligence-Builder Inc. All rights reserved.
