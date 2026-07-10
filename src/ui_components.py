import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

import base64
from io import BytesIO
from PIL import Image

from data_handler import export_csv_path
from schemas import SurveyGroup
from state_manager import StateManager


def render_login():
    st.title("AnkieterAI")
    st.markdown("Zautomatyzowany system wprowadzania ankiet papierowych")
    password = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        sm = StateManager()
        if sm.set_authenticated(password):
            st.rerun()
        else:
            st.error("Nieprawidłowe hasło")


def render_upload():
    st.title("Wgrywanie ankiet")
    files = st.file_uploader(
        "Wybierz zdjęcia (jpg/png/webp)",
        accept_multiple_files=True,
        type=["jpg", "png", "webp"],
    )
    if not files:
        return None, False
    start_clicked = st.button("Rozpocznij analizę", type="primary")
    return list(files), start_clicked


def render_verification(survey: SurveyGroup):
    sm = StateManager()
    current, total = sm.get_progress()

    pct = current / total
    st.markdown(
        f'<div class="header-row">'
        f'<span class="header-label">Ankieta {current} z {total}</span>'
        f'<div class="header-progress">'
        f'<div class="header-progress-fill" style="width:{pct*100}%"></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    _space_shortcut()
    _inject_verification_css()

    col1, col2 = st.columns(2, gap="small")

    with col1:
        _render_image_viewer(survey.files)

    result = (False, None)
    with col2:
        result = _render_form(survey)

    return result


def _space_shortcut():
    st.markdown(
        """
        <script>
        document.addEventListener('keydown', function(e) {
            if (e.key === ' ' && e.target === document.body) {
                e.preventDefault();
                var btn = document.querySelector('button[data-testid="baseButton-primary"]');
                if (btn) btn.click();
            }
        });
        </script>
        """,
        unsafe_allow_html=True,
    )


def _render_image_viewer(files: list[Path]):
    tabs = st.tabs([f"Strona {i + 1}" for i in range(len(files))])
    for tab, file_path in zip(tabs, files):
        with tab:
            data_url = _image_to_data_url(file_path)
            st.markdown(
                f'<div class="image-wrap"><img src="{data_url}" /></div>',
                unsafe_allow_html=True,
            )


# ─── Field definitions per page ────────────────────────────────────

_MFIS_1_15 = [
    ("objaw_mniej_uwazna", "Czułam/em się mniej uważna/y"),
    ("objaw_trudno_skupic", "Trudno było mi się skupić przez dłuższą chwilę"),
    ("objaw_trudno_myslec", "Trudno było mi myśleć logicznie"),
    ("objaw_niezdarna", "Byłam/em niezdarna/y"),
    ("objaw_zapominalska", "Byłam/em zapominalska/ski"),
    ("objaw_wyznaczac_tempo", "Musiałam/em sama/sam wyznaczać sobie indywidualne tempo"),
    ("objaw_zmotywowac_fizycznie", "Trudno było mi się zmotywować do aktywności fizycznej"),
    ("objaw_zmotywowac_spotkania", "Trudno było mi się zmotywować do wyjścia z domu"),
    ("objaw_nie_zdolna_poza_domem", "Nie czułam/em się zdolna/y do robienia czegokolwiek poza domem"),
    ("objaw_wysilek_fizyczny", "Problem z utrzymaniem wysiłku fizycznego przez dłuższy czas"),
    ("objaw_trudnosci_decyzyjne", "Trudności w podejmowaniu decyzji"),
    ("objaw_zmusic_do_myslenia", "Trudno było mi się zmusić do zrobienia czegokolwiek co wymagało myślenia"),
    ("objaw_miesnie_z_waty", "Poczucie, że mięśnie są jak \"zrobione z waty\""),
    ("objaw_dyskomfort_fizyczny", "Odczuwałam/em dyskomfort fizyczny"),
    ("objaw_ukonczenie_myslenie", "Problem z ukończeniem zadania bo wymagało myślenia"),
]

_MFIS_16_21 = [
    ("objaw_uporzadkowanie_mysli", "Trudności w uporządkowaniu myśli podczas pracy"),
    ("objaw_ukonczenie_wysilek", "Problem z ukończeniem zadania bo wymagało wysiłku fizycznego"),
    ("objaw_myslenie_spowolnione", "Wrażenie, że myślenie uległo spowolnieniu"),
    ("objaw_problemy_koncentracja", "Problemy z koncentracją"),
    ("objaw_ograniczyc_aktywnosc", "Musiałam/em ograniczyć aktywność fizyczną"),
    ("objaw_czesciej_odpoczywac", "Musiałam/em odpoczywać częściej i dłużej"),
]

_CESD_FIELDS = [
    ("cesd_przeszkadzaly", "Przeszkadzały mi rzeczy, które zazwyczaj mi nie przeszkadzają"),
    ("cesd_brak_apetytu", "Nie miałem ochoty jeść; mój apetyt był słaby"),
    ("cesd_chandra", "Nie mogłem otrząsnąć się z chandry"),
    ("cesd_tak_samo_dobry", "Czułem, że jestem tak samo dobry jak inni ludzie"),
    ("cesd_ciezko_skoncentrowac", "Było mi ciężko skoncentrować się na tym co robię"),
    ("cesd_przygnebiony", "Czułem się przygnębiony"),
    ("cesd_wysilek", "Czułem, że cokolwiek robię, wymaga wysiłku"),
    ("cesd_optymistycznie", "Optymistycznie patrzyłem w przyszłość"),
    ("cesd_zycie_porazka", "Miałem poczucie, że moje życie to porażka"),
    ("cesd_strach", "Czułem strach"),
    ("cesd_sen_niespokojny", "Mój sen był niespokojny"),
    ("cesd_szczesliwy", "Byłem szczęśliwy"),
    ("cesd_mowil_mniej", "Mówiłem mniej niż zwykle"),
    ("cesd_samotny", "Czułem się samotny"),
    ("cesd_ludzie_nieprzyjazni", "Ludzie byli nastawieni nieprzyjaźnie"),
    ("cesd_radosci", "Czerpałem radość z życia"),
    ("cesd_placzu", "Miałem napady płaczu"),
    ("cesd_smutno", "Było mi smutno"),
    ("cesd_ludzie_nie_lubia", "Czułem, że ludzie mnie nie lubią"),
    ("cesd_nic_nie_zabrac", "Nie byłem w stanie się za nic zabrać"),
]

# ─── Page definitions: (page_name, list_of_field_tuples_or_section_builder) ───

_OBJAWY_SKALA = ["Nigdy", "Rzadko", "Czasami", "Często", "Prawie zawsze"]
_CESD_SKALA = [
    "Rzadko lub wcale (mniej niż 1 dzień)",
    "Przez niedługi czas (1-2 dni)",
    "Czasem lub przez umiarkowany okres (3-4 dni)",
    "Przeważnie lub cały czas (5-7 dni)",
]

# ─── Compact field definitions for 2-column grid ─────────────────

_PAGE1_FIELDS = [
    ("plec", "1. Płeć", "select", ["Kobieta", "Mężczyzna"]),
    ("wiek", "2. Wiek", "number", 18, 80),
    ("miejsce_zamieszkania", "3. Miejsce zamieszkania", "select",
     ["Wieś", "Miasto do 50 tys. mieszkańców", "Miasto 50-100 tys. mieszkańców",
      "Miasto powyżej 100 tys. mieszkańców"]),
    ("stan_cywilny", "4. Stan cywilny", "select",
     ["Panna/kawaler", "W związku nieformalnym", "Mężatka/żonaty"]),
    ("forma_zamieszkania", "5. Forma zamieszkania", "select",
     ["Z rodziną", "W wynajmowanym mieszkaniu/pokoju", "Własne mieszkanie",
      "We własnym mieszkaniu z partnerem", "z partnerem"]),
    ("stopien_studiow", "6. Stopień studiów", "select",
     ["Studia I stopnia", "Studia II stopnia"]),
    ("uczelnia", "7. Uczelnia", "text"),
    ("praca_status", "8. Praca w trakcie studiów?", "select",
     ["Nie", "Tak, w zawodzie medycznym", "Tak, poza zawodem"]),
    ("praca_system", "9. System pracy", "text"),
    ("oddzial", "10. Rodzaj oddziału", "select",
     ["", "Przychodnia", "Zabiegowym", "Zachowawczym", "Pracownia"]),
    ("staz_pracy", "11. Staż pracy", "text"),
    ("sen_godziny", "12. Średnia liczba godzin snu", "select",
     ["Poniżej 5 godzin", "5-6 godzin", "7-8 godzin", "Powyżej 8 godzin"]),
    ("ekran_godziny", "13. Godziny przed ekranem", "select",
     ["1-3 godziny", "Powyżej 3 godzin"]),
    ("kofeina", "14. Spożycie kofeiny", "select",
     ["Nie", "Tak, 1-2 porcje dziennie", "Tak, 3 lub więcej porcji dziennie"]),
]

_ATHENS_FIELDS = [
    ("zasypianie", "Zasypianie", "select",
     ["szybkie", "nieznacznie opóźnione", "opóźnione",
      "bardzo opóźnione lub bezsenność przez całą noc"]),
    ("budzenie_noc", "Budzenie się w nocy", "select",
     ["nie występuje", "sporadycznie", "często",
      "bardzo często lub bezsenność przez całą noc"]),
    ("budzenie_rano", "Wcześniejsze budzenie", "select",
     ["o zamierzonej godzinie", "nieznacznie wcześniej", "znacznie wcześniej",
      "dużo wcześniej lub bezsenność przez całą noc"]),
    ("czas_snu", "Całkowity czas snu", "select",
     ["wystarczający", "nieznacznie niewystarczający",
      "wyraźnie niewystarczający",
      "całkowicie niewystarczający lub bezsenność przez całą noc"]),
    ("jakosc_snu", "Jakość snu", "select",
     ["satysfakcjonująca", "nieznacznie niesatysfakcjonująca",
      "wyraźnie niesatysfakcjonująca", "całkowicie niesatysfakcjonująca"]),
    ("samopoczucie", "Samopoczucie nast. dnia", "select",
     ["dobre", "nieznacznie gorsze", "wyraźnie gorsze"]),
    ("sprawnosc", "Sprawność nast. dnia", "select",
     ["niezaburzona", "nieznacznie zaburzona", "wyraźnie zaburzona"]),
    ("sennosc", "Senność w ciągu dnia", "select",
     ["nie zdarza się", "nieznaczna", "wyraźna", "bardzo nasilona"]),
]

_HEALTH_FIELDS = [
    ("anemia", "Czy stwierdzono anemię?", "select", ["Tak", "Nie"]),
    ("problemy_tarczyca", "Problemy z tarczycą?", "select", ["Tak", "Nie"]),
    ("jaka_tarczyca", "Jakie problemy z tarczycą?", "text"),
    ("inne_choroby", "Inne choroby", "text"),
]


# ─── Helpers ──────────────────────────────────────────────────────

def _image_to_data_url(path: Path) -> str:
    with Image.open(path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buffer = BytesIO()
        img.save(buffer, format=img.format or "JPEG")
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"


def _inject_verification_css():
    st.markdown(
        """
<style>
label { font-size: 0.8rem !important; margin-bottom: 0 !important; padding-bottom: 0 !important; }
div[data-testid="stSelectbox"],
div[data-testid="stTextInput"],
div[data-testid="stNumberInput"] { padding-bottom: 2px !important; padding-top: 0 !important; }
div[data-testid="stSelectbox"] > div,
div[data-testid="stTextInput"] > div,
div[data-testid="stNumberInput"] > div { min-height: 26px !important; }
input { min-height: 26px !important; font-size: 0.8rem !important; }
div[data-baseweb="select"] span { font-size: 0.8rem !important; }
button[data-testid="baseButton-primary"] { margin-top: 4px; font-size: 0.85rem; padding: 0.25rem 1rem; }
.header-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.header-label { font-size: 0.85rem; white-space: nowrap; }
.header-progress { flex: 0 1 140px; height: 6px; background: #e0e0e0; border-radius: 3px; overflow: hidden; }
.header-progress-fill { height: 100%; background: #1E88E5; border-radius: 3px; }
div[data-testid="stProgress"] { margin-bottom: 0 !important; padding: 0 !important; }
div[data-testid="stProgress"] > div { height: 6px !important; }
.image-wrap { height: calc(100vh - 150px) !important; width: 100% !important; }
.image-wrap img { object-fit: contain !important; width: 100% !important; height: 100% !important; }
div[data-testid="column"]:has(.image-wrap) { height: calc(100vh - 80px) !important; overflow: hidden !important; }
.stMainBlockContainer > [data-testid="stVerticalBlock"] { row-gap: 0 !important; gap: 0 !important; }
div[data-testid="column"]:has(.image-wrap) div[data-testid="stVerticalBlock"] { row-gap: 0 !important; gap: 0 !important; }
div[data-testid="column"]:has(.image-wrap) [data-testid="stTabs"] { margin-top: 4px !important; }
</style>
""",
        unsafe_allow_html=True,
    )


def _render_fields_grid(fields, needs_review, data, prefix, columns=2):
    for i in range(0, len(fields), columns):
        cols = st.columns(columns)
        for j, field_def in enumerate(fields[i : i + columns]):
            with cols[j]:
                _render_single_field(field_def, needs_review, data, prefix)


def _render_single_field(field_def, needs_review, data, prefix):
    fn = field_def[0]
    label = field_def[1]
    if needs_review.get(fn):
        label = f"\u26a0\ufe0f {label}"

    kind = field_def[2]
    if kind == "select":
        options = field_def[3]
        current = getattr(data, fn)
        idx = options.index(current) if current in options else 0
        st.selectbox(label, options, index=idx, key=f"{prefix}_{fn}")
    elif kind == "text":
        st.text_input(label, value=getattr(data, fn), key=f"{prefix}_{fn}")
    elif kind == "number":
        lo, hi = field_def[3], field_def[4]
        st.number_input(label, lo, hi, value=getattr(data, fn), key=f"{prefix}_{fn}")


def _render_form(survey: SurveyGroup):
    sm = StateManager()
    result = sm.get_ai_results().get(survey.id)

    if not result:
        st.error("Brak wyników analizy AI dla tej ankiety")
        return False, None

    data = result.validated_data
    needs_review = data.needs_review
    p = f"f_{survey.id}"

    # ── keys used in this survey form ────────
    _ALL_FIELD_KEYS = [
        "plec","wiek","miejsce_zamieszkania","stan_cywilny","forma_zamieszkania",
        "stopien_studiow","uczelnia",
        "praca_status","praca_system","oddzial","staz_pracy",
        "sen_godziny","ekran_godziny","kofeina",
        "anemia","problemy_tarczyca","jaka_tarczyca","inne_choroby",
        "zasypianie","budzenie_noc","budzenie_rano","czas_snu","jakosc_snu",
        "samopoczucie","sprawnosc","sennosc",
    ]
    _ALL_FIELD_KEYS += [fn for fn, _ in _MFIS_1_15]
    _ALL_FIELD_KEYS += [fn for fn, _ in _MFIS_16_21]
    _ALL_FIELD_KEYS += [fn for fn, _ in _CESD_FIELDS]

    # ── render each page inside tabs ────────
    page_tabs = st.tabs(["Strona 1", "Strona 2", "Strona 3", "Strona 4", "Strona 5"])

    with page_tabs[0]:
        col_a, col_b = st.columns(2)
        with col_a:
            for field_def in _PAGE1_FIELDS[:7]:
                _render_single_field(field_def, needs_review, data, p)
        with col_b:
            for field_def in _PAGE1_FIELDS[7:]:
                _render_single_field(field_def, needs_review, data, p)

    with page_tabs[1]:
        st.subheader("Samopoczucie (CES-D)")
        st.markdown(
            '<div style="font-size:0.75rem;margin-bottom:4px">Skala: &lt;1d / 1-2d / 3-4d / 5-7d</div>',
            unsafe_allow_html=True,
        )
        cesd_defs = [(fn, label, "select", _CESD_SKALA) for fn, label in _CESD_FIELDS]
        _render_fields_grid(cesd_defs, needs_review, data, p)

    with page_tabs[2]:
        st.subheader("Ateńska skala bezsenności")
        _render_fields_grid(_ATHENS_FIELDS, needs_review, data, p)

    with page_tabs[3]:
        st.subheader("Zmęczenie MFIS (1-15)")
        st.markdown(
            '<div style="font-size:0.75rem;margin-bottom:4px">Skala: Nigdy / Rzadko / Czasami / Często / Prawie zawsze</div>',
            unsafe_allow_html=True,
        )
        mfis_defs = [(fn, label, "select", _OBJAWY_SKALA) for fn, label in _MFIS_1_15]
        _render_fields_grid(mfis_defs, needs_review, data, p)

    with page_tabs[4]:
        st.subheader("Zmęczenie MFIS (16-21)")
        st.markdown(
            '<div style="font-size:0.75rem;margin-bottom:4px">Skala: Nigdy / Rzadko / Czasami / Często / Prawie zawsze</div>',
            unsafe_allow_html=True,
        )
        mfis2_defs = [(fn, label, "select", _OBJAWY_SKALA) for fn, label in _MFIS_16_21]
        _render_fields_grid(mfis2_defs, needs_review, data, p)
        st.subheader("Stan zdrowia")
        _render_fields_grid(_HEALTH_FIELDS, needs_review, data, p)

    # ── global submit button ─────────────────────────────────────
    submitted = st.button("Zatwierdź i Następna (Spacja)", type="primary", key=f"submit_{survey.id}")

    if submitted:
        kwargs = {}
        for fn in _ALL_FIELD_KEYS:
            widget_key = f"{p}_{fn}"
            val = st.session_state.get(widget_key)
            kwargs[fn] = val
        kwargs["needs_review"] = needs_review
        return submitted, kwargs

    return submitted, None


def render_complete():
    st.balloons()
    st.success("Wszystkie ankiety przetworzone!")

    csv_path = Path(export_csv_path())
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            csv_content = f.read()
        st.download_button(
            "Pobierz CSV",
            data=csv_content,
            file_name="wyniki.csv",
            mime="text/csv",
        )

    if st.button("Nowa sesja"):
        StateManager().clear_session()
        st.rerun()