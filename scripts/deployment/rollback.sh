#!/bin/bash
# Instant Rollback Script - Issue #159
# Performs instant rollback to Blue environment (< 1 minute)

set -e

# Configuration
ENVIRONMENT="${ENVIRONMENT:-staging}"
AWS_REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${ENVIRONMENT}-bluegreen"

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

# Record rollback start time
ROLLBACK_START=$(date +%s)

log_warning "============================================"
log_warning "     INITIATING INSTANT ROLLBACK"
log_warning "============================================"
log_info "Environment: $ENVIRONMENT"
log_info "Target: 100% traffic to Blue"
echo ""

# Step 1: Shift all traffic to Blue (immediate)
log_info "Step 1/3: Shifting traffic to Blue..."

LISTENER_ARN=$(get_stack_output "ProductionListenerArn")
BLUE_TG_ARN=$(get_stack_output "BlueTargetGroupArn")
GREEN_TG_ARN=$(get_stack_output "GreenTargetGroupArn")

aws elbv2 modify-listener \
    --listener-arn "$LISTENER_ARN" \
    --region "$AWS_REGION" \
    --default-actions "[{
        \"Type\": \"forward\",
        \"ForwardConfig\": {
            \"TargetGroups\": [
                {\"TargetGroupArn\": \"${BLUE_TG_ARN}\", \"Weight\": 100},
                {\"TargetGroupArn\": \"${GREEN_TG_ARN}\", \"Weight\": 0}
            ]
        }
    }]" > /dev/null

TRAFFIC_SHIFT_TIME=$(($(date +%s) - ROLLBACK_START))
log_success "Traffic shifted to Blue in ${TRAFFIC_SHIFT_TIME}s"
echo ""

# Step 2: Scale down Green service
log_info "Step 2/3: Scaling down Green service..."

CLUSTER_NAME="${ENVIRONMENT}-bluegreen-cluster"
GREEN_SERVICE="${ENVIRONMENT}-green-service"

aws ecs update-service \
    --cluster "$CLUSTER_NAME" \
    --service "$GREEN_SERVICE" \
    --desired-count 0 \
    --region "$AWS_REGION" > /dev/null

log_success "Green service scale-down initiated"
echo ""

# Step 3: Record rollback metrics
log_info "Step 3/3: Recording rollback metrics..."

aws cloudwatch put-metric-data \
    --namespace CloudOptimizer \
    --metric-name DeploymentRollback \
    --value 1 \
    --unit Count \
    --dimensions Environment="$ENVIRONMENT" \
    --region "$AWS_REGION"

ROLLBACK_END=$(($(date +%s) - ROLLBACK_START))

log_success "============================================"
log_success "     ROLLBACK COMPLETE"
log_success "============================================"
log_info "Total rollback time: ${ROLLBACK_END} seconds"
log_info "Traffic: 100% on Blue"
log_info "Green service: Scaling down"
echo ""

# Verify traffic distribution
log_info "Verifying traffic distribution..."
WEIGHTS=$(aws elbv2 describe-rules \
    --listener-arn "$LISTENER_ARN" \
    --region "$AWS_REGION" \
    --query "Rules[?IsDefault==\`true\`].Actions[0].ForwardConfig.TargetGroups" \
    --output json)

echo "$WEIGHTS" | jq -r '.[] | "  \(.TargetGroupArn | split("/")[1]): \(.Weight)%"'

if [ "$ROLLBACK_END" -lt 60 ]; then
    log_success "Rollback completed under 1 minute requirement!"
else
    log_warning "Rollback took longer than 1 minute target"
fi
