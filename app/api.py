from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select

from app.database import get_session
from app.models import (
    Machine,
    MachineEvent,
    MealConfig,
    MonitorAssignment,
    MonitorHeartbeat,
    ShiftConfig,
    ShiftPerformance,
)
from app.shifts import (
    get_all_shifts_for_date,
    get_shift_for_datetime,
)


BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
TEMPLATE_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


app = FastAPI(
    title="Machine Monitoring Dashboard"
)

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


class MachineConfigRequest(BaseModel):
    machine_id: int | None = None
    machine: str | None = None

    shift_a_start: str
    shift_a_end: str

    shift_b_start: str
    shift_b_end: str

    shift_c_start: str
    shift_c_end: str

    breakfast_time: str
    lunch_time: str
    dinner_time: str


def parse_time(value: str) -> time:
    try:
        return datetime.strptime(
            value,
            "%H:%M",
        ).time()

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid time '{value}'. "
                "Expected HH:MM"
            ),
        ) from exc


def generate_machine_code(
    machine_name: str,
) -> str:
    return (
        machine_name
        .strip()
        .upper()
        .replace(" ", "-")
    )


def get_current_assignment(session):
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


def get_current_machine(session) -> Machine:
    assignment = get_current_assignment(session)

    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail="No machine is currently assigned",
        )

    machine = session.get(
        Machine,
        assignment.machine_id,
    )

    if machine is None:
        raise HTTPException(
            status_code=404,
            detail="Assigned machine does not exist",
        )

    return machine


def validate_shift_schedule(shifts: dict) -> None:
    for shift_name in ("A", "B", "C"):
        if shifts[shift_name][0] == shifts[shift_name][1]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Shift {shift_name} start and end "
                    "cannot be the same"
                ),
            )

    if shifts["A"][1] != shifts["B"][0]:
        raise HTTPException(
            status_code=400,
            detail="Shift A end must equal Shift B start",
        )

    if shifts["B"][1] != shifts["C"][0]:
        raise HTTPException(
            status_code=400,
            detail="Shift B end must equal Shift C start",
        )

    if shifts["C"][1] != shifts["A"][0]:
        raise HTTPException(
            status_code=400,
            detail="Shift C end must equal Shift A start",
        )


def serialize_machine_config(
    machine: Machine,
    shifts,
    meals,
) -> dict:
    shift_map = {
        shift.shift_name: shift
        for shift in shifts
    }

    meal_map = {
        meal.meal_name: meal
        for meal in meals
    }

    for shift_name in ("A", "B", "C"):
        if shift_name not in shift_map:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Shift {shift_name} configuration "
                    f"is missing for {machine.machine_name}"
                ),
            )

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


def get_active_meal(
    session,
    machine_id: int,
    now: datetime,
):
    meals = session.scalars(
        select(MealConfig)
        .where(
            MealConfig.machine_id == machine_id
        )
    ).all()

    local_now = now.astimezone()

    for meal in meals:
        meal_start = datetime.combine(
            local_now.date(),
            meal.start_time,
            tzinfo=local_now.tzinfo,
        )

        meal_end = meal_start + timedelta(hours=1)

        if meal_start <= local_now < meal_end:
            return meal.meal_name

    return None


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


def serialize_performance(
    performance: ShiftPerformance,
) -> dict:
    return {
        "date": performance.shift_date.date().isoformat(),
        "shift": performance.shift_name,
        "uptime_seconds": performance.up_seconds,
        "downtime_seconds": performance.down_seconds,
        "efficiency_pct": performance.efficiency_pct,
        "is_final": performance.is_final,
    }


def calculate_weighted_efficiency(
    performances,
) -> tuple[float, float, float]:
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

    return total_up, total_down, efficiency


@app.get("/")
def dashboard_page():
    return FileResponse(
        TEMPLATE_DIR / "dashboard.html"
    )


@app.get("/setup")
def setup_page():
    return FileResponse(
        TEMPLATE_DIR / "setup.html"
    )


@app.get("/history")
def history_page():
    return FileResponse(
        TEMPLATE_DIR / "history.html"
    )


@app.get("/custom-history")
def custom_history_page():
    return FileResponse(
        TEMPLATE_DIR / "custom_history.html"
    )


@app.get("/api/config")
def get_config():
    with get_session() as session:
        machine = get_current_machine(session)

        shifts = session.scalars(
            select(ShiftConfig)
            .where(
                ShiftConfig.machine_id == machine.id
            )
        ).all()

        meals = session.scalars(
            select(MealConfig)
            .where(
                MealConfig.machine_id == machine.id
            )
        ).all()

        return serialize_machine_config(
            machine,
            shifts,
            meals,
        )


