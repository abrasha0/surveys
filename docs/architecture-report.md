# Architecture Report — AnkieterAI

## Stack i zależności

| Pakiet | Wersja | Użycie |
|--------|--------|--------|
| fastapi | ≥0.115.0 | Backend framework |
| uvicorn[standard] | ≥0.32.0 | ASGI server |
| pydantic | 2.13.4 | Modele danych, walidacja |
| httpx | 0.28.1 | Async HTTP → Ollama |
| Pillow | 12.3.0 | Przetwarzanie obrazów (resize, grayscale, contrast) |
| python-multipart | 0.0.32 | Upload plików (nieużywane — przetwarzanie z lokalnego katalogu) |
| pyyaml | ≥6.0 | Parsowanie `config.yaml` |

Frontend: React 19, TypeScript 6, Vite 8, Tailwind CSS 4, React Router DOM 7, TanStack Query 5, Zustand 5, Oxlint.

Zależności opcjonalne:
- `langsmith` — tracing LangSmith (gdy włączony w `config.yaml`)

---

## Struktura katalogowa

```
surveys/
├── src/                         # Backend (FastAPI)
│   ├── main.py                  # Entry point, FastAPI app, StaticFiles mount
│   ├── config.py                # YAML + env vars override
│   ├── auth.py                  # Autoryzacja (login/logout sesyjny)
│   ├── data_handler.py          # Cache load/save, CSV path
│   ├── logger.py                # Dual handler (file + console)
│   ├── ai/                      # Warstwa AI
│   │   ├── client.py            # Async klient Ollama (VLM + Text LLM), preprocessing obrazów
│   │   ├── prompts.py           # Budowniczy promptów z config.yaml (vlm, text_format, page_*_json_schema)
│   │   └── tracing.py           # Opcjonalny LangSmith tracing (vlm_trace, llm_trace, io_trace)
│   ├── domain/                  # Logika biznesowa
│   │   ├── field_specs.py       # FieldSpec, 70 pól (source of truth) na 5 stronach
│   │   ├── schemas.py           # MedicalSurvey (Pydantic), walidacja, normalizacja, CSV row
│   │   └── csv_export.py        # Export do CSV (UTF-8 BOM, append)
│   ├── ingestion/               # Przetwarzanie wejściowe
│   │   └── file_grouping.py     # Skanowanie katalogu + grupowanie zdjęć po 5
│   ├── routers/                 # Endpointy REST
│   │   └── api.py               # Wszystkie endpointy API (prefix /api)
│   └── worker/                  # Worker w tle
│       ├── __init__.py          # Singleton workera (get_worker())
│       ├── processing_worker.py # Asynchroniczny worker sekwencyjny z retry 3x
│       └── state.py             # Stany: SurveyState, GlobalState, ProcessingState + ETA
├── src_ui/                      # Frontend (React + Vite)
│   ├── src/
│   │   ├── app/                 # Routing, layout, guard
│   │   ├── api/                 # Klient API + TanStack Query hooks
│   │   ├── components/          # Współdzielone komponenty UI
│   │   ├── features/            # Strony aplikacji
│   │   │   ├── auth/            # Logowanie
│   │   │   ├── verification/    # Weryfikacja (side-by-side)
│   │   │   └── complete/        # Ekran zakończenia
│   │   ├── hooks/               # Niestandardowe hooki
│   │   └── store/               # Zustand store (drafty, UI state)
│   ├── dist/                    # Zbudowane assety (dla dev servera)
│   └── vite.config.ts           # Proxy /api → localhost:8000
├── dist/                        # Zbudowany frontend (StaticFiles mount)
├── scripts/                     # Skrypty PowerShell
├── docs/                        # Dokumentacja
├── config.yaml                  # Konfiguracja
└── react-refactor-docs/         # Plany migracji (archiwum)
```

---

## Warstwy architektury

```
┌─────────────────────────────────────────────────┐
│  FRONTEND: React + Vite (src_ui/)               │  UI + routing + state
├─────────────────────────────────────────────────┤
│  API: FastAPI (src/routers/api.py)              │  REST endpointy
├─────────────────────────────────────────────────┤
│  WORKER: src/worker/                             │  Przetwarzanie w tle + kolejka
├─────────────────────────────────────────────────┤
│  DOMAIN: src/domain/*                            │  Logika biznesowa, schematy, walidacja, export
├─────────────────────────────────────────────────┤
│  INFRA: src/ai/*, src/ingestion/*,              │  Integracje zewnętrzne, persistencja
│          src/data_handler.py, src/config.py      │
└─────────────────────────────────────────────────┘
```

---

## Maszyna stanów

```
UNAUTHENTICATED ──(login)──> AUTHENTICATED
                                    │
                              (scan dir + start)
                                    │
                                    ▼
                               QUEUED
                                    │
                            (start processing)
                                    │
                                    ▼
                              PROCESSING
                         (worker w tle, retry 3x)
                          │                 │
                          │  (sukces)       │  (3x fail)
                          │                 │
                          ▼                 ▼
                        READY             ERROR
                          │
                    (weryfikacja + save)
                          │
                          ▼
                      VERIFIED
                          │
              (wszystkie verified/error)
                          │
                          ▼
                      ALL_DONE
                (ekran zakończenia + CSV)
```

`main.py` działa jako entry point FastAPI — montuje routery API oraz StaticFiles
dla zbudowanego frontendu. Worker działa w tle jako singleton, przetwarzając
ankiety sekwencyjnie.

---

## Kluczowe moduły

### domain/field_specs.py — fundament systemu

