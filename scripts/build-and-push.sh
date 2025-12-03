#!/bin/bash

###############################################################################
# Build and Push Docker Image to Amazon ECR
#
# This script builds the Cloud Optimizer Docker image and pushes it to ECR.
# It supports multiple tagging strategies and includes validation steps.
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Docker installed and running
#   - ECR repository created (or will be created if it doesn't exist)
#
# Usage:
#   ./build-and-push.sh [OPTIONS]
#
# Options:
#   -r, --region REGION        AWS region (default: us-east-1)
#   -n, --repository NAME      ECR repository name (default: cloud-optimizer)
#   -t, --tag TAG             Custom tag (default: git commit SHA)
#   -l, --latest              Also tag as 'latest'
#   -c, --create-repo         Create ECR repository if it doesn't exist
#   -s, --scan                Enable vulnerability scanning after push
#   -h, --help                Show this help message
#
# Examples:
#   ./build-and-push.sh
#   ./build-and-push.sh --region us-west-2 --tag v1.0.0 --latest
#   ./build-and-push.sh --create-repo --scan
#
###############################################################################

set -e  # Exit on error

# Default values
AWS_REGION="${AWS_REGION:-us-east-1}"
REPOSITORY_NAME="${REPOSITORY_NAME:-cloud-optimizer}"
CUSTOM_TAG=""
TAG_LATEST=false
CREATE_REPO=false
ENABLE_SCAN=false
DOCKERFILE_PATH="./docker/Dockerfile"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    head -n 40 "$0" | grep "^#" | sed 's/^# //; s/^#//'
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -n|--repository)
            REPOSITORY_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            CUSTOM_TAG="$2"
            shift 2
            ;;
        -l|--latest)
            TAG_LATEST=true
            shift
            ;;
        -c|--create-repo)
            CREATE_REPO=true
            shift
            ;;
        -s|--scan)
            ENABLE_SCAN=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Validation
log_info "Validating prerequisites..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Dockerfile exists
if [ ! -f "$DOCKERFILE_PATH" ]; then
    log_error "Dockerfile not found at: $DOCKERFILE_PATH"
    exit 1
fi

# Verify AWS credentials
log_info "Verifying AWS credentials..."
if ! aws sts get-caller-identity --region "$AWS_REGION" > /dev/null 2>&1; then
    log_error "AWS credentials are not configured or invalid."
    log_error "Please run 'aws configure' or set AWS environment variables."
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log_success "Authenticated as AWS Account: $AWS_ACCOUNT_ID"

# Get or create ECR repository
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPOSITORY_URI="${ECR_REGISTRY}/${REPOSITORY_NAME}"

log_info "Checking if ECR repository exists: $REPOSITORY_NAME"
if ! aws ecr describe-repositories --repository-names "$REPOSITORY_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    if [ "$CREATE_REPO" = true ]; then
        log_warning "Repository does not exist. Creating..."
        aws ecr create-repository \
            --repository-name "$REPOSITORY_NAME" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256 \
            --tags "Key=Environment,Value=production" "Key=ManagedBy,Value=script" > /dev/null
        log_success "ECR repository created: $REPOSITORY_NAME"
    else
        log_error "ECR repository does not exist: $REPOSITORY_NAME"
        log_error "Run with --create-repo flag to create it automatically."
        exit 1
    fi
else
    log_success "ECR repository exists: $REPOSITORY_NAME"
fi

# Determine image tag
if [ -n "$CUSTOM_TAG" ]; then
    IMAGE_TAG="$CUSTOM_TAG"
else
    # Use git commit SHA if available, otherwise use timestamp
    if git rev-parse --git-dir > /dev/null 2>&1; then
        IMAGE_TAG=$(git rev-parse --short HEAD)
        GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
        log_info "Using git commit SHA as tag: $IMAGE_TAG (branch: $GIT_BRANCH)"
    else
        IMAGE_TAG=$(date +%Y%m%d-%H%M%S)
        log_warning "Not a git repository. Using timestamp as tag: $IMAGE_TAG"
    fi
fi

# Build metadata
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

