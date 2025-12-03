# Amazon ECR Setup Guide for Cloud Optimizer

This guide covers the setup and usage of Amazon Elastic Container Registry (ECR) for Cloud Optimizer container deployments.

## Table of Contents

1. [Overview](#overview)
2. [CloudFormation Deployment](#cloudformation-deployment)
3. [Manual ECR Setup](#manual-ecr-setup)
4. [Building and Pushing Images](#building-and-pushing-images)
5. [GitHub Actions CI/CD](#github-actions-cicd)
6. [Kubernetes/Helm Configuration](#kuberneteshelm-configuration)
7. [Troubleshooting](#troubleshooting)

## Overview

The ECR configuration provides:

- **Immutable image tags** (recommended for production)
- **Automatic vulnerability scanning** on image push
- **Lifecycle policies** to retain only the last 10 images
- **Encryption at rest** using AES256
- **Repository policies** for ECS task pull access

## CloudFormation Deployment

### Option 1: Nested Stack (Recommended)

Deploy the complete Cloud Optimizer stack with ECR included:

```bash
aws cloudformation create-stack \
  --stack-name cloud-optimizer \
  --template-body file://cloudformation/cloud-optimizer-quickstart.yaml \
  --parameters \
    ParameterKey=TemplateS3Bucket,ParameterValue=my-cfn-templates-bucket \
    ParameterKey=CreateECRRepository,ParameterValue=true \
    ParameterKey=ImageTagMutability,ParameterValue=IMMUTABLE \
    ParameterKey=DBPassword,ParameterValue=your-secure-password \
    ParameterKey=JWTSecretKey,ParameterValue=your-jwt-secret \
    ParameterKey=ContainerImage,ParameterValue=<your-account>.dkr.ecr.us-east-1.amazonaws.com/cloud-optimizer:latest \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Option 2: ECR Stack Only

Deploy just the ECR repository:

```bash
aws cloudformation create-stack \
  --stack-name cloud-optimizer-ecr \
  --template-body file://cloudformation/nested/ecr.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=cloud-optimizer \
    ParameterKey=ImageTagMutability,ParameterValue=IMMUTABLE \
    ParameterKey=LifecyclePolicyMaxImageCount,ParameterValue=10 \
  --region us-east-1
```

### Retrieve ECR Repository URI

After stack creation:

```bash
# Get repository URI
aws cloudformation describe-stacks \
  --stack-name cloud-optimizer-ecr \
  --query 'Stacks[0].Outputs[?OutputKey==`RepositoryUri`].OutputValue' \
  --output text

# Example output: 123456789012.dkr.ecr.us-east-1.amazonaws.com/cloud-optimizer
```

## Manual ECR Setup

If not using CloudFormation:

```bash
# Create repository
aws ecr create-repository \
  --repository-name cloud-optimizer \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256 \
  --region us-east-1

# Set lifecycle policy
aws ecr put-lifecycle-policy \
  --repository-name cloud-optimizer \
  --lifecycle-policy-text file://ecr-lifecycle-policy.json \
  --region us-east-1
```

**ecr-lifecycle-policy.json:**
```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

## Building and Pushing Images

### Option 1: Using the Build Script (Recommended)

The automated build script handles authentication, building, tagging, and pushing:

```bash
# Basic usage (uses git commit SHA as tag)
./scripts/build-and-push.sh

# With custom tag
./scripts/build-and-push.sh --tag v1.0.0

# Tag as latest and enable vulnerability scanning
./scripts/build-and-push.sh --tag v1.0.0 --latest --scan

# Create repository if it doesn't exist
./scripts/build-and-push.sh --create-repo --region us-west-2

# Full example
./scripts/build-and-push.sh \
  --region us-east-1 \
  --repository cloud-optimizer \
  --tag v1.2.3 \
  --latest \
  --scan
```

### Option 2: Manual Build and Push

```bash
# 1. Authenticate to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 2. Build the image
docker build -f docker/Dockerfile -t cloud-optimizer:latest .

# 3. Tag for ECR
docker tag cloud-optimizer:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/cloud-optimizer:latest

docker tag cloud-optimizer:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/cloud-optimizer:v1.0.0

# 4. Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/cloud-optimizer:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/cloud-optimizer:v1.0.0
```

## GitHub Actions CI/CD

The project includes a GitHub Actions workflow that automatically builds and pushes images to ECR.

### Setup Requirements

#### Option 1: OIDC Authentication (Recommended)

1. **Create IAM OIDC Provider** in your AWS account:

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list <github-thumbprint>
```

2. **Create IAM Role** for GitHub Actions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<your-org>/<your-repo>:*"
        }
      }
    }
  ]
}
```

3. **Attach ECR permissions** to the role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeImages",
        "ecr:DescribeImageScanFindings"
      ],
      "Resource": "*"
    }
  ]
}
```

4. **Add GitHub Secret**:
   - Go to repository Settings > Secrets and variables > Actions
   - Add secret: `AWS_ROLE_TO_ASSUME` = `arn:aws:iam::<account-id>:role/<role-name>`

#### Option 2: Access Keys (Alternative)

1. Create IAM user with ECR permissions
2. Generate access keys
3. Add GitHub secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

### Workflow Triggers

The workflow triggers on:

- **Push to main/develop**: Builds and pushes with branch tag
- **Git tags (v*.*.*)**: Builds and pushes with semantic version tags
- **Pull requests**: Builds only (no push)
- **Manual dispatch**: Custom tag via workflow_dispatch

### Image Tags Generated

- `main` / `develop` - Branch name
- `v1.0.0`, `1.0`, `1` - Semantic version tags
- `main-<sha>` - Git commit SHA
- `latest` - Latest image on main branch
- Custom tag via manual dispatch

## Kubernetes/Helm Configuration

### Option 1: Using EKS with IRSA (Recommended)

For EKS clusters with IAM Roles for Service Accounts (IRSA), no image pull secrets are needed:

```yaml
# values.yaml
ecr:
  enabled: true
  accountId: "123456789012"
  region: "us-east-1"
  repositoryName: "cloud-optimizer"
  useIRSA: true
  iamRoleArn: "arn:aws:iam::123456789012:role/cloud-optimizer-ecr-pull"

image:
  repository: 123456789012.dkr.ecr.us-east-1.amazonaws.com/cloud-optimizer
  tag: "v1.0.0"
  pullPolicy: IfNotPresent

imagePullSecrets: []
```

Deploy:
```bash
helm upgrade --install cloud-optimizer ./helm/cloud-optimizer \
  --set image.repository=123456789012.dkr.ecr.us-east-1.amazonaws.com/cloud-optimizer \
  --set image.tag=v1.0.0 \
  --set ecr.enabled=true \
  --set ecr.accountId=123456789012
```

### Option 2: Using Image Pull Secrets

For non-EKS clusters or without IRSA:

```bash
# Create image pull secret
kubectl create secret docker-registry ecr-registry-secret \
  --docker-server=123456789012.dkr.ecr.us-east-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password --region us-east-1) \
  --namespace default

# Update values.yaml
imagePullSecrets:
  - name: ecr-registry-secret
```

**Note:** ECR tokens expire after 12 hours. Consider using a cronjob to refresh:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: ecr-credential-refresh
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: ecr-credential-refresher
          containers:
          - name: refresh
            image: amazon/aws-cli:latest
            command:
            - /bin/sh
            - -c
            - |
              aws ecr get-login-password --region us-east-1 | \
              kubectl create secret docker-registry ecr-registry-secret \
                --docker-server=<account-id>.dkr.ecr.us-east-1.amazonaws.com \
                --docker-username=AWS \
                --docker-password=$(cat -) \
                --dry-run=client -o yaml | kubectl apply -f -
          restartPolicy: OnFailure
```

## Troubleshooting

### Authentication Issues

**Error:** "no basic auth credentials"

```bash
# Re-authenticate
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
```

**Error:** "denied: Your authorization token has expired"

ECR tokens expire after 12 hours. Re-run the login command.

### Image Pull Errors in ECS

**Error:** "CannotPullContainerError: AccessDeniedException"

1. Verify ECS task execution role has ECR permissions:

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

2. Check repository policy allows ECS:

```bash
aws ecr get-repository-policy \
  --repository-name cloud-optimizer \
  --region us-east-1
```

### Image Not Found

**Error:** "RepositoryNotFoundException" or "ImageNotFoundException"

```bash
# List available images
aws ecr describe-images \
  --repository-name cloud-optimizer \
  --region us-east-1

# Check repository exists
aws ecr describe-repositories \
  --repository-names cloud-optimizer \
  --region us-east-1
```

### Vulnerability Scan Issues

**Error:** "ScanNotFoundException"

Scans take 10-30 seconds to complete. Wait and retry:

```bash
aws ecr wait image-scan-complete \
  --repository-name cloud-optimizer \
  --image-id imageTag=v1.0.0 \
  --region us-east-1

aws ecr describe-image-scan-findings \
  --repository-name cloud-optimizer \
  --image-id imageTag=v1.0.0 \
  --region us-east-1
```

### Multi-Architecture Builds

For ARM64 support (e.g., Graviton instances):

```bash
# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f docker/Dockerfile \
  -t <account-id>.dkr.ecr.us-east-1.amazonaws.com/cloud-optimizer:latest \
  --push \
  .
```

## Best Practices

1. **Use immutable tags** for production deployments
2. **Enable vulnerability scanning** on all repositories
3. **Implement lifecycle policies** to manage storage costs
4. **Use semantic versioning** for release tags (v1.0.0)
5. **Tag images with git commit SHA** for traceability
6. **Use IRSA for EKS** instead of static credentials
7. **Implement automated builds** via CI/CD pipelines
8. **Monitor image scan results** and address vulnerabilities
9. **Use multi-stage builds** to minimize image size
10. **Test images in staging** before production deployment

## Additional Resources

- [AWS ECR Documentation](https://docs.aws.amazon.com/ecr/)
- [ECS Task IAM Roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
- [EKS IRSA Documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Docker Multi-Platform Builds](https://docs.docker.com/build/building/multi-platform/)
- [GitHub Actions AWS Authentication](https://github.com/aws-actions/configure-aws-credentials)