- **70 pól** na 5 stronach jako `FieldSpec` dataclassy
- Definiuje: nazwę, etykietę, stronę, typ (select/text/number), dozwolone wartości, nagłówek CSV
- **Najczęściej importowany moduł** — napędza: walidację Pydantic, generowanie promptów,
  rendering formularzy, nagłówki CSV
- `ALL_FIELDS` — lista wszystkich pól (70 sztuk: 17 + 20 + 8 + 15 + 10)
- `PAGE_MAP` — mapowanie strony → lista pól
- `FIELD_SPEC_BY_NAME` — słownik do szybkiego dostępu
- `PAGE_DESCRIPTIONS` — opisy stron dla promptów (zakaz hardkodowania w prompts.py)

### ai/client.py — klient OCR

- Async `httpx.AsyncClient` → lokalny Ollama (domyślnie qwen3-vl:8b + llama3.1)
- **Sekwencyjne przetwarzanie per-strona**: VLM → Text LLM → następna strona
- Pre-processing obrazów: resize (max 2000px), grayscale, contrast (Pillow)
- Retry z exponential backoff (per-request, osobny od retry workera)
- `analyze_survey()` — 5 stron sekwenyjnie, merge wyników
- `analyze_batch()` — iteruje po ankietach z callbackami progressu
- Szczegółowy dual logging: główny log + dedykowany `ai_requests.log` z rotacją

### worker/processing_worker.py — worker w tle

- Singleton uruchamiany w lifespan FastAPI
- Przetwarza ankiety sekwencyjnie w async tasku
- Aktualizuje stan (`worker/state.py`) — kolejka, ETA, status per-survey
- Obsługa cancel (między ankietami)
- Cache per-survey — JSON w `logs/survey_cache/`

### routers/api.py — REST API

Wszystkie endpointy chronione przez `Depends(get_current_user)` (HMAC cookie):

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| GET | `/api/field-specs` | Schematy pól (70 specyfikacji) |
| GET | `/api/surveys` | Lista ankiet z statusami z katalogu + cache |
| GET | `/api/surveys/export/csv` | Download CSV (UTF-8 BOM) |
| GET | `/api/surveys/{id}/pages/{page}/image` | Zdjęcie strony ankiety |
| GET | `/api/surveys/{id}/result` | Wynik przetwarzania AI (tylko gdy status ready/error) |
| POST | `/api/surveys/{id}/save` | Zapis zweryfikowanych danych do CSV (z opcją force) |
| POST | `/api/processing/start` | Uruchomienie workera (skanuje katalog i przetwarza kolejkę) |
| GET | `/api/processing/status` | Status workera + ETA (total, processed, errors, current_stage) |
| POST | `/api/processing/stop` | Zatrzymanie workera (po bieżącej ankiecie) |

### domain/schemas.py — modele danych

- `MedicalSurvey` (Pydantic BaseModel) — 63 pola
- `from_ai_json()` — fabryka z normalizacją (regex wieku, fuzzy match)
- `normalize_field()` — walidator z `field_specs`
- `to_csv_row()` — generuje wiersz CSV z timestampem

### config.py — konfiguracja

- Ładuje `config.yaml` (lub `config.yaml.example` jako fallback)
- Env override: `ANKIETER_*` prefix
- Zwraca `Section` (dict z dostępem atrybutowym)

---

## Przepływ danych (end-to-end)

```
[Skanowanie katalogu] → ingestion/file_grouping.py → sortowanie, grupowanie po 5
        │
        ▼
[Worker w tle] → ai/client.py: base64 → VLM → raw text → Text LLM → JSON
                  → merge 5 stron → MedicalSurvey → cache per-survey
        │
        ▼ (status: ready)
[Weryfikacja] → features/verification/: obraz | formularz, prefill z AI
        │
        ▼ (user submit)
[POST /api/surveys/{id}/save] → walidacja → domain/csv_export → append do wyniki.csv
        │
        ▼ (status: verified)
[Następna ankieta] → automatyczne przejście lub wybór z zakładek
        │
        ▼ (wszystkie verified)
[ALL_DONE] → CompletePage → Pobierz CSV / Nowa sesja
```

---

## Zależności importowe

```
main.py → config, logger, auth, routers/api.py, worker
  routers/api.py → auth, config, data_handler, domain, ingestion, worker
    data_handler → config
    domain/schemas → field_specs  ★ (fundament)
    domain/csv_export → schemas, field_specs
    ai/client → config, schemas, prompts
      prompts → field_specs
    ingestion/file_grouping → config
  worker → ai/client, config, data_handler, domain
    worker/state → (tylko dataclass)
```

**`field_specs.py`** — najbardziej centralny moduł backendu.

---

## Config

Sekcje `config.yaml`:

| Sekcja       | Opis                                                   |
|--------------|--------------------------------------------------------|
| `app`        | Tytuł, hasło, ścieżki, dozwolone typy plików           |
| `ai`         | Modele (VLM + Text), URL Ollama, retry, timeout, num_ctx, temperature, keep_alive |
| `image`      | max_dimension, contrast_factor, jpeg_quality            |
| `ingestion`  | survey_group_size                                       |
| `logging`    | Plik, poziom, rotacja logów AI, skracanie I/O          |
| `langsmith`  | tracing_v2, endpoint, api_key, project                  |
| `processing` | progress_weights, history_limit, worker_max_retries, eta_rolling_window, survey_cache_dir |
| `prompts`    | VLM extraction, text format + **5 schematów JSON per-strona** (`page_1_json_schema`..`page_5_json_schema`) |

Env vars: `ANKIETER_*` prefix nadpisuje wartości z YAML.
Pełna specyfikacja z komentarzami: `config.yaml.example`.
