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
    Write-Log "=== Cleanup: zatrzymywanie procesow ==="
    if ($uvicornProcess -and -not $uvicornProcess.HasExited) {
        Write-Log "Zatrzymywanie uvicorn (PID: $($uvicornProcess.Id))..."
        $uvicornProcess.Kill()
    }
    if ($npmProcess -and -not $npmProcess.HasExited) {
        Write-Log "Zatrzymywanie npm dev (PID: $($npmProcess.Id))..."
        $npmProcess.Kill()
    }
    Write-Log "=== Cleanup zakonczony ==="
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
                Write-Log "OK: API gotowe na http://localhost:8000"
                return $true
            }
        } catch {
            # uvicorn jeszcze nie gotowy - dalej czekamy
        }
    }
    Write-Log "UWAGA: API nie potwierdzone po ${elapsed}s - sprawdz logi: $LogPath oraz ${LogPath}.err"
    foreach ($f in @($LogPath, "${LogPath}.err")) {
        if (Test-Path -LiteralPath $f) {
            $content = Get-Content -LiteralPath $f -Tail 20
            if ($content) {
                Write-Log "Ostatnie linie $(Split-Path -Path $f -Leaf):"
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
    Write-Log "Uruchom najpierw: .\scripts\full_setup.ps1"
    Write-Log ""
    Write-Log "=== Run Dev - blad ==="
    exit 1
}

# --- Krok 2: Sprawdzenie .venv ---
Write-Log "Krok 2: Sprawdzanie wirtualnego srodowiska..."
if (-not (Test-Path -LiteralPath $VenvPath)) {
    Write-Log "BLAD: .venv nie istnieje."
    Write-Log "Uruchom najpierw: .\scripts\full_setup.ps1"
    exit 1
} else {
    Write-Log "OK: .venv istnieje"
}
$ErrorActionPreference = "Continue"

# --- Krok 3: Uruchomienie uvicorn ---
Write-Log "Krok 3: Uruchamianie uvicorn (API)..."
$PythonExe = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"
$uvicornLog = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\uvicorn_dev.log"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    Write-Log "BLAD: Nie znaleziono python.exe w .venv"
    exit 1
}

$SrcDir = Join-Path -Path $ProjectRoot -ChildPath "src\backend"
$uvicornProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn main:app --reload --port 8000" -WorkingDirectory $SrcDir -NoNewWindow -PassThru -RedirectStandardOutput $uvicornLog -RedirectStandardError "${uvicornLog}.err"
Write-Log "OK: Uvicorn uruchomiony (PID: $($uvicornProcess.Id))"

# --- Waitloop na uvicorn ---
Write-Log "Czekam na gotowosc uvicorn..."
$null = Wait-UvicornReady -LogPath $uvicornLog

# --- Krok 4: Walidacja node/npm ---
Write-Log "Krok 4: Sprawdzanie node i npm..."
$nodePath = (Get-Command "node" -ErrorAction SilentlyContinue).Source
$npmPath = (Get-Command "npm" -ErrorAction SilentlyContinue).Source
if (-not $nodePath) {
    Write-Log "BLAD: Node.js nie znaleziony w PATH. Zainstaluj Node.js >=18: https://nodejs.org/"
    Cleanup
    exit 1
}
if (-not $npmPath) {
    Write-Log "BLAD: npm nie znaleziony w PATH."
    Cleanup
    exit 1
}
Write-Log "OK: node ($nodePath), npm ($npmPath)"

# --- Krok 5: Uruchomienie npm dev ---
Write-Log "Krok 5: Uruchamianie npm dev (frontend)..."
$FrontendDir = Join-Path -Path $ProjectRoot -ChildPath "src\frontend"
$npmLog = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\npm_dev.log"

if (-not (Test-Path -LiteralPath $FrontendDir)) {
    Write-Log "BLAD: Nie znaleziono katalogu src/frontend"
    Cleanup
    exit 1
}

# npm moze byc npm.ps1 (PS skrypt) - Start-Process wymaga exe, uzyj cmd /c
$npmProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $FrontendDir -NoNewWindow -PassThru -RedirectStandardOutput $npmLog -RedirectStandardError "${npmLog}.err"
Write-Log "OK: npm dev uruchomiony (PID: $($npmProcess.Id))"
Write-Log "Frontend dev: http://localhost:5173 (proxy /api -> localhost:8000)"
Write-Log ""
Write-Log "Nacisnij Ctrl+C aby zatrzymac wszystkie procesy."
Write-Log "Nacisnij R aby recznie zrestartowac backend (po zmianie/usunieciu zdjec)."
Write-Log ""

# --- Krok 6: File watcher na katalog zdjec ---
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
    Write-Log "OK: Watcher na katalog zdjec uruchomiony (polling co 2s)"
    Write-Log "     $SurveysDir"
} else {
    Write-Log "OSTRZEZENIE: Katalog zdjec nie istnieje - watcher pominiety"
    Write-Log "     $SurveysDir"
}

