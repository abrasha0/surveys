import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

_SESSION_KEY = "ankieter"


class StateManager:

    @staticmethod
    def init():
        if _SESSION_KEY not in st.session_state:
            st.session_state[_SESSION_KEY] = {
                "authenticated": False,
                "current_index": 0,
                "surveys": [],
                "ai_results": {},
            }

    @staticmethod
    def is_authenticated() -> bool:
        return st.session_state[_SESSION_KEY].get("authenticated", False)

    @staticmethod
    def set_authenticated(password: str) -> bool:
        from config import config

        ok = password == config.app_password
        if ok:
            st.session_state[_SESSION_KEY]["authenticated"] = True
        return ok

    @staticmethod
    def get_current_index() -> int:
        return st.session_state[_SESSION_KEY].get("current_index", 0)

    @staticmethod
    def set_current_index(i: int):
        st.session_state[_SESSION_KEY]["current_index"] = i

    @staticmethod
    def get_surveys():
        return st.session_state[_SESSION_KEY].get("surveys", [])

    @staticmethod
    def set_surveys(surveys: list):
        st.session_state[_SESSION_KEY]["surveys"] = surveys

    @staticmethod
    def get_current_survey():
        surveys = StateManager.get_surveys()
        idx = StateManager.get_current_index()
        if 0 <= idx < len(surveys):
            return surveys[idx]
        return None

    @staticmethod
    def next_survey() -> bool:
        idx = StateManager.get_current_index()
        surveys = StateManager.get_surveys()
        if idx + 1 < len(surveys):
            StateManager.set_current_index(idx + 1)
            return True
        return False

    @staticmethod
    def set_ai_result(survey_id: int, result):
        st.session_state[_SESSION_KEY]["ai_results"][survey_id] = result

    @staticmethod
    def get_ai_results() -> dict:
        return st.session_state[_SESSION_KEY].get("ai_results", {})

    @staticmethod
    def get_progress() -> tuple:
        idx = StateManager.get_current_index()
        total = len(StateManager.get_surveys())
        return idx + 1, total

    @staticmethod
    def clear_session():
        st.session_state[_SESSION_KEY] = {
            "authenticated": False,
            "current_index": 0,
            "surveys": [],
            "ai_results": {},
        }
