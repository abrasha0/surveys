param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "..")
$LogFile = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\full_setup.log"
$VenvPath = Join-Path -Path $ProjectRoot -ChildPath ".venv"
$RequirementsPath = Join-Path -Path $ProjectRoot -ChildPath "requirements.txt"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Read-Config {
    param([string]$ConfigPath)
    if (-not (Test-Path -LiteralPath $ConfigPath)) {
        $ConfigExample = Join-Path -Path $ProjectRoot -ChildPath "configs\config.yaml.example"
        if (-not (Test-Path -LiteralPath $ConfigExample)) {
            Write-Log "OSTROZNIE: brak config.yaml i configs\config.yaml.example"
            return $null
        }
        Write-Log "config.yaml nie istnieje -- uzywam configs\config.yaml.example"
        $ConfigPath = $ConfigExample
    }
    $PythonExe = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $PythonExe)) { $PythonExe = "python" }
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

New-Item -Path $LogFile -ItemType File -Force | Out-Null
Write-Log "=== Full Setup - Environment ==="
Write-Log "Project root: $ProjectRoot"
if ($Force) { Write-Log "Tryb Force: wymuszanie reinstalacji .venv" }

# ============================================================
# Krok 1: Python >= 3.12
# ============================================================
Write-Log "=== Krok 1/9: Python >= 3.12 ==="
try {
    $pyVersion = & python --version 2>&1
    Write-Log "Znaleziono: $pyVersion"
    if ($pyVersion -match 'Python (\d+)\.(\d+)') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
            Write-Log "OK: Python $major.$minor"
        } else {
            throw "Wymagany Python >= 3.12, znaleziono $major.$minor"
        }
    } else {
        throw "Nie rozpoznano wersji: $pyVersion"
    }
} catch {
    Write-Log "BLAD: $_"
    exit 1
}

# ============================================================
# Krok 2: .venv
# ============================================================
Write-Log "=== Krok 2/9: Wirtualne srodowisko ==="
if (Test-Path -LiteralPath $VenvPath) {
    if ($Force) {
        Write-Log "Force: usuwanie istniejacego .venv..."
        Remove-Item -Path $VenvPath -Recurse -Force
        & python -m venv $VenvPath
        if ($LASTEXITCODE -ne 0) { throw "Blad tworzenia venv" }
        Write-Log "OK: .venv utworzony od nowa"
    } else {
        Write-Log "OK: .venv juz istnieje"
    }
} else {
    & python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { throw "Blad tworzenia venv" }
    Write-Log "OK: .venv utworzony"
}

$PythonExe = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Nie znaleziono python.exe w .venv: $PythonExe"
}

Write-Log "Upgrade pip..."
& $PythonExe -m pip install --upgrade pip setuptools wheel 2>&1 | ForEach-Object { Write-Log "  $_" }
if ($LASTEXITCODE -ne 0) { Write-Log "OSTROZNIE: upgrade pip nieudany (kontynuuje)" }

# ============================================================
# Krok 3: pip install requirements.txt
# ============================================================
Write-Log "=== Krok 3/9: Instalacja pakietow Python ==="
if (-not (Test-Path -LiteralPath $RequirementsPath)) {
    throw "Nie znaleziono requirements.txt: $RequirementsPath"
}
& $PythonExe -m pip install -r $RequirementsPath 2>&1 | ForEach-Object { Write-Log "  $_" }
if ($LASTEXITCODE -ne 0) { throw "pip install nie powiodl sie" }
Write-Log "OK: pakiety Python zainstalowane"

# Odczytaj konfiguracje (PyYAML dopiero teraz dostepne w .venv)
$config = Read-Config -ConfigPath (Join-Path -Path $ProjectRoot -ChildPath "config.yaml")
$vlmModel = "moondream"
$textModel = "llama3.2:3b"
if ($config -and $config.ai) {
    if ($config.ai.vlm_model) { $vlmModel = $config.ai.vlm_model }
    if ($config.ai.text_model) { $textModel = $config.ai.text_model }
}
Write-Log "Modele z config.yaml: VLM=$vlmModel  Text=$textModel"

