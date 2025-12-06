#!/bin/bash
# Issue #163: SOC 2 Evidence Collection Automation
# Collects evidence for SOC 2 Type I audit across all Trust Services Criteria

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
EVIDENCE_DIR="${EVIDENCE_DIR:-./evidence/soc2-audit}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
AUDIT_DIR="${EVIDENCE_DIR}/${TIMESTAMP}"
AWS_REGION="${AWS_REGION:-us-east-1}"

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Collect SOC 2 audit evidence for Cloud Optimizer"
    echo ""
    echo "Options:"
    echo "  -o, --output DIR       Output directory (default: ./evidence/soc2-audit)"
    echo "  -r, --region REGION    AWS region (default: us-east-1)"
    echo "  -c, --category CAT     Collect specific category only:"
    echo "                         security, availability, confidentiality,"
    echo "                         processing-integrity, privacy, all (default)"
    echo "  --skip-aws             Skip AWS evidence collection"
    echo "  --skip-code            Skip code analysis evidence"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                     # Collect all evidence"
    echo "  $0 -c security         # Collect security evidence only"
    echo "  $0 --skip-aws          # Collect without AWS API calls"
}

# Default options
CATEGORY="all"
SKIP_AWS=false
SKIP_CODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            EVIDENCE_DIR="$2"
            AUDIT_DIR="${EVIDENCE_DIR}/${TIMESTAMP}"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -c|--category)
            CATEGORY="$2"
            shift 2
            ;;
        --skip-aws)
            SKIP_AWS=true
            shift
            ;;
        --skip-code)
            SKIP_CODE=true
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

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SOC 2 Evidence Collection${NC}"
echo -e "${BLUE}  Cloud Optimizer - $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create directory structure
mkdir -p "${AUDIT_DIR}"/{cc1-control-environment,cc2-communication,cc3-risk-assessment,cc4-monitoring,cc5-control-activities,cc6-access-controls,cc7-system-operations,cc8-change-management,cc9-risk-mitigation,a1-availability,c1-confidentiality,pi1-processing-integrity,p1-privacy}

echo -e "${YELLOW}Evidence Directory: ${AUDIT_DIR}${NC}"
echo ""

# Function to collect evidence with status
collect_evidence() {
    local category="$1"
    local description="$2"
    local output_file="$3"
    local command="$4"

    echo -n "  Collecting: $description... "
    if eval "$command" > "${AUDIT_DIR}/${output_file}" 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${YELLOW}SKIP${NC}"
        return 1
    fi
}

# ===========================================
# CC1: Control Environment
# ===========================================
collect_cc1() {
    echo -e "${BLUE}CC1: Control Environment${NC}"

    if [ "$SKIP_CODE" = false ]; then
        # Organization structure from code
        collect_evidence "cc1" "Organization structure" \
            "cc1-control-environment/organization-structure.txt" \
            "cat docs/02-architecture/ARCHITECTURE.md 2>/dev/null || echo 'Architecture doc not found'"

        # Security roles defined
        collect_evidence "cc1" "Security roles" \
            "cc1-control-environment/security-roles.txt" \
            "grep -r 'role\|Role\|ROLE' docs/ --include='*.md' 2>/dev/null | head -100 || echo 'No role definitions found'"
    fi

    # Policies directory listing
    collect_evidence "cc1" "Policy documents" \
        "cc1-control-environment/policy-documents.txt" \
        "ls -la docs/compliance/policies/ 2>/dev/null || echo 'No policies directory'"

    echo ""
}

# ===========================================
# CC2: Communication and Information
# ===========================================
collect_cc2() {
    echo -e "${BLUE}CC2: Communication and Information${NC}"

    if [ "$SKIP_CODE" = false ]; then
        # System documentation
        collect_evidence "cc2" "API documentation" \
            "cc2-communication/api-documentation.txt" \
            "ls -la docs/api/ 2>/dev/null || echo 'Checking OpenAPI spec...'; cat openapi.yaml 2>/dev/null || echo 'No OpenAPI spec found'"

        # Runbooks
        collect_evidence "cc2" "Runbooks inventory" \
            "cc2-communication/runbooks.txt" \
            "ls -la docs/runbooks/ 2>/dev/null || echo 'No runbooks directory'"
    fi

    echo ""
}

