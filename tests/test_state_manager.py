import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from state.state_manager import StateManager

class TestStateManager:
    def test_init_creates_session_key(self):
        StateManager.init()
        import streamlit as st
        assert "auth" in st.session_state

    def test_is_authenticated_returns_false_initially(self):
        StateManager.init()
        assert StateManager.is_authenticated() is False

    def test_set_authenticated_with_wrong_password(self):
        StateManager.init()
        assert StateManager.set_authenticated("wrong") is False

    def test_set_authenticated_with_correct_password(self):
        StateManager.init()
        from config import config
        assert StateManager.set_authenticated(config.app["password"]) is True

    def test_current_index_defaults_to_zero(self):
        StateManager.init()
        assert StateManager.get_current_index() == 0

    def test_set_current_index(self):
        StateManager.init()
        StateManager.set_current_index(3)
        assert StateManager.get_current_index() == 3

    def test_get_surveys_returns_empty_list(self):
        StateManager.init()
        assert StateManager.get_surveys() == []

    def test_set_surveys(self):
        StateManager.init()
        surveys = ["a", "b", "c"]
        StateManager.set_surveys(surveys)
        assert StateManager.get_surveys() == surveys

    def test_get_current_survey_returns_none_when_no_surveys(self):
        StateManager.init()
        assert StateManager.get_current_survey() is None

    def test_get_current_survey_returns_first(self):
        StateManager.init()
        StateManager.set_surveys(["s1", "s2"])
        StateManager.set_current_index(0)
        assert StateManager.get_current_survey() == "s1"

    def test_next_survey_returns_false_at_end(self):
        StateManager.init()
        StateManager.set_surveys(["s1"])
        StateManager.set_current_index(0)
        assert StateManager.next_survey() is False

    def test_next_survey_increments(self):
        StateManager.init()
        StateManager.set_surveys(["s1", "s2"])
        StateManager.set_current_index(0)
        assert StateManager.next_survey() is True
        assert StateManager.get_current_index() == 1

    def test_set_and_get_ai_results(self):
        StateManager.init()
        StateManager.set_ai_result(1, {"c": 0.95})
        assert StateManager.get_ai_results()[1] == {"c": 0.95}

    def test_get_progress(self):
        StateManager.init()
        StateManager.set_surveys(["s1", "s2", "s3"])
        StateManager.set_current_index(1)
        c, t = StateManager.get_progress()
        assert c == 2 and t == 3

    def test_clear_session_resets_state(self):
        StateManager.init()
        from config import config
        StateManager.set_authenticated(config.app["password"])
        StateManager.clear_session()
        assert StateManager.is_authenticated() is False
        assert StateManager.get_current_index() == 0
        assert StateManager.get_surveys() == []
