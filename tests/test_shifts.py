from datetime import date, datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.models import ShiftConfig
from app.shifts import get_shift_window, get_shift_for_datetime

IST = ZoneInfo("Asia/Kolkata")


def local(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=IST)


def make_shift(name, start_hour, end_hour):
    return ShiftConfig(
        machine_id=1,
        shift_name=name,
        start_time=time(start_hour, 0),
        end_time=time(end_hour, 0),
    )


SHIFT_CONFIGS = [
    make_shift("A", 6, 14),
    make_shift("B", 14, 22),
    ShiftConfig(
        machine_id=1,
        shift_name="C",
        start_time=time(22, 0),
        end_time=time(6, 0),
    ),
]


@patch("app.shifts._get_shift_config")
def test_shift_a_window(mock_config):
    mock_config.return_value = SHIFT_CONFIGS[0]

    w = get_shift_window(1, date(2026, 7, 3), "A")

    assert w.shift_name == "A"
    assert w.shift_date == date(2026, 7, 3)
    assert w.start == local(2026, 7, 3, 6, 0)
    assert w.end == local(2026, 7, 3, 14, 0)


@patch("app.shifts._get_shift_config")
def test_shift_b_window(mock_config):
    mock_config.return_value = SHIFT_CONFIGS[1]

    w = get_shift_window(1, date(2026, 7, 3), "B")

    assert w.shift_name == "B"
    assert w.start == local(2026, 7, 3, 14, 0)
    assert w.end == local(2026, 7, 3, 22, 0)


@patch("app.shifts._get_shift_config")
def test_shift_c_crosses_midnight(mock_config):
    mock_config.return_value = SHIFT_CONFIGS[2]

    w = get_shift_window(1, date(2026, 7, 3), "C")

    assert w.shift_name == "C"
    assert w.start == local(2026, 7, 3, 22, 0)
    assert w.end == local(2026, 7, 4, 6, 0)


@patch("app.shifts._get_shift_configs")
def test_get_shift_for_datetime_during_a(mock_configs):
    mock_configs.return_value = SHIFT_CONFIGS

    w = get_shift_for_datetime(
        1,
        local(2026, 7, 3, 9, 30),
    )

    assert w.shift_name == "A"
    assert w.shift_date == date(2026, 7, 3)


@patch("app.shifts._get_shift_configs")
def test_get_shift_for_datetime_during_b(mock_configs):
    mock_configs.return_value = SHIFT_CONFIGS

    w = get_shift_for_datetime(
        1,
        local(2026, 7, 3, 18, 0),
    )

    assert w.shift_name == "B"
    assert w.shift_date == date(2026, 7, 3)


@patch("app.shifts._get_shift_configs")
def test_get_shift_for_datetime_during_c_before_midnight(mock_configs):
    mock_configs.return_value = SHIFT_CONFIGS

    w = get_shift_for_datetime(
        1,
        local(2026, 7, 3, 23, 30),
    )

    assert w.shift_name == "C"
    assert w.shift_date == date(2026, 7, 3)


@patch("app.shifts._get_shift_configs")
def test_get_shift_for_datetime_during_c_after_midnight(mock_configs):
    mock_configs.return_value = SHIFT_CONFIGS

    w = get_shift_for_datetime(
        1,
        local(2026, 7, 4, 2, 0),
    )

    assert w.shift_name == "C"
    assert w.shift_date == date(2026, 7, 3)


@patch("app.shifts._get_shift_configs")
def test_shift_boundary_is_exclusive_at_end(mock_configs):
    mock_configs.return_value = SHIFT_CONFIGS

    w = get_shift_for_datetime(
        1,
        local(2026, 7, 3, 14, 0),
    )

    assert w.shift_name == "B"


@patch("app.shifts._get_shift_config")
@patch("app.shifts._get_shift_configs")
def test_shift_boundary_is_inclusive_at_start(
    mock_configs,
    mock_config,
):
    mock_configs.return_value = SHIFT_CONFIGS

    def get_config(machine_id, shift_name):
        return next(
            cfg
            for cfg in SHIFT_CONFIGS
            if cfg.shift_name == shift_name
        )

    mock_config.side_effect = get_config

    w = get_shift_for_datetime(
        1,
        local(2026, 7, 3, 6, 0),
    )

    assert w.shift_name == "A"