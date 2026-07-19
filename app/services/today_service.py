from datetime import datetime, time, timezone

from sqlalchemy import select

from app.database import get_session
from app.models import ShiftPerformance

from app.services.config_service import get_current_machine
from app.services.status_service import get_dashboard_date


def get_today():
    now = datetime.now(timezone.utc)

    with get_session() as session:
        machine = get_current_machine(session)

        if machine is None:
            return {
                "assigned": False,
                "machine_id": None,
                "machine": None,
                "date": None,
                "shifts": [],
            }

        dashboard_date = get_dashboard_date(
            machine.id,
            now,
        )

        shift_date = datetime.combine(
            dashboard_date,
            time.min,
        )

        rows = (
            session.scalars(
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
            )
            .all()
        )

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
            "assigned": True,
            "machine_id": machine.id,
            "machine": machine.machine_name,
            "date": dashboard_date.isoformat(),
            "shifts": shifts,
        }