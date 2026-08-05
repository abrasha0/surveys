# AnkieterAI

Automatyczny system wprowadzania ankiet papierowych do formy cyfrowej z wykorzystaniem lokalnego modelu wizyjno-jężykowego (VLM).

**Stack:** FastAPI (backend) + React + Vite (frontend) + Ollama (AI)

## Quick Start

Trzy skrypty w `scripts/`:

| Skrypt | Kiedy | Co robi |
|---|---|---|
| `full_setup.ps1` | **Raz** (pierwsze uruchomienie) | Tworzy .venv, instaluje pakiety Python i npm, instaluje Ollamę, pobiera modele AI |
| `run_prod.ps1` | **Każde uruchomienie** | Buduje frontend, startuje backend + API, wystawia przez tunel Cloudflare |
| `run_dev.ps1` | **Programowanie** | Hot-reload backendu (uvicorn --reload) + Vite HMR frontendu na osobnym porcie |

```powershell
# Pierwsze uruchomienie -- przygotowanie srodowiska (jednorazowo):
.\scripts\full_setup.ps1

# Kazde kolejne uruchomienie produkcyjne:
.\scripts\run_prod.ps1               # z tunelem Cloudflare
.\scripts\run_prod.ps1 -NoTunnel     # tylko lokalnie, bez tunelu

# Tryb deweloperski:
.\scripts\run_dev.ps1
```

**Po uruchomieniu:**
- Produkcja: `http://localhost:8000` (backend serwuje API + zbudowany frontend)
- Dev: frontend `http://localhost:5173` (Vite z proxy /api → :8000), backend `:8000` tylko API
- Tunel Cloudflare (run_prod): URL wyświetlany w konsoli i zapisywany do `working_vault/logs/tunnel_url.txt`

Hasło ustawiasz w `config.yaml` — skopiuj z `config.yaml.example` i edytuj.

> **Uwaga:** Jeśli wejdziesz na `http://localhost:8000` przed zbudowaniem frontendu, zobaczysz stronę z instrukcją uruchomienia zamiast błędu 404.

> **Wymagania:** Python ≥ 3.12, Node.js ≥ 18 (ręcznie, skrypt tylko sprawdza i informuje).

## Funkcjonalności

- Logowanie hasłem do aplikacji (HMAC cookie, single-user session)
- Automatyczna analiza zdjęć ankiet przez VLM (Ollama) + Text LLM
- Dwuetapowe przetwarzanie: VLM → tekst → Text LLM → JSON (70 pól na 5 stronach)
- Globalny asynchroniczny worker w tle z kolejką, retry (per-request do Ollamy + per-survey w workerze), ETA (rolling average) i możliwością zatrzymania
- Batch processing — suwak (1..pozostałe) ustawia liczbę ankiet przetwarzanych w sesji, ETA liczone dla batcha, po zakończeniu batcha worker się kończy i można uruchomić następny ("Następny batch")
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
Skopiuj `config.yaml.example` → `config.yaml` i **dostosuj do swojego środowiska**:
- **Hasło:** ustaw własne w `app.password`
- **Modele AI:** dobierz do swojego hardware (patrz niżej)
- **Ścieżki:** opcjonalnie dostosuj katalogi

Zmienne środowiskowe z prefiksem `ANKIETER_*` nadpisują wartości z pliku YAML.
Przykład: `$env:ANKIETER_VLM_MODEL="moondream"` zmienia model VLM bez edycji pliku.

System rozróżnia dwa osobne retry: `ai.max_retries` (ponawianie pojedynczego
requestu do Ollamy) oraz `processing.worker_max_retries` (ponawianie całej
ankiety po 3 nieudanych próbach).

> **Dobór modeli AI:**
> - GPU ≥8GB VRAM — sprawdź średnie modele, np. `qwen3-vl:8b` + `llama3.1`
> - Słabszy sprzęt / testy — lekkie modele, np. `moondream` + `llama3.2:3b`
> - Zestaw przykładowy i komentarze: `config.yaml.example`

Szczegóły: patrz `config.yaml.example` (skomentowane klucze) oraz `docs/main-doc.md`.

## Architektura frontendu

Frontend (React 19 + Vite 8 + TypeScript 6) znajduje się w `src/frontend/`:
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

- Dokumentacja: `docs/main-doc.md`, `docs/architecture-report.md`, `docs/survey-structure.md`, `docs/known-issues.md`
