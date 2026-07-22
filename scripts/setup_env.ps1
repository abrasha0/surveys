param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "..")
$LogFile = Join-Path -Path $ProjectRoot -ChildPath "logs\setup_env.log"
$VenvPath = Join-Path -Path $ProjectRoot -ChildPath ".venv"
$RequirementsPath = Join-Path -Path $ProjectRoot -ChildPath "requirements.txt"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

New-Item -Path $LogFile -ItemType File -Force | Out-Null
Write-Log "=== Setup Environment - start ==="
Write-Log "Project root: $ProjectRoot"

# --- Krok 1: Sprawdzenie wersji Pythona ---
Write-Log "Krok 1: Sprawdzanie wersji Pythona..."
try {
    $pyVersion = & python --version 2>&1
    Write-Log "Znaleziono: $pyVersion"

    if ($pyVersion -match 'Python (\d+)\.(\d+)') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
            Write-Log "OK: Python $major.$minor >= 3.12"
        } else {
            throw "Wymagany Python >= 3.12, znaleziono $major.$minor"
        }
    } else {
        throw "Nie rozpoznano wersji Pythona: $pyVersion"
    }
} catch {
    Write-Log "BLAD: $_"
    Write-Log "=== Setup Environment - blad ==="
    exit 1
}

# --- Krok 2: Sprawdzenie pip ---
Write-Log "Krok 2: Sprawdzanie pip..."
try {
    $pipVersion = & python -m pip --version 2>&1
    Write-Log "OK: $pipVersion"
} catch {
    Write-Log "BLAD: pip nie jest dostepny - $_"
    exit 1
}

# --- Krok 3: Utworzenie wirtualnego srodowiska ---
Write-Log "Krok 3: Tworzenie wirtualnego srodowiska w $VenvPath..."

if (Test-Path -LiteralPath $VenvPath) {
    if (-not $Force) {
        Write-Log "UWAGA: Katalog .venv juz istnieje. Uzyj -Force aby nadpisac."
        Write-Log "Pominieto tworzenie .venv (uzywam istniejacego)."
    } else {
        Write-Log "Force: Usuwanie istniejącego .venv..."
        Remove-Item -Path $VenvPath -Recurse -Force
        & python -m venv $VenvPath
        if ($LASTEXITCODE -ne 0) { throw "Blad tworzenia venv (exit code: $LASTEXITCODE)" }
        Write-Log "OK: .venv utworzony od nowa."
    }
} else {
    & python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { throw "Blad tworzenia venv (exit code: $LASTEXITCODE)" }
    Write-Log "OK: .venv utworzony."
}

# --- Krok 4: Aktywacja i upgrade pip ---
Write-Log "Krok 4: Aktywacja .venv i upgrade pip..."

$ActivateScript = Join-Path -Path $VenvPath -ChildPath "Scripts\Activate.ps1"
if (-not (Test-Path -LiteralPath $ActivateScript)) {
    throw "Nie znaleziono skryptu aktywacji: $ActivateScript"
}

$pipPath = Join-Path -Path $VenvPath -ChildPath "Scripts\pip.exe"
$pythonVenv = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"

Write-Log "Upgrade pip..."
& $pythonVenv -m pip install --upgrade pip setuptools wheel 2>&1 | ForEach-Object { Write-Log "  $_" }
if ($LASTEXITCODE -ne 0) { throw "Blad upgrade pip (exit code: $LASTEXITCODE)" }
Write-Log "OK: pip zaktualizowany."

# --- Krok 5: Instalacja requirements ---
Write-Log "Krok 5: Instalacja requirements z $RequirementsPath..."
if (-not (Test-Path -LiteralPath $RequirementsPath)) {
    throw "Nie znaleziono requirements.txt: $RequirementsPath"
}

