param(
    [switch]$Force
)

$ProjectRoot = Resolve-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "..")
$LogFile = Join-Path -Path $ProjectRoot -ChildPath "logs\run_dev.log"
$VenvPath = Join-Path -Path $ProjectRoot -ChildPath ".venv"
$SetupEnvScript = Join-Path -Path $PSScriptRoot -ChildPath "setup_env.ps1"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

New-Item -Path $LogFile -ItemType File -Force | Out-Null
Write-Log "=== Run Dev - start ==="

# --- Krok 1: Sprawdzenie Ollamy ---
Write-Log "Krok 1: Sprawdzanie czy Ollama dziala na porcie 11434..."
$ErrorActionPreference = "Stop"
try {
    $r = Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) {
        Write-Log "OK: Ollama odpowiada na http://localhost:11434"
    } else {
        throw "Ollama zwrocila kod $($r.StatusCode)"
    }
} catch {
    Write-Log "BLAD: Ollama nie odpowiada na porcie 11434."
    Write-Log ""
    Write-Log "Uruchom najpierw: .\scripts\setup_ollama.ps1"
    Write-Log ""
    Write-Log "=== Run Dev - blad ==="
    exit 1
}

# --- Krok 2: Sprawdzenie .venv ---
Write-Log "Krok 2: Sprawdzanie wirtualnego srodowiska..."
if (-not (Test-Path -LiteralPath $VenvPath)) {
    Write-Log ".venv nie istnieje. Uruchamiam setup_env.ps1..."
    if (Test-Path -LiteralPath $SetupEnvScript) {
        & $SetupEnvScript -Force
        if ($LASTEXITCODE -ne 0) { throw "setup_env.ps1 nie powiodl sie" }
        Write-Log "OK: .venv utworzony przez setup_env.ps1"
    } else {
        throw "Nie znaleziono setup_env.ps1 w $SetupEnvScript"
    }
} else {
    Write-Log "OK: .venv istnieje"
}
$ErrorActionPreference = "Continue"

# --- Krok 3: Uruchomienie Streamlit ---
Write-Log "Krok 3: Uruchamianie Streamlit..."
$PythonVenv = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"
$Streamlit = Join-Path -Path $VenvPath -ChildPath "Scripts\streamlit.exe"
$MainPy = Join-Path -Path $ProjectRoot -ChildPath "src\main.py"

if (-not (Test-Path -LiteralPath $MainPy)) {
    Write-Log "BLAD: Nie znaleziono src\main.py w $ProjectRoot"
    exit 1
}

Write-Log "Uruchamianie: streamlit run src/main.py --server.port 8501"
Write-Log "Aplikacja dostepna pod adresem: http://localhost:8501"
Write-Log "=== Streamlit przejmuje konsole ==="

& $Streamlit run $MainPy --server.port 8501

Write-Log "=== Run Dev - zakonczony ==="
exit 0
