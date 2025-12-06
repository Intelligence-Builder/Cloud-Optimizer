# AWS Secrets Manager Architecture - Issue #152

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AWS Secrets Manager Stack                         │
│                     (cloud-optimizer-secrets-manager)                    │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           Secrets (Encrypted)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Database Credentials Secret                                     │   │
│  │  cloud-optimizer/{env}/database/credentials                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐  │   │
│  │  │  {                                                          │  │   │
│  │  │    "username": "cloudguardian",                            │  │   │
│  │  │    "password": "auto-generated-32-char",                   │  │   │
│  │  │    "host": "rds-endpoint.region.rds.amazonaws.com",        │  │   │
│  │  │    "port": 5432,                                           │  │   │
│  │  │    "dbname": "cloudguardian",                              │  │   │
│  │  │    "engine": "postgres"                                    │  │   │
│  │  │  }                                                          │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  │  Rotation: Every 30 days (configurable 1-365)                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  API Keys Secret                                                 │   │
│  │  cloud-optimizer/{env}/api/keys                                  │   │
│  │  ┌────────────────────────────────────────────────────────────┐  │   │
│  │  │  {                                                          │  │   │
│  │  │    "jwt_secret_key": "...",                                │  │   │
│  │  │    "aws_access_key_id": "...",                             │  │   │
│  │  │    "aws_secret_access_key": "...",                         │  │   │
│  │  │    "external_api_keys": {}                                 │  │   │
│  │  │  }                                                          │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  │  Rotation: Manual                                                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Integration Credentials Secret                                  │   │
│  │  cloud-optimizer/{env}/integrations/credentials                  │   │
│  │  ┌────────────────────────────────────────────────────────────┐  │   │
│  │  │  {                                                          │  │   │
│  │  │    "slack_webhook_url": "...",                             │  │   │
│  │  │    "pagerduty_api_key": "...",                             │  │   │
│  │  │    "datadog_api_key": "...",                               │  │   │
│  │  │    "github_token": "..."                                   │  │   │
│  │  │  }                                                          │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  │  Rotation: Manual                                                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Encrypted with
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           KMS Encryption Key                             │
├─────────────────────────────────────────────────────────────────────────┤
│  Key ID: SecretsKMSKey                                                   │
│  Alias: alias/cloud-optimizer-{env}-secrets                              │
│  Features:                                                               │
│    ✓ Automatic key rotation enabled                                     │
│    ✓ Service access for Secrets Manager                                 │
│    ✓ Service access for CloudWatch Logs                                 │
│    ✓ Root account permissions                                           │
└─────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                    Automatic Rotation Process                            │
└─────────────────────────────────────────────────────────────────────────┘

  Every 30 days (configurable)
           │
           ▼
  ┌─────────────────┐
  │ Rotation        │
  │ Schedule        │──────────────────┐
  │ Triggered       │                  │
  └─────────────────┘                  │
                                       │
                                       ▼
           ┌────────────────────────────────────────────┐
           │   Lambda Rotation Function                 │
           │   cloud-optimizer-{env}-db-rotation        │
           ├────────────────────────────────────────────┤
           │   Runtime: Python 3.11                     │
           │   Memory: 256 MB                           │
           │   Timeout: 30 seconds                      │
           │   Dependencies: psycopg2 (Lambda Layer)    │
           └────────────────────────────────────────────┘
                              │
                              │ Four-Step Process
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       Rotation Steps                                     │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Step 1: createSecret                                                    │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │  • Generate new 32-character password                   │            │
│  │  • Use Secrets Manager GetRandomPassword API           │            │
│  │  • Store as AWSPENDING version                          │            │
│  │  • Exclude problematic characters: " @ / \ '            │            │
│  └─────────────────────────────────────────────────────────┘            │
│                          ↓                                               │
│  Step 2: setSecret                                                       │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │  • Connect to PostgreSQL using AWSCURRENT credentials   │            │
│  │  • Execute: ALTER USER cloudguardian                    │            │
│  │             WITH PASSWORD 'new_password'                │            │
│  │  • Commit the transaction                               │            │
│  └─────────────────────────────────────────────────────────┘            │
│                          ↓                                               │
│  Step 3: testSecret                                                      │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │  • Connect using AWSPENDING credentials                 │            │
│  │  • Execute: SELECT 1                                    │            │
│  │  • Verify connection succeeds                           │            │
│  │  • Close connection                                     │            │
│  └─────────────────────────────────────────────────────────┘            │
│                          ↓                                               │
│  Step 4: finishSecret                                                    │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │  • Promote AWSPENDING to AWSCURRENT                     │            │
│  │  • Demote old AWSCURRENT to AWSPREVIOUS                │            │
│  │  • Rotation complete                                    │            │
│  └─────────────────────────────────────────────────────────┘            │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                         Network Architecture                             │
│                         (VPC Mode - Optional)                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                              VPC                                         │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │  Private Subnet 1              Private Subnet 2                │     │
│  │  ┌───────────────────┐         ┌───────────────────┐           │     │
│  │  │  Lambda Function  │         │  Lambda Function  │           │     │
│  │  │  (Rotation)       │         │  (Rotation)       │           │     │
│  │  │                   │         │                   │           │     │
│  │  │  Security Group:  │         │  Security Group:  │           │     │
│  │  │  - Egress: 5432   │         │  - Egress: 5432   │           │     │
│  │  │    to DB SG       │         │    to DB SG       │           │     │
│  │  │  - Egress: 443    │         │  - Egress: 443    │           │     │
│  │  │    to 0.0.0.0/0   │         │    to 0.0.0.0/0   │           │     │
│  │  └─────────┬─────────┘         └─────────┬─────────┘           │     │
│  │            │                              │                     │     │
│  │            │                              │                     │     │
│  │            └──────────────┬───────────────┘                     │     │
│  │                           │                                     │     │
│  └───────────────────────────┼─────────────────────────────────────┘     │
│                              │                                           │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │  Database Subnet                                               │     │
│  │  ┌──────────────────────────────────────────────────────┐      │     │
│  │  │  RDS PostgreSQL Instance                             │      │     │
│  │  │  cloudguardian database                              │      │     │
│  │  │                                                       │      │     │
│  │  │  Security Group:                                     │      │     │
│  │  │  - Ingress: 5432 from Lambda SG                      │      │     │
│  │  └──────────────────────────────────────────────────────┘      │     │
│  └────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │  NAT Gateway (for Lambda to reach AWS APIs)                    │     │
│  │  - Secrets Manager API                                          │     │
│  │  - KMS API                                                      │     │
│  └────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                      Monitoring & Logging                                │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  CloudWatch Logs                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Log Group: /aws/lambda/cloud-optimizer-{env}-db-rotation         │  │
│  │  Retention: 30 days (dev/staging) / 90 days (production)          │  │
│  │  ┌──────────────────────────────────────────────────────────────┐ │  │
│  │  │  2025-12-06 10:00:00 INFO createSecret: Created new secret   │ │  │
│  │  │  2025-12-06 10:00:05 INFO setSecret: Updated password in DB  │ │  │
│  │  │  2025-12-06 10:00:08 INFO testSecret: Validated credentials  │ │  │
│  │  │  2025-12-06 10:00:10 INFO finishSecret: Rotation complete    │ │  │
│  │  └──────────────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Error metrics
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  CloudWatch Alarm                                                        │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Alarm: cloud-optimizer-{env}-rotation-failure                     │  │
│  │  Metric: Lambda Errors                                             │  │
│  │  Threshold: >= 1 error in 5 minutes                                │  │
│  │  Action: Send SNS notification (optional)                          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                     Application Integration                              │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  Cloud Optimizer Application                                             │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  SecretsManagerClient (with caching)                               │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  Cache TTL: 5 minutes                                        │  │  │
│  │  │  • Reduces API calls                                         │  │  │
│  │  │  • Provides fallback during rotation                        │  │  │
│  │  │  • Handles ResourceNotFoundException                        │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                              │                                           │
│                              │ GetSecretValue API calls                  │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  AWS Secrets Manager                                               │  │
│  │  • Returns AWSCURRENT version                                      │  │
│  │  • Handles version transitions automatically                       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                          IAM Permissions                                 │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  Rotation Lambda IAM Role                                                │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Managed Policies:                                                 │  │
│  │  • AWSLambdaBasicExecutionRole                                     │  │
│  │  • AWSLambdaVPCAccessExecutionRole (if VPC enabled)                │  │
│  │                                                                     │  │
│  │  Custom Policies:                                                  │  │
│  │  • secretsmanager:DescribeSecret                                   │  │
│  │  • secretsmanager:GetSecretValue                                   │  │
│  │  • secretsmanager:PutSecretValue                                   │  │
│  │  • secretsmanager:UpdateSecretVersionStage                         │  │
│  │  • secretsmanager:GetRandomPassword                                │  │
│  │  • kms:Decrypt, kms:Encrypt, kms:GenerateDataKey                   │  │
│  │  • rds:DescribeDBInstances, rds:DescribeDBClusters                │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  Application IAM Role (read-only)                                        │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Custom Policies:                                                  │  │
│  │  • secretsmanager:GetSecretValue (specific secrets only)           │  │
│  │  • kms:Decrypt (via Secrets Manager service)                       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                        Security Features                                 │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  Encryption                                                              │
│  • At Rest: KMS encryption with automatic key rotation                  │
│  • In Transit: TLS 1.2+ for all AWS API calls                           │
│                                                                          │
│  Access Control                                                          │
│  • IAM role-based access (no IAM users)                                 │
│  • Resource policies on secrets (prevent deletion from other accounts)  │
│  • KMS key policies (service-level access only)                         │
│  • VPC security groups (network isolation)                              │
│                                                                          │
│  Audit & Compliance                                                      │
│  • CloudWatch Logs (all rotation events)                                │
│  • CloudTrail integration (API call auditing)                           │
│  • Secret version history (AWSCURRENT, AWSPENDING, AWSPREVIOUS)         │
│  • 30-day rotation (meets PCI-DSS, SOC2, HIPAA requirements)            │
│                                                                          │
│  Password Security                                                       │
│  • 32-character length                                                  │
│  • Mixed case, numbers, special characters                              │
│  • Exclude ambiguous characters: " @ / \ '                              │
│  • Cryptographically secure random generation                           │
└──────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                      Stack Outputs                                       │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  Exported Values (for cross-stack references)                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  • DatabaseCredentialsSecretArn                                    │  │
│  │  • DatabaseCredentialsSecretName                                   │  │
│  │  • APIKeysSecretArn                                                │  │
│  │  • APIKeysSecretName                                               │  │
│  │  • IntegrationSecretsArn                                           │  │
│  │  • IntegrationSecretsName                                          │  │
│  │  • SecretsKMSKeyId                                                 │  │
│  │  • SecretsKMSKeyArn                                                │  │
│  │  • RotationLambdaArn                                               │  │
│  │  • RotationScheduleDays                                            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                      Cost Breakdown                                      │
└─────────────────────────────────────────────────────────────────────────┘

Monthly Costs (per environment):
  • Secrets Manager: $0.40 × 3 secrets = $1.20
  • KMS Key: $1.00
  • Lambda invocations: ~$0.01 (1 rotation/month, minimal compute)
  • CloudWatch Logs: ~$0.50 (30-90 day retention)
  ────────────────────────────────────────
  Total: ~$2.71/month

Annual Cost (production only): ~$32.52/year
Annual Cost (3 environments): ~$97.56/year
