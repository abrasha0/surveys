# Architecture Report — AnkieterAI

## Stack i zależności

| Pakiet | Wersja | Użycie |
|--------|--------|--------|
| streamlit | 1.59.0 | UI framework |
| pydantic | 2.13.4 | Modele danych, walidacja |
| pydantic-settings | 2.14.2 | Konfiguracja z env vars |
| httpx | 0.28.1 | Async HTTP → Ollama |
| Pillow | 12.3.0 | Przetwarzanie obrazów |
| python-multipart | 0.0.32 | Upload plików |
| pytest | 8.3.4 | Testy |
| pytest-asyncio | 0.24.0 | Testy async |

Zależności opcjonalne:
- `langsmith` — tracing LangSmith (gdy włączony w `config.yaml`)

---

## Struktura katalogowa

```
surveys/
├── src/                         # Kod źródłowy aplikacji
│   ├── app.py                   # Entry point, front controller
│   ├── config.py                # YAML + env vars override
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
│   ├── state/                   # Zarządzanie stanem
│   │   └── state_manager.py     # Static facade nad session_state
│   └── ui/                      # Warstwa prezentacji
│       ├── pages/               # Strony aplikacji
│       │   ├── login.py         # Ekran logowania
│       │   ├── upload.py        # Upload plików
│       │   ├── processing.py    # Przetwarzanie AI (batch)
│       │   ├── verification.py  # Weryfikacja (side-by-side)
│       │   └── complete.py      # Koniec, eksport CSV
│       ├── widgets.py           # Renderer pól formularza
│       ├── styles.py            # CSS/JS injection
│       └── shortcuts.py         # Skróty klawiszowe
├── tests/                       # Testy
│   ├── conftest.py              # Fixture'y
│   ├── test_schemas.py          # Testy modeli danych
│   ├── test_data_handler.py     # Testy I/O danych
│   ├── test_state_manager.py    # Testy stanu sesji
│   ├── test_ai_client.py        # Testy klienta AI
│   └── test_csv_integrity.py    # Testy spójności CSV
├── scripts/                     # Skrypty PowerShell
│   ├── setup_env.ps1            # Python venv + deps
│   ├── setup_ollama.ps1         # Instalacja Ollamy + model
│   ├── run_dev.ps1              # Start Streamlit
│   ├── deploy_tunnel.ps1        # Cloudflare tunnel
│   └── full_setup.ps1           # Orchestrator
├── docs/                        # Dokumentacja
├── config.yaml                  # Konfiguracja (nie w repo)
├── config.yaml.example          # Przykład konfiguracji
├── requirements.txt             # Zależności Python
└── AGENTS.md                    # Wytyczne dla AI agenta
```

---

## Warstwy architektury

```
┌─────────────────────────────────────────────────┐
│  ENTRY POINT: app.py                            │  Orchestration / router stanów
├─────────────────────────────────────────────────┤
│  UI: ui/pages/*, ui/widgets, ui/styles,         │  Renderowanie Streamlit + interakcja
│      ui/shortcuts                               │
├─────────────────────────────────────────────────┤
│  STATE: state/state_manager.py                  │  Abstrakcja stanu sesji
├─────────────────────────────────────────────────┤
│  DOMAIN: domain/*                               │  Logika biznesowa, schematy, walidacja, export
├─────────────────────────────────────────────────┤
│  INFRA: ai/*, ingestion/*, data_handler.py,     │  Integracje zewnętrzne, persistencja
│          config.py, logger.py                   │
└─────────────────────────────────────────────────┘
```

---

## Maszyna stanów

```
UNAUTHENTICATED ──(login)──> AUTHENTICATED ──(upload)──> SURVEYS_SET
     │                                                      │
     │                                                      ▼
     │                                              PROCESSING_MODE
     │                                              (AI batch OCR)
     │                                                      │
     │                                                      ▼
     │                                              VERIFICATION_LOOP
     │                                                 │         │
     │                                            (submit)   (index < total)
     │                                                 │         │
     │                                                 ▼         │
     │                                          SAVE_TO_CSV ─────┘
     │                                          NEXT_SURVEY
     └──────────────────────── ALL_DONE ──────────────────────────┘
```

`app.py` działa jako front controller — przy każdym rerunie Streamlit ewaluuje
warunki i renderuje dokładnie jedną stronę (`st.stop()` zapobiega "przeciekaniu").

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

### state/state_manager.py — zarządzanie stanem

- **Static facade** nad `st.session_state` — wszystkie metody `@staticmethod`
- 6 kluczy sesji: `auth`, `surveys`, `current_index`, `ai_results`, `processing`, `cancel_processing`
- Jedyne źródło prawdy dla stanu aplikacji

### domain/schemas.py — modele danych

- `MedicalSurvey` (Pydantic BaseModel) — 63 pola + `needs_review`
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
[Upload 5N zdjęć] → ingestion/file_grouping.py → sortowanie, grupowanie po 5
        │
        ▼
[AI OCR] → ai/client.py: base64 → VLM → raw text → Text LLM → JSON
           → merge 5 stron → MedicalSurvey
        │
        ▼ (cache JSON)
[Weryfikacja] → ui/pages/verification.py: obraz | formularz, prefill z AI
        │
        ▼ (user submit)
[Walidacja] → MedicalSurvey(**values) → Pydantic walidacja + normalizacja
        │
        ▼
[CSV Export] → domain/csv_export.py → append do wyniki.csv
        │
        ▼
[Next survey] → StateManager.next_survey() → rerun loop
```

---

## Zależności importowe

```
app.py → config, logger, state_manager, data_handler, ui/*
  state_manager → config (lazy)
  data_handler → config
  upload.py → file_grouping, schemas
  processing.py → ai/client, state_manager, data_handler, styles
    ai/client → config, schemas, prompts
      schemas → field_specs  ★ (fundament)
      prompts → field_specs
  verification.py → field_specs, styles, shortcuts, widgets, state_manager
    widgets → field_specs
  complete.py → data_handler, state_manager
  csv_export → schemas, field_specs
```

**`field_specs.py`** — 6 importów, najbardziej centralny moduł.

---

## Config

Sekcje `config.yaml`:

| Sekcja       | Opis                                                   |
|--------------|--------------------------------------------------------|
| `app`        | Tytuł, layout, hasło, ścieżki, dozwolone typy plików   |
| `ai`         | Modele, URL Ollama, retry, timeout, num_ctx, temperature, keep_alive |
| `image`      | max_dimension, contrast_factor, jpeg_quality            |
| `ingestion`  | survey_group_size, upload_dir_prefix                    |
| `logging`    | Plik, poziom, rotacja logów AI, skracanie I/O          |
| `langsmith`  | tracing_v2, endpoint, api_key, project                  |
| `processing` | Wagi progress bara, limit historii                      |
| `prompts`    | VLM extraction, text format (szablony z placeholderami) |

Env vars: `ANKIETER_*` prefix nadpisuje wartości z YAML.
Pełna specyfikacja z komentarzami: `config.yaml.example`.
