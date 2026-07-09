import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from ai_client import AIClient, ProcessingStatus
from config import config
from data_handler import export_csv_path, group_files_by_survey, save_survey_to_csv
from logger import setup_logging
from schemas import MedicalSurvey
from state_manager import StateManager
from ui_components import render_complete, render_login, render_upload, render_verification

logger = logging.getLogger(__name__)


def _inject_global_css():
    st.markdown(
        """
<style>
    header[data-testid="stHeader"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stAppDeployButton { display: none; }
    .stMainBlockContainer, .main .block-container {
        padding-top: 0.25rem !important;
        padding-bottom: 0 !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    .stApp { overflow: hidden; }
    .mini-spinner {
        display: inline-block;
        width: 14px;
        height: 14px;
        border: 2.5px solid rgba(49, 51, 63, 0.12);
        border-top-color: #ff4b4b;
        border-radius: 50%;
        animation: mini-spin 0.7s linear infinite;
        flex-shrink: 0;
    }
    @keyframes mini-spin {
        to { transform: rotate(360deg); }
    }
</style>
""",
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="AnkieterAI", layout="wide")
setup_logging(log_file=config.log_file, level=getattr(logging, config.log_level.upper(), logging.DEBUG))
StateManager.init()
_inject_global_css()
logger.info("Application started")

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

        progress_placeholder = st.empty()

        def _update_progress(status: ProcessingStatus):
            pct = status.survey_idx / max(status.total_surveys, 1)
            with progress_placeholder.container():
                st.progress(pct, text=f"Ankieta {status.survey_idx + 1} z {status.total_surveys}")
                if status.status == "processing_page":
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:8px;min-height:24px;font-size:0.9rem">'
                        f'<span class="mini-spinner"></span>'
                        f'<span>{status.message}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                elif status.status == "retrying":
                    extra = status.extra or {}
                    attempt = extra.get("attempt", 1)
                    st.warning(f"{status.message}")
                elif status.status == "page_error":
                    st.error(status.message)
                elif status.status == "survey_done":
                    extra = status.extra or {}
                    elapsed = extra.get("elapsed_s", "")
                    msg = status.message
                    if elapsed:
                        msg += f" ({elapsed}s)"
                    st.success(msg)
                elif status.status == "batch_done":
                    st.success(status.message)

        logger.info("Upload: %d file(s), grouped into %d survey(s)", len(files), len(surveys))

        client = AIClient()
        results = asyncio.run(
            client.analyze_batch(surveys, progress_callback=_update_progress),
        )

        for r, s in zip(results, surveys):
            sm.set_ai_result(s.id, r)

        logger.info("Batch finished, %d result(s) stored, rerendering", len(results))
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
