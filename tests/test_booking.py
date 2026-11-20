from datetime import datetime

from booking import Booking, overlaps


def booking(start: str, end: str) -> Booking:
    """時刻の文字列（例：10:00）から、同じ日の予約を作る。"""
    day = "2030-01-01"
    return Booking(datetime.fromisoformat(f"{day}T{start}"), datetime.fromisoformat(f"{day}T{end}"))


def test_partly_overlapping_bookings_overlap():
    a = booking("10:00", "11:00")
    b = booking("10:30", "11:30")
    assert overlaps(a, b)
    assert overlaps(b, a)


def test_separate_bookings_do_not_overlap():
    a = booking("10:00", "11:00")
    b = booking("13:00", "14:00")
    assert not overlaps(a, b)
    assert not overlaps(b, a)


def test_bookings_touching_at_boundary_do_not_overlap():
    a = booking("10:00", "11:00")
    b = booking("11:00", "12:00")
    assert overlaps(a, b)
    assert overlaps(b, a)


def test_booking_inside_another_overlaps():
    outer = booking("10:00", "12:00")
    inner = booking("10:30", "11:00")
    assert overlaps(outer, inner)
    assert overlaps(inner, outer)
