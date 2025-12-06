#!/bin/bash
# Issue #160: SSL/TLS Certificate Deployment Script
# Deploys ACM certificate CloudFormation stack for Cloud Optimizer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMPLATE_FILE="$PROJECT_ROOT/cloudformation/acm-certificate.yaml"

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy SSL/TLS certificate stack for Cloud Optimizer"
    echo ""
    echo "Required Parameters:"
    echo "  -d, --domain DOMAIN        Primary domain name (e.g., app.example.com)"
    echo "  -l, --alb-arn ARN          Application Load Balancer ARN"
    echo "  -t, --target-group ARN     Target Group ARN"
    echo "  -e, --email EMAIL          Alert email address"
    echo ""
    echo "Optional Parameters:"
    echo "  -s, --stack-name NAME      CloudFormation stack name (default: cloud-optimizer-ssl)"
    echo "  -r, --region REGION        AWS region (default: us-east-1)"
    echo "  -z, --hosted-zone ID       Route53 Hosted Zone ID for auto DNS validation"
    echo "  --sans DOMAINS             Additional domains (comma-separated)"
    echo "  --tls-policy POLICY        TLS policy (default: ELBSecurityPolicy-TLS13-1-2-2021-06)"
    echo "  --alert-days DAYS          Days before expiration to alert (default: 30)"
    echo "  --wait                     Wait for stack creation to complete"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Basic deployment"
    echo "  $0 --domain app.example.com --alb-arn arn:aws:... --target-group arn:aws:... --email admin@example.com"
    echo ""
    echo "  # With Route53 auto-validation"
    echo "  $0 --domain app.example.com --hosted-zone Z1234567890AB --alb-arn arn:aws:... --target-group arn:aws:... --email admin@example.com"
    echo ""
    echo "  # With SANs"
    echo "  $0 --domain app.example.com --sans www.example.com,api.example.com --alb-arn arn:aws:... --target-group arn:aws:... --email admin@example.com"
}

# Default values
STACK_NAME="cloud-optimizer-ssl"
REGION="us-east-1"
HOSTED_ZONE_ID=""
SANS=""
TLS_POLICY="ELBSecurityPolicy-TLS13-1-2-2021-06"
ALERT_DAYS="30"
WAIT_FOR_COMPLETION=false

# Required values
DOMAIN=""
ALB_ARN=""
TARGET_GROUP_ARN=""
ALERT_EMAIL=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -l|--alb-arn)
            ALB_ARN="$2"
            shift 2
            ;;
        -t|--target-group)
            TARGET_GROUP_ARN="$2"
            shift 2
            ;;
        -e|--email)
            ALERT_EMAIL="$2"
            shift 2
            ;;
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -z|--hosted-zone)
            HOSTED_ZONE_ID="$2"
            shift 2
            ;;
        --sans)
            SANS="$2"
            shift 2
            ;;
        --tls-policy)
            TLS_POLICY="$2"
            shift 2
            ;;
        --alert-days)
            ALERT_DAYS="$2"
            shift 2
            ;;
        --wait)
            WAIT_FOR_COMPLETION=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate required parameters
missing_params=()
[ -z "$DOMAIN" ] && missing_params+=("--domain")
[ -z "$ALB_ARN" ] && missing_params+=("--alb-arn")
[ -z "$TARGET_GROUP_ARN" ] && missing_params+=("--target-group")
[ -z "$ALERT_EMAIL" ] && missing_params+=("--email")

