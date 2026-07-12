# AnkieterAI

Automatyczny system wprowadzania ankiet papierowych do formy cyfrowej z wykorzystaniem lokalnego modelu wizyjno-jężykowego (VLM).

## Architektura

System wykorzystuje architekturę **Producer-Consumer** z dwoma modelami AI:

- **VLM (deepseek-ocr)** — ekstrakcja surowego tekstu z obrazów ankiet
- **Text LLM (llama3.1)** — formatowanie surowego tekstu do struktury JSON

Dzięki temu uzyskujemy:
- Nakładanie faz: podczas gdy Text LLM formatuje jedną stronę, VLM ekstrakuje kolejną
- Automatyczny fallback sekwencyjny przy VRAM OOM
- Lepszą separację odpowiedzialności (wizja vs. formatowanie)

## Funkcjonalności

- Logowanie hasłem do aplikacji
- Upload zdjęć ankiet (jpg/png/webp)
- Automatyczna analiza obrazów przez VLM (Ollama + deepseek-ocr)
- Dwuetapowe przetwarzanie: VLM → tekst → Text LLM → JSON
- Producer-consumer z `asyncio.Queue` dla optymalnego wykorzystania GPU
- Auto-fallback sekwencyjny przy VRAM OOM
- Batch processing z progress barem i cache'owaniem wyników
- Weryfikacja i korekta odczytanych danych w interfejsie side-by-side
- Podgląd zdjęć z zoomem (zakładki dla każdej strony)
- Formularz z dynamicznym zaznaczaniem pól o niskiej pewności odczytu
- Skrót klawiszowy Spacja do szybkiego zatwierdzania
- Eksport wyników do CSV (UTF-8 BOM, gotowy do Excela)
- Zapis do cache (wznawianie sesji po przerwie)

## Konfiguracja

### Podstawowa

| Zmienna środowiskowa | Domyślna wartość | Opis |
|---------------------|------------------|------|
| `ANKIETER_VLM_MODEL` | `deepseek-ocr` | Model wizyjny (VLM) |
| `ANKIETER_TEXT_MODEL` | `llama3.1` | Model tekstowy (formatowanie) |
| `ANKIETER_OLLAMA_NUM_PARALLEL` | `2` | Liczba równoległych żądań |
| `ANKIETER_OLLAMA_URL` | `http://localhost:11434` | URL serwera Ollama |
| `ANKIETER_MAX_RETRIES` | `3` | Maksymalna liczba ponawiań |

### LangSmith (opcjonalne)

Aby włączyć śledzenie wywołań AI w dashboardzie LangSmith, ustaw zmienne środowiskowe:

| Zmienna środowiskowa | Domyślna wartość | Opis |
|---------------------|------------------|------|
| `LANGCHAIN_TRACING_V2` | `false` | Włącz/wyłącz tracing |
| `LANGCHAIN_ENDPOINT` | — | URL API LangSmith |
| `LANGCHAIN_API_KEY` | — | Klucz API LangSmith |
| `LANGCHAIN_PROJECT` | `ankieterai` | Nazwa projektu w LangSmith |

Tracing jest opcjonalny — gdy wyłączony lub gdy pakiet `langsmith` nie jest zainstalowany, traces są pomijane (no-op).

### Logi

- `logs/ankieter.log` — logi główne aplikacji (rotacja: brak)
- `logs/ai_requests.log` — dedykowany log wywołań AI per-call (rotacja: 10MB, 3 kopie zapasowe)
- `logs/cache_results.json` — cache wyników analizy

## Uruchomienie

1. Przygotowanie środowiska:

   ```powershell
   .\scripts\setup_env.ps1
   ```

2. Uruchomienie Ollamy:

   ```powershell
   .\scripts\setup_ollama.ps1
   ```

3. Start aplikacji:
   ```powershell
   .venv\Scripts\Activate.ps1
   streamlit run src/app.py
   ```

Aplikacja dostępna pod `http://localhost:8501`. Domyślne hasło: `a`.

## Testy

```powershell
.venv\Scripts\Activate.ps1
pytest tests/
```
