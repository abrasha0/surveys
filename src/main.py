import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from ai_client import AIClient
from data_handler import export_csv_path, group_files_by_survey, save_survey_to_csv
from schemas import MedicalSurvey
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
    files, start_clicked = render_upload()
    if start_clicked and files:
        surveys = group_files_by_survey(files)
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
    st.stop()

idx = sm.get_current_index()
if idx >= len(surveys):
    render_complete()
    st.stop()

survey = surveys[idx]
submitted, form_data = render_verification(survey)
if submitted and form_data:
    updated = MedicalSurvey(**form_data)
    save_survey_to_csv(updated, export_csv_path())
    sm.next_survey()
    st.rerun()
