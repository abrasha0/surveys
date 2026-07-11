Jesteś zaawansowanym inżynierem oprogramowania odpowiedzialnym za projekt AnkieterAI. Aplikacja została zmigrowana do modularnej architektury (punkt wejścia to `src/app.py`). Mając do dyspozycji pełen kontekst plików z katalogu dokumentacji, zrealizuj poniższy plan krok po kroku. Po każdym etapie zatrzymaj się, przedstaw raport z wykonanych zmian i poczekaj na moją akceptację oraz wyniki testów, zanim przejdziesz do kolejnego.

### ETAP 1: Stabilizacja, Bugfixing i Issue Tracking (Ref. `current-state-report.md`, `known-issues.md`)

- **Zadanie 1.1 - Rozwiązanie Issue #11 (Krytyczne):** Według pliku `known-issues.md` oraz raportu `current-state-report.md`, UI rozjeżdża się przy interakcji z formularzem.[cite: 1, 3] W pliku odpowiedzialnym za weryfikację UI otocz sekcję renderującą prawy formularz dekoratorem `@st.fragment`, co zapobiegnie przeładowywaniu całej strony i utrzyma zakładki na swoim miejscu.[cite: 4]
- **Zadanie 1.2 - Naprawa Testów:** Zaktualizuj 2 failujące testy w pliku `tests/test_schemas.py` wskazane w dokumencie `current-state-report.md` (`test_no_number_fallback`, `test_literal_fallback_to_first`).[cite: 1] Dopasuj asercje do nowej logiki, która przy nieznanych wartościach zwraca `None`.[cite: 1]
- **Zadanie 1.3 - Naprawa Skryptów Deploymentowych:** W skrypcie `scripts/deploy_tunnel.ps1` (błędy wypisane w `current-state-report.md`) popraw niezdefiniowaną zmienną `$cfPath` na `$CloudflaredPath` oraz poprawnie zainicjalizuj zmienną `$TunnelUrlFile`.[cite: 1] Dodatkowo w pliku `scripts/full_setup.ps1` (jak zaznaczono w `repository-structure-report.md`) zmień zahardkodowane hasło "ankieter2026" na docelowe "a", aby projekt był zgodny z konfiguracją.[cite: 6]
- **Zadanie 1.4 - Monitorowanie (Issue #9):** Zgodnie z wytycznymi z pliku `known-issues.md`, zaktualizuj plik `README.md`, dodając do niego sekcję lub tabelę do śledzenia issues.[cite: 3] Odznacz Issue #11 jako rozwiązane po zastosowaniu dekoratora fragmentów.

### ETAP 2: Optymalizacja AI - Quick Wins (Ref. `optimalization-plan.md`)

- **Zadanie 2.1 - Przetwarzanie obrazu:** Na podstawie założeń z pliku `optimalization-plan.md`, zaimplementuj w kodzie funkcję korzystającą z biblioteki Pillow.[cite: 5] Funkcja musi przeskalować każde zdjęcie zachowując proporcje (maksymalnie 1500-2000 px na dłuższym boku), zmienić jego kolorystykę na grayscale, podbić kontrast i zapisać wynik do zoptymalizowanego bufora `io.BytesIO`.[cite: 5]
- **Zadanie 2.2 - Konfiguracja Ollama:** Zgodnie ze wskazówkami w dokumencie `optimalization-plan.md`, wymuś w kodzie klienta dla zapytań API obiekt `options` z parametrami: `temperature: 0.0` oraz `num_ctx: 8192`.[cite: 5] Dodaj również do requestów parametr `keep_alive: "-1"`, aby zablokować usuwanie modelu z pamięci VRAM po wywołaniu.[cite: 5]
- **Zadanie 2.3 - Prompty:** Przestrzegaj kategorycznej restrykcji z pliku `optimalization-plan.md` – obowiązuje absolutny zakaz hardcodowania i modyfikowania treści promptów bezpośrednio w kodzie.[cite: 5] Zawsze korzystaj z zewnętrznej struktury dostarczającej prompty.

### ETAP 3: Przebudowa Architektury AI na Producer-Consumer (Ref. `optimalization-plan.md`)

- **Zadanie 3.1 - Rozbicie modelu na 2 kroki:** Wdrażając nową architekturę z pliku `optimalization-plan.md`, podziel inferencję na dwa izolowane kroki.[cite: 5] Krok A to ekstrakcja surowego tekstu z obrazów za pomocą VLM, a Krok B to formatowanie tych wyników przez mniejszy Text LLM z wykorzystaniem parametru `format="json"`.[cite: 5]
- **Zadanie 3.2 - Asynchroniczna orkiestracja:** Wykorzystaj klasę `asyncio.Queue` do budowy workera typu Producer (pobieranie obrazów, strzały do VLM) oraz workera typu Consumer (nasłuchiwanie na tekst, strzały do Text LLM), dokładnie tak, jak zalecono w dokumencie `optimalization-plan.md`.[cite: 5]
- **Zadanie 3.3 - Zarządzanie VRAM:** Jak zdefiniowano na końcu pliku `optimalization-plan.md`, dodaj obsługę flagi środowiskowej `USE_SEQUENTIAL_BATCHING_FALLBACK`.[cite: 5] Flaga ta ma umożliwić spadek (fallback) do przetwarzania całkowicie sekwencyjnego na wypadek braku pamięci GPU na równoległe działanie modelu wizyjnego i tekstowego.[cite: 5]

### ETAP 4: Observability i Zamknięcie Otwartych Issues (Ref. `optimalization-plan.md`, `known-issues.md`)

- **Zadanie 4.1 - LangSmith:** Zgodnie z sekcją o tracingu w pliku `optimalization-plan.md`, zaimplementuj obsługę zmiennych `LANGCHAIN_*`.[cite: 5] Wymuś takie tagowanie śladów w kodzie (traces), aby w dashboardzie można było łatwo oddzielić czas I/O plików graficznych od czasu odpowiedzi Time to First Token modeli VLM i LLM.[cite: 5]
- **Zadanie 4.2 - Zamknięcie Issue #10:** Zaimplementuj logikę resetującą stan progress bara po kliknięciu "Rozpocznij analizę", co zostało opisane jako problem w dokumencie `known-issues.md`.[cite: 3]
- **Zadanie 4.3 - Zamknięcie Issue #8:** Złap błędy `JSONDecodeError` w logice API i zadbaj o logowanie/wyświetlanie surowego stringa tekstowego, który był przyczyną awarii formatowania, jak zgłoszono w dokumencie `known-issues.md`.[cite: 3]
- **Zadanie 4.4 - Zamknięcie Issue #3.1:** Zgodnie z wytycznymi z pliku `known-issues.md`, rozszerz logger o zrzucanie do zewnętrznego pliku logów dokładnego kontekstu request/response z adekwatnymi timestampami per-call.[cite: 3]
