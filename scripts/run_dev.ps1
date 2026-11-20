param(
    [switch]$Force
)

$ProjectRoot = Resolve-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "..")
$LogFile = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\run_dev.log"
$VenvPath = Join-Path -Path $ProjectRoot -ChildPath ".venv"

$uvicornProcess = $null
$npmProcess = $null

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Cleanup {
    Write-Log "=== Cleanup: stopping processes ==="
    if ($uvicornProcess -and -not $uvicornProcess.HasExited) {
        Write-Log "Stopping uvicorn (PID: $($uvicornProcess.Id))..."
        $uvicornProcess.Kill()
    }
    if ($npmProcess -and -not $npmProcess.HasExited) {
        Write-Log "Stopping npm dev (PID: $($npmProcess.Id))..."
        $npmProcess.Kill()
    }
    Write-Log "=== Cleanup finished ==="
}

function Wait-UvicornReady {
    param([string]$LogPath)
    $intervals = @(1, 1, 2, 2, 3, 3, 5, 8)
    $elapsed = 0
    foreach ($sec in $intervals) {
        Start-Sleep -Seconds $sec
        $elapsed += $sec
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/auth/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) {
                Write-Log "OK: API ready at http://localhost:8000"
                return $true
            }
        } catch {
            # uvicorn is not ready yet - keep waiting
        }
    }
    Write-Log "WARNING: API not confirmed after ${elapsed}s - check the logs: $LogPath and ${LogPath}.err"
    foreach ($f in @($LogPath, "${LogPath}.err")) {
        if (Test-Path -LiteralPath $f) {
            $content = Get-Content -LiteralPath $f -Tail 20
            if ($content) {
                Write-Log "Last lines of $(Split-Path -Path $f -Leaf):"
                $content | ForEach-Object { Write-Log "  $_" }
            }
        }
    }
    return $false
}

# --- development env cleanup ---
$WorkingDir = Join-Path -Path $ProjectRoot -ChildPath "working_vault"
$LogsDir = Join-Path -Path $WorkingDir -ChildPath "logs"
if (Test-Path -LiteralPath $LogsDir) {
    Remove-Item -LiteralPath $LogsDir -Recurse -Force
}

New-Item -Path $LogFile -ItemType File -Force | Out-Null
Write-Log "=== Run Dev - start ==="

# --- Step 1: check Ollama ---
Write-Log "Step 1: checking that Ollama is running on port 11434..."
$ErrorActionPreference = "Stop"
try {
    $r = Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) {
        Write-Log "OK: Ollama responds at http://localhost:11434"
    } else {
        throw "Ollama returned status $($r.StatusCode)"
    }
} catch {
    Write-Log "ERROR: Ollama does not respond on port 11434."
    Write-Log ""
    Write-Log "Run first: .\scripts\full_setup.ps1"
    Write-Log ""
    Write-Log "=== Run Dev - failed ==="
    exit 1
}

# --- Step 2: check .venv ---
Write-Log "Step 2: checking the virtual environment..."
if (-not (Test-Path -LiteralPath $VenvPath)) {
    Write-Log "ERROR: .venv does not exist."
    Write-Log "Run first: .\scripts\full_setup.ps1"
    exit 1
} else {
    Write-Log "OK: .venv exists"
}
$ErrorActionPreference = "Continue"

# --- Step 3: start uvicorn ---
Write-Log "Step 3: starting uvicorn (API)..."
$PythonExe = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"
$uvicornLog = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\uvicorn_dev.log"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    Write-Log "ERROR: python.exe not found in .venv"
    exit 1
}

$SrcDir = Join-Path -Path $ProjectRoot -ChildPath "src\backend"
$uvicornProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn main:app --reload --port 8000" -WorkingDirectory $SrcDir -NoNewWindow -PassThru -RedirectStandardOutput $uvicornLog -RedirectStandardError "${uvicornLog}.err"
Write-Log "OK: uvicorn started (PID: $($uvicornProcess.Id))"

# --- Wait for uvicorn ---
Write-Log "Waiting for uvicorn..."
$null = Wait-UvicornReady -LogPath $uvicornLog

# --- Step 4: check node and npm ---
Write-Log "Step 4: checking node and npm..."
$nodePath = (Get-Command "node" -ErrorAction SilentlyContinue).Source
$npmPath = (Get-Command "npm" -ErrorAction SilentlyContinue).Source
if (-not $nodePath) {
    Write-Log "ERROR: Node.js not found in PATH. Install Node.js 20.19+ or 22.12+: https://nodejs.org/"
    Cleanup
    exit 1
}
if (-not $npmPath) {
    Write-Log "ERROR: npm not found in PATH."
    Cleanup
    exit 1
}
Write-Log "OK: node ($nodePath), npm ($npmPath)"

