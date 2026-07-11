import streamlit as st
from typing import List, Any

class StateManager:
    @staticmethod
    def init():
        if "auth" not in st.session_state:
            st.session_state.auth = False
        if "surveys" not in st.session_state:
            st.session_state.surveys = []
        if "current_index" not in st.session_state:
            st.session_state.current_index = 0
        if "ai_results" not in st.session_state:
            st.session_state.ai_results = {}
        if "processing" not in st.session_state:
            st.session_state.processing = False
        if "cancel_processing" not in st.session_state:
            st.session_state.cancel_processing = False

    @staticmethod
    def is_authenticated() -> bool:
        return st.session_state.auth

    @staticmethod
    def set_authenticated(password: str) -> bool:
        from config import config
        if password == config.app_password:
            st.session_state.auth = True
            return True
        return False

    @staticmethod
    def get_surveys() -> List[Any]:
        return st.session_state.surveys

    @staticmethod
    def set_surveys(surveys: List[Any]):
        st.session_state.surveys = surveys

    @staticmethod
    def get_current_index() -> int:
        return st.session_state.current_index

    @staticmethod
    def set_current_index(idx: int):
        st.session_state.current_index = idx

    @staticmethod
    def next_survey() -> bool:
        idx = st.session_state.current_index
        if idx + 1 < len(st.session_state.surveys):
            st.session_state.current_index = idx + 1
            return True
        return False

    @staticmethod
    def previous_survey() -> bool:
        idx = st.session_state.current_index
        if idx > 0:
            st.session_state.current_index = idx - 1
            return True
        return False

    @staticmethod
    def get_ai_results() -> dict:
        return st.session_state.ai_results

    @staticmethod
    def set_ai_result(survey_id: int, result_dict: dict):
        # result_dict to już słownik z danymi (może być dict z MedicalSurvey)
        st.session_state.ai_results[survey_id] = result_dict

    @staticmethod
    def is_processing() -> bool:
        return st.session_state.processing

    @staticmethod
    def set_processing(val: bool):
        st.session_state.processing = val

    @staticmethod
    def cancel_requested() -> bool:
        return st.session_state.cancel_processing

    @staticmethod
    def request_cancel():
        st.session_state.cancel_processing = True

    @staticmethod
    def reset_cancel():
        st.session_state.cancel_processing = False

    @staticmethod
    def clear_session():
        st.session_state.auth = False
        st.session_state.surveys = []
        st.session_state.current_index = 0
        st.session_state.ai_results = {}
        st.session_state.processing = False
        st.session_state.cancel_processing = False