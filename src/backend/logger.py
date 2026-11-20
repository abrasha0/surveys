import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import config

_LOGGING_SETUP_DONE: bool = False
ai_req_logger: logging.Logger | None = None


def setup_logging(
    log_file: str,
    level: int = logging.DEBUG,
    console_level: int = logging.DEBUG,
):
    global _LOGGING_SETUP_DONE

    if _LOGGING_SETUP_DONE:
        return

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(str(log_path), encoding="utf-8", mode="a")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    for noisy in ("httpx", "httpcore", "PIL", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Dedicated rotating logger for AI requests
    global ai_req_logger
    ai_req_logger = logging.getLogger("ai.requests")
    ai_req_logger.setLevel(logging.DEBUG)
    ai_req_logger.propagate = False  # keep AI request dumps out of the main log and console

    ai_handler = RotatingFileHandler(
        log_path.parent / "ai_requests.log",
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
    app_logger.info("Application started — logging initialized, file: %s", log_path)

    _LOGGING_SETUP_DONE = True
