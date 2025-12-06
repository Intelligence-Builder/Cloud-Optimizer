#!/bin/bash
# Issue #160: SSL/TLS Certificate Status Check Script
# Checks ACM certificate status and expiration for Cloud Optimizer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ALERT_DAYS=${ALERT_DAYS:-30}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Check SSL/TLS certificate status and expiration"
    echo ""
    echo "Options:"
    echo "  -d, --domain DOMAIN     Domain name to check (required if no ARN)"
    echo "  -a, --arn ARN           Certificate ARN to check directly"
    echo "  -r, --region REGION     AWS region (default: us-east-1)"
    echo "  --alert-days DAYS       Days before expiration to alert (default: 30)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --domain app.example.com"
    echo "  $0 --arn arn:aws:acm:us-east-1:123456789:certificate/abc123"
    echo "  $0 --domain app.example.com --alert-days 60"
}

# Parse arguments
DOMAIN=""
CERT_ARN=""
REGION="us-east-1"

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -a|--arn)
            CERT_ARN="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        --alert-days)
            ALERT_DAYS="$2"
            shift 2
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

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Check jq
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Cloud Optimizer Certificate Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Find certificate by domain if ARN not provided
if [ -z "$CERT_ARN" ]; then
    if [ -z "$DOMAIN" ]; then
        echo -e "${RED}Error: Either --domain or --arn is required${NC}"
        usage
        exit 1
    fi

    echo -e "${YELLOW}Searching for certificate for domain: ${DOMAIN}${NC}"

    CERT_ARN=$(aws acm list-certificates --region "$REGION" \
        --query "CertificateSummaryList[?DomainName=='${DOMAIN}'].CertificateArn" \
        --output text 2>/dev/null | head -1)

    if [ -z "$CERT_ARN" ] || [ "$CERT_ARN" == "None" ]; then
        echo -e "${RED}No certificate found for domain: ${DOMAIN}${NC}"
        echo ""
        echo "Available certificates:"
        aws acm list-certificates --region "$REGION" \
            --query "CertificateSummaryList[*].[DomainName,CertificateArn]" \
            --output table 2>/dev/null || echo "  No certificates found"
        exit 1
    fi
fi

echo -e "${GREEN}Found certificate: ${CERT_ARN}${NC}"
echo ""

# Get certificate details
CERT_INFO=$(aws acm describe-certificate --region "$REGION" \
    --certificate-arn "$CERT_ARN" 2>/dev/null)

if [ -z "$CERT_INFO" ]; then
    echo -e "${RED}Failed to get certificate details${NC}"
    exit 1
fi

# Extract certificate information
DOMAIN_NAME=$(echo "$CERT_INFO" | jq -r '.Certificate.DomainName')
STATUS=$(echo "$CERT_INFO" | jq -r '.Certificate.Status')
TYPE=$(echo "$CERT_INFO" | jq -r '.Certificate.Type')
KEY_ALGORITHM=$(echo "$CERT_INFO" | jq -r '.Certificate.KeyAlgorithm')
NOT_BEFORE=$(echo "$CERT_INFO" | jq -r '.Certificate.NotBefore // "N/A"')
NOT_AFTER=$(echo "$CERT_INFO" | jq -r '.Certificate.NotAfter // "N/A"')
RENEWAL_STATUS=$(echo "$CERT_INFO" | jq -r '.Certificate.RenewalSummary.RenewalStatus // "N/A"')
IN_USE_BY=$(echo "$CERT_INFO" | jq -r '.Certificate.InUseBy | length')
SANS=$(echo "$CERT_INFO" | jq -r '.Certificate.SubjectAlternativeNames | join(", ")')

# Display certificate information
echo -e "${BLUE}Certificate Information:${NC}"
echo "  Domain:          $DOMAIN_NAME"
echo "  SANs:            $SANS"
echo "  Type:            $TYPE"
echo "  Key Algorithm:   $KEY_ALGORITHM"
echo ""

# Status with color
echo -e -n "  Status:          "
case $STATUS in
    "ISSUED")
        echo -e "${GREEN}$STATUS${NC}"
        ;;
    "PENDING_VALIDATION")
        echo -e "${YELLOW}$STATUS${NC}"
        ;;
    "VALIDATION_TIMED_OUT"|"REVOKED"|"FAILED")
        echo -e "${RED}$STATUS${NC}"
        ;;
    *)
        echo "$STATUS"
        ;;
esac

echo "  In Use By:       $IN_USE_BY resources"
echo ""

# Expiration check
if [ "$NOT_AFTER" != "N/A" ] && [ "$NOT_AFTER" != "null" ]; then
    echo -e "${BLUE}Expiration Information:${NC}"
    echo "  Issued:          $NOT_BEFORE"
    echo "  Expires:         $NOT_AFTER"

    # Calculate days until expiration
    EXPIRY_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${NOT_AFTER%+*}" "+%s" 2>/dev/null || \
                   date -d "${NOT_AFTER}" "+%s" 2>/dev/null)
    NOW_EPOCH=$(date "+%s")
    DAYS_REMAINING=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    echo -n "  Days Remaining:  "
    if [ "$DAYS_REMAINING" -le 0 ]; then
        echo -e "${RED}EXPIRED${NC}"
    elif [ "$DAYS_REMAINING" -le "$ALERT_DAYS" ]; then
        echo -e "${YELLOW}${DAYS_REMAINING} days (WARNING: Less than ${ALERT_DAYS} days)${NC}"
    else
        echo -e "${GREEN}${DAYS_REMAINING} days${NC}"
    fi

    echo "  Renewal Status:  $RENEWAL_STATUS"
fi

echo ""

# Validation details (for pending certificates)
if [ "$STATUS" == "PENDING_VALIDATION" ]; then
    echo -e "${YELLOW}DNS Validation Records Required:${NC}"
    echo "$CERT_INFO" | jq -r '.Certificate.DomainValidationOptions[] | "  \(.DomainName):\n    CNAME Name:  \(.ResourceRecord.Name)\n    CNAME Value: \(.ResourceRecord.Value)"'
    echo ""
fi

# TLS/SSL configuration recommendations
echo -e "${BLUE}Recommended TLS Configuration:${NC}"
echo "  - TLS Policy:    ELBSecurityPolicy-TLS13-1-2-2021-06"
echo "  - Minimum TLS:   TLS 1.2"
echo "  - HSTS:          max-age=31536000; includeSubDomains"
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
if [ "$STATUS" == "ISSUED" ] && [ "$DAYS_REMAINING" -gt "$ALERT_DAYS" ]; then
    echo -e "${GREEN}  Certificate Status: HEALTHY${NC}"
elif [ "$STATUS" == "ISSUED" ] && [ "$DAYS_REMAINING" -le "$ALERT_DAYS" ]; then
    echo -e "${YELLOW}  Certificate Status: EXPIRING SOON${NC}"
elif [ "$STATUS" == "PENDING_VALIDATION" ]; then
    echo -e "${YELLOW}  Certificate Status: AWAITING VALIDATION${NC}"
else
    echo -e "${RED}  Certificate Status: ATTENTION REQUIRED${NC}"
fi
echo -e "${BLUE}========================================${NC}"

# Exit code based on status
if [ "$STATUS" == "ISSUED" ] && [ "$DAYS_REMAINING" -gt "$ALERT_DAYS" ]; then
    exit 0
elif [ "$STATUS" == "PENDING_VALIDATION" ]; then
    exit 2
else
    exit 1
fi