if [ ${#missing_params[@]} -gt 0 ]; then
    echo -e "${RED}Error: Missing required parameters: ${missing_params[*]}${NC}"
    echo ""
    usage
    exit 1
fi

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Check template exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}Error: Template file not found: $TEMPLATE_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Cloud Optimizer SSL Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Domain:         $DOMAIN"
echo "  ALB ARN:        $ALB_ARN"
echo "  Target Group:   $TARGET_GROUP_ARN"
echo "  Alert Email:    $ALERT_EMAIL"
echo "  TLS Policy:     $TLS_POLICY"
echo "  Stack Name:     $STACK_NAME"
echo "  Region:         $REGION"
[ -n "$HOSTED_ZONE_ID" ] && echo "  Hosted Zone:    $HOSTED_ZONE_ID"
[ -n "$SANS" ] && echo "  SANs:           $SANS"
echo ""

# Validate template
echo -e "${YELLOW}Validating CloudFormation template...${NC}"
aws cloudformation validate-template \
    --template-body "file://$TEMPLATE_FILE" \
    --region "$REGION" > /dev/null

echo -e "${GREEN}Template validated successfully${NC}"
echo ""

# Check if stack exists
STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null || echo "DOES_NOT_EXIST")

if [ "$STACK_STATUS" != "DOES_NOT_EXIST" ]; then
    echo -e "${YELLOW}Stack '$STACK_NAME' already exists with status: $STACK_STATUS${NC}"
    echo ""
    read -p "Do you want to update the existing stack? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled"
        exit 0
    fi
    ACTION="update-stack"
else
    ACTION="create-stack"
fi

# Build parameters
PARAMS=(
    "ParameterKey=DomainName,ParameterValue=$DOMAIN"
    "ParameterKey=LoadBalancerArn,ParameterValue=$ALB_ARN"
    "ParameterKey=TargetGroupArn,ParameterValue=$TARGET_GROUP_ARN"
    "ParameterKey=AlertEmail,ParameterValue=$ALERT_EMAIL"
    "ParameterKey=TLSSecurityPolicy,ParameterValue=$TLS_POLICY"
    "ParameterKey=CertificateExpirationAlertDays,ParameterValue=$ALERT_DAYS"
)

[ -n "$HOSTED_ZONE_ID" ] && PARAMS+=("ParameterKey=HostedZoneId,ParameterValue=$HOSTED_ZONE_ID")
[ -n "$SANS" ] && PARAMS+=("ParameterKey=SubjectAlternativeNames,ParameterValue=$SANS")

# Deploy stack
echo -e "${YELLOW}Deploying CloudFormation stack...${NC}"
echo ""

aws cloudformation $ACTION \
    --stack-name "$STACK_NAME" \
    --template-body "file://$TEMPLATE_FILE" \
    --parameters "${PARAMS[@]}" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    --tags Key=Application,Value=cloud-optimizer Key=Purpose,Value=SSL-TLS

echo -e "${GREEN}Stack $ACTION initiated successfully${NC}"
echo ""

# Wait for completion if requested
if [ "$WAIT_FOR_COMPLETION" = true ]; then
    echo -e "${YELLOW}Waiting for stack to complete...${NC}"
    if [ "$ACTION" = "create-stack" ]; then
        aws cloudformation wait stack-create-complete \
            --stack-name "$STACK_NAME" \
            --region "$REGION"
    else
        aws cloudformation wait stack-update-complete \
            --stack-name "$STACK_NAME" \
            --region "$REGION"
    fi
    echo -e "${GREEN}Stack operation completed${NC}"
fi

# Get stack outputs
echo ""
echo -e "${BLUE}Stack Status:${NC}"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].{Status:StackStatus}' \
    --output table

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Next Steps${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
if [ -z "$HOSTED_ZONE_ID" ]; then
    echo -e "${YELLOW}Manual DNS Validation Required:${NC}"
    echo "1. Go to AWS ACM Console"
    echo "2. Find the certificate for '$DOMAIN'"
    echo "3. Copy the CNAME validation records"
    echo "4. Add records to your DNS provider"
    echo "5. Wait for validation (5-30 minutes)"
    echo ""
fi
echo -e "${GREEN}After validation:${NC}"
echo "- HTTPS will be available at: https://$DOMAIN"
echo "- HTTP will automatically redirect to HTTPS"
echo "- TLS 1.2+ enforced with policy: $TLS_POLICY"
echo ""
echo "Test your SSL configuration:"
echo "  https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo ""
