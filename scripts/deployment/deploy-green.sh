#!/bin/bash
# Deploy to Green Environment Script - Issue #159
# Deploys new version to Green environment for blue/green deployment

set -e

# Configuration
ENVIRONMENT="${ENVIRONMENT:-staging}"
AWS_REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${ENVIRONMENT}-bluegreen"
ECR_REPOSITORY="${ECR_REPOSITORY:-cloud-optimizer}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get CloudFormation output
get_stack_output() {
    local output_key=$1
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='${output_key}'].OutputValue" \
        --output text
}

# Build and push Docker image
build_and_push() {
    local image_tag=${1:-$(git rev-parse --short HEAD)}

    log_info "Building Docker image with tag: $image_tag"

    # Get ECR registry
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local ecr_registry="${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    local image_uri="${ecr_registry}/${ECR_REPOSITORY}:${image_tag}"

    # Login to ECR
    log_info "Logging in to ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ecr_registry"

    # Build image
    log_info "Building Docker image..."
    docker build -f docker/Dockerfile -t "$image_uri" .

    # Push to ECR
    log_info "Pushing image to ECR..."
    docker push "$image_uri"

    log_success "Image pushed: $image_uri"
    echo "$image_uri"
}

# Update task definition with new image
update_task_definition() {
    local image_uri=$1
    local task_family="${ENVIRONMENT}-bluegreen-task"

    log_info "Updating task definition with new image..."

    # Get current task definition
    local task_def=$(aws ecs describe-task-definition \
        --task-definition "$task_family" \
        --region "$AWS_REGION" \
        --query 'taskDefinition')

    # Update image in task definition
    local new_task_def=$(echo "$task_def" | jq --arg IMAGE "$image_uri" \
        '.containerDefinitions[0].image = $IMAGE |
         del(.taskDefinitionArn, .revision, .status, .requiresAttributes,
             .compatibilities, .registeredAt, .registeredBy)')

    # Register new task definition
    local new_task_arn=$(aws ecs register-task-definition \
        --cli-input-json "$new_task_def" \
        --region "$AWS_REGION" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)

    log_success "New task definition: $new_task_arn"
    echo "$new_task_arn"
}

# Deploy to Green service
deploy_to_green() {
    local task_arn=$1
    local desired_count=${2:-2}

    local cluster_name="${ENVIRONMENT}-bluegreen-cluster"
    local green_service="${ENVIRONMENT}-green-service"

    log_info "Deploying to Green service..."
    log_info "  Cluster: $cluster_name"
    log_info "  Service: $green_service"
    log_info "  Task Definition: $task_arn"
    log_info "  Desired Count: $desired_count"

    # Update Green service with new task definition
    aws ecs update-service \
        --cluster "$cluster_name" \
        --service "$green_service" \
        --task-definition "$task_arn" \
        --desired-count "$desired_count" \
        --force-new-deployment \
        --region "$AWS_REGION" > /dev/null

    log_success "Deployment initiated"
}

# Wait for Green service to stabilize
wait_for_stability() {
    local cluster_name="${ENVIRONMENT}-bluegreen-cluster"
    local green_service="${ENVIRONMENT}-green-service"

    log_info "Waiting for Green service to stabilize..."

    aws ecs wait services-stable \
        --cluster "$cluster_name" \
        --services "$green_service" \
        --region "$AWS_REGION"

    log_success "Green service is stable"
}

# Test Green deployment via test listener
test_deployment() {
    local alb_dns=$(get_stack_output "LoadBalancerDNS")
    local test_url="http://${alb_dns}:8080/health"
    local max_attempts=10
    local attempt=1

    log_info "Testing Green deployment at $test_url"

    while [ $attempt -le $max_attempts ]; do
        local response=$(curl -s -o /dev/null -w "%{http_code}" "$test_url" 2>/dev/null || echo "000")

        if [ "$response" = "200" ]; then
            log_success "Health check passed (attempt $attempt)"
            return 0
        fi

        log_warning "Health check returned $response (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done

    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Full deployment workflow
full_deploy() {
    local image_tag=${1:-$(git rev-parse --short HEAD)}
    local desired_count=${2:-2}

    log_info "=== Starting Blue/Green Deployment ==="
    log_info "Environment: $ENVIRONMENT"
    log_info "Image Tag: $image_tag"
    echo ""

    # Step 1: Build and push image
    log_info "Step 1/4: Building and pushing image..."
    local image_uri=$(build_and_push "$image_tag")
    echo ""

    # Step 2: Update task definition
    log_info "Step 2/4: Updating task definition..."
    local task_arn=$(update_task_definition "$image_uri")
    echo ""

    # Step 3: Deploy to Green
    log_info "Step 3/4: Deploying to Green service..."
    deploy_to_green "$task_arn" "$desired_count"
    wait_for_stability
    echo ""

    # Step 4: Test deployment
    log_info "Step 4/4: Testing Green deployment..."
    if test_deployment; then
        log_success "=== Deployment to Green Complete ==="
        log_info "Green environment is ready for traffic shift"
        log_info "Run 'scripts/deployment/traffic-shift.sh canary' to shift traffic"
    else
        log_error "=== Deployment Failed ==="
        log_warning "Consider running rollback or investigating the issue"
        return 1
    fi
}

# Usage information
usage() {
    echo "Deploy to Green Environment Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  deploy [tag] [count]      Full deployment workflow"
    echo "  build [tag]               Build and push Docker image only"
    echo "  update <image_uri>        Update task definition with image"
    echo "  scale <count>             Scale Green service"
    echo "  test                      Test Green deployment"
    echo "  wait                      Wait for service stability"
    echo ""
    echo "Environment Variables:"
    echo "  ENVIRONMENT      Target environment (default: staging)"
    echo "  AWS_REGION       AWS region (default: us-east-1)"
    echo "  ECR_REPOSITORY   ECR repository name (default: cloud-optimizer)"
    echo ""
    echo "Examples:"
    echo "  $0 deploy"
    echo "  $0 deploy v1.2.3 3"
    echo "  $0 build latest"
    echo "  ENVIRONMENT=production $0 deploy"
}

# Main command handling
case "${1:-}" in
    deploy)
        full_deploy "${2:-}" "${3:-2}"
        ;;
    build)
        build_and_push "${2:-$(git rev-parse --short HEAD)}"
        ;;
    update)
        if [ -z "${2:-}" ]; then
            log_error "Usage: $0 update <image_uri>"
            exit 1
        fi
        update_task_definition "$2"
        ;;
    scale)
        if [ -z "${2:-}" ]; then
            log_error "Usage: $0 scale <desired_count>"
            exit 1
        fi
        local cluster_name="${ENVIRONMENT}-bluegreen-cluster"
        local green_service="${ENVIRONMENT}-green-service"
        aws ecs update-service \
            --cluster "$cluster_name" \
            --service "$green_service" \
            --desired-count "$2" \
            --region "$AWS_REGION" > /dev/null
        log_success "Green service scaled to $2 tasks"
        ;;
    test)
        test_deployment
        ;;
    wait)
        wait_for_stability
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac
