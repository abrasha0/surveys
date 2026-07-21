# Etap 3 — Globalny Worker Przetwarzania + Status/ETA

**Zależności:** Etap 2, decyzje #2, #3, #5, #6 z Etapu 0.

To jest etap, który najbardziej różni się od pierwszej wersji szkicu — przez
decyzję o jednym globalnym workerze zamiast triggera per-ankieta.

---

## Cel

Implementacja globalnego workera przetwarzającego kolejkę ankiet w tle (jeden
`asyncio.Task`), niezależnie od żądań HTTP. Worker przetwarza ankiety
sekwencyjnie (strona po stronie, jeden model w VRAM naraz), udostępnia
endpointy statusu/ETA, a przetworzone ankiety są od razu dostępne do
weryfikacji (interleaved verification — decyzja #5).

---

## Nowa struktura plików

```
src/
└── worker/
    ├── __init__.py          # singleton workera
    ├── state.py             # stan workera (GlobalState + SurveyState)
    └── processing_worker.py # główny worker (asyncio.Task)
```

---

## Krok 1: `src/worker/state.py` — Warstwa stanu

**Cel:** Współdzielony stan między workerem a endpointami HTTP. Zero zależności od Streamlit.

### Struktury danych

```python
from dataclasses import dataclass, field
from pathlib import Path
import time

@dataclass
class SurveyState:
    id: int
    files: list[Path]
    status: str = "queued"          # queued | processing | ready | error
    result: dict | None = None      # wynik MedicalSurvey.model_dump()
    error_message: str | None = None

@dataclass
class GlobalState:
    total: int = 0
    processed: int = 0
    errors: int = 0
    current_survey_id: int | None = None
    current_page: int | None = None
    current_stage: str | None = None  # "vlm" | "format"
    eta_seconds: float | None = None
    is_running: bool = False
    started_at: float | None = None
```

### Klasa `ProcessingState`

```python
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
```

---

## Krok 2: `src/worker/processing_worker.py` — Główny worker

**Cel:** Jeden `asyncio.Task` przetwarzający kolejkę sekwencyjnie. Przeżywa między requestami.

### Klasa `ProcessingWorker`

```python
class ProcessingWorker:
    def __init__(self):
        self.state = ProcessingState()
        self._task: asyncio.Task | None = None
        self._client: AIClient | None = None
        self._stop_event = asyncio.Event()

    async def start(self, survey_groups: list[list[Path]]):
        """Uruchamia workera w tle. Zwraca natychmiast."""
        if self.state.is_running:
            raise RuntimeError("Worker already running")

        self.state.init_from_surveys(survey_groups)
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        """Graceful stop — zatrzymuje po zakończeniu bieżącej ankiety."""
        self._stop_event.set()

    async def _run(self):
        """Główna pętla przetwarzania."""
        self._client = AIClient()
        try:
            for idx, survey in enumerate(self.state.surveys):
                if self._stop_event.is_set():
                    logger.info("Worker stop requested — finishing current survey")
                    break

                # Resume check: jeśli ankieta ma już cache, pomijamy
                if survey.status in ("ready", "error"):
                    continue

                await self._process_survey_with_retry(idx, survey)
        finally:
            self.state.global_state.is_running = False
            if self._client:
                await self._client.close()
                self._client = None

    async def _process_survey_with_retry(self, idx: int, survey: SurveyState):
        """Retry tylko stron z błędem — restartuje od pierwszej błęduced strony."""
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
                )
                # Sukces
                self.state.set_survey_status(idx, "ready", result=result)
                save_survey_cache(idx, result, "ready")
                return
            except Exception as e:
                last_error = e
                logger.warning(
                    "Survey %d attempt %d/%d failed: %s",
                    idx, attempt + 1, max_retries, e,
                )
                if attempt < max_retries - 1:
                    # Restart od pierwszej strony (analyze_survey zacznie od zera)
                    pass

        # Wszystkie próby wyczerpane
        error_msg = str(last_error)[:200] if last_error else "Unknown error"
        self.state.set_survey_status(idx, "error", error=error_msg)
        save_survey_cache(idx, {}, "error", error_msg)

    def _progress_callback(self, status: ProcessingStatus):
        """Callback z AIClient — aktualizuje stan."""
        self.state.update_global(
            status.survey_idx,
            status.page_idx if status.page_idx >= 0 else None,
            self._map_stage(status.status),
        )
        if status.extra and "elapsed_s" in status.extra:
            try:
                self.state.record_page_time(float(status.extra["elapsed_s"]))
            except (ValueError, TypeError):
                pass

    def _map_stage(self, status_str: str) -> str | None:
        if "vlm" in status_str:
            return "vlm"
        if "text" in status_str or "format" in status_str:
            return "format"
        return None
```

---

## Krok 3: `src/worker/__init__.py` — Singleton

```python
from worker.processing_worker import ProcessingWorker

_worker: ProcessingWorker | None = None

def get_worker() -> ProcessingWorker:
    global _worker
    if _worker is None:
        _worker = ProcessingWorker()
    return _worker
```

---

## Krok 4: `src/data_handler.py` — Cache per-survey

**Dodajemy nowe funkcje do istniejącego pliku** (stare `save_cache`/`load_cache`
zostają, ale nie są używane przez workera):

```python
def get_cache_dir() -> Path:
    cache_dir = Path(config.processing.get("survey_cache_dir", "logs/survey_cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def save_survey_cache(survey_idx: int, result: dict, status: str, error: str | None = None):
    cache_dir = get_cache_dir()
    cache_file = cache_dir / f"survey_{survey_idx}.json"
    data = {"status": status, "result": result, "error": error}
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.debug("Survey cache saved: %s", cache_file)

def load_survey_cache(survey_idx: int) -> dict | None:
    cache_dir = get_cache_dir()
    cache_file = cache_dir / f"survey_{survey_idx}.json"
    if not cache_file.exists():
        return None
    with open(cache_file, "r", encoding="utf-8") as f:
        return json.load(f)

def load_all_survey_caches() -> dict[int, dict]:
    cache_dir = get_cache_dir()
    results = {}
    for cache_file in cache_dir.glob("survey_*.json"):
        try:
            idx = int(cache_file.stem.split("_")[1])
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            results[idx] = data
        except (ValueError, json.JSONDecodeError):
            continue
    return results
```

---

## Krok 5: `src/routers/api.py` — Implementacja endpointów

Kompletna zmiana pliku — implementacja stubów + nowe endpointy:

```python
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from auth import get_current_user
from config import config
from ingestion.file_grouping import scan_survey_directory
from worker import get_worker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


@router.get("/surveys")
def list_surveys() -> list[dict]:
    surveys_dir = config.app.get("surveys_dir")
    if not surveys_dir:
        raise HTTPException(status_code=500, detail="surveys_dir not configured")
    dir_path = Path(surveys_dir)
    if not dir_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {surveys_dir}")

    groups = scan_survey_directory(dir_path)
    worker = get_worker()

    result = []
    for idx, group in enumerate(groups):
        survey_state = worker.state.get_survey_state(idx)
        status = survey_state.status if survey_state else "queued"
        result.append({
            "id": idx,
            "files": [p.name for p in group],
            "status": status,
        })
    return result


@router.get("/surveys/{survey_id}/pages/{page_num}/image")
def get_survey_image(survey_id: int, page_num: int):
    surveys_dir = config.app.get("surveys_dir")
    if not surveys_dir:
        raise HTTPException(status_code=500, detail="surveys_dir not configured")
    dir_path = Path(surveys_dir)
    if not dir_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {surveys_dir}")

    groups = scan_survey_directory(dir_path)
    if survey_id < 0 or survey_id >= len(groups):
        raise HTTPException(status_code=404, detail=f"Survey {survey_id} not found")

    group = groups[survey_id]
    if page_num < 0 or page_num >= len(group):
        raise HTTPException(
            status_code=400,
            detail=f"Page {page_num} out of range (0-{len(group) - 1})",
        )

    file_path = group[page_num]
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path.name}")

    return FileResponse(path=str(file_path), media_type="image/jpeg")


@router.get("/surveys/{survey_id}/result")
def get_survey_result(survey_id: int):
    worker = get_worker()
    survey = worker.state.get_survey_state(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if survey.status not in ("ready", "error"):
        raise HTTPException(status_code=400, detail="Survey not yet processed")
    return {
        "id": survey_id,
        "status": survey.status,
        "result": survey.result,
        "error": survey.error_message,
    }


@router.post("/processing/start")
async def processing_start():
    worker = get_worker()
    if worker.state.is_running:
        raise HTTPException(status_code=400, detail="Processing already in progress")

    surveys_dir = config.app.get("surveys_dir")
    if not surveys_dir:
        raise HTTPException(status_code=500, detail="surveys_dir not configured")
    dir_path = Path(surveys_dir)
    if not dir_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {surveys_dir}")

    groups = scan_survey_directory(dir_path)
    if not groups:
        raise HTTPException(status_code=404, detail="No surveys found")

    await worker.start(groups)
    return {"status": "started", "total": len(groups)}


@router.get("/processing/status")
async def processing_status():
    worker = get_worker()
    return worker.state.to_global_dict()


@router.post("/processing/stop")
async def processing_stop():
    worker = get_worker()
    if not worker.state.is_running:
        raise HTTPException(status_code=400, detail="Worker not running")
    await worker.stop()
    return {"status": "stopping"}


@router.post("/surveys/{survey_id}/save")
def save_survey(survey_id: int):
    raise HTTPException(status_code=501, detail="Not implemented yet — Etap 4")
```

---

## Krok 6: `src/main.py` — Lifespan cleanup

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(
        log_file=config.logging["file"],
        level=getattr(logging, config.logging["level"].upper(), logging.DEBUG),
    )
    yield
    worker = get_worker()
    if worker.state.is_running:
        await worker.stop()
```

---

## Krok 7: `config.yaml` — Nowe klucze

```yaml
processing:
  progress_vlm_weight: 0.3
  progress_text_weight: 0.6
  history_display_limit: 8
  worker_max_retries: 3
  eta_rolling_window: 10
  survey_cache_dir: "logs/survey_cache"
```

---

## Krok 8: `src/ingestion/file_grouping.py` — Resume check

Nowa funkcja:

```python
def scan_surveys_with_cache_status(dir_path: Path, cache_dir: Path) -> list[tuple[int, list[Path], str]]:
    """Skanuje katalog, sprawdza cache, zwraca (id, files, cached_status)."""
    groups = scan_survey_directory(dir_path)
    result = []
    for idx, group in enumerate(groups):
        cache_file = cache_dir / f"survey_{idx}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                status = data.get("status", "queued")
            except (json.JSONDecodeError, KeyError):
                status = "queued"
        else:
            status = "queued"
        result.append((idx, group, status))
    return result
```

---

## Kolejność implementacji

| Krok | Plik | Zależności | Opis |
|------|------|------------|------|
| 7 | `config.yaml` | brak | Nowe klucze konfiguracyjne |
| 4 | `src/data_handler.py` | krok 7 | Cache per-survey |
| 1 | `src/worker/state.py` | krok 4 | Stan workera |
| 2 | `src/worker/processing_worker.py` | kroki 1, 4 | Główny worker |
| 3 | `src/worker/__init__.py` | kroki 1-2 | Singleton |
| 8 | `src/ingestion/file_grouping.py` | krok 4 | Resume check |
| 5 | `src/routers/api.py` | kroki 3, 8 | Implementacja endpointów |
| 6 | `src/main.py` | krok 3 | Lifespan cleanup |

---

## Kryteria akceptacji

1. `POST /api/processing/start` uruchamia przetwarzanie całej kolejki
2. Polling `GET /api/processing/status` pokazuje narastający postęp z sensownym ETA
3. Ankieta, która skończyła się wcześniej, jest dostępna do weryfikacji zanim worker skończy resztę kolejki
4. Restart serwera w trakcie nie gubi już przetworzonych ankiet

## How to verify

1. **Start:** `POST /api/processing/start` → `{"status": "started", "total": N}`
2. **Poll:** `GET /api/processing/status` → rosnące `processed`, `current_page`, `eta_seconds`
3. **Surveys:** `GET /api/surveys` → statusy `queued → processing → ready/error`
4. **Result:** `GET /api/surveys/0/result` → wynik JSON gdy status `ready`
5. **Resume:** restart serwera w trakcie → ponowny start → ankiety z cache pomijane
6. **Stop:** `POST /api/processing/stop` → worker kończy bieżącą ankietę i przestaje

---

## Kluczowe decyzje implementacyjne

1. **Cache per-survey** (`logs/survey_cache/survey_{id}.json`) zamiast jednego pliku — łatwiejszy resume, mniej contention
2. **Retry tylko stron z błędem** — restart od pierwszej strony, ale strony bez błędu są przetwarzane normalnie
3. **Kompatybilność wsteczna:** stare `cache_results.json` jest ignorowane
4. **`GET /api/surveys`** zwraca realny status z workera od razu (nie hardcoded "queued")
5. **Endpoint `POST /api/processing/stop`** — graceful stop po zakończeniu bieżącej ankiety
6. **Rolling average ETA** — ostatnie N czasów stron × pozostałe strony
