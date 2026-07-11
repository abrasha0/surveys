import streamlit as st
from domain.field_specs import PAGE_MAP, ALL_FIELDS
from ui.styles import inject_verification_css
from ui.shortcuts import inject_space_shortcut
from ui.widgets import render_field
from state.state_manager import StateManager
import logging
from PIL import Image
import base64
from io import BytesIO

logger = logging.getLogger(__name__)


@st.cache_data
def get_image_base64(path):
    """Konwertuje obraz na base64 z cache'owaniem."""
    with Image.open(path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buffer = BytesIO()
        img.save(buffer, format=img.format or "JPEG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def render(survey):
    """
    Renderuje ekran weryfikacji dla pojedynczej ankiety.
    Zwraca (submitted, values) gdzie submitted to bool,
    a values to dict z wartościami pól lub None.
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

    # Inicjalizacja widżetów – tylko jeśli nie istnieją w session_state
    for f in ALL_FIELDS:
        key = f"{prefix}_{f.name}"
        if key not in st.session_state:
            st.session_state[key] = result_dict.get(f.name, f.default)

    # --- Header z postępem ---
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

    # --- Wybór strony (st.radio – stabilny) ---
    page_names = ["Strona 1", "Strona 2", "Strona 3", "Strona 4", "Strona 5"]
    selected_page = st.radio(
        "Wybierz stronę ankiety",
        page_names,
        index=0,
        horizontal=True,
        key=f"page_select_{survey.id}",
    )
    page_idx = page_names.index(selected_page)

    # --- Główny layout: obrazek (lewo) + formularz (prawo) ---
    col_left, col_right = st.columns(2, gap="small")

    # Lewa kolumna – obrazek dla wybranej strony
    with col_left:
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

    # Prawa kolumna – formularz dla wybranej strony
    with col_right:
        show_errors = st.session_state.get(f"show_errors_{survey.id}", False)
        for f in PAGE_MAP.get(page_idx, []):
            render_field(f, prefix, show_errors)

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

    # --- Przyciski ---
    col_btns = st.columns([1, 1, 4])
    with col_btns[0]:
        if st.button("⬅ Poprzednia", key=f"prev_{survey.id}"):
            sm.previous_survey()
            st.rerun()

    with col_btns[1]:
        submitted = st.button("Zatwierdź", type="primary", key=f"submit_{survey.id}")

    force = False
    show_errors = st.session_state.get(f"show_errors_{survey.id}", False)
    if show_errors and errors_exist:
        with col_btns[2]:
            force = st.button(
                "Zatwierdź mimo błędów",
                type="secondary",
                key=f"force_{survey.id}",
            )

    # --- Obsługa zatwierdzenia ---
    if submitted:
        if errors_exist:
            st.session_state[f"show_errors_{survey.id}"] = True
            st.rerun()
        else:
            values = {f.name: st.session_state.get(f"{prefix}_{f.name}") for f in ALL_FIELDS}
            return True, values

    if force:
        values = {f.name: st.session_state.get(f"{prefix}_{f.name}") for f in ALL_FIELDS}
        return True, values

    return False, None