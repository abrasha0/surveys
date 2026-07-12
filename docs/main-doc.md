# Main Documentation — AnkieterAI

## Co to jest i po co

AnkieterAI to automatyczny system wprowadzania ankiet papierowych do formy cyfrowej.
System wykorzystuje lokalny model wizyjno-jężykowy (VLM) serwowany przez Ollamę
do odczytywania danych z zdjęć 5-stronicowych ankiet medycznych.

**Cel:** Zdigitalizować ~150 ankiet (każda po 5 stron) przy minimalnym nakładzie pracy
użytkownika końcowego (osoba nietechniczna).

**Kluczowy koncept:** Human-in-the-loop — AI proponuje odczytane dane, człowiek
weryfikuje i koryguje w szybkim interfejsie side-by-side, a następnie eksportuje
wynik do CSV.

**Środowisko:** Windows, RTX 5070 Ti 16GB VRAM, 32GB RAM. Aplikacja uruchamiana
u dewelopera, dostęp przez Cloudflare tunnel.

---

## Funkcjonalności

- Logowanie hasłem do aplikacji
- Upload zdjęć ankiet (jpg/png/webp)
- Automatyczna analiza obrazów przez VLM (Ollama + deepseek-ocr)
- Dwuetapowe przetwarzanie: VLM → tekst → Text LLM → JSON
- Sekwencyjne przetwarzanie per-strona (jeden model naraz w pamięci GPU)
- Batch processing z progress barem i cache'owaniem wyników
- Weryfikacja i korekta odczytanych danych w interfejsie side-by-side
- Podgląd zdjęć z zoomem (zakładki dla każdej strony)
- Formularz z dynamicznym zaznaczaniem pól o niskiej pewności odczytu
- Skrót klawiszowy Spacja do szybkiego zatwierdzania
- Eksport wyników do CSV (UTF-8 BOM, gotowy do Excela)
- Zapis do cache (wznawianie sesji po przerwie)

---

## Architektura przetwarzania AI

### Sekwencyjne per-strona

Aplikacja przetwarza każdą ankietę sekwencyjnie — stronę po stronie.
Dla każdej strony kolejno:

1. **Pre-processing obrazu** — resize (max 2000px), grayscale, contrast (Pillow)
2. **VLM (deepseek-ocr)** — ekstrakcja surowego tekstu z obrazu
3. **Text LLM (llama3.1)** — formatowanie surowego tekstu do struktury JSON

Następnie: strona 2, strona 3, ..., strona 5. Wyniki 5 stron są merge'owane
do jednego obiektu MedicalSurvey.

### Dlaczego sekwencyjnie (nie producer-consumer)?

- Tylko jeden model naraz w pamięci GPU (mniejsze zużycie VRAM)
- Przewidywalny, deterministyczny flow — łatwy w debugowaniu i logowaniu
- Lepsza separacja odpowiedzialności (wizja vs. formatowanie)

### Zarządzanie VRAM

- `keep_alive: "5m"` — model pozostaje w VRAM przez 5 minut po żądaniu
- `temperature: 0.0` — absolutny determinizm
- `num_ctx: 8192` — rozmiar kontekstu

### Prompty

Prompty zdefiniowane w `config.yaml` (sekcja `prompts`), nie w kodzie.
Dwa prompty:
- `vlm` — ekstrakcja surowego tekstu z obrazu
- `text_format` — formatowanie tekstu do JSON

---

## Model danych

Aplikacja obsługuje ankietę złożoną z 63 pól na 5 stronach.
Szczegółowa struktura: patrz `docs/survey-structure.md`.

Sekcje:
- **Strona 1:** Demografia (7), aktywność zawodowa (4), styl życia (3) = 14 pól
- **Strona 2:** CES-D — skala depresji = 20 pól
- **Strona 3:** Athens — skala bezsenności = 8 pól
- **Strona 4:** MFIS — skala zmęczenia (pozycje 1-15) = 15 pól
- **Strona 5:** MFIS (16-21) + stan zdrowia = 10 pól

---

## Flow użytkownika

### 1. Logowanie
Użytkownik wpisuje hasło (domyślne: `a`). Hasło skonfigurowane w `config.yaml`.

### 2. Upload i grupowanie
Użytkownik wybiera zdjęcia ankiet (jpg/png/webp). System sortuje je alfabetycznie
i grupuje po 5 stron (1 ankieta = 5 zdjęć).

### 3. Przetwarzanie AI (batch)
Kliknięcie "Rozpocznij analizę" uruchamia batch AI. Dla każdej ankiety (sekwencyjnie):
5 stron × (VLM → Text LLM) → merge → MedicalSurvey. Wyniki cache'owane
w `logs/cache_results.json`. Użytkownik widzi pasek postępu.

### 4. Weryfikacja
Ekran side-by-side:
- **Lewa kolumna:** Podgląd obrazu aktualnej strony (5 zakładek)
- **Prawa kolumna:** Formularz z odczytanymi danymi
- Pola oznaczone przez AI jako wątpliwe (`needs_review`) podświetlone na czerwono
- Skrót klawiszowy Spacja = "Zatwierdź i Następna"

### 5. Zapis i następna ankieta
Kliknięcie "Zatwierdź" → zapis do CSV (`wyniki.csv`) → następna ankieta.
Przy błędach: możliwość zatwierdzenia mimo błędów.

### 6. Eksport CSV
Po przetworzeniu wszystkich ankiet: download CSV (UTF-8 BOM, gotowy do Excela).

---

## Konfiguracja

### Plik konfiguracyjny
Aplikacja wykorzystuje `config.yaml` jako główne źródło konfiguracji.
Skopiuj `config.yaml.example` i dostosuj do swojego środowiska.

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
.\scripts\setup_env.ps1          # Tworzenie venv, instalacja deps
.\scripts\setup_ollama.ps1       # Instalacja Ollamy, pull modelu
.venv\Scripts\Activate.ps1
streamlit run src/app.py         # Start aplikacji
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

Aplikacja dostępna pod `http://localhost:8501`. Domyślne hasło: `a`.

---

## Testy

```powershell
.venv\Scripts\Activate.ps1
pytest tests/
```

52 testy, 6 plików testowych:
- `test_schemas.py` — testy modeli danych, normalizacji, CSV
- `test_data_handler.py` — testy grupowania, cache, CSV
- `test_state_manager.py` — testy stanu sesji
- `test_ai_client.py` — testy klienta AI (base64, merge)
- `test_csv_integrity.py` — testy spójności CSV
- `conftest.py` — fixture'y

---

## Ograniczenia i przyszłe ulepszenia

### Otwarte issues
Patrz `docs/known-issues.md`.

### Możliwe ulepszenia
- `@st.fragment` — izolacja rerunów UI (wydajność)
- `st.form` — batchowanie inputów formularza
- Dynamiczne generowanie UI z `field_specs` (zamiast hardkodowanych zakładek)

---

## Historia projektu (krótko)

- **Początek:** Pierwotny brief definiował architekturę flat, single-model, batch-first
- **Optymalizacja:** 4 etapy — preprocessing obrazów, architektura dwuetapowa,
  sekwencyjne przetwarzanie, LangSmith tracing
- **Refaktor:** Przejście z flat struktury (`src/main.py`, `src/ai_client.py`...)
  do modularnej (`src/ai/`, `src/domain/`, `src/ui/`, `src/state/`)
- **Config:** Centralizacja konfiguracji do `config.yaml` (zamiast Pydantic Settings)