@app.get("/api/machines/{machine_id}/config")
def get_machine_config(machine_id: int):
    with get_session() as session:
        machine = session.get(
            Machine,
            machine_id,
        )

        if machine is None:
            raise HTTPException(
                status_code=404,
                detail="Machine does not exist",
            )

        shifts = session.scalars(
            select(ShiftConfig)
            .where(
                ShiftConfig.machine_id == machine.id
            )
        ).all()

        meals = session.scalars(
            select(MealConfig)
            .where(
                MealConfig.machine_id == machine.id
            )
        ).all()

        return serialize_machine_config(
            machine,
            shifts,
            meals,
        )


@app.post("/api/config")
def update_config(
    request: MachineConfigRequest,
):
    shift_times = {
        "A": (
            parse_time(request.shift_a_start),
            parse_time(request.shift_a_end),
        ),
        "B": (
            parse_time(request.shift_b_start),
            parse_time(request.shift_b_end),
        ),
        "C": (
            parse_time(request.shift_c_start),
            parse_time(request.shift_c_end),
        ),
    }

    meal_times = {
        "BREAKFAST": parse_time(
            request.breakfast_time
        ),
        "LUNCH": parse_time(
            request.lunch_time
        ),
        "DINNER": parse_time(
            request.dinner_time
        ),
    }

    validate_shift_schedule(shift_times)

    now = datetime.now(timezone.utc)

    with get_session() as session:
        if request.machine_id is not None:
            machine = session.get(
                Machine,
                request.machine_id,
            )

            if machine is None:
                raise HTTPException(
                    status_code=404,
                    detail="Selected machine does not exist",
                )

        else:
            machine_name = (
                request.machine or ""
            ).strip()

            if not machine_name:
                raise HTTPException(
                    status_code=400,
                    detail="Machine name cannot be empty",
                )

            machine_code = generate_machine_code(
                machine_name
            )

            existing_machine = session.scalars(
                select(Machine)
                .where(
                    Machine.machine_code == machine_code
                )
            ).first()

            if existing_machine is not None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "A machine with this code already exists. "
                        "Select it from Existing Machine."
                    ),
                )

            machine = Machine(
                machine_name=machine_name,
                machine_code=machine_code,
                is_active=True,
            )

            session.add(machine)
            session.flush()

        for shift_name in ("A", "B", "C"):
            start_time, end_time = (
                shift_times[shift_name]
            )

            shift = session.scalars(
                select(ShiftConfig)
                .where(
                    ShiftConfig.machine_id == machine.id
                )
                .where(
                    ShiftConfig.shift_name == shift_name
                )
            ).first()

            if shift is None:
                shift = ShiftConfig(
                    machine_id=machine.id,
                    shift_name=shift_name,
                    start_time=start_time,
                    end_time=end_time,
                )

                session.add(shift)

            else:
                shift.start_time = start_time
                shift.end_time = end_time

        for meal_name, start_time in meal_times.items():
            meal = session.scalars(
                select(MealConfig)
                .where(
                    MealConfig.machine_id == machine.id
                )
                .where(
                    MealConfig.meal_name == meal_name
                )
            ).first()

            if meal is None:
                meal = MealConfig(
                    machine_id=machine.id,
                    meal_name=meal_name,
                    start_time=start_time,
                )

                session.add(meal)

            else:
                meal.start_time = start_time

        current_assignment = get_current_assignment(
            session
        )

        if (
            current_assignment is None
            or current_assignment.machine_id != machine.id
        ):
            if current_assignment is not None:
                current_assignment.unassigned_at = now

            session.add(
                MonitorAssignment(
                    machine_id=machine.id,
                    assigned_at=now,
                )
            )

        session.flush()

        return {
            "message": "Machine configuration updated",
            "machine_id": machine.id,
            "machine": machine.machine_name,
            "machine_code": machine.machine_code,
        }


@app.get("/api/machines")
def get_machines():
    with get_session() as session:
        machines = session.scalars(
            select(Machine)
            .where(
                Machine.is_active.is_(True)
            )
            .order_by(
                Machine.machine_name.asc()
            )
        ).all()

        assignment = get_current_assignment(
            session
        )

        return {
            "current_machine_id": (
                assignment.machine_id
                if assignment
                else None
            ),
            "machines": [
                {
                    "id": machine.id,
                    "name": machine.machine_name,
                    "code": machine.machine_code,
                }
                for machine in machines
            ],
        }


