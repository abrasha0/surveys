#!/usr/bin/env bash
# One-time environment setup for macOS and Linux (equivalent of full_setup.ps1).
# Usage: scripts/full_setup.sh [--force]
#   --force   recreate .venv
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
LOG_FILE="$PROJECT_ROOT/working_vault/logs/full_setup.log"
# shellcheck source=scripts/common.sh
. "$PROJECT_ROOT/scripts/common.sh"

REQUIREMENTS_PATH="$PROJECT_ROOT/requirements.txt"
FRONTEND_DIR="$PROJECT_ROOT/src/frontend"

FORCE=0
for arg in "$@"; do
    case "$arg" in
        --force) FORCE=1 ;;
        -h|--help)
            sed -n '2,4p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown option: $arg (see --help)" >&2
            exit 2
            ;;
    esac
done

fail() {
    log "ERROR: $*"
    exit 1
}

init_log
log "=== Full Setup - Environment ==="
log "Project root: $PROJECT_ROOT"
[ "$FORCE" -eq 1 ] && log "Force mode: recreating .venv"

# ============================================================
# Step 1: Python >= 3.12
# ============================================================
log "=== Step 1/9: Python >= 3.12 ==="
SYSTEM_PYTHON=""
for candidate in ${PYTHON:-} python3.13 python3.12 python3 python; do
    if command -v "$candidate" > /dev/null 2>&1 \
        && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
        SYSTEM_PYTHON=$(command -v "$candidate")
        break
    fi
done
if [ -z "$SYSTEM_PYTHON" ]; then
    log "ERROR: Python >= 3.12 not found (tried: ${PYTHON:+$PYTHON }python3.13 python3.12 python3 python)."
    log "       macOS: brew install python@3.12   Linux: use your package manager or pyenv."
    log "       To use a specific interpreter: PYTHON=/path/to/python3.12 $0"
    exit 1
fi
PY_VERSION=$("$SYSTEM_PYTHON" --version 2>&1)
log "OK: $PY_VERSION ($SYSTEM_PYTHON)"

# ============================================================
# Step 2: .venv
# ============================================================
log "=== Step 2/9: virtual environment ==="
if [ -d "$VENV_PATH" ] && [ "$FORCE" -eq 1 ]; then
    log "Force: removing the existing .venv..."
    rm -rf "$VENV_PATH"
fi
if [ -d "$VENV_PATH" ]; then
    log "OK: .venv already exists"
else
    "$SYSTEM_PYTHON" -m venv "$VENV_PATH" || fail "Failed to create .venv"
    log "OK: .venv created"
fi
[ -x "$VENV_PYTHON" ] || fail "python not found in .venv: $VENV_PYTHON (try --force)"

log "Upgrading pip..."
run_logged "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel \
    || log "WARNING: pip upgrade failed (continuing)"

# ============================================================
# Step 3: pip install -r requirements.txt
# ============================================================
log "=== Step 3/9: installing Python packages ==="
[ -f "$REQUIREMENTS_PATH" ] || fail "requirements.txt not found: $REQUIREMENTS_PATH"
run_logged "$VENV_PYTHON" -m pip install -r "$REQUIREMENTS_PATH" || fail "pip install failed"
log "OK: Python packages installed"

# Read the config now that PyYAML is installed in .venv
CONFIG_PATH="$PROJECT_ROOT/config.yaml"
if [ ! -f "$CONFIG_PATH" ]; then
    log "config.yaml does not exist -- using configs/config.yaml.example"
    CONFIG_PATH="$PROJECT_ROOT/configs/config.yaml.example"
fi
read_config "$VENV_PYTHON" "$CONFIG_PATH"
VLM_MODEL=$CFG_VLM
TEXT_MODEL=$CFG_TEXT
log "Models from config: VLM=$VLM_MODEL  Text=$TEXT_MODEL"

# ============================================================
# Step 4: Node.js and npm
# ============================================================
log "=== Step 4/9: Node.js and npm ==="
if ! command -v node > /dev/null 2>&1; then
    log "ERROR: Node.js not found in PATH."
    log "       Install Node.js 20.19+ or 22.12+: https://nodejs.org/ (macOS: brew install node)"
    log "       Then run this script again."
    exit 1
fi
command -v npm > /dev/null 2>&1 || fail "npm not found in PATH."
NODE_VERSION=$(node --version)
if ! node_version_supported; then
    fail "Node.js $NODE_VERSION is not supported. Install Node.js 20.19+ or 22.12+: https://nodejs.org/"
fi
log "OK: Node $NODE_VERSION, npm $(npm --version)"

# ============================================================
# Step 5: npm install (frontend)
# ============================================================
log "=== Step 5/9: installing frontend dependencies ==="
[ -d "$FRONTEND_DIR" ] || fail "src/frontend directory not found"
if [ -d "$FRONTEND_DIR/node_modules" ]; then
    log "node_modules already exists -- running npm install to sync it"
