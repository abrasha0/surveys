1. Zarządzanie Stanem (Single Source of Truth)

- Inicjalizacja na starcie: Zawsze inicjalizuj zmienne w st.session_state na samej górze skryptu (przed renderowaniem UI), używając wzorca:

```Python
if "zmienna" not in st.session_state:
    st.session_state.zmienna = wartosc_domyslna
```

- Stan zamiast zmiennych lokalnych: Nigdy nie polegaj na zmiennych lokalnych do przechowywania danych między interakcjami. Skrypt Streamlit wykonuje się od góry do dołu przy każdej akcji – wszystko poza session_state zostanie zresetowane.

2. Obsługa Zdarzeń (Callbacks)

- Wzór Callback-First: Zamiast sprawdzać stan przycisków w głównym nurcie kodu (if st.button():), używaj argumentów on_click i on_change podpinając do nich dedykowane funkcje (tzw. mutatory stanu).

- Separacja logiki: Callbacki powinny wyłącznie aktualizować wartości w st.session_state. Renderowanie UI na podstawie tych wartości powinno odbywać się w głównej pętli. Unikniesz w ten sposób problemu "opóźnionego o jedno kliknięcie" interfejsu.

3. Optymalizacja Renderowania i Reaktywność

- Używaj @st.fragment: Zamykaj interaktywne sekcje (np. formularze, wykresy z filtrami) w funkcjach z dekoratorem @st.fragment. Dzięki temu kliknięcie w przycisk odświeży tylko ten mały fragment UI, a nie całą stronę. To klucz do płynności w SPA.

- Cachowanie operacji I/O: Zawsze używaj @st.cache_data dla zapytań do bazy i API oraz @st.cache_resource dla połączeń z bazą danych (np. silniki SQLAlchemy).

4. Architektura i Nawigacja SPA

- Zarządzanie widokami: Dla prostych SPA używaj st.session_state.current_page do przełączania widoków w jednym pliku za pomocą instrukcji match/case lub słownika funkcji renderujących.

- Modułowość UI: Dziel kod na małe funkcje renderujące, np. render_sidebar(), render_dashboard_view(), render_settings_view(). Skrypt główny (np. app.py) powinien być jedynie "dyrygentem" wywołującym te funkcje na podstawie stanu.

- Nowoczesna nawigacja (opcjonalnie): W nowszych wersjach rozważ natywne API st.navigation() i st.Page() do budowania struktury bez konieczności ręcznego pisania routera opartego na stanie.

5. Przeciwdziałanie typowym błędom (Guardrails)

- Nigdy nie zagnieżdżaj interaktywnych widżetów: Jeśli widżet (np. pole tekstowe) jest renderowany warunkowo wewnątrz if st.button():, zniknie po interakcji z nim (bo przycisk wróci do stanu False). Zawsze wiąż takie widżety ze stałym stanem z session_state.

- Klucze widżetów: Zawsze nadawaj widżetom unikalny argument key. Umożliwia to bezpośrednie powiązanie widżetu ze zmienną w st.session_state bez pisania dodatkowego kodu przypisującego.
