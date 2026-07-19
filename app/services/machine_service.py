from sqlalchemy import select
from werkzeug.exceptions import NotFound
from app.database import get_session
from app.models import MonitorAssignment
from datetime import datetime, timezone
from app.models import Machine, MealConfig, ShiftConfig

from app.services.config_service import (
    get_current_assignment,
)
from app.services.status_service import (
    serialize_machine_config,
)


def get_machines():
    with get_session() as session:
        machines = (
            session.scalars(
                select(Machine)
                .where(
                    Machine.is_active.is_(True)
                )
                .order_by(
                    Machine.machine_name.asc()
                )
            )
            .all()
        )

        assignment = get_current_assignment(
            session
        )

        return {
            "assigned": assignment is not None,
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


def get_machine_config(machine_id):
    with get_session() as session:
        machine = session.get(
            Machine,
            machine_id,
        )

        if machine is None:
            raise NotFound(
                "Machine does not exist"
            )

        shifts = (
            session.scalars(
                select(ShiftConfig)
                .where(
                    ShiftConfig.machine_id == machine.id
                )
            )
            .all()
        )

        meals = (
            session.scalars(
                select(MealConfig)
                .where(
                    MealConfig.machine_id == machine.id
                )
            )
            .all()
        )

        return serialize_machine_config(
            machine,
            shifts,
            meals,
        )
    

def assign_machine(machine_id: int):
    now = datetime.now(timezone.utc)

    with get_session() as session:
        machine = session.get(
            Machine,
            machine_id,
        )

        if machine is None:
            raise NotFound(
                "Machine does not exist"
            )

        current_assignment = (
            session.scalars(
                select(MonitorAssignment)
                .where(MonitorAssignment.unassigned_at.is_(None))
                .order_by(MonitorAssignment.assigned_at.desc())
                .limit(1)
            )
            .first()
        )

        if (
            current_assignment is not None
            and current_assignment.machine_id == machine_id
        ):
            return {
                "message": "Machine already assigned"
            }

        if current_assignment is not None:
            current_assignment.unassigned_at = now

        session.add(
            MonitorAssignment(
                machine_id=machine_id,
                assigned_at=now,
                unassigned_at=None,
            )
        )

        session.flush()

        return {
            "message": "Machine assigned successfully"
        }