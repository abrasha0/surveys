import json
import logging
from pathlib import Path
from config import config

logger = logging.getLogger(__name__)

def save_cache(results: dict):
    """Zapisuje słownik wyników do pliku JSON."""
    cache_path = Path(config.app["cache_file"])
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.debug("Cache saved to %s", config.app["cache_file"])

def load_cache() -> dict:
    """Ładuje słownik wyników z pliku JSON."""
    cache_path = Path(config.app["cache_file"])
    if not cache_path.exists():
        return {}
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Klucze mogą być stringami – konwertujemy na int
    return {int(k): v for k, v in data.items()}

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

def export_csv_path() -> str:
    return config.app["csv_results"]