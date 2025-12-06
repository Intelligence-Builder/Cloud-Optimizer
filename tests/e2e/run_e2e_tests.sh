#!/usr/bin/env bash
#
# E2E Test Runner for Cloud Optimizer
#
# This script manages the E2E test lifecycle:
# 1. Checks prerequisites (Docker, docker-compose)
# 2. Starts the docker-compose stack
# 3. Waits for services to be healthy
# 4. Runs pytest E2E tests
# 5. Tears down the stack (unless --keep-running)
#
# Usage:
#   ./run_e2e_tests.sh [options]
#
# Options:
#   --verbose, -v       Enable verbose test output
#   --keep-running, -k  Keep services running after tests
#   --test, -t NAME     Run specific test by name
#   --help, -h          Show this help message

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.e2e.yml"
PROJECT_NAME="co-e2e-test"

# Test configuration
VERBOSE=false
KEEP_RUNNING=false
SPECIFIC_TEST=""

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Function to show help
show_help() {
    cat << EOF
E2E Test Runner for Cloud Optimizer

Usage: $0 [options]

Options:
  --verbose, -v       Enable verbose test output
  --keep-running, -k  Keep services running after tests
  --test, -t NAME     Run specific test by name
  --help, -h          Show this help message

Examples:
  # Run all E2E tests
  $0

  # Run with verbose output
  $0 --verbose

  # Run specific test
  $0 --test test_api_health_check_works

  # Keep services running for debugging
  $0 --keep-running

  # Combine options
  $0 -v -k --test test_database_migrations_ran

Environment Requirements:
  - Docker Desktop or Docker Engine running
  - docker-compose v1.29+ installed
  - Python 3.11+ with test dependencies

Services Started:
  - PostgreSQL (port 5546)
  - LocalStack (port 5566)
  - Cloud Optimizer API (port 18080)

For more information, see tests/e2e/README.md
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -k|--keep-running)
            KEEP_RUNNING=true
            shift
            ;;
        -t|--test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Docker
    if ! command_exists docker; then
        print_error "Docker not found. Please install Docker Desktop or Docker Engine."
        exit 1
    fi
    print_success "Docker installed"

    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon not running. Please start Docker."
        exit 1
    fi
    print_success "Docker daemon running"

    # Check docker-compose
    if ! command_exists docker-compose; then
        print_error "docker-compose not found. Please install docker-compose v1.29+."
        exit 1
    fi
    print_success "docker-compose installed ($(docker-compose --version))"

    # Check Python
    if ! command_exists python; then
        print_error "Python not found. Please install Python 3.11+."
        exit 1
    fi
    print_success "Python installed ($(python --version))"

    # Check pytest
    if ! python -m pytest --version >/dev/null 2>&1; then
        print_warning "pytest not installed. Installing test dependencies..."
        pip install -e "$PROJECT_ROOT[test]"
    fi
    print_success "pytest installed"

    # Check compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    print_success "Compose file found"
}

# Function to start services
start_services() {
    print_header "Starting E2E Test Environment"

    print_info "Starting docker-compose services..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d

    print_info "Waiting for services to be healthy..."

    # Wait for postgres
    print_info "  Waiting for PostgreSQL..."
    timeout=60
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps postgres-test | grep -q "healthy"; then
            print_success "  PostgreSQL is healthy"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    if [ $elapsed -ge $timeout ]; then
        print_error "PostgreSQL failed to become healthy within ${timeout}s"
        show_logs
        cleanup_services
        exit 1
    fi

    # Wait for localstack
    print_info "  Waiting for LocalStack..."
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps localstack | grep -q "healthy"; then
            print_success "  LocalStack is healthy"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    if [ $elapsed -ge $timeout ]; then
        print_error "LocalStack failed to become healthy within ${timeout}s"
        show_logs
        cleanup_services
        exit 1
    fi

    # Wait for API
    print_info "  Waiting for Cloud Optimizer API..."
    elapsed=0
    timeout=120  # API takes longer to start
    while [ $elapsed -lt $timeout ]; do
        if curl -s http://localhost:18080/health >/dev/null 2>&1; then
            print_success "  API is healthy and responding"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    if [ $elapsed -ge $timeout ]; then
        print_error "API failed to become healthy within ${timeout}s"
        show_logs
        cleanup_services
        exit 1
    fi

    print_success "All services are healthy and ready"
}

