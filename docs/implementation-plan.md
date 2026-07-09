# Plan Implementacji: AnkieterAI

## Metadane

- **Project:** AnkieterAI — Zautomatyzowany system wprowadzania ankiet papierowych (VLM)
- **Stack:** Python 3.12, Streamlit, Ollama (deepseek-ocr), Cloudflared Tunnel
- **Hardware:** Windows, RTX 5070 Ti 16GB VRAM, 32GB RAM
- **Hasło domyślne:** `a`
- **Model VLM:** `deepseek-ocr`

---

## Struktura katalogów

```
C:\workspace\dev\surveys\
├── docs/
│   ├── sketch-master-prompt.md      # Pierwotne wytyczne
│   └── implementation-plan.md       # Niniejszy plan
├── logs/                            # Logi, errory, cache
├── src/
│   ├── __init__.py
│   ├── main.py                      # Entry point Streamlit + routing ekranów
│   ├── config.py                    # AppConfig (Pydantic Settings)
│   ├── schemas.py                   # Pydantic: MedicalSurvey, SurveyResult, SurveyGroup
│   ├── state_manager.py             # Zarządzanie st.session_state
│   ├── ui_components.py             # render_login(), render_upload(), render_verification()
│   ├── ai_client.py                 # AIClient: async Ollama API + prompt builder
│   └── data_handler.py              # Groupowanie plików, cache, CSV export
├── scripts/
│   ├── setup_env.ps1               # Python venv + pip install
│   ├── setup_ollama.ps1            # Instalacja Ollamy + pull deepseek-ocr + start serwera
│   ├── run_dev.ps1                 # Start Streamlit + weryfikacja Ollamy
│   ├── deploy_tunnel.ps1           # Cloudflared tunel na localhost:8501
│   └── full_setup.ps1             # Orchestrator: wszystko od zera do tunelu
├── .streamlit/
│   └── config.toml                 # Port 8501, headless, theme
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Sekcja 1 — Środowisko i zależności

### `requirements.txt`

```
streamlit==1.59.0
pydantic==2.13.4
pydantic-settings==2.14.2
Pillow==12.3.0
httpx==0.28.1
python-multipart==0.0.32

pytest==8.3.4
pytest-asyncio==0.24.0
```

### `scripts/setup_env.ps1`

- [ ] Sprawdza `python --version >= 3.12`
- [ ] Tworzy wirtualne środowisko: `python -m venv .venv`
- [ ] Aktywuje `.venv\Scripts\Activate.ps1`
- [ ] `pip install --upgrade pip setuptools wheel`
- [ ] `pip install -r requirements.txt`
- [ ] Log do `logs/setup_env.log`
- [ ] Zwraca `$LASTEXITCODE = 0` jeśli OK

### `.gitignore`

```
.venv/
__pycache__/
*.pyc
.streamlit/secrets.toml
logs/
*.log
*.err
tunnel_url.txt
uploads/
cache_results.json
wyniki.csv
```

### `.streamlit/config.toml`

```toml
[server]
port = 8501
headless = true

[theme]
primaryColor = "#1E88E5"
backgroundColor = "#FAFAFA"
secondaryBackgroundColor = "#EEEEEE"
textColor = "#212121"
font = "sans serif"
```

---

## Sekcja 2 — Ollama

### `scripts/setup_ollama.ps1`

- [ ] Sprawdza `ollama --version`, jeśli brak:
  - Download `OllamaSetup.exe` z `https://ollama.com/download`
  - Cicha instalacja: `OllamaSetup.exe /S`
- [ ] Sprawdza czy serwer działa (`curl http://localhost:11434`):
  - Jeśli nie → startuje proces w tle: `ollama serve`
- [ ] Parametry: `-Model <nazwa>` (domyślnie `deepseek-ocr`), `-SkipPull`, `-ListModels`, `-Status`
- [ ] Wsparcie dla `$env:OLLAMA_MODEL` (nadpisuje `-Model`)
- [ ] Pull modelu: `ollama pull <model>`
- [ ] Weryfikacja: `ollama list` zawiera `<model>`
- [ ] Test API: `curl -X POST http://localhost:11434/api/generate -d "{\"model\":\"<model>\",\"prompt\":\"test\"}"`
- [ ] Log do `logs/setup_ollama.log`

---

## Sekcja 3 — Aplikacja (moduły)

### `src/config.py` — Konfiguracja

- Klasa `AppConfig(BaseSettings)` z polami:
  - `app_password: str = "a"`
  - `ollama_url: str = "http://localhost:11434"`
  - `model_name: str = "deepseek-ocr"`
  - `results_csv: str = "wyniki.csv"`
  - `cache_file: str = "logs/cache_results.json"`
  - `max_retries: int = 3`
  - `timeout_sec: int = 120`
  - `model_config = {"env_prefix": "ANKIETER_"}` — wsparcie dla zmiennych środowiskowych
- Singleton `config = AppConfig()`

### `src/schemas.py` — Modele danych

`MedicalSurvey(BaseModel)` zawiera **67 pól** odwzorowujących rzeczywistą ankietę (plik `wyniki ankiety.csv`), podzielonych na sekcje:

| Sekcja             | Pola | Opis                                                                                                                                                                    |
| ------------------ | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A. Demografia**  | 7    | `plec` (Kobieta/Mężczyzna), `wiek` (int 18-80), `miejsce_zamieszkania` (4 opcje), `stan_cywilny` (3), `forma_zamieszkania` (5), `stopien_studiow` (2), `uczelnia` (str) |
| **B. Praca**       | 4    | `praca_status` (3 opcje), `praca_system` (str), `oddzial` (5), `staz_pracy` (str)                                                                                       |
| **C. Styl życia**  | 3    | `sen_godziny` (4), `ekran_godziny` (2), `kofeina` (3)                                                                                                                   |
| **D. Objawy (21)** | 21   | `objaw_*` — skala: Nigdy/Rzadko/Czasami/Często/Prawie zawsze                                                                                                            |
| **E. Zdrowie**     | 4    | `anemia`, `problemy_tarczyca` (Tak/Nie), `jaka_tarczyca` (str), `inne_choroby` (str)                                                                                    |
| **F. Jakość snu**  | 8    | `zasypianie`, `budzenie_noc`, `budzenie_rano`, `czas_snu`, `jakosc_snu`, `samopoczucie`, `sprawnosc`, `sennosc` — każdy z 3-4 opcjami                                   |
| **G. CES-D (20)**  | 20   | `cesd_*` — skala: <1d / 1-2d / 3-4d / 5-7d                                                                                                                              |
| **H. Metadane AI** | 1    | `needs_review: dict[str, bool]` — flaga wątpliwości per-pole                                                                                                            |

- `CSV_HEADER: list[str]` — 68 nagłówków (z `Sygnatura czasowa` na pierwszej pozycji)
- `_FIELD_TO_CSV: list[tuple]` — mapowanie nazw pól → nagłówki CSV
- `to_csv_row() -> list` — generuje wiersz CSV z timestampem na początku
- `from_ai_json(data: dict) -> MedicalSurvey` — parsuje odpowiedź AI z ekstrakcją wieku
- `SurveyResult(BaseModel)`:
  - `raw_response: str`
  - `validated_data: MedicalSurvey`
  - `confidence: float`
- `SurveyGroup(BaseModel)`:
  - `id: int`
  - `files: list[Path]` (5 zdjęć)
  - `result: SurveyResult | None`

### `src/state_manager.py` — Stan sesji

- Klasa `StateManager`:
  - `init()` — inicjalizuje `st.session_state["ankieter"]` jako pusty słownik
  - `is_authenticated() -> bool`
  - `set_authenticated(password: str) -> bool`
  - `get_current_index() -> int`
  - `set_current_index(i: int)`
  - `get_surveys() -> list[SurveyGroup]`
  - `set_surveys(surveys: list[SurveyGroup])`
  - `get_current_survey() -> SurveyGroup | None`
  - `next_survey() -> bool` (False jeśli koniec)
  - `set_ai_result(survey_id: int, result: SurveyResult)`
  - `get_ai_results() -> dict[int, SurveyResult]`
  - `get_progress() -> (current, total)`
  - `clear_session()` — reset

### `src/data_handler.py` — Dane i cache

- `group_files_by_survey(files: list[UploadedFile]) -> list[SurveyGroup]`:
  - Sortowanie alfabetyczne po nazwach plików
  - Grupowanie po 5 plików (5 stron = 1 ankieta)
  - Zwraca listę `SurveyGroup`
- `save_survey_to_csv(data: MedicalSurvey, path: str)`:
  - Nagłówek CSV z nazw pól `MedicalSurvey`
  - Append wiersza (tryb `"a"`, encoding UTF-8 BOM dla Excela)
  - (Streamlit działa synchronicznie, lock nie jest wymagany)
- `save_cache(results: dict[int, SurveyResult])`:
  - Zapis do `config.cache_file` jako JSON (z `model_dump()`)
- `load_cache() -> dict[int, SurveyResult]`:
  - Odczyt z `config.cache_file`, deserializacja
  - Zwraca pusty dict jeśli plik nie istnieje
- `export_csv_path() -> str`:
  - Zwraca `config.results_csv`

### `src/ai_client.py` — Komunikacja z Ollamą

- Klasa `AIClient`:
  - `__init__(model_name: str = config.model_name, base_url: str = config.ollama_url)`
  - `build_prompt() -> list[dict]` — generuje wiadomości dla `/api/chat`:
    - System: "Jesteś asystentem odczytującym dane z medycznych ankiet papierowych. Zwróć JSON..."
    - User: lista obrazów (base64) + instrukcja JSON
  - `async analyze_survey(survey: SurveyGroup) -> SurveyResult`:
    - Konwersja 5 obrazów do base64
    - POST do `/api/chat` z `model: <config.model_name>, messages: [...], format: "json", stream: false, options: {num_ctx: 8192}`
    - Timeout: 120s
    - Parsowanie odpowiedzi, mapowanie do `MedicalSurvey`
    - Dla pól z niską pewnością → `needs_review=true`
    - Retry 3x jeśli JSON niepoprawny lub nie przechodzi walidacji Pydantic
  - `async analyze_batch(surveys: list[SurveyGroup], progress_callback) -> list[SurveyResult]`:
    - Przetwarza batch sekwencyjnie lub z ograniczonym `asyncio.Semaphore(2)`
    - Wywołuje `progress_callback(completed, total)` po każdej ankiecie
    - Zapisuje do cache po każdej udanej analizie

### `src/ui_components.py` — Komponenty interfejsu

- `render_login()`:
  - `st.title("AnkieterAI")`
  - `st.text_input("Hasło", type="password")`
  - `st.button("Zaloguj")`
- `render_upload()`:
  - `st.file_uploader("Wybierz zdjęcia (jpg/png/webp)", accept_multiple_files=True, type=["jpg","png","webp"])`
  - `st.button("Rozpocznij analizę")`
  - `st.progress()` — pasek postępu podczas batcha AI
  - `st.info("Przetworzono X/Y...")` — aktualizowany w trakcie
- `render_verification(survey: SurveyGroup)`:
  - `st.progress(current, total)` — u góry strony
  - Dwie kolumny (`st.columns(2)`):
    - **Lewa**: `render_image_viewer(survey.files)`
      - 5 zakładek (`st.tabs(["Strona 1", ..., "Strona 5"])`)
      - Każda zakładka: `st.image()` z zoomem
      - Suwak zoom: `st.slider("Powiększenie", 1.0, 5.0, 1.0)` + CSS `transform: scale(zoom)` na obrazie
    - **Prawa**: `render_form(survey)`
      - 5 zakładek (`st.tabs(["Strona 1", ..., "Strona 5"])`) z polami podzielonymi per strona:
        - **Strona 1**: Demografia (A), Aktywność zawodowa (B), Styl życia (C)
        - **Strona 2**: CES-D (20 pytań)
        - **Strona 3**: Ateńska skala bezsenności (8 pól)
        - **Strona 4**: MFIS 1-15
        - **Strona 5**: MFIS 16-21 + Stan zdrowia (E)
      - Pola renderowane ręcznie (`st.selectbox`, `st.number_input`, `st.text_input`)
      - Pola z `needs_review=True` otoczone `st.error()` (czerwona ramka)
      - `st.form_submit_button("Zatwierdź i Następna (Spacja)")`
  - Obsługa skrótu Spacja przez JS:
    ```html
    <script>
      document.addEventListener("keydown", function (e) {
        if (e.key === " " && e.target === document.body) {
          e.preventDefault();
          document
            .querySelector('button[data-testid="baseButton-primary"]')
            ?.click();
        }
      });
    </script>
    ```
- `render_complete()`:
  - `st.balloons()`
  - `st.success("Wszystkie ankiety przetworzone!")`
  - `st.download_button("Pobierz CSV", data=csv_content, file_name="wyniki.csv")`

### `src/main.py` — Główna aplikacja Streamlit

- Konfiguracja strony: `st.set_page_config(layout="wide")`
- Routing:

  ```python
  if "state_manager" not in st.session_state:
      StateManager.init()

  sm = StateManager()

  if not sm.is_authenticated():
      render_login()
      st.stop()

  surveys = sm.get_surveys()
  if not surveys:
      render_upload()
      st.stop()

  current_index = sm.get_current_index()
  if current_index >= len(surveys):
      render_complete()
      st.stop()

  survey = surveys[current_index]
  render_verification(survey)
  ```

- Obsługa callbacków:
  - Upload → `data_handler.group_files_by_survey()` → `asyncio.run(ai_client.analyze_batch())` → cache
  - Zatwierdź → `data_handler.save_survey_to_csv()` → `sm.next_survey()` → `st.rerun()`

---

## Sekcja 4 — Deployment

### `scripts/run_dev.ps1`

- [ ] Parametr: `-Force` (nadpisuje istniejący `.venv`)
- [ ] Sprawdza czy Ollama działa na porcie 11434 (jeśli nie → exit z błędem)
- [ ] Sprawdza czy `.venv` istnieje (jeśli nie → `setup_env.ps1`)
- [ ] Aktywuje venv: `.venv\Scripts\Activate.ps1`
- [ ] `streamlit run src/main.py --server.port 8501`
- [ ] Czeka na proces (Streamlit uruchomiony w foreground)

### `scripts/deploy_tunnel.ps1`

- [ ] Parametr: `-Stop` (zatrzymuje aktywny tunel i czyści plik URL)
- [ ] Sprawdza `cloudflared --version`, jeśli brak:
  - Download `cloudflared-windows-amd64.exe` z `https://github.com/cloudflare/cloudflared/releases/latest`
  - Zapis do `C:\tools\cloudflared.exe`
  - Dodanie `C:\tools` do PATH (na stałe lub na sesję)
- [ ] Sprawdza czy `localhost:8501` odpowiada (Streamlit uruchomiony)
- [ ] Uruchamia: `cloudflared tunnel --url http://localhost:8501`
- [ ] Wyświetla URL (np. `https://xxxxx.trycloudflare.com`)
- [ ] Zapisuje URL do `logs/tunnel_url.txt`

### `scripts/full_setup.ps1` — Orchestrator

- [ ] Parametry: `-NoOllama`, `-NoTunnel`, `-NoEnv`, `-NoDev` (flagi do pomijania)
- [ ] Kolejność:
  1. `setup_env.ps1` (chyba że `-NoEnv`)
  2. `setup_ollama.ps1` (chyba że `-NoOllama`)
  3. `run_dev.ps1` (Start-Process w tle, chyba że `-NoDev`)
  4. `deploy_tunnel.ps1` (chyba że `-NoTunnel`)
