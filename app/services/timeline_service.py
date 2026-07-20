from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.database import get_session
from app.models import MachineEvent, MealConfig, MonitorAssignment
from app.shifts import get_all_shifts_for_date

from app.services.config_service import get_current_machine
from app.services.status_service import get_dashboard_date


# Meal start times are entered and stored as plant-local wall-clock
# time (matching shift start/end times), not UTC. This must be used
# whenever a naive Time value is turned into an absolute instant, or
# meal blocks will drift off by the plant's UTC offset.
PLANT_TIMEZONE = ZoneInfo("Asia/Kolkata")


def get_timeline(selected_date=None):
    now = datetime.now(timezone.utc)

    with get_session() as session:

        machine = get_current_machine(session)

        if machine is None:
            return {
                "assigned": False,
                "machine_id": None,
                "machine": None,
                "date": None,
                "range_start": None,
                "range_end": None,
                "events": [],
                "meals": [],
                "gaps": [],
            }

        target_date = (
            selected_date
            or get_dashboard_date(
                machine.id,
                now,
            )
        )

        windows = get_all_shifts_for_date(
            machine.id,
            target_date,
        )

        range_start = min(window.start for window in windows)
        range_end = max(window.end for window in windows)

        events = (
            session.scalars(
                select(MachineEvent)
                .where(MachineEvent.machine_id == machine.id)
                .where(MachineEvent.event_time >= range_start)
                .where(MachineEvent.event_time < range_end)
                .order_by(MachineEvent.event_time.asc())
            )
            .all()
        )

        # -----------------------------
        # Determine unmonitored gaps
        # -----------------------------
        # A machine can be unassigned and later reassigned within the
        # same window (e.g. swapped out for another machine for a
        # while). Event history has no signal for that on its own —
        # the last known state would otherwise just get extrapolated
        # straight across the gap. MonitorAssignment is the source of
        # truth for when this machine actually had a monitor attached.
        assignments = (
            session.scalars(
                select(MonitorAssignment)
                .where(MonitorAssignment.machine_id == machine.id)
                .where(MonitorAssignment.assigned_at < range_end)
                .where(
                    (MonitorAssignment.unassigned_at.is_(None))
                    | (MonitorAssignment.unassigned_at > range_start)
                )
                .order_by(MonitorAssignment.assigned_at.asc())
            )
            .all()
        )

        monitored_windows = []

        for assignment in assignments:
            window_start = max(assignment.assigned_at, range_start)
            window_end = min(assignment.unassigned_at or range_end, range_end)

            if window_end > window_start:
                monitored_windows.append((window_start, window_end))

        monitored_windows.sort(key=lambda window: window[0])

        merged_windows = []

        for window_start, window_end in monitored_windows:
            if merged_windows and window_start <= merged_windows[-1][1]:
                merged_windows[-1] = (
                    merged_windows[-1][0],
                    max(merged_windows[-1][1], window_end),
                )
            else:
                merged_windows.append((window_start, window_end))

        gaps = []
        cursor = range_start

        for window_start, window_end in merged_windows:
            if window_start > cursor:
                gaps.append((cursor, window_start))
            cursor = max(cursor, window_end)

        if cursor < range_end:
            gaps.append((cursor, range_end))

        # -----------------------------
        # Read meal configuration
        # -----------------------------
        meal_configs = (
            session.scalars(
                select(MealConfig)
                .where(MealConfig.machine_id == machine.id)
            )
            .all()
        )

        meals = []

        for meal in meal_configs:
            meal_start_local = datetime.combine(
                target_date,
                meal.start_time,
                tzinfo=PLANT_TIMEZONE,
            )

            meal_start = meal_start_local.astimezone(timezone.utc)

            # Handle overnight shift windows
            if meal_start < range_start:
                meal_start += timedelta(days=1)

            meal_end = meal_start + timedelta(hours=1)

            if meal_start <= range_end:
                meals.append(
                    {
                        "name": meal.meal_name,
                        "start": meal_start.isoformat(),
                        "end": meal_end.isoformat(),
                    }
                )

        return {
            "assigned": True,
            "machine_id": machine.id,
            "machine": machine.machine_name,
            "date": target_date.isoformat(),
            "range_start": range_start.isoformat(),
            "range_end": range_end.isoformat(),

            "events": [
                {
                    "state": event.state,
                    "event_time": event.event_time.isoformat(),
                    "source": event.source,
                }
                for event in events
            ],

            "meals": meals,

            "gaps": [
                {
                    "start": gap_start.isoformat(),
                    "end": gap_end.isoformat(),
                }
                for gap_start, gap_end in gaps
            ],
        }