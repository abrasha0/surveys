import asyncio
import logging
import time

from ai.client import AIClient, ProcessingStatus
from config import config
from worker.state import ProcessingState, SurveyState

logger = logging.getLogger(__name__)


class ProcessingWorker:
    def __init__(self):
        self.state = ProcessingState()
        self._task: asyncio.Task | None = None
        self._client: AIClient | None = None
        self._stop_event = asyncio.Event()

    async def start(self, survey_groups: list[list], batch_size: int = 0):
        if self.state.is_running:
            raise RuntimeError("Worker already running")

        self.state.ensure_from_cache(survey_groups)

        if any(s.status in ("ready", "error", "verified") for s in self.state.surveys):
            self.state.global_state.is_running = True
            self.state.global_state.started_at = time.time()
            self.state.global_state.total = len(self.state.surveys)
            self.state.global_state.total_pages = sum(
                len(s.files) for s in self.state.surveys
            )
            queued_count = sum(1 for s in self.state.surveys if s.status == "queued")
            effective_batch = batch_size if batch_size > 0 else queued_count
            self.state.global_state.batch_size = min(effective_batch, queued_count)
            self.state.global_state.batch_remaining = self.state.global_state.batch_size
            self.state.global_state.batch_processed = 0

            batch_total_pages = 0
            counted = 0
            for s in self.state.surveys:
                if counted >= self.state.global_state.batch_size:
                    break
                if s.status == "queued":
                    batch_total_pages += len(s.files)
                    counted += 1
            self.state.global_state.batch_total_pages = batch_total_pages
            self.state.global_state.batch_processed_pages = 0
            logger.info(
                "Starting worker (continue) with batch_size=%d (requested=%d, queued=%d)",
                self.state.global_state.batch_size, batch_size, queued_count,
            )
        else:
            self.state.init_batch(survey_groups, batch_size)
            logger.info(
                "Starting worker (fresh) with batch_size=%d (requested=%d, total=%d)",
                self.state.global_state.batch_size, batch_size, len(survey_groups),
            )

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._stop_event.set()

    async def _run(self):
        self._client = AIClient()
        try:
            batch_limit = self.state.global_state.batch_size
            processed_in_batch = 0
            logger.info("_run started: batch_limit=%d", batch_limit)

            for idx, survey in enumerate(self.state.surveys):
                if self._stop_event.is_set():
                    logger.info("Worker stop requested — finishing current survey")
                    break

                if survey.status in ("ready", "error", "verified"):
                    continue

                if batch_limit > 0 and processed_in_batch >= batch_limit:
                    logger.info(
                        "Batch limit reached (%d/%d) — stopping worker",
                        processed_in_batch, batch_limit,
                    )
                    break

                await self._process_survey_with_retry(idx, survey)
                processed_in_batch += 1
        finally:
            self.state.global_state.is_running = False
            if self._client:
                await self._client.close()
                self._client = None

    async def _process_survey_with_retry(self, idx: int, survey: SurveyState):
        self.state.surveys[idx].status = "processing"
        self.state.update_global(idx, 0, None)

        max_retries = config.processing.get("worker_max_retries", 3)
        last_error = None

        for attempt in range(max_retries):
            try:
                result = await self._client.analyze_survey(
                    survey.files,
                    idx,
                    self.state.global_state.total,
                    progress_callback=self._progress_callback,
                    page_done_callback=self.state.mark_page_processed,
                )
                self.state.set_survey_status(idx, "ready", result=result)
                return
            except Exception as e:
                last_error = e
                logger.warning(
                    "Survey %d attempt %d/%d failed: %s",
                    idx, attempt + 1, max_retries, e,
                )
                if attempt < max_retries - 1:
                    pass

        error_msg = str(last_error)[:200] if last_error else "Unknown error"
        self.state.set_survey_status(idx, "error", error=error_msg)

    def _progress_callback(self, status: ProcessingStatus):
        self.state.update_global(
            status.survey_idx,
            status.page_idx if status.page_idx >= 0 else None,
            self._map_stage(status.status),
        )
        if status.extra and "elapsed_s" in status.extra:
            try:
                elapsed = float(status.extra["elapsed_s"])
                if status.status == "survey_done":
                    pages = int(status.extra.get("pages", 1))
                    for _ in range(pages):
                        self.state.record_page_time(elapsed / pages)
                else:
                    self.state.record_page_time(elapsed)
            except (ValueError, TypeError):
                pass

    def _map_stage(self, status_str: str) -> str | None:
        if "vlm" in status_str:
            return "vlm"
        if "text" in status_str or "format" in status_str:
            return "format"
        return None
