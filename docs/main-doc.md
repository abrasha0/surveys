# Main Documentation — AnkieterAI

## Co to jest i po co

AnkieterAI to automatyczny system wprowadzania ankiet papierowych do formy cyfrowej.
System wykorzystuje lokalny model wizyjno-jężykowy (VLM) serwowany przez Ollamę
do odczytywania danych ze zdjęć 5-stronicowych ankiet medycznych.

**Stack:** FastAPI (backend) + React + Vite (frontend) + Ollama (AI)
**Cel:** Zdigitalizować ~150 ankiet (każda po 5 stron) przy minimalnym nakładzie pracy
użytkownika końcowego (osoba nietechniczna).

**Kluczowy koncept:** Human-in-the-loop — AI proponuje odczytane dane, człowiek
weryfikuje i koryguje w szybkim interfejsie side-by-side, a następnie eksportuje
wynik do CSV.

**Środowisko:** Windows, RTX 5070 Ti 16GB VRAM, 32GB RAM. Aplikacja uruchamiana
u dewelopera, dostęp przez Cloudflare tunnel.

**Model przetwarzania:** Jeden globalny asynchroniczny worker w tle (asyncio.Task),
przetwarzający ankiety sekwencyjnie. System rozróżnia dwa poziomy retry:
`ai.max_retries` (ponawianie pojedynczego requestu do Ollamy) oraz
`processing.worker_max_retries` (ponawianie całej ankiety w workerze).

---

## Funkcjonalności

- Logowanie hasłem do aplikacji
- Automatyczna analiza zdjęć ankiet przez VLM (Ollama) + Text LLM
- Dwuetapowe przetwarzanie: VLM → tekst → Text LLM → JSON
- Sekwencyjne przetwarzanie per-strona (jeden model naraz w pamięci GPU)
- Globalny worker w tle z kolejkowaniem, ETA i możliwością zatrzymania (POST /api/processing/stop)
- Interleaved verification — weryfikacja gotowych ankiet w trakcie przetwarzania kolejnych
- Batch processing z progress barem (liczony przez backend z rolling average) i cache'owaniem per-survey
- Weryfikacja i korekta odczytanych danych w interfejsie side-by-side (podział 40/60)
- Dwuetapowe zatwierdzanie: pierwsze kliknięcie uruchamia walidację, drugie "Zatwierdź mimo błędów" wymusza zapis
- Persystencja draftów formularza (Zustand + localStorage) — zmiany nie giną przy nawigacji między ankietami
- Dynamiczne generowanie formularza z definicji pól (field-specs z API)
- Podgląd zdjęć z zakładkami dla każdej strony (5 stron), pamiętany wybór per ankieta
- Skrót klawiszowy Spacja do szybkiego zatwierdzania (ignorowany przy focusie w polu tekstowym)
- Eksport wyników do CSV (UTF-8 BOM, 71 kolumn, gotowy do Excela)
- Lokalny katalog zdjęć (brak uploadu przez sieć — przetwarzanie bezpośrednio z dysku)
- Cache per-survey (working_vault/logs/survey_cache/survey_{idx}.json) — wznawianie sesji po restarcie serwera
- Polling statusu co 2s (GET /api/processing/status + GET /api/surveys)

---

## Architektura przetwarzania AI

### Sekwencyjne per-strona

Aplikacja przetwarza każdą ankietę sekwencyjnie — stronę po stronie.
Dla każdej strony kolejno:

1. **Pre-processing obrazu** — resize (max 2000px), grayscale, contrast (Pillow)
2. **VLM** — ekstrakcja surowego tekstu z obrazu (model skonfigurowany w `config.yaml`)
3. **Text LLM** — formatowanie surowego tekstu do struktury JSON

    > **Dobór modeli:** `config.yaml.example` zawiera przykładowy zestaw. Na GPU ≥8GB VRAM
    > sprawdź modele średniej wielkości (np. `qwen3-vl:8b` + `llama3.1`).
    > Na słabszym sprzęcie lub do testów — lekkie modele (np. `moondream` + `llama3.2:3b`).

Następnie: strona 2, strona 3, ..., strona 5. Wyniki 5 stron są merge'owane
do jednego obiektu MedicalSurvey.

### Architektura systemu

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  React UI   │────▶│  FastAPI     │────▶│  Worker (tło)   │────▶│  Ollama AI   │
│  (src/frontend/)│◀────│  (src/backend/)│◀────│  + kolejka      │     │  (VLM+Text)  │
└─────────────┘     └──────┬───────┘     └─────────────────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  working_vault/│
                    │  dist/        │
                    └──────────────┘