# ===========================================
# CC5: Control Activities
# ===========================================
collect_cc5() {
    echo -e "${BLUE}CC5: Control Activities${NC}"

    if [ "$SKIP_CODE" = false ]; then
        # Authentication implementation
        collect_evidence "cc5" "Authentication controls" \
            "cc5-control-activities/authentication-controls.txt" \
            "grep -r 'jwt\|JWT\|token\|Token\|auth\|Auth' src/cloud_optimizer/auth/ --include='*.py' 2>/dev/null | head -100 || echo 'Auth code not found'"

        # Encryption implementation
        collect_evidence "cc5" "Encryption controls" \
            "cc5-control-activities/encryption-controls.txt" \
            "grep -r 'encrypt\|Encrypt\|Fernet\|KMS\|kms' src/ --include='*.py' 2>/dev/null | head -100 || echo 'No encryption found'"

        # Input validation
        collect_evidence "cc5" "Input validation (Pydantic)" \
            "cc5-control-activities/input-validation.txt" \
            "ls -la src/cloud_optimizer/api/schemas/ 2>/dev/null && wc -l src/cloud_optimizer/api/schemas/*.py 2>/dev/null || echo 'No schemas'"
    fi

    # Security policies
    collect_evidence "cc5" "Security policies" \
        "cc5-control-activities/security-policies.txt" \
        "cat docs/compliance/policies/INFORMATION_SECURITY_POLICY.md 2>/dev/null | head -200 || echo 'No security policy'"

    echo ""
}

# ===========================================
# CC6: Logical and Physical Access Controls
# ===========================================
collect_cc6() {
    echo -e "${BLUE}CC6: Logical and Physical Access Controls${NC}"

    if [ "$SKIP_AWS" = false ]; then
        # IAM policies
        collect_evidence "cc6" "IAM policies" \
            "cc6-access-controls/iam-policies.json" \
            "aws iam list-policies --scope Local --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"

        # IAM users
        collect_evidence "cc6" "IAM users" \
            "cc6-access-controls/iam-users.json" \
            "aws iam list-users --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"

        # MFA status
        collect_evidence "cc6" "MFA devices" \
            "cc6-access-controls/mfa-devices.json" \
            "aws iam list-virtual-mfa-devices --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"

        # Security groups
        collect_evidence "cc6" "Security groups" \
            "cc6-access-controls/security-groups.json" \
            "aws ec2 describe-security-groups --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"
    fi

    if [ "$SKIP_CODE" = false ]; then
        # Access control policy
        collect_evidence "cc6" "Access control policy" \
            "cc6-access-controls/access-control-policy.txt" \
            "cat docs/compliance/policies/ACCESS_CONTROL_POLICY.md 2>/dev/null | head -200 || echo 'No access control policy'"

        # JWT configuration
        collect_evidence "cc6" "JWT configuration" \
            "cc6-access-controls/jwt-configuration.txt" \
            "grep -E 'ACCESS_TOKEN|REFRESH_TOKEN|EXPIR' src/cloud_optimizer/auth/jwt.py 2>/dev/null || echo 'No JWT config found'"
    fi

    echo ""
}

# ===========================================
# CC7: System Operations
# ===========================================
collect_cc7() {
    echo -e "${BLUE}CC7: System Operations${NC}"

    if [ "$SKIP_AWS" = false ]; then
        # CloudWatch alarms
        collect_evidence "cc7" "CloudWatch alarms" \
            "cc7-system-operations/cloudwatch-alarms.json" \
            "aws cloudwatch describe-alarms --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"

        # CloudTrail status
        collect_evidence "cc7" "CloudTrail trails" \
            "cc7-system-operations/cloudtrail-trails.json" \
            "aws cloudtrail describe-trails --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"

        # Log groups
        collect_evidence "cc7" "CloudWatch log groups" \
            "cc7-system-operations/log-groups.json" \
            "aws logs describe-log-groups --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"
    fi

    if [ "$SKIP_CODE" = false ]; then
        # Logging configuration
        collect_evidence "cc7" "Logging configuration" \
            "cc7-system-operations/logging-config.txt" \
            "ls -la src/cloud_optimizer/logging/ 2>/dev/null && head -100 src/cloud_optimizer/logging/*.py 2>/dev/null || echo 'No logging module'"

        # Incident response procedures
        collect_evidence "cc7" "Incident response" \
            "cc7-system-operations/incident-response.txt" \
            "cat docs/compliance/policies/INCIDENT_RESPONSE_POLICY.md 2>/dev/null | head -200 || echo 'No incident response policy'"

        # Runbooks
        collect_evidence "cc7" "Operational runbooks" \
            "cc7-system-operations/runbooks-list.txt" \
            "find docs/runbooks -name '*.md' -exec basename {} \; 2>/dev/null || echo 'No runbooks found'"
    fi

    echo ""
}

