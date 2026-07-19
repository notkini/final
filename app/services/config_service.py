from datetime import datetime, time, timezone
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError

from sqlalchemy import select

from app.database import get_session
from app.models import (
    Machine,
    MealConfig,
    MonitorAssignment,
    ShiftConfig,
)


def parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise BadRequest(f"Invalid time '{value}'. Expected HH:MM")


def generate_machine_code(machine_name: str) -> str:
    return machine_name.strip().upper().replace(" ", "-")


def get_current_assignment(session):
    return (
        session.scalars(
            select(MonitorAssignment)
            .where(MonitorAssignment.unassigned_at.is_(None))
            .order_by(MonitorAssignment.assigned_at.desc())
            .limit(1)
        )
        .first()
    )


def get_config():
    with get_session() as session:
        assignment = get_current_assignment(session)

        if assignment is None:
            raise NotFound("No machine is currently assigned")

        machine = session.get(Machine, assignment.machine_id)

        if machine is None:
            raise NotFound("Assigned machine does not exist")

        shifts = (
            session.scalars(
                select(ShiftConfig)
                .where(ShiftConfig.machine_id == machine.id)
            )
            .all()
        )

        shift_map = {
            shift.shift_name: shift
            for shift in shifts
        }

        for shift_name in ("A", "B", "C"):
            if shift_name not in shift_map:
                raise InternalServerError(
                    f"Shift {shift_name} configuration is missing"
                )

        meals = (
            session.scalars(
                select(MealConfig)
                .where(MealConfig.machine_id == machine.id)
            )
            .all()
        )
        
        meal_map = {
            meal.meal_name: meal
            for meal in meals
        }

        return {
            "machine": machine.machine_name,

            "shift_a_start": shift_map["A"].start_time.strftime("%H:%M"),
            "shift_a_end": shift_map["A"].end_time.strftime("%H:%M"),

            "shift_b_start": shift_map["B"].start_time.strftime("%H:%M"),
            "shift_b_end": shift_map["B"].end_time.strftime("%H:%M"),

            "shift_c_start": shift_map["C"].start_time.strftime("%H:%M"),
            "shift_c_end": shift_map["C"].end_time.strftime("%H:%M"),

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


def update_config(data):
    machine_name = (data.get("machine") or "").strip()
    machine_id = data.get("machine_id")

    shift_times = {
        "A": (
            parse_time(data["shift_a_start"]),
            parse_time(data["shift_a_end"]),
        ),
        "B": (
            parse_time(data["shift_b_start"]),
            parse_time(data["shift_b_end"]),
        ),
        "C": (
            parse_time(data["shift_c_start"]),
            parse_time(data["shift_c_end"]),
        ),
    }

    meal_times = {
        "BREAKFAST": parse_time(data["breakfast_time"]),
        "LUNCH": parse_time(data["lunch_time"]),
        "DINNER": parse_time(data["dinner_time"]),
    }

    now = datetime.now(timezone.utc)

    with get_session() as session:
        if machine_id is not None:
            machine = session.get(Machine, machine_id)

            if machine is None:
                raise NotFound("Selected machine does not exist")

        else:
            if not machine_name:
                raise BadRequest("Machine name cannot be empty")

            machine_code = generate_machine_code(machine_name)

            existing_machine = (
                session.scalars(
                    select(Machine)
                    .where(Machine.machine_code == machine_code)
                )
                .first()
            )

            if existing_machine is not None:
                raise BadRequest("A machine with this name already exists.")

            machine = Machine(
                machine_name=machine_name,
                machine_code=machine_code,
                is_active=True,
            )

            session.add(machine)
            session.flush()

        # Update Meal Configurations
        for meal_name, start_time in meal_times.items():
            meal = (
                session.scalars(
                    select(MealConfig)
                    .where(MealConfig.machine_id == machine.id)
                    .where(MealConfig.meal_name == meal_name)
                )
                .first()
            )

            if meal is None:
                meal = MealConfig(
                    machine_id=machine.id,
                    meal_name=meal_name,
                    start_time=start_time,
                )
                session.add(meal)
            else:
                meal.start_time = start_time

        # Update Shift Configurations
        for shift_name, (start_time, end_time) in shift_times.items():
            shift = (
                session.scalars(
                    select(ShiftConfig)
                    .where(ShiftConfig.machine_id == machine.id)
                    .where(ShiftConfig.shift_name == shift_name)
                )
                .first()
            )

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

        current_assignment = get_current_assignment(session)

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
                    unassigned_at=None,
                )
            )
            
        session.flush()

        return {
            "message": "Machine configuration updated",
            "machine_id": machine.id,
            "machine": machine.machine_name,
        }


def get_current_machine(session) -> Machine | None:
    assignment = get_current_assignment(session)

    if assignment is None:
        return None

    machine = session.get(
        Machine,
        assignment.machine_id,
    )

    if machine is None:
        return None

    return machine