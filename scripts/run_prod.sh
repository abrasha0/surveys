#!/usr/bin/env bash
# Production run for macOS and Linux (equivalent of run_prod.ps1): builds the frontend,
# starts uvicorn on port 8000 and opens a Cloudflare quick tunnel.
# Usage: scripts/run_prod.sh [--no-tunnel] [--cloudflared-dir DIR]
#   --no-tunnel            local only, no Cloudflare tunnel
#   --cloudflared-dir DIR  where to look for cloudflared if it is not in PATH
#                          (default: ~/.local/bin)
set -euo pipefail
set -m  # job control: every background process gets its own process group

PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
LOGS_DIR="$PROJECT_ROOT/working_vault/logs"
LOG_FILE="$LOGS_DIR/run_prod.log"
# shellcheck source=scripts/common.sh
. "$PROJECT_ROOT/scripts/common.sh"

NO_TUNNEL=0
CLOUDFLARED_DIR="$HOME/.local/bin"
while [ $# -gt 0 ]; do
    case "$1" in
        --no-tunnel) NO_TUNNEL=1 ;;
        --cloudflared-dir)
            [ $# -ge 2 ] || { echo "--cloudflared-dir needs a directory" >&2; exit 2; }
            CLOUDFLARED_DIR=$2
            shift
            ;;
        -h|--help)
            sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1 (see --help)" >&2
            exit 2
            ;;
    esac
    shift
done

TUNNEL_URL_FILE="$LOGS_DIR/tunnel_url.txt"
SRC_DIR="$PROJECT_ROOT/src/backend"
FRONTEND_DIR="$PROJECT_ROOT/src/frontend"
DIST_DIR="$PROJECT_ROOT/working_vault/dist"
UVICORN_LOG="$LOGS_DIR/uvicorn_prod.log"

UVICORN_PID=""
TUNNEL_PID=""

cleanup() {
    trap - EXIT INT TERM
    log "=== Cleanup: stopping processes ==="
    stop_process_group "uvicorn" "$UVICORN_PID"
    stop_process_group "cloudflared" "$TUNNEL_PID"
    log "=== Cleanup finished ==="
}

fail() {
    log "ERROR: $*"
    exit 1
}

init_log
log "=== Run Prod - start ==="
log "Flags: NoTunnel=$NO_TUNNEL CloudflaredDir=$CLOUDFLARED_DIR"

# ============================================================
# Step 1: Ollama
# ============================================================
log "=== Step 1/5: checking Ollama ==="
if http_ok "$OLLAMA_URL" 5; then
    log "OK: Ollama responds"
else
    log "ERROR: Ollama does not respond on port 11434."
    log "Run first: scripts/full_setup.sh"
    exit 1
fi

# ============================================================
# Step 2: .venv and password
# ============================================================
log "=== Step 2/5: checking .venv ==="
if [ ! -x "$VENV_PYTHON" ]; then
    log "ERROR: .venv does not exist."
    log "Run first: scripts/full_setup.sh"
    exit 1
fi
log "OK: .venv exists"
read_config "$VENV_PYTHON" "$PROJECT_ROOT/config.yaml"
if [ -n "${ANKIETER_APP_PASSWORD:-}" ]; then
    PASSWORD_STATUS="set (ANKIETER_APP_PASSWORD)"
elif [ "$CFG_PASSWORD_SET" -eq 1 ]; then
    PASSWORD_STATUS="set (config.yaml)"
else
    log "ERROR: app.password is not set in config.yaml -- the backend does not start without a password."
    log "Copy configs/config.yaml.example to config.yaml and set app.password."
    exit 1
fi

# Look for cloudflared before the build, so a missing binary fails fast.
CLOUDFLARED_BIN=""
if [ "$NO_TUNNEL" -eq 0 ]; then
    if command -v cloudflared > /dev/null 2>&1; then
        CLOUDFLARED_BIN=$(command -v cloudflared)
    elif [ -x "$CLOUDFLARED_DIR/cloudflared" ]; then
        CLOUDFLARED_BIN="$CLOUDFLARED_DIR/cloudflared"
    else
        # Unlike run_prod.ps1, do not download a binary: use the system package instead.
        log "ERROR: cloudflared not found in PATH or in $CLOUDFLARED_DIR."
        log "       macOS: brew install cloudflared"
        log "       Linux: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        log "       Or run without the tunnel: scripts/run_prod.sh --no-tunnel"
        exit 1
    fi
    log "OK: cloudflared found: $CLOUDFLARED_BIN"
fi

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# ============================================================
# Step 3: build the frontend
# ============================================================
log "=== Step 3/5: building the frontend ==="
[ -d "$FRONTEND_DIR" ] || fail "src/frontend directory not found"

