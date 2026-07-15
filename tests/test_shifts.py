from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.shifts import get_shift_window, get_shift_for_datetime

IST = ZoneInfo("Asia/Kolkata")


def local(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=IST)


def test_shift_a_window():
    w = get_shift_window(date(2026, 7, 3), "A")

    assert w.shift_name == "A"
    assert w.shift_date == date(2026, 7, 3)
    assert w.start == local(2026, 7, 3, 6, 0)
    assert w.end == local(2026, 7, 3, 14, 0)


def test_shift_b_window():
    w = get_shift_window(date(2026, 7, 3), "B")

    assert w.shift_name == "B"
    assert w.start == local(2026, 7, 3, 14, 0)
    assert w.end == local(2026, 7, 3, 22, 0)


def test_shift_c_crosses_midnight():
    w = get_shift_window(date(2026, 7, 3), "C")

    assert w.shift_name == "C"
    assert w.start == local(2026, 7, 3, 22, 0)
    assert w.end == local(2026, 7, 4, 6, 0)


def test_get_shift_for_datetime_during_a():
    w = get_shift_for_datetime(local(2026, 7, 3, 9, 30))

    assert w.shift_name == "A"
    assert w.shift_date == date(2026, 7, 3)


def test_get_shift_for_datetime_during_b():
    w = get_shift_for_datetime(local(2026, 7, 3, 18, 0))

    assert w.shift_name == "B"
    assert w.shift_date == date(2026, 7, 3)


def test_get_shift_for_datetime_during_c_before_midnight():
    w = get_shift_for_datetime(local(2026, 7, 3, 23, 30))

    assert w.shift_name == "C"
    assert w.shift_date == date(2026, 7, 3)


def test_get_shift_for_datetime_during_c_after_midnight():
    w = get_shift_for_datetime(local(2026, 7, 4, 2, 0))

    assert w.shift_name == "C"
    assert w.shift_date == date(2026, 7, 3)


def test_shift_boundary_is_exclusive_at_end():
    w = get_shift_for_datetime(local(2026, 7, 3, 14, 0))

    assert w.shift_name == "B"


def test_shift_boundary_is_inclusive_at_start():
    w = get_shift_for_datetime(local(2026, 7, 3, 6, 0))

    assert w.shift_name == "A"