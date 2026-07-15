"""
Main monitoring service.

The monitor dynamically reads the currently assigned machine from
monitor_assignments.

Every machine event, heartbeat, and shift calculation is linked to the
assigned machine.
"""

import logging
import threading
import time as time_module
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app import offline_queue
from app.backfill import backfill_shift_performance
from app.calculations import (
    MonitoringWindow,
    calculate_shift_performance,
    get_last_state_before,
)
from app.config import config
from app.database import (
    get_session,
    is_postgres_reachable,
)
from app.gpio_reader import GpioReader
from app.logging_config import setup_logging
from app.models import (
    Machine,
    MachineEvent,
    MonitorAssignment,
    MonitorHeartbeat,
    ShiftPerformance,
)
from app.shifts import get_shift_for_datetime


logger = logging.getLogger("weldomat.monitor")

_stop_event = threading.Event()

_machine_lock = threading.Lock()
_cached_machine_id = None


# ---------------------------------------------------------------------------
# Machine assignment
# ---------------------------------------------------------------------------

def _set_cached_machine_id(
    machine_id: int | None,
) -> None:
    global _cached_machine_id

    with _machine_lock:
        _cached_machine_id = machine_id


def _get_cached_machine_id() -> int | None:
    with _machine_lock:
        return _cached_machine_id


def _get_active_assignment(
    session,
) -> MonitorAssignment | None:
    """
    Return the currently active monitor assignment.
    """

    return session.scalars(
        select(MonitorAssignment)
        .where(
            MonitorAssignment.unassigned_at.is_(None)
        )
        .order_by(
            MonitorAssignment.assigned_at.desc()
        )
        .limit(1)
    ).first()


def _initialize_machine_assignment() -> int:
    """
    Load the current machine assignment.

    During the initial migration phase, if no assignment exists, assign
    the monitor to the first active machine automatically.
    """

    with get_session() as session:
        assignment = _get_active_assignment(session)

        if assignment is not None:
            machine_id = assignment.machine_id

        else:
            machine = session.scalars(
                select(Machine)
                .where(
                    Machine.is_active.is_(True)
                )
                .order_by(Machine.id.asc())
                .limit(1)
            ).first()

            if machine is None:
                raise RuntimeError(
                    "No active machine exists. "
                    "Create a machine before starting the monitor."
                )

            assignment = MonitorAssignment(
                machine_id=machine.id,
                assigned_at=datetime.now(
                    timezone.utc
                ),
                unassigned_at=None,
            )

            session.add(assignment)

            machine_id = machine.id

            logger.info(
                "No active assignment found. "
                "Automatically assigned monitor to machine_id=%s",
                machine_id,
            )

    _set_cached_machine_id(machine_id)

    return machine_id


def _refresh_machine_assignment() -> int | None:
    """
    Refresh the machine assignment from PostgreSQL.

    This allows a configuration page to switch machines without restarting
    the monitor service.
    """

    if not is_postgres_reachable():
        return _get_cached_machine_id()

    with get_session() as session:
        assignment = _get_active_assignment(session)

        machine_id = (
            assignment.machine_id
            if assignment is not None
            else None
        )

    previous_machine_id = _get_cached_machine_id()

    if machine_id != previous_machine_id:
        logger.info(
            "Monitor assignment changed: %s -> %s",
            previous_machine_id,
            machine_id,
        )

        _set_cached_machine_id(machine_id)

    return machine_id


def _require_machine_id() -> int:
    machine_id = _refresh_machine_assignment()

    if machine_id is None:
        raise RuntimeError(
            "Monitor is not assigned to a machine"
        )

    return machine_id


# ---------------------------------------------------------------------------
# Event ingestion
# ---------------------------------------------------------------------------

def _insert_event_if_new(
    session,
    machine_id: int,
    state: str,
    event_time: datetime,
    source: str,
    event_key: str,
) -> bool:
    """
    Insert one machine transition event.
    """

    statement = (
        insert(MachineEvent)
        .values(
            machine_id=machine_id,
            event_key=event_key,
            state=state,
            event_time=event_time,
            source=source,
        )
        .on_conflict_do_nothing(
            index_elements=["event_key"]
        )
    )

    result = session.execute(
        statement.returning(MachineEvent.id)
    )

    return (
        result.scalar_one_or_none()
        is not None
    )


