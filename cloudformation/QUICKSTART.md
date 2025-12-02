# Cloud Optimizer - 5-Minute Quickstart

Deploy Cloud Optimizer to AWS in under 10 minutes.

## Prerequisites

- AWS CLI installed and configured
- AWS account with admin or CloudFormation permissions

## One-Command Deployment

### Step 1: Generate Secrets

```bash
# Generate database password
DB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
echo "Database Password: $DB_PASSWORD"

# Generate JWT secret
JWT_SECRET=$(openssl rand -base64 48 | tr -dc 'a-zA-Z0-9' | head -c 48)
echo "JWT Secret: $JWT_SECRET"

# Save these values securely!
```

### Step 2: Deploy Stack

```bash
cd cloudformation

aws cloudformation create-stack \
  --stack-name cloud-optimizer \
  --template-body file://cloud-optimizer-standalone.yaml \
  --parameters \
    ParameterKey=DBPassword,ParameterValue=$DB_PASSWORD \
    ParameterKey=JWTSecretKey,ParameterValue=$JWT_SECRET \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Step 3: Monitor Deployment

```bash
# Watch stack creation (takes 8-10 minutes)
aws cloudformation wait stack-create-complete \
  --stack-name cloud-optimizer \
  --region us-east-1

echo "Deployment complete!"
```

### Step 4: Get Application URL

```bash
# Get the URL
aws cloudformation describe-stacks \
  --stack-name cloud-optimizer \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' \
  --output text
```

## What Gets Created

- **VPC** with 2 public and 2 private subnets across 2 AZs
- **RDS PostgreSQL** (db.t3.micro, 20GB, encrypted)
- **ECS Fargate** service (0.25 vCPU, 512MB RAM)
- **Application Load Balancer** (internet-facing)
- **Security Groups** (properly locked down)
- **CloudWatch Logs** for application monitoring

## Next Steps

1. **Update Container Image**:
   - Build and push your Docker image to ECR
   - Update stack with your image URL

2. **View Logs**:
   ```bash
   aws logs tail /ecs/cloud-optimizer --follow --region us-east-1
   ```

3. **Scale Application**:
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

```bash
# Delete everything
aws cloudformation delete-stack \
  --stack-name cloud-optimizer \
  --region us-east-1
```

## Cost Estimate

**Trial configuration**: ~$85/month

- RDS db.t3.micro: ~$15
- ECS Fargate (1 task): ~$12
- NAT Gateway: ~$35
- ALB: ~$18
- Data transfer: ~$5

## Troubleshooting

### Stack creation failed

```bash
# Check events for errors
aws cloudformation describe-stack-events \
  --stack-name cloud-optimizer \
  --region us-east-1 \
  --max-items 10
```

### Application not responding

```bash
# Check ECS tasks
CLUSTER=$(aws cloudformation describe-stacks \
  --stack-name cloud-optimizer \
  --query 'Stacks[0].Outputs[?OutputKey==`ECSCluster`].OutputValue' \
  --output text)

aws ecs list-tasks --cluster $CLUSTER --region us-east-1

# View logs
aws logs tail /ecs/cloud-optimizer --follow --region us-east-1
```

## Full Documentation

See [README.md](README.md) for comprehensive documentation.
