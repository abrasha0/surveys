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
            Write-Log "WARNING: neither config.yaml nor configs\config.yaml.example exists"
            return $null
        }
        Write-Log "config.yaml does not exist -- using configs\config.yaml.example"
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
if ($Force) { Write-Log "Force mode: recreating .venv" }

# ============================================================
# Step 1: Python >= 3.12
# ============================================================
Write-Log "=== Step 1/9: Python >= 3.12 ==="
try {
    $pyVersion = & python --version 2>&1
    Write-Log "Found: $pyVersion"
    if ($pyVersion -match 'Python (\d+)\.(\d+)') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
            Write-Log "OK: Python $major.$minor"
        } else {
            throw "Python >= 3.12 is required, found $major.$minor"
        }
    } else {
        throw "Unrecognized version: $pyVersion"
    }
} catch {
    Write-Log "ERROR: $_"
    exit 1
}

# ============================================================
# Step 2: .venv
# ============================================================
Write-Log "=== Step 2/9: virtual environment ==="
if (Test-Path -LiteralPath $VenvPath) {
    if ($Force) {
        Write-Log "Force: removing the existing .venv..."
        Remove-Item -Path $VenvPath -Recurse -Force
        & python -m venv $VenvPath
        if ($LASTEXITCODE -ne 0) { throw "Failed to create .venv" }
        Write-Log "OK: .venv recreated"
    } else {
        Write-Log "OK: .venv already exists"
    }
} else {
    & python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { throw "Failed to create .venv" }
    Write-Log "OK: .venv created"
}

$PythonExe = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "python.exe not found in .venv: $PythonExe"
}

Write-Log "Upgrading pip..."
& $PythonExe -m pip install --upgrade pip setuptools wheel 2>&1 | ForEach-Object { Write-Log "  $_" }
if ($LASTEXITCODE -ne 0) { Write-Log "WARNING: pip upgrade failed (continuing)" }

# ============================================================
# Step 3: pip install -r requirements.txt
# ============================================================
Write-Log "=== Step 3/9: installing Python packages ==="
if (-not (Test-Path -LiteralPath $RequirementsPath)) {
    throw "requirements.txt not found: $RequirementsPath"
}
& $PythonExe -m pip install -r $RequirementsPath 2>&1 | ForEach-Object { Write-Log "  $_" }
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
Write-Log "OK: Python packages installed"

# Read the config now that PyYAML is installed in .venv
$config = Read-Config -ConfigPath (Join-Path -Path $ProjectRoot -ChildPath "config.yaml")
$vlmModel = "moondream"
$textModel = "llama3.2:3b"
if ($config -and $config.ai) {
    if ($config.ai.vlm_model) { $vlmModel = $config.ai.vlm_model }
    if ($config.ai.text_model) { $textModel = $config.ai.text_model }
}
Write-Log "Models from config: VLM=$vlmModel  Text=$textModel"

# ============================================================
# Step 4: Node.js and npm
# ============================================================
Write-Log "=== Step 4/9: Node.js and npm ==="
$nodePath = (Get-Command "node" -ErrorAction SilentlyContinue).Source
$npmPath = (Get-Command "npm" -ErrorAction SilentlyContinue).Source
if (-not $nodePath) {
    Write-Log "ERROR: Node.js not found in PATH."
    Write-Log "       Install Node.js 20.19+ or 22.12+ manually: https://nodejs.org/"
    Write-Log "       Then run this script again."
    exit 1
}
if (-not $npmPath) {
    Write-Log "ERROR: npm not found in PATH."
    exit 1
}
try {
    $nodeVersion = & node --version 2>&1
    # Vite 8 requires Node.js ^20.19.0 || >=22.12.0
    if ($nodeVersion -match 'v(\d+)\.(\d+)\.') {
        $nodeMajor = [int]$Matches[1]
        $nodeMinor = [int]$Matches[2]
        $nodeSupported = ($nodeMajor -eq 20 -and $nodeMinor -ge 19) -or ($nodeMajor -eq 22 -and $nodeMinor -ge 12) -or ($nodeMajor -gt 22)
        if (-not $nodeSupported) {
            Write-Log "ERROR: Node.js $nodeVersion is not supported. Install Node.js 20.19+ or 22.12+: https://nodejs.org/"
            exit 1
        }
    }
    Write-Log "OK: Node $nodeVersion, npm $(& npm --version 2>&1)"
} catch {
    Write-Log "ERROR: failed to check the Node.js version"
    exit 1
}

