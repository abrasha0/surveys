# Kompleksowy raport struktury repozytorium — AnkieterAI

## Ogólny opis

Aplikacja **AnkieterAI** — webowa aplikacja Streamlit do automatyzacji digitalizacji papierowych ankiet medycznych za pomocą lokalnego modelu VLM (Ollama, deepseek-ocr). Użytkownik przesyła zdjęcia 5-stronicowej ankiety, AI wyciąga dane, człowiek weryfikuje i koryguje wyniki, a następnie eksportuje do CSV.

**Stack:** Python 3.12+, Streamlit, Pydantic, Ollama (deepseek-ocr), httpx, Pillow, Cloudflared  
**Branch:** `main` (czysta)  
**Remote:** `https://github.com/abrasha0/surveys` (GitHub)  
**Brak CI/CD, brak Dockera**

---

## Struktura katalogowa (top-level)

```
C:\workspace\dev\surveys\
├── AGENTS.md                    # Wytyczne dla AI agenta (workflow, commity)
├── README.md                    # Podstawowy README aplikacji
├── requirements.txt             # Zależności Python
├── .gitignore                   # Ignorowane pliki
├── current-state-report.md      # Raport stanu projektu
├── wyniki.csv                   # Plik wynikowy (wyniki ankiet)
│
├── src/                         # AKTYWNA implementacja (flat structure)
├── src2/                        # PRZEBUDOWANA implementacja (modularna) — osobny raport
│
├── tests/                       # Testy pytest
├── scripts/                     # Skrypty PowerShell (setup, deploy, dev)
├── docs/                        # Dokumentacja, plany, prompty
├── logs/                        # Logi i cache runtime
├── .streamlit/                  # Konfiguracja Streamlit
├── .venv/                       # Wirtualne środowisko Python
└── .pytest_cache/               # Cache pytest
```

---

## Pliki root-level

| Plik | Opis |
|------|------|
| `AGENTS.md` (58 linii) | Wytyczne: workflow realizacji faz, konwencje commitów (feat/fix/chore/refactor), polityka aktualizacji README |
| `README.md` (45 linii) | Krótki opis aplikacji, lista funkcjonalności, instrukcja uruchamiania, komendy testów |
| `requirements.txt` (9 linii) | Zależności: streamlit 1.59.0, pydantic 2.13.4, pydantic-settings 2.14.2, Pillow 12.3.0, httpx 0.28.1, python-multipart 0.0.32, pytest 8.3.4, pytest-asyncio 0.24.0 |
| `.gitignore` (11 linii) | Ignoruje: .venv, __pycache__, secrets, logs, uploads, cache, wyniki.csv |
| `current-state-report.md` (133 linii) | Raport stanu: fazy 0-9, status modułów, otwarte issues, 2 failing testy, priorytety dalszych prac |
| `wyniki.csv` (5 linii) | Plik wynikowy — 68 kolumn z nagłówkami CSV, 4 rekordy danych (w tym 2 testowe) |

---

## `src/` — Aktywna implementacja (9 plików, ~1 840 LOC)

```
src/
├── __init__.py         (0 linii)   — marker pakietu
├── main.py             (130 linii) — punkt wejścia, orkiestrator flow
├── config.py           (18 linii)  — konfiguracja aplikacji (Pydantic Settings)
├── schemas.py          (470 linii) — modele danych, walidacja, mapowanie CSV
├── ai_client.py        (461 linii) — klient Ollama, prompty per-page, retry logic
├── ui_components.py    (439 linii) — komponenty UI (4 ekrany + helpery)
├── state_manager.py    (90 linii)  — zarządzanie stanem sesji Streamlit
├── data_handler.py     (78 linii)  — grupowanie plików, eksport CSV, cache JSON
└── logger.py           (57 linii)  — konfiguracja logowania (plik + konsola)
```

### Szczegóły modułów

