"""
Local SQLite queue used ONLY as a buffer for MachineEvent rows when
Postgres is unreachable (network blip, container restart, etc). It is not
a second source of truth -- monitor.py drains it into Postgres as soon as
connectivity returns (checked every OFFLINE_SYNC_INTERVAL_SECONDS) and
never reads from it for calculations.
"""
import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import config

logger = logging.getLogger("weldomat.offline_queue")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS queued_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT NOT NULL UNIQUE,
    machine_id INTEGER NOT NULL,
    state TEXT NOT NULL,
    event_time TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'gpio',
    queued_at TEXT NOT NULL
);
"""


def _ensure_dir():
    directory = os.path.dirname(config.OFFLINE_QUEUE_PATH)

    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


@contextmanager
def _conn():
    _ensure_dir()
    conn = sqlite3.connect(config.OFFLINE_QUEUE_PATH)

    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def enqueue_event(
    machine_id: int,
    state: str,
    event_time: datetime,
    source: str = "gpio",
    event_key: str | None = None,
) -> str:
    """
    Save an event locally when PostgreSQL cannot be reached.

    event_key is returned so monitor.py can use the same UUID when it later
    inserts into PostgreSQL. This makes retrying safe and idempotent.
    """
    if event_time.tzinfo is None:
        raise ValueError("event_time must be timezone-aware")

    event_key = event_key or str(uuid.uuid4())

    with _conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO queued_events
            (
                event_key,
                machine_id,
                state,
                event_time,
                source,
                queued_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_key,
                machine_id,
                state,
                event_time.isoformat(),
                source,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    logger.warning(
        "Postgres unreachable -- queued %s event for machine %s @ %s locally",
        state,
        machine_id,
        event_time,
    )

    return event_key


def pending_count() -> int:
    with _conn() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM queued_events")
        return cursor.fetchone()[0]


def fetch_all_pending():
    """
    Return rows in original event-time order.

    Tuple format:
        (id, event_key, machine_id, state, event_time, source)
    """
    with _conn() as conn:
        cursor = conn.execute(
            """
            SELECT
                id,
                event_key,
                machine_id,
                state,
                event_time,
                source
            FROM queued_events
            ORDER BY event_time ASC, id ASC
            """
        )
        return cursor.fetchall()


def delete_synced(ids: list[int]) -> None:
    if not ids:
        return

    with _conn() as conn:
        placeholders = ",".join("?" for _ in ids)

        conn.execute(
            f"DELETE FROM queued_events WHERE id IN ({placeholders})",
            ids,
        )