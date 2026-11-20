#!/usr/bin/env bash
# Development run for macOS and Linux (equivalent of run_dev.ps1): uvicorn with --reload
# on port 8000 and the Vite dev server on port 5173.
# Usage: scripts/run_dev.sh
# Keys: R restarts the backend, Ctrl+C stops everything.
set -euo pipefail
set -m  # job control: every background process gets its own process group

PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
LOGS_DIR="$PROJECT_ROOT/working_vault/logs"
LOG_FILE="$LOGS_DIR/run_dev.log"
# shellcheck source=scripts/common.sh
. "$PROJECT_ROOT/scripts/common.sh"

case "${1:-}" in
    "") ;;
    -h|--help)
        sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'
        exit 0
        ;;
    *)
        echo "Unknown option: $1 (see --help)" >&2
        exit 2
        ;;
esac

SRC_DIR="$PROJECT_ROOT/src/backend"
FRONTEND_DIR="$PROJECT_ROOT/src/frontend"
SURVEYS_DIR="$PROJECT_ROOT/working_vault/surveys_data"
UVICORN_LOG="$LOGS_DIR/uvicorn_dev.log"
NPM_LOG="$LOGS_DIR/npm_dev.log"

UVICORN_PID=""
NPM_PID=""

cleanup() {
    trap - EXIT INT TERM
    log "=== Cleanup: stopping processes ==="
    stop_process_group "uvicorn" "$UVICORN_PID"
    stop_process_group "npm dev" "$NPM_PID"
    log "=== Cleanup finished ==="
}

start_uvicorn() {
    start_background "$SRC_DIR" "$UVICORN_LOG" "$UVICORN_LOG.err" \
        "$VENV_PYTHON" -m uvicorn main:app --reload --port 8000
    UVICORN_PID=$BG_PID
    log "OK: uvicorn started (PID: $UVICORN_PID)"
}

wait_uvicorn_ready() {
    local elapsed=0 sec f
    for sec in 1 1 2 2 3 3 5 8; do
        sleep "$sec"
        elapsed=$((elapsed + sec))
        if http_ok "$API_HEALTH_URL" 2; then
            log "OK: API ready at http://localhost:8000"
            return 0
        fi
    done
    log "WARNING: API not confirmed after ${elapsed}s - check the logs: $UVICORN_LOG and $UVICORN_LOG.err"
    for f in "$UVICORN_LOG" "$UVICORN_LOG.err"; do
        if [ -s "$f" ]; then
            log "Last lines of $(basename "$f"):"
            tail -n 20 "$f" | while IFS= read -r line; do log "  $line"; done
        fi
    done
    return 0
}

restart_uvicorn() {
    stop_process_group "uvicorn" "$UVICORN_PID"
    start_uvicorn
    log "Waiting for uvicorn..."
    wait_uvicorn_ready
}

# File names and modification times of the image directory, one per line.
if stat -c '%Y' "$PROJECT_ROOT" > /dev/null 2>&1; then
    STAT_ARGS=(-c '%n:%Y')  # GNU coreutils
else
    STAT_ARGS=(-f '%N:%m')  # BSD / macOS
fi
dir_snapshot() {
    [ -d "$1" ] || return 0
    find "$1" -maxdepth 1 -type f -exec stat "${STAT_ARGS[@]}" {} + 2>/dev/null | sort
}

# --- development env cleanup ---
rm -rf "$LOGS_DIR"
init_log
log "=== Run Dev - start ==="

# --- Step 1: check Ollama ---
log "Step 1: checking that Ollama is running on port 11434..."
if http_ok "$OLLAMA_URL" 5; then
    log "OK: Ollama responds at $OLLAMA_URL"
else
    log "ERROR: Ollama does not respond on port 11434."
    log ""
    log "Run first: scripts/full_setup.sh"
    log ""
    log "=== Run Dev - failed ==="
    exit 1
fi

# --- Step 2: check .venv ---
log "Step 2: checking the virtual environment..."
if [ ! -x "$VENV_PYTHON" ]; then
    log "ERROR: .venv does not exist."
    log "Run first: scripts/full_setup.sh"
    exit 1
fi
log "OK: .venv exists"

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# --- Step 3: start uvicorn ---
log "Step 3: starting uvicorn (API)..."
start_uvicorn
log "Waiting for uvicorn..."
wait_uvicorn_ready

# --- Step 4: check node and npm ---
log "Step 4: checking node and npm..."
if ! command -v node > /dev/null 2>&1; then
    log "ERROR: Node.js not found in PATH. Install Node.js 20.19+ or 22.12+: https://nodejs.org/"
    exit 1
fi
if ! command -v npm > /dev/null 2>&1; then
    log "ERROR: npm not found in PATH."
    exit 1
fi
log "OK: node ($(command -v node)), npm ($(command -v npm))"

# --- Step 5: start npm dev ---
log "Step 5: starting npm dev (frontend)..."
if [ ! -d "$FRONTEND_DIR" ]; then
    log "ERROR: src/frontend directory not found"
    exit 1
fi
start_background "$FRONTEND_DIR" "$NPM_LOG" "$NPM_LOG.err" npm run dev
NPM_PID=$BG_PID
log "OK: npm dev started (PID: $NPM_PID)"
log "Frontend dev: http://localhost:5173 (proxy /api -> localhost:8000)"
log ""
log "Press Ctrl+C to stop all processes."
if [ -t 0 ]; then
    log "Press R to restart the backend manually (e.g. after adding or removing images)."
fi
log ""

# --- Step 6: watch the image directory ---
WATCH=0
LAST_SNAPSHOT=""
if [ -d "$SURVEYS_DIR" ]; then
    WATCH=1
    LAST_SNAPSHOT=$(dir_snapshot "$SURVEYS_DIR")
    log "OK: watching the image directory (polling every 2 s)"
else
    log "WARNING: image directory does not exist - watcher skipped"
fi
log "     $SURVEYS_DIR"
LAST_RESTART=0

# --- Step 7: monitor processes and reload ---
while true; do
    key=""
    if [ -t 0 ]; then
        read -rsn1 -t 2 key || true
    else
        sleep 2
    fi

    # --- 7a: restart the backend when images change ---
    if [ "$WATCH" -eq 1 ]; then
        current=$(dir_snapshot "$SURVEYS_DIR")
        if [ "$current" != "$LAST_SNAPSHOT" ]; then
            LAST_SNAPSHOT=$current
            now=$(date +%s)
            if [ $((now - LAST_RESTART)) -ge 3 ]; then
                log "=== Image directory changed - restarting backend ==="
                restart_uvicorn
                LAST_RESTART=$now
            fi
        fi
    fi

    # --- 7b: manual reload (R key) ---
    if [ "$key" = "r" ] || [ "$key" = "R" ]; then
        log "=== Manual backend reload (R key) ==="
        restart_uvicorn
        log "INFO: Vite reconnects to the restarted backend automatically"
    fi

    # --- 7c: stop when both processes have exited ---
    if ! is_running "$UVICORN_PID" && ! is_running "$NPM_PID"; then
        break
    fi
done

log "=== Run Dev - finished ==="
