import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from state_manager import StateManager

st.set_page_config(page_title="AnkieterAI", layout="wide")
StateManager.init()

sm = StateManager()


def render_login():
    st.title("AnkieterAI")
    st.markdown("Zautomatyzowany system wprowadzania ankiet papierowych")
    password = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if sm.set_authenticated(password):
            st.rerun()
        else:
            st.error("Nieprawidłowe hasło")


def render_upload():
    st.title("Wgrywanie ankiet")
    st.info("Ekran wgrywania plików — implementacja w fazie 4")
    if st.button("Resetuj sesję"):
        sm.clear_session()
        st.rerun()


def render_verification():
    survey = sm.get_current_survey()
    current, total = sm.get_progress()
    st.progress(current / total, text=f"Ankieta {current} z {total}")
    st.info("Ekran weryfikacji — implementacja w fazie 4–6")
    if st.button("Zatwierdź i Następna"):
        if sm.next_survey():
            st.rerun()
        else:
            st.rerun()


def render_complete():
    st.balloons()
    st.success("Wszystkie ankiety przetworzone!")
    if st.button("Nowa sesja"):
        sm.clear_session()
        st.rerun()


if not sm.is_authenticated():
    render_login()
    st.stop()

surveys = sm.get_surveys()
if not surveys:
    render_upload()
    st.stop()

idx = sm.get_current_index()
if idx >= len(surveys):
    render_complete()
    st.stop()

render_verification()