#### `main.py` — Punkt wejścia / Orkiestrator
- Inicjalizacja Streamlit (page config, CSS, logging, session state)
- Liniowy state machine: Login → Upload → Batch AI → Verify → CSV → Complete
- `asyncio.run()` do przetwarzania batch AI z progress callbackiem
- Zależności: wszystkie pozostałe moduły src/

#### `config.py` — Konfiguracja
- `AppConfig(BaseSettings)` z prefixem env `ANKIETER_`
- Hasło: `"a"`, Ollama URL: `localhost:11434`, model: `deepseek-ocr`
- Pliki: `wyniki.csv`, `logs/cache_results.json`, `logs/ankieter.log`
- Timeout: 120s, max retries: 3, log level: DEBUG

#### `schemas.py` — Modele danych (470 linii — największy plik)
- **`MedicalSurvey(BaseModel)`** — 67 pól ankietowych + metadane AI:
  - A. Demografia (7 pól): płeć, wiek, miasto, stan cywilny, forma zamieszkania, stopień studiów, uczelnia
  - B. Aktywność zawodowa (4): status, system pracy, oddział, staż
  - C. Styl życia (3): godziny snu, godziny ekranu, kofeina
  - D. MFIS — objawy zmęczenia (21 pól): skala 5-stopniowa
  - E. Stan zdrowia (4): anemia, tarczyca, inne choroby
  - F. Jakość snu / Athens (8): skala bezsenności
  - G. CES-D (20): skala depresji
  - H. Metadane: `needs_review: dict[str, bool]`
- `CSV_HEADER` — 68 polskich nagłówków (format Google Forms)
- `_FIELD_TO_CSV` — mapowanie pól Python → CSV (68 wpisów)
- `_LITERAL_CHOICES` — dozwolone wartości dla pól wyboru
- `from_ai_json()` — fabryka z normalizacją wartości
- `_normalize_value()` — normalizacja case-insensitive, obsługa polskich znaków
- `_extract_age()` — ekstrakcja wieku z tekstu OCR
- **`SurveyResult`** — raw_response, validated_data, confidence
- **`SurveyGroup`** — id, files (5 stron), result

#### `ai_client.py` — Integracja z Ollama (461 linii)
- `AIClient` — async klient httpx do Ollama `/api/chat`
- 5 specyficznych promptów per-strona (strona 0–4), każdy wyciąga inne pola
- `check_ollama_health()` → `GET /api/tags`
- `_analyze_page()` — pojedyncza strona: base64 → Ollama → JSON, retry z exponential backoff
- `analyze_survey()` — sekwencyjne 5 stron → merge → MedicalSurvey → confidence
- `analyze_batch()` — sekwencyjnie ankietami, cache po każdej
- `_merge_partial_results()` — łączenie wyników per-strona
- `_image_to_base64()` — konwersja obrazu do base64
- `ProcessingStatus` — dataclass do raportowania postępu
- Kontekst: `num_ctx=8192`

#### `ui_components.py` — Warstwa UI (439 linii)
- `render_login()` — ekran logowania (hasło)
- `render_upload()` — upload plików (jpg/png/webp) + start analizy
- `render_verification(survey)` — główny ekran weryfikacji:
  - 5 tabów (po jednym na stronę ankiety)
  - Layout 2-kolumnowy: obraz (lewo) + formularz (prawo)
  - Czerwone kropki na pustych/podejrzanych polach
  - Skrót klawiszowy Space do submitu
- `render_complete()` — koniec: baloniki, download CSV, nowa sesja
- Helpery: CSS injection, image-to-data-URL, touched field tracking

#### `state_manager.py` — Stan sesji (90 linii)
- Thin wrapper nad `st.session_state`
- Struktura: `{authenticated, current_index, surveys, ai_results}`
- Metody: init, auth check, navigation (next/index), survey CRUD, progress, clear

