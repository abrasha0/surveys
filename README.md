# AnkieterAI

Automatyczny system wprowadzania ankiet papierowych do formy cyfrowej z wykorzystaniem lokalnego modelu wizyjno-jężykowego (VLM).

**Stack:** FastAPI (backend) + React + Vite (frontend) + Ollama (AI)

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

- Logowanie hasłem do aplikacji (HMAC cookie, single-user session)
- Automatyczna analiza zdjęć ankiet przez VLM (Ollama) + Text LLM
- Dwuetapowe przetwarzanie: VLM → tekst → Text LLM → JSON (70 pól na 5 stronach)
- Globalny asynchroniczny worker w tle z kolejką, retry 3x, ETA (rolling average) i możliwością zatrzymania
- Interleaved verification — weryfikacja gotowych ankiet w trakcie przetwarzania kolejnych
- Weryfikacja i korekta odczytanych danych w interfejsie side-by-side (podział 40/60)
- Dwuetapowe zatwierdzanie: walidacja → "Zatwierdź mimo błędów" (force save)
- Persystencja draftów formularza (Zustand + localStorage) — zmiany nie giną przy nawigacji
- Dynamiczne generowanie formularza z definicji pól (field-specs z API)
- Podgląd zdjęć z zakładkami dla każdej strony (5 stron), wybór pamiętany per ankieta
- Skrót klawiszowy Spacja do szybkiego zatwierdzania (ignorowany przy focusie w polu)
- Eksport wyników do CSV (UTF-8 BOM, 71 kolumn, gotowy do Excela)
- Lokalny katalog zdjęć (brak uploadu przez sieć — przetwarzanie bezpośrednio z dysku)
- Cache per-survey (logs/survey_cache/) + wznawianie sesji po restarcie serwera
- Polling statusu co 2s (GET /api/processing/status + GET /api/surveys)
- Tryb deweloperski z hot-reloadem (Vite + uvicorn --reload)
- Cloudflare tunnel do udostępnienia publicznego

## Konfiguracja

Aplikacja wykorzystuje `config.yaml` jako główne źródło konfiguracji.
Skopiuj `config.yaml.example` i dostosuj do swojego środowiska.

Zmienne środowiskowe z prefiksem `ANKIETER_*` nadpisują wartości z pliku YAML.

Szczegóły: patrz `config.yaml.example` (skomentowane klucze) oraz `docs/main-doc.md`.

## Architektura frontendu

Frontend (React 19 + Vite 8 + TypeScript 6) znajduje się w `src_ui/`:
- **Routing:** React Router DOM 7 (`/login`, `/app`, `/complete`)
- **Stan serwerowy:** TanStack Query 5 (polling, cache, mutacje)
- **Stan lokalny:** Zustand 5 (UI state, drafty formularzy, localStorage persistence)
- **Stylowanie:** Tailwind CSS 4
- **Auth:** HMAC cookie (session_token, 8h TTL)

## Dokumentacja

- `docs/architecture-report.md` — opis architektury i modułów
- `docs/survey-structure.md` — pełna struktura ankiety (70 pól, 5 stron)
- `docs/main-doc.md` — szczegółowy opis flow, funkcjonalności, konfiguracji
- `docs/known-issues.md` — bieżące problemy

## Uwagi

- `react-refactor-docs/` — archiwum planów migracji Streamlit → FastAPI + React (nie odzwierciedla bieżącego stanu)
