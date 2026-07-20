import logging
from pathlib import Path
import tempfile
from typing import List, Tuple

from config import config

logger = logging.getLogger(__name__)

_UPLOAD_DIR = None

def get_upload_dir() -> Path:
    global _UPLOAD_DIR
    if _UPLOAD_DIR is None:
        _UPLOAD_DIR = Path(tempfile.mkdtemp(prefix=config.ingestion["upload_dir_prefix"]))
    return _UPLOAD_DIR

def group_files_by_survey(files: list) -> Tuple[List[List[Path]], List[str]]:
    """
    Grupuje pliki po 5, sortując leksykograficznie po nazwie.
    Zwraca listę grup (każda lista ścieżek) oraz listę ostrzeżeń.
    """
    sorted_files = sorted(files, key=lambda f: f.name)
    groups = []
    warnings = []
    upload_dir = get_upload_dir()

    # Zapisz pliki na dysk
    saved_paths = []
    for f in sorted_files:
        dest = upload_dir / f.name
        with open(dest, "wb") as out:
            out.write(f.getbuffer())
        saved_paths.append(dest)

    # Podziel na grupy
    group_size = config.ingestion["survey_group_size"]
    for i in range(0, len(saved_paths), group_size):
        chunk = saved_paths[i:i+group_size]
        if len(chunk) < group_size:
            warnings.append(f"Ostatnia grupa ma tylko {len(chunk)} plików (oczekiwano 5).")
        groups.append(chunk)

    # Sprawdź, czy nazwy plików sugerują poprawną kolejność (opcjonalnie)
    for idx, group in enumerate(groups):
        names = [p.name for p in group]
        logger.debug("Grupa %d: %s", idx, ", ".join(names))

    return groups, warnings


def scan_survey_directory(dir_path: Path) -> List[List[Path]]:
    """Skanuje katalog ze zdjęciami, sortuje po nazwie, grupuje po 5."""
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