# ============================================================
# Krok 4: Node.js >= 18 + npm
# ============================================================
Write-Log "=== Krok 4/9: Node.js i npm ==="
$nodePath = (Get-Command "node" -ErrorAction SilentlyContinue).Source
$npmPath = (Get-Command "npm" -ErrorAction SilentlyContinue).Source
if (-not $nodePath) {
    Write-Log "BLAD: Node.js nie znaleziony w PATH."
    Write-Log "       Zainstaluj Node.js >=18 recznie: https://nodejs.org/"
    Write-Log "       Po instalacji uruchom ten skrypt ponownie."
    exit 1
}
if (-not $npmPath) {
    Write-Log "BLAD: npm nie znaleziony w PATH."
    exit 1
}
try {
    $nodeVersion = & node --version 2>&1
    if ($nodeVersion -match 'v(\d+)\.') {
        $nodeMajor = [int]$Matches[1]
        if ($nodeMajor -lt 18) {
            Write-Log "BLAD: Node.js $nodeMajor < 18. Zainstaluj Node.js >=18: https://nodejs.org/"
            exit 1
        }
    }
    Write-Log "OK: Node $nodeVersion, npm $(& npm --version 2>&1)"
} catch {
    Write-Log "BLAD: nie udalo sie sprawdzic wersji Node.js"
    exit 1
}

# ============================================================
# Krok 5: npm install (frontend)
# ============================================================
Write-Log "=== Krok 5/9: Instalacja zaleznosci frontendu ==="
$FrontendDir = Join-Path -Path $ProjectRoot -ChildPath "src\frontend"
if (-not (Test-Path -LiteralPath $FrontendDir)) {
    throw "Nie znaleziono src/frontend"
}
$nodeModules = Join-Path -Path $FrontendDir -ChildPath "node_modules"
if (Test-Path -LiteralPath $nodeModules) {
    Write-Log "node_modules juz istnieje -- uruchamiam npm install (sprawdzi aktualizacje)"
}
& npm install --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }
if ($LASTEXITCODE -ne 0) { throw "npm install nie powiodl sie" }
Write-Log "OK: zaleznosci frontendu zainstalowane"

# ============================================================
# Krok 6: Ollama -- lokalizacja
# ============================================================
Write-Log "=== Krok 6/9: Ollama ==="
$ollamaSearchPaths = @(
    "C:\Program Files\Ollama\ollama.exe",
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
)
$ollamaPath = (Get-Command "ollama" -ErrorAction SilentlyContinue).Source
if (-not $ollamaPath) {
    foreach ($p in $ollamaSearchPaths) {
        if (Test-Path -LiteralPath $p) { $ollamaPath = $p; break }
    }
}
if (-not $ollamaPath) {
    Write-Log "Ollama nie znaleziona. Pobieram instalator..."
    $url = "https://ollama.com/download/OllamaSetup.exe"
    $dst = "$env:TEMP\OllamaSetup.exe"
    (New-Object System.Net.WebClient).DownloadFile($url, $dst)
    Write-Log "Instalacja cicha..."
    Start-Process $dst -ArgumentList "/S" -Wait -PassThru | Out-Null
    $ollamaPath = "C:\Program Files\Ollama\ollama.exe"
    if (-not (Test-Path -LiteralPath $ollamaPath)) {
        throw "Instalacja Ollamy nieudana -- zainstaluj recznie: https://ollama.com/download"
    }
    Write-Log "OK: Ollama zainstalowana"
}
Write-Log "Ollama: $ollamaPath"

# ============================================================
# Krok 7: Ollama -- serwer
# ============================================================
Write-Log "=== Krok 7/9: Serwer Ollamy ==="
$ollamaReady = $false
try {
    $r = Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) {
        Write-Log "OK: serwer Ollamy juz dziala"
        $ollamaReady = $true
    }
} catch {}

