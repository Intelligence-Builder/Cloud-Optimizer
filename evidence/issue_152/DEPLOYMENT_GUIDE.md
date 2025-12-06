# AWS Secrets Manager Deployment Guide - Issue #152

## Overview
This guide explains how to deploy the AWS Secrets Manager CloudFormation template for the Cloud Optimizer project, which provides automatic credential rotation for database passwords and secure storage for API keys and integration credentials.

## Template Location
`/Users/robertstanley/desktop/cloud-optimizer/cloudformation/secrets-manager.yaml`

## Validation Status
- **Template Validation**: PASSED
- **Validation Date**: 2025-12-06
- **AWS CLI Validation**: Successfully validated
- **Required Capabilities**: CAPABILITY_NAMED_IAM

## Components Deployed

### 1. Secrets Manager Secrets
- **Database Credentials**: `cloud-optimizer/{Environment}/database/credentials`
  - Automatic password generation (32 characters)
  - Rotation enabled (30 days default)
  - KMS encrypted

- **API Keys**: `cloud-optimizer/{Environment}/api/keys`
  - JWT secret key
  - AWS access keys
  - External API keys

- **Integration Credentials**: `cloud-optimizer/{Environment}/integrations/credentials`
  - Slack webhook URL
  - PagerDuty API key
  - Datadog API key
  - GitHub token

### 2. KMS Encryption
- Automatic key rotation enabled
- Service-level permissions for Secrets Manager and CloudWatch Logs
- Alias: `alias/cloud-optimizer-{Environment}-secrets`

### 3. Lambda Rotation Function
- Runtime: Python 3.11
- Memory: 256 MB
- Timeout: 30 seconds
- Four-step rotation process (createSecret, setSecret, testSecret, finishSecret)
- PostgreSQL support (MySQL/MariaDB framework ready)

### 4. Monitoring
- CloudWatch Log Group with 30-90 day retention
- CloudWatch Alarm for rotation failures
- Comprehensive logging in rotation Lambda

## Prerequisites

### Required for Basic Deployment (Non-VPC)
1. AWS CLI configured with appropriate permissions
2. IAM permissions to create:
   - Secrets Manager secrets
   - KMS keys
   - Lambda functions
   - IAM roles
   - CloudWatch resources

### Additional Requirements for VPC Deployment
1. VPC with private subnets
2. NAT Gateway configured in private subnets
3. Database security group that allows PostgreSQL connections
4. Subnet IDs where Lambda will run

### Database Requirements
1. PostgreSQL database instance running
2. Database user `cloudguardian` created
3. Database accessible from Lambda (if using VPC mode)

## Deployment Methods

### Method 1: AWS Console (Recommended for First-Time Deployment)

1. **Navigate to CloudFormation Console**
   ```
   AWS Console → CloudFormation → Create Stack
   ```

2. **Upload Template**
   - Choose "Upload a template file"
   - Select `cloudformation/secrets-manager.yaml`
   - Click "Next"

3. **Configure Stack Parameters**
   - **Stack name**: `cloud-optimizer-secrets-manager-{environment}`
   - **Environment**: `production`, `staging`, or `development`
   - **RotationSchedule**: `30` (days between rotations)
   - **DatabaseEngine**: `postgres` (default)
   - **VpcId**: Leave empty for non-VPC or provide VPC ID
   - **SubnetIds**: Leave empty for non-VPC or provide comma-separated subnet IDs
   - **DatabaseSecurityGroupId**: Leave empty for non-VPC or provide security group ID

4. **Configure Stack Options**
   - Add tags as needed:
     - Key: `Project`, Value: `CloudOptimizer`
     - Key: `ManagedBy`, Value: `CloudFormation`
   - Leave other options as default

5. **Review and Create**
   - Review all parameters
   - Check "I acknowledge that AWS CloudFormation might create IAM resources with custom names"
   - Click "Create stack"

6. **Monitor Deployment**
   - Watch the Events tab for progress
   - Deployment typically takes 3-5 minutes
   - Stack status should show `CREATE_COMPLETE`

### Method 2: AWS CLI (For Automation)

#### Non-VPC Deployment
```bash
aws cloudformation create-stack \
  --stack-name cloud-optimizer-secrets-manager-production \
  --template-body file://cloudformation/secrets-manager.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=production \
    ParameterKey=RotationSchedule,ParameterValue=30 \
    ParameterKey=DatabaseEngine,ParameterValue=postgres \
  --capabilities CAPABILITY_NAMED_IAM \
  --tags \
    Key=Project,Value=CloudOptimizer \
    Key=ManagedBy,Value=CloudFormation
```

#### VPC Deployment
```bash
aws cloudformation create-stack \
  --stack-name cloud-optimizer-secrets-manager-production \
  --template-body file://cloudformation/secrets-manager.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=production \
    ParameterKey=RotationSchedule,ParameterValue=30 \
    ParameterKey=DatabaseEngine,ParameterValue=postgres \
    ParameterKey=VpcId,ParameterValue=vpc-xxxxx \
    ParameterKey=SubnetIds,ParameterValue=subnet-xxxxx,subnet-yyyyy \
    ParameterKey=DatabaseSecurityGroupId,ParameterValue=sg-xxxxx \
  --capabilities CAPABILITY_NAMED_IAM \
  --tags \
    Key=Project,Value=CloudOptimizer \
    Key=ManagedBy,Value=CloudFormation
```

