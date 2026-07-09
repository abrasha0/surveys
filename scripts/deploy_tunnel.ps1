param(
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "..")
$LogFile = Join-Path -Path $ProjectRoot -ChildPath "logs\deploy_tunnel.log"
$TunnelUrlFile = Join-Path -Path $ProjectRoot -ChildPath "logs\tunnel_url.txt"
$CloudflaredDir = "C:\tools"
$CloudflaredPath = Join-Path -Path $CloudflaredDir -ChildPath "cloudflared.exe"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
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

# --- Krok 2: Sprawdzenie Streamlit ---
Write-Log "Krok 2: Sprawdzanie czy Streamlit dziala na porcie 8501..."
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8501" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) {
        Write-Log "OK: Streamlit odpowiada na http://localhost:8501"
    } else {
        throw "Streamlit zwrocil kod $($r.StatusCode)"
    }
} catch {
    Write-Log "BLAD: Streamlit nie odpowiada na porcie 8501."
    Write-Log "Uruchom najpierw: .\scripts\run_dev.ps1"
    exit 1
}

# --- Krok 3: Uruchomienie tunelu ---
Write-Log "Krok 3: Uruchamianie tunelu Cloudflare..."
Write-Log "Lacze z Cloudflare..."

$dateStr = Get-Date -Format "yyyyMMdd_HHmmss"
$logOutput = Join-Path -Path $ProjectRoot -ChildPath "logs\tunnel_${dateStr}.log"

try {
    $proc = Start-Process -FilePath $cfPath -ArgumentList "tunnel --url http://localhost:8501" -NoNewWindow -PassThru -RedirectStandardOutput $logOutput -RedirectStandardError "${logOutput}.err"

    Start-Sleep -Seconds 6

    $tunnelUrl = $null
    for ($i = 0; $i -lt 12; $i++) {
        if (Test-Path -LiteralPath $logOutput) {
            $content = Get-Content -Path $logOutput -Raw
            if ($content -match 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com') {
                $tunnelUrl = $Matches[0]
                break
            }
        }
        Start-Sleep -Seconds 3
    }

    if ($tunnelUrl) {
        Write-Log "OK: Tunel aktywny!"
        Write-Log "URL: $tunnelUrl"
        $tunnelUrl | Set-Content -Path $TunnelUrlFile -Force
        Write-Log "URL zapisany do: $TunnelUrlFile"
    } else {
        Write-Log "OSTROZNIE: Nie wykryto URL tunelu. Sprawdz log: $logOutput"
        Write-Log "Tunel moze byc juz aktywny - sprawdz recznie."
    }
} catch {
    Write-Log "BLAD: Nie udalo sie uruchomic tunelu - $_"
    Write-Log "Sprawdz log: $logOutput"
    exit 1
}

Write-Log "=== Deploy Tunnel - zakonczony ==="
Write-Log "Tunel: $tunnelUrl"
Write-Log "Aby zatrzymac: .\scripts\deploy_tunnel.ps1 -Stop"

exit 0
