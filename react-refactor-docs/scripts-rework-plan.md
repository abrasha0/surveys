# Plan Refaktoryzacji Skryptów PowerShell (`scripts/`)

## Stan wyjściowy

Aktualna architektura to **FastAPI + React/Vite na jednym porcie 8000** (produkcja: uvicorn serwuje API + statyczny frontend z `dist/`; dev: uvicorn 8000 + Vite 5173 z proxy). Skrypty były już częściowo modyfikowane w Etapie 9 migracji, ale zawierają **krytyczne błędy** i niespójności.

---

## Problemy do rozwiązania

| # | Skrypt | Problem | Typ |
|---|--------|---------|-----|
| 1 | `full_setup.ps1:138` | **`$VenvPath` niezdefiniowane** — użyte, ale nie zadeklarowane w tym skrypcie → crash przy próbie startu uvicorn | **CRITICAL** |
| 2 | `setup_ollama.ps1:2` | Domyślny model `deepseek-ocr` nieaktualny — config.yaml używa `moondream` (VLM) i `llama3.2:3b` (text) | Błąd konfiguracji |
| 3 | `run_dev.ps1:97` | Brak sprawdzenia dostępności node/npm przed `npm run dev` | Brak walidacji |
| 4 | `full_setup.ps1:169` | Tunel uruchamiany jako osobny proces PowerShell (fragile, problemy z cleanupem) | Architektura |
| 5 | Wszystkie | Skrypty nie czytają `config.yaml` — porty, modele, hasło są hardcodowane | Utrzymywalność |
| 6 | Wszystkie | Duplikacja `Write-Log` w każdym pliku | Suchość kodu |
| 7 | `full_setup.ps1:208` | Hasło `a` hardcodowane w podsumowaniu | Błąd informacyjny |
| 8 | `run_dev.ps1` | Brak waita na gotowość uvicorn przed ogłoszeniem sukcesu | UX |
| 9 | `setup_ollama.ps1` | Pobiera tylko 1 model, ale system wymaga 2 (VLM + text) | Funkcjonalność |
| 10 | `setup_env.ps1:149` | Końcowe instrukcje wspominają `uvicorn main:app --port 8000` (OK), ale brak wzmianki o froncie | Dokładność |

---

## Plan naprawy (kolejność chronologiczna)

---

### Krok 1: `setup_ollama.ps1` — Obsługa dwóch modeli z config.yaml

**Plik:** `scripts\setup_ollama.ps1`

**Zmiany:**
1. Dodanie parsowania `config.yaml` (YAML → PowerShell) — odczyt sekcji `ai` → `vlm_model` i `text_model`
2. Zmiana parametru `-Model` (pojedynczy) na `-VlmModel` i `-TextModel` z wartościami domyślnymi z config.yaml
3. Sekcja pull modeli: **pull obu modeli** (VLM i text) zamiast jednego
4. Walidacja: oba modele muszą być dostępne po pullu
5. Flaga `-Status`: pokazuje status obu modeli
6. Backwards compatibility: jeśli nie ma `config.yaml`, fallback do parametrów (lub `deepseek-ocr` / `llama3.2:3b`)

**Przykład odczytu YAML w PS:**
```powershell
$configPath = Join-Path -Path $ProjectRoot -ChildPath "config.yaml"
if (Test-Path $configPath) {
    $config = Get-Content $configPath -Raw | ConvertFrom-Yaml
    # Requires PowerShellGet\Install-Module -Name powershell-yaml
    # OR manual regex parsing
}
```
*(Uwaga: braku natywnego YAML w PS5.1 — można użyć prostego regexa dla sekcji `ai:`, bo plik jest prosty, albo zależność od `powershell-yaml`)*

---

### Krok 2: `setup_env.ps1` — Drobne poprawki

**Plik:** `scripts\setup_env.ps1`

**Zmiany:**
1. Weryfikacja istnienia `src\main.py` (punkt wejścia FastAPI) — opcjonalne ostrzeżenie
2. Końcowe instrukcje: doprecyzowanie architektury single-port
3. Sprawdzenie czy Node.js >= 18 (minimalna wersja dla Vite 8)

---

### Krok 3: `run_dev.ps1` — Dodanie walidacji i waitów

**Plik:** `scripts\run_dev.ps1`

**Zmiany:**
1. Przed `npm run dev` — sprawdzenie czy `node` i `npm` są w PATH (z czytelnym komunikatem)
2. Waitloop na uvicorn przed ogłoszeniem sukcesu (poll `http://localhost:8000` max 10s)
3. Opcjonalne: czytanie portu z `config.yaml.app.port` (jeśli istnieje)
4. Lepsze komunikaty: rozróżnienie "API:8000" vs "Frontend dev:5173"