# ===========================================
# CC8: Change Management
# ===========================================
collect_cc8() {
    echo -e "${BLUE}CC8: Change Management${NC}"

    if [ "$SKIP_CODE" = false ]; then
        # Git log (recent changes)
        collect_evidence "cc8" "Recent commits (30 days)" \
            "cc8-change-management/recent-commits.txt" \
            "git log --oneline --since='30 days ago' --no-decorate 2>/dev/null | head -100 || echo 'Not a git repo'"

        # CI/CD configuration
        collect_evidence "cc8" "CI/CD configuration" \
            "cc8-change-management/cicd-config.txt" \
            "cat .github/workflows/*.yml 2>/dev/null | head -200 || echo 'No GitHub Actions workflows'"

        # Pre-commit hooks
        collect_evidence "cc8" "Pre-commit hooks" \
            "cc8-change-management/pre-commit-config.txt" \
            "cat .pre-commit-config.yaml 2>/dev/null || echo 'No pre-commit config'"

        # Change management policy
        collect_evidence "cc8" "Change management policy" \
            "cc8-change-management/change-management-policy.txt" \
            "cat docs/compliance/policies/CHANGE_MANAGEMENT_POLICY.md 2>/dev/null | head -200 || echo 'No change management policy'"

        # Infrastructure as Code
        collect_evidence "cc8" "CloudFormation templates" \
            "cc8-change-management/cloudformation-inventory.txt" \
            "ls -la cloudformation/*.yaml 2>/dev/null || echo 'No CloudFormation templates'"

        # Docker images
        collect_evidence "cc8" "Container images" \
            "cc8-change-management/docker-images.txt" \
            "cat docker/Dockerfile 2>/dev/null | head -50 || echo 'No Dockerfile'"
    fi

    echo ""
}

# ===========================================
# A1: Availability
# ===========================================
collect_a1() {
    echo -e "${BLUE}A1: Availability${NC}"

    if [ "$SKIP_AWS" = false ]; then
        # RDS instances
        collect_evidence "a1" "RDS instances" \
            "a1-availability/rds-instances.json" \
            "aws rds describe-db-instances --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"

        # RDS automated backups
        collect_evidence "a1" "RDS backups" \
            "a1-availability/rds-backups.json" \
            "aws rds describe-db-snapshots --region $AWS_REGION --output json 2>/dev/null | head -200 || echo '{\"message\": \"AWS access not available\"}'"

        # Load balancers
        collect_evidence "a1" "Load balancers" \
            "a1-availability/load-balancers.json" \
            "aws elbv2 describe-load-balancers --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"

        # Auto Scaling groups
        collect_evidence "a1" "Auto Scaling groups" \
            "a1-availability/autoscaling-groups.json" \
            "aws autoscaling describe-auto-scaling-groups --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"

        # ECS services
        collect_evidence "a1" "ECS services" \
            "a1-availability/ecs-services.json" \
            "aws ecs list-clusters --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"
    fi

    if [ "$SKIP_CODE" = false ]; then
        # Health check endpoints
        collect_evidence "a1" "Health check endpoints" \
            "a1-availability/health-endpoints.txt" \
            "grep -r 'health\|Health\|/health' src/cloud_optimizer/api/ --include='*.py' 2>/dev/null | head -50 || echo 'No health endpoints found'"

        # Kubernetes deployment config
        collect_evidence "a1" "Kubernetes deployment" \
            "a1-availability/k8s-deployment.txt" \
            "cat helm/cloud-optimizer/templates/deployment.yaml 2>/dev/null | head -100 || echo 'No Helm deployment'"

        # DR/BCP documentation
        collect_evidence "a1" "DR/BCP documentation" \
            "a1-availability/dr-bcp-docs.txt" \
            "cat docs/compliance/BUSINESS_CONTINUITY_PLAN.md 2>/dev/null | head -200 || echo 'No BCP document'"
    fi

    echo ""
}

