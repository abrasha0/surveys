# Etap 9 — Pipeline deploymentu (PowerShell)

## Kontekst i stan wyjściowy

Etap 9 (zgodnie z `react-refactor-docs/migration-stages.md:194-206`) przekształca pipeline deploymentu z modelu Streamlit-only do modelu FastAPI + React, gdzie frontend jest budowany jako statyczne assety, a backend (uvicorn) serwuje zarówno API, jak i te pliki. Cloudflare tunnel wystawia całość na jednym porcie.

### Co już jest gotowe (zależności Etapu 9)

| Warstwa | Status | Lokalizacja |
|---------|--------|-------------|
| Backend FastAPI | Gotowy | `src/main.py` (punkt wejścia), `src/routers/api.py` (wszystkie endpointy), `src/auth.py`, `src/worker/`, `src/ai/`, `src/domain/` |
| Frontend React+Vite | Gotowy | `src_ui/src/` (pełna aplikacja: login, kolejka, weryfikacja, formularz, obraz, nawigacja) |
| StaticFiles mounting | Gotowe | `src/main.py:35-37` montuje `dist/` z roota |
| Vite config | Gotowe | `src_ui/vite.config.ts` — proxy `/api` → `localhost:8000` |

### Co wymaga zmiany (istniejące skrypty są Streamlit-oriented)

| Skrypt | Problem | Port docelowy |
|--------|---------|---------------|
| `scripts/setup_env.ps1` | Brak `npm install` | — |
| `scripts/run_dev.ps1` | Uruchamia Streamlit na 8501 | 8000 (uvicorn) + 5173 (vite dev) |
| `scripts/deploy_tunnel.ps1` | Tunel do 8501 | 8000 |
| `scripts/full_setup.ps1` | Orkiestruje Streamlit | Ollama → npm build → dist → uvicorn 8000 → tunnel |
| `requirements.txt` | Zawiera `streamlit==1.59.0` | Usunąć |
| `config.yaml.example` | Zawiera `layout: "wide"` (Streamlit) | Usunąć |

### Kryteria akceptacji (z `migration-stages.md:204-205`)

> `full_setup.ps1` na czystym środowisku Windows kończy się działającą aplikacją dostępną przez tunnel na jednym porcie.

---

## Szczegółowy plan implementacji

### Krok 1: `setup_env.ps1` — Dodanie npm install

**Plik:** `scripts/setup_env.ps1`

**Zmiany:**

1. **Dodanie sekcji "Krok 7: Instalacja zależności frontendu (npm)"** po istniejącym "Kroku 6: Weryfikacja":
   - Sprawdzenie, czy `node` i `npm` są dostępne w PATH
   - Jeśli tak → uruchomienie `npm install` w katalogu `src_ui/`
   - Logowanie wyniku instalacji
   - Obsługa błędów (exit code ≠ 0)

2. **Aktualizacja sekcji "Krok 6: Weryfikacja"**:
   - Usunięcie `streamlit` z listy kluczowych pakietów (`$keyPackages`)
   - Dodanie `fastapi` i `uvicorn` do listy kluczowych pakietów

3. **Aktualizacja sekcji końcowej (instrukcje)**:
   - Zmiana `streamlit run src/app.py` → `uvicorn main:app --port 8000` (lub odniesienie do `run_dev.ps1`)

**Kod do dodania (po Kroku 6, przed exit):**

```powershell
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
    } catch {
        Write-Log "OSTROZNE: node/npm nie znajduja sie w PATH - pomijam npm install"
        Write-Log "Zainstaluj Node.js: https://nodejs.org/"
    }
    & npm install --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }
    if ($LASTEXITCODE -ne 0) { throw "npm install nie powiodl sie (exit code: $LASTEXITCODE)" }
    Write-Log "OK: zaleznosci frontendu zainstalowane."
}
```

---

### Krok 2: `run_dev.ps1` — Równoległe uvicorn + npm dev

**Plik:** `scripts/run_dev.ps1`

**Zmiany:**

1. **Zamiana logiki uruchamiania** — zamiast uruchamiać Streamlit, uruchomić dwa procesy równolegle:
   - `uvicorn main:app --reload --port 8000` (z aktywowanym `.venv`)
   - `npm run dev` w katalogu `src_ui/` (proxy `/api` → `localhost:8000`)

2. **Użycie `Start-Process` z `-PassThru`** dla obu procesów, by móc je monitorować

3. **Pętla oczekująca** na zakończenie któregokolwiek procesu