# Function to show service logs
show_logs() {
    print_header "Service Logs (last 50 lines)"

    echo -e "${YELLOW}=== PostgreSQL ===${NC}"
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs --tail=50 postgres-test || true

    echo -e "${YELLOW}=== LocalStack ===${NC}"
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs --tail=50 localstack || true

    echo -e "${YELLOW}=== Cloud Optimizer API ===${NC}"
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs --tail=50 app || true
}

# Function to run tests
run_tests() {
    print_header "Running E2E Tests"

    cd "$PROJECT_ROOT"

    # Build pytest command
    PYTEST_CMD="python -m pytest tests/e2e/ -m e2e"

    if [ "$VERBOSE" = true ]; then
        PYTEST_CMD="$PYTEST_CMD -vv -s"
    else
        PYTEST_CMD="$PYTEST_CMD -v"
    fi

    if [ -n "$SPECIFIC_TEST" ]; then
        PYTEST_CMD="$PYTEST_CMD -k $SPECIFIC_TEST"
        print_info "Running specific test: $SPECIFIC_TEST"
    else
        print_info "Running all E2E tests"
    fi

    # Add color output
    PYTEST_CMD="$PYTEST_CMD --color=yes"

    # Add short traceback for failures
    PYTEST_CMD="$PYTEST_CMD --tb=short"

    print_info "Command: $PYTEST_CMD"
    echo ""

    # Run tests
    if eval "$PYTEST_CMD"; then
        TEST_EXIT_CODE=0
        print_success "All tests passed!"
    else
        TEST_EXIT_CODE=$?
        print_error "Some tests failed (exit code: $TEST_EXIT_CODE)"
    fi

    return $TEST_EXIT_CODE
}

# Function to cleanup services
cleanup_services() {
    if [ "$KEEP_RUNNING" = true ]; then
        print_header "Services Still Running"
        print_info "Services are still running (--keep-running flag)"
        print_info ""
        print_info "Service URLs:"
        print_info "  API:        http://localhost:18080"
        print_info "  API Docs:   http://localhost:18080/docs"
        print_info "  PostgreSQL: localhost:5546 (user: test, db: test_intelligence)"
        print_info "  LocalStack: http://localhost:5566"
        print_info ""
        print_info "To stop services manually:"
        print_info "  docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down -v"
        print_info ""
        print_info "To view logs:"
        print_info "  docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f"
    else
        print_header "Cleaning Up E2E Test Environment"
        print_info "Stopping and removing containers..."
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v
        print_success "Cleanup complete"
    fi
}

# Function to handle script interruption
cleanup_on_exit() {
    exit_code=$?
    echo ""
    if [ $exit_code -ne 0 ]; then
        print_warning "Script interrupted or failed"
        show_logs
        if [ "$KEEP_RUNNING" != true ]; then
            KEEP_RUNNING=true
            print_info ""
            print_info "Keeping containers running for debugging."
            print_info "Stop them manually with:"
            print_info "  docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down -v"
        fi
    fi
    if [ "$KEEP_RUNNING" != true ]; then
        cleanup_services
    fi
    exit $exit_code
}

# Trap EXIT signal to ensure cleanup
trap cleanup_on_exit EXIT INT TERM

# Main execution flow
main() {
    print_header "Cloud Optimizer E2E Test Runner"

    # Run checks
    check_prerequisites

    # Start services
    start_services

    # Run tests
    run_tests
    TEST_RESULT=$?

    # Show summary
    print_header "Test Summary"
    if [ $TEST_RESULT -eq 0 ]; then
        print_success "✓ All E2E tests passed"
    else
        print_error "✗ Some E2E tests failed"
        print_info "Check test output above for details"
    fi

    # Return test exit code
    exit $TEST_RESULT
}

# Run main function
main
