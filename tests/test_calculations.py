from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.calculations import calculate_shift_performance, get_last_state_before
from app.shifts import get_shift_window

IST = ZoneInfo("Asia/Kolkata")


def local(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=IST)


@dataclass
class FakeEvent:
    state: str
    event_time: datetime


def test_no_events_no_state_change_all_down():
    window = get_shift_window(date(2026, 7, 3), "A")
    as_of = local(2026, 7, 3, 10, 0)

    result = calculate_shift_performance(
        window,
        events=[],
        as_of=as_of,
        initial_state="DOWN",
    )

    assert result.up_seconds == 0
    assert result.down_seconds == 4 * 60 * 60
    assert result.efficiency_pct == 0
    assert result.is_final is False


def test_continuous_up_no_state_change_mid_shift():
    window = get_shift_window(date(2026, 7, 3), "A")
    as_of = local(2026, 7, 3, 9, 0)

    result = calculate_shift_performance(
        window,
        events=[],
        as_of=as_of,
        initial_state="UP",
    )

    assert result.up_seconds == 3 * 60 * 60
    assert result.down_seconds == 0
    assert result.efficiency_pct == 100
    assert result.is_final is False


def test_one_transition_mid_shift():
    window = get_shift_window(date(2026, 7, 3), "A")
    events = [FakeEvent("UP", local(2026, 7, 3, 8, 0))]
    as_of = local(2026, 7, 3, 10, 0)

    result = calculate_shift_performance(
        window,
        events=events,
        as_of=as_of,
        initial_state="DOWN",
    )

    assert result.up_seconds == 2 * 60 * 60
    assert result.down_seconds == 2 * 60 * 60
    assert result.efficiency_pct == 50


def test_shift_marked_final_once_as_of_passes_end():
    window = get_shift_window(date(2026, 7, 3), "A")
    as_of = local(2026, 7, 3, 14, 0)

    result = calculate_shift_performance(
        window,
        events=[],
        as_of=as_of,
        initial_state="UP",
    )

    assert result.up_seconds == 8 * 60 * 60
    assert result.down_seconds == 0
    assert result.efficiency_pct == 100
    assert result.is_final is True


def test_shift_not_started_yet():
    window = get_shift_window(date(2026, 7, 3), "B")
    as_of = local(2026, 7, 3, 10, 0)

    result = calculate_shift_performance(
        window,
        events=[],
        as_of=as_of,
        initial_state="UP",
    )

    assert result.up_seconds == 0
    assert result.down_seconds == 0
    assert result.efficiency_pct == 0
    assert result.is_final is False


def test_midnight_crossing_shift_c_full_duration():
    window = get_shift_window(date(2026, 7, 3), "C")
    as_of = local(2026, 7, 4, 6, 0)

    result = calculate_shift_performance(
        window,
        events=[],
        as_of=as_of,
        initial_state="UP",
    )

    assert result.up_seconds == 8 * 60 * 60
    assert result.down_seconds == 0
    assert result.efficiency_pct == 100
    assert result.is_final is True


def test_get_last_state_before_empty():
    assert get_last_state_before([]) == "DOWN"


def test_get_last_state_before_uses_latest():
    events = [
        FakeEvent("UP", local(2026, 7, 3, 5, 0)),
        FakeEvent("DOWN", local(2026, 7, 3, 5, 30)),
    ]

    assert get_last_state_before(events) == "DOWN"