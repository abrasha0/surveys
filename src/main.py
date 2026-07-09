import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from state_manager import StateManager
from ui_components import render_complete, render_login, render_upload, render_verification

st.set_page_config(page_title="AnkieterAI", layout="wide")
StateManager.init()

sm = StateManager()

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

survey = surveys[idx]
render_verification(survey)
