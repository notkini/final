"""
Manual development test for the missed-shift backfill feature.

Example:
    python scripts/backfill_test.py --as-of "2026-07-06T18:00:00+00:00"

This calculates every shift from the earliest machine_events row through
the supplied UTC time. It is for laptop testing only. Do not run it with
future dates on the real Raspberry Pi database.
"""
import argparse
from datetime import datetime

from app.logging_config import setup_logging
from app.backfill import backfill_shift_performance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--as-of",
        required=True,
        help="Timezone-aware UTC timestamp, for example 2026-07-06T18:00:00+00:00",
    )
    args = parser.parse_args()

    as_of = datetime.fromisoformat(args.as_of)

    if as_of.tzinfo is None:
        raise ValueError("--as-of must include a timezone such as +00:00")

    setup_logging()
    count = backfill_shift_performance(as_of=as_of)
    print(f"Processed {count} shift window(s).")


if __name__ == "__main__":
    main()