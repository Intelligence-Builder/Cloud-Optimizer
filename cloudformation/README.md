# Cloud Optimizer - CloudFormation Quickstart

One-click AWS deployment for Cloud Optimizer using CloudFormation.

## Overview

This CloudFormation template deploys a complete, production-ready Cloud Optimizer infrastructure in your AWS account:

- **VPC**: Custom VPC with public and private subnets across 2 Availability Zones
- **RDS**: PostgreSQL database (encrypted, automated backups)
- **ECS Fargate**: Serverless container orchestration
- **Application Load Balancer**: External access with health checks
- **Security Groups**: Properly configured network security

**Deployment Time**: 8-10 minutes

## Deployment Options

### Option 1: Standalone Template (Recommended for Trial)

**Best for**: Quick deployment, no S3 setup required

```bash
aws cloudformation create-stack \
  --stack-name cloud-optimizer \
  --template-body file://cloud-optimizer-standalone.yaml \
  --parameters file://parameters/trial.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Option 2: Nested Stacks (Recommended for Production)

**Best for**: Modular updates, reusable components

1. Upload nested templates to S3:
```bash
# Create S3 bucket (if you don't have one)
aws s3 mb s3://your-cloudformation-templates

# Upload nested templates
aws s3 sync nested/ s3://your-cloudformation-templates/cloudformation/nested/
```

2. Deploy the main stack:
```bash
aws cloudformation create-stack \
  --stack-name cloud-optimizer \
  --template-body file://cloud-optimizer-quickstart.yaml \
  --parameters \
    ParameterKey=TemplateS3Bucket,ParameterValue=your-cloudformation-templates \
    ParameterKey=TemplateS3KeyPrefix,ParameterValue=cloudformation/nested/ \
    ParameterKey=DBPassword,ParameterValue=YourSecurePassword123 \
    ParameterKey=JWTSecretKey,ParameterValue=YourRandomSecret32CharsOrMore \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

## Prerequisites

### Required

1. **AWS Account** with sufficient permissions:
   - VPC, EC2, RDS, ECS, IAM, CloudFormation, Elastic Load Balancing

2. **AWS CLI** installed and configured:
   ```bash
   aws --version
   aws configure
   ```

3. **Generate Secure Secrets**:
   ```bash
   # Generate database password (8-41 alphanumeric characters)
   openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32

   # Generate JWT secret (minimum 32 characters)
   openssl rand -base64 48 | tr -dc 'a-zA-Z0-9' | head -c 48
   ```

### Optional

- **Docker Image**: Update `ContainerImage` parameter with your ECR/Docker Hub image
- **Domain Name**: For production HTTPS setup (requires ACM certificate)

## Parameters

### Environment Configuration

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `EnvironmentName` | Prefix for all resources | `cloud-optimizer` | No |

### Database Configuration

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `DBInstanceClass` | RDS instance type | `db.t3.micro` | No |
| `DBPassword` | Database password (8-41 chars) | - | **Yes** |
| `AllocatedStorage` | Database storage in GB | `20` | No |
| `MultiAZ` | Enable Multi-AZ deployment | `false` | No |

### ECS Configuration

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `ContainerImage` | Docker image URL | `nginx:latest` | No |
| `ContainerCpu` | CPU units (256 = 0.25 vCPU) | `256` | No |
| `ContainerMemory` | Memory in MB | `512` | No |
| `DesiredCount` | Number of tasks | `1` | No |

### Security Configuration

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `JWTSecretKey` | JWT secret (min 32 chars) | - | **Yes** |

## Deployment Steps

### Step 1: Prepare Parameters

Edit `parameters/trial.json` and update:
- `DBPassword`: Your secure database password
- `JWTSecretKey`: Your JWT secret key
- `ContainerImage`: Your Docker image (when ready)

### Step 2: Validate Template

```bash
# Validate standalone template
aws cloudformation validate-template \
  --template-body file://cloud-optimizer-standalone.yaml

# Validate nested template
aws cloudformation validate-template \
  --template-body file://cloud-optimizer-quickstart.yaml
```

