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
    Write-Log "=== Cleanup: zatrzymywanie procesow ==="
    foreach ($entry in $activePids.GetEnumerator()) {
        $proc = $entry.Value
        if ($proc -and -not $proc.HasExited) {
            Write-Log "Zatrzymywanie $($entry.Key) (PID: $($proc.Id))..."
            try { $proc.Kill() } catch { }
        }
    }
    $tunnelProc = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
    if ($tunnelProc) {
        Write-Log "Zatrzymywanie cloudflared..."
        $tunnelProc | Stop-Process -Force
    }
    Write-Log "=== Cleanup zakonczony ==="
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
    # Krok 1: Ollama
    # ============================================================
    Write-Log "=== Krok 1/5: Sprawdzanie Ollamy ==="
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) {
            Write-Log "OK: Ollama odpowiada"
        } else {
            throw "Ollama zwrocila kod $($r.StatusCode)"
        }
    } catch {
        Write-Log "BLAD: Ollama nie odpowiada na porcie 11434."
        Write-Log "Uruchom najpierw: .\scripts\full_setup.ps1"
        exit 1
    }

    # ============================================================
    # Krok 2: .venv
    # ============================================================
    Write-Log "=== Krok 2/5: Sprawdzanie .venv ==="
    if (-not (Test-Path -LiteralPath $VenvPath)) {
        Write-Log "BLAD: .venv nie istnieje."
        Write-Log "Uruchom najpierw: .\scripts\full_setup.ps1"
        exit 1
    }
    Write-Log "OK: .venv istnieje"
    if (-not $cfgPassword -and -not $env:ANKIETER_APP_PASSWORD) {
        Write-Log "BLAD: brak hasla (app.password) w config.yaml -- backend nie wystartuje bez hasla."
        Write-Log "Skopiuj configs\config.yaml.example do config.yaml i ustaw app.password."
        exit 1
    }

    # ============================================================
    # Krok 3: Budowa frontendu
    # ============================================================
    Write-Log "=== Krok 3/5: Budowa frontendu ==="
    $FrontendDir = Join-Path -Path $ProjectRoot -ChildPath "src\frontend"
    $DistDir = Join-Path -Path $ProjectRoot -ChildPath "working_vault\dist"
    $FrontendDist = Join-Path -Path $FrontendDir -ChildPath "dist"

    if (-not (Test-Path -LiteralPath $FrontendDir)) {
        throw "Nie znaleziono src/frontend"
    }

    Write-Log "npm install..."
    & npm install --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }
    if ($LASTEXITCODE -ne 0) { throw "npm install nie powiodl sie" }

    Write-Log "npm run build..."
    & npm run build --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }
    if ($LASTEXITCODE -ne 0) { throw "npm run build nie powiodl sie" }

    if (-not (Test-Path -LiteralPath $FrontendDist)) {
        throw "Katalog $FrontendDist nie istnieje po buildzie -- sprawdz logi npm run build"
    }

    if (Test-Path -LiteralPath $DistDir) {
        Remove-Item -Path $DistDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
    Copy-Item -Path "$FrontendDist\*" -Destination $DistDir -Recurse -Force

    $indexHtml = Join-Path -Path $DistDir -ChildPath "index.html"
    if (-not (Test-Path -LiteralPath $indexHtml)) {
        throw "Po kopiowaniu brak $indexHtml -- dystrybucja frontendu niekompletna"
    }
    Write-Log "OK: Frontend zbudowany i skopiowany do $DistDir"

    # ============================================================
    # Krok 4: Uvicorn
    # ============================================================
    Write-Log "=== Krok 4/5: Uruchamianie uvicorn ==="
    $PythonExe = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"
    $uvicornLog = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\uvicorn_prod.log"
    $SrcDir = Join-Path -Path $ProjectRoot -ChildPath "src\backend"

    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "Nie znaleziono python.exe w .venv: $PythonExe"
    }

    $uvicornProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn main:app --port 8000" -WorkingDirectory $SrcDir -NoNewWindow -PassThru -RedirectStandardOutput $uvicornLog -RedirectStandardError "${uvicornLog}.err"
    Track-Process -Name "Uvicorn" -Process $uvicornProcess
    Write-Log "OK: Uvicorn uruchomiony (PID: $($uvicornProcess.Id))"

    # Wait na API
    Write-Log "Czekam na API..."
    $apiReady = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/auth/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { $apiReady = $true; break }
        } catch { }
    }
    if (-not $apiReady) {
        throw "API nie odpowiada po 20s"
    }
    Write-Log "OK: API gotowe na http://localhost:8000"

    # Sprawdz frontend
    try {
        $fr = Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 3
        $contentType = $fr.Headers["Content-Type"]
        if ($fr.StatusCode -eq 200 -and $contentType -match "text/html") {
            Write-Log "OK: Frontend serwowany na http://localhost:8000"
        } else {
            Write-Log "OSTROZNIE: / zwraca $($fr.StatusCode) Content-Type=$contentType"
        }
    } catch {
        Write-Log "OSTROZNIE: / nie odpowiada -- $_"
    }

    # ============================================================
    # Krok 5: Tunel Cloudflare
    # ============================================================
    $tunnelUrl = $null
    if (-not $NoTunnel) {
        Write-Log "=== Krok 5/5: Tunel Cloudflare ==="

        $cfPath = (Get-Command "cloudflared" -ErrorAction SilentlyContinue).Source
        if (-not $cfPath) {
            if (Test-Path -LiteralPath $CloudflaredPath) {
                $cfPath = $CloudflaredPath
                Write-Log "Znaleziono cloudflared: $cfPath"
            }
        }
        if (-not $cfPath) {
            Write-Log "cloudflared nie znaleziony. Pobieram..."
            $url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
            $tmpDst = "$env:TEMP\cloudflared.exe"
            try {
                Invoke-WebRequest -Uri $url -OutFile $tmpDst -UseBasicParsing -TimeoutSec 60
                Write-Log "OK: pobrano cloudflared"
            } catch {
                Write-Log "BLAD: nie udalo sie pobrac cloudflared -- $_"
                Write-Log "Sprobuj recznie: https://github.com/cloudflare/cloudflared/releases/latest"
                Write-Log "Umiesc w: $CloudflaredPath"
                exit 1
            }
            if (-not (Test-Path -LiteralPath $CloudflaredDir)) {
                New-Item -ItemType Directory -Path $CloudflaredDir -Force | Out-Null
            }
            Move-Item -Path $tmpDst -Destination $CloudflaredPath -Force
            Write-Log "OK: cloudflared zainstalowany w $CloudflaredPath"
            $cfPath = $CloudflaredPath
            $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
            if ($currentPath -notlike "*$CloudflaredDir*") {
                [Environment]::SetEnvironmentVariable("Path", "$currentPath;$CloudflaredDir", "User")
            }
            $env:Path = "$env:Path;$CloudflaredDir"
        } else {
            Write-Log "Znaleziono cloudflared: $cfPath"
        }

        $dateStr = Get-Date -Format "yyyyMMdd_HHmmss"
        $tunnelLog = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\tunnel_${dateStr}.log"
        Write-Log "Uruchamianie cloudflared tunnel --url http://localhost:8000"
        $tunnelProcess = Start-Process -FilePath $cfPath -ArgumentList "tunnel --url http://localhost:8000" -NoNewWindow -PassThru -RedirectStandardOutput $tunnelLog -RedirectStandardError "${tunnelLog}.err"
        Track-Process -Name "Cloudflare" -Process $tunnelProcess

        Write-Log "Czekam na URL tunelu (do 60s)..."
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
            Write-Log "OK: Tunel aktywny"
            Write-Log "URL: $tunnelUrl"
            $tunnelUrl | Set-Content -Path $TunnelUrlFile -Force
        } else {
            Write-Log "OSTROZNIE: Nie wykryto URL tunelu po 60s. Sprawdz log: $tunnelLog"
        }
    } else {
        Write-Log "=== Krok 5/5: Tunel pominieto (-NoTunnel) ==="
    }

    # ============================================================
    # Podsumowanie
    # ============================================================
    Write-Log ""
    Write-Log "========================================"
    Write-Log "  AnkieterAI - Gotowe!"
    Write-Log "========================================"
    Write-Log "  Aplikacja lokalna: http://localhost:8000"

    if ($tunnelUrl) {
        Write-Log "  Tunel publiczny:   $tunnelUrl"
    }

    $passwordStatus = if ($env:ANKIETER_APP_PASSWORD) { "ustawione (ANKIETER_APP_PASSWORD)" } elseif ($cfgPassword) { "ustawione (config.yaml)" } else { "brak" }
    Write-Log "  Haslo:             $passwordStatus"
    Write-Log "  Modele:            VLM=$cfgVlm  Text=$cfgText"
    Write-Log "========================================"
    Write-Log ""
    Write-Log "Nacisnij Ctrl+C aby zatrzymac wszystkie procesy."
    Write-Log ""

    Write-Log "=== Run Prod - uruchomiony pomyslnie ==="

    $lastTunnelCheck = $null

    while ($true) {
        Start-Sleep -Seconds 10
        $activeCount = 0
        foreach ($entry in $activePids.GetEnumerator()) {
            if ($entry.Value -and -not $entry.Value.HasExited) { $activeCount++ }
        }
        if ($activeCount -eq 0) { break }

        # Tunnel health check co 30s
        if ($tunnelUrl) {
            $now = Get-Date
            if (-not $lastTunnelCheck -or (($now - $lastTunnelCheck).TotalSeconds -ge 30)) {
                $lastTunnelCheck = $now
                try {
                    $hc = Invoke-WebRequest -Uri $tunnelUrl -UseBasicParsing -TimeoutSec 10
                    Write-Log "tunnel health: OK (HTTP $($hc.StatusCode))"
                } catch {
                    Write-Log "tunnel health: nie odpowiada -- $_"
                }
            }
        }
    }
} finally {
    Cleanup
}

Write-Log "=== Run Prod - zakonczony ==="
exit 0