def handle_state_change(
    state: str,
    event_time: datetime,
):
    """
    Called by GpioReader for every genuine transition.
    """

    if event_time.tzinfo is None:
        raise ValueError(
            "event_time must be timezone-aware"
        )

    machine_id = _require_machine_id()

    event_key = str(uuid.uuid4())

    source = (
        "gpio"
        if not config.SIMULATION_MODE
        else "simulation"
    )

    if is_postgres_reachable():
        try:
            with get_session() as session:
                inserted = _insert_event_if_new(
                    session=session,
                    machine_id=machine_id,
                    state=state,
                    event_time=event_time,
                    source=source,
                    event_key=event_key,
                )

            if inserted:
                logger.info(
                    "Recorded machine_id=%s %s event @ %s",
                    machine_id,
                    state,
                    event_time,
                )

            else:
                logger.info(
                    "Duplicate event ignored: %s",
                    event_key,
                )

        except Exception:
            logger.exception(
                "Postgres event write failed. "
                "Falling back to offline queue."
            )

            offline_queue.enqueue_event(
                machine_id=machine_id,
                state=state,
                event_time=event_time,
                source=source,
                event_key=event_key,
            )

    else:
        offline_queue.enqueue_event(
            machine_id=machine_id,
            state=state,
            event_time=event_time,
            source=source,
            event_key=event_key,
        )

    try:
        recalculate_current_shift()

    except Exception:
        logger.exception(
            "Recalculation after event failed"
        )


# ---------------------------------------------------------------------------
# Recalculation
# ---------------------------------------------------------------------------

def _get_monitoring_windows(
    session,
    machine_id: int,
    window,
    as_of: datetime,
) -> list[MonitoringWindow]:
    """
    Return assignment periods overlapping the shift.
    """

    effective_end = min(
        window.end,
        as_of,
    )

    assignments = session.scalars(
        select(MonitorAssignment)
        .where(
            MonitorAssignment.machine_id
            == machine_id
        )
        .where(
            MonitorAssignment.assigned_at
            < effective_end
        )
        .where(
            (
                MonitorAssignment.unassigned_at.is_(None)
            )
            | (
                MonitorAssignment.unassigned_at
                > window.start
            )
        )
        .order_by(
            MonitorAssignment.assigned_at.asc()
        )
    ).all()

    monitoring_windows = []

    for assignment in assignments:
        monitoring_start = max(
            assignment.assigned_at,
            window.start,
        )

        assignment_end = (
            assignment.unassigned_at
            if assignment.unassigned_at is not None
            else effective_end
        )

        monitoring_end = min(
            assignment_end,
            effective_end,
        )

        if monitoring_end <= monitoring_start:
            continue

        monitoring_windows.append(
            MonitoringWindow(
                start=monitoring_start,
                end=monitoring_end,
            )
        )

    return monitoring_windows


def recalculate_current_shift():
    """
    Recalculate the active shift for the currently assigned machine.
    """

    if not is_postgres_reachable():
        logger.debug(
            "Skipping recalculation -- Postgres unreachable"
        )
        return

    machine_id = _require_machine_id()

    now = datetime.now(timezone.utc)

    window = get_shift_for_datetime(
        machine_id,
        now,
    )

    with get_session() as session:
        monitoring_windows = _get_monitoring_windows(
            session=session,
            machine_id=machine_id,
            window=window,
            as_of=now,
        )

        if not monitoring_windows:
            logger.debug(
                "No monitoring window for machine_id=%s",
                machine_id,
            )
            return

        events_in_window = session.scalars(
            select(MachineEvent)
            .where(
                MachineEvent.machine_id
                == machine_id
            )
            .where(
                MachineEvent.event_time
                >= window.start
            )
            .where(
                MachineEvent.event_time
                < window.end
            )
            .order_by(
                MachineEvent.event_time.asc()
            )
        ).all()

        last_event_before = session.scalars(
            select(MachineEvent)
            .where(
                MachineEvent.machine_id
                == machine_id
            )
            .where(
                MachineEvent.event_time
                < window.start
            )
            .order_by(
                MachineEvent.event_time.desc()
            )
            .limit(1)
        ).all()

        initial_state = get_last_state_before(
            last_event_before
        )

        result = calculate_shift_performance(
            window=window,
            events=events_in_window,
            as_of=now,
            monitoring_windows=monitoring_windows,
            initial_state=initial_state,
        )

        shift_date_value = datetime.combine(
            window.shift_date,
            datetime.min.time(),
        )

        row = session.scalars(
            select(ShiftPerformance)
            .where(
                ShiftPerformance.machine_id
                == machine_id
            )
            .where(
                ShiftPerformance.shift_date
                == shift_date_value
            )
            .where(
                ShiftPerformance.shift_name
                == window.shift_name
            )
        ).first()

        if row is None:
            row = ShiftPerformance(
                machine_id=machine_id,
                shift_date=shift_date_value,
                shift_name=window.shift_name,
            )

            session.add(row)

        row.up_seconds = result.up_seconds
        row.down_seconds = result.down_seconds
        row.efficiency_pct = result.efficiency_pct
        row.is_final = result.is_final

    logger.debug(
        "machine_id=%s Shift %s (%s): "
        "up=%.0fs down=%.0fs eff=%.1f%% final=%s",
        machine_id,
        window.shift_name,
        window.shift_date,
        result.up_seconds,
        result.down_seconds,
        result.efficiency_pct,
        result.is_final,
    )


