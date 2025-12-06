#!/usr/bin/env bash
#
# E2E Test Setup Verification Script
#
# This script verifies that all E2E test components are properly installed
# and configured. Run this before attempting to run E2E tests.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Counters
PASSED=0
FAILED=0
WARNINGS=0

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_check() {
    echo -n "Checking $1... "
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED + 1))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC}"
    if [ -n "$1" ]; then
        echo -e "  ${RED}→ $1${NC}"
    fi
    FAILED=$((FAILED + 1))
}

print_warning() {
    echo -e "${YELLOW}⚠ WARNING${NC}"
    if [ -n "$1" ]; then
        echo -e "  ${YELLOW}→ $1${NC}"
    fi
    WARNINGS=$((WARNINGS + 1))
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

print_header "E2E Test Setup Verification"

# Check required files
print_header "Checking Required Files"

print_check "conftest.py"
if [ -f "$SCRIPT_DIR/conftest.py" ]; then
    print_pass
else
    print_fail "Missing conftest.py"
fi

print_check "test_e2e_smoke.py"
if [ -f "$SCRIPT_DIR/test_e2e_smoke.py" ]; then
    print_pass
else
    print_fail "Missing test_e2e_smoke.py"
fi

print_check "run_e2e_tests.sh"
if [ -f "$SCRIPT_DIR/run_e2e_tests.sh" ]; then
    if [ -x "$SCRIPT_DIR/run_e2e_tests.sh" ]; then
        print_pass
    else
        print_fail "run_e2e_tests.sh not executable (run: chmod +x tests/e2e/run_e2e_tests.sh)"
    fi
else
    print_fail "Missing run_e2e_tests.sh"
fi

print_check "docker-compose.e2e.yml"
if [ -f "$PROJECT_ROOT/docker/docker-compose.e2e.yml" ]; then
    print_pass
else
    print_fail "Missing docker/docker-compose.e2e.yml"
fi

# Check prerequisites
print_header "Checking Prerequisites"

print_check "Docker installed"
if command_exists docker; then
    print_pass
    echo -e "  ${BLUE}→ Version: $(docker --version)${NC}"
else
    print_fail "Docker not found. Install from https://docker.com"
fi

print_check "Docker daemon running"
if docker info >/dev/null 2>&1; then
    print_pass
else
    print_fail "Docker daemon not running. Start Docker Desktop or systemctl start docker"
fi

print_check "docker-compose installed"
if command_exists docker-compose; then
    print_pass
    echo -e "  ${BLUE}→ Version: $(docker-compose --version)${NC}"
else
    print_fail "docker-compose not found. Install from https://docs.docker.com/compose/"
fi

print_check "Python installed"
if command_exists python; then
    print_pass
    echo -e "  ${BLUE}→ Version: $(python --version)${NC}"
else
    print_fail "Python not found. Install Python 3.11+"
fi

print_check "pytest installed"
if python -m pytest --version >/dev/null 2>&1; then
    print_pass
    echo -e "  ${BLUE}→ Version: $(python -m pytest --version)${NC}"
else
    print_fail "pytest not found. Install with: pip install -e '.[test]'"
fi

# Check Python dependencies
print_header "Checking Python Dependencies"

check_python_package() {
    package=$1
    if python -c "import $package" 2>/dev/null; then
        print_pass
    else
        print_fail "Install with: pip install $package"
    fi
}

print_check "httpx"
check_python_package "httpx"

print_check "docker (Python SDK)"
check_python_package "docker"

print_check "boto3"
check_python_package "boto3"

print_check "sqlalchemy"
check_python_package "sqlalchemy"

print_check "asyncpg"
check_python_package "asyncpg"

print_check "pytest-asyncio"
if python -c "import pytest_asyncio" 2>/dev/null; then
    print_pass
else
    print_warning "pytest-asyncio recommended but not required"
fi

# Check pytest configuration
print_header "Checking Pytest Configuration"

print_check "E2E marker configured"
if grep -q "e2e: End-to-end tests" "$PROJECT_ROOT/pyproject.toml" 2>/dev/null; then
    print_pass
else
    print_warning "E2E marker not found in pyproject.toml (tests will still work)"
fi

print_check "Test discovery"
cd "$PROJECT_ROOT"
num_tests=$(python -m pytest tests/e2e/ --collect-only -q 2>/dev/null | grep "test_" | wc -l || echo "0")
if [ "$num_tests" -gt 0 ]; then
    print_pass
    echo -e "  ${BLUE}→ Discovered $num_tests E2E tests${NC}"
else
    print_fail "No tests discovered. Check test file syntax"
fi

# Check docker-compose configuration
print_header "Checking Docker Compose Configuration"

print_check "docker-compose.e2e.yml syntax"
if docker-compose -f "$PROJECT_ROOT/docker/docker-compose.e2e.yml" config >/dev/null 2>&1; then
    print_pass
else
    print_fail "Invalid docker-compose.e2e.yml syntax"
fi

# Check port availability
print_header "Checking Port Availability"

check_port() {
    port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $port already in use (may cause conflicts)"
    else
        print_pass
    fi
}

print_check "Port 18080 (API)"
check_port 18080

print_check "Port 5546 (PostgreSQL)"
check_port 5546

print_check "Port 5566 (LocalStack)"
check_port 5566

print_check "Intelligence-Builder API (localhost:8100)"
if curl -sf http://localhost:8100/ >/dev/null 2>&1; then
    print_pass
else
    print_warning "IB API not reachable on localhost:8100 (start the Intelligence-Builder stack)"
fi

# Check optional dependencies
print_header "Checking Optional Dependencies"

print_check "IB API Key"
if [ -n "$IB_API_KEY" ]; then
    print_pass
else
    print_warning "IB_API_KEY not set (security tests will skip if IB rejects requests)"
fi

print_check "Anthropic API Key"
if [ -n "$ANTHROPIC_API_KEY" ]; then
    print_pass
    echo -e "  ${BLUE}→ Chat tests will run with real API${NC}"
else
    print_warning "Not set (chat tests will verify graceful degradation)"
fi

print_check "Intelligence-Builder SDK"
if python -c "import ib_platform" 2>/dev/null; then
    print_pass
    echo -e "  ${BLUE}→ Advanced security analysis tests will run${NC}"
else
    print_warning "Not available (some security tests will be skipped)"
fi

# Summary
print_header "Verification Summary"

echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ E2E test setup is complete!${NC}"
    echo ""
    echo "Ready to run tests:"
    echo "  ./tests/e2e/run_e2e_tests.sh"
    echo ""
    echo "Or manually:"
    echo "  docker-compose -f docker/docker-compose.e2e.yml up -d"
    echo "  pytest tests/e2e/ -v -m e2e"
    echo ""
    exit 0
else
    echo -e "${RED}✗ E2E test setup incomplete${NC}"
    echo ""
    echo "Please fix the failed checks above before running E2E tests."
    echo ""
    if [ $WARNINGS -gt 0 ]; then
        echo "Warnings can be ignored - tests will still run."
    fi
    exit 1
fi
