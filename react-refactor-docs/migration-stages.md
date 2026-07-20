# Plan Migracji: AnkieterAI (Streamlit → FastAPI + React)

Dokument roboczy do wykorzystania z agentami (analogicznie do wzorca `AGENTS.md` +
komenda przeglądu, znanego z projektu budget-tracker). Każdy etap poniżej to
osobna sesja agenta: ma jasny cel, zależności od poprzednich etapów, zakres
i kryteria akceptacji.

**v2 — zaktualizowano po ustaleniu:** przetwarzania jako jednego globalnego workera
w tle (nie per-ankieta na żądanie), interleaved weryfikacji, uproszczonego auth,
zasad retry/skip przy błędach OCR, oraz rezygnacji z testów jako osobnego etapu.

---

## Etap 0 — Domknięcie decyzji architektonicznych

**Cel:** rozstrzygnąć pytania nieobecne w `base-guidelines-sketch.md`, zanim
jakikolwiek agent zacznie pisać kod.

| # | Pytanie | Decyzja |
|---|---------|---------|
| 1 | Jak wygląda auth? | Hasło hardkodowane/z configu, prosty ekran logowania blokujący całą appkę. Bez rozbudowanego systemu sesji — jeden współdzielony token/cookie ważny przez czas trwania sesji (góra kilka godzin). Zero priorytetu na bezpieczeństwo poza "nie wchodzisz bez hasła". |
| 2 | Model przetwarzania batcha? | **Jeden globalny worker w tle**, nie trigger per-ankieta. `POST /api/processing/start` uruchamia przetwarzanie całej kolejki nieprzetworzonych ankiet sekwencyjnie (strona po stronie, jeden model w VRAM naraz — zgodnie z obecnym ograniczeniem). Worker działa niezależnie od tego, co robi użytkownik w UI. |
| 3 | Jak frontend widzi postęp? | Polling `GET /api/processing/status` (globalny: która ankieta/strona/etap modelu + ETA) + `GET /api/surveys` (status per ankieta: queued/processing/ready/error/verified). Polling, nie WebSocket/SSE — mniej podatne na zrywanie przez Cloudflare tunnel. |
| 4 | Skąd frontend bierze obrazy stron? | `GET /api/surveys/{id}/pages/{n}/image` |
| 5 | Weryfikacja: sekwencyjnie po całym batchu czy na bieżąco? | **Na bieżąco** — skoro worker jest jeden globalny i śledzi status per ankieta, ankieta ze statusem `ready` jest od razu dostępna do weryfikacji, niezależnie od tego, że worker dalej procesuje kolejne. To naturalna konsekwencja decyzji #2, więc jest "łatwe" — patrz Etap 3. |
| 6 | Co się dzieje przy błędzie VLM/LLM? | Retry całej ankiety do 3 razy (na poziomie orkiestracji, ponad istniejącym retry z backoffem w `ai/client.py` na poziomie pojedynczego wywołania — do skonsolidowania, żeby nie było podwójnego retry-stormu). Po 3 nieudanych próbach: status `error`, worker leci dalej, ankieta zostaje oznaczona jako nieprzeprocesowana. |
| 7 | Co ze `schemas.py`? | Zostaje strukturalnie, usuwamy tylko pole `needs_review`. |
| 8 | Co z formatem ankiety i CSV? | Oba już ustalone i udokumentowane po Twojej stronie — do przekazania agentowi w momencie implementacji Etapu 4 (nie trzeba ich ustalać teraz). |
| 9 | Co z issue #7 (próg re-OCR)? | Jawnie odłożone poza zakres migracji. |
| 10 | Co z `ai/tracing.py` (LangSmith)? | Zostaje bez zmian, opcjonalny no-op jak dotąd. |
| 11 | Testy automatyczne? | **Poza zakresem migracji.** Nie ma osobnego etapu testowego; jeśli coś powstanie przy okazji (np. agent doda test smoke), to bonus, nie wymóg. |

**Kryteria akceptacji:** masz zaakceptowaną (lub zmienioną) tabelę powyżej.

---

## Etap 1 — Szkielet backendu FastAPI

**Zależności:** Etap 0.

**Zakres:**
- Nowy punkt wejścia (`main.py`), router API pod `/api`
- `StaticFiles` serwujące zbudowany frontend (`/dist`) na `/` — na razie placeholder
- Prosty auth: `POST /api/auth/login` (hasło z `config.yaml`) ustawia cookie/token;
  dependency FastAPI blokująca resztę `/api/*` bez ważnego tokena. Bez wygasania,
  refresh tokenów itd. — to nie jest system security-krytyczny.
