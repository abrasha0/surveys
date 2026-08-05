param(
    [switch]$NoEnv,
    [switch]$NoOllama,
    [switch]$NoDev,
    [switch]$NoTunnel
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "..")
$LogFile = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\full_setup.log"
$VenvPath = Join-Path -Path $ProjectRoot -ChildPath ".venv"

$ScriptsDir = $PSScriptRoot
$SetupEnvScript = Join-Path -Path $ScriptsDir -ChildPath "setup_env.ps1"
$SetupOllamaScript = Join-Path -Path $ScriptsDir -ChildPath "setup_ollama.ps1"
$DeployTunnelScript = Join-Path -Path $ScriptsDir -ChildPath "deploy_tunnel.ps1"

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
    $script = @"
import yaml, json, sys
with open(sys.argv[1], 'r') as f:
    cfg = yaml.safe_load(f)
print(json.dumps(cfg))
"@
    try {
        $json = & "$VenvPath\Scripts\python.exe" -c $script $ConfigPath 2>&1
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
Write-Log "=== Full Setup - start ==="
Write-Log "Flagi: NoEnv=$NoEnv NoOllama=$NoOllama NoDev=$NoDev NoTunnel=$NoTunnel"

# --- Wczytaj konfiguracje ---
$configPath = Join-Path -Path $ProjectRoot -ChildPath "config.yaml"
$config = Read-Config -ConfigPath $configPath
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
    # --- Krok 1: Srodowisko Python ---
    if (-not $NoEnv) {
        Write-Log "=== Krok 1/5: Konfiguracja srodowiska Python ==="
        if (Test-Path -LiteralPath $SetupEnvScript) {
            & $SetupEnvScript
            if ($LASTEXITCODE -ne 0) {
                throw "setup_env.ps1 nie powiodl sie"
            }
            Write-Log "OK: Srodowisko Python gotowe"
        } else {
            Write-Log "OSTROZNE: Nie znaleziono $SetupEnvScript - pomijam"
        }
    } else {
        Write-Log "Krok 1/5: Pominieto (-NoEnv)"
    }

    # --- Krok 2: Ollama ---
    if (-not $NoOllama) {
        Write-Log "=== Krok 2/5: Konfiguracja Ollamy ==="
        if (Test-Path -LiteralPath $SetupOllamaScript) {
            & $SetupOllamaScript -VlmModel $cfgVlm -TextModel $cfgText
            if ($LASTEXITCODE -ne 0) {
                throw "setup_ollama.ps1 nie powiodl sie"
            }
            Write-Log "OK: Ollama gotowa"
        } else {
            Write-Log "OSTROZNE: Nie znaleziono $SetupOllamaScript - pomijam"
        }
    } else {
        Write-Log "Krok 2/5: Pominieto (-NoOllama)"
    }

    # --- Krok 3: Budowa frontendu ---
    if (-not $NoDev) {
        Write-Log "=== Krok 3/5: Budowa frontendu (npm run build) ==="
        $FrontendDir = Join-Path -Path $ProjectRoot -ChildPath "src\frontend"
        $DistDir = Join-Path -Path $ProjectRoot -ChildPath "working_vault\dist"
        $FrontendDist = Join-Path -Path $FrontendDir -ChildPath "dist"

        if (-not (Test-Path -LiteralPath $FrontendDir)) {
            Write-Log "OSTROZNE: Katalog src/frontend nie istnieje - pomijam budowe frontendu"
        } else {
            try {
                & npm install --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }
                if ($LASTEXITCODE -ne 0) { throw "npm install nie powiodl sie" }
                & npm run build --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }
                if ($LASTEXITCODE -ne 0) { throw "npm run build nie powiodl sie" }
                if (Test-Path -LiteralPath $DistDir) {
                    Remove-Item -Path $DistDir -Recurse -Force
                }
                New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
                Copy-Item -Path "$FrontendDist\*" -Destination $DistDir -Recurse -Force
                Write-Log "OK: Frontend zbudowany i skopiowany do $DistDir"
            } catch {
                Write-Log "BLAD: $_ - pomijam budowe frontendu"
            }
        }
    } else {
        Write-Log "Krok 3/5: Pominieto (-NoDev)"
    }

    # --- Krok 4: Uruchomienie aplikacji ---
    if (-not $NoDev) {
        Write-Log "=== Krok 4/5: Uruchamianie uvicorn (API + frontend static) ==="
        $PythonExe = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"
        $appLog = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\uvicorn_full.log"
        $SrcDir = Join-Path -Path $ProjectRoot -ChildPath "src\backend"

        if (Test-Path -LiteralPath $PythonExe) {
            try {
                $appProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn main:app --port 8000" -WorkingDirectory $SrcDir -NoNewWindow -PassThru -RedirectStandardOutput $appLog -RedirectStandardError "${appLog}.err"
                Track-Process -Name "Uvicorn" -Process $appProcess
                Write-Log "OK: Uvicorn uruchomiony (PID: $($appProcess.Id))"

                # Wait na uvicorn
                Write-Log "Czekam na gotowosc uvicorn..."
                $uvicornReady = $false
                for ($i = 0; $i -lt 15; $i++) {
                    Start-Sleep -Seconds 1
                    try {
                        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/auth/health" -UseBasicParsing -TimeoutSec 2
                        $uvicornReady = $true
                        break
                    } catch { }
                }
                if ($uvicornReady) {
                    Write-Log "OK: API gotowe na http://localhost:8000"
                } else {
                    Write-Log "OSTROZNE: API nie odpowiada po 15s - sprawdz log: $appLog"
                }
            } catch {
                throw "Nie udalo sie uruchomic uvicorn - $_"
            }
        } else {
            throw "Nie znaleziono python.exe w .venv"
        }
    } else {
        Write-Log "Krok 4/5: Pominieto (-NoDev)"
    }

    # --- Krok 5: Tunel Cloudflare (inline) ---
    if (-not $NoTunnel) {
        Write-Log "=== Krok 5/5: Uruchamianie tunelu Cloudflare ==="
        $cfPath = (Get-Command "cloudflared" -ErrorAction SilentlyContinue).Source
        if (-not $cfPath) {
            $cfLocal = "C:\tools\cloudflared.exe"
            if (Test-Path -LiteralPath $cfLocal) { $cfPath = $cfLocal }
        }
        if (-not $cfPath) {
            Write-Log "OSTROZNE: cloudflared nie znaleziony - probuje deploy_tunnel.ps1"
            if (Test-Path -LiteralPath $DeployTunnelScript) {
                & $DeployTunnelScript
            } else {
                Write-Log "OSTROZNE: Nie znaleziono deploy_tunnel.ps1 - pomijam tunel"
            }
        } else {
            $tunnelLog = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\tunnel_full.log"
            $tunnelUrlFile = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\tunnel_url.txt"
            Write-Log "Uruchamianie cloudflared z: $cfPath"
            $tunnelProcess = Start-Process -FilePath $cfPath -ArgumentList "tunnel --url http://localhost:8000" -NoNewWindow -PassThru -RedirectStandardOutput $tunnelLog -RedirectStandardError "${tunnelLog}.err"
            Track-Process -Name "Tunnel" -Process $tunnelProcess
            Start-Sleep -Seconds 6
            $tunnelUrl = $null
            for ($i = 0; $i -lt 20; $i++) {
                if (Test-Path -LiteralPath $tunnelLog) {
                    $content = Get-Content -Path $tunnelLog -Raw
                    if ($content -match 'https://[\w.-]+\.trycloudflare\.com') {
                        $tunnelUrl = $Matches[0]
                        break
                    }
                }
                Start-Sleep -Seconds 3
            }
            if ($tunnelUrl) {
                Write-Log "OK: Tunel aktywny!"
                Write-Log "URL: $tunnelUrl"
                $tunnelUrl | Set-Content -Path $tunnelUrlFile -Force
                Write-Log "URL zapisany do: $tunnelUrlFile"
            } else {
                Write-Log "OSTROZNIE: Nie wykryto URL tunelu. Sprawdz log: $tunnelLog"
            }
        }
    } else {
        Write-Log "Krok 5/5: Pominieto (-NoTunnel)"
    }

    # --- Podsumowanie ---
    Write-Log ""
    Write-Log "========================================"
    Write-Log "  AnkieterAI - Gotowe!"
    Write-Log "========================================"
    Write-Log "  Aplikacja lokalna: http://localhost:8000"

    if (-not $NoTunnel -and $tunnelUrl) {
        Write-Log "  Tunel publiczny:   $tunnelUrl"
    }

    $displayPassword = if ($cfgPassword) { $cfgPassword } else { "(brak - skonfiguruj w config.yaml)" }
    Write-Log "  Haslo:             $displayPassword"
    Write-Log "  Model VLM:         $cfgVlm"
    Write-Log "  Model Text:        $cfgText"
    Write-Log "========================================"
    Write-Log ""
    Write-Log "Nacisnij Ctrl+C aby zatrzymac wszystkie procesy."
    Write-Log ""

    Write-Log "=== Full Setup - zakonczony pomyslnie ==="

    # Keep script running to maintain child processes
    while ($true) {
        Start-Sleep -Seconds 10
        $activeCount = 0
        foreach ($entry in $activePids.GetEnumerator()) {
            if ($entry.Value -and -not $entry.Value.HasExited) { $activeCount++ }
        }
        if ($activeCount -eq 0) { break }
    }
} finally {
    Cleanup
}

exit 0