#### `data_handler.py` — I/O danych (78 linii)
- `group_files_by_survey()` — sortowanie alfabetyczne, chunkowanie co 5 plików
- `save_survey_to_csv()` — append do CSV z UTF-8 BOM
- `save_cache()` / `load_cache()` — JSON cache do `logs/cache_results.json`
- `export_csv_path()` — ścieżka do pliku wynikowego

#### `logger.py` — Logowanie (57 linii)
- Dual handler: plik (`logs/ankieter.log`) + stderr
- Tłumienie hałasu: httpx, httpcore, PIL, asyncio
- Guard flag zapobiega podwójnej konfiguracji

---

## `tests/` — Testy (6 plików, ~58 testów, 2 failing)

```
tests/
├── conftest.py            (165 linii) — fixture'y: sample_survey_data, sample_survey, ai_json_response, autouse reset
├── test_schemas.py        (58 linii)  — 18 testów: extract_age, normalize_value, from_ai_json, to_csv_row, field_names, SurveyResult/Group
├── test_data_handler.py   (60 linii)  — 8 testów: grupowanie plików, CSV z BOM, cache roundtrip
├── test_state_manager.py  (86 linii)  — 14 testów: auth, indeksowanie, next/clear, progress
├── test_ai_client.py      (51 linii)  — 8 testów: image_to_base64, merge_partial_results
└── test_csv_integrity.py  (25 linii)  — 7 testów: 68 kolumn, unikalność, mapowanie 1:1
```

**2 failing testy** (przyczyna: usunięto defaulty w `_normalize_value`, testy nie zaktualizowane):
- `test_no_number_fallback` — oczekuje `22`, dostaje `None`
- `test_literal_fallback_to_first` — oczekuje `"Kobieta"`, dostaje `None`

---

## `scripts/` — Skrypty PowerShell (5 plików)