@app.get("/api/status")
def get_status():
    now = datetime.now(timezone.utc)

    with get_session() as session:
        machine = get_current_machine(session)

        heartbeat = session.scalars(
            select(MonitorHeartbeat)
            .where(
                MonitorHeartbeat.machine_id == machine.id
            )
            .order_by(
                MonitorHeartbeat.last_beat.desc()
            )
            .limit(1)
        ).first()

        try:
            shift_window = get_shift_for_datetime(
                machine.id,
                now,
            )

        except ValueError:
            shift_window = None

        performance = None

        if shift_window is not None:
            shift_date = datetime.combine(
                shift_window.shift_date,
                time.min,
            )

            performance = session.scalars(
                select(ShiftPerformance)
                .where(
                    ShiftPerformance.machine_id == machine.id
                )
                .where(
                    ShiftPerformance.shift_date == shift_date
                )
                .where(
                    ShiftPerformance.shift_name
                    == shift_window.shift_name
                )
            ).first()

        current_state = (
            heartbeat.current_state
            if heartbeat
            else "UNKNOWN"
        )

        active_meal = get_active_meal(
            session,
            machine.id,
            now,
        )

        display_status = (
            f"{active_meal} TIME"
            if active_meal
            else current_state
        )

        return {
            "machine_id": machine.id,
            "machine": machine.machine_name,
            "status": current_state,
            "display_status": display_status,
            "active_meal": active_meal,
            "current_shift": (
                shift_window.shift_name
                if shift_window
                else None
            ),
            "uptime_seconds": (
                performance.up_seconds
                if performance
                else 0
            ),
            "downtime_seconds": (
                performance.down_seconds
                if performance
                else 0
            ),
            "efficiency_pct": (
                performance.efficiency_pct
                if performance
                else 0
            ),
            "last_updated": (
                heartbeat.last_beat.isoformat()
                if heartbeat
                else None
            ),
        }


@app.get("/api/today")
def get_today():
    now = datetime.now(timezone.utc)

    with get_session() as session:
        machine = get_current_machine(session)

        dashboard_date = get_dashboard_date(
            machine.id,
            now,
        )

        shift_date = datetime.combine(
            dashboard_date,
            time.min,
        )

        rows = session.scalars(
            select(ShiftPerformance)
            .where(
                ShiftPerformance.machine_id == machine.id
            )
            .where(
                ShiftPerformance.shift_date == shift_date
            )
            .order_by(
                ShiftPerformance.shift_name.asc()
            )
        ).all()

        performance_map = {
            row.shift_name: row
            for row in rows
        }

        shifts = []

        for shift_name in ("A", "B", "C"):
            row = performance_map.get(
                shift_name
            )

            shifts.append(
                {
                    "shift": shift_name,
                    "uptime_seconds": (
                        row.up_seconds if row else 0
                    ),
                    "downtime_seconds": (
                        row.down_seconds if row else 0
                    ),
                    "efficiency_pct": (
                        row.efficiency_pct if row else 0
                    ),
                    "is_final": (
                        row.is_final if row else False
                    ),
                }
            )

        return {
            "machine_id": machine.id,
            "machine": machine.machine_name,
            "date": dashboard_date.isoformat(),
            "shifts": shifts,
        }


@app.get("/api/timeline")
def get_timeline(
    selected_date: date | None = Query(
        default=None,
        alias="date",
    ),
):
    now = datetime.now(timezone.utc)

    with get_session() as session:
        machine = get_current_machine(session)

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

        range_start = min(
            window.start
            for window in windows
        )

        range_end = max(
            window.end
            for window in windows
        )

        events = session.scalars(
            select(MachineEvent)
            .where(
                MachineEvent.machine_id == machine.id
            )
            .where(
                MachineEvent.event_time >= range_start
            )
            .where(
                MachineEvent.event_time < range_end
            )
            .order_by(
                MachineEvent.event_time.asc()
            )
        ).all()

        return {
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
        }


@app.get("/api/history/7-days")
def get_seven_day_history():
    now = datetime.now(timezone.utc)

    with get_session() as session:
        machine = get_current_machine(session)

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

        rows = session.scalars(
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
        ).all()

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

            daily_map[date_key][
                "uptime_seconds"
            ] += row.up_seconds

            daily_map[date_key][
                "downtime_seconds"
            ] += row.down_seconds

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


@app.get("/api/history/custom")
def get_custom_history(
    machine_id: int,
    from_date: date,
    to_date: date,
    shifts: str = "A,B,C",
):
    if from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail="From date cannot be after to date",
        )

    selected_shifts = {
        shift.strip().upper()
        for shift in shifts.split(",")
        if shift.strip()
    }

    if not selected_shifts:
        raise HTTPException(
            status_code=400,
            detail="Select at least one shift",
        )

    if selected_shifts - {"A", "B", "C"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid shift selection",
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
            raise HTTPException(
                status_code=404,
                detail="Machine does not exist",
            )

        rows = session.scalars(
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
        ).all()

        total_up, total_down, weighted_efficiency = (
            calculate_weighted_efficiency(rows)
        )

        return {
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