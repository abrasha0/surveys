# Plan Frontend: AnkieterAI (React + Vite, hostowany przez FastAPI) — v2

Zaktualizowane po przeczytaniu pełnego `src/ui/*`. To zmieniło kilka rzeczy —
niektóre założenia z v1 były błędne albo za mało precyzyjne. Poniżej najpierw
co się zmieniło i dlaczego, potem tłumaczenie wzorców Streamlit → React, potem
pełna, bardziej granularna lista etapów.

---

## Co ujawnił kod źródłowy (i jak to zmienia plan)

- **Czerwona kropka przy polu to NIE `needs_review`.** To osobny mechanizm:
  wskaźnik "pole wymagane a puste", widoczny dopiero po pierwszej nieudanej
  próbie zatwierdzenia (`show_errors`). `needs_review` (do usunięcia wg
  `known-issues.md` #5) nigdzie w tym kodzie się nie pojawia — najwyraźniej
  UI już z niego zrezygnował, zostało tylko do wyczyszczenia w modelu danych
  po stronie backendu. **Wskaźnik błędu wymaganego pola zostaje w Reactcie 1:1.**
- **Zatwierdzanie jest dwuetapowe, nie blokujące.** Pierwsze kliknięcie
  "Zatwierdź" przy brakujących polach nie zapisuje nic — tylko odsłania
  czerwone kropki i przycisk "Zatwierdź mimo błędów". Dopiero świadome
  kliknięcie tego drugiego przycisku zapisuje dane mimo braków. To trzeba
  odtworzyć dokładnie, bo to świadomy safety-net, nie przypadek.
- **Spacja celuje wyłącznie w główny przycisk "Zatwierdź", nigdy w "mimo błędów".**
  Efekt uboczny: jeśli brakuje pól, samo wciskanie Spacji nigdy nie przepchnie
  ankiety dalej — trzeba kliknąć myszką. To wygląda na celowe zabezpieczenie
  przed przypadkowym pomijaniem wymaganych pól i warto to zachować.
  Dodatkowo: skrót nie odpala się, gdy focus jest w polu tekstowym (Streamlit
  sprawdza `e.target === document.body`) — w Reakcie to `document.activeElement`.
- **Draft ankiety przeżywa nawigację "Poprzednia"/"Następna" bez zapisu.**
  Streamlit trzyma wartości w `session_state` pod kluczem per-ankieta, więc
  wpisane, ale niezatwierdzone dane nie znikają przy przejściu do innej ankiety
  i powrocie. To osobna decyzja architektoniczna dla Reacta (stan lokalny nie
  jest tu "za darmo" jak w Streamlit) — dodałem osobny etap na to (F12).
- **Wybór zakładki strony (1-5) też jest pamiętany per ankieta.** Wracasz do
  ankiety i widzisz tę samą stronę, na której skończyłeś.
- **Progress bar przetwarzania liczony jest z wag konfigurowalnych** (VLM ≈ X%,
  formatowanie ≈ Y% "slotu" jednej ankiety) obliczanych po stronie Streamlit z
  `config.processing`. W Reakcie **lepiej, żeby backend przysyłał już gotowy
  ułamek postępu**, zamiast duplikować tę wiedzę o wagach na froncie — patrz
  punkt koordynacji niżej.
- **"Ostatnie kroki" (historia zdarzeń)** — w Streamlit każdy callback trafiał
  do UI natychmiast (proces synchroniczny). Przy pollingu z Reacta pojedyncze,
  szybkie przejścia (np. `vlm_extracting` → `text_formatting` tej samej strony
  w czasie krótszym niż interwał pollingu) mogą zostać przegapione. Backend
  powinien sam trzymać ograniczoną listę zdarzeń i zwracać ją w całości przy
  każdym pollu — patrz punkt koordynacji niżej.
- **Obrazy nie muszą być base64.** `get_image_base64` + `st.cache_data` to
  obejście specyficzne dla wstrzykiwania obrazu w Streamlit. W Reakcie to
  zwykły `<img src="/api/surveys/{id}/pages/{n}/image">` — przeglądarka
  cache'uje sama, zero dodatkowej roboty.
- **Cały CSS-in-JS fighting (`_inject_image_scaling_js`, `MutationObserver`,
  wymuszanie stylów przez `!important` na węzłach DOM) jest w 100% obejściem
  tego, że Streamlit sam zarządza swoim drzewem DOM przez Emotion.** W Reakcie
  ty jesteś właścicielem DOM — te wszystkie hacki po prostu znikają, layout
  robi się zwykłym flexboksem/Tailwindem bez żadnej gimnastyki.
- **Dwa osobne paski postępu, nie jeden.** Pasek w `processing.py` (postęp
  OCR całego batcha) i pasek w `verification.py` (pozycja w kolejce
  weryfikacji) to różne liczniki o różnym mianowniku. Łatwo je pomylić przy
  projektowaniu jednego komponentu — rozdzielam je świadomie na F7 i F8.

---

## Mapowanie Streamlit → React

| Streamlit (obecny kod) | React (docelowo) |
|---|---|
| `st.session_state[f"{prefix}_{field}"]` per pole | stan formularza w store per-ankieta (Zustand/Context), nie per-pole-jako-string-key |
| `st.fragment` (izolowany rerun formularza) | naturalna właściwość Reacta — update stanu w komponencie dziecka nie rerenderuje rodzica; nie trzeba nic specjalnego |
| `get_image_base64` + `st.cache_data` | `<img src=".../image">`, cache przeglądarki |
| `_inject_image_scaling_js` (MutationObserver, wymuszanie stylów) | Tailwind flex/`object-contain` bezpośrednio na elemencie — usuwamy całkowicie |
| `st.balloons()` na ekranie końcowym | opcjonalny, lekki akcent (np. subtelna animacja checkmarka) albo pomijamy — to fajerwerk, nie funkcja |
| JS listener na `document.body` (Spacja) | `useEffect` + `window.addEventListener('keydown', ...)`, sprawdzenie `document.activeElement` |
| Wagi z `config.processing` liczone w UI | backend zwraca gotowy `progress_fraction` w odpowiedzi statusu |
| Lista "ostatnich kroków" budowana z kolejnych callbacków | backend trzyma i zwraca `recent_events` (ograniczona lista) przy każdym pollu |
| `st.radio` z kluczem per ankieta (pamięć wybranej strony) | stan `selectedPage` w store per-ankieta, nie per-komponent |
| Kolumny `st.columns([4,6])` | `grid-cols-[4fr_6fr]` albo flex `basis-[40%]`/`basis-[60%]` |

---

## Nowe punkty koordynacji z backendem

1. **`GET /api/field-specs`** (już zgłoszone w v1) — serializacja `ALL_FIELDS`,
   żeby front nie duplikował definicji 63 pól.
2. **`GET /api/processing/status` powinien zwracać więcej niż tylko punktowy stan:**
   - `progress_fraction: float` (0-1) — już policzony po stronie backendu,
     tą samą logiką wag co obecne `config.processing["progress_vlm_weight"]`/
     `progress_text_weight`, żeby front niczego nie duplikował
   - `recent_events: [{status, message, survey_idx, timestamp}]` — ograniczona
     lista (np. ostatnie 10-20), żeby nic nie ginęło między pollami
   - `status` jako enum zgodny z obecnym: `survey_start | vlm_extracting |
     vlm_retrying | text_formatting | text_retrying | page_error |
     survey_retry | survey_error | survey_done | batch_done` (dodałem
     `survey_retry`/`survey_error` pod nową logikę retry-całej-ankiety-3x,
     której nie było jeszcze w oryginalnym kodzie)
   - `extra: {elapsed_s?, pages?}` — jak obecnie, do komunikatu przy `survey_done`

---

## Założenia technologiczne (aktualizacja)

Wszystko z v1 (Vite+React+TS, Tailwind, TanStack Query, lekki router) zostaje.
Dodatkowo, pod wpływem odkrycia draft-persistence i per-ankieta stanu UI
(wybrana strona, `show_errors`):

- **Zustand** (nie Context, nie Redux) na stan, który nie jest danymi z serwera:
  draft wartości pól per-ankieta, `selectedPage` per-ankieta, `showErrors`
  per-ankieta. Płaski, mały store `Record<surveyId, {...}>`, blisko
  koncepcyjnie do tego, co robił `session_state` — najmniej zaskoczeń przy
  portowaniu logiki 1:1. Świadomie **nie** React Hook Form — RHF zakłada
  jedną żywą instancję formularza, a tu potrzebujemy trzymać draft wielu
  ankiet naraz (ta, którą się opuszcza bez zapisu, ma nie stracić danych).
- Formularz i tak zostaje w pełni kontrolowany (controlled inputs) — walidacja
  "czy pole puste" jest prosta i nie potrzebuje biblioteki walidacyjnej.

---

## Etapy

### F1 — Scaffold i tooling
**Zależności:** brak.
- Vite (react-ts), Tailwind init, ESLint/Prettier
- Struktura `src/{api,store,features,app}`
- Proxy `/api` → `localhost:8000`, `.env` z `VITE_API_BASE`

**Kryteria akceptacji:** `npm run dev`/`npm run build` działają na pustym layoucie.

---

### F2 — Design tokens i wspólne prymitywy wizualne
**Zależności:** F1.
- Tailwind theme: kolory statusów (błąd `#ff4b4b`, info/postęp `#1E88E5`,
  sukces zielony, warning żółty), spacing dla kompaktowych formularzy
- Współdzielone komponenty: `Spinner` (props: kolor — bo VLM ma czerwony top-border,
  formatter niebieski), `Alert` (warianty info/warning/error/success — 1:1 z
  `st.info/warning/error/success`), `ProgressBar` (cienki, zaokrąglony, jak
  `header-progress` z `styles.py`), `ErrorDot`

**Kryteria akceptacji:** wszystkie warianty widoczne w prostym podglądzie
(np. tymczasowa strona `/dev/components`), zgodne wizualnie z oryginałem
(te same kolory/kształty, bez CSS-owej gimnastyki).

---

### F3 — API client + warstwa danych (na mockach)
**Zależności:** F2.
- Fetch wrapper (`credentials: 'include'`, przechwytywanie 401)
- TanStack Query: `useSurveys()`, `useProcessingStatus()` (polling), mutacje
  `useLogin()`, `useStartProcessing()`, `useSaveSurvey()`, `useFieldSpecs()`
- Fixture'y zgodne z rozszerzonym kontraktem statusu (`progress_fraction`,
  `recent_events`) i z realnymi 63 polami z `survey-structure.md`

