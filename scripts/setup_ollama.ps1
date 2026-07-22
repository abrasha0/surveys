param(
    [string]$VlmModel = "",
    [string]$TextModel = "",
    [switch]$SkipPull,
    [switch]$ListModels,
    [switch]$Status
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "..")
$LogFile = Join-Path -Path $ProjectRoot -ChildPath "logs\setup_ollama.log"

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
        $json = & "$ProjectRoot\.venv\Scripts\python.exe" -c $script $ConfigPath 2>&1
        return ($json | ConvertFrom-Json)
    } catch {
        return $null
    }
}

New-Item -Path $LogFile -ItemType File -Force | Out-Null
Write-Log "=== Setup Ollama - start ==="

# --- Wczytaj konfiguracje ---
$ConfigPath = Join-Path -Path $ProjectRoot -ChildPath "config.yaml"
$config = Read-Config -ConfigPath $ConfigPath

$defaultVlm = "moondream"
$defaultText = "llama3.2:3b"
if ($config -and $config.ai) {
    if ($config.ai.vlm_model) { $defaultVlm = $config.ai.vlm_model }
    if ($config.ai.text_model) { $defaultText = $config.ai.text_model }
}

if (-not $VlmModel) { $VlmModel = $defaultVlm }
if (-not $TextModel) { $TextModel = $defaultText }

# Backwards compatibility: env OLLAMA_MODEL ustawia VLM
if ($env:OLLAMA_MODEL) {
    $VlmModel = $env:OLLAMA_MODEL
    Write-Log "VLM model z env OLLAMA_MODEL: $VlmModel"
}
Write-Log "VLM model: $VlmModel"
Write-Log "Text model: $TextModel"

# --- Znajdz ollama ---
Write-Log "Krok 1: Lokalizacja Ollamy..."
$searchPaths = @(
    "C:\Program Files\Ollama\ollama.exe",
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
)
$ollamaPath = (Get-Command "ollama" -ErrorAction SilentlyContinue).Source
if (-not $ollamaPath) {
    foreach ($p in $searchPaths) {
        if (Test-Path -LiteralPath $p) { $ollamaPath = $p; break }
    }
}

# Instalacja tylko jesli brak
if (-not $ollamaPath) {
    Write-Log "Ollama nie znaleziona. Pobieram instalke..."
    $url = "https://ollama.com/download/OllamaSetup.exe"
    $dst = "$env:TEMP\OllamaSetup.exe"
    Write-Log "Pobieranie $url ..."
    (New-Object System.Net.WebClient).DownloadFile($url, $dst)
    Write-Log "Instalacja (cicha)..."
    Start-Process $dst -ArgumentList "/S" -Wait -PassThru | Out-Null
    $ollamaPath = "C:\Program Files\Ollama\ollama.exe"
    if (-not (Test-Path $ollamaPath)) { throw "Instalacja nieudana" }
    Write-Log "OK: zainstalowano"
}
Write-Log "Sciezka: $ollamaPath"

# --- Status / ListModels ---
if ($ListModels) {
    Write-Log "Lista modeli:"
    & $ollamaPath list 2>&1 | ForEach-Object { Write-Host "  $_" }
    exit 0
}
if ($Status) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 5
        Write-Host "Serwer: DZIALA (HTTP $($r.StatusCode))"
    } catch {
        Write-Host "Serwer: NIE DZIALA"
    }
    & $ollamaPath list 2>&1 | Write-Host
    Write-Host ""
    Write-Host "Oczekiwane modele:"
    Write-Host "  VLM:  $VlmModel"
    Write-Host "  Text: $TextModel"
    exit 0
}

# --- Serwer ---
Write-Log "Krok 2: Serwer Ollama..."
$serverOk = $false
try {
    $r = Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 3
    Write-Log "OK: serwer dziala"
    $serverOk = $true
} catch {
    Write-Log "Serwer nie odpowiada. Uruchamiam..."
    $proc = Start-Process -FilePath $ollamaPath -ArgumentList "serve" -NoNewWindow -PassThru
    Start-Sleep -Seconds 4
    for ($i = 0; $i -lt 6; $i++) {
        try { Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 3 | Out-Null; $serverOk = $true; break }
        catch { Write-Log "Czekam... ($($i+1)/6)"; Start-Sleep -Seconds 3 }
    }
    if (-not $serverOk) { throw "Serwer nie wystartowal" }
}

function Pull-Model {
    param([string]$ModelName)
    Write-Log "Pull modelu $ModelName ..."
    $list = & $ollamaPath list 2>&1
    if ($list -match [regex]::Escape($ModelName)) {
        Write-Log "OK: $ModelName jest pobrany."
        return $true
    }
    Write-Log "Pobieranie $ModelName (to moze chwile zajac)..."
    $oldErrPref = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $ollamaPath pull $ModelName 2>&1 | ForEach-Object { Write-Log "  $_" }
    $ErrorActionPreference = $oldErrPref
    if ($LASTEXITCODE -ne 0) { return $false }
    Write-Log "OK: $ModelName pobrany."
    return $true
}

function Test-Model {
    param([string]$ModelName)
    Write-Log "Test API z modelem $ModelName ..."
    try {
        $body = @{ model = $ModelName; prompt = "Powiedz tylko: OK"; stream = $false } | ConvertTo-Json
        $r = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 60
        $json = $r.Content | ConvertFrom-Json
        Write-Log "OK: odpowiedz $ModelName = $($json.response)"
        return $true
    } catch {
        Write-Log "OSTROZNIE: test API nieudany dla $ModelName - $_"
        return $false
    }
}

# --- Pull modeli ---
if (-not $SkipPull) {
    Write-Log "Krok 3: Pull modeli VLM i Text..."
    $vlmOk = Pull-Model -ModelName $VlmModel
    $textOk = Pull-Model -ModelName $TextModel
    if (-not $vlmOk) { throw "Pull VLM modelu $VlmModel nieudany" }
    if (-not $textOk) { throw "Pull Text modelu $TextModel nieudany" }
} else {
    Write-Log "Krok 3: pominiety (-SkipPull)"
}

# --- Weryfikacja ---
Write-Log "Krok 4: Weryfikacja modeli..."
& $ollamaPath list 2>&1 | ForEach-Object { Write-Log "  $_" }

$vlmTestOk = Test-Model -ModelName $VlmModel
$textTestOk = Test-Model -ModelName $TextModel

if (-not $vlmTestOk -or -not $textTestOk) {
    Write-Log "OSTROZNIE: Niektore modele nie przeszly testu API."
    Write-Log "Moga byc jeszcze ladowane. Sprobuj recznie: ollama run <model>"
}

Write-Log "=== Setup Ollama - zakonczony ==="
Write-Log "VLM: $VlmModel  |  Text: $TextModel  |  Serwer: http://localhost:11434"
exit 0