4. **Cleanup** — zatrzymanie obu procesów przy wyjściu

**Nowa struktura skryptu:**

```powershell
# Krok 1: Sprawdzenie Ollamy (bez zmian z obecnego)
# Krok 2: Sprawdzenie .venv (bez zmian z obecnego)
# Krok 3: Uruchomienie uvicorn (zastępuje Streamlit)
# Krok 4: Uruchomienie npm dev (nowy)
# Krok 5: Monitorowanie i czyszczenie
```

**Szczegóły Krok 3 (uvicorn):**
- `$PythonVenv = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"`
- `$Uvicorn = Join-Path -Path $VenvPath -ChildPath "Scripts\uvicorn.exe"`
- Uruchomienie: `Start-Process -FilePath $Uvicorn -ArgumentList "main:app --reload --port 8000" -WorkingDirectory $ProjectRoot -PassThru`
- Log: `http://localhost:8000`

**Szczegóły Krok 4 (npm dev):**
- `$FrontendDir = Join-Path -Path $ProjectRoot -ChildPath "src_ui"`
- Uruchomienie: `Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory $FrontendDir -PassThru`
- Log: `http://localhost:5173` (Vite dev server z proxy do API)

---

### Krok 3: `deploy_tunnel.ps1` — Tunel do portu 8000

**Plik:** `scripts/deploy_tunnel.ps1`

**Zmiany:**

1. **Linia 84-96** — Zmiana sprawdzania Streamlit na sprawdzanie uvicorn:
   - `http://localhost:8501` → `http://localhost:8000`
   - Tekst błędów: "Streamlit" → "uvicorn"
   - Instrukcja: `.\scripts\run_dev.ps1` (bez zmian, bo run_dev będzie uruchamiał uvicorn)

2. **Linia 106** — Zmiana targetu tunelu:
   - `http://localhost:8501` → `http://localhost:8000`

---

### Krok 4: `full_setup.ps1` — Pełny pipeline produkcyjny

**Plik:** `scripts/full_setup.ps1`

**Zmiany:**

1. **Dodanie nowego kroku "Krok 3/5: Budowa frontendu"** między Ollamą a uruchomieniem aplikacji:
   - Sprawdzenie, czy `node`/`npm` dostępne
   - `npm install --prefix src_ui` (jeśli nie było zrobione w setup_env)
   - `npm run build --prefix src_ui`
   - Po zakończeniu: kopiowanie zawartości `src_ui/dist/` do rootowego `dist/`
   - Usunięcie starego `dist/` przed skopiowaniem (czyste)

2. **Zamiana "Krok 4/4: Uruchamianie aplikacji Streamlit"** na **"Krok 4/5: Uruchomienie uvicorn"**:
   - Zamiast `run_dev.ps1` (który uruchamia Streamlit), uruchomić `uvicorn main:app --port 8000`
   - Użycie `Start-Process` z logowaniem do pliku

3. **Aktualizacja podsumowania**:
   - `http://localhost:8501` → `http://localhost:8000`

4. **Rejestracja procesu uvicorn do cleanupu** (dodanie do zmiennej `$appProcess`)

5. **Pętla monitorująca** — zaktualizowanie do sprawdzania `$appProcess` zamiast `$streamlitProcess`

**Szczegóły Krok 3 (npm build + copy):**

```powershell
# --- Krok 3/5: Budowa frontendu ---
Write-Log "=== Krok 3/5: Budowa frontendu (npm run build) ==="
$FrontendDir = Join-Path -Path $ProjectRoot -ChildPath "src_ui"
$DistDir = Join-Path -Path $ProjectRoot -ChildPath "dist"
$FrontendDist = Join-Path -Path $FrontendDir -ChildPath "dist"

& npm install --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }
& npm run build --prefix $FrontendDir 2>&1 | ForEach-Object { Write-Log "  $_" }

# Przeniesienie dist
if (Test-Path -LiteralPath $DistDir) {
    Remove-Item -Path $DistDir -Recurse -Force
}
New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
Copy-Item -Path "$FrontendDist\*" -Destination $DistDir -Recurse -Force
Write-Log "OK: Frontend zbudowany i skopiowany do $DistDir"
```

**Szczegóły Krok 4 (uvicorn):**

