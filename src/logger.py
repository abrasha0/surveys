import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import config

_LOG_FILE: Path | None = None
_LOGGING_SETUP_DONE: bool = False
ai_req_logger: logging.Logger | None = None


def setup_logging(
    log_dir: str = "logs",
    log_file: str = "ankieter.log",
    level: int = logging.DEBUG,
    console_level: int = logging.DEBUG,
):
    global _LOG_FILE, _LOGGING_SETUP_DONE

    if _LOGGING_SETUP_DONE:
        return

    log_path = Path(log_file)
    if log_path.parent != Path("."):
        _LOG_FILE = log_path
    else:
        _LOG_FILE = Path(log_dir) / log_path
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

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

    for noisy in ("httpx", "httpcore", "PIL", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Dedykowany logger dla AI requests z rotacją
    global ai_req_logger
    ai_req_logger = logging.getLogger("ai.requests")
    ai_req_logger.setLevel(logging.DEBUG)
    ai_req_logger.propagation = False  # nie duplikuj do root

    ai_handler = RotatingFileHandler(
        _LOG_FILE.parent / "ai_requests.log",
        maxBytes=config.logging["ai_log_max_bytes"],
        backupCount=config.logging["ai_log_backup_count"],
        encoding="utf-8"
    )
    ai_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    ai_req_logger.addHandler(ai_handler)

    separator = "=" * 60
    app_logger = logging.getLogger("app")
    app_logger.info(separator)
    app_logger.info("Application started — logging initialized, file: %s", _LOG_FILE)

    _LOGGING_SETUP_DONE = True


def get_log_path() -> Path | None:
    return _LOG_FILE
