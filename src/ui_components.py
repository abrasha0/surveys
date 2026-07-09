import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from ai_client import AIClient
from data_handler import export_csv_path, group_files_by_survey, save_survey_to_csv
from schemas import MedicalSurvey, SurveyGroup
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
        return

    if st.button("Rozpocznij analizę", type="primary"):
        surveys = group_files_by_survey(files)
        sm = StateManager()
        sm.set_surveys(surveys)
        sm.set_current_index(0)

        progress_bar = st.progress(0, text="Przygotowywanie...")
        status_text = st.info("Przetworzono 0/0")

        def _update_progress(completed, total):
            progress_bar.progress(
                completed / total,
                text=f"Przetworzono {completed} z {total}",
            )
            status_text.info(f"Przetworzono {completed}/{total}")

        client = AIClient()
        results = asyncio.run(
            client.analyze_batch(surveys, progress_callback=_update_progress),
        )

        for r, s in zip(results, surveys):
            sm.set_ai_result(s.id, r)

        st.rerun()


def render_verification(survey: SurveyGroup):
    sm = StateManager()
    current, total = sm.get_progress()
    st.progress(current / total, text=f"Ankieta {current} z {total}")

    _space_shortcut()

    col1, col2 = st.columns(2)

    with col1:
        _render_image_viewer(survey.files)

    with col2:
        _render_form(survey)


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
    zoom = st.slider("Powiększenie", 1.0, 5.0, 1.0, key="zoom_slider")

    tabs = st.tabs([f"Strona {i + 1}" for i in range(len(files))])
    for tab, file_path in zip(tabs, files):
        with tab:
            st.image(str(file_path), width='stretch')
            if zoom != 1.0:
                st.markdown(
                    f"""
                    <style>
                    div[data-testid="stImage"] > img {{
                        transform: scale({zoom});
                        transform-origin: top left;
                    }}
                    </style>
                    """,
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


def _render_form(survey: SurveyGroup):
    sm = StateManager()
    result = sm.get_ai_results().get(survey.id)

    if not result:
        st.error("Brak wyników analizy AI dla tej ankiety")
        return

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
        st.subheader("A. Dane demograficzne")
        _rw("plec", needs_review)
        st.selectbox(
            "Płeć", ["Kobieta", "Mężczyzna"],
            index=0 if data.plec != "Mężczyzna" else 1,
            key=f"{p}_plec",
        )
        _rw("wiek", needs_review)
        st.number_input("Wiek", 18, 80, value=data.wiek, key=f"{p}_wiek")
        _rw("miejsce_zamieszkania", needs_review)
        _sb(
            "Miejsce zamieszkania",
            ["Wieś", "Miasto do 50 tys. mieszkańców", "Miasto 50-100 tys. mieszkańców", "Miasto powyżej 100 tys. mieszkańców"],
            data.miejsce_zamieszkania, f"{p}_mz",
        )
        _rw("stan_cywilny", needs_review)
        _sb(
            "Stan cywilny",
            ["Panna/kawaler", "W związku nieformalnym", "Mężatka/żonaty"],
            data.stan_cywilny, f"{p}_sc",
        )
        _rw("forma_zamieszkania", needs_review)
        _sb(
            "Forma zamieszkania w trakcie studiów",
            ["Z rodziną", "W wynajmowanym mieszkaniu/pokoju", "Własne mieszkanie",
             "We własnym mieszkaniu z partnerem", "z partnerem"],
            data.forma_zamieszkania, f"{p}_fz",
        )
        _rw("stopien_studiow", needs_review)
        _sb(
            "Stopień studiów",
            ["Studia I stopnia", "Studia II stopnia"],
            data.stopien_studiow, f"{p}_ss",
        )
        _rw("uczelnia", needs_review)
        st.text_input("Uczelnia", value=data.uczelnia, key=f"{p}_ucz")

        st.subheader("B. Aktywność zawodowa")
        _rw("praca_status", needs_review)
        _sb(
            "Czy pracujesz zawodowo w trakcie studiów?",
            ["Nie", "Tak, w zawodzie medycznym", "Tak, poza zawodem"],
            data.praca_status, f"{p}_ps",
        )
        _rw("praca_system", needs_review)
        st.text_input(
            "System pracy (jeśli dotyczy)", value=data.praca_system,
            key=f"{p}_psy",
        )
        _rw("oddzial", needs_review)
        _sb(
            "Rodzaj oddziału",
            ["", "Przychodnia", "Zabiegowym", "Zachowawczym", "Pracownia"],
            data.oddzial, f"{p}_od",
        )
        _rw("staz_pracy", needs_review)
        st.text_input(
            "Staż pracy", value=data.staz_pracy, key=f"{p}_staz",
        )

        st.subheader("C. Styl życia")
        _rw("sen_godziny", needs_review)
        _sb(
            "Średnia liczba godzin snu na dobę",
            ["Poniżej 5 godzin", "5-6 godzin", "7-8 godzin", "Powyżej 8 godzin"],
            data.sen_godziny, f"{p}_sen",
        )
        _rw("ekran_godziny", needs_review)
        _sb(
            "Godziny przed ekranem dziennie",
            ["1-3 godziny", "Powyżej 3 godzin"],
            data.ekran_godziny, f"{p}_ekr",
        )
        _rw("kofeina", needs_review)
        _sb(
            "Spożycie kofeiny",
            ["Nie", "Tak, 1-2 porcje dziennie", "Tak, 3 lub więcej porcji dziennie"],
            data.kofeina, f"{p}_kof",
        )

    with page_tabs[1]:
        st.subheader("Samopoczucie w ostatnim tygodniu (CES-D)")
        st.markdown(
            "Skala: Rzadko lub wcale (<1 dzień) / Przez niedługi czas (1-2 dni) / "
            "Czasem lub przez umiarkowany okres (3-4 dni) / Przeważnie lub cały czas (5-7 dni)"
        )
        for fn, label in _CESD_FIELDS:
            _rw(fn, needs_review)
            _sb(
                label,
                _CESD_SKALA,
                getattr(data, fn), f"{p}_{fn}",
            )

    with page_tabs[2]:
        st.subheader("Ateńska skala bezsenności")
        _rw("zasypianie", needs_review)
        _sb(
            "Zasypianie",
            ["szybkie", "nieznacznie opóźnione", "opóźnione",
             "bardzo opóźnione lub bezsenność przez całą noc"],
            data.zasypianie, f"{p}_zas",
        )
        _rw("budzenie_noc", needs_review)
        _sb(
            "Budzenie się podczas nocy",
            ["nie występuje", "sporadycznie", "często",
             "bardzo często lub bezsenność przez całą noc"],
            data.budzenie_noc, f"{p}_bn",
        )
        _rw("budzenie_rano", needs_review)
        _sb(
            "Budzenie się rano wcześniej niż planowano",
            ["o zamierzonej godzinie", "nieznacznie wcześniej", "znacznie wcześniej",
             "dużo wcześniej lub bezsenność przez całą noc"],
            data.budzenie_rano, f"{p}_br",
        )
        _rw("czas_snu", needs_review)
        _sb(
            "Całkowity czas snu",
            ["wystarczający", "nieznacznie niewystarczający",
             "wyraźnie niewystarczający",
             "całkowicie niewystarczający lub bezsenność przez całą noc"],
            data.czas_snu, f"{p}_cs",
        )
        _rw("jakosc_snu", needs_review)
        _sb(
            "Jakość snu",
            ["satysfakcjonująca", "nieznacznie niesatysfakcjonująca",
             "wyraźnie niesatysfakcjonująca", "całkowicie niesatysfakcjonująca"],
            data.jakosc_snu, f"{p}_js",
        )
        _rw("samopoczucie", needs_review)
        _sb(
            "Samopoczucie następnego dnia",
            ["dobre", "nieznacznie gorsze", "wyraźnie gorsze"],
            data.samopoczucie, f"{p}_sam",
        )
        _rw("sprawnosc", needs_review)
        _sb(
            "Sprawność psychiczna i fizyczna następnego dnia",
            ["niezaburzona", "nieznacznie zaburzona", "wyraźnie zaburzona"],
            data.sprawnosc, f"{p}_sp",
        )
        _rw("sennosc", needs_review)
        _sb(
            "Senność w ciągu dnia",
            ["nie zdarza się", "nieznaczna", "wyraźna", "bardzo nasilona"],
            data.sennosc, f"{p}_sen2",
        )

    with page_tabs[3]:
        st.subheader("Skala zmęczenia MFIS (1-15)")
        st.markdown("Skala: Nigdy / Rzadko / Czasami / Często / Prawie zawsze")
        for fn, label in _MFIS_1_15:
            _rw(fn, needs_review)
            _sb(
                label,
                _OBJAWY_SKALA,
                getattr(data, fn), f"{p}_{fn}",
            )

    with page_tabs[4]:
        st.subheader("Skala zmęczenia MFIS (16-21)")
        st.markdown("Skala: Nigdy / Rzadko / Czasami / Często / Prawie zawsze")
        for fn, label in _MFIS_16_21:
            _rw(fn, needs_review)
            _sb(
                label,
                _OBJAWY_SKALA,
                getattr(data, fn), f"{p}_{fn}",
            )

        st.subheader("Stan zdrowia")
        _rw("anemia", needs_review)
        _sb("Czy stwierdzono anemię?", ["Tak", "Nie"], data.anemia, f"{p}_an")
        _rw("problemy_tarczyca", needs_review)
        _sb(
            "Czy stwierdzono problemy z tarczycą?", ["Tak", "Nie"],
            data.problemy_tarczyca, f"{p}_tar",
        )
        _rw("jaka_tarczyca", needs_review)
        st.text_input(
            "Jakie problemy z tarczycą?", value=data.jaka_tarczyca,
            key=f"{p}_jt",
        )
        _rw("inne_choroby", needs_review)
        st.text_input(
            "Inne choroby", value=data.inne_choroby, key=f"{p}_ich",
        )

    # ── global submit button ─────────────────────────────────────
    submitted = st.button("Zatwierdź i Następna (Spacja)", type="primary", key=f"submit_{survey.id}")

    if submitted:
        kwargs = {}
        for fn in _ALL_FIELD_KEYS:
            widget_key = f"{p}_{fn}"
            val = st.session_state.get(widget_key)
            kwargs[fn] = val
        kwargs["needs_review"] = needs_review
        updated = MedicalSurvey(**kwargs)
        save_survey_to_csv(updated, export_csv_path())

        if sm.next_survey():
            st.rerun()
        else:
            st.rerun()


def _rw(field_name: str, needs_review: dict):
    if needs_review.get(field_name):
        st.error(f"Pole — niska pewność odczytu")


def _sb(label: str, options: list, current, key: str):
    index = options.index(current) if current in options else 0
    return st.selectbox(label, options, index=index, key=key)


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
