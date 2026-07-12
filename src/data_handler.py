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

def export_csv_path() -> str:
    return config.app["csv_results"]