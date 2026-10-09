"""
Logging tizimi — barcha xatolar va muhim voqealar faylga yoziladi.
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


LOG_DIR = os.path.join(BASE_DIR, "data", "logs")


def setup_logger(name="Komplaynsbot", level=logging.INFO):
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    log_file = os.path.join(LOG_DIR, "app.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


log = setup_logger()


def log_error(error, context=""):
    import traceback
    log.error(f"{context}: {type(error).__name__}: {error}")
    log.debug(traceback.format_exc())


def log_info(message):
    log.info(message)


def log_warning(message):
    log.warning(message)


def cleanup_old_logs(days=30):
    try:
        if not os.path.exists(LOG_DIR):
            return 0
        cutoff = datetime.now().timestamp() - (days * 86400)
        removed = 0
        for f in os.listdir(LOG_DIR):
            fpath = os.path.join(LOG_DIR, f)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                try:
                    os.remove(fpath)
                    removed += 1
                except OSError:
                    pass
        return removed
    except Exception:
        return 0
