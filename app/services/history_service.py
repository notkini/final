from calendar import monthrange
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from werkzeug.exceptions import BadRequest, NotFound

from app.database import get_session
from app.models import Machine, ShiftPerformance

from app.services.config_service import get_current_machine
from app.services.status_service import (
    get_dashboard_date,
    calculate_weighted_efficiency,
    serialize_performance,
)


def fetch_history_rows(
    session,
    machine_id,
    from_date,
    to_date,
    selected_shifts,
):
    start_datetime = datetime.combine(
        from_date,
        time.min,
    )

    end_datetime = datetime.combine(
        to_date,
        time.min,
    )

    return (
        session.scalars(
            select(ShiftPerformance)
            .where(
                ShiftPerformance.machine_id == machine_id
            )
            .where(
                ShiftPerformance.shift_date >= start_datetime
            )
            .where(
                ShiftPerformance.shift_date <= end_datetime
            )
            .where(
                ShiftPerformance.shift_name.in_(selected_shifts)
            )
            .order_by(
                ShiftPerformance.shift_date.asc(),
                ShiftPerformance.shift_name.asc(),
            )
        )
        .all()
    )


def build_daily_summary(rows):
    daily_map = {}

    for row in rows:

        key = row.shift_date.date().isoformat()

        if key not in daily_map:

            daily_map[key] = {
                "date": key,
                "uptime_seconds": 0.0,
                "downtime_seconds": 0.0,
            }

        daily_map[key]["uptime_seconds"] += row.up_seconds
        daily_map[key]["downtime_seconds"] += row.down_seconds

    daily_rows = []

    for day in daily_map.values():

        elapsed = (
            day["uptime_seconds"]
            + day["downtime_seconds"]
        )

        day["efficiency_pct"] = (
            round(
                day["uptime_seconds"] / elapsed * 100,
                2,
            )
            if elapsed > 0
            else 0.0
        )

        daily_rows.append(day)

    return daily_rows


def get_seven_day_history():
    now = datetime.now(timezone.utc)

    with get_session() as session:
        
        machine = get_current_machine(session)
        
        if machine is None:
            return {
                "assigned": False,
                "machine_id": None,
                "machine": None,
                "from_date": None,
                "to_date": None,
                "total_uptime_seconds": 0,
                "total_downtime_seconds": 0,
                "weighted_efficiency_pct": 0,
                "daily": [],
                "shifts": [],
            }

        end_date = get_dashboard_date(
            machine.id,
            now,
        )

        start_date = end_date - timedelta(days=6)

        rows = fetch_history_rows(
            session,
            machine.id,
            start_date,
            end_date,
            {"A", "B", "C"},
        )
        
        total_up, total_down, weighted_efficiency = (
            calculate_weighted_efficiency(rows)
        )

        return {
            "assigned": True,
            "machine_id": machine.id,
            "machine": machine.machine_name,
            "from_date": start_date.isoformat(),
            "to_date": end_date.isoformat(),
            "total_uptime_seconds": total_up,
            "total_downtime_seconds": total_down,
            "weighted_efficiency_pct": weighted_efficiency,
            "daily": build_daily_summary(rows),
            "shifts": [
                serialize_performance(row)
                for row in rows
            ],
        }


def get_custom_history(
    machine_id,
    from_date,
    to_date,
    shifts,
):
    if from_date > to_date:
        raise BadRequest(
            "From date cannot be after to date"
        )

    selected_shifts = {
        shift.strip().upper()
        for shift in shifts.split(",")
        if shift.strip()
    }

    if not selected_shifts:
        raise BadRequest(
            "Select at least one shift"
        )

    if selected_shifts - {"A", "B", "C"}:
        raise BadRequest(
            "Invalid shift selection"
        )

    with get_session() as session:

        machine = session.get(
            Machine,
            machine_id,
        )

        if machine is None:
            raise NotFound(
                "Machine does not exist"
            )

        rows = fetch_history_rows(
            session,
            machine.id,
            from_date,
            to_date,
            selected_shifts,
        )
        
        total_up, total_down, weighted_efficiency = (
            calculate_weighted_efficiency(rows)
        )
        
        return {
            "assigned": True,
            "machine_id": machine.id,
            "machine": machine.machine_name,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "selected_shifts": sorted(selected_shifts),
            "total_uptime_seconds": total_up,
            "total_downtime_seconds": total_down,
            "weighted_efficiency_pct": weighted_efficiency,
            "daily": build_daily_summary(rows),
            "shifts": [
                serialize_performance(row)
                for row in rows
            ],
        }


def get_history(
    range_type,
    year=None,
    month=None,
    date=None,
):
    now = datetime.now(timezone.utc)

    with get_session() as session:

        machine = get_current_machine(session)

        if machine is None:
            return {
                "assigned": False,
                "machine_id": None,
                "machine": None,
                "from_date": None,
                "to_date": None,
                "total_uptime_seconds": 0,
                "total_downtime_seconds": 0,
                "weighted_efficiency_pct": 0,
                "daily": [],
                "shifts": [],
            }

        dashboard_date = get_dashboard_date(
            machine.id,
            now,
        )

        if range_type == "7d":

            start_date = dashboard_date - timedelta(days=6)
            end_date = dashboard_date

        elif range_type == "month":

            selected_year = year or dashboard_date.year
            selected_month = month or dashboard_date.month

            start_date = datetime(
                selected_year,
                selected_month,
                1,
            ).date()

            last_day = monthrange(
                selected_year,
                selected_month,
            )[1]

            end_date = datetime(
                selected_year,
                selected_month,
                last_day,
            ).date()

        elif range_type == "date":

            if not date:
                raise BadRequest("Date is required")

            selected_date = datetime.strptime(
                date,
                "%Y-%m-%d",
            ).date()

            start_date = selected_date
            end_date = selected_date

        elif range_type == "year":

            selected_year = year or dashboard_date.year

            start_date = datetime(
                selected_year,
                1,
                1,
            ).date()

            end_date = datetime(
                selected_year,
                12,
                31,
            ).date()

        else:
            raise BadRequest("Invalid history range")

        return get_custom_history(
            machine.id,
            start_date,
            end_date,
            "A,B,C",
        )