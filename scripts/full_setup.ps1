param(
    [switch]$NoEnv,
    [switch]$NoOllama,
    [switch]$NoDev,
    [switch]$NoTunnel
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "..")
$LogFile = Join-Path -Path $ProjectRoot -ChildPath "logs\full_setup.log"

$ScriptsDir = $PSScriptRoot
$SetupEnvScript = Join-Path -Path $ScriptsDir -ChildPath "setup_env.ps1"
$SetupOllamaScript = Join-Path -Path $ScriptsDir -ChildPath "setup_ollama.ps1"
$RunDevScript = Join-Path -Path $ScriptsDir -ChildPath "run_dev.ps1"
$DeployTunnelScript = Join-Path -Path $ScriptsDir -ChildPath "deploy_tunnel.ps1"

$ollamaProcess = $null
$streamlitProcess = $null
$tunnelProcess = $null

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Cleanup {
    Write-Log "=== Cleanup: zatrzymywanie procesow ==="
    
    $tunnelProc = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
    if ($tunnelProc) {
        Write-Log "Zatrzymywanie cloudflared..."
        $tunnelProc | Stop-Process -Force
    }
    
    $streamlitProc = Get-Process -Name "streamlit" -ErrorAction SilentlyContinue
    if ($streamlitProc) {
        Write-Log "Zatrzymywanie Streamlit..."
        $streamlitProc | Stop-Process -Force
    }
    
    $ollamaProc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if ($ollamaProc) {
        Write-Log "Zatrzymywanie Ollama..."
        $ollamaProc | Stop-Process -Force
    }
    
    Write-Log "=== Cleanup zakonczony ==="
}

# Register cleanup on exit
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup } | Out-Null

# Trap Ctrl+C
$exitHandler = {
    Write-Log ""
    Write-Log "Przerwano przez uzytkownika. Czyszczenie..."
    Cleanup
    exit 0
}
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $exitHandler | Out-Null

New-Item -Path $LogFile -ItemType File -Force | Out-Null
Write-Log "=== Full Setup - start ==="
Write-Log "Flagi: NoEnv=$NoEnv NoOllama=$NoOllama NoDev=$NoDev NoTunnel=$NoTunnel"

# --- Krok 1: Srodowisko Python ---
if (-not $NoEnv) {
    Write-Log "=== Krok 1/4: Konfiguracja srodowiska Python ==="
    if (Test-Path -LiteralPath $SetupEnvScript) {
        & $SetupEnvScript
        if ($LASTEXITCODE -ne 0) {
            Write-Log "BLAD: setup_env.ps1 nie powiodl sie"
            Cleanup
            exit 1
        }
        Write-Log "OK: Srodowisko Python gotowe"
    } else {
        Write-Log "OSTROZNE: Nie znaleziono $SetupEnvScript - pomijam"
    }
} else {
    Write-Log "Krok 1/4: Pominieto (-NoEnv)"
}

# --- Krok 2: Ollama ---
if (-not $NoOllama) {
    Write-Log "=== Krok 2/4: Konfiguracja Ollamy ==="
    if (Test-Path -LiteralPath $SetupOllamaScript) {
        & $SetupOllamaScript
        if ($LASTEXITCODE -ne 0) {
            Write-Log "BLAD: setup_ollama.ps1 nie powiodl sie"
            Cleanup
            exit 1
        }
        Write-Log "OK: Ollama gotowa"
    } else {
        Write-Log "OSTROZNE: Nie znaleziono $SetupOllamaScript - pomijam"
    }
} else {
    Write-Log "Krok 2/4: Pominieto (-NoOllama)"
}

# --- Krok 3: Uruchomienie aplikacji ---
if (-not $NoDev) {
    Write-Log "=== Krok 3/4: Uruchamianie aplikacji Streamlit ==="
    $streamlitLog = Join-Path -Path $ProjectRoot -ChildPath "logs\streamlit_full.log"
    
    if (Test-Path -LiteralPath $RunDevScript) {
        try {
            $streamlitProcess = Start-Process -FilePath "powershell" -ArgumentList "-File `"$RunDevScript`"" -NoNewWindow -PassThru -RedirectStandardOutput $streamlitLog -RedirectStandardError "${streamlitLog}.err"
            Write-Log "OK: Streamlit uruchomiony (PID: $($streamlitProcess.Id))"
            Write-Log "Log: $streamlitLog"
        } catch {
            Write-Log "BLAD: Nie udalo sie uruchomic run_dev.ps1 - $_"
            Cleanup
            exit 1
        }
    } else {
        Write-Log "OSTROZNE: Nie znaleziono $RunDevScript - pomijam"
    }
} else {
    Write-Log "Krok 3/4: Pominieto (-NoDev)"
}

# --- Krok 4: Tunel Cloudflare ---
if (-not $NoTunnel) {
    Write-Log "=== Krok 4/4: Uruchamianie tunelu Cloudflare ==="
    
    Start-Sleep -Seconds 3
    
    if (Test-Path -LiteralPath $DeployTunnelScript) {
        try {
            $tunnelLog = Join-Path -Path $ProjectRoot -ChildPath "logs\tunnel_full.log"
            $tunnelProcess = Start-Process -FilePath "powershell" -ArgumentList "-File `"$DeployTunnelScript`"" -NoNewWindow -PassThru -RedirectStandardOutput $tunnelLog -RedirectStandardError "${tunnelLog}.err"
            Write-Log "OK: Tunel uruchomiony (PID: $($tunnelProcess.Id))"
            Write-Log "Log: $tunnelLog"
            
            Start-Sleep -Seconds 8
            
            $tunnelUrlFile = Join-Path -Path $ProjectRoot -ChildPath "logs\tunnel_url.txt"
            if (Test-Path -LiteralPath $tunnelUrlFile) {
                $tunnelUrl = Get-Content -Path $tunnelUrlFile -Raw
                Write-Log "URL tunelu: $tunnelUrl"
            } else {
                Write-Log "OSTROZNE: URL tunelu nie jest jeszcze dostepny"
                Write-Log "Sprawdz log tunelu: $tunnelLog"
            }
        } catch {
            Write-Log "BLAD: Nie udalo sie uruchomic deploy_tunnel.ps1 - $_"
            Cleanup
            exit 1
        }
    } else {
        Write-Log "OSTROZNE: Nie znaleziono $DeployTunnelScript - pomijam"
    }
} else {
    Write-Log "Krok 4/4: Pominieto (-NoTunnel)"
}

# --- Podsumowanie ---
Write-Log ""
Write-Log "========================================"
Write-Log "  AnkieterAI - Gotowe!"
Write-Log "========================================"
Write-Log "  Aplikacja lokalna: http://localhost:8501"

if (-not $NoTunnel -and $tunnelUrl) {
    Write-Log "  Tunel publiczny:   $tunnelUrl"
}

Write-Log "  Haslo:             a"

$modelName = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "deepseek-ocr" }
Write-Log "  Model:             $modelName"
Write-Log "========================================"
Write-Log ""
Write-Log "Nacisnij Ctrl+C aby zatrzymac wszystkie procesy."
Write-Log ""

Write-Log "=== Full Setup - zakonczony pomyslnie ==="

# Keep script running to maintain child processes
try {
    while ($true) {
        Start-Sleep -Seconds 10
        $activeProcs = @()
        if ($streamlitProcess -and -not $streamlitProcess.HasExited) { $activeProcs += "Streamlit" }
        if ($tunnelProcess -and -not $tunnelProcess.HasExited) { $activeProcs += "Tunnel" }
        if ($activeProcs.Count -eq 0) { break }
    }
} finally {
    Cleanup
}

exit 0