### Step 3: Deploy Stack

Using AWS CLI:
```bash
aws cloudformation create-stack \
  --stack-name cloud-optimizer \
  --template-body file://cloud-optimizer-standalone.yaml \
  --parameters file://parameters/trial.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

Using AWS Console:
1. Go to CloudFormation console
2. Click "Create stack" > "With new resources"
3. Upload `cloud-optimizer-standalone.yaml`
4. Fill in parameters
5. Check "I acknowledge that AWS CloudFormation might create IAM resources with custom names"
6. Click "Create stack"

### Step 4: Monitor Deployment

```bash
# Watch stack events
aws cloudformation describe-stack-events \
  --stack-name cloud-optimizer \
  --region us-east-1

# Check stack status
aws cloudformation describe-stacks \
  --stack-name cloud-optimizer \
  --region us-east-1 \
  --query 'Stacks[0].StackStatus'
```

### Step 5: Get Application URL

```bash
# Get the load balancer URL
aws cloudformation describe-stacks \
  --stack-name cloud-optimizer \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' \
  --output text
```

## Post-Deployment

### Access Your Application

1. Wait for stack creation to complete (status: `CREATE_COMPLETE`)
2. Get the Application URL from stack outputs
3. Open the URL in your browser
4. Verify the `/health` endpoint returns 200 OK

### View ECS Tasks

```bash
# Get cluster name
CLUSTER=$(aws cloudformation describe-stacks \
  --stack-name cloud-optimizer \
  --query 'Stacks[0].Outputs[?OutputKey==`ECSCluster`].OutputValue' \
  --output text)

# List running tasks
aws ecs list-tasks --cluster $CLUSTER --region us-east-1

# Describe task
aws ecs describe-tasks \
  --cluster $CLUSTER \
  --tasks <task-id> \
  --region us-east-1
```

### View Application Logs

```bash
# CloudWatch Logs
aws logs tail /ecs/cloud-optimizer --follow --region us-east-1
```

### Connect to Database (from ECS task)

The database is only accessible from ECS tasks (not publicly accessible). To connect:

1. Use ECS Execute Command:
```bash
aws ecs execute-command \
  --cluster cloud-optimizer-cluster \
  --task <task-id> \
  --container cloud-optimizer-container \
  --command "/bin/bash" \
  --interactive
```

2. From inside the container:
```bash
psql -h $DATABASE_HOST -U cloudguardian -d cloudguardian
```

## Updating the Stack

### Update Container Image

```bash
aws cloudformation update-stack \
  --stack-name cloud-optimizer \
  --use-previous-template \
  --parameters \
    ParameterKey=ContainerImage,ParameterValue=your-ecr-repo/cloud-optimizer:latest \
    ParameterKey=DBPassword,UsePreviousValue=true \
    ParameterKey=JWTSecretKey,UsePreviousValue=true \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Scale ECS Service

```bash
aws cloudformation update-stack \
  --stack-name cloud-optimizer \
  --use-previous-template \
  --parameters \
    ParameterKey=DesiredCount,ParameterValue=3 \
    ParameterKey=DBPassword,UsePreviousValue=true \
    ParameterKey=JWTSecretKey,UsePreviousValue=true \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

## Cleanup

### Delete Stack

```bash
aws cloudformation delete-stack \
  --stack-name cloud-optimizer \
  --region us-east-1
