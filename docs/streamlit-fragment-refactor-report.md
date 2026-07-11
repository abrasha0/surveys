# Raport Refactoru: Wykorzystanie `@st.fragment` i zaawansowanego UI/UX w Streamlit

**Data:** 2026-07-11
**Projekt:** AnkieterAI — architektura `src2`
**Streamlit:** 1.59.0 (wsparcie dla `@st.fragment` od v1.37, `parallel` od v1.58)

---

## 1. Podsumowanie wykonawcze

### Problem

Architektura `src2` **nie wykorzystuje dekoratora `@st.fragment`** w żadnym z 19 plików źródłowych. Aplikacja opiera się na `app.py` jako **front controllerze** z pełnym `st.rerun()` przy każdej akcji użytkownika. W praktyce oznacza to, że:

- Zmiana **jednego selectboxa** w formularzu weryfikacyjnym → rerun **całej aplikacji** (header, radio, obraz base64, wszystkie pola formularza, przyciski)
- Kliknięcie **"Zatwierdź"** z błędami → rerun wszystkiego + ponowne przerysowanie HTML obrazu base64
- **Każda interakcja** kosztuje pełny cykl renderowania Streamlit

To jest bezpośrednią przyczyną **issue #11** (rozjeżdżanie UI przy interakcji z formularzem).

### Rozwiązanie

Wdrożenie dekoratora `@st.fragment` izolującego sekcje UI tak, aby interakcja z widgetem rerenderowała **tylko swój fragment**, nie całą aplikację. Uzupełnienie o inne nowoczesne mechanizmy Streamlit (`@st.dialog`, `st.form`, `st.toast`, `st.badge`, `st.popover`, `st.query_params`).

### Oczekiwany efekt

| Metryka | PRZED | PO refactorze |
|---------|-------|---------------|
| Componentów rerenderowanych przy zmianie pola formularza | ~15-20 (wszystko) | 3-5 (tylko fragment formularza) |
| Koszt zmiany strony (radio) | Pełny rerun | 2 fragmenty (obraz + formularz) |
| Koszt kliknięcia "Poprzednia" | Pełny rerun | 1 fragment (nawigacja) + st.rerun() |
|.issue #11 (rozjeżdżanie UI) | Aktywny | Eliminacja przyczyny źródłowej |
| Dodatkowe funkcje UI | brak | dialogi, toasty, badge'e, popover |

---

## 2. Analiza obecnego stanu

### 2.1. Wykorzystanie dekoratorów Streamlit

| Dekorator | Wystąpienia | Opis |
|-----------|-------------|------|
| `@st.fragment` | **0** | Nie jest używany nigdzie |
| `@st.cache_data` | 1 | `verification.py` — `get_image_base64()` |
| `@st.cache_resource` | 0 | Nie jest używany |
| `@st.dialog` | 0 | Nie jest używany |
| `@st.form` | 0 | Nie jest używany — formularz "ręczny" |

### 2.2. Mapa rerunów (obecny stan)

```
Każda akcja użytkownika → app.py → pełny rerun skryptu
                                    ├── inject_global_css() (guard: _CSS_INJECTED)
                                    ├── inject_verification_css() (pass)
                                    ├── inject_space_shortcut()
                                    ├── Pobranie AI results z session_state
                                    ├── Inicjalizacja widgetów (if key not in session_state)
                                    ├── Wyrenderowanie headera HTML
                                    ├── Wyrenderowanie radio buttona
                                    ├── Lewa kolumna: get_image_base64() → st.markdown(base64)
                                    ├── Prawa kolumna: render_field() × N (dla każdego pola strony)
                                    ├── Walidacja wszystkich pól
                                    └── Wyrenderowanie przycisków
```

### 2.3. Szczegółowa analiza `verification.py` — kandydat nr 1

Plik `ui/pages/verification.py` (158 linii) jest **najczęściej rerenderowanym** ekranem w aplikacji. Każda interakcja (zmiana pola, zmiana strony, submit) powoduje:

1. **Linia 32-33**: Injekcja CSS i JS shortcut (koszt: minimalny, ale wykonywany)
2. **Linia 35-50**: Pobranie stanu + inicjalizacja wszystkich 63 pól w session_state
3. **Linia 53-63**: Wyrenderowanie headera HTML z progress barem
4. **Linia 66-74**: Wyrenderowanie radio buttona (5 stron)
5. **Linia 79-99**: Lewa kolumna — `get_image_base64()` (z cache) + `st.markdown(img base64)`
6. **Linia 101-105**: Prawa kolumna — `render_field()` dla pól aktualnej strony
7. **Linia 108-123**: Walidacja WSZYSTKICH 63 pól (nie tylko aktualnej strony)
8. **Linia 126-143**: Wyrenderowanie 2-3 przycisków

