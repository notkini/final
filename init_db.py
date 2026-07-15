"""
One-time setup script: verifies that PostgreSQL is reachable and ensures the
local offline-queue SQLite file/table exists.

Run this only after:

    alembic upgrade head

The PostgreSQL schema is created only by Alembic. Do not use
Base.metadata.create_all() here, because that bypasses migration history.
"""
import logging

from app.logging_config import setup_logging
from app.database import is_postgres_reachable
from app import offline_queue

logger = logging.getLogger("weldomat.init_db")


def main():
    setup_logging()

    if not is_postgres_reachable():
        logger.error(
            "Cannot reach Postgres at the configured DATABASE_URL. "
            "Check docker-compose is up (`docker compose up -d`) and your "
            ".env values."
        )
        raise SystemExit(1)

    logger.info("Postgres is reachable and Alembic schema is expected to be ready.")

    logger.info("Ensuring local offline-queue SQLite file/table exists...")
    offline_queue.pending_count()
    logger.info("Offline queue ready.")

    logger.info("Done. You can now run: python -m app.monitor")


if __name__ == "__main__":
    main()