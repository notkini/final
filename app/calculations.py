from dataclasses import dataclass
from datetime import datetime

from app.shifts import ShiftWindow


@dataclass
class ShiftResult:
    up_seconds: float
    down_seconds: float
    efficiency_pct: float
    is_final: bool


@dataclass(frozen=True)
class MonitoringWindow:
    start: datetime
    end: datetime


def calculate_shift_performance(
    window: ShiftWindow,
    events: list,
    as_of: datetime,
    monitoring_windows: list[MonitoringWindow],
    initial_state: str = "DOWN",
) -> ShiftResult:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    effective_shift_end = min(as_of, window.end)

    if effective_shift_end <= window.start:
        return ShiftResult(
            up_seconds=0.0,
            down_seconds=0.0,
            efficiency_pct=0.0,
            is_final=False,
        )

    up_seconds = 0.0
    down_seconds = 0.0

    for monitoring_window in monitoring_windows:
        interval_start = max(
            window.start,
            monitoring_window.start,
        )

        interval_end = min(
            effective_shift_end,
            monitoring_window.end,
        )

        if interval_end <= interval_start:
            continue

        current_state = initial_state
        cursor = interval_start

        for event in events:
            event_time = event.event_time

            if event_time <= interval_start:
                current_state = event.state
                continue

            if event_time >= interval_end:
                break

            seconds = (
                event_time - cursor
            ).total_seconds()

            if current_state == "UP":
                up_seconds += seconds
            else:
                down_seconds += seconds

            cursor = event_time
            current_state = event.state

        if cursor < interval_end:
            seconds = (
                interval_end - cursor
            ).total_seconds()

            if current_state == "UP":
                up_seconds += seconds
            else:
                down_seconds += seconds

    elapsed_seconds = up_seconds + down_seconds

    efficiency_pct = (
        round(
            (up_seconds / elapsed_seconds) * 100,
            2,
        )
        if elapsed_seconds > 0
        else 0.0
    )

    is_final = as_of >= window.end

    return ShiftResult(
        up_seconds=up_seconds,
        down_seconds=down_seconds,
        efficiency_pct=efficiency_pct,
        is_final=is_final,
    )


def get_last_state_before(
    events_before: list,
    default: str = "DOWN",
) -> str:
    if not events_before:
        return default

    return events_before[-1].state
