# AnkieterAI

Automatyczny system wprowadzania ankiet papierowych do formy cyfrowej z wykorzystaniem lokalnego modelu wizyjno-jężykowego (VLM).

## Quick Start

1. Przygotowanie środowiska (Python + npm):

   ```powershell
   .\scripts\setup_env.ps1
   ```

2. Uruchomienie Ollamy:

   ```powershell
   .\scripts\setup_ollama.ps1
   ```

3. Pełne uruchomienie produkcyjne:

   ```powershell
   .\scripts\full_setup.ps1
   ```

4. Uruchomienie deweloperskie (z hot-reloadem):

   ```powershell
   .\scripts\run_dev.ps1
   ```

Aplikacja dostępna pod `http://localhost:8000` (produkcja) lub `http://localhost:5173` (dev frontend z proxy API). Domyślne hasło: `a`.

> **Wymagania:** Python ≥ 3.12, Node.js (dla frontendu React).

## Funkcjonalności

- Logowanie hasłem do aplikacji
- Automatyczna analiza zdjęć ankiet przez VLM (Ollama) + Text LLM
- Batch processing z progress barem, ETA i cache'owaniem wyników
- Kolejka przetwarzania z równoległą weryfikacją gotowych ankiet
- Weryfikacja i korekta odczytanych danych w interfejsie side-by-side
- Podgląd zdjęć z zakładkami dla każdej strony
- Formularz z walidacją pól wymaganych
- Skrót klawiszowy Spacja do szybkiego zatwierdzania
- Eksport wyników do CSV (UTF-8 BOM, gotowy do Excela)
- Tryb deweloperski z hot-reloadem (Vite + uvicorn --reload)
- Cloudflare tunnel do udostępnienia publicznego

## Konfiguracja

Aplikacja wykorzystuje `config.yaml` jako główne źródło konfiguracji.
Skopiuj `config.yaml.example` i dostosuj do swojego środowiska.

Zmienne środowiskowe z prefiksem `ANKIETER_*` nadpisują wartości z pliku YAML.

Szczegóły: patrz `config.yaml.example` (skomentowane klucze) oraz `docs/main-doc.md`.

## Testy

```powershell
.venv\Scripts\Activate.ps1
pytest tests/
```

## Dokumentacja

- `docs/architecture-report.md` — opis architektury i modułów
- `docs/survey-structure.md` — pełna struktura ankiety (70 pól)
- `docs/main-doc.md` — szczegółowy opis flow, funkcjonalności, konfiguracji
- `docs/known-issues.md` — bieżące problemy