log_info "Building Docker image..."
log_info "  Image: $ECR_REPOSITORY_URI:$IMAGE_TAG"
log_info "  Build Date: $BUILD_DATE"
log_info "  VCS Ref: $VCS_REF"

# Build the image
docker build \
    --file "$DOCKERFILE_PATH" \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg VERSION="$IMAGE_TAG" \
    --tag "${ECR_REPOSITORY_URI}:${IMAGE_TAG}" \
    --tag "${ECR_REPOSITORY_URI}:${GIT_BRANCH:-latest}" \
    .

log_success "Docker image built successfully"

# Tag as latest if requested
if [ "$TAG_LATEST" = true ]; then
    log_info "Tagging image as 'latest'..."
    docker tag "${ECR_REPOSITORY_URI}:${IMAGE_TAG}" "${ECR_REPOSITORY_URI}:latest"
fi

# Login to ECR
log_info "Logging in to Amazon ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$ECR_REGISTRY"

log_success "Logged in to ECR"

# Push the image
log_info "Pushing image to ECR..."
docker push "${ECR_REPOSITORY_URI}:${IMAGE_TAG}"

if [ -n "$GIT_BRANCH" ]; then
    log_info "Pushing branch tag: $GIT_BRANCH"
    docker push "${ECR_REPOSITORY_URI}:${GIT_BRANCH}"
fi

if [ "$TAG_LATEST" = true ]; then
    log_info "Pushing 'latest' tag..."
    docker push "${ECR_REPOSITORY_URI}:latest"
fi

log_success "Image pushed successfully"

# Display pushed images
echo ""
log_info "Pushed images:"
echo "  - ${ECR_REPOSITORY_URI}:${IMAGE_TAG}"
[ -n "$GIT_BRANCH" ] && echo "  - ${ECR_REPOSITORY_URI}:${GIT_BRANCH}"
[ "$TAG_LATEST" = true ] && echo "  - ${ECR_REPOSITORY_URI}:latest"

# Vulnerability scanning
if [ "$ENABLE_SCAN" = true ]; then
    log_info "Waiting for vulnerability scan to complete..."
    sleep 10

    log_info "Retrieving scan results..."
    if aws ecr describe-image-scan-findings \
        --repository-name "$REPOSITORY_NAME" \
        --image-id "imageTag=${IMAGE_TAG}" \
        --region "$AWS_REGION" > /tmp/scan-results.json 2>&1; then

        # Parse scan results
        CRITICAL=$(jq -r '.imageScanFindings.findingSeverityCounts.CRITICAL // 0' /tmp/scan-results.json)
        HIGH=$(jq -r '.imageScanFindings.findingSeverityCounts.HIGH // 0' /tmp/scan-results.json)
        MEDIUM=$(jq -r '.imageScanFindings.findingSeverityCounts.MEDIUM // 0' /tmp/scan-results.json)
        LOW=$(jq -r '.imageScanFindings.findingSeverityCounts.LOW // 0' /tmp/scan-results.json)

        echo ""
        log_info "Vulnerability Scan Results:"
        echo "  Critical: $CRITICAL"
        echo "  High: $HIGH"
        echo "  Medium: $MEDIUM"
        echo "  Low: $LOW"

        if [ "$CRITICAL" -gt 0 ] || [ "$HIGH" -gt 0 ]; then
            log_warning "Image has CRITICAL or HIGH vulnerabilities!"
        else
            log_success "No critical vulnerabilities found"
        fi
    else
        log_warning "Scan not yet complete. Check ECR console for results."
    fi
fi

# Summary
echo ""
echo "=========================================="
log_success "BUILD AND PUSH COMPLETED"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Update your CloudFormation parameters with the new image:"
echo "     ContainerImage: ${ECR_REPOSITORY_URI}:${IMAGE_TAG}"
echo ""
echo "  2. Update your ECS service to use the new image:"
echo "     aws ecs update-service --cluster <cluster-name> --service <service-name> --force-new-deployment"
echo ""
echo "  3. Monitor the deployment:"
echo "     aws ecs describe-services --cluster <cluster-name> --services <service-name>"
echo ""
echo "  4. View logs in CloudWatch:"
echo "     https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}"
echo ""