log "npm install..."
run_logged npm install --prefix "$FRONTEND_DIR" || fail "npm install failed"
log "npm run build..."
run_logged npm run build --prefix "$FRONTEND_DIR" || fail "npm run build failed"
[ -d "$FRONTEND_DIR/dist" ] || fail "$FRONTEND_DIR/dist does not exist after the build -- check the npm run build output"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"
cp -R "$FRONTEND_DIR/dist/." "$DIST_DIR/"
[ -f "$DIST_DIR/index.html" ] || fail "$DIST_DIR/index.html is missing after the copy -- the frontend build is incomplete"
log "OK: frontend built and copied to $DIST_DIR"

# ============================================================
# Step 4: uvicorn
# ============================================================
log "=== Step 4/5: starting uvicorn ==="
start_background "$SRC_DIR" "$UVICORN_LOG" "$UVICORN_LOG.err" \
    "$VENV_PYTHON" -m uvicorn main:app --port 8000
UVICORN_PID=$BG_PID
log "OK: uvicorn started (PID: $UVICORN_PID)"

log "Waiting for the API..."
api_ready=0
for _ in $(seq 1 20); do
    sleep 1
    if http_ok "$API_HEALTH_URL" 2; then
        api_ready=1
        break
    fi
done
if [ "$api_ready" -ne 1 ]; then
    if [ -s "$UVICORN_LOG.err" ]; then
        tail -n 20 "$UVICORN_LOG.err" | while IFS= read -r line; do log "  $line"; done
    fi
    fail "API does not respond after 20 s"
fi
log "OK: API ready at http://localhost:8000"

# Check that the frontend is served
content_type=$(curl -fsS -o /dev/null --max-time 3 -w '%{content_type}' "http://127.0.0.1:8000/" 2>/dev/null || true)
case "$content_type" in
    text/html*) log "OK: frontend served at http://localhost:8000" ;;
    *) log "WARNING: / does not return HTML (Content-Type: ${content_type:-none})" ;;
esac

# ============================================================
# Step 5: Cloudflare tunnel
# ============================================================
TUNNEL_URL=""
if [ "$NO_TUNNEL" -eq 0 ]; then
    log "=== Step 5/5: Cloudflare tunnel ==="

    TUNNEL_LOG="$LOGS_DIR/tunnel_$(date +%Y%m%d_%H%M%S).log"
    log "Starting cloudflared tunnel --url http://localhost:8000"
    start_background "$PROJECT_ROOT" "$TUNNEL_LOG" "$TUNNEL_LOG.err" \
        "$CLOUDFLARED_BIN" tunnel --url http://localhost:8000
    TUNNEL_PID=$BG_PID

    log "Waiting for the tunnel URL (up to 60 s)..."
    sleep 4
    for _ in $(seq 1 20); do
        sleep 3
        TUNNEL_URL=$(cat "$TUNNEL_LOG" "$TUNNEL_LOG.err" 2>/dev/null \
            | grep -Eo 'https://[A-Za-z0-9.-]+\.trycloudflare\.com' | head -n 1 || true)
        [ -n "$TUNNEL_URL" ] && break
    done

    if [ -n "$TUNNEL_URL" ]; then
        log "OK: tunnel active"
        log "URL: $TUNNEL_URL"
        printf '%s\n' "$TUNNEL_URL" > "$TUNNEL_URL_FILE"
    else
        log "WARNING: no tunnel URL after 60 s. Check the log: $TUNNEL_LOG"
    fi
else
    log "=== Step 5/5: tunnel skipped (--no-tunnel) ==="
fi

# ============================================================
# Summary
# ============================================================
log ""
log "========================================"
log "  AnkieterAI - ready"
log "========================================"
log "  Local app:         http://localhost:8000"
[ -n "$TUNNEL_URL" ] && log "  Public tunnel:     $TUNNEL_URL"
log "  Password:          $PASSWORD_STATUS"
log "  Models:            VLM=$CFG_VLM  Text=$CFG_TEXT"
log "========================================"
log ""
log "Press Ctrl+C to stop all processes."
log ""
log "=== Run Prod - started ==="

LAST_TUNNEL_CHECK=0
while true; do
    sleep 10
    if ! is_running "$UVICORN_PID" && ! is_running "$TUNNEL_PID"; then
        break
    fi

    # Tunnel health check every 30 s
    if [ -n "$TUNNEL_URL" ]; then
        now=$(date +%s)
        if [ $((now - LAST_TUNNEL_CHECK)) -ge 30 ]; then
            LAST_TUNNEL_CHECK=$now
            status=$(curl -s -o /dev/null --max-time 10 -w '%{http_code}' "$TUNNEL_URL" || true)
            if [ -n "$status" ] && [ "$status" != "000" ]; then
                log "tunnel health: OK (HTTP $status)"
            else
                log "tunnel health: no response"
            fi
        fi
    fi
done

log "=== Run Prod - finished ==="