**Kryteria akceptacji:** hooki zwracają dane z fixture'ów, polling działa.

---

### F4 — App shell, routing, auth guard
**Zależności:** F3.
- Layout `100vh`, brak scrolla okna
- Trasy `/login`, `/app`, guard przez próbę requestu chronionego (401 → redirect)

**Kryteria akceptacji:** brak sesji → redirect na `/login`.

---

### F5 — Ekran logowania
**Zależności:** F4.
- Tytuł "AnkieterAI" + podtytuł, pole hasła, przycisk "Zaloguj"
- Błędne hasło → komunikat inline (odpowiednik `st.error("Nieprawidłowe hasło")`)

**Kryteria akceptacji:** poprawne hasło wpuszcza, złe pokazuje błąd bez przeładowania.

---

### F6 — Dashboard kolejki ankiet
**Zależności:** F3, F4.
- Lista ankiet z `useSurveys()`, statusy `queued/processing/ready/error/verified`
  wizualnie rozróżnione (kolor/ikona)
- Przycisk startu przetwarzania (`useStartProcessing()`)
- Klik na ankietę `ready`/`verified` → widok weryfikacji

**Kryteria akceptacji:** lista aktualizuje się przy pollingu, tylko
`ready`/`verified` są klikalne.

---

### F7 — Panel postępu przetwarzania (osobny od F8!)
**Zależności:** F3, F6, punkt koordynacji #2 z backendem.
- Pasek postępu z `progress_fraction` (bezpośrednio z API, bez liczenia wag na froncie)
- Aktualny stan: ikona/spinner + komunikat, zgodnie z mapowaniem statusów:
  - `survey_start` → `Alert variant="info"`
  - `vlm_extracting` → `Spinner color="red"` + 👁 + komunikat
  - `vlm_retrying` → `Alert variant="warning"` + 🔄
  - `text_formatting` → `Spinner color="blue"` + 📝 + komunikat
  - `text_retrying` → `Alert variant="warning"` + 🔄
  - `page_error` → `Alert variant="error"`
  - `survey_retry` (nowość) → `Alert variant="warning"` z numerem próby
  - `survey_error` (nowość, po 3 nieudanych próbach) → `Alert variant="error"`,
    ankieta oznaczona jako nieprzeprocesowana
  - `survey_done` → `Alert variant="success"` + `({elapsed_s}s, {pages} stron)` z `extra`
  - `batch_done` → `Alert variant="success"`