# ===========================================
# C1: Confidentiality
# ===========================================
collect_c1() {
    echo -e "${BLUE}C1: Confidentiality${NC}"

    if [ "$SKIP_AWS" = false ]; then
        # KMS keys
        collect_evidence "c1" "KMS keys" \
            "c1-confidentiality/kms-keys.json" \
            "aws kms list-keys --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"

        # Secrets Manager secrets (names only)
        collect_evidence "c1" "Secrets Manager inventory" \
            "c1-confidentiality/secrets-inventory.json" \
            "aws secretsmanager list-secrets --region $AWS_REGION --output json 2>/dev/null || echo '{\"message\": \"AWS access not available\"}'"
    fi

    if [ "$SKIP_CODE" = false ]; then
        # PII filter configuration
        collect_evidence "c1" "PII filter configuration" \
            "c1-confidentiality/pii-filter.txt" \
            "cat src/cloud_optimizer/logging/pii_filter.py 2>/dev/null | head -150 || echo 'No PII filter'"

        # Data classification policy
        collect_evidence "c1" "Data classification policy" \
            "c1-confidentiality/data-classification-policy.txt" \
            "cat docs/compliance/policies/DATA_CLASSIFICATION_POLICY.md 2>/dev/null | head -200 || echo 'No data classification policy'"

        # Data retention policy
        collect_evidence "c1" "Data retention policy" \
            "c1-confidentiality/data-retention-policy.txt" \
            "cat docs/compliance/policies/DATA_RETENTION_POLICY.md 2>/dev/null | head -200 || echo 'No data retention policy'"
    fi

    echo ""
}

# ===========================================
# PI1: Processing Integrity
# ===========================================
collect_pi1() {
    echo -e "${BLUE}PI1: Processing Integrity${NC}"

    if [ "$SKIP_CODE" = false ]; then
        # Pydantic schemas
        collect_evidence "pi1" "Pydantic schemas" \
            "pi1-processing-integrity/pydantic-schemas.txt" \
            "ls -la src/cloud_optimizer/api/schemas/*.py 2>/dev/null && wc -l src/cloud_optimizer/api/schemas/*.py || echo 'No schemas'"

        # Type checking config
        collect_evidence "pi1" "Type checking (mypy)" \
            "pi1-processing-integrity/mypy-config.txt" \
            "cat pyproject.toml 2>/dev/null | grep -A 20 '\[tool.mypy\]' || echo 'No mypy config'"

        # Test coverage
        collect_evidence "pi1" "Test coverage" \
            "pi1-processing-integrity/test-coverage.txt" \
            "cat coverage.xml 2>/dev/null | head -50 || pytest --cov=src --cov-report=term-missing --no-header -q 2>/dev/null | tail -20 || echo 'No coverage report'"

        # CI quality gates
        collect_evidence "pi1" "CI quality gates" \
            "pi1-processing-integrity/ci-quality-gates.txt" \
            "grep -E 'coverage|lint|test|quality' .github/workflows/*.yml 2>/dev/null || echo 'No CI quality gates'"
    fi

    echo ""
}

# ===========================================
# P1: Privacy
# ===========================================
collect_p1() {
    echo -e "${BLUE}P1: Privacy${NC}"

    if [ "$SKIP_CODE" = false ]; then
        # Privacy notice/policy
        collect_evidence "p1" "Privacy policy" \
            "p1-privacy/privacy-policy.txt" \
            "cat docs/compliance/PRIVACY_POLICY.md 2>/dev/null | head -200 || echo 'No privacy policy document'"

        # Data processing activities
        collect_evidence "p1" "Data processing log" \
            "p1-privacy/data-processing.txt" \
            "grep -r 'personal\|PII\|user_data\|email\|phone' src/cloud_optimizer/ --include='*.py' 2>/dev/null | head -50 || echo 'No data processing found'"

        # GDPR compliance
        collect_evidence "p1" "GDPR controls" \
            "p1-privacy/gdpr-controls.txt" \
            "cat data/compliance/frameworks/gdpr/controls.yaml 2>/dev/null | head -100 || echo 'No GDPR controls'"
    fi

    echo ""
}