| Skrypt | Linie | Opis |
|--------|-------|------|
| `setup_env.ps1` | 127 | Tworzenie venv, install deps. Flagi: `-Force` |
| `setup_ollama.ps1` | 136 | Lokalizacja/installacja Ollama, pull modelu. Flagi: `-Model`, `-SkipPull`, `-ListModels`, `-Status` |
| `run_dev.ps1` | 74 | Sprawdzenie Ollama, uruchomienie `streamlit run src/main.py` na porcie 8501 |
| `deploy_tunnel.ps1` | 141 | Cloudflare tunnel (cloudflared.exe → `C:\tools\`). Flagi: `-Stop`. **Znane bugi:** nazwy zmiennych |
| `full_setup.ps1` | 198 | Orkiestrator — uruchamia wszystkie 4 skrypty. Flagi: `-NoEnv`, `-NoOllama`, `-NoDev`, `-NoTunnel`. **Bug:** hardkoduje hasło "ankieter2026" zamiast "a" |

**Quick start:**
```powershell
.\scripts\full_setup.ps1        # albo kolejno:
.\scripts\setup_env.ps1
.\scripts\setup_ollama.ps1
.venv\Scripts\Activate.ps1
streamlit run src/main.py
```

---

## `docs/` — Dokumentacja (6 plików)

| Plik | Linie | Opis |
|------|-------|------|
| `sketch-master-prompt.md` | 85 | Oryginalny brief projektowy — architektura, UX, wyzwania OCR, flow użytkownika, fazy implementacji. Z annotacją o odchyleniach od planu |
| `implementation-plan.md` | 387 | **Autorytatywny plan implementacji** — struktura katalogów, zależności, specyfikacja 7 modułów, 4 skrypty deploy, 6 plików testów, 10 faz |
| `known-issues.md` | 34 | Tracker issue: 11 łącznie, 7 Done, 4 Open (w tym **#11 CRITICAL: UI breaks on form interaction**) |
| `optimalization-plan.md` | 72 | Plan optymalizacji 4-stage: preprocessing obrazów, architektura dwuetapowa VLM+TextLLM, async producer-consumer, LangSmith. Cel: 110s → ~15s/stronę |
| `_PAGE_PROMPTS.txt` | 122 | Oryginalne prompty v1 (5 stron) |
| `_PAGE_PROMPTS_v2.txt` | 139 | Aktualne prompty v2 (5 stron) — dopasowane do layoutu fizycznej ankiety |

**Open issues (z `known-issues.md`):**

| # | Priorytet | Opis |
|---|-----------|------|
| 3.1 | Medium | Rozszerzone logowanie request/response per-call |
| 8 | Medium | Lepsze komunikaty JSONDecodeError |
| 9 | Low | Monitoring issue w repo |
| 10 | Medium | Reset progress bar po kliknięciu "Start Analysis" |
| **11** | **CRITICAL** | **UI layout breaks on form interaction — taby rozszerzają się w pionie** |

---

## `logs/` — Pliki runtime

| Plik | Opis |
|------|------|
| `ankieter.log` | Log aplikacji (DEBUG level) |
| `run_dev.log` | Log uruchomienia dev servera |
| `cache_results.json` | Cache AI — 1 wpis (puste dane, prawdopodobnie z failed run) |

---

## `.streamlit/config.toml`

- Port: 8501, headless: true
- Theme: Material Design blue (#1E88E5), light background (#FAFAFA)
- Toolbar: viewer mode

---

## Architektura aplikacji (flow)

```
Login (hasło: "a")
  → Upload (wielokrotne jpg/png/webp)
    → Batch AI Processing (sekwencyjnie per-ankieta, per-strona)
      [5 stron × specyficzny prompt → Ollama → JSON → merge → walidacja]
      [Cache do logs/cache_results.json]
    → Verification UI (5 tabów, obraz + formularz side-by-side)
      [Czerwone kropki na needs_review, Space shortcut]
    → Export to CSV (UTF-8 BOM)
  → Download CSV / Nowa sesja
```

```
┌───────────────────────────────────────────────┐
│              main.py (Orchestrator)            │
├──────────┬────────────────┬───────────────────┤
│ State    │  AI Client     │  UI Components    │
│ Manager  │  (Ollama OCR)  │  (4 ekrany)       │
├──────────┴────────────────┴───────────────────┤
│              schemas.py (Domain Models)        │
├──────────────────┬────────────────────────────┤
│  data_handler.py │        config.py           │
│  (File I/O)      │    (Configuration)         │
├──────────────────┴────────────────────────────┤
│                 logger.py (Logging)            │
└───────────────────────────────────────────────┘
```

---

## `src2/` — Wzmianka

W katalogu `src2/` znajduje się **przebudowana implementacja** o modularnej strukturze:
- `app.py` — punkt wejścia
- `domain/` — warstwa danych (FieldSpec dataclassy, dynamiczne definiowanie pól, CSV export)
- `ai/` — warstwa AI (client, dynamiczne prompt generation z FieldSpec)
- `ingestion/` — grupowanie plików
- `state/` — manager stanu (z dodanym processing/cancel state)
- `ui/` — strona per ekran (login, upload, processing, verification, complete), dynamiczne widgety
- `.streamlit/config.toml` z `toolbarMode = "minimal"` (nowsza wersja)

Kluczowa różnica: pola zdefiniowane jako `FieldSpec` dataclassy (dynamiczne generowanie UI i promptów), zamiast hardkodowanych tuple'ów w `src/`. **Pełna analiza src2/ w osobnym raporcie.**

---

## Podsumowanie statusu

| Aspekt | Status |
|--------|--------|
| Fazy implementacji (0-9) | Wszystkie zrealizowane (0-9 w pełni, częściowo 8-9) |
| Testy | 56/58 passing, 2 failing (stale asercje) |
| Open issues | 4 (w tym 1 CRITICAL: #11 UI bug) |
| CI/CD | Brak |
| Docker | Brak |
| README | Minimalny, do aktualizacji |
| src2/ | Istnieje, nie jest jeszcze aktywną implementacją |
