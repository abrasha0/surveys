import streamlit as st

st.set_page_config(
    page_title="surveyAI",
    layout="wide",
)

import logging
from state.state_manager import StateManager
from ui.pages import login, upload, processing, verification, complete
from data_handler import load_cache, export_csv_path
from logger import setup_logging
from config import config
from ui.styles import inject_global_css

setup_logging(log_file=config.log_file, level=getattr(logging, config.log_level.upper(), logging.DEBUG))
StateManager.init()
inject_global_css()

cached = load_cache()
if cached:
    st.session_state["ai_results"] = cached

if not StateManager.is_authenticated():
    login.render()
    st.stop()

surveys = StateManager.get_surveys()
if not surveys:
    groups, start = upload.render()
    if start and groups:
        StateManager.set_surveys(groups)
        StateManager.set_current_index(0)
        StateManager.set_processing(True)
        st.rerun()
    st.stop()

if StateManager.is_processing():
    processing.render()
    st.stop()

idx = StateManager.get_current_index()
if idx >= len(surveys):
    complete.render()
    st.stop()

survey = surveys[idx]
submitted, values = verification.render(survey)
if submitted and values:
    from domain.csv_export import save_survey_to_csv
    from domain.schemas import MedicalSurvey
    survey_data = MedicalSurvey(**values)
    save_survey_to_csv(survey_data, export_csv_path())
    StateManager.next_survey()
    st.rerun()