# ===========================================
# Generate Summary Report
# ===========================================
generate_summary() {
    echo -e "${BLUE}Generating Summary Report${NC}"

    cat > "${AUDIT_DIR}/EVIDENCE_SUMMARY.md" << EOF
# SOC 2 Type I Evidence Collection Summary

**Collection Date:** $(date '+%Y-%m-%d %H:%M:%S')
**Audit Period:** $(date -v-1y '+%Y-%m-%d' 2>/dev/null || date -d '1 year ago' '+%Y-%m-%d' 2>/dev/null || echo 'N/A') to $(date '+%Y-%m-%d')
**AWS Region:** ${AWS_REGION}

## Evidence Categories Collected

### Common Criteria (CC)
- CC1: Control Environment - $(ls -1 ${AUDIT_DIR}/cc1-control-environment/ 2>/dev/null | wc -l) files
- CC2: Communication and Information - $(ls -1 ${AUDIT_DIR}/cc2-communication/ 2>/dev/null | wc -l) files
- CC3: Risk Assessment - $(ls -1 ${AUDIT_DIR}/cc3-risk-assessment/ 2>/dev/null | wc -l) files
- CC4: Monitoring Activities - $(ls -1 ${AUDIT_DIR}/cc4-monitoring/ 2>/dev/null | wc -l) files
- CC5: Control Activities - $(ls -1 ${AUDIT_DIR}/cc5-control-activities/ 2>/dev/null | wc -l) files
- CC6: Logical and Physical Access - $(ls -1 ${AUDIT_DIR}/cc6-access-controls/ 2>/dev/null | wc -l) files
- CC7: System Operations - $(ls -1 ${AUDIT_DIR}/cc7-system-operations/ 2>/dev/null | wc -l) files
- CC8: Change Management - $(ls -1 ${AUDIT_DIR}/cc8-change-management/ 2>/dev/null | wc -l) files
- CC9: Risk Mitigation - $(ls -1 ${AUDIT_DIR}/cc9-risk-mitigation/ 2>/dev/null | wc -l) files

### Trust Services Criteria
- A1: Availability - $(ls -1 ${AUDIT_DIR}/a1-availability/ 2>/dev/null | wc -l) files
- C1: Confidentiality - $(ls -1 ${AUDIT_DIR}/c1-confidentiality/ 2>/dev/null | wc -l) files
- PI1: Processing Integrity - $(ls -1 ${AUDIT_DIR}/pi1-processing-integrity/ 2>/dev/null | wc -l) files
- P1: Privacy - $(ls -1 ${AUDIT_DIR}/p1-privacy/ 2>/dev/null | wc -l) files

## Collection Configuration

- AWS Evidence: $([ "$SKIP_AWS" = true ] && echo "Skipped" || echo "Collected")
- Code Analysis: $([ "$SKIP_CODE" = true ] && echo "Skipped" || echo "Collected")
- Category Filter: ${CATEGORY}

## Next Steps

1. Review collected evidence for completeness
2. Verify all AWS resources are documented
3. Ensure policy documents are current
4. Schedule internal audit review
5. Prepare for external SOC 2 auditor

---

*Generated by Cloud Optimizer SOC 2 Evidence Collection Tool*
EOF

    echo -e "${GREEN}Summary report generated${NC}"
}

# ===========================================
# Main Execution
# ===========================================

case $CATEGORY in
    all)
        collect_cc1
        collect_cc2
        collect_cc5
        collect_cc6
        collect_cc7
        collect_cc8
        collect_a1
        collect_c1
        collect_pi1
        collect_p1
        ;;
    security)
        collect_cc1
        collect_cc5
        collect_cc6
        collect_cc7
        collect_cc8
        ;;
    availability)
        collect_a1
        ;;
    confidentiality)
        collect_c1
        ;;
    processing-integrity)
        collect_pi1
        ;;
    privacy)
        collect_p1
        ;;
    *)
        echo -e "${RED}Unknown category: $CATEGORY${NC}"
        usage
        exit 1
        ;;
esac

generate_summary

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  Evidence Collection Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Evidence saved to: ${GREEN}${AUDIT_DIR}${NC}"
echo ""
echo "Total files collected: $(find ${AUDIT_DIR} -type f | wc -l | tr -d ' ')"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Review evidence in ${AUDIT_DIR}"
echo "2. Verify AWS evidence (if collected)"
echo "3. Update SOC 2 readiness checklist"
echo "4. Schedule internal audit review"