**Kluczowy problem:** Zmiana jednego `selectbox` w linii 105 powoduje rerun od linii 1, w tym ponowne wyrenderowanie obrazu base64 (linia 86-93) — mimo że obraz się nie zmienił.

### 2.4. Analiza `processing.py` — kandydat nr 2

Plik `ui/pages/processing.py` (70 linii) używa `asyncio.run()` do blokowania整个 UI na czas przetwarzania AI. Progress bar jest aktualizowany przez callback, ale:

- `progress_placeholder.container()` przerysowuje cały kontener przy każdym callbacku
- `history_placeholder.container()` kumuluje historię — rerunuje się przy każdej nowej wiadomości
- Brak możliwości anulowania w trakcie (retry logic blokuje UI)

---

## 3. Primer: `@st.fragment` w Streamlit 1.59.0

### 3.1. Czym jest fragment

Fragment to funkcja Pythona ozdobiona dekoratorem `@st.fragment`, która może się **przeladowywać niezależnie od reszty aplikacji**. Przy interakcji z widgetem wewnątrz fragmentu, rerunowany jest **tylko ten fragment** — reszta aplikacji pozostaje zamrożona.

```python
import streamlit as st

@st.fragment
def my_fragment():
    name = st.text_input("Imię")
    if st.button("Powitanie"):
        st.write(f"Cześć, {name}!")

# Reszta aplikacji NIE rerunuje się przy interakcji z powyższymi widgetami
st.write("To jest reszta aplikacji - stabilna")
my_fragment()
```

### 3.2. Sygnatura

```python
@st.fragment(func=None, *, run_every=None, parallel=False)
```

| Parametr | Typ | Opis |
|----------|-----|------|
| `func` | callable | Funkcja do zamienienia na fragment |
| `run_every` | str/float/timedelta/None | Auto-rerun co interwał (np. `"2s"`, `5`, `timedelta(seconds=10)`) |
| `parallel` | bool | `True` = wykonywanie równolegle z innymi fragmentami w thread poolu (od v1.58) |

### 3.3. Kluczowe zasady

1. **Widgety tylko wewnątrz fragmentu** — nie można renderować widgetów z poziomu fragmentu do zewnętrznych kontenerów
2. **`st.rerun()`** wywołane wewnątrz fragmentu → pełny rerun aplikacji
3. **`st.rerun(scope="fragment")`** → rerun tylko tego fragmentu
4. **Wartości zwracane** są ignorowane podczas fragment rerun — komunikacja przez `st.session_state`
5. **`st.sidebar`** nie jest bezpośrednio obsługiwany — trzeba wywołać fragment wewnątrz `with st.sidebar:`
6. **Nie można łączyć** `@st.cache_data` i `@st.fragment` na tej samej funkcji

### 3.4. Porównanie z innymi mechanizmami

| Mechanizm | Kiedy rerunuje | Co rerunuje | Widgety |
|-----------|---------------|-------------|---------|
| **Brak (normalny Streamlit)** | Każda interakcja | Cały skrypt | Wszędzie |
| **`@st.fragment`** | Interakcja z widgetem w fragmencie | Tylko ten fragment | Tylko wewnątrz fragmentu |
| **`@st.fragment(run_every=...)`** | Co X sekund + interakcja | Tylko ten fragment | Tylko wewnątrz fragmentu |
| **`st.form`** | Submit formularza | Cały skrypt | Tylko wewnątrz formularza |
| **Callback (`on_click`)** | Przed rerunem | Cały skrypt (callback jako prefix) | Wszędzie |

---

## 4. Szczegółowy plan refactoru

### Faza 1: Fragmentacja `verification.py` (WYSOKI priorytet)

**Cel:** Izolacja 4 sekcji UI w `verification.py` do osobnych fragmentów, tak aby interakacja z jednym nie rerenderowała pozostałych.

**Obecna struktura (158 linii, 1 plik):**
```
render()
├── inject CSS/JS
├── init session_state
├── header HTML
├── radio (wybór strony)
├── col_left: obraz base64
├── col_right: formularz (render_field × N)
├── walidacja wszystkich pól
└── przyciski (Poprzednia, Zatwierdź, Mimo błędów)
```

**Docelowa struktura (4 pliki):**
```
render()                          # Orkiestrator (brak @st.fragment)
├── render_header_fragment()      # @st.fragment — header + postęp
├── render_image_fragment()       # @st.fragment — obraz dla aktualnej strony
├── render_form_fragment()        # @st.fragment — formularz dla aktualnej strony
└── render_navigation_fragment()  # @st.fragment — przyciski nawigacyjne
```

#### 4.1.1. `render_image_fragment()` — izolacja obrazu

