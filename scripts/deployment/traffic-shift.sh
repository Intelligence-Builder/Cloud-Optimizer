#!/bin/bash
# Blue/Green Traffic Shifting Script - Issue #159
# Implements gradual traffic shift (canary) between Blue and Green environments

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
NC='\033[0m' # No Color

# Logging functions
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

# Get CloudFormation outputs
get_stack_output() {
    local output_key=$1
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='${output_key}'].OutputValue" \
        --output text
}

# Get current traffic weights
get_current_weights() {
    local listener_arn=$(get_stack_output "ProductionListenerArn")

    aws elbv2 describe-rules \
        --listener-arn "$listener_arn" \
        --region "$AWS_REGION" \
        --query "Rules[?IsDefault==\`true\`].Actions[0].ForwardConfig.TargetGroups" \
        --output json
}

# Shift traffic to specified weights
shift_traffic() {
    local blue_weight=$1
    local green_weight=$2

    local listener_arn=$(get_stack_output "ProductionListenerArn")
    local blue_tg_arn=$(get_stack_output "BlueTargetGroupArn")
    local green_tg_arn=$(get_stack_output "GreenTargetGroupArn")

    log_info "Shifting traffic: Blue=${blue_weight}%, Green=${green_weight}%"

    aws elbv2 modify-listener \
        --listener-arn "$listener_arn" \
        --region "$AWS_REGION" \
        --default-actions "[{
            \"Type\": \"forward\",
            \"ForwardConfig\": {
                \"TargetGroups\": [
                    {\"TargetGroupArn\": \"${blue_tg_arn}\", \"Weight\": ${blue_weight}},
                    {\"TargetGroupArn\": \"${green_tg_arn}\", \"Weight\": ${green_weight}}
                ]
            }
        }]" > /dev/null

    log_success "Traffic shift complete"
}

# Monitor error rate during traffic shift
monitor_errors() {
    local duration=${1:-60}
    local threshold=${2:-5}
    local alb_arn=$(get_stack_output "LoadBalancerArn")
    local alb_name=$(echo "$alb_arn" | sed 's/.*loadbalancer\///')

    log_info "Monitoring error rate for ${duration} seconds..."

    local start_time=$(date -u -d "${duration} seconds ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-${duration}S +%Y-%m-%dT%H:%M:%SZ)
    local end_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    local error_count=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/ApplicationELB \
        --metric-name HTTPCode_Target_5XX_Count \
        --dimensions Name=LoadBalancer,Value="$alb_name" \
        --start-time "$start_time" \
        --end-time "$end_time" \
        --period 60 \
        --statistics Sum \
        --region "$AWS_REGION" \
        --query 'Datapoints[0].Sum' \
        --output text)

    error_count=${error_count:-0}

    if [ "$error_count" = "None" ]; then
        error_count=0
    fi

    log_info "Error count: $error_count (threshold: $threshold)"

    if [ "$error_count" -gt "$threshold" ]; then
        log_error "Error rate exceeded threshold!"
        return 1
    fi

    log_success "Error rate within acceptable limits"
    return 0
}

# Canary deployment with gradual traffic shift
canary_deploy() {
    local steps=${1:-"10,50,100"}
    local interval=${2:-300}  # 5 minutes between steps

    IFS=',' read -ra WEIGHTS <<< "$steps"

    for green_weight in "${WEIGHTS[@]}"; do
        local blue_weight=$((100 - green_weight))

        log_info "=== Canary Step: ${green_weight}% traffic to Green ==="

        shift_traffic "$blue_weight" "$green_weight"

        if [ "$green_weight" -lt 100 ]; then
            log_info "Waiting ${interval} seconds before next step..."
            sleep "$interval"

            if ! monitor_errors 60 5; then
                log_error "Error rate exceeded, triggering rollback"
                rollback
                exit 1
            fi
        fi
    done

    log_success "Canary deployment complete - 100% traffic on Green"
}

# Instant rollback to Blue
rollback() {
    log_warning "Initiating rollback to Blue environment..."

    shift_traffic 100 0

    # Scale down Green service
    local cluster_name="${ENVIRONMENT}-bluegreen-cluster"
    local green_service="${ENVIRONMENT}-green-service"

    aws ecs update-service \
        --cluster "$cluster_name" \
        --service "$green_service" \
        --desired-count 0 \
        --region "$AWS_REGION" > /dev/null

    log_success "Rollback complete - 100% traffic on Blue"

    # Record rollback metric
    aws cloudwatch put-metric-data \
        --namespace CloudOptimizer \
        --metric-name DeploymentRollback \
        --value 1 \
        --unit Count \
        --dimensions Environment="$ENVIRONMENT" \
        --region "$AWS_REGION"
}

# Show current status
status() {
    log_info "=== Blue/Green Deployment Status ==="
    log_info "Environment: $ENVIRONMENT"
    log_info "Stack: $STACK_NAME"
    echo ""

    log_info "Current Traffic Distribution:"
    local weights=$(get_current_weights)
    echo "$weights" | jq -r '.[] | "  \(.TargetGroupArn | split("/")[1]): \(.Weight)%"'
    echo ""

    log_info "Target Group Health:"
    local blue_tg=$(get_stack_output "BlueTargetGroupArn")
    local green_tg=$(get_stack_output "GreenTargetGroupArn")

    echo "  Blue:"
    aws elbv2 describe-target-health \
        --target-group-arn "$blue_tg" \
        --region "$AWS_REGION" \
        --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}" \
        --output table 2>/dev/null || echo "    No targets registered"

    echo "  Green:"
    aws elbv2 describe-target-health \
        --target-group-arn "$green_tg" \
        --region "$AWS_REGION" \
        --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}" \
        --output table 2>/dev/null || echo "    No targets registered"
}

# Usage information
usage() {
    echo "Blue/Green Traffic Shifting Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  shift <blue%> <green%>    Shift traffic to specified weights"
    echo "  canary [steps] [interval] Gradual traffic shift (default: 10,50,100)"
    echo "  rollback                  Instant rollback to Blue"
    echo "  status                    Show current deployment status"
    echo "  monitor [duration] [threshold]  Monitor error rate"
    echo ""
    echo "Environment Variables:"
    echo "  ENVIRONMENT    Target environment (default: staging)"
    echo "  AWS_REGION     AWS region (default: us-east-1)"
    echo ""
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 shift 50 50"
    echo "  $0 canary 10,50,100 300"
    echo "  $0 rollback"
    echo "  ENVIRONMENT=production $0 canary"
}

# Main command handling
case "${1:-}" in
    shift)
        if [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
            log_error "Usage: $0 shift <blue%> <green%>"
            exit 1
        fi
        shift_traffic "$2" "$3"
        ;;
    canary)
        canary_deploy "${2:-10,50,100}" "${3:-300}"
        ;;
    rollback)
        rollback
        ;;
    status)
        status
        ;;
    monitor)
        monitor_errors "${2:-60}" "${3:-5}"
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac
