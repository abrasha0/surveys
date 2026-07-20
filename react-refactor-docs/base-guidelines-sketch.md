# Wytyczne Migracji Architektury: AnkieterAI (Streamlit -> FastAPI + React)

## Cel Dokumentu

Przejście z aplikacji opartej na frameworku Streamlit na architekturę rozdzieloną: backend w FastAPI (Python) oraz frontend w React/Vite (JavaScript/TypeScript). Całość serwowana na jednym porcie dla uproszczenia wdrożenia przez Cloudflare Tunnel.

---

## 1. Refaktoryzacja Backendu (Python / FastAPI)

### Do zachowania (Core logiki biznesowej):

- Moduł `src/domain/` pozostaje bez zmian[cite: 2]. Obejmuje to plik `field_specs.py` z definicjami 63 pól na 5 stronach[cite: 1, 2].
- Pydantic models (m.in. `MedicalSurvey`) w pliku `schemas.py` służące do walidacji pozostają niezmienione[cite: 1, 2].
- Moduł `csv_export.py` odpowiadający za eksport do formatu CSV pozostaje bez zmian[cite: 1, 2].
- Moduł `src/ai/client.py` z asynchronicznym klientem `httpx` komunikującym się z serwerem Ollama (VLM deepseek-ocr i Text LLM llama3.1) pozostaje zachowany[cite: 2, 4].
- Konfiguracja z pliku `config.yaml` oraz system promptów zdefiniowany w sekcji `prompts` zostają zachowane[cite: 2, 4].

### Do całkowitego usunięcia:

- Cały katalog `src/ui/` (pliki `pages/`, `widgets.py`, `styles.py`, `shortcuts.py`) zostaje usunięty[cite: 2].
- Moduł zarządzania stanem Streamlita `src/state/state_manager.py` zostaje usunięty[cite: 2].
- Plik wejściowy `app.py` pełniący rolę routera Streamlit zostaje usunięty i zastąpiony nowym punktem wejścia FastAPI[cite: 2].

### Nowa implementacja (Zadania dla agenta API):

- **Stworzenie instancji FastAPI:** Aplikacja ma posiadać router API pod prefiksem `/api`.
- **Wystawianie plików statycznych:** Skonfigurować `StaticFiles` w FastAPI do serwowania zbudowanego folderu aplikacji React (np. `/dist`) na ścieżce głównej `/`.
- **Zarządzanie ankietami:** Wdrożenie procesowania bezpośrednio z lokalnego katalogu[cite: 3]. Endpoint `/api/surveys` ma skanować katalog ze zdjęciami i grupować je po 5 stron w jedną ankietę[cite: 4].
- **Cachowanie:** Endpoint API ma zapisywać i wznawiać przetworzone wyniki z lokalnych plików (np. JSON), eliminując konieczność ponownego procesowania tych samych zdjęć[cite: 3, 4].
- **Model danych:** Całkowite usunięcie mechanizmów powiązanych z polem `needs_review` z backendu oraz modeli Pydantic[cite: 3].
- **Endpointy API do wdrożenia:**
  - `GET /api/surveys` - lista dostępnych ankiet zgrupowanych po 5 zdjęć.
  - `POST /api/surveys/{id}/process` - trigger wywołujący sekwencyjne przetwarzanie AI (VLM -> LLM) dla 5 stron[cite: 4].
  - `GET /api/surveys/{id}/result` - pobieranie wygenerowanego JSON.
  - `POST /api/surveys/{id}/save` - endpoint walidujący dane przez model Pydantic i zapisujący wynik do pliku `wyniki.csv`[cite: 4].

---

## 2. Założenia UI / UX (Frontend - React/Tailwind)

Frontend przejmuje całkowicie odpowiedzialność za interfejs "Human-in-the-loop", korzystając ze standardów webowych.

### Layout (Single Page Application):

- Brak przeładowywania i brak przewijania okna (wysokość sztywno ustawiona na `100vh`).
- Podział interfejsu na układ 40/60 (40% widok zdjęcia, 60% formularz boczny)[cite: 3].

### Moduł Przeglądarki Zdjęć (Lewy panel):

- Zdjęcie ankiety musi automatycznie skalować się do wysokości ekranu (CSS: `object-contain`, brak scrolla na zdjęciu)[cite: 3].
- Panel posiada 5 zakładek (Tabs) do szybkiego przełączania się między 5 stronami ankiety[cite: 4].
- Opcjonalnie: integracja biblioteki typu `react-zoom-pan-pinch` do bezproblemowego przybliżania szczegółów obrazu.

### Moduł Formularza (Prawy panel):

- Kontener z ustawionym `overflow-y: auto`, co pozwala na niezależne przewijanie formularza posiadającego 63 pola zdefiniowane w ankiecie medycznej[cite: 1, 4].
- Formularz generuje się na podstawie definicji pól i mapowania ich na konkretne strony[cite: 1].
- Usunięcie jakiegokolwiek wyróżniania na czerwono pól "wątpliwych" (wycofanie logiki `needs_review`)[cite: 3, 4].
- Globalny skrót klawiszowy "Spacja" służący do szybkiego zatwierdzenia formularza i przejścia do następnej ankiety[cite: 4].

### Topbar (Pasek nawigacji / akcji):

- Wszystkie przyciski nawigacyjne mają znaleźć się na tym samym poziomie (w tym samym rzędzie) co wskaźnik postępu, np. tekst "Ankieta 1 z 1"[cite: 3].
- Etykiety przycisków muszą jasno opisywać ich cel (np. "Poprzednia ankieta", "Zatwierdź i następna")[cite: 3].

---

## 3. Pipeline Deploymentu i Skrypty PowerShell

Całość aplikacji będzie działać na systemie Windows i będzie wystawiona światu za pomocą tunelu Cloudflare[cite: 4].

### Logika "Single Port":

Aplikacja Node.js (Vite) nie będzie działać w osobnym procesie w środowisku produkcyjnym. Proces składa się z budowy assetów statycznych, które następnie przejmuje Uvicorn (FastAPI).

### Aktualizacja Skryptów `scripts/`:

1. **`setup_env.ps1`**:
   - Pozostaje budowa wirtualnego środowiska `.venv` dla Pythona[cite: 2].
   - Dodanie komendy `npm install` w nowym katalogu frontendu (np. `src_ui`).

2. **`run_dev.ps1` (Środowisko developerskie)**:
   - Skrypt ma uruchamiać równolegle (w tle):
     - API Pythona: `uvicorn main:app --reload --port 8000`
     - Serwer Vite: `npm run dev` w katalogu frontendu (z ustawionym proxy w Vite kierującym zapytania `/api` na port `8000`).

3. **`full_setup.ps1` / `deploy.ps1` (Środowisko produkcyjne)**:
   - Procesowanie sekwencyjne:
     1. Uruchomienie Ollama[cite: 4].
     2. Kompilacja interfejsu klienta: `npm run build`[cite: 4].
     3. Przeniesienie wygenerowanego katalogu `dist` do odpowiedniego folderu serwowanego przez FastAPI (np. `backend/static`).
     4. Uruchomienie backendu Pythona portem `8000`: `uvicorn main:app --port 8000`[cite: 4].
     5. Aktywacja tunelu Cloudflare przekierowującego zewnętrzny ruch na `localhost:8000`[cite: 2, 4].