```python
# ui/pages/verification_fragments.py

@st.fragment
def render_image_fragment(survey, page_idx: int):
    """
    Fragment odpowiedzialny za wyświetlanie obrazu ankiety.
    Rerunuje się TYLKO cuando zmienia się page_idx (przez radio).
    Zmiana pól formularza NIE wpływa na ten fragment.
    """
    if page_idx < len(survey.files):
        img_path = survey.files[page_idx]
        if img_path.exists():
            try:
                b64 = get_image_base64(img_path)
                st.markdown(
                    f"""
                    <div class="verify-col-image">
                        <img src="data:image/jpeg;base64,{b64}" />
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            except Exception as e:
                st.error(f"Błąd wczytywania obrazu: {e}")
        else:
            st.info(f"Plik nie istnieje: {img_path.name}")
    else:
        st.info("Brak obrazu dla tej strony")
```

**Efekt:** `get_image_base64()` ma `@st.cache_data`, więc nawet przy rerunie fragmentu obraz jest z cache. Ale kluczowe jest to, że **sam HTML z base64 nie jest przerysowywany** gdy user klika w pole formularza.

#### 4.1.2. `render_form_fragment()` — izolacja formularza

```python
@st.fragment
def render_form_fragment(survey, page_idx: int, prefix: str):
    """
    Fragment odpowiedzialny za formularz pól aktualnej strony.
    Rerunuje się TYLKO gdy zmienia się page_idx lub wartość pola.
    Zmiana obrazu (gdyby była niezależna) NIE wpływa na ten fragment.
    """
    show_errors = st.session_state.get(f"show_errors_{survey.id}", False)

    fields = PAGE_MAP.get(page_idx, [])
    for f in fields:
        render_field(f, prefix, show_errors)
```

**Efekt:** Zmiana jednego selectboxa rerunuje tylko ten fragment — reszta UI (obraz, header, radio, przyciski) pozostaje stabilna.

#### 4.1.3. `render_navigation_fragment()` — izolacja nawigacji

```python
@st.fragment
def render_navigation_fragment(survey_id: int, errors_exist: bool):
    """
    Fragment odpowiedzialny za przyciski nawigacyjne.
    Zawiera logikę submit i walidacji.
    """
    sm = StateManager()

    col_btns = st.columns([1, 1, 4])
    with col_btns[0]:
        if st.button("⬅ Poprzednia", key=f"prev_{survey_id}"):
            sm.previous_survey()
            st.rerun()  # pełny rerun — zmiana indexu wymaga odświeżenia całej strony

    with col_btns[1]:
        submitted = st.button("Zatwierdź", type="primary", key=f"submit_{survey_id}")

    force = False
    show_errors = st.session_state.get(f"show_errors_{survey_id}", False)
    if show_errors and errors_exist:
        with col_btns[2]:
            force = st.button(
                "Zatwierdź mimo błędów",
                type="secondary",
                key=f"force_{survey_id}",
            )

    # Obsługa zatwierdzenia — zapisz wynik w session_state
    if submitted:
        if errors_exist:
            st.session_state[f"show_errors_{survey_id}"] = True
            st.rerun(scope="fragment")
        else:
            st.session_state[f"_submit_result_{survey_id}"] = True

    if force:
        st.session_state[f"_submit_result_{survey_id}"] = True
```

#### 4.1.4. `render()` — orkiestrator (refaktorowany)

```python
def render(survey):
    """
    Orkiestrator ekranu weryfikacji. Wywołuje 4 niezależne fragmenty.
    Sam NIE jest fragmentem — pełny rerun tutaj oznacza odświeżenie
    całej strony (np. po zmianie indexu ankiety).
    """
    inject_verification_css()
    inject_space_shortcut()

    sm = StateManager()
    current, total = sm.get_current_index() + 1, len(sm.get_surveys())
    prefix = f"f_{survey.id}"

    # Pobierz wyniki AI
    ai_results = sm.get_ai_results()
    result_dict = ai_results.get(survey.id)
    if not result_dict:
        st.error("Brak wyników AI dla tej ankiety")
        return False, None

    # Inicjalizacja widgetów
    for f in ALL_FIELDS:
        key = f"{prefix}_{f.name}"
        if key not in st.session_state:
            st.session_state[key] = result_dict.get(f.name, f.default)

    # --- Header (zwykły, bez fragmentu — koszt minimalny) ---
    st.markdown(
        f"""
        <div class="header-container">
            <span class="header-label">Ankieta {current} z {total}</span>
            <div class="header-progress-wrapper">
                <div class="header-progress-fill" style="width:{current/total*100}%"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Wybór strony (bezpośrednio, nie we fragmencie — radiobutton jest lekki) ---
    page_names = ["Strona 1", "Strona 2", "Strona 3", "Strona 4", "Strona 5"]
    selected_page = st.radio(
        "Wybierz stronę ankiety",
        page_names,
        index=0,
        horizontal=True,
        key=f"page_select_{survey.id}",
    )
    page_idx = page_names.index(selected_page)

    # --- Główny layout ---
    col_left, col_right = st.columns(2, gap="small")

    # Lewa kolumna — FRAGMENT obrazu
    with col_left:
        render_image_fragment(survey, page_idx)

    # Prawa kolumna — FRAGMENT formularza
    with col_right:
        render_form_fragment(survey, page_idx, prefix)

    # --- Walidacja błędów ---
    errors_exist = False
    for f in ALL_FIELDS:
        key = f"{prefix}_{f.name}"
        val = st.session_state.get(key)
        if f.kind == "select":
            if val is None or val not in f.choices:
                errors_exist = True
                break
        elif f.kind == "text":
            if val is None or str(val).strip() == "":
                errors_exist = True
                break
        elif f.kind == "number":
            if val is None:
                errors_exist = True
                break

    # --- FRAGMENT nawigacji ---
    render_navigation_fragment(survey.id, errors_exist)

    # --- Sprawdź wynik z session_state (fragment zapisał tam submit) ---
    if st.session_state.pop(f"_submit_result_{survey.id}", False):
        values = {f.name: st.session_state.get(f"{prefix}_{f.name}") for f in ALL_FIELDS}
        return True, values

    return False, None
```

