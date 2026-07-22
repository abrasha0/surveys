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

---

## Funkcjonalności

- Logowanie hasłem do aplikacji
- Automatyczna analiza zdjęć ankiet przez VLM (Ollama) + Text LLM
- Dwuetapowe przetwarzanie: VLM → tekst → Text LLM → JSON
- Sekwencyjne przetwarzanie per-strona (jeden model naraz w pamięci GPU)
- Globalny worker w tle z kolejkowaniem i ETA
- Interleaved verification — weryfikacja gotowych ankiet w trakcie przetwarzania kolejnych
- Batch processing z progress barem i cache'owaniem wyników
- Weryfikacja i korekta odczytanych danych w interfejsie side-by-side
- Podgląd zdjęć z zoomem (zakładki dla każdej strony)
- Formularz z walidacją pól wymaganych
- Skrót klawiszowy Spacja do szybkiego zatwierdzania
- Eksport wyników do CSV (UTF-8 BOM, gotowy do Excela)
- Lokalny katalog zdjęć (brak uploadu przez sieć)
- Zapis do cache per-survey (wznawianie sesji po przerwie)

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

### Architektura systemu

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  React UI   │────▶│  FastAPI     │────▶│  Worker (tło)   │
│  (src_ui/)  │◀────│  (src/)      │◀────│  + Ollama AI    │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
                    ┌──────▼───────┐
                    │  dist/       │
                    │  (StaticFiles)│
                    └──────────────┘
```

Frontend (React) komunikuje się z backendem przez REST API na porcie 8000.
W produkcji backend serwuje również zbudowane pliki frontendu z `dist/`.
Worker działa w tle — przetwarza ankiety sekwencyjnie, umożliwiając weryfikację
gotowych wyników w trakcie przetwarzania kolejnych (interleaved).

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

### 2. Skanowanie lokalnego katalogu
System skanuje katalog `surveys_data` (konfigurowalny w `config.yaml`) i grupuje
zdjęcia alfabetycznie po 5 sztuk (1 ankieta = 5 zdjęć). Brak uploadu — zdjęcia
są procesowane bezpośrednio z lokalnego dysku.

### 3. Przetwarzanie AI (worker w tle)
Kliknięcie "Rozpocznij analizę" uruchamia worker w tle. Dla każdej ankiety
(sekwencyjnie): 5 stron × (VLM → Text LLM) → merge → MedicalSurvey.
Wyniki cache'owane w `logs/survey_cache/`. Użytkownik widzi pasek postępu z ETA.

### 4. Weryfikacja (interleaved)
Ekran side-by-side — dostępny natychmiast po przetworzeniu pierwszej ankiety:
- **Lewa kolumna:** Podgląd obrazu aktualnej strony (5 zakładek)
- **Prawa kolumna:** Formularz z odczytanymi danymi
- Formularz z walidacją pól wymaganych
- Skrót klawiszowy Spacja = "Zatwierdź i Następna"

Możliwość przełączania między gotowymi ankietami w trakcie przetwarzania kolejnych.

### 5. Zapis i następna ankieta
Kliknięcie "Zatwierdź ankietę" → walidacja → zapis do CSV (`wyniki.csv`) →
automatyczne przejście do następnej ankiety.

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
| `ai`         | Modele, URL Ollama, retry, timeout, num_ctx, temperature, keep_alive |
| `image`      | max_dimension, contrast_factor, jpeg_quality            |
| `ingestion`  | survey_group_size                                       |
| `logging`    | Plik, poziom, rotacja logów AI, skracanie I/O          |
| `langsmith`  | tracing_v2, endpoint, api_key, project                  |
| `processing` | Wagi progress bara, retry, ETA window, cache_dir       |
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
.\scripts\setup_env.ps1          # Tworzenie venv, pip install, npm install
.\scripts\setup_ollama.ps1       # Instalacja Ollamy, pull modelu
.venv\Scripts\Activate.ps1
cd src_ui; npm run build; cd ..
Copy-Item src_ui/dist/* dist/ -Recurse -Force
uvicorn main:app --port 8000     # Start aplikacji (z katalogu src/)
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

Aplikacja dostępna pod `http://localhost:8000`. Domyślne hasło: `a`.

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
- Próg re-OCR dla niskiej jakości odczytu
- Dynamiczne generowanie UI z `field_specs` (zamiast hardkodowanych zakładek)
- Testy automatyczne dla nowego stacka (FastAPI + React)