```

**Important**: This will:
- Delete all resources created by the stack
- Create a final RDS snapshot (can be restored later)
- Remove NAT Gateway (stops hourly charges)

### Delete Nested Stack Resources

If using nested stacks, also clean up S3 bucket:
```bash
aws s3 rm s3://your-cloudformation-templates/cloudformation/ --recursive
```

## Cost Estimates

### Trial Configuration (default parameters)

| Resource | Configuration | Monthly Cost (USD) |
|----------|--------------|-------------------|
| RDS PostgreSQL | db.t3.micro, 20GB | ~$15 |
| ECS Fargate | 0.25 vCPU, 0.5GB RAM | ~$12 |
| NAT Gateway | Single NAT + data | ~$35 |
| Application Load Balancer | 1 ALB | ~$18 |
| Data Transfer | Minimal usage | ~$5 |
| **Total** | | **~$85/month** |

### Production Configuration

| Resource | Configuration | Monthly Cost (USD) |
|----------|--------------|-------------------|
| RDS PostgreSQL | db.t3.small, Multi-AZ | ~$60 |
| ECS Fargate | 0.5 vCPU, 1GB RAM x 2 tasks | ~$48 |
| NAT Gateway | 2 NATs + data | ~$70 |
| Application Load Balancer | 1 ALB | ~$18 |
| Data Transfer | Moderate usage | ~$15 |
| **Total** | | **~$211/month** |

### Cost Optimization Tips

1. **Use Fargate Spot** for non-critical workloads (up to 70% savings)
2. **Single NAT Gateway** for trial deployments ($35/month savings)
3. **RDS Reserved Instances** for 1-year commitment (up to 40% savings)
4. **Turn off during development** to avoid charges

## Architecture

```
Internet
    |
[Internet Gateway]
    |
    +-- [ALB in Public Subnets] --+
                                   |
    +-- [NAT Gateway] -------------+
    |                              |
    |                   [ECS Tasks in Private Subnets]
    |                              |
    +-------------- [RDS in Private Subnets]
```

### Network Architecture

- **VPC**: 10.0.0.0/16
- **Public Subnets**: 10.0.1.0/24, 10.0.2.0/24 (ALB, NAT Gateway)
- **Private Subnets**: 10.0.3.0/24, 10.0.4.0/24 (ECS, RDS)
- **Availability Zones**: 2 AZs for high availability

### Security

- **ALB Security Group**: Allows HTTP (80) and HTTPS (443) from internet
- **ECS Security Group**: Allows port 8000 from ALB only
- **RDS Security Group**: Allows PostgreSQL (5432) from ECS only
- **Database**: Encrypted at rest, not publicly accessible
- **IAM Roles**: Least privilege for ECS tasks

## Troubleshooting

### Stack Creation Failed

1. Check CloudFormation events:
```bash
aws cloudformation describe-stack-events \
  --stack-name cloud-optimizer \
  --region us-east-1
```

2. Common issues:
   - Insufficient IAM permissions
   - Parameter validation errors
   - Resource limits exceeded (e.g., VPC limit)

### ECS Tasks Not Starting

1. Check ECS task logs:
```bash
aws logs tail /ecs/cloud-optimizer --follow --region us-east-1
```

2. Common issues:
   - Container image not accessible
   - Environment variables incorrect
   - Health check failing

### Application Not Accessible

1. Verify ALB health checks:
```bash
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>
```

2. Common issues:
   - Security group misconfiguration
   - Health check endpoint not responding
   - Container port mismatch

### Database Connection Issues

1. Check from ECS task:
```bash
# Get task ID
aws ecs list-tasks --cluster cloud-optimizer-cluster

# Connect to task
aws ecs execute-command \
  --cluster cloud-optimizer-cluster \
  --task <task-id> \
  --container cloud-optimizer-container \
  --command "/bin/bash" \
  --interactive

# Test connection
telnet $DATABASE_HOST 5432
```

## Production Checklist

Before going to production:

- [ ] Change default database password
- [ ] Change JWT secret key
- [ ] Update container image to your application
- [ ] Enable Multi-AZ for RDS
- [ ] Add HTTPS certificate to ALB
- [ ] Configure custom domain name
- [ ] Enable CloudWatch alarms
- [ ] Set up automated backups
- [ ] Configure auto-scaling for ECS
- [ ] Review IAM permissions
- [ ] Enable VPC Flow Logs
- [ ] Set up AWS WAF (optional)

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/cloud-optimizer/issues
- Documentation: https://docs.cloud-optimizer.com

## License

[Your License Here]