#### Monitor Stack Creation
```bash
aws cloudformation wait stack-create-complete \
  --stack-name cloud-optimizer-secrets-manager-production

aws cloudformation describe-stacks \
  --stack-name cloud-optimizer-secrets-manager-production \
  --query 'Stacks[0].StackStatus'
```

## Post-Deployment Configuration

### 1. Update Database Credentials Secret

The database credentials secret needs to be updated with actual connection details:

```bash
# Get current secret value
aws secretsmanager get-secret-value \
  --secret-id cloud-optimizer/production/database/credentials \
  --query SecretString --output text

# Update with actual database connection info
aws secretsmanager put-secret-value \
  --secret-id cloud-optimizer/production/database/credentials \
  --secret-string '{
    "username": "cloudguardian",
    "password": "GENERATED_PASSWORD_FROM_SECRET",
    "host": "your-rds-endpoint.region.rds.amazonaws.com",
    "port": 5432,
    "dbname": "cloudguardian",
    "engine": "postgres"
  }'
```

### 2. Update API Keys Secret

```bash
aws secretsmanager put-secret-value \
  --secret-id cloud-optimizer/production/api/keys \
  --secret-string '{
    "jwt_secret_key": "your-jwt-secret-key-here",
    "aws_access_key_id": "your-aws-access-key",
    "aws_secret_access_key": "your-aws-secret-key",
    "external_api_keys": {}
  }'
```

### 3. Update Integration Credentials Secret

```bash
aws secretsmanager put-secret-value \
  --secret-id cloud-optimizer/production/integrations/credentials \
  --secret-string '{
    "slack_webhook_url": "https://hooks.slack.com/services/...",
    "pagerduty_api_key": "your-pagerduty-key",
    "datadog_api_key": "your-datadog-key",
    "github_token": "your-github-token"
  }'
```

### 4. Install psycopg2 Lambda Layer (IMPORTANT)

The rotation Lambda function requires the `psycopg2` library. You need to create and attach a Lambda layer:

#### Option A: Use AWS-provided Layer
```bash
# Find the latest psycopg2 layer ARN for your region
# AWS provides these in some regions
aws lambda list-layers --region us-east-1 | grep -i psycopg2
```

#### Option B: Create Custom Layer
```bash
# Create a directory for the layer
mkdir -p lambda-layer/python
cd lambda-layer/python

# Install psycopg2-binary (works in Lambda)
pip install psycopg2-binary -t .

# Create zip file
cd ..
zip -r psycopg2-layer.zip python/

# Upload layer
aws lambda publish-layer-version \
  --layer-name cloud-optimizer-psycopg2 \
  --description "PostgreSQL adapter for Python" \
  --zip-file fileb://psycopg2-layer.zip \
  --compatible-runtimes python3.11

# Attach layer to Lambda function
LAYER_ARN=$(aws lambda list-layer-versions --layer-name cloud-optimizer-psycopg2 --query 'LayerVersions[0].LayerVersionArn' --output text)

aws lambda update-function-configuration \
  --function-name cloud-optimizer-production-db-rotation \
  --layers $LAYER_ARN
```

### 5. Test Manual Rotation

Before waiting 30 days, test the rotation manually:

```bash
aws secretsmanager rotate-secret \
  --secret-id cloud-optimizer/production/database/credentials
```

Monitor the rotation in CloudWatch Logs:
```bash
aws logs tail /aws/lambda/cloud-optimizer-production-db-rotation --follow
```

### 6. Configure CloudWatch Alarm Notifications

Set up SNS topic for alarm notifications:

```bash
# Create SNS topic
aws sns create-topic --name cloud-optimizer-rotation-alerts

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:REGION:ACCOUNT_ID:cloud-optimizer-rotation-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Update the CloudWatch alarm to send to SNS
aws cloudwatch put-metric-alarm \
  --alarm-name cloud-optimizer-production-rotation-failure \
  --alarm-actions arn:aws:sns:REGION:ACCOUNT_ID:cloud-optimizer-rotation-alerts
```

## Application Integration

### Python Example

```python
import boto3
import json
from functools import lru_cache
from datetime import datetime, timedelta

class SecretsManagerClient:
    """Client for retrieving secrets from AWS Secrets Manager with caching."""

    def __init__(self, region_name='us-east-1'):
        self.client = boto3.client('secretsmanager', region_name=region_name)
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)

    def get_secret(self, secret_id: str) -> dict:
        """Get secret value with caching to reduce API calls."""
        now = datetime.now()

        # Check cache
        if secret_id in self.cache:
            cached_value, cached_time = self.cache[secret_id]
            if now - cached_time < self.cache_ttl:
                return cached_value

        # Fetch from Secrets Manager
        try:
            response = self.client.get_secret_value(SecretId=secret_id)
            secret_value = json.loads(response['SecretString'])

            # Update cache
            self.cache[secret_id] = (secret_value, now)

            return secret_value
        except Exception as e:
            # If rotation is in progress, use cached value if available
            if secret_id in self.cache:
                return self.cache[secret_id][0]
            raise

# Usage
secrets = SecretsManagerClient()

# Get database credentials
db_creds = secrets.get_secret('cloud-optimizer/production/database/credentials')
connection_string = f"postgresql://{db_creds['username']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['dbname']}"

# Get API keys
api_keys = secrets.get_secret('cloud-optimizer/production/api/keys')
jwt_secret = api_keys['jwt_secret_key']
```

