import json
import logging
import shutil
import time
from pathlib import Path

from config import APP_ROOT, config

logger = logging.getLogger(__name__)

PROCESSED_FILE = "processed.json"
_DEFAULT_SURVEY_CACHE_DIR = "working_vault/logs/survey_cache"


def _processed_path() -> Path:
    p = Path(config.app["processing_dir"]) / PROCESSED_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_processed_data() -> dict:
    path = _processed_path()
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_processed_data(data: dict):
    path = _processed_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.debug("Processed data saved to %s", path)


def update_survey_in_processed(survey_id: int, update: dict, page_times: list[float] | None = None):
    data = load_processed_data()
    surveys = data.setdefault("surveys", {})
    if str(survey_id) in surveys:
        surveys[str(survey_id)].update(update)
    else:
        surveys[str(survey_id)] = update
    if page_times is not None:
        data["page_times"] = page_times
    data["updated_at"] = time.time()
    save_processed_data(data)


ARCHIVE_DIR = "archive"


def _new_archive_dir() -> Path:
    """Create a unique, sortable archive directory: <processing_dir>/archive/YYYYMMDD-HHMMSS[-N]."""
    root = Path(config.app["processing_dir"]) / ARCHIVE_DIR
    root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    candidate = root / stamp
    n = 2
    while True:
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            candidate = root / f"{stamp}-{n}"
            n += 1


def archive_session() -> Path | None:
    """Move processed.json and the results CSV into a new timestamped archive directory.

    Previous archives are never overwritten or deleted. Returns the archive directory,
    or None when there was nothing to archive.
    """
    files = [p for p in (_processed_path(), Path(config.app["csv_results"])) if p.exists()]
    if not files:
        return None
    target = _new_archive_dir()
    for path in files:
        shutil.move(str(path), str(target / path.name))
    logger.info("Archived %s -> %s", ", ".join(p.name for p in files), target)
    return target


def survey_cache_dir() -> Path:
    return Path(config.processing.get("survey_cache_dir") or APP_ROOT / _DEFAULT_SURVEY_CACHE_DIR)


def drafts_dir() -> Path:
    return survey_cache_dir() / "drafts"


def export_csv_path() -> str:
    return config.app["csv_results"]