- Lista "Ostatnie kroki" z `recent_events` (nie budowana lokalnie z historii pollingu)

**Kryteria akceptacji:** panel na mockach odtwarza sekwencję stanów 1:1 z
oryginałem (kolory, ikony, treść), historia nie gubi zdarzeń między pollami.

---

### F8 — Topbar weryfikacji (pozycja w kolejce weryfikacji, osobna liczba od F7)
**Zależności:** F6.
- "Ankieta X z Y" — X/Y liczone wśród ankiet `ready`+`verified` (nie wśród
  wszystkich w batchu — to inna liczba niż pasek w F7)
- Przyciski w jednym rzędzie: "Poprzednia ankieta", "Następna ankieta",
  "Zatwierdź ankietę" (issues #3, #4)
- Nawigacja pomija `queued`/`processing`/`error`

**Kryteria akceptacji:** licznik i nawigacja poprawne przy rosnącej w czasie
liczbie gotowych ankiet (interleaved processing).

---

### F9 — Moduł przeglądarki zdjęć
**Zależności:** F8.
- Panel ~40% szerokości, `<img src="/api/surveys/{id}/pages/{n}/image">`,
  `object-contain`, bez scrolla
- 5 zakładek stron, wybór **pamiętany per ankieta** (store z F-technologicznego
  założenia, nie lokalny stan komponentu)
- Stany brzegowe: brak pliku dla strony → komunikat (odpowiednik
  `"Plik nie istnieje"` / `"Brak obrazu dla tej strony"`)
- Opcjonalnie `react-zoom-pan-pinch`

**Kryteria akceptacji:** obraz zawsze w całości widoczny, przełączanie zakładek
natychmiastowe, powrót do wcześniej oglądanej ankiety pokazuje tę samą stronę.

---

### F10 — Moduł formularza — renderowanie pól
**Zależności:** F3 (field-specs), F8.
- Pola z bieżącej strony podzielone na dwie kolumny **po indeksie, nie po
  kategorii** (`fields.slice(0, mid)` / `fields.slice(mid)`) — dokładnie jak
  `render_form_fragment`
- Mapowanie typów: `select` → dropdown z `choices`, domyślny index jak
  `_get_index` (wartość jeśli jest w `choices`, inaczej pierwszy element);
  `text` → input tekstowy; `number` → input numeryczny z `min`/`max` z
  field-spec (domyślnie 0/100 jeśli brak) i placeholderem z field-spec
  (w oryginale zahardkodowany "Wpisz wiek" — bo to jedyne pole liczbowe;
  jeśli zostanie jedynym, można zostawić 1:1, inaczej placeholder per pole)

**Kryteria akceptacji:** 63 pola renderują się z poprawnym typem kontrolki
zgodnie z `survey-structure.md`.

---

### F11 — Walidacja i wskaźnik błędu pola
**Zależności:** F10.
- Reguła błędu per typ: `select` → brak wartości lub spoza `choices`;
  `text` → puste po trim; `number` → `null`/`undefined`
- `ErrorDot` po lewej stronie pola, widoczny tylko gdy `showErrors===true`
  (per-ankieta) **i** pole ma błąd — placeholder o tej samej szerokości gdy
  niewidoczny, żeby layout się nie przesuwał

**Kryteria akceptacji:** kropki pojawiają się dopiero po pierwszej próbie
zatwierdzenia z brakami, nie wcześniej; brak przeskoków layoutu.

---

### F12 — Trwałość draftu formularza między nawigacją
**Zależności:** F10, F11, store z założeń technologicznych.
- Wartości pól inicjalizowane z wyniku AI **tylko przy pierwszym wejściu** w
  daną ankietę (jeśli w store nic jeszcze nie ma dla tej ankiety) — kolejne
  wejścia czytają z draftu, nie nadpisują go wynikiem AI ponownie
- "Poprzednia"/"Następna" nie czyszczą draftu niezatwierdzonej ankiety

**Kryteria akceptacji:** wpisujesz coś, przechodzisz do innej ankiety i
wracasz — wpisana wartość nadal tam jest, mimo braku zapisu na backend.

---

### F13 — Flow zatwierdzania: dwuetapowy submit + Spacja
**Zależności:** F11, F12.
- Klik "Zatwierdź": jeśli są błędy → `showErrors=true` dla tej ankiety,
  **nie wysyła** requestu; jeśli brak błędów → `useSaveSurvey()`, status → `verified`
- Przycisk "Zatwierdź mimo błędów" renderowany **tylko** gdy `showErrors &&
  errorsExist` — wysyła draft mimo braków
- Global listener na Spację (`useEffect`): ignorowany, gdy `document.activeElement`
  to input/select/textarea; w przeciwnym razie odpowiada dokładnie kliknięciu
  "Zatwierdź" (nie "mimo błędów" — to zostaje wyłącznie akcją świadomą, myszką)
- Po zapisie: przejście do kolejnej ankiety `ready` (nie kolejnej w ogóle)

**Kryteria akceptacji:** pierwsze zatwierdzenie z brakami tylko odsłania błędy,
nie zapisuje; Spacja nigdy nie wywołuje force-submitu; po realnym zapisie
licznik z F8 i lista z F6 aktualizują się.

---

### F14 — Ekran zakończenia
**Zależności:** F6, F8.
- Widoczny, gdy nie ma już ankiet do zweryfikowania (wszystkie `verified`/`error`)
  i worker skończył (`batch_done`)
- Komunikat sukcesu + przycisk pobrania CSV (link/`fetch` do gotowego pliku)
- "Nowa sesja" — do ustalenia przy implementacji, co dokładnie resetuje w
  nowym modelu (obrazy są już w katalogu z góry, więc to raczej ponowny skan
  katalogu niż czyszczenie uploadu jak w oryginale)
- `st.balloons()` — pomijamy albo lekki odpowiednik (patrz mapowanie wyżej)

**Kryteria akceptacji:** ekran pojawia się automatycznie po ostatniej
weryfikacji, CSV faktycznie się pobiera.

---

### F15 — Stany błędów i brzegowe
**Zależności:** F6-F14.
- Ankieta `error`/`survey_error`: widoczny powód, nie blokuje reszty UI
- Pusty stan (kolejka pusta)
- Baner "worker dalej przetwarza w tle" widoczny w widoku weryfikacji, gdy
  batch jeszcze trwa

**Kryteria akceptacji:** żaden stan nie daje białego ekranu ani zawieszenia.

---

### F16 — Polish
**Zależności:** wszystko powyżej, najlepiej już na prawdziwym backendzie.
- Skeletony, przejścia, focus management
- Przegląd spójności z F2 (tokeny wizualne) na całej aplikacji

**Kryteria akceptacji:** pełny flow login → kolejka → weryfikacja (z draftem,
błędami, Spacją) → zakończenie działa płynnie i bez niespójności wizualnych.
