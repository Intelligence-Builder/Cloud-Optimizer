#!/usr/bin/env bash

set -euo pipefail

APP_ROOT="/app"
DEFAULT_CMD=("python" "-m" "cloud_optimizer.entrypoint")

log() {
    local level="$1"
    shift
    printf '[entrypoint] [%s] %s\n' "${level}" "$*"
}

cd "${APP_ROOT}"

log INFO "Starting Cloud Optimizer container (user: $(whoami))"
log INFO "Working directory: ${APP_ROOT}"

if [[ $# -gt 0 ]]; then
    log INFO "Executing custom command: $*"
    exec "$@"
else
    log INFO "Running default entrypoint: ${DEFAULT_CMD[*]}"
    exec "${DEFAULT_CMD[@]}"
fi
