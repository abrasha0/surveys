param(
    [switch]$NoTunnel,
    # Directory where cloudflared.exe is looked up and, if missing, installed.
    [string]$CloudflaredDir = "C:\tools"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "..")
$LogFile = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\run_prod.log"
$VenvPath = Join-Path -Path $ProjectRoot -ChildPath ".venv"
$TunnelUrlFile = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\tunnel_url.txt"
$CloudflaredPath = Join-Path -Path $CloudflaredDir -ChildPath "cloudflared.exe"

$activePids = @{}

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Read-Config {
    param([string]$ConfigPath)
    if (-not (Test-Path -LiteralPath $ConfigPath)) { return $null }
    $PythonExe = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"
    $script = @"
import yaml, json, sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)
print(json.dumps(cfg))
"@
    try {
        $json = & $PythonExe -c $script $ConfigPath 2>&1
        return ($json | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Track-Process {
    param([string]$Name, [System.Diagnostics.Process]$Process)
    if ($Process -and -not $Process.HasExited) {
        $activePids[$Name] = $Process
    }
}

function Cleanup {
    Write-Log "=== Cleanup: stopping processes ==="
    foreach ($entry in $activePids.GetEnumerator()) {
        $proc = $entry.Value
        if ($proc -and -not $proc.HasExited) {
            Write-Log "Stopping $($entry.Key) (PID: $($proc.Id))..."
            try { $proc.Kill() } catch { }
        }
    }
    $tunnelProc = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
    if ($tunnelProc) {
        Write-Log "Stopping cloudflared..."
        $tunnelProc | Stop-Process -Force
    }
    Write-Log "=== Cleanup finished ==="
}

New-Item -Path $LogFile -ItemType File -Force | Out-Null
Write-Log "=== Run Prod - start ==="
Write-Log "Flags: NoTunnel=$NoTunnel CloudflaredDir=$CloudflaredDir"

$config = Read-Config -ConfigPath (Join-Path -Path $ProjectRoot -ChildPath "config.yaml")
$cfgPassword = ""
$cfgVlm = "moondream"
$cfgText = "llama3.2:3b"
if ($config) {
    if ($config.app -and $config.app.password) { $cfgPassword = $config.app.password }
    if ($config.ai) {
        if ($config.ai.vlm_model) { $cfgVlm = $config.ai.vlm_model }
        if ($config.ai.text_model) { $cfgText = $config.ai.text_model }
    }
}

try {
    # ============================================================
    # Step 1: Ollama
    # ============================================================
    Write-Log "=== Step 1/5: checking Ollama ==="
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) {
            Write-Log "OK: Ollama responds"
        } else {
            throw "Ollama returned status $($r.StatusCode)"
        }
    } catch {
        Write-Log "ERROR: Ollama does not respond on port 11434."
        Write-Log "Run first: .\scripts\full_setup.ps1"
        exit 1
    }

    # ============================================================
    # Step 2: .venv and password
    # ============================================================
    Write-Log "=== Step 2/5: checking .venv ==="
    if (-not (Test-Path -LiteralPath $VenvPath)) {
        Write-Log "ERROR: .venv does not exist."
        Write-Log "Run first: .\scripts\full_setup.ps1"
        exit 1
    }
    Write-Log "OK: .venv exists"
    if (-not $cfgPassword -and -not $env:ANKIETER_APP_PASSWORD) {
        Write-Log "ERROR: app.password is not set in config.yaml -- the backend does not start without a password."
        Write-Log "Copy configs\config.yaml.example to config.yaml and set app.password."
        exit 1
    }

    # ============================================================
    # Step 3: build the frontend
    # ============================================================
    Write-Log "=== Step 3/5: building the frontend ==="
    $FrontendDir = Join-Path -Path $ProjectRoot -ChildPath "src\frontend"
    $DistDir = Join-Path -Path $ProjectRoot -ChildPath "working_vault\dist"
    $FrontendDist = Join-Path -Path $FrontendDir -ChildPath "dist"

    if (-not (Test-Path -LiteralPath $FrontendDir)) {
        throw "src/frontend directory not found"
    }

    Write-Log "npm install..."
    & npm install --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }
    if ($LASTEXITCODE -ne 0) { throw "npm install failed" }

    Write-Log "npm run build..."
    & npm run build --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }

    if (-not (Test-Path -LiteralPath $FrontendDist)) {
        throw "$FrontendDist does not exist after the build -- check the npm run build output"
    }

    if (Test-Path -LiteralPath $DistDir) {
        Remove-Item -Path $DistDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
    Copy-Item -Path "$FrontendDist\*" -Destination $DistDir -Recurse -Force

    $indexHtml = Join-Path -Path $DistDir -ChildPath "index.html"
    if (-not (Test-Path -LiteralPath $indexHtml)) {
        throw "$indexHtml is missing after the copy -- the frontend build is incomplete"
    }
    Write-Log "OK: frontend built and copied to $DistDir"

    # ============================================================
    # Step 4: uvicorn
    # ============================================================
    Write-Log "=== Step 4/5: starting uvicorn ==="
    $PythonExe = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"
    $uvicornLog = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\uvicorn_prod.log"
    $SrcDir = Join-Path -Path $ProjectRoot -ChildPath "src\backend"

    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "python.exe not found in .venv: $PythonExe"
    }

    $uvicornProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn main:app --port 8000" -WorkingDirectory $SrcDir -NoNewWindow -PassThru -RedirectStandardOutput $uvicornLog -RedirectStandardError "${uvicornLog}.err"
    Track-Process -Name "Uvicorn" -Process $uvicornProcess
    Write-Log "OK: uvicorn started (PID: $($uvicornProcess.Id))"

    # Wait for the API
    Write-Log "Waiting for the API..."
    $apiReady = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/auth/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { $apiReady = $true; break }
        } catch { }
    }
    if (-not $apiReady) {
        throw "API does not respond after 20 s"
    }
    Write-Log "OK: API ready at http://localhost:8000"

    # Check that the frontend is served
    try {
        $fr = Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 3
        $contentType = $fr.Headers["Content-Type"]
        if ($fr.StatusCode -eq 200 -and $contentType -match "text/html") {
            Write-Log "OK: frontend served at http://localhost:8000"
        } else {
            Write-Log "WARNING: / returns $($fr.StatusCode) Content-Type=$contentType"
        }
    } catch {
        Write-Log "WARNING: / does not respond -- $_"
    }

    # ============================================================
    # Step 5: Cloudflare tunnel
    # ============================================================
    $tunnelUrl = $null
    if (-not $NoTunnel) {
        Write-Log "=== Step 5/5: Cloudflare tunnel ==="

        $cfPath = (Get-Command "cloudflared" -ErrorAction SilentlyContinue).Source
        if (-not $cfPath) {
            if (Test-Path -LiteralPath $CloudflaredPath) {
                $cfPath = $CloudflaredPath
                Write-Log "Found cloudflared: $cfPath"
            }
        }
        if (-not $cfPath) {
            Write-Log "cloudflared not found. Downloading..."
            $url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
            $tmpDst = "$env:TEMP\cloudflared.exe"
            try {
                Invoke-WebRequest -Uri $url -OutFile $tmpDst -UseBasicParsing -TimeoutSec 60
                Write-Log "OK: cloudflared downloaded"
            } catch {
                Write-Log "ERROR: failed to download cloudflared -- $_"
                Write-Log "Download it manually: https://github.com/cloudflare/cloudflared/releases/latest"
                Write-Log "Save it as: $CloudflaredPath"
                exit 1
            }
            if (-not (Test-Path -LiteralPath $CloudflaredDir)) {
                New-Item -ItemType Directory -Path $CloudflaredDir -Force | Out-Null
            }
            Move-Item -Path $tmpDst -Destination $CloudflaredPath -Force
            Write-Log "OK: cloudflared installed at $CloudflaredPath"
            $cfPath = $CloudflaredPath
            $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
            if ($currentPath -notlike "*$CloudflaredDir*") {
                [Environment]::SetEnvironmentVariable("Path", "$currentPath;$CloudflaredDir", "User")
            }
            $env:Path = "$env:Path;$CloudflaredDir"
        } else {
            Write-Log "Found cloudflared: $cfPath"
        }

        $dateStr = Get-Date -Format "yyyyMMdd_HHmmss"
        $tunnelLog = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\tunnel_${dateStr}.log"
        Write-Log "Starting cloudflared tunnel --url http://localhost:8000"
        $tunnelProcess = Start-Process -FilePath $cfPath -ArgumentList "tunnel --url http://localhost:8000" -NoNewWindow -PassThru -RedirectStandardOutput $tunnelLog -RedirectStandardError "${tunnelLog}.err"
        Track-Process -Name "Cloudflare" -Process $tunnelProcess

        Write-Log "Waiting for the tunnel URL (up to 60 s)..."
        Start-Sleep -Seconds 4
        $tunnelErrLog = "${tunnelLog}.err"
        for ($i = 0; $i -lt 20; $i++) {
            Start-Sleep -Seconds 3
            foreach ($lf in @($tunnelLog, $tunnelErrLog)) {
                if (Test-Path -LiteralPath $lf) {
                    $content = Get-Content -Path $lf -Raw -ErrorAction SilentlyContinue
                    if ($content -and $content -match 'https://[\w.-]+\.trycloudflare\.com') {
                        $tunnelUrl = $Matches[0]
                        break
                    }
                }
            }
            if ($tunnelUrl) { break }
        }

        if ($tunnelUrl) {
            Write-Log "OK: tunnel active"
            Write-Log "URL: $tunnelUrl"
            $tunnelUrl | Set-Content -Path $TunnelUrlFile -Force
        } else {
            Write-Log "WARNING: no tunnel URL after 60 s. Check the log: $tunnelLog"
        }
    } else {
        Write-Log "=== Step 5/5: tunnel skipped (-NoTunnel) ==="
    }

    # ============================================================
    # Summary
    # ============================================================
    Write-Log ""
    Write-Log "========================================"
    Write-Log "  AnkieterAI - ready"
    Write-Log "========================================"
    Write-Log "  Local app:         http://localhost:8000"

    if ($tunnelUrl) {
        Write-Log "  Public tunnel:     $tunnelUrl"
    }

    $passwordStatus = if ($env:ANKIETER_APP_PASSWORD) { "set (ANKIETER_APP_PASSWORD)" } elseif ($cfgPassword) { "set (config.yaml)" } else { "not set" }
    Write-Log "  Password:          $passwordStatus"
    Write-Log "  Models:            VLM=$cfgVlm  Text=$cfgText"
    Write-Log "========================================"
    Write-Log ""
    Write-Log "Press Ctrl+C to stop all processes."
    Write-Log ""

    Write-Log "=== Run Prod - started ==="

    $lastTunnelCheck = $null

    while ($true) {
        Start-Sleep -Seconds 10
        $activeCount = 0
        foreach ($entry in $activePids.GetEnumerator()) {
            if ($entry.Value -and -not $entry.Value.HasExited) { $activeCount++ }
        }
        if ($activeCount -eq 0) { break }

        # Tunnel health check every 30 s
        if ($tunnelUrl) {
            $now = Get-Date
            if (-not $lastTunnelCheck -or (($now - $lastTunnelCheck).TotalSeconds -ge 30)) {
                $lastTunnelCheck = $now
                try {
                    $hc = Invoke-WebRequest -Uri $tunnelUrl -UseBasicParsing -TimeoutSec 10
                    Write-Log "tunnel health: OK (HTTP $($hc.StatusCode))"
                } catch {
                    Write-Log "tunnel health: no response -- $_"
                }
            }
        }
    }
} finally {
    Cleanup
}

Write-Log "=== Run Prod - finished ==="
exit 0
