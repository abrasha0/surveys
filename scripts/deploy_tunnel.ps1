param(
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "..")
$LogFile = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\deploy_tunnel.log"
$TunnelUrlFile = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\tunnel_url.txt"
$CloudflaredDir = "C:\tools"
$CloudflaredPath = Join-Path -Path $CloudflaredDir -ChildPath "cloudflared.exe"

$tunnelProcess = $null

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Cleanup {
    Write-Log "=== Cleanup: zatrzymywanie tunelu ==="
    if ($tunnelProcess -and -not $tunnelProcess.HasExited) {
        Write-Log "Zatrzymywanie cloudflared (PID: $($tunnelProcess.Id))..."
        $tunnelProcess.Kill()
    }
    Write-Log "=== Cleanup zakonczony ==="
}

New-Item -Path $LogFile -ItemType File -Force | Out-Null
Write-Log "=== Deploy Tunnel - start ==="

# --- Stop mode ---
if ($Stop) {
    Write-Log "Tryb stop: zatrzymywanie tunelu..."
    $tunnelProc = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
    if ($tunnelProc) {
        $tunnelProc | Stop-Process -Force
        Write-Log "OK: tunel zatrzymany"
    } else {
        Write-Log "Brak dzialajacego tunelu"
    }
    if (Test-Path -LiteralPath $TunnelUrlFile) {
        Remove-Item -Path $TunnelUrlFile -Force
        Write-Log "Usunieto plik $TunnelUrlFile"
    }
    Write-Log "=== Deploy Tunnel - zatrzymany ==="
    exit 0
}

# --- Krok 1: Sprawdzenie cloudflared ---
Write-Log "Krok 1: Lokalizacja cloudflared..."
$cfPath = (Get-Command "cloudflared" -ErrorAction SilentlyContinue).Source

if (-not $cfPath) {
    if (Test-Path -LiteralPath $CloudflaredPath) {
        $cfPath = $CloudflaredPath
        Write-Log "Znaleziono w $CloudflaredPath"
    } else {
        Write-Log "cloudflared nie znaleziony. Pobieram..."
        $url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        $tmpDst = "$env:TEMP\cloudflared.exe"

        try {
            Invoke-WebRequest -Uri $url -OutFile $tmpDst -UseBasicParsing -TimeoutSec 60
            Write-Log "OK: pobrano cloudflared"
        } catch {
            Write-Log "BLAD: nie udalo sie pobrac cloudflared - $_"
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
            Write-Log "Dodano $CloudflaredDir do PATH uzytkownika"
        }
        $env:Path = "$env:Path;$CloudflaredDir"
    }
} else {
    Write-Log "Znaleziono cloudflared: $cfPath"
}

# --- Krok 2: Sprawdzenie uvicorn ---
Write-Log "Krok 2: Sprawdzanie czy uvicorn dziala na porcie 8000..."
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8000" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200 -or $r.StatusCode -eq 401) {
        Write-Log "OK: uvicorn odpowiada na http://localhost:8000"
    } else {
        throw "uvicorn zwrocil kod $($r.StatusCode)"
    }
} catch {
    Write-Log "BLAD: uvicorn nie odpowiada na porcie 8000."
    Write-Log "Uruchom najpierw: .\scripts\run_dev.ps1"
    exit 1
}

# --- Krok 3: Uruchomienie tunelu ---
Write-Log "Krok 3: Uruchamianie tunelu Cloudflare..."
Write-Log "Lacze z Cloudflare..."

$dateStr = Get-Date -Format "yyyyMMdd_HHmmss"
$logOutput = Join-Path -Path $ProjectRoot -ChildPath "working_vault\logs\tunnel_${dateStr}.log"

try {
    $tunnelProcess = Start-Process -FilePath $cfPath -ArgumentList "tunnel --url http://localhost:8000" -NoNewWindow -PassThru -RedirectStandardOutput $logOutput -RedirectStandardError "${logOutput}.err"

    Start-Sleep -Seconds 6

    Write-Log "Oczekiwanie na URL tunelu (do 60s)..."
    $tunnelUrl = $null
    for ($i = 0; $i -lt 20; $i++) {
        if (Test-Path -LiteralPath $logOutput) {
            $content = Get-Content -Path $logOutput -Raw
            if ($content -match 'https://[\w.-]+\.trycloudflare\.com') {
                $tunnelUrl = $Matches[0]
                break
            }
        }
        if ($i -eq 0) { Write-Log "connecting..." }
        Start-Sleep -Seconds 3
    }

    if ($tunnelUrl) {
        Write-Log "connected: Tunel aktywny!"
        Write-Log "URL: $tunnelUrl"
        $tunnelUrl | Set-Content -Path $TunnelUrlFile -Force
        Write-Log "URL zapisany do: $TunnelUrlFile"

        # Petla monitorujaca z health check
        try {
            while ($true) {
                Start-Sleep -Seconds 30
                if ($tunnelProcess.HasExited) {
                    Write-Log "failed: Proces cloudflared zakonczyl sie."
                    break
                }
                try {
                    $hc = Invoke-WebRequest -Uri $tunnelUrl -UseBasicParsing -TimeoutSec 10
                    Write-Log "health: OK (HTTP $($hc.StatusCode))"
                } catch {
                    Write-Log "health: Tunel nie odpowiada - $_"
                }
            }
        } finally {
            Cleanup
        }
    } else {
        Write-Log "failed: Nie wykryto URL tunelu po 60s. Sprawdz log: $logOutput"
        Cleanup
        exit 1
    }
} catch {
    Write-Log "BLAD: Nie udalo sie uruchomic tunelu - $_"
    Write-Log "Sprawdz log: $logOutput"
    Cleanup
    exit 1
}

Write-Log "=== Deploy Tunnel - zakonczony ==="
exit 0
