#!/bin/bash
# Internal Security Audit Script - Issue #162
# Comprehensive security audit before penetration testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Output directory
AUDIT_DIR="./security-audit-$(date +%Y%m%d-%H%M%S)"
REPORT_FILE="$AUDIT_DIR/audit-report.md"

log_header() { echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"; }
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; ((PASSED++)); echo "- [x] $1" >> "$REPORT_FILE"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; ((FAILED++)); echo "- [ ] **FAIL:** $1" >> "$REPORT_FILE"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; ((WARNINGS++)); echo "- [ ] *WARN:* $1" >> "$REPORT_FILE"; }
log_skip() { echo -e "${YELLOW}[SKIP]${NC} $1"; }

# Initialize report
init_report() {
    mkdir -p "$AUDIT_DIR"
    cat > "$REPORT_FILE" << EOF
# Security Audit Report

**Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Project:** Cloud Optimizer
**Issue:** #162 - Penetration Testing Preparation

---

EOF
}

# Check if command exists
check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# 1. Dependency Vulnerability Scanning
check_dependencies() {
    log_header "1. DEPENDENCY VULNERABILITY SCAN"
    echo -e "\n## 1. Dependency Vulnerabilities\n" >> "$REPORT_FILE"

    # Python dependencies
    log_info "Checking Python dependencies..."
    if check_command pip-audit; then
        if pip-audit --desc --strict 2>/dev/null; then
            log_pass "No critical Python vulnerabilities found"
        else
            log_fail "Python dependency vulnerabilities detected"
        fi
    elif check_command safety; then
        if safety check -r requirements.txt 2>/dev/null; then
            log_pass "No critical Python vulnerabilities found (safety)"
        else
            log_fail "Python dependency vulnerabilities detected (safety)"
        fi
    else
        log_warn "pip-audit/safety not installed - using pip check"
        if pip check 2>/dev/null; then
            log_pass "Python dependencies consistent"
        else
            log_fail "Python dependency issues found"
        fi
    fi

    # Check for outdated packages
    log_info "Checking for outdated packages..."
    OUTDATED=$(pip list --outdated 2>/dev/null | wc -l)
    if [ "$OUTDATED" -lt 5 ]; then
        log_pass "Few outdated packages ($OUTDATED)"
    else
        log_warn "$OUTDATED outdated packages found"
    fi

    # Frontend dependencies (if exists)
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        log_info "Checking JavaScript dependencies..."
        cd frontend
        if check_command npm; then
            AUDIT_RESULT=$(npm audit --json 2>/dev/null || echo '{"vulnerabilities":{}}')
            CRITICAL=$(echo "$AUDIT_RESULT" | grep -c '"severity":"critical"' || echo "0")
            HIGH=$(echo "$AUDIT_RESULT" | grep -c '"severity":"high"' || echo "0")
            if [ "$CRITICAL" -eq 0 ] && [ "$HIGH" -eq 0 ]; then
                log_pass "No critical/high npm vulnerabilities"
            else
                log_fail "npm vulnerabilities: $CRITICAL critical, $HIGH high"
            fi
        fi
        cd ..
    fi
}

