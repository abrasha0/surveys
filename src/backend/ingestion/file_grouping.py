import logging
from pathlib import Path

from config import config

logger = logging.getLogger(__name__)


def scan_survey_directory(dir_path: Path) -> list[list[Path]]:
    """Scan the image directory, sort files by name and split them into surveys.

    Group size comes from ingestion.survey_group_size (one image per page).
    """
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    files = [
        p for p in dir_path.iterdir()
        if p.is_file() and p.suffix.lower() in extensions
    ]
    files.sort(key=lambda p: p.name)

    group_size = config.ingestion["survey_group_size"]
    groups = []
    for i in range(0, len(files), group_size):
        groups.append(files[i : i + group_size])

    logger.debug("Scanned %s: %d files, %d groups", dir_path, len(files), len(groups))
    return groups