if (-not $ollamaReady) {
    Write-Log "Serwer nie dziala. Uruchamiam ollama serve..."
    Start-Process -FilePath $ollamaPath -ArgumentList "serve" -NoNewWindow -PassThru | Out-Null
    Start-Sleep -Seconds 4
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 3
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) { $ollamaReady = $true; break }
        } catch {}
        Write-Log "Czekam na serwer... ($($i+1)/10)"
    }
    if (-not $ollamaReady) {
        throw "Serwer Ollamy nie wystartowal po 30s"
    }
    Write-Log "OK: serwer Ollamy odpowiada"
}

# ============================================================
# Krok 8: Pull modeli
# ============================================================
Write-Log "=== Krok 8/9: Modele AI ==="

function Pull-ModelIfMissing {
    param([string]$Name)
    $list = & $ollamaPath list 2>&1 | Out-String
    if ($list -match [regex]::Escape($Name)) {
        Write-Log "OK: $Name juz pobrany"
        return $true
    }
    Write-Log "Pobieranie $Name (to moze chwile zajac)..."
    $oldErrPref = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $ollamaPath pull $Name 2>&1 | ForEach-Object { Write-Log "  $_" }
    $ErrorActionPreference = $oldErrPref
    if ($LASTEXITCODE -ne 0) { return $false }
    Write-Log "OK: $Name pobrany"
    return $true
}

function Test-Model {
    param([string]$Name)
    try {
        $body = @{ model = $Name; prompt = "Powiedz tylko: OK"; stream = $false } | ConvertTo-Json -Compress
        $r = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 120
        $json = $r.Content | ConvertFrom-Json
        Write-Log "OK: $Name -- $($json.response)"
        return $true
    } catch {
        Write-Log "OSTROZNIE: test API nieudany dla $Name -- $_"
        return $false
    }
}

$vlmOk = Pull-ModelIfMissing -Name $vlmModel
$textOk = Pull-ModelIfMissing -Name $textModel
if (-not $vlmOk) { throw "Pull VLM $vlmModel nieudany" }
if (-not $textOk) { throw "Pull Text $textModel nieudany" }

# ============================================================
# Krok 9: Test modeli
# ============================================================
Write-Log "=== Krok 9/9: Test modeli ==="
Write-Log "Test VLM ($vlmModel)..."
$vlmTest = Test-Model -Name $vlmModel
Write-Log "Test Text ($textModel)..."
$textTest = Test-Model -Name $textModel

if (-not $vlmTest -or -not $textTest) {
    Write-Log "OSTROZNIE: Niektore modele nie przeszly testu API."
    Write-Log "Moga byc jeszcze ladowane. Sprobuj recznie: ollama run $vlmModel"
}

# ============================================================
# Podsumowanie
# ============================================================
Write-Log ""
Write-Log "========================================"
Write-Log "  AnkieterAI -- Srodowisko gotowe"
Write-Log "========================================"
Write-Log "  Python:  $pyVersion"
Write-Log "  .venv:   $VenvPath"
Write-Log "  Backend: $RequirementsPath"
Write-Log "  Frontend:$FrontendDir ($(if($nodeVersion){$nodeVersion}else{'?'}))"
Write-Log "  Ollama:  $ollamaPath"
Write-Log "  VLM:     $vlmModel"
Write-Log "  Text:    $textModel"
Write-Log "========================================"
Write-Log ""
Write-Log "Aby uruchomic aplikacje:"
Write-Log "  .\scripts\run_prod.ps1    (produkcja + tunel Cloudflare)"
Write-Log "  .\scripts\run_dev.ps1     (deweloperski, hot-reload)"
Write-Log ""

Write-Log "=== Full Setup -- zakonczony pomyslnie ==="
exit 0