# 2. Secret Detection
check_secrets() {
    log_header "2. SECRET DETECTION"
    echo -e "\n## 2. Secret Detection\n" >> "$REPORT_FILE"

    log_info "Scanning for hardcoded secrets..."

    # Check for common secret patterns
    PATTERNS=(
        "password\s*=\s*['\"][^'\"]+['\"]"
        "api[_-]?key\s*=\s*['\"][^'\"]+['\"]"
        "secret[_-]?key\s*=\s*['\"][^'\"]+['\"]"
        "aws[_-]?access[_-]?key[_-]?id\s*=\s*['\"][A-Z0-9]{20}['\"]"
        "aws[_-]?secret[_-]?access[_-]?key\s*=\s*['\"][^'\"]{40}['\"]"
        "AKIA[0-9A-Z]{16}"
        "ghp_[a-zA-Z0-9]{36}"
        "-----BEGIN.*PRIVATE KEY-----"
    )

    SECRETS_FOUND=0
    for pattern in "${PATTERNS[@]}"; do
        MATCHES=$(grep -rIE "$pattern" --include="*.py" --include="*.js" --include="*.ts" --include="*.yaml" --include="*.yml" --include="*.json" --include="*.env*" src/ frontend/src/ 2>/dev/null | grep -v "test" | grep -v "__pycache__" | wc -l || echo "0")
        if [ "$MATCHES" -gt 0 ]; then
            ((SECRETS_FOUND+=MATCHES))
        fi
    done

    if [ "$SECRETS_FOUND" -eq 0 ]; then
        log_pass "No hardcoded secrets detected"
    else
        log_fail "Potential hardcoded secrets found: $SECRETS_FOUND occurrences"
    fi

    # Check .env files not in gitignore
    if [ -f ".env" ] && ! grep -q "^\.env$" .gitignore 2>/dev/null; then
        log_fail ".env file exists but not in .gitignore"
    else
        log_pass ".env properly ignored"
    fi

    # Check for .env.example without real values
    if [ -f ".env.example" ]; then
        if grep -qE "=['\"]?[^'\"\$\{]+" .env.example 2>/dev/null; then
            log_warn ".env.example may contain real values"
        else
            log_pass ".env.example contains only placeholders"
        fi
    fi
}

# 3. Security Headers Check
check_security_headers() {
    log_header "3. SECURITY HEADERS"
    echo -e "\n## 3. Security Headers\n" >> "$REPORT_FILE"

    # Check if middleware is configured
    if grep -rq "SecurityHeadersMiddleware\|security_headers" src/ 2>/dev/null; then
        log_pass "Security headers middleware configured"
    else
        log_fail "Security headers middleware not found"
    fi

    # Check HSTS configuration
    if grep -rq "Strict-Transport-Security" src/ 2>/dev/null; then
        log_pass "HSTS header configured"
    else
        log_warn "HSTS header not found in code"
    fi

    # Check CSP configuration
    if grep -rq "Content-Security-Policy" src/ 2>/dev/null; then
        log_pass "CSP header configured"
    else
        log_warn "CSP header not found in code"
    fi

    # Check X-Frame-Options
    if grep -rq "X-Frame-Options" src/ 2>/dev/null; then
        log_pass "X-Frame-Options configured"
    else
        log_warn "X-Frame-Options not found"
    fi
}

# 4. Authentication & Authorization
check_auth() {
    log_header "4. AUTHENTICATION & AUTHORIZATION"
    echo -e "\n## 4. Authentication & Authorization\n" >> "$REPORT_FILE"

    # Check JWT configuration
    if grep -rq "JWT\|jwt\|JsonWebToken" src/ 2>/dev/null; then
        log_pass "JWT authentication implemented"

        # Check for short expiry
        if grep -rqE "expire.*=.*[0-9]+" src/ 2>/dev/null; then
            log_pass "Token expiration configured"
        else
            log_warn "Token expiration not clearly configured"
        fi
    else
        log_warn "JWT authentication not found"
    fi

    # Check password hashing
    if grep -rq "bcrypt\|argon2\|scrypt\|pbkdf2" src/ 2>/dev/null; then
        log_pass "Strong password hashing in use"
    else
        log_fail "No strong password hashing found"
    fi

    # Check for authorization decorators
    if grep -rqE "@requires_auth|@login_required|Depends.*get_current_user|verify_token" src/ 2>/dev/null; then
        log_pass "Authorization checks implemented"
    else
        log_warn "Authorization decorators not clearly found"
    fi

    # Check for RBAC
    if grep -rq "role\|permission\|RBAC\|roles" src/ 2>/dev/null; then
        log_pass "Role-based access control implemented"
    else
        log_warn "RBAC not clearly implemented"
    fi
}

