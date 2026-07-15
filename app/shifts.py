from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.config import config
from app.database import get_session
from app.models import ShiftConfig


LOCAL_TZ = ZoneInfo(config.TIMEZONE)


@dataclass(frozen=True)
class ShiftWindow:
    shift_name: str
    shift_date: date
    start: datetime
    end: datetime

    def contains(self, dt: datetime) -> bool:
        return self.start <= dt < self.end


def _get_shift_configs(machine_id: int) -> list[ShiftConfig]:
    """
    Load all configured shifts for a machine.
    """

    with get_session() as session:
        configs = (
            session.query(ShiftConfig)
            .filter(ShiftConfig.machine_id == machine_id)
            .order_by(ShiftConfig.start_time)
            .all()
        )

        if not configs:
            raise ValueError(
                f"No shift configuration found for machine_id={machine_id}"
            )

        # Detach the objects before the session closes.
        for shift_config in configs:
            session.expunge(shift_config)

        return configs


def _get_shift_config(
    machine_id: int,
    shift_name: str,
) -> ShiftConfig:
    """
    Load one shift configuration for a machine.
    """

    with get_session() as session:
        shift_config = (
            session.query(ShiftConfig)
            .filter(
                ShiftConfig.machine_id == machine_id,
                ShiftConfig.shift_name == shift_name,
            )
            .one_or_none()
        )

        if shift_config is None:
            raise ValueError(
                f"Shift {shift_name} is not configured "
                f"for machine_id={machine_id}"
            )

        session.expunge(shift_config)

        return shift_config


def get_shift_window(
    machine_id: int,
    shift_date: date,
    shift_name: str,
) -> ShiftWindow:
    """
    Build the UTC shift window for a machine.
    """

    shift_config = _get_shift_config(
        machine_id,
        shift_name,
    )

    start_time = shift_config.start_time
    end_time = shift_config.end_time

    local_start = datetime.combine(
        shift_date,
        start_time,
        tzinfo=LOCAL_TZ,
    )

    local_end = datetime.combine(
        shift_date,
        end_time,
        tzinfo=LOCAL_TZ,
    )

    # Shift crosses midnight.
    if end_time <= start_time:
        local_end += timedelta(days=1)

    return ShiftWindow(
        shift_name=shift_name,
        shift_date=shift_date,
        start=local_start.astimezone(timezone.utc),
        end=local_end.astimezone(timezone.utc),
    )


def get_shift_for_datetime(
    machine_id: int,
    dt: datetime,
) -> ShiftWindow:
    """
    Find which configured shift contains the datetime.
    """

    if dt.tzinfo is None:
        raise ValueError(
            "Shift calculation requires a timezone-aware datetime"
        )

    local_dt = dt.astimezone(LOCAL_TZ)

    shift_configs = _get_shift_configs(machine_id)

    for day_offset in (0, -1):
        candidate_date = (
            local_dt + timedelta(days=day_offset)
        ).date()

        for shift_config in shift_configs:
            window = get_shift_window(
                machine_id,
                candidate_date,
                shift_config.shift_name,
            )

            if window.contains(
                dt.astimezone(timezone.utc)
            ):
                return window

    raise ValueError(
        f"No shift window matched for "
        f"machine_id={machine_id}, "
        f"datetime={dt.isoformat()}"
    )


def get_all_shifts_for_date(
    machine_id: int,
    shift_date: date,
) -> list[ShiftWindow]:
    """
    Return all configured shifts for a machine and date.
    """

    shift_configs = _get_shift_configs(machine_id)

    return [
        get_shift_window(
            machine_id,
            shift_date,
            shift_config.shift_name,
        )
        for shift_config in shift_configs
    ]