```

Frontend (React) komunikuje się z backendem przez REST API na porcie 8000.
W produkcji backend serwuje również zbudowane pliki frontendu z `working_vault/dist/`.
Worker działa w tle — przetwarza ankiety sekwencyjnie, umożliwiając weryfikację
gotowych wyników w trakcie przetwarzania kolejnych (interleaved).

### Zarządzanie VRAM

- `keep_alive: "5m"` — model pozostaje w VRAM przez 5 minut po żądaniu
- `temperature: 0.0` — absolutny determinizm
- `num_ctx: 8192` — rozmiar kontekstu

### Prompty

Prompty zdefiniowane w `config.yaml` (sekcja `prompts`), nie w kodzie.
Struktura promptów:
- `vlm` — ekstrakcja surowego tekstu z obrazu (z placeholders `{page_idx}`)
- `text_format` — formatowanie tekstu do JSON (z placeholders `{vlm_output}`, `{page_json_schema}`)
- `page_1_json_schema`..`page_5_json_schema` — 5 schematów JSON per-strona z dozwolonymi wartościami

To oznacza, że zmiana formatu ankiety (np. dodanie/usunięcie pola) wymaga aktualizacji:
1. `src/backend/domain/field_specs.py` — definicja pola
2. Odpowiedniego `page_N_json_schema` w `config.yaml` — dla ekstrakcji AI

---

## Model danych

Aplikacja obsługuje ankietę złożoną z **70 pól** na 5 stronach (63 oryginalne + 7 rozszerzonych pól "Inne").
Szczegółowa struktura: patrz `docs/survey-structure.md`.

Sekcje:
- **Strona 1:** Demografia (8), aktywność zawodowa (6), styl życia (3) = **17 pól** (w tym 3x "Inne")
- **Strona 2:** CES-D — skala depresji = **20 pól**
- **Strona 3:** Athens — skala bezsenności = **8 pól**
- **Strona 4:** MFIS — skala zmęczenia (pozycje 1-15) = **15 pól**
- **Strona 5:** MFIS (16-21) + stan zdrowia = **10 pól**

---

## Flow użytkownika

### 1. Logowanie
Użytkownik wpisuje hasło skonfigurowane w `config.yaml` (patrz `config.yaml.example` — szablon z pustym hasłem jako placeholder; przed uruchomieniem ustaw własne).

### 2. Skanowanie lokalnego katalogu
System skanuje katalog `surveys_data` (konfigurowalny w `config.yaml`) i grupuje
zdjęcia alfabetycznie po 5 sztuk (1 ankieta = 5 zdjęć). Brak uploadu — zdjęcia
są procesowane bezpośrednio z lokalnego dysku.

### 3. Przetwarzanie AI (worker w tle)
Kliknięcie "Rozpocznij analizę" uruchamia worker w tle. Dla każdej ankiety
(sekwencyjnie): 5 stron × (VLM → Text LLM) → merge → MedicalSurvey.
Wyniki cache'owane w `working_vault/logs/survey_cache/`. Użytkownik widzi pasek postępu z ETA.

### 4. Weryfikacja (interleaved)
Ekran side-by-side — dostępny natychmiast po przetworzeniu pierwszej ankiety:
- **Lewa kolumna (~40%):** Podgląd obrazu aktualnej strony (5 zakładek, wybór pamiętany per ankieta)
- **Prawa kolumna (~60%):** Formularz z odczytanymi danymi AI (prefill), generowany dynamicznie z field-specs
- Formularz z walidacją pól wymaganych (czerwone kropki po pierwszej próbie zatwierdzenia)
- Skrót klawiszowy Spacja = "Zatwierdź" (ignorowany przy focusie w polu tekstowym)
- **Dwuetapowe zatwierdzanie:** pierwsze kliknięcie → walidacja (jeśli błędy → pokaż kropki, nie wysyła);
  przycisk "Zatwierdź mimo błędów" → force save do CSV
- **Draft persistence:** wartości formularza zapisywane do localStorage (Zustand, debounce 500ms) —
  przejście do innej ankiety i powrót nie traci wprowadzonych danych

Możliwość przełączania między gotowymi ankietami w trakcie przetwarzania kolejnych.
Pasek postępu przetwarzania (ProcessingProgressBar) widoczny na górze ekranu — pokazuje
ETAs, aktualny etap modelu (VLM/format), liczbę przetworzonych/błędnych ankiet.

### 5. Zapis i następna ankieta
Kliknięcie "Zatwierdź ankietę" (lub Spacja przy braku błędów) → walidacja przez
`MedicalSurvey` → zapis wiersza do CSV (`working_vault/wyniki.csv`) przez `save_survey_to_csv()` →
status ankiety `ready` → `verified` → automatyczne przejście do następnej gotowej ankiety.

### 6. Ekran zakończenia
Po zweryfikowaniu wszystkich ankiet: komunikat sukcesu, przycisk "Pobierz CSV"
i "Nowa sesja".

### 7. Eksport CSV
Download CSV (UTF-8 BOM, gotowy do Excela) z poziomu ekranu zakończenia.

---

## Konfiguracja

### Plik konfiguracyjny
Aplikacja wykorzystuje `config.yaml` jako główne źródło konfiguracji.
Skopiuj `config.yaml.example` i dostosuj do swojego środowiska.

Sekcje `config.yaml`:

| Sekcja       | Opis                                                   |
|--------------|--------------------------------------------------------|
| `app`        | Tytuł, hasło, ścieżki, dozwolone typy plików           |
| `ai`         | Modele (VLM + Text), URL Ollama, retry, timeout, num_ctx, temperature, keep_alive |
| `image`      | max_dimension, contrast_factor, jpeg_quality            |
| `ingestion`  | survey_group_size, upload_dir_prefix                    |
| `logging`    | Plik, poziom, rotacja logów AI, skracanie I/O          |
| `langsmith`  | tracing_v2, endpoint, api_key, project                  |
| `processing` | progress_vlm_weight, progress_text_weight, history_display_limit, worker_max_retries, eta_rolling_window, survey_cache_dir |
| `prompts`    | VLM, text_format + **5 schematów JSON per-strona** (`page_1_json_schema`..`page_5_json_schema`) |

> **Uwaga — dwa osobne retry:** System rozróżnia `ai.max_retries` (ponawianie
> pojedynczego requestu do Ollamy, np. przy timeout) oraz
> `processing.worker_max_retries` (ponawianie całej ankiety w workerze po 3
> nieudanych próbach). Oba konfigurowalne w `config.yaml`.

### Zmienne środowiskowe
Zmienne z prefiksem `ANKIETER_*` nadpisują wartości z pliku YAML.
Przykład: `ANKIETER_VLM_MODEL=custom-model` zmienia model VLM.

### LangSmith (opcjonalne)
Aby włączyć śledzenie wywołań AI w dashboardzie LangSmith:

| Zmienna | Domyślna | Opis |
|---------|----------|------|
| `LANGCHAIN_TRACING_V2` | false | Włącz/wyłącz tracing |
| `LANGCHAIN_ENDPOINT` | — | URL API LangSmith |
| `LANGCHAIN_API_KEY` | — | Klucz API LangSmith |
| `LANGCHAIN_PROJECT` | ankieterai | Nazwa projektu |

Tracing jest opcjonalny — gdy wyłączony lub gdy pakiet `langsmith` nie jest
zainstalowany, traces są pomijane (no-op).

---

## Deployment

### Scenariusz 1: Ręczny
```powershell
.\scripts\setup_env.ps1          # Tworzenie venv, pip install, npm install
.\scripts\setup_ollama.ps1       # Instalacja Ollamy, pull modelu
.venv\Scripts\Activate.ps1
cd src/frontend; npm run build; cd ../..
Copy-Item src/frontend/dist/* working_vault/dist/ -Recurse -Force  # build do working_vault/dist/
cd src/backend; uvicorn main:app --port 8000            # Start aplikacji
```

### Scenariusz 2: Automatyczny
```powershell
.\scripts\full_setup.ps1         # Uruchamia wszystkie skrypty
```

### Scenariusz 3: Z tunelem Cloudflare
```powershell
.\scripts\full_setup.ps1         # W tym tunelem
# lub osobno:
.\scripts\deploy_tunnel.ps1      # Tylko tunel
```

Aplikacja dostępna pod `http://localhost:8000`. Hasło ustawiasz w `config.yaml` (szablon w `config.yaml.example` ma pusty placeholder).

### Uruchomienie deweloperskie (hot-reload)
```powershell
.\scripts\run_dev.ps1            # uvicorn --reload (port 8000) + Vite dev (port 5173)
```

Frontend deweloperski: `http://localhost:5173` (proxy `/api` → `localhost:8000`).

---

## Ograniczenia i przyszłe ulepszenia

### Otwarte issues
Patrz `docs/known-issues.md`.

### Możliwe ulepszenia
- Próg re-OCR dla niskiej jakości odczytu (issue #7)
- Testy automatyczne (backend + frontend)
- WebSocket/SSE zamiast pollingu (2s interwał) dla szybszej aktualizacji statusu
- Autoodświeżanie tokena sesyjnego (obecnie stały 8h TTL bez refresh)
