#!/bin/bash

###############################################################################
# Security Scan Script for Cloud Optimizer
#
# This script runs Trivy vulnerability scanning on the Docker image locally.
# It can scan both built images and filesystem for vulnerabilities.
#
# Prerequisites:
#   - Docker installed and running
#   - Trivy installed (or will use Docker to run Trivy)
#
# Usage:
#   ./scripts/security-scan.sh [OPTIONS]
#
# Options:
#   -i, --image IMAGE     Image to scan (default: builds cloud-optimizer:local)
#   -f, --filesystem      Also scan the filesystem for vulnerabilities
#   -s, --severity LEVEL  Minimum severity (CRITICAL,HIGH,MEDIUM,LOW)
#   -o, --output FORMAT   Output format (table, json, sarif)
#   --fail-on LEVEL       Exit with error if vulnerabilities at this level found
#   -h, --help            Show this help message
#
# Examples:
#   ./scripts/security-scan.sh                      # Build and scan image
#   ./scripts/security-scan.sh -i my-image:latest   # Scan existing image
#   ./scripts/security-scan.sh -f                   # Also scan filesystem
#   ./scripts/security-scan.sh --fail-on HIGH       # Fail on HIGH or CRITICAL
#
###############################################################################

set -e

# Default values
IMAGE_NAME=""
BUILD_IMAGE=true
SCAN_FILESYSTEM=false
SEVERITY="CRITICAL,HIGH,MEDIUM"
OUTPUT_FORMAT="table"
FAIL_ON=""
USE_DOCKER_TRIVY=true

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

show_help() {
    head -n 35 "$0" | grep "^#" | sed 's/^# //; s/^#//'
    exit 0
}

# Check if Trivy is installed
check_trivy() {
    if command -v trivy &> /dev/null; then
        USE_DOCKER_TRIVY=false
        log_info "Using locally installed Trivy"
    else
        log_info "Trivy not found, will use Docker image"
        USE_DOCKER_TRIVY=true
    fi
}

# Run Trivy command
run_trivy() {
    if [ "$USE_DOCKER_TRIVY" = true ]; then
        docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v "$PWD:/workspace" \
            -w /workspace \
            aquasec/trivy:latest "$@"
    else
        trivy "$@"
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--image)
            IMAGE_NAME="$2"
            BUILD_IMAGE=false
            shift 2
            ;;
        -f|--filesystem)
            SCAN_FILESYSTEM=true
            shift
            ;;
        -s|--severity)
            SEVERITY="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --fail-on)
            FAIL_ON="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Main execution
log_info "Cloud Optimizer Security Scan"
echo "========================================"

check_trivy

# Build image if needed
if [ "$BUILD_IMAGE" = true ]; then
    log_info "Building Docker image for scanning..."
    IMAGE_NAME="cloud-optimizer:security-scan"
    docker build -f docker/Dockerfile -t "$IMAGE_NAME" . --quiet
    log_success "Image built: $IMAGE_NAME"
fi

# Scan the Docker image
echo ""
log_info "Scanning Docker image: $IMAGE_NAME"
echo "----------------------------------------"

TRIVY_ARGS=(
    "image"
    "--severity" "$SEVERITY"
    "--format" "$OUTPUT_FORMAT"
    "--ignore-unfixed"
)

if [ -n "$FAIL_ON" ]; then
    TRIVY_ARGS+=("--exit-code" "1" "--severity" "$FAIL_ON")
fi

TRIVY_ARGS+=("$IMAGE_NAME")

if run_trivy "${TRIVY_ARGS[@]}"; then
    log_success "Image scan completed - no critical vulnerabilities found"
else
    log_error "Vulnerabilities found in image!"
    IMAGE_SCAN_FAILED=true
fi

# Scan filesystem if requested
if [ "$SCAN_FILESYSTEM" = true ]; then
    echo ""
    log_info "Scanning filesystem for vulnerabilities..."
    echo "----------------------------------------"

    FS_ARGS=(
        "filesystem"
        "--severity" "$SEVERITY"
        "--format" "$OUTPUT_FORMAT"
        "."
    )

    if run_trivy "${FS_ARGS[@]}"; then
        log_success "Filesystem scan completed - no issues found"
    else
        log_warning "Issues found in filesystem dependencies"
    fi
fi

# Scan for secrets
echo ""
log_info "Scanning for secrets in codebase..."
echo "----------------------------------------"

SECRET_ARGS=(
    "filesystem"
    "--scanners" "secret"
    "--format" "$OUTPUT_FORMAT"
    "."
)

if run_trivy "${SECRET_ARGS[@]}"; then
    log_success "Secret scan completed - no secrets detected"
else
    log_warning "Potential secrets found in codebase!"
fi

# Summary
echo ""
echo "========================================"
if [ "$IMAGE_SCAN_FAILED" = true ]; then
    log_error "SECURITY SCAN COMPLETED WITH ISSUES"
    echo ""
    echo "Recommendations:"
    echo "  1. Update base image to latest patch version"
    echo "  2. Update vulnerable dependencies"
    echo "  3. Review and address HIGH/CRITICAL findings"
    exit 1
else
    log_success "SECURITY SCAN COMPLETED SUCCESSFULLY"
fi
echo "========================================"
