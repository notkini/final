"""
Creates and updates shift_performance rows for every monitored machine.

Performance is calculated only during periods where the Raspberry Pi was
assigned to the machine. Unmonitored time is not counted as downtime.
"""
import logging
from datetime import datetime, time, timezone

from sqlalchemy import select

from app.services.excel_report_service import update_shift_report
from app.database import get_session, is_postgres_reachable
from app.models import (
    Machine,
    MachineEvent,
    MonitorAssignment,
    ShiftPerformance,
)
from app.shifts import get_all_shifts_for_date, LOCAL_TZ
from app.calculations import (
    MonitoringWindow,
    calculate_shift_performance,
    get_last_state_before,
)


logger = logging.getLogger("weldomat.backfill")


def _local_midnight_datetime(shift_date) -> datetime:
    return datetime.combine(
        shift_date,
        time.min,
    )


def _get_first_assignment_time(
    session,
    machine_id: int,
) -> datetime | None:
    """
    Return when monitoring first started for the machine.
    """

    return session.scalars(
        select(MonitorAssignment.assigned_at)
        .where(
            MonitorAssignment.machine_id == machine_id
        )
        .order_by(
            MonitorAssignment.assigned_at.asc()
        )
        .limit(1)
    ).first()


def _get_monitoring_windows(
    session,
    machine_id: int,
    window,
    as_of: datetime,
) -> list[MonitoringWindow]:
    """
    Return assignment periods overlapping a shift window.
    """

    effective_end = min(
        window.end,
        as_of,
    )

    assignments = session.scalars(
        select(MonitorAssignment)
        .where(
            MonitorAssignment.machine_id == machine_id
        )
        .where(
            MonitorAssignment.assigned_at < effective_end
        )
        .where(
            (
                MonitorAssignment.unassigned_at.is_(None)
            )
            | (
                MonitorAssignment.unassigned_at > window.start
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


def _save_shift_performance(
    session,
    machine_id: int,
    window,
    as_of: datetime,
) -> None:
    """
    Calculate and save one machine shift.
    """

    monitoring_windows = _get_monitoring_windows(
        session=session,
        machine_id=machine_id,
        window=window,
        as_of=as_of,
    )

    shift_date_value = _local_midnight_datetime(
        window.shift_date
    )

    row = session.scalars(
        select(ShiftPerformance)
        .where(
            ShiftPerformance.machine_id == machine_id
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
        if not monitoring_windows:
            return

        row = ShiftPerformance(
            machine_id=machine_id,
            shift_date=shift_date_value,
            shift_name=window.shift_name,
        )

        session.add(row)

    events_in_window = session.scalars(
        select(MachineEvent)
        .where(
            MachineEvent.machine_id == machine_id
        )
        .where(
            MachineEvent.event_time >= window.start
        )
        .where(
            MachineEvent.event_time < window.end
        )
        .order_by(
            MachineEvent.event_time.asc()
        )
    ).all()

    last_event_before = session.scalars(
        select(MachineEvent)
        .where(
            MachineEvent.machine_id == machine_id
        )
        .where(
            MachineEvent.event_time < window.start
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
        as_of=as_of,
        monitoring_windows=monitoring_windows,
        initial_state=initial_state,
    )

    row.up_seconds = result.up_seconds
    row.down_seconds = result.down_seconds
    row.efficiency_pct = result.efficiency_pct
    row.is_final = result.is_final
    session.flush()
    
    machine = session.get(
        Machine,
        machine_id,
    )

    try:
        update_shift_report(
            machine_name=machine.machine_name,
            shift_date=window.shift_date,
            shift_name=window.shift_name,
            up_seconds=result.up_seconds,
            down_seconds=result.down_seconds,
            efficiency=result.efficiency_pct,
        )
    except Exception:
        logger.exception("Failed to update Excel report")


def _backfill_machine(
    session,
    machine_id: int,
    as_of: datetime,
) -> int:
    """
    Backfill all monitored shifts for one machine.
    """

    first_assignment_time = _get_first_assignment_time(
        session,
        machine_id,
    )

    if first_assignment_time is None:
        return 0

    first_local_date = (
        first_assignment_time
        .astimezone(LOCAL_TZ)
        .date()
    )

    last_local_date = (
        as_of
        .astimezone(LOCAL_TZ)
        .date()
    )

    processed = 0
    current_date = first_local_date

    while current_date <= last_local_date:
        windows = get_all_shifts_for_date(
            machine_id,
            current_date,
        )

        for window in windows:
            if window.start > as_of:
                continue

            _save_shift_performance(
                session=session,
                machine_id=machine_id,
                window=window,
                as_of=as_of,
            )

            processed += 1

        current_date = current_date.fromordinal(
            current_date.toordinal() + 1
        )

    return processed


def backfill_shift_performance(
    as_of: datetime | None = None,
) -> int:
    """
    Backfill shift performance for every active machine.
    """

    if not is_postgres_reachable():
        logger.debug(
            "Skipping backfill -- Postgres unreachable"
        )
        return 0

    if as_of is None:
        as_of = datetime.now(timezone.utc)

    if as_of.tzinfo is None:
        raise ValueError(
            "as_of must be timezone-aware"
        )

    with get_session() as session:
        machines = session.scalars(
            select(Machine)
            .where(Machine.is_active.is_(True))
            .order_by(Machine.id.asc())
        ).all()

        processed = 0

        for machine in machines:
            processed += _backfill_machine(
                session=session,
                machine_id=machine.id,
                as_of=as_of,
            )

    logger.info(
        "Backfilled %d shift performance row(s)",
        processed,
    )

    return processed