# --- Step 5: start npm dev ---
Write-Log "Step 5: starting npm dev (frontend)..."
$FrontendDir = Join-Path -Path $ProjectRoot -ChildPath "src\frontend"
$npmLog = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\npm_dev.log"

if (-not (Test-Path -LiteralPath $FrontendDir)) {
    Write-Log "ERROR: src/frontend directory not found"
    Cleanup
    exit 1
}

# npm may resolve to npm.ps1, and Start-Process needs an executable, so go through cmd /c
$npmProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $FrontendDir -NoNewWindow -PassThru -RedirectStandardOutput $npmLog -RedirectStandardError "${npmLog}.err"
Write-Log "OK: npm dev started (PID: $($npmProcess.Id))"
Write-Log "Frontend dev: http://localhost:5173 (proxy /api -> localhost:8000)"
Write-Log ""
Write-Log "Press Ctrl+C to stop all processes."
Write-Log "Press R to restart the backend manually (e.g. after adding or removing images)."
Write-Log ""

# --- Step 6: watch the image directory ---
$SurveysDir = Join-Path -Path $ProjectRoot -ChildPath "working_vault\surveys_data"
$lastSnapshot = $null
$lastRestartTime = [DateTime]::UtcNow.AddSeconds(-10)

function Get-DirSnapshot {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return "" }
    $items = Get-ChildItem -Path $Path -File | ForEach-Object {
        "$($_.Name):$($_.LastWriteTimeUtc.Ticks)"
    }
    return ($items -join '|')
}

if (Test-Path -LiteralPath $SurveysDir) {
    $lastSnapshot = Get-DirSnapshot -Path $SurveysDir
    Write-Log "OK: watching the image directory (polling every 2 s)"
    Write-Log "     $SurveysDir"
} else {
    Write-Log "WARNING: image directory does not exist - watcher skipped"
    Write-Log "     $SurveysDir"
}

# --- Step 7: monitor processes and reload ---
try {
    while ($true) {
        Start-Sleep -Seconds 2

        # --- 7a: restart the backend when images change ---
        if ($lastSnapshot) {
            $currentSnapshot = Get-DirSnapshot -Path $SurveysDir
            if ($currentSnapshot -ne $lastSnapshot) {
                $lastSnapshot = $currentSnapshot
                $now = [DateTime]::UtcNow
                if (($now - $lastRestartTime).TotalSeconds -ge 3) {
                    Write-Log "=== Image directory changed - restarting backend ==="
                    if ($uvicornProcess -and -not $uvicornProcess.HasExited) {
                        $uvicornProcess.Kill()
                        $null = $uvicornProcess.WaitForExit(5000)
                    }
                    $uvicornProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn main:app --reload --port 8000" -WorkingDirectory $SrcDir -NoNewWindow -PassThru -RedirectStandardOutput $uvicornLog -RedirectStandardError "${uvicornLog}.err"
                    $lastRestartTime = $now
                    Write-Log "OK: uvicorn restarted (PID: $($uvicornProcess.Id))"
                    Write-Log "Waiting for uvicorn..."
                    $null = Wait-UvicornReady -LogPath $uvicornLog
                }
            }
        }

        # --- 7b: manual reload (R key) ---
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            if ($key.Key -eq 'R') {
                Write-Log "=== Manual backend reload (R key) ==="
                if ($uvicornProcess -and -not $uvicornProcess.HasExited) {
                    $uvicornProcess.Kill()
                    $null = $uvicornProcess.WaitForExit(5000)
                }
                $uvicornProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn main:app --reload --port 8000" -WorkingDirectory $SrcDir -NoNewWindow -PassThru -RedirectStandardOutput $uvicornLog -RedirectStandardError "${uvicornLog}.err"
                Write-Log "OK: uvicorn restarted (PID: $($uvicornProcess.Id))"
                Write-Log "Waiting for uvicorn..."
                $null = Wait-UvicornReady -LogPath $uvicornLog
                Write-Log "INFO: Vite reconnects to the restarted backend automatically"
            }
        }

        # --- 7c: stop when both processes have exited ---
        $activeProcs = @()
        if ($uvicornProcess -and -not $uvicornProcess.HasExited) { $activeProcs += "uvicorn" }
        if ($npmProcess -and -not $npmProcess.HasExited) { $activeProcs += "npm" }
        if ($activeProcs.Count -eq 0) { break }
    }
} finally {
    Cleanup
}

Write-Log "=== Run Dev - finished ==="
exit 0