#### 4.1.5. Mapa rerunów PO refactorze

```
Interakcja z polem formularza:
  → render_form_fragment() rerun (3-5 komponentów)
  → reszta NIE rerunuje się (obraz, header, radio, nawigacja — stabilne)

Zmiana strony (radio):
  → Pełny rerun (radio jest poza fragmentami)
  → render_image_fragment() — nowy obraz
  → render_form_fragment() — nowe pola

Kliknięcie "Poprzednia":
  → render_navigation_fragment() rerun
  → st.rerun() → pełny rerun (zmiana indexu wymaga odświeżenia)

Kliknięcie "Zatwierdź" (z błędami):
  → render_navigation_fragment() → st.rerun(scope="fragment")
  → Tylko nawigacja się przerysowuje (pojawia się "Zatwierdź mimo błędów")
```

---

### Faza 2: `@st.fragment` z `run_every` w `processing.py` (ŚREDNI priorytet)

**Cel:** Auto-aktualizacja progress bara bez blokowania UI i bez `asyncio.run()` blokującego główny wątek.

#### 4.2.1. Refaktor `processing.py`

```python
import streamlit as st
from state.state_manager import StateManager
from ai.client import AIClient, ProcessingStatus
from data_handler import save_cache
from ui.styles import inject_global_css
import asyncio
import threading


def render():
    inject_global_css()
    sm = StateManager()
    surveys = sm.get_surveys()
    if not surveys:
        st.error("Brak ankiet do przetworzenia")
        return

    # Jeśli już przetwarzamy — pokaż progress fragment
    if StateManager.is_processing():
        render_processing_fragment()
    else:
        # Przycisk start
        if st.button("Rozpocznij przetwarzanie", type="primary"):
            StateManager.set_processing(True)
            StateManager.reset_cancel()
            # Uruchom batch w tle (nie blokując UI)
            _start_background_batch(surveys)
            st.rerun()


def _start_background_batch(surveys):
    """Uruchamia batch AI w osobnym wątku, nie blokując UI."""
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            client = AIClient()
            sm = StateManager()

            async def batch():
                groups = [s.files for s in surveys]
                await client.analyze_batch(
                    groups,
                    progress_callback=lambda status: _store_progress(status),
                    survey_done_callback=lambda idx, res: sm.set_ai_result(idx, res),
                )
                save_cache(sm.get_ai_results())
                sm.set_processing(False)

            loop.run_until_complete(batch())
        except Exception as e:
            StateManager.set_processing(False)
        finally:
            loop.close()
            client.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


def _store_progress(status: ProcessingStatus):
    """Zapisuje status do session_state dla odczytu przez fragment."""
    st.session_state["_processing_status"] = {
        "survey_idx": status.survey_idx,
        "total_surveys": status.total_surveys,
        "status": status.status,
        "message": status.message,
        "extra": status.extra,
    }


@st.fragment(run_every="2s")
def render_processing_fragment():
    """
    Fragment auto-odświeżający progress co 2s.
    Nie blokuje UI — reszta aplikacji pozostaje responsywna.
    """
    status_data = st.session_state.get("_processing_status")

    if not status_data:
        st.info("Oczekiwanie na rozpoczęcie przetwarzania...")
        return

    pct = status_data["survey_idx"] / max(status_data["total_surveys"], 1)
    st.progress(pct, text=f"Ankieta {status_data['survey_idx']+1} z {status_data['total_surveys']}")

    status = status_data["status"]
    msg = status_data["message"]

    if status == "processing_page":
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;min-height:24px;font-size:0.9rem">'
            f'<span class="mini-spinner"></span><span>{msg}</span></div>',
            unsafe_allow_html=True,
        )
    elif status == "retrying":
        st.warning(msg)
    elif status == "page_error":
        st.error(msg)
    elif status == "survey_done":
        extra = status_data.get("extra") or {}
        elapsed = extra.get("elapsed_s", "")
        if elapsed:
            msg += f" ({elapsed}s)"
        st.success(msg)
    elif status == "batch_done":
        st.success(msg)

    # Historia
    if "_processing_history" not in st.session_state:
        st.session_state["_processing_history"] = []

    history = st.session_state["_processing_history"]
    if msg not in history[-5:]:
        history.append(msg)

    st.caption("Podsumowanie ostatnich kroków:")
    for line in history[-5:]:
        st.text(line)

    # Przycisk anulowania
    if st.button("Anuluj przetwarzanie"):
        StateManager.request_cancel()
        st.rerun()

    # Sprawdź czy batch się skończył
    if not StateManager.is_processing():
        st.success("Przetwarzanie zakończone!")
        if st.button("Przejdź do weryfikacji"):
            st.rerun()
```

**Efekt:**
- Progress bar auto-odświeża się co 2s **bez blokowania UI**
- Użytkownik może klikać inne elementy interfejsu w trakcie przetwarzania
- Anulowanie jest dostępne w czasie rzeczywistym

---

### Faza 3: `@st.dialog` na potwierdzenie błędów (NISKI priorytet)

**Cel:** Zastąpienie warunkowego renderowania "Zatwierdź mimo błędów" modalnym oknem dialogowym.

#### 4.3.1. Dialog w `verification.py`

```python
@st.dialog("Potwierdzenie", width="small")
def confirm_force_dialog(survey_id: int, prefix: str):
    """Modalne okno potwierdzenia zatwierdzenia mimo błędów."""
    st.warning("Istnieją pola z nieprawidłowymi wartościami. Czy na pewno chcesz zatwierdzić?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Anuluj", use_container_width=True):
            st.rerun(scope="fragment")
    with col2:
        if st.button("Zatwierdź mimo błędów", type="primary", use_container_width=True):
            values = {f.name: st.session_state.get(f"{prefix}_{f.name}") for f in ALL_FIELDS}
            st.session_state[f"_submit_result_{survey_id}"] = True
            st.rerun(scope="fragment")
```

**Wywołanie w `render_navigation_fragment()`:**

```python
if submitted:
    if errors_exist:
        confirm_force_dialog(survey_id, prefix)
    else:
        st.session_state[f"_submit_result_{survey_id}"] = True
```

**Efekt:**
- Czystszy UX — modal zamiast dodatkowego przycisku
- Dialog dziedziczy zachowanie fragmentu — widgety w dialogu rerunują tylko dialog
- Konfigurowalna szerokość (`"small"`, `"medium"`, `"large"`)

---

### Faza 4: `st.form` w `verification.py` (ŚREDNI priorytet)

**Cel:** Batchowanie inputów formularza — submit dopiero po kliknięciu przycisku, nie natychmiastowo.

> **UWAGA:** `st.form` **nie jest kompatybilny** z `@st.fragment` na tej samej funkcji. Formularz musi być albo w formie, albo we fragmencie. Rekomendacja: użyć formularza **zamiast** fragmentu formularza, lub **połączyć** oba mechanizmy (formularz wewnątrz fragmentu).

#### 4.4.1. Formularz wewnątrz fragmentu

```python
@st.fragment
def render_form_fragment(survey, page_idx: int, prefix: str):
    """
    Formularz wewnątrz fragmentu — widgety batchowane w formie.
    Submit rerunuje tylko ten fragment.
    """
    show_errors = st.session_state.get(f"show_errors_{survey.id}", False)

    with st.form(key=f"form_{survey.id}_{page_idx}", clear_on_submit=False):
        fields = PAGE_MAP.get(page_idx, [])
        for f in fields:
            key = f"{prefix}_{f.name}"
            current_value = st.session_state.get(key, f.default)

            if f.kind == "select":
                st.selectbox(f.label, f.choices, index=_get_index(current_value, f.choices), key=key)
            elif f.kind == "text":
                st.text_input(f.label, value=current_value or "", key=key)
            elif f.kind == "number":
                st.number_input(f.label, min_value=f.min or 0, max_value=f.max or 100,
                              value=current_value, key=key, placeholder="Wpisz wartość")

        submitted = st.form_submit_button("Zatwierdź stronę", type="primary")

    if submitted:
        # Wartości są już w session_state dzięki key widgetów
        pass  # logika walidacji w render_navigation_fragment
```

**Kiedy stosować `st.form` zamiast `@st.fragment`:**
- Gdy chcemy **opóźnić przetwarzanie** do czasu submitu
- Gdy pola formularza **nie muszą się dynamicznie aktualizować** wzajemnie
- Gdy chcemy **unikać rerunów** przy każdej zmianie pola

