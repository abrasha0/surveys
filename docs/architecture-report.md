# Architecture Report — AnkieterAI

## Stack i zależności

| Pakiet | Wersja | Użycie |
|--------|--------|--------|
| fastapi | ≥0.115.0 | Backend framework |
| uvicorn | ≥0.32.0 | ASGI server |
| pydantic | 2.13.4 | Modele danych, walidacja |
| pydantic-settings | 2.14.2 | Konfiguracja z env vars |
| httpx | 0.28.1 | Async HTTP → Ollama |
| Pillow | 12.3.0 | Przetwarzanie obrazów |
| python-multipart | 0.0.32 | Upload plików |
| pyyaml | ≥6.0 | Parsowanie config.yaml |

Frontend: React 19, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Zustand.

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
│   │   ├── client.py            # Async klient Ollama (VLM + Text LLM)
│   │   ├── prompts.py           # Budowniczy promptów z config.yaml
│   │   └── tracing.py           # LangSmith integration
│   ├── domain/                  # Logika biznesowa
│   │   ├── field_specs.py       # FieldSpec, 63 pola (source of truth)
│   │   ├── schemas.py           # MedicalSurvey, walidacja, CSV mapping
│   │   └── csv_export.py        # Export do CSV
│   ├── ingestion/               # Przetwarzanie wejściowe
│   │   └── file_grouping.py     # Grupowanie zdjęć po 5
│   ├── routers/                 # Endpointy REST
│   │   └── api.py               # Wszystkie endpointy API
│   └── worker/                  # Worker w tle
│       ├── __init__.py          # Singleton workera
│       ├── processing_worker.py # Logika przetwarzania sekwencyjnego
│       └── state.py             # Stan kolejki (SurveyState)
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
UNAUTHENTICATED ──(login)──> AUTHENTICATED ──(scan dir)──> QUEUED
                                                                │
                                                        (start processing)
                                                                │
                                                                ▼
                                                        PROCESSING
                                                     (worker w tle)
                                                     │           │
                                                     │  (ankieta  │
                                                     │   gotowa)  │
                                                     │           │
                                                     ▼           │
                                                  READY ────────┘
                                                     │
                                               (weryfikacja)
                                                     │
                                                     ▼
                                                VERIFIED ────────┘
                                                     │
                                          (wszystkie zrobione)
                                                     │
                                                     ▼
                                                ALL_DONE
                                              (ekran zakończenia)
```

`main.py` działa jako entry point FastAPI — montuje routery API oraz StaticFiles
dla zbudowanego frontendu. Worker działa w tle jako singleton, przetwarzając
ankiety sekwencyjnie.

---

## Kluczowe moduły

### domain/field_specs.py — fundament systemu

- **63 pola** na 5 stronach jako `FieldSpec` dataclassy
- Definiuje: nazwę, etykietę, stronę, typ (select/text/number), dozwolone wartości, nagłówek CSV
- **Najczęściej importowany moduł** — napędza: walidację Pydantic, generowanie promptów,
  rendering formularzy, nagłówki CSV
- `ALL_FIELDS` — lista wszystkich pól
- `PAGE_MAP` — mapowanie strony → lista pól
- `FIELD_SPEC_BY_NAME` — słownik do szybkiego dostępu

### ai/client.py — klient OCR

- Async `httpx.AsyncClient` → lokalny Ollama (deepseek-ocr + llama3.1)
- **Sekwencyjne przetwarzanie per-strona**: VLM → Text LLM → następna strona
- Pre-processing obrazów: resize (max 2000px), grayscale, contrast (Pillow)
- Retry z exponential backoff
- `analyze_survey()` — 5 stron sekwenyjnie, merge wyników
- `analyze_batch()` — iteruje po ankietach z callbackami progressu

### worker/processing_worker.py — worker w tle

- Singleton uruchamiany w lifespan FastAPI
- Przetwarza ankiety sekwencyjnie w async tasku
- Aktualizuje stan (`worker/state.py`) — kolejka, ETA, status per-survey
- Obsługa cancel (między ankietami)
- Cache per-survey — JSON w `logs/survey_cache/`

### routers/api.py — REST API

- `GET /api/field-specs` — schematy pól
- `GET /api/surveys` — lista ankiet z statusami
- `GET /api/surveys/export/csv` — download CSV
- `GET /api/surveys/{id}/pages/{page}/image` — zdjęcie strony
- `GET /api/surveys/{id}/result` — wynik przetwarzania AI
- `POST /api/surveys/{id}/save` — zapis zweryfikowanych danych do CSV
- `POST /api/processing/start` — uruchomienie workera
- `GET /api/processing/status` — status + ETA
- `POST /api/processing/stop` — zatrzymanie workera

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
| `ai`         | Modele, URL Ollama, retry, timeout, num_ctx, temperature, keep_alive |
| `image`      | max_dimension, contrast_factor, jpeg_quality            |
| `ingestion`  | survey_group_size                                       |
| `logging`    | Plik, poziom, rotacja logów AI, skracanie I/O          |
| `langsmith`  | tracing_v2, endpoint, api_key, project                  |
| `processing` | progress_weights, history_limit, worker_max_retries, eta_rolling_window, survey_cache_dir |
| `prompts`    | VLM extraction, text format (szablony z placeholderami) |

Env vars: `ANKIETER_*` prefix nadpisuje wartości z YAML.
Pełna specyfikacja z komentarzami: `config.yaml.example`.
