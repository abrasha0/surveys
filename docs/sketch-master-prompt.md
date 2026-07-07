# Projekt: AnkieterAI - Zautomatyzowany system wprowadzania ankiet papierowych (VLM)

## 1. Cel Projektu i Kontekst
Zbudowanie modułowej aplikacji webowej w Streamlit, służącej do odczytywania danych z medycznych ankiet papierowych (ok. 150 sztuk, każda po 5 stron) za pomocą lokalnego modelu VLM i konwertowania ich do pliku CSV. 
Użytkownikiem końcowym jest osoba nietechniczna. Rozwiązanie ma działać dla niej "magicznie" i bezkonfiguracyjnie (otwiera link i działa). Główną rolą użytkownika jest weryfikacja (Human-in-the-loop) i ewentualna, błyskawiczna korekta danych zaproponowanych przez AI, a nie ręczne przepisywanie.

## 2. Architektura i Deployment
- **Środowisko deweloperskie/hostujące:** Windows, RTX 5070 Ti, 32GB RAM (aplikacja uruchamiana u dewelopera).
- **Dostęp użytkownika:** Zapewniony przez zewnętrzny tunel (np. Cloudflare Quick Tunnels). Brak konieczności instalacji czegokolwiek u użytkownika.
- **Bezpieczeństwo:** Ze względu na wystawienie na zewnątrz, aplikacja wymaga prostego, jednostronicowego ekranu logowania (jedno zakodowane na sztywno hasło).
- **Backend AI:** Lokalna instancja `Ollama` (port 11434).
- **Baza danych:** Zapis lokalny do pliku `wyniki.csv`.

## 3. Założenia UX / UI (Krytyczne!)
- **Zero czekania (Płynny Workflow):** Gdy użytkownik klika "Zatwierdź i Następna", aplikacja natychmiast zapisuje wiersz, ładuje nową ankietę i asynchronicznie odpala AI. 
- **Side-by-Side:** Ekran roboczy podzielony na dwie połowy. Lewa to przeglądarka obrazów z wbudowanym **ZOOMEM** (możliwość powiększenia niewyraźnego pisma). Prawa to wygenerowany formularz z odpowiedziami z AI.
- **Walidacja w czasie rzeczywistym:** Jeśli AI nie jest pewne odczytu (np. bazgroły, skreślenia), pole w formularzu musi rzucać się w oczy (np. pomarańczowa ramka/ostrzeżenie). Użytkownik poprawia to jednym kliknięciem przed przejściem dalej. Brak konieczności "powrotu do błędów po 3 dniach".
- **Przyszłościowa definicja ankiety:** Pola formularza nie powinny być zaszyte chaotycznie w kodzie UI. Mają być generowane dynamicznie na podstawie schematu (np. klasy Pydantic lub pliku JSON), co w przyszłości pozwoli użytkownikowi łatwo "wyklikać" definicję nowej ankiety.

## 4. Wyzwania OCR/VLM (Specyfika Danych)
Aplikacja operuje na zdjęciach, które zawierają:
1. Standardowe pola wyboru (krzyżyki).
2. Pismo odręczne (cyfry, krótkie nazwy - np. "Uczelnia: P.A.N.S.").
3. Skale punktowe gdzie odpowiedź to zakreślona kółkiem cyfra (np. 0, 1, 2, 3).
4. Pytania, gdzie użytkownik zakreślił kółkiem całe zdanie/blok tekstu.
5. Gęste tabele z odpowiedziami (krzyżyki w siatce).

## 5. Główne Flow Użytkownika (Asynchroniczny Speed-run)
1. **Upload i Batch:** Użytkownik wgrywa folder ze zdjęciami. Klika "Rozpocznij analizę". Aplikacja przetwarza wszystkie pliki w tle za pomocą Ollamy, zapisując surowe wyniki JSON w `st.session_state` lub pliku cache. Użytkownik widzi pasek postępu (np. "Przetworzono 43/150...").
2. **Tryb Weryfikacji:** Po zakończeniu batcha aktywuje się ekran weryfikacji. 
3. **Szybki Skim (Side-by-Side):** 
   - Lewa kolumna: Podgląd 5 stron aktualnej ankiety (płynny scroll lub taby).
   - Prawa kolumna: Skondensowany, czytelny widok wszystkich wyciągniętych danych na jednym ekranie (podsumowanie).
   - Pola oznaczone przez AI jako wątpliwe (`needs_review: true`) są podświetlone na czerwono.
4. **Błyskawiczne Zatwierdzenie:** Jeśli dane są poprawne, użytkownik klika przycisk "Zatwierdź (Spacja)" – system zapisuje wiersz do docelowego CSV i *natychmiast* bez żadnego opóźnienia wyświetla dane dla kolejnej ankiety.