**Kiedy stosować `@st.fragment` zamiast `st.form`:**
- Gdy pola **mogą się dynamicznie zmieniać** (np.選択 jednego pola wpływa na inne)
- Gdy chcemy **natychmiastowego feedbacku** (np. walidacja w czasie rzeczywistym)
- Gdy chcemy **izolować rerun** do konkretnej sekcji UI

**Rekomendacja dla AnkieterAI:** Użyć `@st.fragment` zamiast `st.form`, ponieważ pola ankiety mogą się wzajemnie influences (np. wiek wpływa na dostępność pewnych opcji).

---

### Faza 5: Toasty, badge'e, popover (NISKI priorytet — polish UX)

#### 4.5.1. `st.toast()` zamiast `st.success()` / `st.error()` w nawigacji

```python
# Zamiast:
st.success("Zapisano ankietę!")

# Użyj:
st.toast("Ankieta zapisana", icon="✅")
```

`st.toast()` generuje **tymczasowe powiadomienie** (toast), które znika po kilku sekundach. Nie zajmuje miejsca w layout i nie powoduje przesunięcia reszty UI.

**Zastosowanie:**
- Potwierdzenie zapisu ankiety → `st.toast("Zapisano", icon="✅")`
- Błąd walidacji → `st.toast("Wypełnij wszystkie pola", icon="⚠️")`
- Zmiana strony → `st.toast("Strona 2", icon="📄")`

#### 4.5.2. `st.badge()` zamiast kropek CSS

```python
# Zamiast:
st.markdown('<div class="field-err-dot"></div>', unsafe_allow_html=True)

# Użyj:
if show_errors and error:
    st.badge("!", color="red")
```

`st.badge()` generuje **mały kolorowy badge** — natywny komponent Streamlit, nie wymaga CSS.

#### 4.5.3. `st.popover()` na pomoc kontekstową pól

```python
def render_field_with_help(field_spec: FieldSpec, prefix: str, show_errors: bool):
    key = f"{prefix}_{field_spec.name}"
    current_value = st.session_state.get(key, field_spec.default)

    col1, col2, col3 = st.columns([0.04, 0.88, 0.08])

    with col1:
        if show_errors and _has_error(field_spec, current_value):
            st.badge("!", color="red")

    with col2:
        if field_spec.kind == "select":
            st.selectbox(field_spec.label, field_spec.choices,
                        index=_get_index(current_value, field_spec.choices), key=key)
        elif field_spec.kind == "text":
            st.text_input(field_spec.label, value=current_value or "", key=key)
        elif field_spec.kind == "number":
            st.number_input(field_spec.label, min_value=field_spec.min or 0,
                          max_value=field_spec.max or 100, value=current_value, key=key)

    with col3:
        with st.popover("❓", use_container_width=True):
            st.caption(f"**{field_spec.label}**")
            if field_spec.choices:
                st.caption("Dopuszczalne wartości:")
                for c in field_spec.choices:
                    st.caption(f"• {c}")
```

#### 4.5.4. `st.container(key=...)` z CSS `.st-key-*`

```python
# Zamiast:
st.markdown("<style>...</style>", unsafe_allow_html=True)

# Użyj natywne CSS classes:
with st.container(key="verification-card"):
    st.write("Treść")

# CSS via config.toml lub markdown:
st.markdown("""
<style>
.st-key-verification-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 16px;
    background: #fafafa;
}
</style>
""", unsafe_allow_html=True)
```

---

### Faza 6: Fragment `upload.py` (NISKI priorytet)

#### 4.6.1. Podgląd grupowania jako fragment

```python
@st.fragment
def render_group_preview(files):
    """Fragment podglądu grupowania — rerunuje się tylko przy zmianie plików."""
    if not files:
        return

    raw_groups, warnings = group_files_by_survey(files)
    groups = [SurveyGroup(id=i, files=group) for i, group in enumerate(raw_groups)]

    st.subheader("Podgląd grupowania")
    for g in groups:
        names = [p.name for p in g.files]
        st.write(f"**Grupa {g.id+1}** ({len(g.files)} plików): {', '.join(names)}")

    if warnings:
        for w in warnings:
            st.warning(w)

    return groups


def render():
    st.title("Wgrywanie ankiet")
    files = st.file_uploader(
        "Wybierz zdjęcia (jpg/png/webp)",
        accept_multiple_files=True,
        type=["jpg", "png", "webp"],
    )
    if not files:
        return None, False

    groups = render_group_preview(files)

    start_clicked = st.button("Rozpocznij analizę", type="primary")
    if start_clicked and groups:
        return groups, True
    return None, False
```

---

### Faza 7: `@st.cache_resource` na `AIClient` (NISKI priorytet)