---

### Krok 4: `full_setup.ps1` — Naprawa krytycznego buga + refaktoryzacja

**Plik:** `scripts\full_setup.ps1`

**Zmiany:**
1. **Fix CRITICAL:** Zdefiniowanie `$VenvPath` na początku skryptu (tak samo jak w `run_dev.ps1`)
2. Czytanie konfiguracji z `config.yaml` dla hasła i modeli w podsumowaniu
3. Uruchamianie `deploy_tunnel.ps1` **w tym samym procesie** (inline) zamiast jako osobny PowerShell:
   - Uruchomienie `cloudflared` bezpośrednio przez `Start-Process` z `$cfPath`
   - Detekcja URL w pętli (tak jak robi to `deploy_tunnel.ps1`)
   - Zapis URL do pliku
4. Lepszy cleanup: śledzenie PIDów w tablicy, cleanup przez `try/finally` (zamiast zawodnego `Register-EngineEvent`)
5. Wait na uvicorn przed tunelem (poll na `http://localhost:8000` z timeoutem)
6. Podsumowanie z rzeczywistych wartości (hasło z configu, model z configu)

---

### Krok 5: `deploy_tunnel.ps1` — Usprawnienia

**Plik:** `scripts\deploy_tunnel.ps1`

**Zmiany:**
1. Bardziej odporny regex na URL tunelu (`https://[\w.-]+\.trycloudflare\.com`)
2. Dłuższy wait na URL (do 60s zamiast 36s)
3. Okresowe health checki tunelu (poll URL co 30s)
4. Czytelniejsze logi (rozróżnienie "connecting" / "connected" / "failed")

---

### Krok 6: Cross-cutting — Wspólna funkcja Write-Log (opcjonalnie)

**Decyzja:** Czy wyciągnąć `Write-Log` do osobnego pliku `scripts\_common.ps1` i dot-source'ować? 
- **Za:** mniej duplikacji, jedna zmiana logowania
- **Przeciw:** więcej zależności, skrypty przestają być standalone, utrudnione kopiowanie/debug

**Rekomendacja:** Zostawić w każdym pliku, ale ujednolicić implementację (wszystkie mają już praktycznie identyczną).

---

## Diagram przepływu (po refaktoryzacji)

```
full_setup.ps1 (produkcja)
├── 1. setup_env.ps1
│   ├── Python >=3.12 check
│   ├── .venv create + pip install  
│   ├── npm install (src_ui/)
│   └── Weryfikacja (fastapi, uvicorn, node)
├── 2. setup_ollama.ps1 (z config.yaml)
│   ├── Ollama server start
│   ├── Pull VLM model + text model
│   └── Weryfikacja obu modeli
├── 3. npm run build (src_ui/) → src_ui/dist/
├── 4. Copy src_ui/dist/ → dist/ (root)
├── 5. uvicorn main:app --port 8000 (API + StaticFiles)
│   └── Wait: poll localhost:8000 aż odpowie
├── 6. cloudflared tunnel --url localhost:8000
│   └── Wait: detekcja trycloudflare.com URL
└── Pętla monitorująca + cleanup (try/finally)

run_dev.ps1 (development)
├── 1. Check: Ollama na 11434
├── 2. Check: .venv (auto setup_env jeśli brak)
├── 3. Check: node/npm w PATH
├── 4. Start uvicorn --reload --port 8000
├── 5. Wait: poll localhost:8000
├── 6. Start npm run dev (src_ui/)
└── Pętla monitorująca + cleanup
```

---

## Podsumowanie zmian

| Krok | Plik | Zmiany | Linii dotkniętych |
|------|------|--------|-------------------|
| 1 | `setup_ollama.ps1` | Obsługa 2 modeli, czytanie config.yaml, -VlmModel/-TextModel params | ~40 |
| 2 | `setup_env.ps1` | Weryfikacja src/main.py, Node.js >=18, lepsze instrukcje | ~15 |
| 3 | `run_dev.ps1` | Walidacja node/npm, waitloop na uvicorn | ~20 |
| 4 | `full_setup.ps1` | Fix $VenvPath, czytanie config.yaml, inline tunnel, lepszy cleanup | ~60 |
| 5 | `deploy_tunnel.ps1` | Lepszy regex URL, dłuższy timeout, health check | ~15 |
| 6 | Wszystkie | Ujednolicenie Write-Log (kosmetyka) | ~0 |