fi
run_logged npm install --prefix "$FRONTEND_DIR" || fail "npm install failed"
log "OK: frontend dependencies installed"

# ============================================================
# Step 6: locate Ollama
# ============================================================
log "=== Step 6/9: Ollama ==="
OLLAMA_BIN=""
if command -v ollama > /dev/null 2>&1; then
    OLLAMA_BIN=$(command -v ollama)
elif [ -x "/Applications/Ollama.app/Contents/Resources/ollama" ]; then
    OLLAMA_BIN="/Applications/Ollama.app/Contents/Resources/ollama"
fi
if [ -z "$OLLAMA_BIN" ]; then
    # Unlike full_setup.ps1, do not install Ollama automatically: the Linux installer
    # needs root and on macOS Ollama is a desktop app or a Homebrew package.
    log "ERROR: Ollama not found."
    log "       macOS: brew install ollama, or the app from https://ollama.com/download"
    log "       Linux: curl -fsSL https://ollama.com/install.sh | sh"
    log "       Then run this script again."
    exit 1
fi
log "Ollama: $OLLAMA_BIN"

# ============================================================
# Step 7: Ollama server
# ============================================================
log "=== Step 7/9: Ollama server ==="
if http_ok "$OLLAMA_URL"; then
    log "OK: Ollama server is already running"
else
    OLLAMA_LOG="$PROJECT_ROOT/working_vault/logs/ollama_serve.log"
    log "Server is not running. Starting ollama serve (log: $OLLAMA_LOG)..."
    nohup "$OLLAMA_BIN" serve < /dev/null > "$OLLAMA_LOG" 2>&1 &
    ready=0
    for i in 1 2 3 4 5 6 7 8 9 10; do
        sleep 3
        if http_ok "$OLLAMA_URL"; then
            ready=1
            break
        fi
        log "Waiting for the server... ($i/10)"
    done
    [ "$ready" -eq 1 ] || fail "Ollama server did not start within 30 s"
    log "OK: Ollama server responds"
fi

# ============================================================
# Step 8: pull models
# ============================================================
log "=== Step 8/9: AI models ==="

pull_model_if_missing() {
    local name=$1 models
    # Capture first: "list | grep -q" can fail under pipefail when grep exits early.
    models=$("$OLLAMA_BIN" list 2>/dev/null || true)
    if [[ "$models" == *"$name"* ]]; then
        log "OK: $name already pulled"
        return 0
    fi
    log "Pulling $name (this may take a while)..."
    run_logged "$OLLAMA_BIN" pull "$name" || return 1
    log "OK: $name pulled"
}

test_model() {
    local name=$1 body response
    body=$("$VENV_PYTHON" -c 'import json, sys; print(json.dumps({"model": sys.argv[1], "prompt": "Powiedz tylko: OK", "stream": False}))' "$name")
    if ! response=$(curl -fsS --max-time 120 -H 'Content-Type: application/json' -d "$body" "$OLLAMA_URL/api/generate" 2>&1); then
        log "WARNING: API test failed for $name -- $response"
        return 1
    fi
    response=$(printf '%s' "$response" | "$VENV_PYTHON" -c 'import json, sys; print(json.load(sys.stdin).get("response", "").strip())' 2>/dev/null || true)
    log "OK: $name -- $response"
}

pull_model_if_missing "$VLM_MODEL" || fail "Failed to pull VLM $VLM_MODEL"
pull_model_if_missing "$TEXT_MODEL" || fail "Failed to pull text model $TEXT_MODEL"

# ============================================================
# Step 9: test models
# ============================================================
log "=== Step 9/9: testing models ==="
models_ok=1
log "Testing VLM ($VLM_MODEL)..."
test_model "$VLM_MODEL" || models_ok=0
log "Testing text model ($TEXT_MODEL)..."
test_model "$TEXT_MODEL" || models_ok=0
if [ "$models_ok" -eq 0 ]; then
    log "WARNING: some models failed the API test."
    log "They may still be loading. Try manually: ollama run $VLM_MODEL"
fi

# ============================================================
# Summary
# ============================================================
log ""
log "========================================"
log "  AnkieterAI -- environment ready"
log "========================================"
log "  Python:  $PY_VERSION"
log "  .venv:   $VENV_PATH"
log "  Backend: $REQUIREMENTS_PATH"
log "  Frontend:$FRONTEND_DIR ($NODE_VERSION)"
log "  Ollama:  $OLLAMA_BIN"
log "  VLM:     $VLM_MODEL"
log "  Text:    $TEXT_MODEL"
log "========================================"
log ""
log "To start the app:"
log "  scripts/run_prod.sh    (production build + Cloudflare tunnel)"
log "  scripts/run_dev.sh     (development, hot reload)"
log ""
log "=== Full Setup -- finished successfully ==="
