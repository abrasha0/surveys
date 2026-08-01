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
    total_pages: int = 0
    processed_pages: int = 0
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
        self._counted_pages: set[tuple[int, int]] = set()
        self._eta_rolling_window: int = config.processing["eta_rolling_window"]

    @property
    def is_running(self) -> bool:
        return self.global_state.is_running

    @is_running.setter
    def is_running(self, value: bool):
        self.global_state.is_running = value

    def _build_from_processed(self, survey_groups: list[list[Path]]):
        from data_handler import load_processed_data, save_processed_data
        processed = load_processed_data()
        cached_surveys = processed.get("surveys", {})
        self.page_times = processed.get("page_times", [])
        self.surveys = []
        total_pages = 0
        fresh_surveys = {}
        for idx, group in enumerate(survey_groups):
            key = str(idx)
            s = cached_surveys.get(key)
            actual_files = [p.name for p in group]
            if s is not None and s.get("files") == actual_files:
                status = s.get("status", "queued")
                result = s.get("result")
                error = s.get("error_message")
                fresh_surveys[key] = s
            else:
                status = "queued"
                result = None
                error = None
            self.surveys.append(SurveyState(id=idx, files=group, status=status, result=result, error_message=error))
            total_pages += len(group)
        self.global_state.total = len(self.surveys)
        self.global_state.total_pages = total_pages
        processed_surveys = [s for s in self.surveys if s.status in ("ready", "error", "verified")]
        self.global_state.processed = len(processed_surveys)
        self.global_state.processed_pages = sum(len(s.files) for s in processed_surveys)
        self.global_state.errors = sum(1 for s in self.surveys if s.status == "error")
        if fresh_surveys != cached_surveys:
            processed["surveys"] = fresh_surveys
            save_processed_data(processed)
        self._recalculate_eta()

    def ensure_from_cache(self, survey_groups: list[list[Path]]):
        if self.surveys:
            return
        self._build_from_processed(survey_groups)

    def init_from_surveys(self, survey_groups: list[list[Path]]):
        from data_handler import save_processed_data
        self.surveys = []
        total_pages = 0
        for idx, group in enumerate(survey_groups):
            self.surveys.append(SurveyState(id=idx, files=group))
            total_pages += len(group)
        self.global_state = GlobalState(
            total=len(survey_groups),
            total_pages=total_pages,
            is_running=True,
            started_at=time.time(),
        )
        self.page_times.clear()
        self._counted_pages.clear()
        save_processed_data({
            "session_started_at": self.global_state.started_at,
            "surveys": {},
            "total_surveys": len(survey_groups),
            "total_pages": self.global_state.total_pages,
        })

    def get_survey_state(self, survey_id: int) -> SurveyState | None:
        if 0 <= survey_id < len(self.surveys):
            return self.surveys[survey_id]
        return None

    def _persist_survey_to_processed(self, survey_id: int):
        from data_handler import update_survey_in_processed
        survey = self.surveys[survey_id]
        update_survey_in_processed(survey_id, {
            "status": survey.status,
            "result": survey.result,
            "error_message": survey.error_message,
            "files": [str(p.name) for p in survey.files],
            "survey_id": survey_id,
        }, page_times=self.page_times)

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
            already_counted = sum(1 for (sid, _) in self._counted_pages if sid == survey_id)
            uncounted = len(survey.files) - already_counted
            if uncounted > 0:
                self.global_state.processed_pages += uncounted
            if status == "error":
                self.global_state.errors += 1
        self._persist_survey_to_processed(survey_id)

    def mark_verified(self, survey_id: int, result: dict | None = None):
        survey = self.surveys[survey_id]
        if survey.status != "ready":
            raise ValueError(f"Cannot verify survey in status '{survey.status}'")
        survey.status = "verified"
        survey.result = result
        self._persist_survey_to_processed(survey_id)

    def mark_page_processed(self, survey_id: int, page_idx: int):
        key = (survey_id, page_idx)
        if key not in self._counted_pages:
            self._counted_pages.add(key)
            self.global_state.processed_pages += 1

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
        else:
            remaining = self.global_state.total_pages - self.global_state.processed_pages
        self.global_state.eta_seconds = avg * remaining if remaining > 0 else 0

    def is_finished(self) -> bool:
        return all(s.status in ("ready", "error", "verified") for s in self.surveys)

    def reset(self):
        self.surveys.clear()
        self.results.clear()
        self.page_times.clear()
        self._counted_pages.clear()
        self.global_state = GlobalState()

    def to_global_dict(self) -> dict:
        return {
            "total": self.global_state.total,
            "processed": self.global_state.processed,
            "errors": self.global_state.errors,
            "total_pages": self.global_state.total_pages,
            "processed_pages": self.global_state.processed_pages,
            "current_survey_id": self.global_state.current_survey_id,
            "current_page": self.global_state.current_page,
            "current_stage": self.global_state.current_stage,
            "eta_seconds": self.global_state.eta_seconds,
            "is_running": self.global_state.is_running,
        }
