param(
    [string]$Model = "deepseek-ocr",
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

New-Item -Path $LogFile -ItemType File -Force | Out-Null
Write-Log "=== Setup Ollama - start ==="

# Model z parametru lub zmiennej srodowiskowej (latwa zmiana)
if ($env:OLLAMA_MODEL) {
    $Model = $env:OLLAMA_MODEL
    Write-Log "Model z env OLLAMA_MODEL: $Model"
} else {
    Write-Log "Model z parametru: $Model"
}

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

# --- Pull modelu ---
if (-not $SkipPull) {
    Write-Log "Krok 3: Pull modelu $Model ..."
    $list = & $ollamaPath list 2>&1
    if ($list -match [regex]::Escape($Model)) {
        Write-Log "OK: $Model jest pobrany."
    } else {
        Write-Log "Pobieranie $Model (to moze chwile zajac)..."
        
        # TYMCZASOWA ZMIANA: Ignoruj stderr potraktowany jako błąd
        $oldErrPref = $ErrorActionPreference
        $ErrorActionPreference = "Continue" 
        
        & $ollamaPath pull $Model 2>&1 | ForEach-Object { Write-Log "  $_" }
        
        # PRZYWRÓCENIE USTAWIENIA
        $ErrorActionPreference = $oldErrPref

        if ($LASTEXITCODE -ne 0) { throw "Pull nieudany (exit: $LASTEXITCODE)" }
        Write-Log "OK: $Model pobrany."
    }
} else {
    Write-Log "Krok 3: pominiety (-SkipPull)"
}

# --- Weryfikacja ---
Write-Log "Krok 4: Weryfikacja..."
& $ollamaPath list 2>&1 | ForEach-Object { Write-Log "  $_" }

Write-Log "Test API z modelem $Model ..."
try {
    $body = @{ model = $Model; prompt = "Powiedz tylko: OK"; stream = $false } | ConvertTo-Json
    $r = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 60
    $json = $r.Content | ConvertFrom-Json
    Write-Log "OK: odpowiedz modelu = $($json.response)"
} catch {
    Write-Log "OSTROZNIE: test API nieudany - $_"
    Write-Log "(Model moze byc jeszcze ladowany. Sprobuj: ollama run $Model)"
}

Write-Log "=== Setup Ollama - zakonczony ==="
Write-Log "Model: $Model  |  Serwer: http://localhost:11434"
exit 0