- Przeniesienie `config.py` bez zmian logiki (YAML + `ANKIETER_*` env override)
- `logger.py` bez zmian

**Kryteria akceptacji:** `uvicorn main:app` startuje, `GET /api/health` odpowiada
200, endpoint chroniony bez tokena zwraca 401, z tokenem po loginie — 200.

---

## Etap 2 — Port warstwy domain

**Zależności:** Etap 1.

**Zakres:**
- `domain/field_specs.py` bez zmian (63 pola, fundament)
- `domain/schemas.py` bez `needs_review`
- `domain/csv_export.py` bez zmian logiki (finalna walidacja formatu — Etap 4,
  gdy dostarczysz referencję)
- Adaptacja `ai/client.py`/`ai/prompts.py` do wywołania z async workera FastAPI
  zamiast Streamlit rerun-loop; preprocessing obrazów (resize, kontrast — Pillow)
  zostaje bez zmian koncepcyjnych, tylko zmienia się miejsce wywołania

**Kryteria akceptacji:** moduły importują się bez zależności od `streamlit`.

---

## Etap 3 — Globalny worker przetwarzania + status/ETA (kluczowy etap)

**Zależności:** Etap 2, decyzje #2, #3, #5, #6 z Etapu 0.

To jest etap, który najbardziej różni się od pierwszej wersji szkicu — przez
decyzję o jednym globalnym workerze zamiast triggera per-ankieta.

**Model działania:**
- `ingestion/file_grouping.py` skanuje katalog obok appki (pakiet zdjęć wgrany
  wcześniej), grupuje po 5 stron, buduje kolejkę
- `POST /api/processing/start` — uruchamia w tle (jeden `asyncio.Task`/worker,
  **nie** `BackgroundTasks` per-request, bo musi przetrwać między requestami)
  sekwencyjne przetwarzanie **całej kolejki**: ankieta po ankiecie, strona po
  stronie, jeden model w VRAM naraz. Endpoint zwraca natychmiast.
