"""
Central logging setup. Called once at process startup (monitor.py /
init_db.py). Rotating file handler so logs/ never grows unbounded on the
Pi's SD card, plus a console handler for systemd journal / interactive use.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import config


def setup_logging():
    os.makedirs(config.LOG_DIR, exist_ok=True)
    log_path = os.path.join(config.LOG_DIR, config.LOG_FILE)

    root = logging.getLogger("weldomat")
    root.setLevel(config.LOG_LEVEL)
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path, maxBytes=config.LOG_MAX_BYTES, backupCount=config.LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)

    return root
