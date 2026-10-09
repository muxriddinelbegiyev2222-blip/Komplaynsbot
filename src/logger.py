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
    """
    Logger yaratadi. Faylga va konsolga yozadi.
    Fayl rotatsiyasi: 5 MB dan oshsa, yangi fayl.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Takroriy handler'larni oldini olish
    if logger.handlers:
        return logger

    # Fayl handler (rotatsiya bilan)
    log_file = os.path.join(LOG_DIR, "app.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    # Konsol handler (faqat Windows'da)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Global logger
log = setup_logger()


def log_error(error, context=""):
    """Xatoni log qilish (traceback bilan)."""
    import traceback
    log.error(f"{context}: {type(error).__name__}: {error}")
    log.debug(traceback.format_exc())


def log_info(message):
    """Muhim voqeani log qilish."""
    log.info(message)


def log_warning(message):
    """Ogohlantirish."""
    log.warning(message)


def cleanup_old_logs(days=30):
    """30 kundan eski log fayllarni o'chirish."""
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