```powershell
# --- Krok 4/5: Uruchomienie uvicorn ---
$Uvicorn = Join-Path -Path $VenvPath -ChildPath "Scripts\uvicorn.exe"
$appLog = Join-Path -Path $ProjectRoot -ChildPath "logs\uvicorn_full.log"
$appProcess = Start-Process -FilePath $Uvicorn -ArgumentList "main:app --port 8000" -WorkingDirectory $ProjectRoot -NoNewWindow -PassThru -RedirectStandardOutput $appLog -RedirectStandardError "${appLog}.err"
Write-Log "OK: Uvicorn uruchomiony (PID: $($appProcess.Id))"
```

---

### Krok 5: `requirements.txt` — Usunięcie streamlit

**Plik:** `requirements.txt`

**Zmiana:**
- Usunięcie linii `streamlit==1.59.0`
- Pozostałe pakiety pozostają bez zmian

**Nowa treść:**

```
pydantic==2.13.4
pydantic-settings==2.14.2
Pillow==12.3.0
httpx==0.28.1
python-multipart==0.0.32
pyyaml>=6.0
langsmith>=0.2.0
fastapi>=0.115.0
uvicorn[standard]>=0.32.0

pytest==8.3.4
pytest-asyncio==0.24.0
```

---

### Krok 6: `config.yaml.example` — Usunięcie pola Streamlit-specific

**Plik:** `config.yaml.example`

**Zmiana:**
- Usunięcie pola `layout: "wide"` z sekcji `app` (to ustawienie Streamlit)
- Opcjonalnie: dodanie komentarza, że `surveys_dir` to katalog ze zdjęciami ankiet

---

### Krok 7: Aktualizacja `README.md`

**Plik:** `README.md`

**Zmiany:**
- Sekcja "Quick Start" — zamiana `streamlit run src/app.py` na `uvicorn main:app --port 8000` + `npm install` w `src_ui/`
- Sekcja "Funkcjonalności" — usunięcie Streamlit-specyficznych opisów, aktualizacja na FastAPI+React
- Dodanie informacji o wymaganiach (Node.js dla frontendu)

---

## Diagram przepływu (po zmianach)

### full_setup.ps1 (produkcyjny)

```
1. setup_env.ps1          → .venv + pip install + npm install
2. setup_ollama.ps1       → Ollama server + model pull
3. npm run build (src_ui/) → src_ui/dist/
4. Copy src_ui/dist/ → dist/
5. uvicorn main:app --port 8000   (serwuje API + StaticFiles z dist/)
6. deploy_tunnel.ps1      → Cloudflare tunnel → localhost:8000
```

### run_dev.ps1 (developerski)

```
1. Sprawdź Ollamę
2. Sprawdź .venv + npm deps
3. uvicorn main:app --reload --port 8000     (API)
4. npm run dev (src_ui/)                     → localhost:5173 (proxy /api → 8000)
```

---

## Podsumowanie kroków do zrealizowania

| Kolejność | Plik | Działanie | Typ zmiany |
|-----------|------|-----------|------------|
| 1 | `scripts/setup_env.ps1` | Dodanie Krok 7: npm install + aktualizacja weryfikacji | Edycja |
| 2 | `scripts/run_dev.ps1` | Zamiana Streamlit → uvicorn + npm dev (równolegle) | Rewrite |
| 3 | `scripts/deploy_tunnel.ps1` | Port 8501 → 8000 | Edycja (2 miejsca) |
| 4 | `scripts/full_setup.ps1` | Dodanie npm build + copy dist, zamiana Streamlit → uvicorn | Rewrite |
| 5 | `requirements.txt` | Usunięcie streamlit | Edycja |
| 6 | `config.yaml.example` | Usunięcie `layout: "wide"` | Edycja |
| 7 | `README.md` | Aktualizacja Quick Start i Funkcjonalności | Edycja |

---

## Ryzyka i uwagi

1. **Port 8000** — Upewnić się, że nie ma konfliktu z innymi usługami. Port 8000 jest standardowym dla FastAPI/uvicorn.
2. **Kopiowanie dist/** — `Copy-Item -Recurse -Force` może mieć problemy z ukrytymi plikami. Alternatywnie użyć `robocopy`.
3. **Node.js w PATH** — `setup_env.ps1` i `full_setup.ps1` powinny sprawdzać dostępność node/npm i dawać jasny komunikat o braku.
4. **Windows PowerShell 5.1** — Używać pełnych nazw cmdletów (np. `Remove-Item`, `New-Item`, `Copy-Item`), unikać aliasów.
5. **Restart aplikacji** — Po zmianie skryptów, `full_setup.ps1` musi być przetestowany od zera na czystym środowisku.
6. **Zależności Etapu 9** — Wszystkie endpointy API i frontend muszą być gotowe przed uruchomieniem tego pipeline'u.