- [ ] Cleanup: trap na Ctrl+C → Stop-Process Ollama/Streamlit/cloudflared
- [ ] Wypisuje podsumowanie:
  ```
  === AnkieterAI — Gotowe! ===
  Aplikacja lokalna:  http://localhost:8501
  Tunel publiczny:    https://xxxxx.trycloudflare.com
  Hasło:              a
  Model:              $modelName (deepseek-ocr lub z $env:OLLAMA_MODEL)
  ==============================
  ```

---

## Sekcja 5 — Testy

### `tests/` — 6 plików testowych

- `conftest.py` — Fixture `sample_survey_data`, `sample_survey`, `ai_json_response` + autouse reset `st.session_state`
- `test_schemas.py` — Testy `_extract_age`, `_normalize_value`, `MedicalSurvey.from_ai_json()`, `to_csv_row()`, `SurveyResult`, `SurveyGroup`
- `test_data_handler.py` — Testy grupowania plików, zapisu CSV z BOM, cache roundtrip
- `test_state_manager.py` — Testy logowania, indeksowania, next/clear
- `test_ai_client.py` — Testy `_image_to_base64()`, `_merge_partial_results()`
- `test_csv_integrity.py` — Testy spójności: 68 kolumn, wszystkie nagłówki unikalne, mapowanie 1:1

Uruchomienie:

```powershell
.venv\Scripts\Activate.ps1
pytest tests/
```

---

## Sekcja 6 — Harmonogram implementacji (fazy)

| Faza | Opis                                                  | Pliki                                                                        | Status |
| ---- | ----------------------------------------------------- | ---------------------------------------------------------------------------- | ------ |
| 0    | Środowisko: requirements.txt, .gitignore, config.toml | `requirements.txt`, `.gitignore`, `.streamlit/config.toml`                   |        |
| 1    | Skrypt środowiska                                     | `scripts/setup_env.ps1`                                                      |        |
| 2    | Skrypt Ollama                                         | `scripts/setup_ollama.ps1`                                                   |        |
| 3    | Fundament aplikacji                                   | `src/config.py`, `src/state_manager.py`, `src/main.py` (szkielet + login)    |        |
| 4    | Schemat i obsługa danych                              | `src/schemas.py`, `src/data_handler.py`                                      |        |
| 5    | AI Client                                             | `src/ai_client.py`                                                           |        |
| 6    | UI Components                                         | `src/ui_components.py`                                                       |        |
| 7    | Spięcie logiki w main.py                              | `src/main.py` (pełna logika + routing)                                       |        |
| 8    | Deployment scripts                                    | `scripts/run_dev.ps1`, `scripts/deploy_tunnel.ps1`, `scripts/full_setup.ps1` |        |
| 9    | Testy i walidacja całego flow                         | Wszystkie moduły                                                             |        |

---

## Uwagi techniczne

1. **Streamlit + asyncio:** Streamlit działa na pętli synchronicznej. Do wywołania `analyze_batch()` używamy `asyncio.run()`. Do update'u progress bara w trakcie batcha — zapis do `st.session_state` w osobnym wątku lub callback.
2. **Obrazy base64:** `PIL.Image` → `BytesIO` → base64. Maksymalny rozmiar payloadu: 5 obrazów × ~1-2MB = bezpieczne dla Ollamy.
3. **Format JSON w Ollamie:** Używamy parametru `format: "json"` w `/api/chat` (wspierany od Ollama 0.12+), co wymusza odpowiedź w czystym JSON.
4. **CSV z polskimi znakami:** Zapis z `encoding="utf-8-sig"` (BOM) dla poprawnego otwierania w Excelu.
5. **Cloudflared na Windows:** Pobieramy plik wykonywalny, nie wymaga instalacji. Uruchamiamy jako podproces.