```python
# ai/client.py

import streamlit as st

class AIClient:
    def __init__(self, model_name: str = None, base_url: str = None):
        from config import config
        self.model_name = model_name or config.model_name
        self.base_url = base_url or config.ollama_url
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(config.timeout_sec),
        )

    # ... reszta metod bez zmian ...


@st.cache_resource
def get_ai_client() -> AIClient:
    """Cache'uje instancję AIClient — jeden obiekt na całą sesję."""
    return AIClient()
```

**Uwaga:** `@st.cache_resource` zwraca **ten sam obiekt** — nie tworzy kopii. Dlatego:
- Bezppieczne dla klientów HTTP (connection pooling)
- Niebezpieczne dla mutable state (każda mutacja wpływa na wszystkie wywołania)

---

## 5. Porównanie PRZED/PO — mapa rerunów

### Scenariusz: Zmiana pola "Płeć" w formularzu weryfikacyjnym

#### PRZED refactorem

```
Kliknięcie w selectbox "Płeć"
  → Streamlit rerunuje CAŁY skrypt
  → app.py (linia 1-55): pełna ewaluacja
  → verification.py render():
      → inject_verification_css()         ✓ (guard: _CSS_INJECTED)
      → inject_space_shortcut()           ✓ (injectuje JS ponownie!)
      → Pobranie stanu session_state      ✓
      → Inicjalizacja 63 pól              ✓ (if key not in — skip)
      → Wyrenderowanie headera HTML       ✓ (st.markdown z base64 progress)
      → Wyrenderowanie radio buttona      ✓ (st.radio z key)
      → Lewa kolumna: get_image_base64()  ✓ (z @st.cache_data)
      → Lewa kolumna: st.markdown(img)    ✓ (ponowne wstrzyknięcie base64 HTML!)
      → Prawa kolumna: render_field() × N ✓ (WSZYSTKIE pola strony)
      → Walidacja 63 pól                  ✓ (pełna pętla po ALL_FIELDS)
      → Wyrenderowanie przycisków         ✓
  === Rerenderowanych komponentów: ~15-20 ===
```

#### PO refactorze

```
Kliknięcie w selectbox "Płeć"
  → render_form_fragment() rerun (TYLKO ten fragment)
  → render_field() dla pola "Płeć"        ✓ ( zmiana selectboxa )
  → Reszta fragmentu: przerysowanie      ✓ ( ale tylko 5-8 komponentów )
  === Rerenderowanych komponentów: 3-5 ===
  → Obraz base64: STABILNY (nie rerenderowany)
  → Header: STABILNY
  → Radio: STABILNE
  → Przyciski: STABILNE
```

---

## 6. Mapa zmian w plikach

| Plik | Zmiana | Priorytet |
|------|--------|-----------|
| `ui/pages/verification.py` | Rozdzielenie na `render()` + 3 fragmenty | 1 (WYSOKI) |
| `ui/pages/verification_fragments.py` | **NOWY** — 3 funkcje z `@st.fragment` | 1 (WYSOKI) |
| `ui/pages/processing.py` | Refaktor na `@st.fragment(run_every=2s)` + wątek tło | 2 (ŚREDNI) |
| `ui/widgets.py` | Dodanie `st.popover` i `st.badge` do `render_field()` | 3 (NISKI) |
| `ui/pages/upload.py` | Fragment podglądu grupowania | 3 (NISKI) |
| `ui/styles.py` | Usunięcie nadmiarowego CSS (zastąpienie natywnymi komponentami) | 3 (NISKI) |
| `ai/client.py` | `@st.cache_resource` na `get_ai_client()` | 3 (NISKI) |

---

## 7. Wpływ na issue #11

### Przyczyna issue #11

Issue #11 ("rozjeżdżanie UI przy interakcji z kontrolką") jest bezpośrednią konsekwencją obecnej architektury:

1. **`st.rerun()` po każdej akcji** — pełny rerun skryptu
2. **`st.columns()` w pętli** — dynamiczna liczba kolumn przy każdej zmianie strony
3. **CSS `transform: scale`** — potencjalne konflikty z przeliczaniem layoutu
4. **`st.radio` z `key`** — zmiana key powoduje rerun + przeliczenie layoutu

### Jak `@st.fragment` rozwiązuje issue #11

1. **Izolacja rerunów** — zmiana pola rerunuje TYLKO fragment formularza, nie layout strony
2. **Stabilny layout** — `st.columns()` jest renderowane raz, nie przy każdym rerunie
3. **Brak konfliktów CSS** — obraz base64 nie jest przerysowywany, więc `transform: scale` nie jest ponownie aplikowany
4. **`st.rerun(scope="fragment")`** — nawigacja może się przerysować bez wpływu na resztę

### Potwierdzenie

Po wdrożeniu Fazy 1, **issue #11 powinno zostać çöznięte**, ponieważ:
- `st.columns()` nie jest ponownie renderowane przy zmianie pola
- Obraz base64 nie jest ponownie wstrzykiwany do HTML
- Layout pozostaje stabilny niezależnie od interakcji z widgetami