# 5. Input Validation
check_input_validation() {
    log_header "5. INPUT VALIDATION"
    echo -e "\n## 5. Input Validation\n" >> "$REPORT_FILE"

    # Check for Pydantic models
    if grep -rq "BaseModel\|pydantic" src/ 2>/dev/null; then
        log_pass "Pydantic validation in use"
    else
        log_warn "Pydantic validation not found"
    fi

    # Check for SQL injection prevention
    if grep -rqE "execute\(['\"][^%f]*%|execute\(f['\"]" src/ 2>/dev/null; then
        log_fail "Potential SQL injection (string formatting in queries)"
    else
        log_pass "No obvious SQL injection patterns"
    fi

    # Check for parameterized queries
    if grep -rqE "execute.*\?|execute.*%s|\$[0-9]" src/ 2>/dev/null; then
        log_pass "Parameterized queries in use"
    fi

    # Check for XSS prevention in templates
    if grep -rq "Markup\|safe\|autoescape" src/ 2>/dev/null; then
        log_warn "Check template autoescaping is enabled"
    fi
}

# 6. API Security
check_api_security() {
    log_header "6. API SECURITY"
    echo -e "\n## 6. API Security\n" >> "$REPORT_FILE"

    # Check for rate limiting
    if grep -rq "ratelimit\|rate_limit\|throttle\|slowapi" src/ 2>/dev/null; then
        log_pass "Rate limiting implemented"
    else
        log_fail "Rate limiting not found"
    fi

    # Check CORS configuration
    if grep -rq "CORSMiddleware\|cors" src/ 2>/dev/null; then
        log_pass "CORS middleware configured"
        if grep -rq "allow_origins.*\*" src/ 2>/dev/null; then
            log_fail "CORS allows all origins (*)"
        else
            log_pass "CORS properly restricted"
        fi
    else
        log_warn "CORS configuration not found"
    fi

    # Check for API versioning
    if grep -rq "/api/v[0-9]\|/v[0-9]/" src/ 2>/dev/null; then
        log_pass "API versioning in use"
    else
        log_warn "API versioning not clearly defined"
    fi
}

# 7. Logging & Monitoring
check_logging() {
    log_header "7. LOGGING & MONITORING"
    echo -e "\n## 7. Logging & Monitoring\n" >> "$REPORT_FILE"

    # Check for structured logging
    if grep -rq "logging\|logger\|structlog" src/ 2>/dev/null; then
        log_pass "Logging implemented"
    else
        log_fail "Logging not properly implemented"
    fi

    # Check for audit logging
    if grep -rq "audit\|AuditLog" src/ 2>/dev/null; then
        log_pass "Audit logging implemented"
    else
        log_warn "Audit logging not clearly implemented"
    fi

    # Check for sensitive data in logs
    if grep -rqE "log.*password|log.*secret|log.*token|log.*key" src/ 2>/dev/null; then
        log_warn "Potential sensitive data logging"
    else
        log_pass "No obvious sensitive data logging"
    fi
}

# 8. Error Handling
check_error_handling() {
    log_header "8. ERROR HANDLING"
    echo -e "\n## 8. Error Handling\n" >> "$REPORT_FILE"

    # Check for exception handlers
    if grep -rq "exception_handler\|HTTPException\|@app.exception" src/ 2>/dev/null; then
        log_pass "Exception handlers configured"
    else
        log_warn "Exception handlers not clearly configured"
    fi

    # Check for stack traces in production
    if grep -rq "debug.*=.*True\|DEBUG.*=.*True" src/ 2>/dev/null; then
        log_warn "Debug mode may be enabled - verify production settings"
    else
        log_pass "Debug mode not hardcoded"
    fi

    # Check for generic error messages
    if grep -rq "HTTPException.*detail" src/ 2>/dev/null; then
        log_pass "Custom error messages in use"
    fi
}