- Worker po każdej stronie aktualizuje stan współdzielony (in-memory + zapis do
  cache JSON co ankietę — issue #6, resume po restarcie)
- Retry na poziomie ankiety: do 3 prób całej ankiety przy błędzie, potem
  `status: error` i dalej w kolejce (decyzja #6)

**Endpointy statusu:**
- `GET /api/processing/status` — stan globalny: `total`, `processed`,
  `errors`, `current_survey_id`, `current_page`, `current_stage`
  (`vlm` / `format`), `eta_seconds` (liczone z rolling average czasu/stronę
  w bieżącej sesji × liczba pozostałych stron)
- `GET /api/surveys` — lista ze statusem per ankieta:
  `queued | processing | ready | error | verified`
- `GET /api/surveys/{id}/pages/{n}/image`
- `GET /api/surveys/{id}/result` — dostępne, gdy status = `ready` (albo `error`,
  do ręcznego podejrzenia co poszło nie tak)

**Interleaved weryfikacja (decyzja #5):** ponieważ status jest per-ankieta i
niezależny od globalnego postępu workera, frontend może otworzyć do weryfikacji
dowolną ankietę ze statusem `ready`, podczas gdy worker dalej procesuje kolejne —
nie wymaga to żadnej dodatkowej synchronizacji poza już istniejącym pollingiem
`GET /api/surveys`.

**Kryteria akceptacji:** `start` uruchamia przetwarzanie całej kolejki, polling
`processing/status` pokazuje narastający postęp z sensownym ETA, ankieta, która
skończyła się wcześniej, jest dostępna do weryfikacji zanim worker skończy resztę
kolejki, restart serwera w trakcie nie gubi już przetworzonych ankiet.

---

## Etap 4 — Endpoint zapisu + zgodność formatu CSV

**Zależności:** Etap 2, Etap 3.

**Zakres:**
- `POST /api/surveys/{id}/save` — walidacja przez `MedicalSurvey(**values)`,
  zapis wiersza do CSV zgodnie z ustalonym już formatem (dostarczasz go na
  wejściu tego etapu), status ankiety → `verified`
- Zachowanie "zatwierdź mimo błędów walidacji" z obecnej appki — do potwierdzenia
  przy tym etapie, czy nadal potrzebne
- Weryfikacja zgodności `csv_export.py` z docelowym formatem kolumna-po-kolumnie

**Kryteria akceptacji:** zapisany wiersz CSV zgadza się z docelowym formatem.

---

## Etap 5 — Szkielet frontendu (Vite + React + Tailwind)

**Zależności:** Etap 1.

**Zakres:**
- Inicjalizacja Vite w katalogu frontendu (np. `src_ui`)
- Layout SPA: `100vh`, brak scrolla okna, podział 40/60 (obraz/formularz)
- Proxy dev `/api` → `localhost:8000`
- Klient API z obsługą tokena z Etapu 1
- Ekran logowania

**Kryteria akceptacji:** `npm run dev` + `uvicorn --reload` razem działają,
logowanie działa end-to-end.

---

## Etap 6 — Moduł przeglądarki zdjęć

**Zależności:** Etap 3 (endpoint obrazów), Etap 5.

**Zakres:**
- Panel lewy: `object-contain`, bez scrolla, auto-skalowanie do wysokości
- 5 zakładek do przełączania stron
- Opcjonalnie `react-zoom-pan-pinch`

**Kryteria akceptacji:** zdjęcie zawsze w całości widoczne, zakładki płynne.

---

## Etap 7 — Moduł formularza dynamicznego

**Zależności:** Etap 2 (field specs dostępne przez API), Etap 5.

**Zakres:**
- Generowanie formularza z definicji pól (63 pola, 5 stron)
- Kontener `overflow-y: auto`, niezależny od panelu obrazu
- Usunięcie wyróżniania `needs_review`
- Spacja = zatwierdź i przejdź dalej (do kolejnej ankiety o statusie `ready`,
  niekoniecznie kolejnej w kolejce przetwarzania — patrz Etap 3)

**Kryteria akceptacji:** formularz renderuje 63 pola z poprawną walidacją,
Spacja zatwierdza i ładuje kolejną gotową ankietę.

---

## Etap 8 — Topbar/nawigacja + integracja postępu i ETA

**Zależności:** Etapy 3, 6, 7.

**Zakres:**
- Przyciski nawigacyjne w jednym rzędzie ze wskaźnikiem "Ankieta X z Y"
- Jasne etykiety: "Poprzednia ankieta", "Następna ankieta", "Zatwierdź ankietę"
- Pasek postępu batcha podpięty do `GET /api/processing/status`: liczba
  zakolejkowanych/przetworzonych/błędnych ankiet, aktualny etap modelu
  (VLM/formatter), ETA
- Wizualne rozróżnienie ankiet `ready` (dostępnych do weryfikacji od ręki, nawet
  gdy worker dalej pracuje w tle) od `queued`/`processing`/`error`

**Kryteria akceptacji:** widać łączny postęp całego batcha z ETA, użytkownik
może zacząć weryfikować pierwszą gotową ankietę, zanim reszta się doprocesuje.

---

## Etap 9 — Pipeline deploymentu (PowerShell)

**Zależności:** Etapy 1, 5, wszystkie endpointy gotowe.

**Zakres:**
- `setup_env.ps1` — dodanie `npm install` w katalogu frontendu
- `run_dev.ps1` — równoległe `uvicorn --reload` i `npm run dev`
- `full_setup.ps1`/`deploy.ps1` — Ollama → `npm run build` → przeniesienie
  `dist` → `uvicorn` na porcie 8000 → tunnel Cloudflare

**Kryteria akceptacji:** `full_setup.ps1` na czystym środowisku Windows kończy
się działającą aplikacją dostępną przez tunnel na jednym porcie.

---

## Etap 10 — Cutover i sprzątanie

**Zależności:** wszystkie powyższe, zweryfikowane na realnych ankietach.

**Zakres:**
- Usunięcie `src/ui/`, `src/state/state_manager.py`, starego `app.py`
- Aktualizacja `main-doc.md`/`architecture-report.md` pod nowy stack (w tym
  nowy model przetwarzania — jeden globalny worker zamiast per-ankieta)
- Przegląd `known-issues.md`: zamknięcie #3, #4, #5, #6, #8, #9; notatka o
  odłożeniu #7 poza zakres migracji
- Test end-to-end na pełnym zestawie ~150 ankiet (albo próbce)

**Kryteria akceptacji:** stary kod Streamlit usunięty, dokumentacja spójna
z nowym stackiem, `known-issues.md` odzwierciedla realny stan po migracji.