---

## 8. Ryzyka i ograniczenia

### 8.1. Ograniczenia `@st.fragment`

| Ograniczenie | Wpływ na projekt | Mitigacja |
|-------------|------------------|-----------|
| Widgety tylko wewnątrz fragmentu | Nie można renderować widgetów z fragmentu do zewnętrznych kontenerów | Projekt już przestrzega tego wzorca |
| `st.sidebar` nie jest bezpośrednio obsługiwany | Nie dotyczy — sidebar nie jest używany | Wywołać fragment w `with st.sidebar:` jeśli potrzeba |
| Nie można łączyć `@st.cache_data` i `@st.fragment` na tej samej funkcji | `get_image_base64()` ma `@st.cache_data` — OK, jest poza fragmentem | Cache zostaje w osobnej funkcji, fragment go wywołuje |
| `st.rerun()` wewnątrz fragmentu → pełny rerun | Nawigacja (Poprzednia) wymaga pełnego rerunu | Użyć `st.rerun()` celowo dla nawigacji |
| Fragment nie może zwrócić wartości | Komunikacja przez `session_state` | Wzorzec `_submit_result_{id}` w session_state |

### 8.2. Ryzyka implementacyjne

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja |
|--------|-------------------|-------|-----------|
| Zmiana inicjalizacji widgetów w session_state | Średnie | Fragmenty mogą nie widzieć wartości zainicjalizowanych przez orkiestrator | Inicjalizacja PRZED wywołaniem fragmentów |
| Kompatybilność z `st.radio` (poza fragmentami) | Niskie | Radio jest poza fragmentami — OK | Radio powinno triggerować pełny rerun |
| `asyncio.run()` w processing.py | Średnie | Blockowanie UI | Wątek tło z nowym event loopem |
| CSS guard `_CSS_INJECTED` | Niskie | Fragmenty mogą injectować CSS wielokrotnie | Guard już istnieje, działa poprawnie |

---

## 9. Rekomendowany harmonogram

| # | Faza | Czas szac. | Zależności | Efekt |
|---|------|-----------|------------|-------|
| 1 | Fragmentacja verification.py | 2-3h | brak | Eliminacja issue #11 |
| 2 | Refaktor processing.py (run_every + wątek) | 1-2h | brak | Responsywny progress |
| 3 | @st.dialog na potwierdzenie błędów | 30min | Faza 1 | Czystszy UX |
| 4 | Toasty zamiast success/error | 30min | brak | Subtelniejsze powiadomienia |
| 5 | Badge + popover w render_field | 1h | Faza 1 | Lepsza informacja zwrotna |
| 6 | Fragment upload.py | 30min | brak | Izolacja podglądu |
| 7 | @st.cache_resource na AIClient | 15min | brak | Optymalizacja połączeń |

**Łączny szacowany czas:** 5-7h

---

## 10. Załączniki

### 10.1. Istniejące funkcje Streamlit 1.59.0 (nieużywane w projekcie)

| Funkcja | Dostępna od | Opis |
|---------|-------------|------|
| `@st.fragment` | v1.37 | Izolacja rerunów UI |
| `@st.fragment(parallel=True)` | v1.58 | Równoległa execucja fragmentów |
| `@st.fragment(run_every=...)` | v1.37 | Auto-rerun co interwał |
| `@st.dialog` | v1.37 | Modalne okna dialogowe |
| `st.form(enter_to_submit)` | v1.37 | Enter submituje formularz |
| `st.toast()` | v1.33 | Tymczasowe powiadomienia |
| `st.badge()` | v1.35 | Małe kolorowe etykiety |
| `st.popover()` | v1.40 | Wyskakujące kontenery |
| `st.pagination()` | v1.58 | Natywne paginowanie |
| `st.context` | v1.37 | Info o przeglądarce |
| `st.query_params` | v1.30 | URL query sync |
| `st.link_button()` | v1.30 | Przycisk-link |
| `st.menu_button()` | v1.35 | Menu dropdown |
| `st.feedback()` | v1.33 | Przyciski rating |
| `container(key=...)` + `.st-key-*` | v1.35 | CSS classes bez JS |

### 10.2. Wzorzec inicjalizacji session_state przed fragmentami

```python
def render(survey):
    # 1. Inicjalizacja session_state PRZED wywołaniem fragmentów
    for f in ALL_FIELDS:
        key = f"{prefix}_{f.name}"
        if key not in st.session_state:
            st.session_state[key] = result_dict.get(f.name, f.default)

    # 2. Wywołanie fragmentów (odczytują zainicjalizowane wartości)
    render_image_fragment(survey, page_idx)
    render_form_fragment(survey, page_idx, prefix)
    render_navigation_fragment(survey.id, errors_exist)
```