# 9. Docker Security
check_docker_security() {
    log_header "9. DOCKER SECURITY"
    echo -e "\n## 9. Docker Security\n" >> "$REPORT_FILE"

    if [ -f "docker/Dockerfile" ] || [ -f "Dockerfile" ]; then
        DOCKERFILE=$([ -f "docker/Dockerfile" ] && echo "docker/Dockerfile" || echo "Dockerfile")

        # Check for non-root user
        if grep -q "USER\|--chown" "$DOCKERFILE" 2>/dev/null; then
            log_pass "Non-root user configured in Dockerfile"
        else
            log_fail "Container may run as root"
        fi

        # Check for pinned base image
        if grep -qE "FROM.*:[0-9]+\.[0-9]+|FROM.*@sha256:" "$DOCKERFILE" 2>/dev/null; then
            log_pass "Base image version pinned"
        else
            log_warn "Base image should be pinned to specific version"
        fi

        # Check for COPY vs ADD
        if grep -q "^ADD " "$DOCKERFILE" 2>/dev/null; then
            log_warn "Using ADD instead of COPY - review necessity"
        else
            log_pass "Using COPY instead of ADD"
        fi

        # Check for .dockerignore
        if [ -f ".dockerignore" ]; then
            log_pass ".dockerignore exists"
        else
            log_warn ".dockerignore not found"
        fi
    else
        log_skip "No Dockerfile found"
    fi
}

# 10. Infrastructure Security
check_infrastructure() {
    log_header "10. INFRASTRUCTURE SECURITY"
    echo -e "\n## 10. Infrastructure Security\n" >> "$REPORT_FILE"

    # Check CloudFormation templates
    if ls cloudformation/*.yaml 1> /dev/null 2>&1; then
        # Check for encrypted storage
        if grep -rq "StorageEncrypted.*true\|Encrypted.*true" cloudformation/ 2>/dev/null; then
            log_pass "Encryption enabled in CloudFormation"
        else
            log_warn "Check encryption settings in CloudFormation"
        fi

        # Check for security groups
        if grep -rq "0\.0\.0\.0/0.*22\|0\.0\.0\.0/0.*3389" cloudformation/ 2>/dev/null; then
            log_fail "SSH/RDP open to world in CloudFormation"
        else
            log_pass "No world-open SSH/RDP in CloudFormation"
        fi
    fi

    # Check Helm charts
    if [ -d "helm" ]; then
        # Check for security context
        if grep -rq "securityContext\|runAsNonRoot" helm/ 2>/dev/null; then
            log_pass "Security context configured in Helm"
        else
            log_warn "Security context not found in Helm charts"
        fi
    fi
}

# Generate Summary
generate_summary() {
    log_header "AUDIT SUMMARY"

    TOTAL=$((PASSED + FAILED + WARNINGS))

    cat >> "$REPORT_FILE" << EOF

---

## Summary

| Status | Count |
|--------|-------|
| Passed | $PASSED |
| Failed | $FAILED |
| Warnings | $WARNINGS |
| Total | $TOTAL |

### Overall Score: $((PASSED * 100 / TOTAL))%

---

*Generated by security-audit.sh - Issue #162*
EOF

    echo ""
    echo -e "  ${GREEN}Passed:   $PASSED${NC}"
    echo -e "  ${RED}Failed:   $FAILED${NC}"
    echo -e "  ${YELLOW}Warnings: $WARNINGS${NC}"
    echo ""
    echo -e "  Overall Score: ${CYAN}$((PASSED * 100 / TOTAL))%${NC}"
    echo ""
    echo -e "  Report saved to: ${BLUE}$REPORT_FILE${NC}"
    echo ""

    if [ "$FAILED" -gt 0 ]; then
        echo -e "${RED}ACTION REQUIRED: Fix $FAILED critical issues before penetration testing${NC}"
        exit 1
    elif [ "$WARNINGS" -gt 5 ]; then
        echo -e "${YELLOW}REVIEW RECOMMENDED: $WARNINGS warnings found${NC}"
        exit 0
    else
        echo -e "${GREEN}READY: Application appears ready for penetration testing${NC}"
        exit 0
    fi
}

# Main execution
main() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║       CLOUD OPTIMIZER - INTERNAL SECURITY AUDIT               ║${NC}"
    echo -e "${CYAN}║       Issue #162 - Penetration Testing Preparation            ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    init_report

    check_dependencies
    check_secrets
    check_security_headers
    check_auth
    check_input_validation
    check_api_security
    check_logging
    check_error_handling
    check_docker_security
    check_infrastructure

    generate_summary
}

# Run main
main "$@"
