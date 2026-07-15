import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


class Config:
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
    POSTGRES_PORT = _get_int("POSTGRES_PORT", 5432)
    POSTGRES_DB = os.getenv("POSTGRES_DB", "weldomat_monitor")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "weldomat")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme")

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
    )

    TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

    OFFLINE_QUEUE_PATH = os.getenv(
        "OFFLINE_QUEUE_PATH",
        str(PROJECT_ROOT / "data" / "offline_queue.db"),
    )
    OFFLINE_SYNC_INTERVAL_SECONDS = _get_int(
        "OFFLINE_SYNC_INTERVAL_SECONDS",
        45,
    )

    GPIO_PIN = _get_int("GPIO_PIN", 17)
    DEBOUNCE_SECONDS = float(os.getenv("DEBOUNCE_SECONDS", "0.08"))
    ACTIVE_HIGH = _get_bool("ACTIVE_HIGH", True)
    SIMULATION_MODE = _get_bool("SIMULATION_MODE", True)

    SHIFTS = {
        "A": {"start": "06:00", "end": "14:00"},
        "B": {"start": "14:00", "end": "22:00"},
        "C": {"start": "22:00", "end": "06:00"},
    }

    RECALC_INTERVAL_SECONDS = _get_int("RECALC_INTERVAL_SECONDS", 45)
    HEARTBEAT_INTERVAL_SECONDS = _get_int(
        "HEARTBEAT_INTERVAL_SECONDS",
        15,
    )

    LOG_DIR = os.getenv("LOG_DIR", str(PROJECT_ROOT / "logs"))
    LOG_FILE = os.getenv("LOG_FILE", "monitor.log")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_MAX_BYTES = _get_int("LOG_MAX_BYTES", 5 * 1024 * 1024)
    LOG_BACKUP_COUNT = _get_int("LOG_BACKUP_COUNT", 5)


config = Config()