# ============================================================
# Step 5: npm install (frontend)
# ============================================================
Write-Log "=== Step 5/9: installing frontend dependencies ==="
$FrontendDir = Join-Path -Path $ProjectRoot -ChildPath "src\frontend"
if (-not (Test-Path -LiteralPath $FrontendDir)) {
    throw "src/frontend directory not found"
}
$nodeModules = Join-Path -Path $FrontendDir -ChildPath "node_modules"
if (Test-Path -LiteralPath $nodeModules) {
    Write-Log "node_modules already exists -- running npm install to sync it"
}
& npm install --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }
if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
Write-Log "OK: frontend dependencies installed"

# ============================================================
# Step 6: locate or install Ollama
# ============================================================
Write-Log "=== Step 6/9: Ollama ==="
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
    Write-Log "Ollama not found. Downloading the installer..."
    $url = "https://ollama.com/download/OllamaSetup.exe"
    $dst = "$env:TEMP\OllamaSetup.exe"
    (New-Object System.Net.WebClient).DownloadFile($url, $dst)
    Write-Log "Silent install..."
    Start-Process $dst -ArgumentList "/S" -Wait -PassThru | Out-Null
    $ollamaPath = "C:\Program Files\Ollama\ollama.exe"
    if (-not (Test-Path -LiteralPath $ollamaPath)) {
        throw "Ollama installation failed -- install it manually: https://ollama.com/download"
    }
    Write-Log "OK: Ollama installed"
}
Write-Log "Ollama: $ollamaPath"

# ============================================================
# Step 7: Ollama server
# ============================================================
Write-Log "=== Step 7/9: Ollama server ==="
$ollamaReady = $false
try {
    $r = Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) {
        Write-Log "OK: Ollama server is already running"
        $ollamaReady = $true
    }
} catch {}

if (-not $ollamaReady) {
    Write-Log "Server is not running. Starting ollama serve..."
    Start-Process -FilePath $ollamaPath -ArgumentList "serve" -NoNewWindow -PassThru | Out-Null
    Start-Sleep -Seconds 4
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 3
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:11434" -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) { $ollamaReady = $true; break }
        } catch {}
        Write-Log "Waiting for the server... ($($i+1)/10)"
    }
    if (-not $ollamaReady) {
        throw "Ollama server did not start within 30 s"
    }
    Write-Log "OK: Ollama server responds"
}

# ============================================================
# Step 8: pull models
# ============================================================
Write-Log "=== Step 8/9: AI models ==="

function Pull-ModelIfMissing {
    param([string]$Name)
    $list = & $ollamaPath list 2>&1 | Out-String
    if ($list -match [regex]::Escape($Name)) {
        Write-Log "OK: $Name already pulled"
        return $true
    }
    Write-Log "Pulling $Name (this may take a while)..."
    $oldErrPref = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $ollamaPath pull $Name 2>&1 | ForEach-Object { Write-Log "  $_" }
    $ErrorActionPreference = $oldErrPref
    if ($LASTEXITCODE -ne 0) { return $false }
    Write-Log "OK: $Name pulled"
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
        Write-Log "WARNING: API test failed for $Name -- $_"
        return $false
    }
}

$vlmOk = Pull-ModelIfMissing -Name $vlmModel
$textOk = Pull-ModelIfMissing -Name $textModel
if (-not $vlmOk) { throw "Failed to pull VLM $vlmModel" }
if (-not $textOk) { throw "Failed to pull text model $textModel" }

# ============================================================
# Step 9: test models
# ============================================================
Write-Log "=== Step 9/9: testing models ==="
Write-Log "Testing VLM ($vlmModel)..."
$vlmTest = Test-Model -Name $vlmModel
Write-Log "Testing text model ($textModel)..."
$textTest = Test-Model -Name $textModel

if (-not $vlmTest -or -not $textTest) {
    Write-Log "WARNING: some models failed the API test."
    Write-Log "They may still be loading. Try manually: ollama run $vlmModel"
}

# ============================================================
# Summary
# ============================================================
Write-Log ""
Write-Log "========================================"
Write-Log "  AnkieterAI -- environment ready"
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
Write-Log "To start the app:"
Write-Log "  .\scripts\run_prod.ps1    (production build + Cloudflare tunnel)"
Write-Log "  .\scripts\run_dev.ps1     (development, hot reload)"
Write-Log ""

Write-Log "=== Full Setup -- finished successfully ==="
exit 0