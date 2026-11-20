# Shared helpers for the macOS/Linux scripts. Sourced, not executed.
# Requires PROJECT_ROOT and LOG_FILE to be set by the calling script.
# shellcheck shell=bash
# shellcheck disable=SC2034  # variables set here are used by the calling scripts

VENV_PATH="$PROJECT_ROOT/.venv"
VENV_PYTHON="$VENV_PATH/bin/python"
OLLAMA_URL="http://localhost:11434"
API_HEALTH_URL="http://127.0.0.1:8000/api/auth/health"

log() {
    local line
    line="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    printf '%s\n' "$line"
    printf '%s\n' "$line" >> "$LOG_FILE"
}

# Runs a command and writes each line of its output to the log.
# Returns the exit status of the command (the scripts use pipefail).
run_logged() {
    "$@" 2>&1 | while IFS= read -r line; do log "  $line"; done
}

init_log() {
    mkdir -p "$(dirname "$LOG_FILE")"
    : > "$LOG_FILE"
}

http_ok() {
    curl -fsS -o /dev/null --max-time "${2:-3}" "$1" 2>/dev/null
}

# Checks that Node.js meets the Vite 8 requirement: ^20.19.0 || >=22.12.0.
node_version_supported() {
    local version major minor
    version=$(node --version 2>/dev/null) || return 1
    version=${version#v}
    major=${version%%.*}
    minor=${version#*.}
    minor=${minor%%.*}
    case "$major$minor" in
        *[!0-9]*) return 1 ;;
    esac
    if [ "$major" -eq 20 ] && [ "$minor" -ge 19 ]; then return 0; fi
    if [ "$major" -eq 22 ] && [ "$minor" -ge 12 ]; then return 0; fi
    [ "$major" -gt 22 ]
}

# Reads the AI models and whether a password is set from a YAML config.
# Sets CFG_VLM, CFG_TEXT and CFG_PASSWORD_SET (1 or 0). Keeps the defaults when the
# file is missing or cannot be parsed. The password itself never leaves Python.
read_config() {
    local python_exe=$1 config_path=$2 output
    CFG_VLM="moondream"
    CFG_TEXT="llama3.2:3b"
    CFG_PASSWORD_SET=0
    [ -f "$config_path" ] || return 0
    if ! output=$("$python_exe" - "$config_path" <<'PY'
import sys
import yaml

with open(sys.argv[1], "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
ai = cfg.get("ai") or {}
app = cfg.get("app") or {}
print(ai.get("vlm_model") or "")
print(ai.get("text_model") or "")
print(1 if app.get("password") else 0)
PY
    ); then
        log "WARNING: could not read $config_path -- using default models"
        return 0
    fi
    local vlm text password_set
    vlm=$(printf '%s\n' "$output" | sed -n 1p)
    text=$(printf '%s\n' "$output" | sed -n 2p)
    password_set=$(printf '%s\n' "$output" | sed -n 3p)
    [ -n "$vlm" ] && CFG_VLM=$vlm
    [ -n "$text" ] && CFG_TEXT=$text
    [ "$password_set" = "1" ] && CFG_PASSWORD_SET=1
    return 0
}

# Starts a command in the background in its own process group, with stdin from
# /dev/null and output in the given log files. Sets BG_PID, which is also the process
# group ID. Job control must be on (set -m), and the function must not run in a
# subshell such as $(...), or the process stays in the script's process group.
start_background() {
    local workdir=$1 stdout_log=$2 stderr_log=$3
    shift 3
    (cd "$workdir" && exec "$@") < /dev/null > "$stdout_log" 2> "$stderr_log" &
    BG_PID=$!
    disown "$BG_PID"  # no "Terminated" job notices when cleanup stops it
}

is_running() {
    [ -n "${1:-}" ] && kill -0 "$1" 2>/dev/null
}

# Stops a process started with start_background, including its children
# (uvicorn --reload and npm both start child processes).
stop_process_group() {
    local name=$1 pid=${2:-}
    is_running "$pid" || return 0
    log "Stopping $name (PID: $pid)..."
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    local i=0
    while is_running "$pid" && [ "$i" -lt 10 ]; do
        sleep 0.5
        i=$((i + 1))
    done
    if is_running "$pid"; then
        kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
    fi
}