def _recalculation_loop():
    while not _stop_event.is_set():
        try:
            recalculate_current_shift()
            backfill_shift_performance()

        except Exception:
            logger.exception(
                "Periodic recalculation/backfill failed"
            )

        _stop_event.wait(
            config.RECALC_INTERVAL_SECONDS
        )


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------

def _heartbeat_loop(
    gpio_reader: GpioReader,
):
    while not _stop_event.is_set():
        try:
            if is_postgres_reachable():
                machine_id = _refresh_machine_assignment()

                with get_session() as session:
                    row = session.get(
                        MonitorHeartbeat,
                        1,
                    )

                    if row is None:
                        row = MonitorHeartbeat(
                            id=1,
                            machine_id=machine_id,
                            last_beat=datetime.now(
                                timezone.utc
                            ),
                        )

                        session.add(row)

                    row.machine_id = machine_id

                    row.last_beat = datetime.now(
                        timezone.utc
                    )

                    row.current_state = (
                        gpio_reader.current_state
                    )

        except Exception:
            logger.exception(
                "Heartbeat write failed"
            )

        _stop_event.wait(
            config.HEARTBEAT_INTERVAL_SECONDS
        )


# ---------------------------------------------------------------------------
# Offline queue synchronization
# ---------------------------------------------------------------------------

def _offline_sync_loop():
    while not _stop_event.is_set():
        try:
            if (
                offline_queue.pending_count() > 0
                and is_postgres_reachable()
            ):
                pending = (
                    offline_queue.fetch_all_pending()
                )

                synced_ids = []

                with get_session() as session:
                    for (
                        row_id,
                        event_key,
                        machine_id,
                        state,
                        event_time_str,
                        source,
                    ) in pending:
                        event_time = datetime.fromisoformat(
                            event_time_str
                        )

                        if event_time.tzinfo is None:
                            event_time = (
                                event_time.replace(
                                    tzinfo=timezone.utc
                                )
                            )

                        _insert_event_if_new(
                            session=session,
                            machine_id=machine_id,
                            state=state,
                            event_time=event_time,
                            source=source,
                            event_key=event_key,
                        )

                        synced_ids.append(row_id)

                offline_queue.delete_synced(
                    synced_ids
                )

                logger.info(
                    "Synced %d queued event(s) "
                    "into Postgres",
                    len(synced_ids),
                )

                recalculate_current_shift()
                backfill_shift_performance()

        except Exception:
            logger.exception(
                "Offline queue sync failed"
            )

        _stop_event.wait(
            config.OFFLINE_SYNC_INTERVAL_SECONDS
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    setup_logging()

    logger.info(
        "Starting machine monitor "
        "(simulation_mode=%s)",
        config.SIMULATION_MODE,
    )

    if not is_postgres_reachable():
        raise RuntimeError(
            "Postgres must be reachable during monitor startup "
            "to resolve the machine assignment"
        )

    machine_id = _initialize_machine_assignment()

    logger.info(
        "Monitor assigned to machine_id=%s",
        machine_id,
    )

    try:
        backfill_shift_performance()

    except Exception:
        logger.exception(
            "Startup backfill failed"
        )

    gpio_reader = GpioReader(
        on_state_change=handle_state_change
    )

    gpio_reader.start()

    threads = [
        threading.Thread(
            target=_recalculation_loop,
            daemon=True,
        ),
        threading.Thread(
            target=_heartbeat_loop,
            args=(gpio_reader,),
            daemon=True,
        ),
        threading.Thread(
            target=_offline_sync_loop,
            daemon=True,
        ),
    ]

    for thread in threads:
        thread.start()

    try:
        while True:
            time_module.sleep(1)

    except KeyboardInterrupt:
        logger.info(
            "Shutdown requested -- stopping monitor"
        )

        _stop_event.set()

        gpio_reader.stop()

        for thread in threads:
            thread.join(timeout=5)


if __name__ == "__main__":
    main()