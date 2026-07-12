# AnkieterAI

Automatyczny system wprowadzania ankiet papierowych do formy cyfrowej z wykorzystaniem lokalnego modelu wizyjno-jężykowego (VLM).

## Quick Start

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

## Funkcjonalności

- Logowanie hasłem do aplikacji
- Upload zdjęć ankiet (jpg/png/webp)
- Automatyczna analiza obrazów przez VLM (Ollama + deepseek-ocr)
- Dwuetapowe przetwarzanie: VLM → tekst → Text LLM → JSON
- Sekwencyjne przetwarzanie per-strona (jeden model naraz)
- Batch processing z progress barem i cache'owaniem wyników
- Weryfikacja i korekta odczytanych danych w interfejsie side-by-side
- Podgląd zdjęć z zoomem (zakładki dla każdej strony)
- Formularz z dynamicznym zaznaczaniem pól o niskiej pewności odczytu
- Skrót klawiszowy Spacja do szybkiego zatwierdzania
- Eksport wyników do CSV (UTF-8 BOM, gotowy do Excela)

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
- `docs/survey-structure.md` — pełna struktura ankiety (63 pola)
- `docs/main-doc.md` — szczegółowy opis flow, funkcjonalności, konfiguracji
- `docs/known-issues.md` — bieżące problemy
