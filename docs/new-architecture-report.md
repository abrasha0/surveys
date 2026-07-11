# Architektura `src2` — Kompletny Raport

## Struktura katalogów

```
src2/
├── .streamlit/config.toml          # konfiguracja Streamlit (toolbar)
├── ai/
│   ├── client.py                   # async klient Ollama (HTTP + OCR)
│   └── prompts.py                  # budowniczy promptów systemowych per strona
├── domain/
│   ├── csv_export.py               # eksport wierszy do CSV
│   ├── field_specs.py              # specyfikacja 63 pól formularza (data dictionary)
│   └── schemas.py                  # modele Pydantic: MedicalSurvey, SurveyGroup
├── ingestion/
│   └── file_grouping.py            # grupowanie uploadowanych zdjęć (5 na ankietę)
├── state/
│   └── state_manager.py            # manager stanu sesji (singleton-fasada)
├── ui/
│   ├── pages/
│   │   ├── complete.py             # strona "koniec"
│   │   ├── login.py                # autoryzacja hasłem
│   │   ├── processing.py           # przetwarzanie AI batch z progressbarem
│   │   ├── upload.py               # upload plików + podgląd grup
│   │   └── verification.py         # weryfikacja obraz + formularz side-by-side
│   ├── shortcuts.py                # skróty klawiszowe (Space = Submit)
│   ├── styles.py                   # globalne CSS + JS ukrywający toolbar
│   └── widgets.py                  # renderer pól formularza (select/text/number)
├── app.py                          # ★ PUNKT WEJŚCIA — router stanów
├── config.py                       # konfiguracja (pydantic-settings, env vars)
├── data_handler.py                 # cache load/save (JSON) + ścieżka CSV
└── logger.py                       # logging (plik + konsola)
```

**15 plików źródłowych**, brak `__init__.py`.

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

## Maszyna stanów (przepływ aplikacji)

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

`app.py` działa jako **front controller** — przy każdym rerunie Streamlit ewaluuje warunki i renderuje dokładnie jedną stronę (`st.stop()` zapobiega "przeciekaniu").

---

## Kluczowe moduły

### `domain/field_specs.py` — jądro systemu
- **63 pola** na 5 stronach (demografia, skala CES-D, Athene, MFIS, pytania zdrowotne)
- Definiuje `FieldSpec` (nazwa, etykieta, typ, dozwolone wartości, nagłówek CSV)
- **Najczęściej importowany moduł** (6 innych plików) — napędza: walidację Pydantic, generowanie promptów AI, rendering formularzy, nagłówki CSV

### `ai/client.py` — klient OCR
- Async `httpx.AsyncClient` → lokalny **Ollama** (`deepseek-ocr`)
- Retry z exponential backoff (`2^attempt` sekund)
- `analyze_survey()` przetwarza 5 stron sekwencyjnie, scala wyniki
- `analyze_batch()` iteruje po ankietach z callbackami progressu

### `state/state_manager.py` — zarządzanie stanem
- **Static facade** nad `st.session_state` — wszystkie metody `@staticmethod`
- 6 kluczy sesji: `auth`, `surveys`, `current_index`, `ai_results`, `processing`, `cancel_processing`
- Jedyne źródło prawdy dla stanu aplikacji

### `domain/schemas.py` — modele danych
- `MedicalSurvey` (Pydantic BaseModel) — 63 pola + `needs_review`
- `from_ai_json()` — fabryka z normalizacją (regex wieku, fuzzy match dla selectów)
- `normalize_field()` — walidator `@field_validator("*")` z `field_specs`

---

## Przepływ danych (end-to-end)

```
[Upload 5N zdjęć] → ingestion/file_grouping.py → sortowanie, grupowanie po 5
        │
        ▼
[AI OCR] → ai/client.py: base64→Ollama→JSON→merge 5 stron→MedicalSurvey.from_ai_json()
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

## Zależności zewnętrzne

| Pakiet | Użycie |
|--------|--------|
| `streamlit` | UI framework |
| `pydantic` | Modele danych, walidacja |
| `pydantic-settings` | Konfiguracja z env vars |
| `httpx` | Async HTTP → Ollama |
| `Pillow (PIL)` | Przetwarzanie obrazów |

**Serwis:** lokalny Ollama (port 11434), model `deepseek-ocr`

---

## Konfiguracja (`config.py`)

Prefiks env vars: `ANKIETER_*` — hasło, URL Ollama, model, ścieżki plików, retry, timeout, log level. Singleton `config = AppConfig()`.

---

## Kluczowe wzorce architektoniczne

1. **Specification-driven** — `field_specs.py` jest single source of truth, reszta się dopasowuje
2. **State machine routing** — `app.py` jako front controller z `if/elif` chain
3. **Static facade** — `StateManager` bez instancji, dostępny globalnie
4. **Graceful degradation** — błędy AI → puste dicty (nie exceptions), "submit anyway" override
5. **One-time injection guards** — CSS i logging nie duplikują się przy rerunach
6. **Callback pattern** — AI batch reportuje progress przez callbacki do UI

---

## Grafa zależności (importy)

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
