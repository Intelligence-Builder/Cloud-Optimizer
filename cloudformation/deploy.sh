#!/bin/bash
#
# Cloud Optimizer - CloudFormation Deployment Script
#
# This script validates and deploys the Cloud Optimizer CloudFormation stack
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
STACK_NAME="cloud-optimizer"
REGION="us-east-1"
TEMPLATE="cloud-optimizer-standalone.yaml"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install it first."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi

    log_info "Prerequisites check passed"
}

generate_secrets() {
    log_info "Generating secure secrets..."

    # Generate database password
    DB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)

    # Generate JWT secret
    JWT_SECRET=$(openssl rand -base64 48 | tr -dc 'a-zA-Z0-9' | head -c 48)

    log_info "Secrets generated successfully"
    log_warn "SAVE THESE CREDENTIALS SECURELY:"
    echo "  Database Password: $DB_PASSWORD"
    echo "  JWT Secret: $JWT_SECRET"
    echo ""
}

validate_template() {
    log_info "Validating CloudFormation template..."

    if ! aws cloudformation validate-template \
        --template-body file://$TEMPLATE \
        --region $REGION &> /dev/null; then
        log_error "Template validation failed"
        exit 1
    fi

    log_info "Template validation passed"
}

deploy_stack() {
    log_info "Deploying CloudFormation stack: $STACK_NAME"

    # Check if stack already exists
    if aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION &> /dev/null; then
        log_warn "Stack $STACK_NAME already exists. Use update-stack instead."

        read -p "Do you want to update the existing stack? (yes/no): " UPDATE_CONFIRM
        if [ "$UPDATE_CONFIRM" != "yes" ]; then
            log_info "Deployment cancelled"
            exit 0
        fi

        # Update stack
        aws cloudformation update-stack \
            --stack-name $STACK_NAME \
            --template-body file://$TEMPLATE \
            --parameters \
                ParameterKey=DBPassword,ParameterValue=$DB_PASSWORD \
                ParameterKey=JWTSecretKey,ParameterValue=$JWT_SECRET \
            --capabilities CAPABILITY_NAMED_IAM \
            --region $REGION

        log_info "Stack update initiated. Waiting for completion..."

        aws cloudformation wait stack-update-complete \
            --stack-name $STACK_NAME \
            --region $REGION
    else
        # Create new stack
        aws cloudformation create-stack \
            --stack-name $STACK_NAME \
            --template-body file://$TEMPLATE \
            --parameters \
                ParameterKey=DBPassword,ParameterValue=$DB_PASSWORD \
                ParameterKey=JWTSecretKey,ParameterValue=$JWT_SECRET \
            --capabilities CAPABILITY_NAMED_IAM \
            --region $REGION

        log_info "Stack creation initiated. This will take 8-10 minutes..."

        # Show progress
        echo ""
        echo "Progress indicators:"
        echo "  - VPC and networking: 2-3 minutes"
        echo "  - Security groups: 1 minute"
        echo "  - RDS database: 5-6 minutes (longest step)"
        echo "  - Load balancer: 2 minutes"
        echo "  - ECS service: 1-2 minutes"
        echo ""

        aws cloudformation wait stack-create-complete \
            --stack-name $STACK_NAME \
            --region $REGION
    fi

    log_info "Stack deployment completed successfully!"
}

show_outputs() {
    log_info "Getting stack outputs..."

    # Get application URL
    APP_URL=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' \
        --output text)

    # Get database endpoint
    DB_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
        --output text)

    echo ""
    echo "========================================"
    echo "  Cloud Optimizer Deployment Complete"
    echo "========================================"
    echo ""
    echo "Application URL: $APP_URL"
    echo "Database Endpoint: $DB_ENDPOINT"
    echo ""
    echo "Next steps:"
    echo "  1. Open the application URL in your browser"
    echo "  2. Check /health endpoint: curl $APP_URL/health"
    echo "  3. View logs: aws logs tail /ecs/$STACK_NAME --follow --region $REGION"
    echo "  4. Update container image when ready"
    echo ""
    echo "Documentation:"
    echo "  - Quickstart: QUICKSTART.md"
    echo "  - Full guide: README.md"
    echo "  - Architecture: ARCHITECTURE.md"
    echo ""
}

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -n, --stack-name NAME    Stack name (default: cloud-optimizer)"
    echo "  -r, --region REGION      AWS region (default: us-east-1)"
    echo "  -t, --template FILE      Template file (default: cloud-optimizer-standalone.yaml)"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                       Deploy with defaults"
    echo "  $0 -n my-stack -r us-west-2"
    echo "  $0 --template cloud-optimizer-quickstart.yaml"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -t|--template)
            TEMPLATE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
echo ""
echo "========================================"
echo "  Cloud Optimizer - Deployment Script"
echo "========================================"
echo ""
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo "Template: $TEMPLATE"
echo ""

# Confirm deployment
read -p "Do you want to proceed with deployment? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    log_info "Deployment cancelled"
    exit 0
fi

# Execute deployment steps
check_prerequisites
generate_secrets
validate_template

# Give user a chance to save credentials
echo ""
log_warn "Please save the credentials above before continuing!"
read -p "Press Enter when you're ready to continue..."

deploy_stack
show_outputs

log_info "Deployment complete!"
