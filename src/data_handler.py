import csv
import json
import logging
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import config
from schemas import CSV_HEADER, MedicalSurvey, SurveyGroup, SurveyResult

logger = logging.getLogger(__name__)

_UPLOAD_DIR: Path | None = None


def _get_upload_dir() -> Path:
    global _UPLOAD_DIR
    if _UPLOAD_DIR is None:
        _UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="ankieter_uploads_"))
    return _UPLOAD_DIR


def group_files_by_survey(files: list) -> list[SurveyGroup]:
    sorted_files = sorted(files, key=lambda f: f.name)
    groups = []
    upload_dir = _get_upload_dir()
    logger.debug("Grouping %d files in %s", len(sorted_files), upload_dir)
    for i in range(0, len(sorted_files), 5):
        chunk = sorted_files[i : i + 5]
        saved_paths = []
        for f in chunk:
            dest = upload_dir / f.name
            with open(dest, "wb") as out:
                out.write(f.getbuffer())
            saved_paths.append(dest)
        file_names = [p.name for p in saved_paths]
        groups.append(SurveyGroup(id=len(groups), files=saved_paths))
        logger.info("Survey group %d: %s", len(groups) - 1, ", ".join(file_names))
    return groups


def save_survey_to_csv(data: MedicalSurvey, path: str):
    filepath = Path(path)
    exists = filepath.exists()
    with open(filepath, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(CSV_HEADER)
            logger.info("Created CSV file: %s", path)
        writer.writerow(data.to_csv_row())
    logger.debug("Appended survey row to CSV: %s", path)


def save_cache(results: dict[int, SurveyResult]):
    data = {str(k): v.model_dump() for k, v in results.items()}
    cache_path = Path(config.cache_file)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.debug("Cache saved: %d result(s) to %s", len(results), config.cache_file)


def load_cache() -> dict[int, SurveyResult]:
    cache_path = Path(config.cache_file)
    if not cache_path.exists():
        logger.debug("No cache file at %s", config.cache_file)
        return {}
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    loaded = {int(k): SurveyResult(**v) for k, v in data.items()}
    logger.info("Cache loaded: %d result(s) from %s", len(loaded), config.cache_file)
    return loaded


def export_csv_path() -> str:
    return config.results_csv
