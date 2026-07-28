import json
import logging
import shutil
import time
from pathlib import Path
from config import config

logger = logging.getLogger(__name__)

PROCESSED_FILE = "processed.json"

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

def update_survey_in_processed(survey_id: int, update: dict):
    data = load_processed_data()
    surveys = data.setdefault("surveys", {})
    if str(survey_id) in surveys:
        surveys[str(survey_id)].update(update)
    else:
        surveys[str(survey_id)] = update
    data["updated_at"] = time.time()
    save_processed_data(data)

def archive_processed():
    path = _processed_path()
    if path.exists():
        archived = path.with_suffix(".json.old")
        shutil.move(str(path), str(archived))
        logger.info("Archived %s -> %s", path.name, archived.name)

def archive_csv():
    csv_path = Path(config.app["csv_results"])
    if csv_path.exists():
        archived = csv_path.with_suffix(".csv.old")
        shutil.move(str(csv_path), str(archived))
        logger.info("Archived %s -> %s", csv_path.name, archived.name)

def clear_survey_cache_dir():
    cache_dir = Path(config.processing.get("survey_cache_dir", "logs/survey_cache"))
    if cache_dir.exists():
        for f in cache_dir.glob("survey_*.json"):
            f.unlink()
            logger.debug("Removed cache: %s", f.name)

def clear_cache_file():
    cache_path = Path(config.app["cache_file"])
    if cache_path.exists():
        cache_path.unlink()
        logger.debug("Removed cache file: %s", cache_path.name)

def export_csv_path() -> str:
    return config.app["csv_results"]