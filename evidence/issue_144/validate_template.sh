#!/bin/bash
set -e

# ElastiCache Redis CloudFormation Template Validation Script
# Issue #144 - Cloud Optimizer

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_PATH="${SCRIPT_DIR}/../../cloudformation/elasticache-redis.yaml"

echo "========================================="
echo "ElastiCache Redis Template Validation"
echo "========================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ ERROR: AWS CLI is not installed"
    echo "   Install from: https://aws.amazon.com/cli/"
    exit 1
fi
echo "✅ AWS CLI is installed"

# Check if template file exists
if [ ! -f "$TEMPLATE_PATH" ]; then
    echo "❌ ERROR: Template file not found at: $TEMPLATE_PATH"
    exit 1
fi
echo "✅ Template file exists: $TEMPLATE_PATH"

# Count template lines
LINE_COUNT=$(wc -l < "$TEMPLATE_PATH" | tr -d ' ')
echo "✅ Template size: $LINE_COUNT lines"

echo ""
echo "Running AWS CloudFormation template validation..."
echo "-------------------------------------------------"

# Validate the template
if aws cloudformation validate-template --template-body "file://$TEMPLATE_PATH" > /tmp/cf_validation_output.json 2>&1; then
    echo "✅ CloudFormation template validation PASSED"
    echo ""

    # Extract and display parameters
    PARAM_COUNT=$(jq '.Parameters | length' /tmp/cf_validation_output.json)
    echo "Template Parameters: $PARAM_COUNT"
    echo ""

    # Display parameter details
    jq -r '.Parameters[] | "  - \(.ParameterKey) (\(.DefaultValue // "required"))"' /tmp/cf_validation_output.json
    echo ""

    # Display description
    DESCRIPTION=$(jq -r '.Description' /tmp/cf_validation_output.json)
    echo "Template Description:"
    echo "$DESCRIPTION" | fold -w 70 -s | sed 's/^/  /'
    echo ""

    echo "========================================="
    echo "✅ VALIDATION SUCCESSFUL"
    echo "========================================="
    echo ""
    echo "Next Steps:"
    echo "1. Review deployment_example.json for deployment examples"
    echo "2. Customize parameters for your environment"
    echo "3. Deploy using AWS CLI or AWS Console"
    echo ""
    echo "Example deployment command:"
    echo "  aws cloudformation create-stack \\"
    echo "    --stack-name cloud-optimizer-dev-redis \\"
    echo "    --template-body file://$TEMPLATE_PATH \\"
    echo "    --parameters \\"
    echo "      ParameterKey=Environment,ParameterValue=development \\"
    echo "      ParameterKey=VpcId,ParameterValue=vpc-xxxxx \\"
    echo "      ParameterKey=PrivateSubnetIds,ParameterValue='subnet-xxxxx,subnet-yyyyy' \\"
    echo "      ParameterKey=ECSSecurityGroupId,ParameterValue=sg-xxxxx"
    echo ""

    exit 0
else
    echo "❌ CloudFormation template validation FAILED"
    echo ""
    echo "Error details:"
    cat /tmp/cf_validation_output.json
    echo ""

    echo "========================================="
    echo "❌ VALIDATION FAILED"
    echo "========================================="
    exit 1
fi