## 6. Struktura Katalogów i Modułów (Czysty Kod)
Projekt musi być napisany zgodnie z dobrymi praktykami. Wymagam podzielenia kodu logicznie na moduły. Proponowana struktura:
- `main.py` -> Punkt wejścia Streamlit, zarządzanie głównym routingiem i autoryzacją.
- `config.py` -> Konfiguracja aplikacji (hasło, ścieżki, URL do Ollamy).
- `schemas.py` -> Modele Pydantic definiujące strukturę ankiety (nazwy kolumn, typy danych, opcje wyboru). Baza pod generowanie formularza i promptu JSON.
- `state_manager.py` -> Logika obsługi `st.session_state` (aktualny indeks ankiety, przechowywanie wgranych plików, flagi ładowania).
- `ui_components.py` -> Wyodrębnione funkcje UI (np. `render_image_viewer()`, `render_form()`, `render_progress_bar()`).
- `ai_client.py` -> Komunikacja z API Ollamy, obsługa błędów JSON, budowanie promptu na podstawie `schemas.py`.
- `data_handler.py` -> Logika grupowania wgranych plików (np. po prefixach nazw 5 stron w jedną ankietę) oraz funkcja zapisu do `csv`.

## 7. Główne Flow Aplikacji
1. **Ekran Logowania:** Wpisanie hasła.
2. **Ekran Inicjalizacyjny (Upload):** Użytkownik wgrywa paczkę plików (np. `.zip` lub wielokrotny wybór zdjęć). `data_handler.py` sortuje je alfabetycznie i grupuje po 5 stron per student.
3. **Ekran Główny (Pętla Weryfikacji):**
   - Wczytanie grupy 5 zdjęć (ankieta nr 1).
   - Przekazanie zdjęć do `ai_client.py`. (UI w tym czasie pokazuje spinner ładujący w prawej kolumnie, lewa jest już widoczna).
   - Zwrócenie ustrukturyzowanego JSON-a, na bazie którego renderuje się formularz (prawa strona).
   - Użytkownik przegląda 5 stron (zakładki w lewej kolumnie) i poprawia błędy w prawym formularzu.
4. **Zapis i iteracja:** Kliknięcie "Zapisz i Następna" -> zapis do CSV (`data_handler.py`), inkrementacja indeksu (`state_manager.py`), przeładowanie ekranu na ankietę nr 2.

## 7. Fazy Implementacji dla Agenta
Proszę o implementację krokową. Będziemy pisać moduł po module. Pytaj mnie o testy po każdej fazie.
- **Faza 1 (Fundament):** Utworzenie `config.py`, `main.py` (ekran logowania) oraz `state_manager.py`. Zbudowanie pustego szkieletu przepływu ekranów.
- **Faza 2 (Dane i Schemat):** Stworzenie `schemas.py` z przykładowym schematem (wiek, płeć, skala 1-5). Napisanie `data_handler.py` obsługującego upload wielu plików i grupowanie ich w obiekty "Ankieta" (po 5 sztuk).
- **Faza 3 (Logika Batcha i Cache, uzupełnienie data_handler):** Napisanie `data_handler.py` pod kątem asynchronicznego procesowania całej kolejki zdjęć przed uruchomieniem ekranu weryfikacji. Zapisywanie wyników cząstkowych do tymczasowego cache, aby zapobiec utracie danych przy przypadkowym odświeżeniu strony.
- **Faza 4.1 (Interfejs Użytkownika):** Implementacja `ui_components.py`. Skup się na lewej kolumnie: widok obrazu z obsługą przybliżania (zoom) oraz zakładkami na 5 stron. Prawa kolumna to dynamiczny formularz generowany na bazie `schemas.py`.
- **Faza 4.2 (UI dla Speed-runu):** Stworzenie skondensowanego widoku podsumowania ankiety (prawa kolumna) zoptymalizowanego pod szybki przegląd wzrokowy i obsługę klawisza Spacji jako akcji "Zatwierdź i przejdź dalej".
- **Faza 5 (Integracja VLM):** Implementacja `ai_client.py`. Połączenie z Ollamą (port 11434). Wymuszenie zwrotu obiektu JSON zgodnego ze schematem oraz flagi `needs_review: bool` dla każdego pola, które budzi wątpliwości modelu.
- **Faza 6 (Spięcie logiki):** Podłączenie pętli "Zapisz i Następna" oraz pobierania gotowego CSV. Podświetlanie pól oznaczonych jako `needs_review`.

