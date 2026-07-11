# PLAN OPTYMALIZACJI PROCESU OCR I EKSTRAKCJI DANYCH

## Cel projektu

Zrefaktoryzowanie obecnego, jednoczesnego skryptu przetwarzania ankiet (Image -> JSON) do wysokowydajnej, asynchronicznej architektury dwuetapowej. System działa lokalnie na sprzęcie z kartą z serii RTX (pamięć VRAM jest kluczowym zasobem) oraz 32 GB RAM, wykorzystując modele serwowane przez Ollama. Czas przetwarzania jednej strony musi spaść z obecnych ~110 sekund do kilkunastu sekund.

## Ważne założenia i ograniczenia dla Agenta Kodującego

- **ZARZĄDZANIE PROMPTAMI:** Kategoryczny zakaz modyfikowania, wymyślania lub hardcodowania treści promptów w kodzie. Prompty (zarówno dla modelu wizyjnego, jak i tekstowego) będą dostarczane z zewnętrznego modułu/konfiguracji w języku angielskim. Twoim zadaniem jest wyłącznie przygotowanie architektury do ich przyjmowania i przekazywania.
- **ZARZĄDZANIE VRAM:** Minimalizacja operacji ładowania/rozładowywania modeli (model shuffling) jest absolutnym priorytetem optymalizacyjnym.

---

## ETAP 1: Pre-processing obrazu i optymalizacja zapytań API (Quick Wins)

**Cel:** Drastyczne zmniejszenie liczby tokenów wizyjnych oraz wymuszenie determinizmu modelu i utrzymania go w pamięci.

1.  **Moduł przetwarzania obrazu (Pillow):**
    - Zaimplementuj funkcję pre-processingu dla każdego zdjęcia wejściowego.
    - Przeskaluj obraz zachowując proporcje, tak aby dłuższy bok miał **maksymalnie 1500-2000 pikseli**.
    - Przekonwertuj obraz do skali szarości (grayscale).
    - Zaaplikuj lekkie podbicie kontrastu.
    - Zapisz wynikowy obraz w buforze pamięciowym (np. `io.BytesIO`) do wysyłki.
2.  **Konfiguracja klienta Ollama:**
    - Dla każdego zapytania do API (zarówno VLM, jak i modelu tekstowego) wymuś przekazywanie następującego obiektu `options`:
      - `temperature: 0.0` (absolutny determinizm).
      - `num_ctx: 8192` (lub więcej, aby zapobiec ucinaniu kontekstu przy wielu obrazach).
    - W każdym zapytaniu dodaj parametr: `keep_alive: "-1"` (lub np. `"30m"`), aby zablokować domyślne usuwanie modelu z VRAM po wykonaniu zadania.

---

## ETAP 2: Architektura Dwuetapowa i Batching (Rozbicie logiki)

**Cel:** Rozwiązanie problemu wąskiego gardła kognitywnego i przeładowywania pamięci VRAM poprzez wdrożenie dwóch osobnych przebiegów i przetwarzania wsadowego (batching).

1.  **Krok A: Ekstrakcja surowego tekstu (VLM - Vision Language Model)**
    - Zaimplementuj logikę, która ładuje model wizyjny (np. z rodziny `qwen-vl` lub `minicpm-v`).
    - Skrypt musi przyjąć listę zoptymalizowanych obrazów i przepuścić je przez VLM **jeden po drugim (lub w asynchronicznym batchu)** z wykorzystaniem zewnętrznego promptu (wyciąganie tekstu z obrazu).
    - Wyniki (surowe stringi) zapisuj do tymczasowej struktury danych (np. listy słowników, prostej bazy SQLite lub pamięci podręcznej).
2.  **Krok B: Formatowanie JSON (Text LLM)**
    - Po zakończeniu Kroku A dla danej partii danych, skrypt przełącza się na model tekstowy (np. z rodziny `llama3.1` lub `granite`).
    - Dla każdego zapisanego surowego stringa z Kroku A, skrypt inicjuje zapytanie do modelu tekstowego, wstrzykując tekst do zewnętrznego promptu formatującego.
    - W tym kroku wykorzystaj wbudowany w Ollama parametr `format='json'` (lub wymuś schemat Pydantic, jeśli korzystasz z nowszego API), aby zagwarantować odpowiednią strukturę wyjściową.

---

## ETAP 3: Asynchroniczna Orkiestracja (LangChain & asyncio)

**Cel:** Zbudowanie asynchronicznego potoku typu Producer-Consumer w celu nakładania na siebie zadań w czasie.

1.  **Integracja asyncio:**
    - Ustaw asynchroniczną kolejkę (`asyncio.Queue`).
    - **Worker Producer:** Pobiera obrazy, asynchronicznie odpytuje model VLM o surowy tekst i wrzuca wynik (`item_id`, `raw_text`) na kolejkę.
    - **Worker Consumer:** Nasłuchuje na kolejce. Gdy pojawi się `raw_text`, natychmiast asynchronicznie odpytuje model tekstowy o sformatowany JSON.
2.  **Opcjonalne spięcie przez LangChain (LCEL):**
    - Wykorzystaj LangChain do definicji łańcucha (Chain) przetwarzania, aby ułatwić batching (wywołania `.abatch()`) i ujednolicić interfejsy modeli (korzystając np. z `ChatOllama`).

_Krytyczna uwaga do sprzętu:_ Ze względu na ograniczenia VRAM na pojedynczej karcie, uruchomienie architektury z Etapu 3 (Producer-Consumer) wymaga, aby modele VLM i Text LLM zmieściły się w pamięci GPU _jednocześnie_. Aplikacja musi uwzględniać flagę środowiskową (np. `USE_SEQUENTIAL_BATCHING_FALLBACK`), która w razie błędu braku pamięci automatycznie cofa system do strategii z Etapu 2 (najpierw wszystkie obrazy, potem wszystkie teksty). Wymagane jest też ustawienie w systemie `OLLAMA_NUM_PARALLEL=2`.

---

## ETAP 4: Observability i Tracing (LangSmith)

**Cel:** Monitoring wydajności w czasie rzeczywistym i lokalizowanie wąskich gardeł w zrefaktoryzowanym kodzie.

1.  Zaimplementuj obsługę zmiennych środowiskowych dla LangSmith (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_ENDPOINT`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`).
2.  Upewnij się, że wywołania do modeli wizyjnych i tekstowych są otagowane/nagrane w śladach (traces) tak, aby w panelu LangSmith można było jednoznacznie oddzielić:
    - Czas trwania operacji wejścia/wyjścia plików obrazów.
    - Czas oczekiwania na połączenie z Ollama.
    - _Time to First Token_ oraz _Latency_ z podziałem na VLM i model tekstowy.

---
