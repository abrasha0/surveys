import logging
import sys
from pathlib import Path

_LOG_FILE: Path | None = None


def setup_logging(
    log_dir: str = "logs",
    log_file: str = "ankieter.log",
    level: int = logging.DEBUG,
    console_level: int = logging.DEBUG,
):
    global _LOG_FILE
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    _LOG_FILE = log_path / log_file

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(str(_LOG_FILE), encoding="utf-8", mode="a")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    logging.getLogger(__name__).info("Logging initialized, file: %s", _LOG_FILE)


def get_log_path() -> Path | None:
    return _LOG_FILE