### Update Cloud Optimizer Configuration

Update your application's configuration to use Secrets Manager:

```python
# src/cloud_optimizer/config.py
from .secrets import SecretsManagerClient

secrets_client = SecretsManagerClient()

# Replace hardcoded credentials with Secrets Manager
DATABASE_CONFIG = secrets_client.get_secret('cloud-optimizer/production/database/credentials')
API_KEYS = secrets_client.get_secret('cloud-optimizer/production/api/keys')
```

## Monitoring and Maintenance

### CloudWatch Logs
Monitor rotation Lambda execution:
```bash
aws logs tail /aws/lambda/cloud-optimizer-production-db-rotation --follow
```

### CloudWatch Metrics
View Lambda invocations and errors:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=cloud-optimizer-production-db-rotation \
  --start-time 2025-12-06T00:00:00Z \
  --end-time 2025-12-06T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

### Rotation History
View secret version history:
```bash
aws secretsmanager describe-secret \
  --secret-id cloud-optimizer/production/database/credentials \
  --query 'VersionIdsToStages'
```

## Troubleshooting

### Rotation Fails with "Connection Timeout"
**Problem**: Lambda cannot reach the database
**Solution**:
- Ensure Lambda is in the same VPC as RDS
- Check security group allows Lambda to access database port 5432
- Verify subnets have NAT gateway for Secrets Manager API access

### Rotation Fails with "Permission Denied"
**Problem**: Lambda IAM role lacks necessary permissions
**Solution**:
```bash
# Check IAM role has correct policies
aws iam get-role \
  --role-name cloud-optimizer-production-rotation-lambda-role

# Verify KMS key policy allows Lambda to use the key
aws kms get-key-policy \
  --key-id alias/cloud-optimizer-production-secrets \
  --policy-name default
```

### Rotation Fails with "ALTER USER Failed"
**Problem**: Database user doesn't exist or lacks permissions
**Solution**:
```sql
-- Connect to database as superuser
CREATE USER cloudguardian WITH PASSWORD 'initial_password';
ALTER USER cloudguardian WITH SUPERUSER;  -- Or specific permissions needed
```

### Application Can't Connect After Rotation
**Problem**: Application is caching old credentials
**Solution**:
- Implement secret caching with short TTL (5-10 minutes)
- Add retry logic for database connections
- Handle ResourceNotFoundException during rotation

## Stack Updates

To update the stack with new parameters:

```bash
aws cloudformation update-stack \
  --stack-name cloud-optimizer-secrets-manager-production \
  --template-body file://cloudformation/secrets-manager.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=production \
    ParameterKey=RotationSchedule,ParameterValue=7 \
  --capabilities CAPABILITY_NAMED_IAM
```

## Stack Deletion

**WARNING**: Deleting the stack will delete all secrets. Ensure you have backups!

```bash
# Disable rotation first
aws secretsmanager cancel-rotate-secret \
  --secret-id cloud-optimizer/production/database/credentials

# Delete stack
aws cloudformation delete-stack \
  --stack-name cloud-optimizer-secrets-manager-production
```

## Security Best Practices

1. **Least Privilege**: Only grant application IAM roles the `secretsmanager:GetSecretValue` permission
2. **VPC Deployment**: Deploy Lambda in VPC for production environments
3. **Monitoring**: Set up CloudWatch alarms and SNS notifications for rotation failures
4. **Audit Trail**: Enable CloudTrail logging for Secrets Manager API calls
5. **Regular Testing**: Test manual rotation quarterly to ensure process works
6. **Backup**: Document initial passwords in secure password manager before enabling rotation

## Cost Estimation

### Monthly Costs (Production Environment)
- Secrets Manager: $0.40/secret/month × 3 secrets = $1.20
- KMS Key: $1.00/month
- Lambda Invocations: ~$0.01/month (1 rotation/month)
- CloudWatch Logs: ~$0.50/month (minimal logging)

**Total**: ~$2.71/month per environment

## Compliance Notes

This implementation meets the following compliance requirements:
- **PCI-DSS**: 90-day maximum password age (template supports 1-365 days)
- **SOC 2**: Automated credential rotation
- **HIPAA**: Encryption at rest (KMS) and in transit (TLS)
- **ISO 27001**: Access control and audit logging

## References

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [Rotating AWS Secrets Manager Secrets](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)
- Cloud Optimizer Issue #152
- Evidence: `/Users/robertstanley/desktop/cloud-optimizer/evidence/issue_152/`
