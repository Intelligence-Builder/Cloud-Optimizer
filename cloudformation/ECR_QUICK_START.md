# ECR Quick Start Guide

This is a quick reference for getting started with ECR for Cloud Optimizer.

## 1. Create ECR Repository

### Using CloudFormation (Recommended)
```bash
aws cloudformation create-stack \
  --stack-name cloud-optimizer-ecr \
  --template-body file://cloudformation/nested/ecr.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=cloud-optimizer \
    ParameterKey=ImageTagMutability,ParameterValue=IMMUTABLE \
  --region us-east-1

# Get repository URI
ECR_URI=$(aws cloudformation describe-stacks \
  --stack-name cloud-optimizer-ecr \
  --query 'Stacks[0].Outputs[?OutputKey==`RepositoryUri`].OutputValue' \
  --output text)

echo "ECR Repository: $ECR_URI"
```

### Using AWS CLI
```bash
aws ecr create-repository \
  --repository-name cloud-optimizer \
  --image-scanning-configuration scanOnPush=true \
  --region us-east-1
```

## 2. Build and Push Image

### Using the Automated Script (Easiest)
```bash
# Make script executable (first time only)
chmod +x scripts/build-and-push.sh

# Build and push (auto-detects git commit SHA as tag)
./scripts/build-and-push.sh

# With custom version tag and latest
./scripts/build-and-push.sh --tag v1.0.0 --latest --scan
```

### Using Manual Commands
```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1

# Login to ECR
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build image
docker build -f docker/Dockerfile -t cloud-optimizer:v1.0.0 .

# Tag for ECR
docker tag cloud-optimizer:v1.0.0 \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/cloud-optimizer:v1.0.0

docker tag cloud-optimizer:v1.0.0 \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/cloud-optimizer:latest

# Push to ECR
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/cloud-optimizer:v1.0.0
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/cloud-optimizer:latest
```

## 3. Deploy with ECR Image

### Update CloudFormation Stack
```bash
# Get your ECR image URI
ECR_IMAGE="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/cloud-optimizer:v1.0.0"

# Update stack with new image
aws cloudformation update-stack \
  --stack-name cloud-optimizer \
  --use-previous-template \
  --parameters \
    ParameterKey=ContainerImage,ParameterValue=$ECR_IMAGE \
    ParameterKey=DBPassword,UsePreviousValue=true \
    ParameterKey=JWTSecretKey,UsePreviousValue=true \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Deploy with Helm (Kubernetes)
```bash
helm upgrade --install cloud-optimizer ./helm/cloud-optimizer \
  --set image.repository=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/cloud-optimizer \
  --set image.tag=v1.0.0
```

## 4. Setup GitHub Actions CI/CD (Optional)

### Step 1: Create IAM OIDC Provider
```bash
# This is a one-time setup per AWS account
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com
```

### Step 2: Create IAM Role for GitHub Actions
Save this as `github-actions-ecr-role-trust-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/cloud-optimizer:*"
        }
      }
    }
  ]
}
```

Replace `ACCOUNT_ID` and `YOUR_ORG`, then create the role:
```bash
aws iam create-role \
  --role-name GitHubActionsECRRole \
  --assume-role-policy-document file://github-actions-ecr-role-trust-policy.json

# Attach ECR policy
aws iam attach-role-policy \
  --role-name GitHubActionsECRRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
```

### Step 3: Add GitHub Secret
1. Go to your GitHub repository
2. Settings > Secrets and variables > Actions > New repository secret
3. Add secret:
   - Name: `AWS_ROLE_TO_ASSUME`
   - Value: `arn:aws:iam::ACCOUNT_ID:role/GitHubActionsECRRole`

### Step 4: Push to Trigger Build
```bash
git add .
git commit -m "Configure ECR deployment"
git push origin main
```

The workflow will automatically:
- Build the Docker image
- Tag with git commit SHA, branch name, and latest
- Push to ECR
- Scan for vulnerabilities

## 5. Common Commands

### View Images in Repository
```bash
aws ecr describe-images \
  --repository-name cloud-optimizer \
  --region us-east-1 \
  --output table
```

### Get Latest Image Tag
```bash
aws ecr describe-images \
  --repository-name cloud-optimizer \
  --region us-east-1 \
  --query 'sort_by(imageDetails,& imagePushedAt)[-1].imageTags[0]' \
  --output text
```

### View Vulnerability Scan Results
```bash
aws ecr describe-image-scan-findings \
  --repository-name cloud-optimizer \
  --image-id imageTag=v1.0.0 \
  --region us-east-1
```

### Delete Old Images
```bash
# List images older than 30 days
aws ecr list-images \
  --repository-name cloud-optimizer \
  --region us-east-1 \
  --filter "tagStatus=UNTAGGED"

# Delete untagged images (lifecycle policy handles this automatically)
aws ecr batch-delete-image \
  --repository-name cloud-optimizer \
  --image-ids imageDigest=sha256:xxxxx \
  --region us-east-1
```

## 6. Troubleshooting

### Cannot Authenticate to ECR
```bash
# Token expires after 12 hours - re-authenticate
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

### ECS Cannot Pull Image
Ensure ECS task execution role has these permissions:
```json
{
  "Effect": "Allow",
  "Action": [
    "ecr:GetAuthorizationToken",
    "ecr:BatchCheckLayerAvailability",
    "ecr:GetDownloadUrlForLayer",
    "ecr:BatchGetImage"
  ],
  "Resource": "*"
}
```

### Image Not Found
```bash
# Verify image exists
aws ecr describe-images \
  --repository-name cloud-optimizer \
  --image-ids imageTag=v1.0.0 \
  --region us-east-1
```

## Next Steps

- Read the comprehensive [ECR Setup Guide](ECR_SETUP_GUIDE.md)
- Configure [GitHub Actions workflows](.github/workflows/docker-build.yml)
- Review [Helm deployment options](../helm/cloud-optimizer/values.yaml)
- Set up [CloudFormation parameters](parameters/)

## File Locations

```
cloudformation/
├── nested/
│   └── ecr.yaml                          # ECR CloudFormation template
├── cloud-optimizer-quickstart.yaml       # Main stack (includes ECR)
├── ECR_SETUP_GUIDE.md                    # Comprehensive guide
└── ECR_QUICK_START.md                    # This file

.github/
└── workflows/
    └── docker-build.yml                  # GitHub Actions CI/CD

scripts/
└── build-and-push.sh                     # Automated build script

helm/
└── cloud-optimizer/
    └── values.yaml                       # ECR configuration for K8s
```
