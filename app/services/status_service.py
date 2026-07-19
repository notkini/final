from datetime import date, datetime, time, timezone

from sqlalchemy import select
from werkzeug.exceptions import NotFound

from app.database import get_session
from app.models import (
    Machine,
    MonitorHeartbeat,
    ShiftPerformance,
)

from app.shifts import get_shift_for_datetime
from app.services.config_service import get_current_assignment


def get_machine_status():
    now = datetime.now(timezone.utc)

    with get_session() as session:
        assignment = get_current_assignment(session)

        if assignment is None:
            return {
                "assigned": False,
                "machine_id": None,
                "machine": None,
                "status": "UNASSIGNED",
                "current_shift": None,
                "uptime_seconds": 0,
                "downtime_seconds": 0,
                "efficiency_pct": 0,
                "last_updated": None,
                "message": "No machine assigned",
            }

        machine = session.get(
            Machine,
            assignment.machine_id,
        )

        if machine is None:
            raise NotFound("Assigned machine does not exist")

        heartbeat = (
            session.scalars(
                select(MonitorHeartbeat)
                .where(
                    MonitorHeartbeat.machine_id == machine.id
                )
                .order_by(
                    MonitorHeartbeat.last_beat.desc()
                )
                .limit(1)
            )
            .first()
        )

        try:
            shift_window = get_shift_for_datetime(
                machine.id,
                now,
            )
        except ValueError:
            shift_window = None

        performance = None

        if shift_window is not None:
            shift_date_value = datetime.combine(
                shift_window.shift_date,
                time.min,
            )

            performance = (
                session.scalars(
                    select(ShiftPerformance)
                    .where(
                        ShiftPerformance.machine_id == machine.id
                    )
                    .where(
                        ShiftPerformance.shift_date == shift_date_value
                    )
                    .where(
                        ShiftPerformance.shift_name == shift_window.shift_name
                    )
                )
                .first()
            )

        return {
            "assigned": True,
            
            "machine_id": machine.id,
            "machine": machine.machine_name,

            "status": (
                heartbeat.current_state
                if heartbeat is not None
                else "UNKNOWN"
            ),

            "current_shift": (
                shift_window.shift_name
                if shift_window is not None
                else None
            ),

            "uptime_seconds": (
                performance.up_seconds
                if performance is not None
                else 0
            ),

            "downtime_seconds": (
                performance.down_seconds
                if performance is not None
                else 0
            ),

            "efficiency_pct": (
                performance.efficiency_pct
                if performance is not None
                else 0
            ),

            "last_updated": (
                heartbeat.last_beat.isoformat()
                if heartbeat is not None
                else None
            ),
        }
    

def get_dashboard_date(
    machine_id: int,
    now: datetime,
) -> date:
    try:
        window = get_shift_for_datetime(
            machine_id,
            now,
        )

        return window.shift_date

    except ValueError:
        return now.date()
    

def serialize_performance(performance):
    return {
        "date": performance.shift_date.date().isoformat(),
        "shift": performance.shift_name,
        "uptime_seconds": performance.up_seconds,
        "downtime_seconds": performance.down_seconds,
        "efficiency_pct": performance.efficiency_pct,
        "is_final": performance.is_final,
    }


def calculate_weighted_efficiency(performances):
    total_up = sum(
        row.up_seconds
        for row in performances
    )

    total_down = sum(
        row.down_seconds
        for row in performances
    )

    total_elapsed = total_up + total_down

    efficiency = (
        round(
            total_up / total_elapsed * 100,
            2,
        )
        if total_elapsed > 0
        else 0.0
    )

    return (
        total_up,
        total_down,
        efficiency,
    )


def serialize_machine_config(
    machine,
    shifts,
    meals,
):
    shift_map = {
        shift.shift_name: shift
        for shift in shifts
    }

    meal_map = {
        meal.meal_name: meal
        for meal in meals
    }

    return {
        "machine_id": machine.id,
        "machine": machine.machine_name,

        "shift_a_start":
            shift_map["A"].start_time.strftime("%H:%M"),
        "shift_a_end":
            shift_map["A"].end_time.strftime("%H:%M"),

        "shift_b_start":
            shift_map["B"].start_time.strftime("%H:%M"),
        "shift_b_end":
            shift_map["B"].end_time.strftime("%H:%M"),

        "shift_c_start":
            shift_map["C"].start_time.strftime("%H:%M"),
        "shift_c_end":
            shift_map["C"].end_time.strftime("%H:%M"),

        "breakfast_time": (
            meal_map["BREAKFAST"].start_time.strftime("%H:%M")
            if "BREAKFAST" in meal_map
            else "09:00"
        ),

        "lunch_time": (
            meal_map["LUNCH"].start_time.strftime("%H:%M")
            if "LUNCH" in meal_map
            else "13:00"
        ),

        "dinner_time": (
            meal_map["DINNER"].start_time.strftime("%H:%M")
            if "DINNER" in meal_map
            else "20:00"
        ),
    }