& $pythonVenv -m pip install -r $RequirementsPath 2>&1 | ForEach-Object { Write-Log "  $_" }
if ($LASTEXITCODE -ne 0) { throw "Blad instalacji requirements (exit code: $LASTEXITCODE)" }
Write-Log "OK: wszystkie pakiety zainstalowane."

# --- Krok 6: Weryfikacja ---
Write-Log "Krok 6: Weryfikacja instalacji..."
$installed = & $pythonVenv -m pip list --format=freeze 2>&1
Write-Log "Zainstalowane pakiety:"
$installed | ForEach-Object { Write-Log "  - $_" }

# Sprawdz kluczowe pakiety
$keyPackages = @("fastapi", "uvicorn", "pydantic", "Pillow", "httpx")
foreach ($pkg in $keyPackages) {
    $found = $installed -like "$pkg==*"
    if ($found) {
        Write-Log "OK: $pkg obecny ($found)"
    } else {
        Write-Log "OSTROZNE: $pkg nie znaleziony na liscie!"
    }
}

# --- Krok 7: Instalacja zależności frontendu ---
Write-Log "Krok 7: Instalacja zaleznosci frontendu (npm)..."
$FrontendDir = Join-Path -Path $ProjectRoot -ChildPath "src_ui"
if (-not (Test-Path -LiteralPath $FrontendDir)) {
    Write-Log "OSTROZNE: Katalog src_ui nie istnieje - pomijam npm install"
} else {
    try {
        $nodeVersion = & node --version 2>&1
        Write-Log "Znaleziono: $nodeVersion"
        $npmVersion = & npm --version 2>&1
        Write-Log "npm: $npmVersion"
        & npm install --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }
        if ($LASTEXITCODE -ne 0) { throw "npm install nie powiodl sie (exit code: $LASTEXITCODE)" }
        Write-Log "OK: zaleznosci frontendu zainstalowane."
    } catch {
        Write-Log "OSTROZNE: node/npm nie znajduja sie w PATH - pomijam npm install"
        Write-Log "Zainstaluj Node.js >=18: https://nodejs.org/"
    }
}

# --- Krok 8: Weryfikacja Node.js >= 18 ---
Write-Log "Krok 8: Sprawdzanie Node.js >= 18..."
try {
    $nodeVersion = & node --version 2>&1
    if ($nodeVersion -match 'v(\d+)\.') {
        $nodeMajor = [int]$Matches[1]
        if ($nodeMajor -lt 18) {
            Write-Log "OSTROZNE: Node.js $nodeMajor < 18 (Vite 8 wymaga >= 18)"
        } else {
            Write-Log "OK: Node.js $nodeVersion"
        }
    }
} catch {
    Write-Log "OSTROZNE: Node.js nie znaleziony w PATH - pomijam weryfikacje"
}

# --- Krok 9: Weryfikacja src/main.py ---
Write-Log "Krok 9: Sprawdzanie src/main.py..."
$MainPy = Join-Path -Path $ProjectRoot -ChildPath "src\main.py"
if (Test-Path -LiteralPath $MainPy) {
    Write-Log "OK: $MainPy istnieje"
} else {
    Write-Log "OSTROZNE: Nie znaleziono src/main.py - FastAPI entry point brak"
}

Write-Log "=== Setup Environment - zakonczony pomyslnie ==="
Write-Log ""
Write-Log "Aby aktywowac srodowisko recznie:"
Write-Log "  .venv\Scripts\Activate.ps1"
Write-Log ""
Write-Log "Uruchomienie deweloperskie (API + frontend hot-reload):"
Write-Log "  .\scripts\run_dev.ps1"
Write-Log ""
Write-Log "Uruchomienie produkcyjne (API + frontend static na jednym porcie):"
Write-Log "  .\scripts\full_setup.ps1"
Write-Log ""
Write-Log "Architektura: FastAPI na porcie 8000 serwuje API i statyczny frontend (dist/).
Write-Log "W dev: dodatkowo Vite na porcie 5173 z proxy /api -> localhost:8000."

exit 0