# --- Krok 7: Monitorowanie z reloadem ---
try {
    while ($true) {
        Start-Sleep -Seconds 2

        # --- 7a: Sprawdz zmiany w katalogu zdjec ---
        if ($lastSnapshot) {
            $currentSnapshot = Get-DirSnapshot -Path $SurveysDir
            if ($currentSnapshot -ne $lastSnapshot) {
                $lastSnapshot = $currentSnapshot
                $now = [DateTime]::UtcNow
                if (($now - $lastRestartTime).TotalSeconds -ge 3) {
                    Write-Log "=== Zmiana w katalogu zdjec - restart backendu ==="
                    if ($uvicornProcess -and -not $uvicornProcess.HasExited) {
                        $uvicornProcess.Kill()
                        $null = $uvicornProcess.WaitForExit(5000)
                    }
                    $uvicornProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn main:app --reload --port 8000" -WorkingDirectory $SrcDir -NoNewWindow -PassThru -RedirectStandardOutput $uvicornLog -RedirectStandardError "${uvicornLog}.err"
                    $lastRestartTime = $now
                    Write-Log "OK: Uvicorn zrestartowany (PID: $($uvicornProcess.Id))"
                    Write-Log "Czekam na gotowosc uvicorn..."
                    $null = Wait-UvicornReady -LogPath $uvicornLog
                }
            }
        }

        # --- 7b: Reczny reload (klawisz R) ---
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            if ($key.Key -eq 'R') {
                Write-Log "=== Reczny reload backendu (klawisz R) ==="
                if ($uvicornProcess -and -not $uvicornProcess.HasExited) {
                    $uvicornProcess.Kill()
                    $null = $uvicornProcess.WaitForExit(5000)
                }
                $uvicornProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn main:app --reload --port 8000" -WorkingDirectory $SrcDir -NoNewWindow -PassThru -RedirectStandardOutput $uvicornLog -RedirectStandardError "${uvicornLog}.err"
                Write-Log "OK: Uvicorn zrestartowany (PID: $($uvicornProcess.Id))"
                Write-Log "Czekam na gotowosc uvicorn..."
                $null = Wait-UvicornReady -LogPath $uvicornLog
                # Odswiez frontend przez Vite
                Write-Log "INFO: Frontend Vite HMR odswiezy automatycznie po restarcie backendu"
            }
        }

        # --- 7c: Sprawdz czy procesy zyja ---
        $activeProcs = @()
        if ($uvicornProcess -and -not $uvicornProcess.HasExited) { $activeProcs += "uvicorn" }
        if ($npmProcess -and -not $npmProcess.HasExited) { $activeProcs += "npm" }
        if ($activeProcs.Count -eq 0) { break }
    }
} finally {
    Cleanup
}

Write-Log "=== Run Dev - zakonczony ==="
exit 0
