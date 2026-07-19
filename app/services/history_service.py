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

        start_datetime = datetime.combine(
            start_date,
            time.min,
        )

        end_datetime = datetime.combine(
            end_date,
            time.min,
        )

        rows = (
            session.scalars(
                select(ShiftPerformance)
                .where(
                    ShiftPerformance.machine_id == machine.id
                )
                .where(
                    ShiftPerformance.shift_date >= start_datetime
                )
                .where(
                    ShiftPerformance.shift_date <= end_datetime
                )
                .order_by(
                    ShiftPerformance.shift_date.asc(),
                    ShiftPerformance.shift_name.asc(),
                )
            )
            .all()
        )

        total_up, total_down, weighted_efficiency = (
            calculate_weighted_efficiency(rows)
        )

        daily_map = {}

        for row in rows:
            date_key = row.shift_date.date().isoformat()

            if date_key not in daily_map:
                daily_map[date_key] = {
                    "date": date_key,
                    "uptime_seconds": 0.0,
                    "downtime_seconds": 0.0,
                }

            daily_map[date_key]["uptime_seconds"] += row.up_seconds
            daily_map[date_key]["downtime_seconds"] += row.down_seconds

        daily_rows = []

        for daily_row in daily_map.values():
            elapsed = (
                daily_row["uptime_seconds"]
                + daily_row["downtime_seconds"]
            )

            daily_row["efficiency_pct"] = (
                round(
                    daily_row["uptime_seconds"]
                    / elapsed
                    * 100,
                    2,
                )
                if elapsed > 0
                else 0.0
            )

            daily_rows.append(daily_row)

        return {
            "assigned": True,
            "machine_id": machine.id,
            "machine": machine.machine_name,
            "from_date": start_date.isoformat(),
            "to_date": end_date.isoformat(),
            "total_uptime_seconds": total_up,
            "total_downtime_seconds": total_down,
            "weighted_efficiency_pct": weighted_efficiency,
            "daily": daily_rows,
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

    start_datetime = datetime.combine(
        from_date,
        time.min,
    )

    end_datetime = datetime.combine(
        to_date,
        time.min,
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

        rows = (
            session.scalars(
                select(ShiftPerformance)
                .where(
                    ShiftPerformance.machine_id == machine.id
                )
                .where(
                    ShiftPerformance.shift_date >= start_datetime
                )
                .where(
                    ShiftPerformance.shift_date <= end_datetime
                )
                .where(
                    ShiftPerformance.shift_name.in_(
                        selected_shifts
                    )
                )
                .order_by(
                    ShiftPerformance.shift_date.asc(),
                    ShiftPerformance.shift_name.asc(),
                )
            )
            .all()
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
            "selected_shifts": sorted(
                selected_shifts
            ),
            "total_uptime_seconds": total_up,
            "total_downtime_seconds": total_down,
            "weighted_efficiency_pct": weighted_efficiency,
            "rows": [
                serialize_performance(row)
                for row in rows
            ],
        }