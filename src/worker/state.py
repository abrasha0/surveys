from dataclasses import dataclass, field
from pathlib import Path
import time

from config import config


@dataclass
class SurveyState:
    id: int
    files: list[Path]
    status: str = "queued"
    result: dict | None = None
    error_message: str | None = None


@dataclass
class GlobalState:
    total: int = 0
    processed: int = 0
    errors: int = 0
    current_survey_id: int | None = None
    current_page: int | None = None
    current_stage: str | None = None
    eta_seconds: float | None = None
    is_running: bool = False
    started_at: float | None = None


class ProcessingState:
    def __init__(self):
        self.surveys: list[SurveyState] = []
        self.global_state = GlobalState()
        self.results: dict[int, dict] = {}
        self.page_times: list[float] = []
        self._eta_rolling_window: int = config.processing["eta_rolling_window"]

    def init_from_surveys(self, survey_groups: list[list[Path]]):
        self.surveys = [
            SurveyState(id=idx, files=group)
            for idx, group in enumerate(survey_groups)
        ]
        self.global_state.total = len(self.surveys)
        self.global_state.processed = 0
        self.global_state.errors = 0
        self.global_state.is_running = True
        self.global_state.started_at = time.time()
        self.page_times.clear()

    def get_survey_state(self, survey_id: int) -> SurveyState | None:
        if 0 <= survey_id < len(self.surveys):
            return self.surveys[survey_id]
        return None

    def set_survey_status(self, survey_id: int, status: str,
                          result: dict | None = None, error: str | None = None):
        survey = self.surveys[survey_id]
        survey.status = status
        if result is not None:
            survey.result = result
            self.results[survey_id] = result
        if error is not None:
            survey.error_message = error
        if status in ("ready", "error"):
            self.global_state.processed += 1
            if status == "error":
                self.global_state.errors += 1

    def update_global(self, survey_id: int, page: int | None, stage: str | None):
        self.global_state.current_survey_id = survey_id
        self.global_state.current_page = page
        self.global_state.current_stage = stage
        self._recalculate_eta()

    def record_page_time(self, elapsed: float):
        self.page_times.append(elapsed)
        if len(self.page_times) > self._eta_rolling_window:
            self.page_times = self.page_times[-self._eta_rolling_window:]

    def _recalculate_eta(self):
        if not self.page_times:
            self.global_state.eta_seconds = None
            return
        avg = sum(self.page_times) / len(self.page_times)
        remaining = 0
        current_survey_id = self.global_state.current_survey_id
        if current_survey_id is not None:
            current_survey = self.surveys[current_survey_id]
            current_page = self.global_state.current_page
            if current_page is not None:
                remaining += len(current_survey.files) - current_page - 1
            for s in self.surveys[current_survey_id + 1:]:
                remaining += len(s.files)
        self.global_state.eta_seconds = avg * remaining if remaining > 0 else 0

    def is_finished(self) -> bool:
        return all(s.status in ("ready", "error") for s in self.surveys)

    def to_global_dict(self) -> dict:
        return {
            "total": self.global_state.total,
            "processed": self.global_state.processed,
            "errors": self.global_state.errors,
            "current_survey_id": self.global_state.current_survey_id,
            "current_page": self.global_state.current_page,
            "current_stage": self.global_state.current_stage,
            "eta_seconds": self.global_state.eta_seconds,
            "is_running": self.global_state.is_running,
        }
